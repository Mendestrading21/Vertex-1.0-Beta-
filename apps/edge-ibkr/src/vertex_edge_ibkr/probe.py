"""Bounded IBKR entitlement probe (docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md).

The probe answers, for one exact underlying and one exact option: which fields
does the API actually deliver, with which market-data type, when, under which
limits and with which proof. The result is an immutable, per-field
``SourceCapabilitySnapshot`` whose statuses come from
``vertex_core.contracts.SourceCapabilityStatus``.

Hard rules implemented here:

- 6 bounded steps: preflight, chain definition, underlying live, option live,
  optional delayed fallback, cancel-and-publish;
- a single probe active at a time; at most 2 simultaneous data lines;
- injectable step timeout (12s), total deadline (60s) and result TTL (21600s);
- the provider error mapping is EXACTLY the manifest's
  (``manifests/ibkr-market-data-capabilities.yaml``);
- ``ERROR`` is NEVER converted into ``NOT_ENTITLED``: a timeout, rate
  breach, competing session or missing tick is inconclusive, not a proof of
  missing entitlement;
- delayed/frozen evidence is recorded as ``DELAYED`` and never requalified
  live.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic as _time_monotonic
from typing import Any

from vertex_core.contracts import ContractModel, NonEmptyStr, SourceCapabilityStatus, UtcDatetime
from vertex_edge_ibkr.pacing import LineBudget
from vertex_edge_ibkr.port import (
    DELAYED_QUOTE_TICKS,
    LIVE_QUOTE_TICKS,
    CancellationOutcome,
    ContractSpec,
    EdgeIbkrError,
    GreeksObservation,
    IbkrInformationPort,
    MarketDataSnapshotResult,
    ProviderError,
    QuoteObservation,
)
from vertex_edge_ibkr.state import PROVIDER_STATUS_CODES

__all__ = [
    "INFORMATIONAL_CODE_RANGE",
    "PROVIDER_ERROR_MAPPING",
    "CapabilityFieldEvidence",
    "EntitlementProbe",
    "ProbeAlreadyActiveError",
    "ProbeConfig",
    "ProbeGate",
    "ProbeSessionCompromisedError",
    "ProviderErrorMapping",
    "SourceCapabilitySnapshot",
    "is_informational_code",
    "map_provider_error",
]

_STATUS = SourceCapabilityStatus


# --------------------------------------------------------------------------
# Manifest error mapping — EXACT, never widened, never reinterpreted
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderErrorMapping:
    """How one provider error code translates into a capability status."""

    status: SourceCapabilityStatus
    reason_code: str
    per_field: bool = False
    #: True for a provider NOTICE (codes 2100-2200): a status message, not a
    #: failure. Such a code must never mask the honest reason of a field that
    #: simply received no tick.
    informational: bool = False


#: Exact mapping from manifests/ibkr-market-data-capabilities.yaml.
PROVIDER_ERROR_MAPPING: dict[int, ProviderErrorMapping] = {
    100: ProviderErrorMapping(_STATUS.ERROR, "MESSAGE_RATE_EXCEEDED"),
    101: ProviderErrorMapping(_STATUS.ERROR, "MARKET_DATA_LINES_EXHAUSTED"),
    354: ProviderErrorMapping(_STATUS.NOT_ENTITLED, "LIVE_MARKET_DATA_NOT_SUBSCRIBED"),
    10090: ProviderErrorMapping(
        _STATUS.NOT_ENTITLED, "PARTIAL_MARKET_DATA_SUBSCRIPTION", per_field=True
    ),
    10186: ProviderErrorMapping(
        _STATUS.NOT_ENTITLED, "LIVE_NOT_SUBSCRIBED_DELAYED_NOT_ENABLED"
    ),
    10197: ProviderErrorMapping(_STATUS.ERROR, "COMPETING_SESSION"),
}


#: Plage des NOTIFICATIONS fournisseur d'IBKR (message_codes.html) : messages
#: d'avertissement et de statut, PAS des erreurs. `2104 Market data farm
#: connection is OK` en fait partie — le traiter comme une erreur masquait la
#: raison honnete des champs simplement non observes (mesure du 2026-08-31).
INFORMATIONAL_CODE_RANGE: tuple[int, int] = (2100, 2200)


def is_informational_code(code: int) -> bool:
    """True pour une NOTICE fournisseur, jamais pour une erreur mappee.

    Un code explicitement present au manifeste garde son sens, meme s'il
    tombait dans la plage : le manifeste reste l'autorite.
    """
    if code in PROVIDER_ERROR_MAPPING:
        return False
    return INFORMATIONAL_CODE_RANGE[0] <= code <= INFORMATIONAL_CODE_RANGE[1]


def map_provider_error(code: int) -> ProviderErrorMapping:
    """Exact manifest mapping; unknown codes are inconclusive (``ERROR``).

    An unknown or transport-level code never becomes ``NOT_ENTITLED``. A
    provider NOTICE (2100-2200) is flagged ``informational`` so it never
    replaces the honest reason of an unobserved field.
    """
    mapping = PROVIDER_ERROR_MAPPING.get(code)
    if mapping is not None:
        return mapping
    if is_informational_code(code):
        return ProviderErrorMapping(
            _STATUS.ERROR, f"PROVIDER_NOTICE_{code}", informational=True
        )
    return ProviderErrorMapping(_STATUS.ERROR, f"UNMAPPED_PROVIDER_ERROR_{code}")


# --------------------------------------------------------------------------
# Immutable probe result
# --------------------------------------------------------------------------


class CapabilityFieldEvidence(ContractModel):
    """Per-field proof: status, tick, market-data type, instant, error."""

    capability_id: NonEmptyStr
    field: NonEmptyStr
    status: SourceCapabilityStatus
    reason_code: NonEmptyStr | None = None
    tick_type: int | None = None
    market_data_type: int | None = None
    observed_at: UtcDatetime | None = None
    provider_error_code: int | None = None


class SourceCapabilitySnapshot(ContractModel):
    """Immutable per-field capability snapshot with a bounded validity.

    Valid only for the tested instrument, venue, technical user, environment
    and connection epoch. Once ``expires_at`` passes, the capability becomes
    unknown for the gates and must be re-probed.
    """

    probe_id: NonEmptyStr
    source: NonEmptyStr
    connection_epoch: int
    tested_at: UtcDatetime
    expires_at: UtcDatetime
    fields: tuple[CapabilityFieldEvidence, ...]

    def field_evidence(self, capability_id: str, field: str) -> CapabilityFieldEvidence | None:
        for evidence in self.fields:
            if evidence.capability_id == capability_id and evidence.field == field:
                return evidence
        return None

    def status_of(self, capability_id: str, field: str) -> SourceCapabilityStatus | None:
        evidence = self.field_evidence(capability_id, field)
        return None if evidence is None else evidence.status

    def is_valid_at(self, now: datetime) -> bool:
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("naive datetime rejected: aware UTC required")
        return now < self.expires_at


# --------------------------------------------------------------------------
# Single-probe gate
# --------------------------------------------------------------------------


class ProbeAlreadyActiveError(RuntimeError):
    """A second concurrent probe was refused: one probe active at a time."""


class ProbeSessionCompromisedError(EdgeIbkrError):
    """A market-data line could not be proved closed after one retry."""


class ProbeGate:
    """Exclusive slot: at most one entitlement probe runs at any moment."""

    def __init__(self) -> None:
        self._active_probe_id: str | None = None

    @property
    def active_probe_id(self) -> str | None:
        return self._active_probe_id

    def acquire(self, probe_id: str) -> None:
        if self._active_probe_id is not None:
            raise ProbeAlreadyActiveError(
                f"probe {self._active_probe_id} is already active; one probe at a time"
            )
        self._active_probe_id = probe_id

    def release(self, probe_id: str) -> None:
        if self._active_probe_id == probe_id:
            self._active_probe_id = None


_DEFAULT_GATE = ProbeGate()


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProbeConfig:
    """Bounded probe configuration (manifest ``probe_defaults``).

    The exact underlying and option come from local configuration — nothing
    popular is hard-coded. Both must carry a ``con_id``; the option must carry
    its ``trading_class``. Ambiguity stops the probe before it starts.
    """

    underlying: ContractSpec
    option: ContractSpec
    allow_delayed_fallback: bool = False
    step_timeout_seconds: float = 12.0
    total_deadline_seconds: float = 60.0
    result_ttl_seconds: float = 21600.0
    max_concurrent_lines: int = 2

    def __post_init__(self) -> None:
        if self.underlying.con_id is None:
            raise ValueError("underlying con_id is required (exact contract only)")
        if self.option.con_id is None:
            raise ValueError("option con_id is required (exact contract only)")
        if not self.option.trading_class:
            raise ValueError("option trading_class is required (exact contract only)")
        if self.step_timeout_seconds <= 0 or self.total_deadline_seconds <= 0:
            raise ValueError("timeouts must be strictly positive")
        if self.result_ttl_seconds <= 0:
            raise ValueError("result_ttl_seconds must be strictly positive")
        if self.max_concurrent_lines < 1:
            raise ValueError("max_concurrent_lines must be >= 1")


# --------------------------------------------------------------------------
# Field plans (what each step is allowed to prove)
# --------------------------------------------------------------------------

CHAIN_CAPABILITY = "option_chain_definition"
UNDERLYING_TOP = "underlying_top_of_book"
OPTION_TOP = "option_top_of_book"
OPTION_GREEKS_LIVE = "option_computations_live"
OPTION_GREEKS_DELAYED = "option_computations_delayed"

#: Generic-tick capabilities requested on the exact underlying (manifest:
#: ``requires_exact_underlying``), with their payload attribute and tick id.
GENERIC_CAPABILITY_FIELDS: tuple[tuple[str, str, int], ...] = (
    ("underlying_call_put_option_volume", "call_volume", 29),
    ("underlying_call_put_option_volume", "put_volume", 30),
    ("option_open_interest", "call_open_interest", 27),
    ("option_open_interest", "put_open_interest", 28),
    ("underlying_historical_volatility_30d", "historical_volatility_30d", 23),
    ("underlying_average_option_volume", "average_option_volume", 87),
    ("underlying_option_implied_volatility_30d", "option_implied_volatility_30d", 24),
)

#: Generic ticks requested with the underlying subscription.
UNDERLYING_GENERIC_TICKS: tuple[int, ...] = (100, 101, 104, 105, 106)

TOP_OF_BOOK_FIELDS: tuple[str, ...] = ("bid", "ask", "last", "volume")
GREEK_FIELDS: tuple[str, ...] = ("implied_volatility", "delta", "gamma", "vega", "theta")


@dataclass(frozen=True, slots=True)
class _FieldPlan:
    capability_id: str
    field: str
    payload_attr: str
    kind: str  # "quote" | "greek"
    tick_type: int | None = None  # fixed tick id for generic quote fields


def _underlying_plan() -> tuple[_FieldPlan, ...]:
    plan = [
        _FieldPlan(UNDERLYING_TOP, name, name, "quote") for name in TOP_OF_BOOK_FIELDS
    ]
    plan.extend(
        _FieldPlan(capability, attr, attr, "quote", tick)
        for capability, attr, tick in GENERIC_CAPABILITY_FIELDS
    )
    return tuple(plan)


def _option_live_plan() -> tuple[_FieldPlan, ...]:
    plan = [_FieldPlan(OPTION_TOP, name, name, "quote") for name in TOP_OF_BOOK_FIELDS]
    plan.extend(_FieldPlan(OPTION_GREEKS_LIVE, name, name, "greek") for name in GREEK_FIELDS)
    return tuple(plan)


def _option_delayed_plan() -> tuple[_FieldPlan, ...]:
    return tuple(_FieldPlan(OPTION_GREEKS_DELAYED, name, name, "greek") for name in GREEK_FIELDS)


class _DeadlineExhausted(Exception):
    """Internal: the total probe deadline was consumed."""


# --------------------------------------------------------------------------
# The probe
# --------------------------------------------------------------------------


class EntitlementProbe:
    """One bounded, cancellable, single-flight entitlement probe.

    Everything temporal is injectable: ``clock`` (aware UTC now, for
    ``tested_at``/``expires_at``), ``monotonic`` (seconds, for the total
    deadline) and the per-step timeout in the configuration.
    """

    def __init__(
        self,
        port: IbkrInformationPort,
        config: ProbeConfig,
        *,
        epoch_provider: Callable[[], int],
        gate: ProbeGate | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] = _time_monotonic,
        probe_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        if clock is None:
            raise ValueError("clock must be injected (aware UTC now); no implicit time source")
        self._port = port
        self._config = config
        self._gate = gate if gate is not None else _DEFAULT_GATE
        self._clock = clock
        self._monotonic = monotonic
        self._epoch_provider = epoch_provider
        self._probe_id_factory = probe_id_factory
        # Structural line bound: never more than max_concurrent_lines (<= 2 by
        # default) simultaneous data lines, whatever the steps do.
        self._lines = LineBudget(
            detected_lines=config.max_concurrent_lines * 2,
            hard_cap=config.max_concurrent_lines,
        )

    async def run(self) -> SourceCapabilitySnapshot:
        """Execute the 6 bounded steps and publish the immutable snapshot."""
        probe_id = self._probe_id_factory()
        self._gate.acquire(probe_id)  # step gate: one probe at a time
        try:
            return await self._execute(probe_id)
        finally:
            self._gate.release(probe_id)

    # -- internals ---------------------------------------------------------

    async def _execute(self, probe_id: str) -> SourceCapabilitySnapshot:
        self._require_clean_session()
        probe_epoch = self._require_probe_epoch()
        config = self._config
        deadline = self._monotonic() + config.total_deadline_seconds
        evidence: dict[tuple[str, str], CapabilityFieldEvidence] = {}
        planned: list[_FieldPlan] = [
            _FieldPlan(CHAIN_CAPABILITY, "definition", "definition", "quote"),
            *_underlying_plan(),
            *_option_live_plan(),
        ]

        try:
            # Step 1 — preflight: connection and server clock must answer.
            try:
                await self._bounded(self._port.server_time, deadline)
            except TimeoutError:
                self._require_probe_epoch(probe_epoch)
                self._fill_missing(evidence, planned, _STATUS.ERROR, "STEP_TIMEOUT")
                return self._publish(probe_id, evidence, connection_epoch=probe_epoch)
            except ProviderError as exc:
                if exc.code in PROVIDER_STATUS_CODES:
                    raise
                self._require_probe_epoch(probe_epoch)
                mapping = map_provider_error(exc.code)
                # Fields never probed are inconclusive: always ERROR here,
                # never NOT_ENTITLED (nothing was requested for them).
                reason = (
                    mapping.reason_code
                    if mapping.status is _STATUS.ERROR
                    else "PREFLIGHT_FAILED"
                )
                self._fill_missing(evidence, planned, _STATUS.ERROR, reason, exc.code)
                return self._publish(probe_id, evidence, connection_epoch=probe_epoch)
            self._require_probe_epoch(probe_epoch)

            # Step 2 — chain definition (definition only, never quote proof).
            await self._chain_step(evidence, deadline, probe_epoch)

            # Step 3 — underlying live with the manifest generic ticks.
            await self._snapshot_step(
                evidence,
                _underlying_plan(),
                self._config.underlying,
                generic_ticks=UNDERLYING_GENERIC_TICKS,
                market_data_type=1,
                deadline=deadline,
                expected_epoch=probe_epoch,
            )

            # Step 4 — option live and computations.
            await self._snapshot_step(
                evidence,
                _option_live_plan(),
                self._config.option,
                generic_ticks=(),
                market_data_type=1,
                deadline=deadline,
                expected_epoch=probe_epoch,
            )

            # Step 5 — delayed fallback, only if live was refused AND the
            # local configuration explicitly allows it.
            if config.allow_delayed_fallback and self._live_option_refused(evidence):
                delayed_plan = _option_delayed_plan()
                planned.extend(delayed_plan)
                await self._snapshot_step(
                    evidence,
                    delayed_plan,
                    self._config.option,
                    generic_ticks=(),
                    market_data_type=3,
                    deadline=deadline,
                    expected_epoch=probe_epoch,
                )
        except _DeadlineExhausted:
            self._require_probe_epoch(probe_epoch)
            self._fill_missing(evidence, planned, _STATUS.ERROR, "PROBE_DEADLINE_EXCEEDED")

        self._require_probe_epoch(probe_epoch)
        self._fill_missing(evidence, planned, _STATUS.ERROR, "NO_OBSERVATION")
        return self._publish(probe_id, evidence, connection_epoch=probe_epoch)

    async def _bounded(self, factory: Callable[[], Any], deadline: float) -> Any:
        """Run ``factory()`` with min(step timeout, remaining total budget).

        ``factory`` is a zero-argument callable returning the awaitable, so
        nothing is created (and later leaked) when the deadline is already
        consumed.
        """
        remaining = deadline - self._monotonic()
        if remaining <= 0:
            raise _DeadlineExhausted()
        timeout = min(self._config.step_timeout_seconds, remaining)
        return await asyncio.wait_for(factory(), timeout=timeout)

    async def _chain_step(
        self,
        evidence: dict[tuple[str, str], CapabilityFieldEvidence],
        deadline: float,
        expected_epoch: int,
    ) -> None:
        key = (CHAIN_CAPABILITY, "definition")
        self._require_probe_epoch(expected_epoch)
        try:
            chains = await self._bounded(
                lambda: self._port.sec_def_opt_params(self._config.underlying), deadline
            )
        except TimeoutError:
            self._require_probe_epoch(expected_epoch)
            evidence[key] = self._evidence(key, _STATUS.ERROR, "STEP_TIMEOUT")
            return
        except ProviderError as exc:
            if exc.code in PROVIDER_STATUS_CODES:
                raise
            self._require_probe_epoch(expected_epoch)
            mapping = map_provider_error(exc.code)
            evidence[key] = self._evidence(
                key, mapping.status, mapping.reason_code, provider_error_code=exc.code
            )
            return
        self._require_probe_epoch(expected_epoch)
        if chains:
            evidence[key] = self._evidence(
                key, _STATUS.AVAILABLE, None, observed_at=self._clock()
            )
        else:
            # A silent empty answer is inconclusive, never proof of absence.
            evidence[key] = self._evidence(key, _STATUS.ERROR, "NO_OBSERVATION")

    async def _snapshot_step(
        self,
        evidence: dict[tuple[str, str], CapabilityFieldEvidence],
        plan: tuple[_FieldPlan, ...],
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...],
        market_data_type: int,
        deadline: float,
        expected_epoch: int,
    ) -> None:
        self._require_probe_epoch(expected_epoch)
        pending_before = self._require_clean_session()
        self._lines.acquire()  # structural <= max_concurrent_lines bound
        try:
            result = await self._bounded(
                lambda: self._port.market_data_snapshot(
                    spec,
                    generic_ticks=generic_ticks,
                    market_data_type=market_data_type,
                ),
                deadline,
            )
        except TimeoutError:
            self._require_probe_epoch(expected_epoch)
            if self._port.pending_subscription_count > pending_before:
                # The adapter preserved the task cancellation raised by
                # asyncio.wait_for. Re-raise that primary timeout: a retained
                # provider line makes the whole session unfit for another
                # instrument and no capability snapshot may be published.
                raise
            self._assign_step_failure(evidence, plan, _STATUS.ERROR, "STEP_TIMEOUT", None)
            return
        except ProviderError as exc:
            if exc.code in PROVIDER_STATUS_CODES:
                raise
            self._require_probe_epoch(expected_epoch)
            if self._port.pending_subscription_count > pending_before:
                # The adapter retained both this primary provider error and
                # the unconfirmed line. Never downgrade it into field evidence
                # and then continue with another instrument.
                raise
            mapping = map_provider_error(exc.code)
            self._assign_step_failure(
                evidence, plan, mapping.status, mapping.reason_code, exc.code
            )
            return
        finally:
            self._lines.release()
        await self._confirm_cancellation(
            result,
            pending_before=pending_before,
            deadline=deadline,
        )
        self._validate_snapshot_epoch(result, expected_epoch)
        self._interpret_snapshot(evidence, plan, result)

    async def _confirm_cancellation(
        self,
        result: MarketDataSnapshotResult,
        *,
        pending_before: int,
        deadline: float,
    ) -> None:
        """Require a closed line before evidence or another request is allowed.

        The adapter already attempted cancellation while producing ``result``.
        A non-confirmed outcome gets exactly one immediate retry. Any remaining
        ambiguity aborts the probe without a publishable snapshot; the adapter
        keeps the line quarantined until its owning session is disconnected.
        """
        outcome = result.cancellation_outcome
        if outcome is CancellationOutcome.SESSION_CLOSED:
            raise ProbeSessionCompromisedError(
                "provider session closed before the market-data observation "
                "could be admitted"
            )

        registry_released = self._port.pending_subscription_count <= pending_before
        if outcome is CancellationOutcome.CANCELLED and registry_released:
            return

        try:
            outcome = await self._bounded(
                lambda: self._port.cancel_subscription(result.subscription_id),
                deadline,
            )
        except _DeadlineExhausted as exc:
            raise ProbeSessionCompromisedError(
                "market-data cancellation retry could not start before the probe deadline"
            ) from exc
        except TimeoutError as exc:
            raise ProbeSessionCompromisedError(
                "market-data cancellation retry timed out"
            ) from exc
        registry_released = self._port.pending_subscription_count <= pending_before
        if outcome is CancellationOutcome.CANCELLED and registry_released:
            return

        raise ProbeSessionCompromisedError(
            "market-data cancellation was not confirmed after one retry "
            f"(outcome={outcome.value})"
        )

    def _require_clean_session(self) -> int:
        pending = self._port.pending_subscription_count
        if pending != 0:
            raise ProbeSessionCompromisedError(
                "provider session already has unresolved market-data lines"
            )
        return pending

    def _require_probe_epoch(self, expected: int | None = None) -> int:
        """Require one positive, unchanged connection epoch for the whole probe."""
        current = self._epoch_provider()
        if (
            not isinstance(current, int)
            or isinstance(current, bool)
            or current <= 0
        ):
            raise ProbeSessionCompromisedError(
                "probe requires a positive connected-session epoch"
            )
        if expected is not None and current != expected:
            raise ProbeSessionCompromisedError(
                "connection epoch changed during the capability probe"
            )
        return current

    def _validate_snapshot_epoch(
        self,
        result: MarketDataSnapshotResult,
        expected_epoch: int,
    ) -> None:
        """Reject mixed-session evidence before it can enter the matrix."""
        self._require_probe_epoch(expected_epoch)
        if result.operation.connection_epoch_at_start != expected_epoch:
            raise ProbeSessionCompromisedError(
                "snapshot operation belongs to another connection epoch"
            )
        if any(
            envelope.connection_epoch != expected_epoch
            for envelope in result.envelopes
        ):
            raise ProbeSessionCompromisedError(
                "snapshot evidence mixes connection epochs"
            )

    def _interpret_snapshot(
        self,
        evidence: dict[tuple[str, str], CapabilityFieldEvidence],
        plan: tuple[_FieldPlan, ...],
        result: MarketDataSnapshotResult,
    ) -> None:
        reported = result.reported_market_data_type
        delayed = result.requested_market_data_type in (3, 4) or reported in (3, 4)
        observed_status = _STATUS.DELAYED if delayed else _STATUS.AVAILABLE
        quote_ticks = DELAYED_QUOTE_TICKS if delayed else LIVE_QUOTE_TICKS

        error_mapped: tuple[int, ProviderErrorMapping] | None = None
        entitlement_mapped: tuple[int, ProviderErrorMapping] | None = None
        for info in result.provider_errors:
            mapping = map_provider_error(info.code)
            if mapping.informational:
                # Une NOTICE de bon fonctionnement ne dit rien du droit : la
                # laisser gagner remplacerait `NO_OBSERVATION` par une raison
                # fausse.
                continue
            if mapping.status is _STATUS.ERROR and error_mapped is None:
                error_mapped = (info.code, mapping)
            if mapping.status is _STATUS.NOT_ENTITLED and entitlement_mapped is None:
                entitlement_mapped = (info.code, mapping)

        for item in plan:
            key = (item.capability_id, item.field)
            observed = self._extract(result, item)
            if observed is not None:
                value_tick, observed_at, mdt = observed
                tick = value_tick if value_tick is not None else quote_ticks.get(item.field)
                if item.tick_type is not None:
                    tick = item.tick_type
                evidence[key] = self._evidence(
                    key,
                    observed_status,
                    None,
                    tick_type=tick,
                    market_data_type=mdt if mdt is not None else reported,
                    observed_at=observed_at,
                )
            elif error_mapped is not None:
                # ERROR always wins for unobserved fields: an inconclusive
                # probe is never converted into a NOT_ENTITLED proof.
                code, mapping = error_mapped
                evidence[key] = self._evidence(
                    key, _STATUS.ERROR, mapping.reason_code, provider_error_code=code
                )
            elif entitlement_mapped is not None:
                code, mapping = entitlement_mapped
                evidence[key] = self._evidence(
                    key,
                    _STATUS.NOT_ENTITLED,
                    mapping.reason_code,
                    provider_error_code=code,
                )
            else:
                # No tick during a short window is not proof of non-entitlement.
                evidence[key] = self._evidence(key, _STATUS.ERROR, "NO_OBSERVATION")

    def _extract(
        self, result: MarketDataSnapshotResult, item: _FieldPlan
    ) -> tuple[int | None, datetime | None, int | None] | None:
        """Return (tick_type, observed_at, market_data_type) when observed."""
        if item.kind == "quote":
            for envelope in result.envelopes:
                payload = envelope.payload
                if isinstance(payload, QuoteObservation):
                    if getattr(payload, item.payload_attr) is not None:
                        observed_at = envelope.observed_at or envelope.as_of
                        return None, observed_at, payload.market_data_type
                    return None
            return None
        for envelope in result.envelopes:
            payload = envelope.payload
            if isinstance(payload, GreeksObservation):
                if getattr(payload, item.payload_attr) is not None:
                    observed_at = envelope.observed_at or envelope.as_of
                    return payload.tick_type, observed_at, payload.market_data_type
        return None

    def _live_option_refused(
        self, evidence: dict[tuple[str, str], CapabilityFieldEvidence]
    ) -> bool:
        for (capability_id, _field), item in evidence.items():
            if capability_id in (OPTION_TOP, OPTION_GREEKS_LIVE):
                if item.status is _STATUS.NOT_ENTITLED:
                    return True
        return False

    def _assign_step_failure(
        self,
        evidence: dict[tuple[str, str], CapabilityFieldEvidence],
        plan: tuple[_FieldPlan, ...],
        status: SourceCapabilityStatus,
        reason: str,
        provider_error_code: int | None,
    ) -> None:
        for item in plan:
            key = (item.capability_id, item.field)
            if key not in evidence:
                evidence[key] = self._evidence(
                    key, status, reason, provider_error_code=provider_error_code
                )

    def _fill_missing(
        self,
        evidence: dict[tuple[str, str], CapabilityFieldEvidence],
        planned: list[_FieldPlan],
        status: SourceCapabilityStatus,
        reason: str,
        provider_error_code: int | None = None,
    ) -> None:
        for item in planned:
            key = (item.capability_id, item.field)
            if key not in evidence:
                evidence[key] = self._evidence(
                    key, status, reason, provider_error_code=provider_error_code
                )

    def _evidence(
        self,
        key: tuple[str, str],
        status: SourceCapabilityStatus,
        reason_code: str | None,
        *,
        tick_type: int | None = None,
        market_data_type: int | None = None,
        observed_at: datetime | None = None,
        provider_error_code: int | None = None,
    ) -> CapabilityFieldEvidence:
        return CapabilityFieldEvidence(
            capability_id=key[0],
            field=key[1],
            status=status,
            reason_code=reason_code,
            tick_type=tick_type,
            market_data_type=market_data_type,
            observed_at=observed_at,
            provider_error_code=provider_error_code,
        )

    def _publish(
        self,
        probe_id: str,
        evidence: dict[tuple[str, str], CapabilityFieldEvidence],
        *,
        connection_epoch: int,
    ) -> SourceCapabilitySnapshot:
        self._require_probe_epoch(connection_epoch)
        tested_at = self._clock()
        expires_at = tested_at + timedelta(seconds=self._config.result_ttl_seconds)
        ordered = tuple(
            evidence[key] for key in sorted(evidence.keys())
        )
        return SourceCapabilitySnapshot(
            probe_id=probe_id,
            source="ibkr",
            connection_epoch=connection_epoch,
            tested_at=tested_at,
            expires_at=expires_at,
            fields=ordered,
        )
