"""Entitlement probe: exact error mapping, timeouts, TTL, per-field 10090,
single active probe, delayed fallback, immutability."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from fakes import (
    T0,
    FakeInformationPort,
    SteppingMonotonic,
    fixed_clock,
    full_greeks,
    full_quote,
    make_envelope,
    make_snapshot_result,
)
from pydantic import ValidationError

from vertex_core.contracts import DelayStatus, SourceCapabilityStatus
from vertex_edge_ibkr.port import (
    CancellationOutcome,
    ContractSpec,
    MarketDataSnapshotResult,
    OperationToken,
    ProviderError,
    ProviderErrorInfo,
)
from vertex_edge_ibkr.probe import (
    CHAIN_CAPABILITY,
    OPTION_GREEKS_DELAYED,
    OPTION_GREEKS_LIVE,
    OPTION_TOP,
    UNDERLYING_TOP,
    EntitlementProbe,
    ProbeAlreadyActiveError,
    ProbeConfig,
    ProbeGate,
    ProbeSessionCompromisedError,
    map_provider_error,
)

_STATUS = SourceCapabilityStatus

UNDERLYING = ContractSpec(sec_type="STK", con_id=1001, symbol="SYN")
OPTION = ContractSpec(
    sec_type="OPT",
    con_id=2002,
    symbol="SYN",
    trading_class="SYN1",
    strike=Decimal("100"),
    right="C",
    last_trade_date="20261218",
)


def make_config(**overrides) -> ProbeConfig:
    values = {
        "underlying": UNDERLYING,
        "option": OPTION,
        "step_timeout_seconds": 1.0,
        "total_deadline_seconds": 5.0,
    }
    values.update(overrides)
    return ProbeConfig(**values)


def happy_port() -> FakeInformationPort:
    return FakeInformationPort(
        snapshot_behaviors={
            (1001, 1): make_snapshot_result(
                (make_envelope(full_quote(1001, with_generics=True), con_id=1001),)
            ),
            (2002, 1): make_snapshot_result(
                (
                    make_envelope(full_quote(2002), con_id=2002),
                    make_envelope(full_greeks(2002, tick_type=13), con_id=2002),
                )
            ),
        }
    )


def make_probe(
    port,
    config=None,
    *,
    gate=None,
    monotonic=None,
    epoch_provider=None,
) -> EntitlementProbe:
    return EntitlementProbe(
        port,
        config if config is not None else make_config(),
        gate=gate if gate is not None else ProbeGate(),
        clock=fixed_clock(),
        monotonic=monotonic if monotonic is not None else SteppingMonotonic(),
        epoch_provider=epoch_provider if epoch_provider is not None else lambda: 1,
        probe_id_factory=lambda: "probe-synthetic-1",
    )


def run(probe: EntitlementProbe):
    return asyncio.run(probe.run())


class ScriptedCancellationPort(FakeInformationPort):
    """Probe fake that mirrors the adapter's quarantined-line contract."""

    def __init__(
        self,
        initial_outcome: CancellationOutcome,
        retry_outcome: CancellationOutcome | BaseException,
    ) -> None:
        underlying_result = make_snapshot_result(
            (make_envelope(full_quote(1001, with_generics=True), con_id=1001),)
        )
        super().__init__(
            snapshot_behaviors={
                (1001, 1): replace(
                    underlying_result,
                    cancellation_outcome=initial_outcome,
                ),
                (2002, 1): make_snapshot_result(
                    (
                        make_envelope(full_quote(2002), con_id=2002),
                        make_envelope(full_greeks(2002, tick_type=13), con_id=2002),
                    )
                ),
            }
        )
        self._retry_outcome = retry_outcome
        self._pending_subscription_count = 0

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> MarketDataSnapshotResult:
        result = await super().market_data_snapshot(
            spec,
            generic_ticks=generic_ticks,
            market_data_type=market_data_type,
            timeout_seconds=timeout_seconds,
        )
        if result.cancellation_outcome is not CancellationOutcome.CANCELLED:
            self._pending_subscription_count = 1
        return result

    async def cancel_subscription(
        self, subscription_id: str
    ) -> CancellationOutcome:
        self.cancelled_subscriptions.append(subscription_id)
        if isinstance(self._retry_outcome, BaseException):
            raise self._retry_outcome
        if self._retry_outcome is CancellationOutcome.CANCELLED:
            self._pending_subscription_count = 0
        return self._retry_outcome

    @property
    def pending_subscription_count(self) -> int:
        return self._pending_subscription_count


