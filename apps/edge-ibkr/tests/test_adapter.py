"""Adapter: read-only loopback session, sentinel handling, delayed greeks."""

from __future__ import annotations

import asyncio
import random
from decimal import Decimal

import pytest

from vertex_core.contracts import DelayStatus, EnvelopeQuality

from vertex_edge_ibkr.adapter import (
    DEFAULT_CLIENT_ID,
    LOOPBACK_HOST,
    IbAsyncInformationAdapter,
)
from vertex_edge_ibkr.port import (
    ContractSpec,
    GreeksObservation,
    QuoteObservation,
    ScannerDefinition,
)
from vertex_edge_ibkr.state import ConnectionStateMachine

from fakes import NAN, FakeComputation, FakeIB, FakeTicker, T1, fixed_clock, instant_sleep

STOCK = ContractSpec(sec_type="STK", con_id=1001, symbol="SYN", exchange="SMART", currency="USD")
OPTION = ContractSpec(
    sec_type="OPT",
    con_id=2002,
    symbol="SYN",
    trading_class="SYN1",
    strike=Decimal("100"),
    right="C",
    last_trade_date="20261218",
)


def make_adapter(fake: FakeIB, **overrides) -> IbAsyncInformationAdapter:
    values = dict(
        ib=fake,
        clock=fixed_clock(T1),
        sleep=instant_sleep,
        snapshot_timeout_seconds=0.2,
        snapshot_poll_seconds=0.1,
        event_id_factory=iter(f"evt-{i}" for i in range(1000)).__next__,
    )
    values.update(overrides)
    return IbAsyncInformationAdapter(**values)


def snapshot(adapter: IbAsyncInformationAdapter, spec: ContractSpec, **kwargs):
    return asyncio.run(adapter.market_data_snapshot(spec, **kwargs))


# -- construction refusals --------------------------------------------------


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "localhost", "example.com", ""])
def test_non_loopback_host_is_refused(host: str) -> None:
    with pytest.raises(ValueError):
        make_adapter(FakeIB(), host=host)


@pytest.mark.parametrize("client_id", [0, -1, -71, True, False])
def test_client_id_must_be_a_nonzero_positive_integer(client_id) -> None:
    with pytest.raises(ValueError):
        make_adapter(FakeIB(), client_id=client_id)


def test_default_client_id_is_71_and_loopback() -> None:
    adapter = make_adapter(FakeIB())
    assert DEFAULT_CLIENT_ID == 71
    assert LOOPBACK_HOST == "127.0.0.1"
    assert adapter is not None


# -- connect: readonly always transmitted -----------------------------------


def test_connect_transmits_readonly_true_and_loopback_and_client_id() -> None:
    fake = FakeIB()
    adapter = make_adapter(fake)
    asyncio.run(adapter.connect())
    assert len(fake.connect_calls) == 1
    call = fake.connect_calls[0]
    assert call["readonly"] is True  # ALWAYS read-only, no exception
    assert call["host"] == "127.0.0.1"
    assert call["clientId"] == 71
    # Empty startup fetch mask: no account-scoped startup requests at all.
    assert getattr(call["fetchFields"], "value", call["fetchFields"]) == 0


def test_connect_drives_the_state_machine_epoch() -> None:
    fake = FakeIB()
    state = ConnectionStateMachine(rng=random.Random(1))
    adapter = make_adapter(fake, state=state)
    asyncio.run(adapter.connect())
    assert state.connection_epoch == 1
    result = snapshot(adapter, STOCK)
    assert result.envelopes[0].connection_epoch == 1


# -- sentinels: -1/NaN stay None, never zero --------------------------------


def test_sentinel_minus_one_and_nan_become_none_never_zero() -> None:
    ticker = FakeTicker(bid=-1.0, bidSize=NAN, ask=101.5, askSize=3.0, last=NAN, volume=-1.0, close=4.2)
    result = snapshot(make_adapter(FakeIB(ticker=ticker)), STOCK)
    quote = result.quote()
    assert quote is not None
    assert quote.bid is None  # -1 sentinel is absence, never Decimal("0")
    assert quote.bid_size is None
    assert quote.last is None
    assert quote.volume is None
    assert quote.ask == Decimal("101.5")
    assert quote.close == Decimal("4.2")
    for value in (quote.bid, quote.bid_size, quote.last, quote.volume):
        assert value != Decimal("0")


