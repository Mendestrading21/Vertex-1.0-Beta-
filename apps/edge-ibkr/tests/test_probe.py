"""Entitlement probe: exact error mapping, timeouts, TTL, per-field 10090,
single active probe, delayed fallback, immutability."""

from __future__ import annotations

import asyncio
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
from vertex_edge_ibkr.port import ContractSpec, ProviderError, ProviderErrorInfo
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


def make_probe(port, config=None, *, gate=None, monotonic=None) -> EntitlementProbe:
    return EntitlementProbe(
        port,
        config if config is not None else make_config(),
        gate=gate if gate is not None else ProbeGate(),
        clock=fixed_clock(),
        monotonic=monotonic if monotonic is not None else SteppingMonotonic(),
        epoch_provider=lambda: 5,
        probe_id_factory=lambda: "probe-synthetic-1",
    )


def run(probe: EntitlementProbe):
    return asyncio.run(probe.run())


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
    assert snapshot.connection_epoch == 5
    assert snapshot.status_of(CHAIN_CAPABILITY, "definition") is _STATUS.AVAILABLE
    for field in ("bid", "ask", "last", "volume"):
        assert snapshot.status_of(UNDERLYING_TOP, field) is _STATUS.AVAILABLE
        assert snapshot.status_of(OPTION_TOP, field) is _STATUS.AVAILABLE
    for field in ("implied_volatility", "delta", "gamma", "vega", "theta"):
        evidence = snapshot.field_evidence(OPTION_GREEKS_LIVE, field)
        assert evidence.status is _STATUS.AVAILABLE
        assert evidence.tick_type == 13  # model computation proved it


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