class PrimaryFailureWithQuarantinedLinePort(FakeInformationPort):
    """A provider call that kept its primary error and its uncertain line."""

    def __init__(self, primary: BaseException) -> None:
        super().__init__()
        self._primary = primary
        self._pending_subscription_count = 0

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> MarketDataSnapshotResult:
        self.snapshot_calls.append(
            (
                spec.con_id,
                market_data_type,
                generic_ticks,
            )
        )
        self._pending_subscription_count = 1
        raise self._primary

    @property
    def pending_subscription_count(self) -> int:
        return self._pending_subscription_count


class HangingCancellationPort(ScriptedCancellationPort):
    """Cancellation retry that never completes inside the bounded step."""

    async def cancel_subscription(
        self, subscription_id: str
    ) -> CancellationOutcome:
        self.cancelled_subscriptions.append(subscription_id)
        await asyncio.sleep(60)
        return CancellationOutcome.CANCELLED


# -- exact error mapping ----------------------------------------------------


@pytest.mark.parametrize(
    ("code", "status", "reason", "per_field"),
    [
        (100, _STATUS.ERROR, "MESSAGE_RATE_EXCEEDED", False),
        (101, _STATUS.ERROR, "MARKET_DATA_LINES_EXHAUSTED", False),
        (354, _STATUS.NOT_ENTITLED, "LIVE_MARKET_DATA_NOT_SUBSCRIBED", False),
        (10090, _STATUS.NOT_ENTITLED, "PARTIAL_MARKET_DATA_SUBSCRIPTION", True),
        (10186, _STATUS.NOT_ENTITLED, "LIVE_NOT_SUBSCRIBED_DELAYED_NOT_ENABLED", False),
        (10197, _STATUS.ERROR, "COMPETING_SESSION", False),
    ],
)
def test_manifest_error_mapping_is_exact(code, status, reason, per_field) -> None:
    mapping = map_provider_error(code)
    assert mapping.status is status
    assert mapping.reason_code == reason
    assert mapping.per_field is per_field


def test_unknown_code_is_error_never_not_entitled() -> None:
    mapping = map_provider_error(1234)
    assert mapping.status is _STATUS.ERROR
    assert mapping.reason_code == "UNMAPPED_PROVIDER_ERROR_1234"


@pytest.mark.parametrize(
    ("code", "status", "reason"),
    [
        (100, _STATUS.ERROR, "MESSAGE_RATE_EXCEEDED"),
        (101, _STATUS.ERROR, "MARKET_DATA_LINES_EXHAUSTED"),
        (354, _STATUS.NOT_ENTITLED, "LIVE_MARKET_DATA_NOT_SUBSCRIBED"),
        (10186, _STATUS.NOT_ENTITLED, "LIVE_NOT_SUBSCRIBED_DELAYED_NOT_ENABLED"),
        (10197, _STATUS.ERROR, "COMPETING_SESSION"),
    ],
)
def test_option_step_provider_error_maps_to_exact_status(code, status, reason) -> None:
    port = happy_port()
    port.snapshot_behaviors[(2002, 1)] = ProviderError(code, "synthetic refusal")
    snapshot = run(make_probe(port))
    evidence = snapshot.field_evidence(OPTION_TOP, "bid")
    assert evidence is not None
    assert evidence.status is status
    assert evidence.reason_code == reason
    assert evidence.provider_error_code == code
    # The underlying step stays independently AVAILABLE.
    assert snapshot.status_of(UNDERLYING_TOP, "bid") is _STATUS.AVAILABLE