def test_a_true_zero_stays_zero_and_distinct_from_absent() -> None:
    ticker = FakeTicker(bid=101.0, ask=101.5, last=101.2, volume=0.0)
    quote = snapshot(make_adapter(FakeIB(ticker=ticker)), STOCK).quote()
    assert quote.volume == Decimal("0.0")  # a real zero is preserved
    assert quote.bid_size is None  # while absence stays None


def test_greek_sentinels_stay_none() -> None:
    ticker = FakeTicker(
        bid=1.0,
        ask=1.2,
        last=1.1,
        modelGreeks=FakeComputation(impliedVol=-1.0, delta=-2.0, gamma=0.04, vega=-2.0, theta=-2.0, undPrice=-1.0),
    )
    result = snapshot(make_adapter(FakeIB(ticker=ticker)), OPTION)
    greeks = result.greeks()
    assert len(greeks) == 1
    observation = greeks[0]
    assert observation.implied_volatility is None
    assert observation.delta is None
    assert observation.vega is None  # ib_async 2.1.0 leaks -2 for vega; we do not
    assert observation.theta is None
    assert observation.underlying_price is None
    assert observation.gamma == Decimal("0.04")


# -- delayed vs live greeks -------------------------------------------------


def test_delayed_greeks_are_never_labelled_live() -> None:
    ticker = FakeTicker(
        marketDataType=3,
        bid=1.0,
        ask=1.2,
        last=1.1,
        bidGreeks=FakeComputation(impliedVol=0.32, delta=0.5),
        modelGreeks=FakeComputation(impliedVol=0.31, delta=0.52),
    )
    result = snapshot(make_adapter(FakeIB(ticker=ticker)), OPTION, market_data_type=3)
    assert result.reported_market_data_type == 3
    greeks_envelopes = [
        env for env in result.envelopes if isinstance(env.payload, GreeksObservation)
    ]
    assert greeks_envelopes, "delayed computations must still be observed"
    for envelope in greeks_envelopes:
        assert envelope.delay_status is DelayStatus.DELAYED
        assert envelope.delay_status is not DelayStatus.LIVE
        assert envelope.payload.tick_type in (80, 81, 82, 83)  # delayed tick ids
        assert envelope.payload.market_data_type == 3
    quote_envelope = next(
        env for env in result.envelopes if isinstance(env.payload, QuoteObservation)
    )
    assert quote_envelope.delay_status is DelayStatus.DELAYED


def test_live_greeks_use_live_tick_ids_in_distinct_envelopes() -> None:
    ticker = FakeTicker(
        marketDataType=1,
        bid=1.0,
        ask=1.2,
        last=1.1,
        bidGreeks=FakeComputation(impliedVol=0.30, delta=0.48),
        askGreeks=FakeComputation(impliedVol=0.33, delta=0.52),
        modelGreeks=FakeComputation(impliedVol=0.31, delta=0.50),
    )
    result = snapshot(make_adapter(FakeIB(ticker=ticker)), OPTION)
    greeks = result.greeks()
    assert {g.basis for g in greeks} == {"bid", "ask", "model"}
    assert {g.tick_type for g in greeks} == {10, 11, 13}
    # One DISTINCT envelope per basis, plus the quote envelope.
    assert len(result.envelopes) == 4


def test_requested_delayed_but_reported_live_is_unknown_not_live() -> None:
    ticker = FakeTicker(marketDataType=1, bid=1.0, ask=1.2, last=1.1)
    result = snapshot(make_adapter(FakeIB(ticker=ticker)), OPTION, market_data_type=3)
    envelope = result.envelopes[0]
    # Contradictory evidence never silently upgrades to LIVE.
    assert envelope.delay_status is DelayStatus.UNKNOWN


# -- envelopes --------------------------------------------------------------


def test_every_observation_is_an_ibkr_envelope_with_time_and_hash() -> None:
    result = snapshot(make_adapter(FakeIB(ticker=FakeTicker(bid=9.0, ask=9.2, last=9.1))), STOCK)
    for envelope in result.envelopes:
        assert envelope.source == "ibkr"
        assert envelope.received_at.tzinfo is not None
        assert envelope.observed_at is None or envelope.observed_at <= envelope.received_at
        assert envelope.stale_after > envelope.received_at
        assert envelope.payload_hash.startswith("sha256:")
        assert envelope.instrument_id == "1001"


