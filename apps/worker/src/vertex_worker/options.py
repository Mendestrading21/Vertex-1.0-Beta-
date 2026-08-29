"""Option-chain snapshot chain: ``option_chains.ingested`` handler.

Topic decision (documented, same pattern as ``quotes.ingested``): ingestion
enqueues an ADDITIONAL ``option_chains.ingested`` message when (and only
when) the ingested envelope carries an option-chain schema
(:func:`is_option_chain_schema`) — same transaction, same idempotence. The
registry stays strictly one-handler-per-topic.

The handler recomputes one ``option_chain/{underlying}`` snapshot per
declared underlying present in the recent observation window:

- per ``(expiration, trading_class)`` — two trading classes at the SAME
  expiration are two distinct groups, never merged — the snapshot lists every
  contract with its COMPLETE identity (synthetic ``con_id``, trading class,
  strike, right, multiplier, currency, exchange, style, settlement,
  expiration); a contract with an incomplete identity is discarded with a
  reason and NO calculation ever runs on it;
- quotes are relayed VERBATIM (decimal strings) with a quality status:
  ``OK``, ``CROSSED`` (bid > ask), ``STALE`` (older than the configured
  maximum age) or ``MISSING``. Locked quotes (bid == ask) are ``CROSSED``
  for calculation purposes: an unexplained locked quote is never a healthy
  IV input;
- Vertex IV is resolved through the single authority
  ``vertex_core.calculations.options.implied_volatility`` on the MID of a
  sane quote ONLY — a crossed, locked, stale or missing quote NEVER gets an
  IV; the refusal reason is recorded instead. Greeks are computed on the
  resolved IV only. Both carry ``value_nature = "THEORETICAL"`` and the
  preserved :class:`CalculationRecord` lineage (engine version, method,
  input/result hashes);
- per-group coverage accounts expected/received/valid/resolved contracts
  with per-contract discard reasons; a global row budget is applied and
  displayed (truncation is counted, never silent);
- ``population`` propagates ``SYNTHETIC`` as soon as one record is
  synthetic.

Publication follows the same publish-if-changed semantics as the other
handlers; identical inputs and clock republish nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_core.calculations.options import (
    IVNoSolutionError,
    OptionInputError,
    greeks,
    implied_volatility,
)
from vertex_core.contracts import CalculationRecord, make_calculation_record
from vertex_core.synthetic import (
    SYNTHETIC_OPTION_UNDERLYINGS,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
)
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.models import Observation
from vertex_persistence.repository.outbox import ClaimedOutboxMessage

from vertex_worker.registry import HandlerRegistry

__all__ = [
    "DEV_SYNTHETIC_OPTIONS_CONFIG",
    "OPTION_CHAIN_SCHEMA_PREFIXES",
    "OPTION_CHAIN_SCHEMA_VERSION",
    "QUOTE_STATUS_CROSSED",
    "QUOTE_STATUS_MISSING",
    "QUOTE_STATUS_OK",
    "QUOTE_STATUS_STALE",
    "REASON_CONTRACT_EXPIRED",
    "REASON_INCOMPLETE_IDENTITY",
    "REASON_INVALID_PAYLOAD",
    "REASON_IV_UNRESOLVED",
    "REASON_QUOTE_CROSSED",
    "REASON_QUOTE_MISSING",
    "REASON_QUOTE_STALE",
    "REASON_RIGHTS_NOT_USABLE",
    "REASON_SOURCE_NOT_ALLOWED",
    "REASON_UNDERLYING_NOT_DECLARED",
    "SNAPSHOT_KIND_OPTION_CHAIN",
    "TOPIC_OPTION_CHAINS_INGESTED",
    "VALUE_NATURE_THEORETICAL",
    "OptionChainRecord",
    "OptionChainsHandler",
    "OptionsConfig",
    "build_option_chain_content",
    "is_option_chain_schema",
    "load_option_chain_records",
    "register_options_handler",
]

log = logging.getLogger("vertex_worker.options")

Clock = Callable[[], datetime]

TOPIC_OPTION_CHAINS_INGESTED = "option_chains.ingested"
"""Outbox topic enqueued (in addition to ``observation.ingested``) for every
newly written option-chain observation."""

SNAPSHOT_KIND_OPTION_CHAIN = "option_chain"
OPTION_CHAIN_SCHEMA_VERSION = "vertex.option-chain/1.0"

OPTION_CHAIN_SCHEMA_PREFIXES: tuple[str, ...] = ("synthetic-option-chain/",)
"""Schema families recognized as option chains (extensible; deny by default)."""

VALUE_NATURE_THEORETICAL = "THEORETICAL"
"""Nature label of every Vertex IV/Greek in the snapshot: a theoretical value
derived from a model, NEVER a quote and never presented as one."""

QUOTE_STATUS_OK = "OK"
QUOTE_STATUS_CROSSED = "CROSSED"
QUOTE_STATUS_STALE = "STALE"
QUOTE_STATUS_MISSING = "MISSING"

REASON_QUOTE_MISSING = "missing_quote"
REASON_QUOTE_CROSSED = "crossed_quote"
REASON_QUOTE_STALE = "stale_quote"
REASON_CONTRACT_EXPIRED = "contract_expired"
REASON_INCOMPLETE_IDENTITY = "incomplete_identity"
REASON_IV_UNRESOLVED = "iv_unresolved"
REASON_INVALID_PAYLOAD = "invalid_payload"
REASON_SOURCE_NOT_ALLOWED = "source_not_allowed"
REASON_RIGHTS_NOT_USABLE = "rights_not_usable"
REASON_UNDERLYING_NOT_DECLARED = "underlying_not_declared"

_CODE_SHA = f"module:vertex_core.calculations.options@{ENGINE_VERSION}"
_IV_QUOTE_SIDE = "MID"


def is_option_chain_schema(schema_version: str) -> bool:
    """``True`` when ``schema_version`` belongs to a declared chain family."""
    return isinstance(schema_version, str) and schema_version.startswith(
        OPTION_CHAIN_SCHEMA_PREFIXES
    )


@dataclass(frozen=True)
class OptionChainRecord:
    """ORM-free view of one persisted option-chain-slice observation."""

    event_id: str
    source: str
    instrument_ref: Optional[str]
    as_of: datetime
    quality_status: str
    rights: str
    schema_version: str
    payload: Mapping[str, Any]


def _is_synthetic(record: OptionChainRecord) -> bool:
    return record.rights == SYNTHETIC_RIGHTS or record.source == SYNTHETIC_SOURCE


@dataclass(frozen=True)
class OptionsConfig:
    """Declared inputs of the option-chain builder (owned upstream).

    ``underlyings`` is the declared universe: a chain slice for an undeclared
    underlying is rejected and counted, never silently added.
    ``max_quote_age`` is the staleness gate of the IV input: a quote older
    than this (relative to the evaluation clock) is ``STALE`` and never
    priced. ``max_chain_rows`` is the displayed row budget of one published
    chain.
    """

    underlyings: tuple[str, ...]
    allowed_sources: frozenset[str]
    usable_rights: frozenset[str]
    max_quote_age: timedelta = timedelta(hours=6)
    lookback: timedelta = timedelta(hours=72)
    max_observations: int = 200
    max_chain_rows: int = 240

    def __post_init__(self) -> None:
        if not self.underlyings:
            raise ValueError("underlyings: at least one underlying required")
        if self.max_quote_age <= timedelta(0):
            raise ValueError("max_quote_age: must be a positive duration")
        if self.lookback <= timedelta(0):
            raise ValueError("lookback: must be a positive duration")
        if not isinstance(self.max_observations, int) or self.max_observations < 1:
            raise ValueError("max_observations: must be an int >= 1")
        if not isinstance(self.max_chain_rows, int) or self.max_chain_rows < 1:
            raise ValueError("max_chain_rows: must be an int >= 1")


DEV_SYNTHETIC_OPTIONS_CONFIG = OptionsConfig(
    underlyings=SYNTHETIC_OPTION_UNDERLYINGS,
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)
"""Development-only registry: ONLY the synthetic source/rights and the 4
declared synthetic underlyings. Every snapshot it produces is population
``SYNTHETIC``."""


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def load_option_chain_records(
    session: Session, *, now: datetime, lookback: timedelta, limit: int
) -> list[OptionChainRecord]:
    """Load the bounded recent option-chain window, deterministically ordered."""
    filters = [
        Observation.schema_version.like(f"{prefix}%")
        for prefix in OPTION_CHAIN_SCHEMA_PREFIXES
    ]
    schema_filter = filters[0]
    for extra in filters[1:]:
        schema_filter = schema_filter | extra
    rows = (
        session.execute(
            select(Observation)
            .where(
                Observation.as_of <= now,
                Observation.as_of >= now - lookback,
                schema_filter,
            )
            .order_by(Observation.as_of.desc(), Observation.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        OptionChainRecord(
            event_id=row.event_id,
            source=row.source,
            instrument_ref=row.instrument_ref,
            as_of=row.as_of,
            quality_status=row.quality_status,
            rights=row.rights,
            schema_version=row.schema_version,
            payload=row.payload,
        )
        for row in rows
    ]


# --------------------------------------------------------------------------
# Pure content builder (no session, fully deterministic)
# --------------------------------------------------------------------------


def _num_string(value: float) -> str:
    """Render a float64 engine result as its exact decimal string."""
    return format(Decimal(repr(value)), "f")


def _calculation_meta(record: CalculationRecord) -> dict[str, Any]:
    """Lineage subset kept in the snapshot: version + hashes, no result blob."""
    return {
        "calculation_id": record.calculation_id,
        "engine_version": record.engine_version,
        "method": record.method,
        "input_hash": record.input_hash,
        "result_hash": record.result_hash,
        "status": record.status.value,
    }


def _optional_decimal(value: Any) -> Optional[Decimal]:
    """Parse a decimal string fail-closed; None stays None; junk is invalid."""
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("decimal string required")
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ValueError("finite decimal required")
    return parsed


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("integer required")
    return value


@dataclass(frozen=True)
class _SliceIdentity:
    expiration: date
    trading_class: str
    exchange: str
    style: str
    settlement: str
    multiplier: int
    currency: str


def _parse_slice_identity(payload: Mapping[str, Any]) -> Optional[_SliceIdentity]:
    """Parse the shared identity fields of a chain slice; None when invalid."""
    expiration = payload.get("expiration")
    trading_class = payload.get("trading_class")
    exchange = payload.get("exchange")
    style = payload.get("style")
    settlement = payload.get("settlement")
    multiplier = payload.get("multiplier")
    currency = payload.get("currency")
    if not all(
        isinstance(value, str) and value
        for value in (expiration, trading_class, exchange, style, settlement, currency)
    ):
        return None
    if isinstance(multiplier, bool) or not isinstance(multiplier, int) or multiplier <= 0:
        return None
    try:
        expiry = date.fromisoformat(expiration)  # type: ignore[arg-type]
    except ValueError:
        return None
    assert isinstance(trading_class, str) and isinstance(exchange, str)
    assert isinstance(style, str) and isinstance(settlement, str)
    assert isinstance(currency, str)
    return _SliceIdentity(
        expiration=expiry,
        trading_class=trading_class,
        exchange=exchange,
        style=style,
        settlement=settlement,
        multiplier=multiplier,
        currency=currency,
    )


def _quote_status(
    *,
    bid: Optional[Decimal],
    ask: Optional[Decimal],
    observed_at: Optional[datetime],
    now: datetime,
    max_quote_age: timedelta,
) -> str:
    if bid is None or ask is None:
        return QUOTE_STATUS_MISSING
    if bid >= ask:
        # A crossed OR unexplained locked quote is never a sane IV input.
        return QUOTE_STATUS_CROSSED
    if observed_at is None or now - observed_at > max_quote_age:
        return QUOTE_STATUS_STALE
    return QUOTE_STATUS_OK


_IV_REFUSAL_BY_QUOTE_STATUS = {
    QUOTE_STATUS_MISSING: REASON_QUOTE_MISSING,
    QUOTE_STATUS_CROSSED: REASON_QUOTE_CROSSED,
    QUOTE_STATUS_STALE: REASON_QUOTE_STALE,
}


def _build_contract_entry(
    raw: Mapping[str, Any],
    *,
    identity: _SliceIdentity,
    spot: Decimal,
    rate: Decimal,
    dividend_yield: Decimal,
    maturity_years: float,
    now: datetime,
    config: OptionsConfig,
    source_event_id: str,
    synthetic: bool,
) -> tuple[dict[str, Any], Optional[str]]:
    """Build one contract entry; returns (entry, discard_reason_or_None).

    The discard reason names why NO Vertex IV exists for the contract; the
    contract row itself stays published with its verbatim quote (a chain
    shows partial coverage honestly, it does not hide rows).
    """
    con_id = raw.get("con_id")
    strike_text = raw.get("strike")
    right = raw.get("right")
    identity_complete = (
        isinstance(con_id, int)
        and not isinstance(con_id, bool)
        and con_id > 0
        and isinstance(strike_text, str)
        and bool(strike_text)
        and right in ("CALL", "PUT")
    )
    strike: Optional[Decimal] = None
    if identity_complete:
        try:
            strike = _optional_decimal(strike_text)
        except (ValueError, InvalidOperation):
            identity_complete = False
    if strike is not None and strike <= 0:
        identity_complete = False

    try:
        bid = _optional_decimal(raw.get("bid"))
        ask = _optional_decimal(raw.get("ask"))
    except (ValueError, InvalidOperation):
        bid = ask = None
    observed_at: Optional[datetime] = None
    observed_text = raw.get("observed_at")
    if isinstance(observed_text, str):
        try:
            parsed = datetime.fromisoformat(observed_text)
        except ValueError:
            parsed = None
        if parsed is not None and parsed.tzinfo is not None:
            observed_at = parsed

    status = _quote_status(
        bid=bid,
        ask=ask,
        observed_at=observed_at,
        now=now,
        max_quote_age=config.max_quote_age,
    )

    entry: dict[str, Any] = {
        "con_id": con_id if isinstance(con_id, int) else None,
        "strike": strike_text if isinstance(strike_text, str) else None,
        "right": right if right in ("CALL", "PUT") else None,
        "expiration": identity.expiration.isoformat(),
        "trading_class": identity.trading_class,
        "multiplier": identity.multiplier,
        "currency": identity.currency,
        "exchange": identity.exchange,
        "style": identity.style,
        "settlement": identity.settlement,
        "quote": {
            "bid": raw.get("bid") if isinstance(raw.get("bid"), str) else None,
            "ask": raw.get("ask") if isinstance(raw.get("ask"), str) else None,
            "bid_size": raw.get("bid_size") if isinstance(raw.get("bid_size"), int) else None,
            "ask_size": raw.get("ask_size") if isinstance(raw.get("ask_size"), int) else None,
            "observed_at": observed_at.isoformat() if observed_at else None,
            "age_seconds": (
                int((now - observed_at).total_seconds()) if observed_at else None
            ),
            "status": status,
        },
        "volume": raw.get("volume") if isinstance(raw.get("volume"), int) else None,
        "open_interest": (
            raw.get("open_interest")
            if isinstance(raw.get("open_interest"), int)
            else None
        ),
        "open_interest_status": (
            raw.get("open_interest_status")
            if isinstance(raw.get("open_interest_status"), str)
            else None
        ),
        "synthetic": synthetic,
    }

    # ---- fail-closed calculation gates: identity, expiry, quote sanity ----
    reason: Optional[str] = None
    if not identity_complete:
        reason = REASON_INCOMPLETE_IDENTITY
    elif maturity_years <= 0.0:
        reason = REASON_CONTRACT_EXPIRED
    elif status != QUOTE_STATUS_OK:
        reason = _IV_REFUSAL_BY_QUOTE_STATUS[status]

    if reason is not None:
        entry["iv"] = {"status": "ABSENT", "reason": reason}
        entry["greeks"] = {"status": "ABSENT", "reason": REASON_IV_UNRESOLVED}
        return entry, reason

    assert strike is not None and bid is not None and ask is not None
    mid = (bid + ask) / 2
    try:
        iv_value = implied_volatility(
            mid,
            spot,
            strike,
            maturity_years,
            rate,
            dividend_yield,
            right,
            _IV_QUOTE_SIDE,
        )
    except (IVNoSolutionError, OptionInputError) as exc:
        # NEVER clamped, never guessed: the typed refusal reason is recorded.
        entry["iv"] = {"status": "ABSENT", "reason": exc.reason}
        entry["greeks"] = {"status": "ABSENT", "reason": REASON_IV_UNRESOLVED}
        return entry, exc.reason

    iv_record = make_calculation_record(
        calculation_id="options.implied_volatility",
        calculation_type="options",
        code_sha=_CODE_SHA,
        method="brentq bracketed BSM inversion on the quote MID",
        inputs={
            "observed_price": mid,
            "spot": spot,
            "strike": strike,
            "maturity_years": maturity_years,
            "rate": rate,
            "dividend_yield": dividend_yield,
            "right": right,
            "quote_side": _IV_QUOTE_SIDE,
        },
        result=iv_value,
        started_at=now,
        completed_at=now,
        source_event_ids=(source_event_id,),
        assumptions=(
            "flat synthetic rate and dividend yield",
            "ACT/365F maturity from the expiration date",
        ),
    )
    entry["iv"] = {
        "status": "OK",
        "value": _num_string(iv_value),
        "quote_side": _IV_QUOTE_SIDE,
        "value_nature": VALUE_NATURE_THEORETICAL,
        "calculation": _calculation_meta(iv_record),
    }

    try:
        greeks_result = greeks(
            spot, strike, maturity_years, rate, dividend_yield, iv_value, right
        )
    except OptionInputError as exc:  # pragma: no cover - resolved IV > 0
        entry["greeks"] = {"status": "ABSENT", "reason": exc.reason}
        return entry, None
    greeks_record = make_calculation_record(
        calculation_id="options.greeks",
        calculation_type="options",
        code_sha=_CODE_SHA,
        method="closed-form BSM sensitivities on the resolved Vertex IV",
        inputs={
            "spot": spot,
            "strike": strike,
            "maturity_years": maturity_years,
            "rate": rate,
            "dividend_yield": dividend_yield,
            "volatility": iv_value,
            "right": right,
        },
        result=greeks_result.model_dump(),
        started_at=now,
        completed_at=now,
        source_event_ids=(source_event_id,),
        assumptions=("greeks computed on the Vertex IV resolved from the MID",),
    )
    entry["greeks"] = {
        "status": "OK",
        "delta": _num_string(greeks_result.delta),
        "gamma": _num_string(greeks_result.gamma),
        "vega": _num_string(greeks_result.vega),
        "vega_per_point": _num_string(greeks_result.vega_per_point),
        "theta": _num_string(greeks_result.theta),
        "theta_per_calendar_day": _num_string(greeks_result.theta_per_calendar_day),
        "rho": _num_string(greeks_result.rho),
        "rho_per_bp": _num_string(greeks_result.rho_per_bp),
        "value_nature": VALUE_NATURE_THEORETICAL,
        "calculation": _calculation_meta(greeks_record),
    }
    return entry, None


def build_option_chain_content(
    records: Sequence[OptionChainRecord],
    *,
    underlying: str,
    now: datetime,
    config: OptionsConfig,
) -> dict[str, Any]:
    """Build the ``option_chain/{underlying}`` snapshot content.

    Pure and deterministic: identical ``records`` (in any order), ``now`` and
    ``config`` produce an identical dict. Every considered record is either
    used or rejected with a reason; every contract without a Vertex IV keeps
    its typed discard reason. No value is ever interpolated or defaulted.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    if underlying not in config.underlyings:
        raise ValueError(f"underlying {underlying!r} is not declared")

    rejected_records: list[dict[str, str]] = []
    by_group: dict[tuple[str, str], tuple[OptionChainRecord, _SliceIdentity]] = {}
    synthetic_count = 0
    considered = 0

    for record in sorted(records, key=lambda r: (r.as_of, r.event_id)):
        payload = record.payload
        payload_underlying = (
            payload.get("underlying") if isinstance(payload, Mapping) else None
        )
        if payload_underlying != underlying:
            continue  # another underlying's slice; counted by its own snapshot
        considered += 1
        if record.source not in config.allowed_sources:
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_SOURCE_NOT_ALLOWED}
            )
            continue
        if record.rights not in config.usable_rights:
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_RIGHTS_NOT_USABLE}
            )
            continue
        identity = _parse_slice_identity(payload)
        contracts = payload.get("contracts")
        spot_text = payload.get("underlying_spot")
        rate_text = payload.get("rate")
        q_text = payload.get("dividend_yield")
        try:
            spot = _optional_decimal(spot_text)
            rate = _optional_decimal(rate_text)
            dividend_yield = _optional_decimal(q_text)
        except (ValueError, InvalidOperation):
            spot = rate = dividend_yield = None
        if (
            identity is None
            or not isinstance(contracts, list)
            or spot is None
            or spot <= 0
            or rate is None
            or dividend_yield is None
        ):
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_INVALID_PAYLOAD}
            )
            continue
        if _is_synthetic(record):
            synthetic_count += 1
        # Latest record wins per (expiration, trading_class): records are
        # iterated in ascending (as_of, event_id) order.
        by_group[(identity.expiration.isoformat(), identity.trading_class)] = (
            record,
            identity,
        )

    expirations: list[dict[str, Any]] = []
    total_rows = 0
    published_rows = 0
    spot_block: Optional[dict[str, Any]] = None
    assumptions_block: Optional[dict[str, Any]] = None

    for group_key in sorted(by_group):
        record, identity = by_group[group_key]
        payload = record.payload
        spot = _optional_decimal(payload["underlying_spot"])
        rate = _optional_decimal(payload["rate"])
        dividend_yield = _optional_decimal(payload["dividend_yield"])
        assert spot is not None and rate is not None and dividend_yield is not None
        days_to_expiry = (identity.expiration - now.date()).days
        maturity_years = days_to_expiry / 365.0

        if spot_block is None:
            spot_block = {
                "value": payload["underlying_spot"],
                "currency": identity.currency,
                "observed_at": record.as_of.isoformat(),
                "source_event_id": record.event_id,
            }
            assumptions_block = {
                "rate": payload["rate"],
                "dividend_yield": payload["dividend_yield"],
                "quote_side_for_iv": _IV_QUOTE_SIDE,
                "max_quote_age_seconds": int(config.max_quote_age.total_seconds()),
            }

        entries: list[dict[str, Any]] = []
        discarded: list[dict[str, Any]] = []
        quotes_received = quotes_valid = iv_resolved = 0
        raw_contracts = payload["contracts"]
        for raw in raw_contracts:
            if not isinstance(raw, Mapping):
                discarded.append(
                    {
                        "con_id": None,
                        "strike": None,
                        "right": None,
                        "reason": REASON_INVALID_PAYLOAD,
                    }
                )
                continue
            entry, reason = _build_contract_entry(
                raw,
                identity=identity,
                spot=spot,
                rate=rate,
                dividend_yield=dividend_yield,
                maturity_years=maturity_years,
                now=now,
                config=config,
                source_event_id=record.event_id,
                synthetic=_is_synthetic(record),
            )
            entries.append(entry)
            if entry["quote"]["status"] != QUOTE_STATUS_MISSING:
                quotes_received += 1
            if entry["quote"]["status"] == QUOTE_STATUS_OK:
                quotes_valid += 1
            if entry["iv"]["status"] == "OK":
                iv_resolved += 1
            if reason is not None:
                discarded.append(
                    {
                        "con_id": entry["con_id"],
                        "strike": entry["strike"],
                        "right": entry["right"],
                        "reason": reason,
                    }
                )

        total_rows += len(entries)
        budget_left = config.max_chain_rows - published_rows
        published_entries = entries[: max(0, budget_left)]
        published_rows += len(published_entries)

        expirations.append(
            {
                "expiration": identity.expiration.isoformat(),
                "trading_class": identity.trading_class,
                "exchange": identity.exchange,
                "style": identity.style,
                "settlement": identity.settlement,
                "multiplier": identity.multiplier,
                "currency": identity.currency,
                "maturity_years": _num_string(maturity_years),
                "source_event_id": record.event_id,
                "quality": record.quality_status,
                "contracts": published_entries,
                "coverage": {
                    "expected": len(raw_contracts),
                    "quotes_received": quotes_received,
                    "quotes_valid": quotes_valid,
                    "iv_resolved": iv_resolved,
                    "discarded": discarded,
                },
            }
        )

    if considered == 0:
        population = "EMPTY"
    elif synthetic_count > 0:
        population = "SYNTHETIC"
    else:
        population = "REAL"

    return {
        "schema_version": OPTION_CHAIN_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "underlying": underlying,
        "engine_version": ENGINE_VERSION,
        "value_nature": VALUE_NATURE_THEORETICAL,
        "spot": spot_block,
        "assumptions": assumptions_block,
        "expirations": expirations,
        "row_budget": {
            "max_rows": config.max_chain_rows,
            "total_rows": total_rows,
            "published_rows": published_rows,
            "truncated_rows": total_rows - published_rows,
        },
        "coverage": {
            "observations_considered": considered,
            "groups_published": len(expirations),
            "rejected_records": rejected_records,
            "lookback_seconds": int(config.lookback.total_seconds()),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class OptionChainsHandler:
    """Handler of ``option_chains.ingested``: recompute per-underlying chains."""

    def __init__(self, *, config: OptionsConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local import avoids a module cycle (handlers imports this module).
        from vertex_worker.handlers import publish_if_changed

        now = self._clock()
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("clock returned a naive datetime; aware UTC required")
        records = load_option_chain_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )
        seen_underlyings = {
            record.payload.get("underlying")
            for record in records
            if isinstance(record.payload, Mapping)
        }
        for underlying in self._config.underlyings:
            if underlying not in seen_underlyings:
                # Never published an invented empty chain: absence stays
                # absent and the API answers its honest empty state.
                continue
            content = build_option_chain_content(
                records, underlying=underlying, now=now, config=self._config
            )
            published = publish_if_changed(
                session,
                kind=SNAPSHOT_KIND_OPTION_CHAIN,
                key=underlying,
                content=content,
                as_of=now,
            )
            if published is None:
                log.info(
                    "option chain %s unchanged (message_id=%s)",
                    underlying,
                    message.id,
                )
            else:
                log.info(
                    "option chain %s published version=%s (message_id=%s)",
                    underlying,
                    published.version,
                    message.id,
                )


def register_options_handler(
    registry: HandlerRegistry, *, clock: Clock, config: OptionsConfig
) -> None:
    """Register the option-chain handler on ``option_chains.ingested``."""
    registry.register(
        TOPIC_OPTION_CHAINS_INGESTED, OptionChainsHandler(config=config, clock=clock)
    )