def test_error_wins_over_not_entitled_for_unobserved_fields() -> None:
    port = happy_port()
    port.snapshot_behaviors[(2002, 1)] = make_snapshot_result(
        (),
        errors=(
            ProviderErrorInfo(code=10197, message="synthetic"),
            ProviderErrorInfo(code=354, message="synthetic"),
        ),
    )
    snapshot = run(make_probe(port))
    for field in ("bid", "ask", "last", "volume"):
        evidence = snapshot.field_evidence(OPTION_TOP, field)
        assert evidence.status is _STATUS.ERROR  # never converted to NOT_ENTITLED
        assert evidence.reason_code == "COMPETING_SESSION"


def test_10090_is_applied_per_field_not_globally() -> None:
    port = happy_port()
    port.snapshot_behaviors[(2002, 1)] = make_snapshot_result(
        (make_envelope(full_quote(2002), con_id=2002),),
        errors=(ProviderErrorInfo(code=10090, message="synthetic partial"),),
    )
    snapshot = run(make_probe(port))
    # Observed quote fields stay positive evidence.
    for field in ("bid", "ask", "last", "volume"):
        assert snapshot.status_of(OPTION_TOP, field) is _STATUS.AVAILABLE
    # Missing greeks are NOT_ENTITLED per field, with the manifest reason.
    for field in ("implied_volatility", "delta", "gamma", "vega", "theta"):
        evidence = snapshot.field_evidence(OPTION_GREEKS_LIVE, field)
        assert evidence.status is _STATUS.NOT_ENTITLED
        assert evidence.reason_code == "PARTIAL_MARKET_DATA_SUBSCRIPTION"
        assert evidence.provider_error_code == 10090


# -- happy path -------------------------------------------------------------


def test_happy_path_publishes_available_per_field_with_epoch() -> None:
    snapshot = run(make_probe(happy_port()))
    assert snapshot.probe_id == "probe-synthetic-1"
    assert snapshot.source == "ibkr"
    assert snapshot.connection_epoch == 1
    assert snapshot.status_of(CHAIN_CAPABILITY, "definition") is _STATUS.AVAILABLE
    for field in ("bid", "ask", "last", "volume"):
        assert snapshot.status_of(UNDERLYING_TOP, field) is _STATUS.AVAILABLE
        assert snapshot.status_of(OPTION_TOP, field) is _STATUS.AVAILABLE
    for field in ("implied_volatility", "delta", "gamma", "vega", "theta"):
        evidence = snapshot.field_evidence(OPTION_GREEKS_LIVE, field)
        assert evidence.status is _STATUS.AVAILABLE
        assert evidence.tick_type == 13  # model computation proved it


def test_un_resultat_qui_melange_deux_epochs_interrompt_la_sonde() -> None:
    """Une matrice ne peut jamais agréger quote et greeks de sessions différentes."""
    port = happy_port()
    port.snapshot_behaviors[(2002, 1)] = make_snapshot_result(
        (
            make_envelope(full_quote(2002), con_id=2002, epoch=1),
            make_envelope(full_greeks(2002, tick_type=13), con_id=2002, epoch=2),
        )
    )

    with pytest.raises(ProbeSessionCompromisedError, match="mixes connection epochs"):
        run(make_probe(port))

    assert [call[0] for call in port.snapshot_calls] == [1001, 2002]


def test_un_token_operation_d_un_autre_epoch_interrompt_la_sonde() -> None:
    """L'enveloppe correcte ne peut pas blanchir un token d'une autre session."""
    port = happy_port()
    port.snapshot_behaviors[(1001, 1)] = make_snapshot_result(
        (make_envelope(full_quote(1001, with_generics=True), con_id=1001),),
        operation=OperationToken(
            journal_id="journal-autre-epoch",
            connection_epoch_at_start=2,
            provider_sequence_at_start=0,
            market_update_sequence_at_start=0,
        ),
    )

    with pytest.raises(ProbeSessionCompromisedError, match="operation belongs"):
        run(make_probe(port))

    assert [call[0] for call in port.snapshot_calls] == [1001]