def test_partial_quote_is_labelled_partial_quality() -> None:
    result = snapshot(make_adapter(FakeIB(ticker=FakeTicker(bid=9.0))), STOCK)
    assert result.envelopes[0].quality_status is EnvelopeQuality.PARTIAL
    empty = snapshot(make_adapter(FakeIB(ticker=FakeTicker())), STOCK)
    assert empty.envelopes[0].quality_status is EnvelopeQuality.INSUFFICIENT_DATA


# -- greeks quality is DERIVED, exactly like the quote quality ---------------

_GREEK_FIELDS = (
    "implied_volatility",
    "delta",
    "gamma",
    "vega",
    "theta",
    "option_price",
    "pv_dividend",
    "underlying_price",
)


def greeks_envelope(ticker: FakeTicker, **kwargs):
    """The single greeks envelope of an option snapshot."""
    result = snapshot(make_adapter(FakeIB(ticker=ticker)), OPTION, **kwargs)
    return next(env for env in result.envelopes if isinstance(env.payload, GreeksObservation))


def test_greeks_with_one_field_out_of_eight_are_not_valid() -> None:
    """A computation carrying 7 sentinels out of 8 degrades; it never passes.

    Reproducer (CONSTITUTION §4): stamping it VALID removes the
    ``PARTIAL_SNAPSHOT`` degradation of
    ``evaluate_snapshot_fresh_and_coherent``, so advice could be built on
    almost-empty greeks believed to be complete. The quote observed in the
    SAME snapshot is the witness: it derives PARTIAL from the same evidence.
    """
    ticker = FakeTicker(
        bid=1.0,  # ask/last stay unset -> the quote witness is PARTIAL
        modelGreeks=FakeComputation(
            impliedVol=-1.0,
            delta=-2.0,
            gamma=0.04,
            vega=-2.0,
            theta=-2.0,
            optPrice=-1.0,
            pvDividend=-1.0,
            undPrice=-1.0,
        ),
    )
    result = snapshot(make_adapter(FakeIB(ticker=ticker)), OPTION)
    greeks_env = next(e for e in result.envelopes if isinstance(e.payload, GreeksObservation))
    quote_env = next(e for e in result.envelopes if isinstance(e.payload, QuoteObservation))
    present = [name for name in _GREEK_FIELDS if getattr(greeks_env.payload, name) is not None]
    assert present == ["gamma"]  # 1 field out of 8
    assert quote_env.quality_status is EnvelopeQuality.PARTIAL
    assert greeks_env.quality_status is EnvelopeQuality.PARTIAL


def test_complete_risk_set_is_valid_without_the_provider_context_fields() -> None:
    """VALID requires the five risk fields; the three context fields may be absent.

    ``option_price``, ``pv_dividend`` and ``underlying_price`` are provider
    context that IBKR legitimately omits (no dividend, non-model basis).
    Requiring them would make almost every real computation PARTIAL and turn
    the degradation into noise.
    """
    ticker = FakeTicker(
        bid=1.0,
        ask=1.2,
        last=1.1,
        modelGreeks=FakeComputation(
            impliedVol=0.31, delta=0.55, gamma=0.04, vega=0.12, theta=-0.05
        ),
    )
    envelope = greeks_envelope(ticker)
    assert envelope.payload.option_price is None
    assert envelope.payload.pv_dividend is None
    assert envelope.payload.underlying_price is None
    assert envelope.quality_status is EnvelopeQuality.VALID


@pytest.mark.parametrize("missing", ["impliedVol", "delta", "gamma", "vega", "theta"])
def test_any_missing_risk_field_degrades_to_partial(missing: str) -> None:
    """Each of the five risk fields is required: losing one degrades the whole."""
    computation = dict(impliedVol=0.31, delta=0.55, gamma=0.04, vega=0.12, theta=-0.05)
    del computation[missing]
    ticker = FakeTicker(
        bid=1.0, ask=1.2, last=1.1, modelGreeks=FakeComputation(**computation)
    )
    assert greeks_envelope(ticker).quality_status is EnvelopeQuality.PARTIAL


def test_greeks_with_only_context_fields_are_insufficient_data() -> None:
    """No risk field at all is INSUFFICIENT_DATA, never PARTIAL and never VALID."""
    ticker = FakeTicker(
        bid=1.0,
        ask=1.2,
        last=1.1,
        modelGreeks=FakeComputation(optPrice=1.15, undPrice=100.0, pvDividend=0.0),
    )
    envelope = greeks_envelope(ticker)
    assert envelope.payload.underlying_price == Decimal("100.0")
    assert envelope.quality_status is EnvelopeQuality.INSUFFICIENT_DATA