def test_un_changement_epoch_entre_deux_etapes_interrompt_la_sonde() -> None:
    """L'epoch capturé au préambule reste l'unique epoch publiable."""

    class MutableEpoch:
        value = 1

        def __call__(self) -> int:
            return self.value

    epoch = MutableEpoch()

    class EpochChangingPort(FakeInformationPort):
        async def sec_def_opt_params(self, underlying):
            result = await super().sec_def_opt_params(underlying)
            epoch.value = 2
            return result

    port = EpochChangingPort(
        snapshot_behaviors=happy_port().snapshot_behaviors,
    )

    with pytest.raises(ProbeSessionCompromisedError, match="epoch changed"):
        run(make_probe(port, epoch_provider=epoch))

    assert port.snapshot_calls == []


@pytest.mark.parametrize("epoch", [0, -1, True])
def test_sonde_refuse_un_epoch_non_connecte(epoch: int) -> None:
    with pytest.raises(ProbeSessionCompromisedError, match="positive connected-session"):
        run(make_probe(happy_port(), epoch_provider=lambda: epoch))


def test_generic_tick_fields_carry_their_manifest_tick_ids() -> None:
    snapshot = run(make_probe(happy_port()))
    expectations = {
        ("underlying_call_put_option_volume", "call_volume"): 29,
        ("underlying_call_put_option_volume", "put_volume"): 30,
        ("option_open_interest", "call_open_interest"): 27,
        ("option_open_interest", "put_open_interest"): 28,
        ("underlying_historical_volatility_30d", "historical_volatility_30d"): 23,
        ("underlying_average_option_volume", "average_option_volume"): 87,
        ("underlying_option_implied_volatility_30d", "option_implied_volatility_30d"): 24,
    }
    for (capability, field), tick in expectations.items():
        evidence = snapshot.field_evidence(capability, field)
        assert evidence is not None
        assert evidence.status is _STATUS.AVAILABLE
        assert evidence.tick_type == tick


def test_underlying_step_requests_the_manifest_generic_ticks() -> None:
    port = happy_port()
    run(make_probe(port))
    underlying_calls = [c for c in port.snapshot_calls if c[0] == 1001]
    assert underlying_calls == [(1001, 1, (100, 101, 104, 105, 106))]


# -- cancellation proof -----------------------------------------------------


@pytest.mark.parametrize(
    ("stage", "code"),
    [("preflight", 502), ("chain", 1100), ("snapshot", 1102)],
)
def test_un_statut_de_session_leve_ne_devient_jamais_une_matrice(
    stage: str,
    code: int,
) -> None:
    """Un code global exige une nouvelle session, pas des champs `ERROR`."""
    error = ProviderError(code, "synthetic provider status")
    kwargs: dict[str, object] = {}
    if stage == "preflight":
        kwargs["server_time_behavior"] = error
    elif stage == "chain":
        kwargs["chain_behavior"] = error
    else:
        kwargs["snapshot_behaviors"] = {(1001, 1): error}
    port = FakeInformationPort(**kwargs)

    with pytest.raises(ProviderError) as caught:
        run(make_probe(port))

    assert caught.value is error


def test_false_then_true_cancellation_retries_once_before_continuing() -> None:
    port = ScriptedCancellationPort(
        CancellationOutcome.NOT_FOUND,
        CancellationOutcome.CANCELLED,
    )

    snapshot = run(make_probe(port))

    assert snapshot.status_of(UNDERLYING_TOP, "bid") is _STATUS.AVAILABLE
    assert snapshot.status_of(OPTION_TOP, "bid") is _STATUS.AVAILABLE
    assert port.cancelled_subscriptions == ["sub-1"]
    assert [call[0] for call in port.snapshot_calls] == [1001, 2002]
    assert port.pending_subscription_count == 0


def test_preexisting_quarantined_line_blocks_request_and_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = ScriptedCancellationPort(
        CancellationOutcome.CANCELLED,
        CancellationOutcome.CANCELLED,
    )
    port._pending_subscription_count = 1
    probe = make_probe(port)
    published: list[object] = []
    monkeypatch.setattr(
        probe,
        "_publish",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )

    with pytest.raises(ProbeSessionCompromisedError, match="already has unresolved"):
        run(probe)

    assert port.snapshot_calls == []
    assert port.cancelled_subscriptions == []
    assert published == []


def test_preexisting_quarantined_line_blocks_even_a_preflight_failure_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = ScriptedCancellationPort(
        CancellationOutcome.CANCELLED,
        CancellationOutcome.CANCELLED,
    )
    port._pending_subscription_count = 1
    port.server_time_behavior = ProviderError(10197, "synthetic preflight failure")
    probe = make_probe(port)
    published: list[object] = []
    monkeypatch.setattr(
        probe,
        "_publish",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )

    with pytest.raises(ProbeSessionCompromisedError, match="already has unresolved"):
        run(probe)

    assert port.snapshot_calls == []
    assert port.cancelled_subscriptions == []
    assert published == []


def test_false_then_false_cancellation_aborts_before_publish_or_next_instrument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = ScriptedCancellationPort(
        CancellationOutcome.NOT_FOUND,
        CancellationOutcome.NOT_FOUND,
    )
    probe = make_probe(port)
    published: list[object] = []
    monkeypatch.setattr(
        probe,
        "_publish",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )

    with pytest.raises(ProbeSessionCompromisedError, match="not confirmed"):
        run(probe)

    assert port.cancelled_subscriptions == ["sub-1"]
    assert [call[0] for call in port.snapshot_calls] == [1001]
    assert port.pending_subscription_count == 1
    assert published == []


def test_cancellation_exception_then_true_retries_once_before_continuing() -> None:
    port = ScriptedCancellationPort(
        CancellationOutcome.FAILED,
        CancellationOutcome.CANCELLED,
    )

    snapshot = run(make_probe(port))

    assert snapshot.status_of(OPTION_TOP, "bid") is _STATUS.AVAILABLE
    assert port.cancelled_subscriptions == ["sub-1"]
    assert [call[0] for call in port.snapshot_calls] == [1001, 2002]
    assert port.pending_subscription_count == 0


def test_two_cancellation_exceptions_abort_after_exactly_one_retry() -> None:
    port = ScriptedCancellationPort(
        CancellationOutcome.FAILED,
        CancellationOutcome.FAILED,
    )

    with pytest.raises(ProbeSessionCompromisedError, match="FAILED"):
        run(make_probe(port))

    assert port.cancelled_subscriptions == ["sub-1"]
    assert [call[0] for call in port.snapshot_calls] == [1001]
    assert port.pending_subscription_count == 1


def test_session_closed_is_never_retried_or_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = ScriptedCancellationPort(
        CancellationOutcome.SESSION_CLOSED,
        CancellationOutcome.CANCELLED,
    )
    probe = make_probe(port)
    published: list[object] = []
    monkeypatch.setattr(
        probe,
        "_publish",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )

    with pytest.raises(ProbeSessionCompromisedError, match="session closed"):
        run(probe)

    assert port.cancelled_subscriptions == []
    assert [call[0] for call in port.snapshot_calls] == [1001]
    assert published == []


def test_ordinary_retry_exception_is_preserved_and_blocks_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retry_error = RuntimeError("synthetic ordinary retry failure")
    port = ScriptedCancellationPort(CancellationOutcome.NOT_FOUND, retry_error)
    probe = make_probe(port)
    published: list[object] = []
    monkeypatch.setattr(
        probe,
        "_publish",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )

    with pytest.raises(RuntimeError) as caught:
        run(probe)

    assert caught.value is retry_error
    assert port.cancelled_subscriptions == ["sub-1"]
    assert [call[0] for call in port.snapshot_calls] == [1001]
    assert port.pending_subscription_count == 1
    assert published == []


def test_hanging_cancellation_retry_is_bounded_and_blocks_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = HangingCancellationPort(
        CancellationOutcome.NOT_FOUND,
        CancellationOutcome.CANCELLED,
    )
    probe = make_probe(port, make_config(step_timeout_seconds=0.01))
    published: list[object] = []
    monkeypatch.setattr(
        probe,
        "_publish",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )

    with pytest.raises(ProbeSessionCompromisedError, match="retry timed out"):
        run(probe)

    assert port.cancelled_subscriptions == ["sub-1"]
    assert [call[0] for call in port.snapshot_calls] == [1001]
    assert port.pending_subscription_count == 1
    assert published == []