def test_delayed_greeks_quality_is_derived_too() -> None:
    """The delayed regime uses the same derivation: a lone greek is PARTIAL."""
    ticker = FakeTicker(
        marketDataType=3,
        bid=1.0,
        ask=1.2,
        last=1.1,
        modelGreeks=FakeComputation(delta=0.52),
    )
    envelope = greeks_envelope(ticker, market_data_type=3)
    assert envelope.delay_status is DelayStatus.DELAYED
    assert envelope.quality_status is EnvelopeQuality.PARTIAL


# -- subscription lifecycle -------------------------------------------------


def test_snapshot_always_cancels_its_line() -> None:
    fake = FakeIB(ticker=FakeTicker(bid=1.0, ask=1.1, last=1.05))
    result = snapshot(make_adapter(fake), STOCK)
    assert result.cancelled is True
    assert len(fake.cancellations) == 1
    assert len(fake.subscriptions) == 1


def test_snapshot_cancels_even_on_timeout_with_empty_ticker() -> None:
    fake = FakeIB(ticker=FakeTicker())  # never becomes ready
    result = snapshot(make_adapter(fake), STOCK)
    assert result.cancelled is True
    assert len(fake.cancellations) == 1


def test_provider_errors_during_subscription_are_reported() -> None:
    fake = FakeIB(ticker=FakeTicker(), subscribe_errors=((7, 354, "synthetic refusal"),))
    result = snapshot(make_adapter(fake), OPTION)
    codes = [error.code for error in result.provider_errors]
    assert codes == [354]
    assert result.cancelled is True


def test_generic_ticks_are_forwarded_and_mapped() -> None:
    ticker = FakeTicker(
        bid=9.0,
        ask=9.2,
        last=9.1,
        callVolume=1200.0,
        putVolume=900.0,
        callOpenInterest=5000.0,
        putOpenInterest=-1.0,  # sentinel stays None
        histVolatility=0.22,
        impliedVolatility=0.25,
        avOptionVolume=1500.0,
    )
    fake = FakeIB(ticker=ticker)
    result = snapshot(make_adapter(fake), STOCK, generic_ticks=(100, 101, 104, 105, 106))
    assert fake.subscriptions[0][1] == "100,101,104,105,106"
    quote = result.quote()
    assert quote.call_volume == Decimal("1200.0")
    assert quote.put_open_interest is None
    assert quote.historical_volatility_30d == Decimal("0.22")
    assert quote.option_implied_volatility_30d == Decimal("0.25")


def test_market_data_type_is_requested_and_preserved() -> None:
    fake = FakeIB(ticker=FakeTicker(marketDataType=3, bid=1.0, ask=1.2, last=1.1))
    result = snapshot(make_adapter(fake), STOCK, market_data_type=3)
    assert fake.market_data_type_requests == [3]
    assert result.requested_market_data_type == 3
    assert result.reported_market_data_type == 3
    assert result.quote().market_data_type == 3


# -- an ABSENT provider answer is not an EMPTY one --------------------------


def test_empty_scan_is_a_real_answer_but_a_missing_one_is_not() -> None:
    """Zero rows = the scan matched nothing (VALID); no answer = no evidence."""
    definition = ScannerDefinition(
        instrument="STK", location_code="STK.US.MAJOR", scan_code="TOP_PERC_GAIN"
    )
    empty = asyncio.run(make_adapter(FakeIB(scan_rows=())).scanner_run(definition))
    assert empty.payload.rows == ()
    assert empty.quality_status is EnvelopeQuality.VALID

    missing = asyncio.run(make_adapter(FakeIB(scan_rows=None)).scanner_run(definition))
    assert missing.quality_status is EnvelopeQuality.INSUFFICIENT_DATA


def test_empty_news_provider_list_is_a_real_answer_but_a_missing_one_is_not() -> None:
    empty = asyncio.run(make_adapter(FakeIB(providers=())).news_providers())
    assert empty.payload.providers == ()
    assert empty.quality_status is EnvelopeQuality.VALID

    missing = asyncio.run(make_adapter(FakeIB(providers=None)).news_providers())
    assert missing.quality_status is EnvelopeQuality.INSUFFICIENT_DATA