def test_retry_cancelled_error_is_preserved_and_stops_the_probe() -> None:
    cancelled = asyncio.CancelledError("synthetic cancellation")
    port = ScriptedCancellationPort(CancellationOutcome.FAILED, cancelled)

    with pytest.raises(asyncio.CancelledError) as caught:
        run(make_probe(port))

    assert caught.value is cancelled
    assert port.cancelled_subscriptions == ["sub-1"]
    assert [call[0] for call in port.snapshot_calls] == [1001]


def test_primary_provider_error_is_preserved_when_its_line_is_quarantined() -> None:
    primary = ProviderError(10197, "synthetic primary")
    port = PrimaryFailureWithQuarantinedLinePort(primary)

    with pytest.raises(ProviderError) as caught:
        run(make_probe(port))

    assert caught.value is primary
    assert [call[0] for call in port.snapshot_calls] == [1001]


def test_primary_cancelled_error_is_preserved_and_stops_the_probe() -> None:
    primary = asyncio.CancelledError("synthetic primary cancellation")
    port = PrimaryFailureWithQuarantinedLinePort(primary)

    with pytest.raises(asyncio.CancelledError) as caught:
        run(make_probe(port))

    assert caught.value is primary
    assert [call[0] for call in port.snapshot_calls] == [1001]


def test_primary_timeout_is_preserved_when_its_line_is_quarantined() -> None:
    primary = TimeoutError("synthetic primary timeout")
    port = PrimaryFailureWithQuarantinedLinePort(primary)

    with pytest.raises(TimeoutError) as caught:
        run(make_probe(port))

    assert caught.value is primary
    assert [call[0] for call in port.snapshot_calls] == [1001]


# -- timeouts and deadline --------------------------------------------------


def test_step_timeout_yields_error_step_timeout_never_not_entitled() -> None:
    port = happy_port()
    port.snapshot_behaviors[(1001, 1)] = ("hang", 5.0)
    config = make_config(step_timeout_seconds=0.05)
    snapshot = run(make_probe(port, config))
    for field in ("bid", "ask", "last", "volume"):
        evidence = snapshot.field_evidence(UNDERLYING_TOP, field)
        assert evidence.status is _STATUS.ERROR
        assert evidence.reason_code == "STEP_TIMEOUT"
    # The option step still ran afterwards.
    assert snapshot.status_of(OPTION_TOP, "bid") is _STATUS.AVAILABLE


def test_preflight_timeout_publishes_error_for_every_planned_field() -> None:
    port = happy_port()
    port.server_time_behavior = ("hang", 5.0)
    config = make_config(step_timeout_seconds=0.05)
    snapshot = run(make_probe(port, config))
    assert snapshot.fields  # everything planned is published
    for evidence in snapshot.fields:
        assert evidence.status is _STATUS.ERROR
        assert evidence.reason_code == "STEP_TIMEOUT"


def test_preflight_provider_refusal_never_becomes_not_entitled() -> None:
    port = happy_port()
    port.server_time_behavior = ProviderError(354, "synthetic")
    snapshot = run(make_probe(port))
    for evidence in snapshot.fields:
        assert evidence.status is _STATUS.ERROR
        assert evidence.reason_code == "PREFLIGHT_FAILED"


def test_total_deadline_marks_remaining_fields_deadline_exceeded() -> None:
    port = happy_port()
    # Each monotonic() call advances 6s; total deadline is 10s, so the chain
    # step (second _bounded call) finds the budget consumed.
    monotonic = SteppingMonotonic(start=0.0, step=6.0)
    config = make_config(total_deadline_seconds=10.0)
    snapshot = run(make_probe(port, config, monotonic=monotonic))
    assert snapshot.field_evidence(CHAIN_CAPABILITY, "definition").reason_code == (
        "PROBE_DEADLINE_EXCEEDED"
    )
    for field in ("bid", "ask", "last", "volume"):
        evidence = snapshot.field_evidence(OPTION_TOP, field)
        assert evidence.status is _STATUS.ERROR
        assert evidence.reason_code == "PROBE_DEADLINE_EXCEEDED"


# -- TTL --------------------------------------------------------------------


def test_result_ttl_defaults_to_21600_seconds() -> None:
    snapshot = run(make_probe(happy_port()))
    assert snapshot.expires_at - snapshot.tested_at == timedelta(seconds=21600)
    assert snapshot.is_valid_at(snapshot.tested_at + timedelta(seconds=21599)) is True
    assert snapshot.is_valid_at(snapshot.tested_at + timedelta(seconds=21601)) is False


def test_ttl_is_injectable_and_naive_now_is_rejected() -> None:
    config = make_config(result_ttl_seconds=60.0)
    snapshot = run(make_probe(happy_port(), config))
    assert snapshot.expires_at - snapshot.tested_at == timedelta(seconds=60)
    with pytest.raises(ValueError):
        snapshot.is_valid_at(T0.replace(tzinfo=None))


# -- single active probe ----------------------------------------------------


def test_only_one_probe_active_at_a_time() -> None:
    async def scenario() -> None:
        gate = ProbeGate()
        slow_port = happy_port()
        slow_port.server_time_behavior = ("slow", 0.2, T0)
        probe_one = make_probe(slow_port, gate=gate)
        probe_two = make_probe(happy_port(), gate=gate)
        task = asyncio.create_task(probe_one.run())
        await asyncio.sleep(0.05)
        with pytest.raises(ProbeAlreadyActiveError):
            await probe_two.run()
        first = await task
        assert first.probe_id == "probe-synthetic-1"
        # The gate is released after completion: a new probe may run.
        second = await probe_two.run()
        assert second.fields

    asyncio.run(scenario())


def test_gate_is_released_even_when_a_step_fails() -> None:
    gate = ProbeGate()
    port = happy_port()
    port.server_time_behavior = ProviderError(10197, "synthetic")
    run(make_probe(port, gate=gate))
    assert gate.active_probe_id is None


# -- delayed fallback -------------------------------------------------------


def _delayed_port() -> FakeInformationPort:
    port = happy_port()
    port.snapshot_behaviors[(2002, 1)] = ProviderError(354, "synthetic live refusal")
    port.snapshot_behaviors[(2002, 3)] = make_snapshot_result(
        (
            make_envelope(
                full_quote(2002, market_data_type=3),
                con_id=2002,
                delay=DelayStatus.DELAYED,
            ),
            make_envelope(
                full_greeks(2002, tick_type=83, market_data_type=3),
                con_id=2002,
                delay=DelayStatus.DELAYED,
            ),
        ),
        requested=3,
        reported=3,
    )
    return port


def test_delayed_fallback_records_delayed_never_available() -> None:
    config = make_config(allow_delayed_fallback=True)
    snapshot = run(make_probe(_delayed_port(), config))
    # Live refusal stays a live NOT_ENTITLED proof.
    assert snapshot.status_of(OPTION_TOP, "bid") is _STATUS.NOT_ENTITLED
    for field in ("implied_volatility", "delta", "gamma", "vega", "theta"):
        evidence = snapshot.field_evidence(OPTION_GREEKS_DELAYED, field)
        assert evidence is not None
        assert evidence.status is _STATUS.DELAYED  # never AVAILABLE, never live
        assert evidence.tick_type == 83  # delayed computation tick, not 13
        assert evidence.market_data_type == 3


def test_delayed_fallback_requires_local_opt_in() -> None:
    port = _delayed_port()
    snapshot = run(make_probe(port, make_config(allow_delayed_fallback=False)))
    assert all(e.capability_id != OPTION_GREEKS_DELAYED for e in snapshot.fields)
    assert all(call != (2002, 3, ()) for call in port.snapshot_calls)


# -- construction and immutability ------------------------------------------


def test_probe_config_requires_exact_contracts() -> None:
    with pytest.raises(ValueError):
        make_config(underlying=ContractSpec(sec_type="STK", symbol="SYN"))
    with pytest.raises(ValueError):
        make_config(option=ContractSpec(sec_type="OPT", con_id=2002))  # no trading class
    with pytest.raises(ValueError):
        make_config(max_concurrent_lines=0)


def test_snapshot_is_immutable_per_field() -> None:
    snapshot = run(make_probe(happy_port()))
    with pytest.raises(ValidationError):
        snapshot.probe_id = "rewritten"
    evidence = snapshot.fields[0]
    with pytest.raises(ValidationError):
        evidence.status = _STATUS.AVAILABLE
