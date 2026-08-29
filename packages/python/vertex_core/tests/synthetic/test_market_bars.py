"""Tests of the deterministic synthetic daily-OHLCV-bars generator.

The bars generator is a SEPARATE function: the existing daily-quote envelope
stream must stay byte-stable. Everything here is synthetic, deterministic and
clock-free.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from vertex_core.contracts import EnvelopeQuality
from vertex_core.synthetic import (
    SYNTHETIC_BAR_COUNT,
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_OPTION_UNDERLYINGS,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SCHEMA_DAILY_BARS,
    SYNTHETIC_SOURCE,
    generate_daily_bar_envelopes,
    generate_daily_quote_envelopes,
)

SEED = 20260830
BASE_TIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def envelopes():
    return generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)


def test_pure_function_of_inputs(envelopes) -> None:
    again = generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    assert [e.model_dump(mode="json") for e in envelopes] == [
        e.model_dump(mode="json") for e in again
    ]


def test_existing_daily_quote_stream_is_untouched() -> None:
    # Regression guard: adding the bars generator must not shift the RNG
    # stream of the existing daily-quote generator.
    first = generate_daily_quote_envelopes(seed=7, base_time=BASE_TIME)
    second = generate_daily_quote_envelopes(seed=7, base_time=BASE_TIME)
    assert [e.payload for e in first] == [e.payload for e in second]
    assert len(first) == 46


def test_one_envelope_per_focus_ticker(envelopes) -> None:
    assert [e.payload["ticker"] for e in envelopes] == list(SYNTHETIC_FOCUS_TICKERS)
    assert SYNTHETIC_FOCUS_TICKERS == SYNTHETIC_OPTION_UNDERLYINGS
    for envelope in envelopes:
        assert envelope.schema_version == SYNTHETIC_SCHEMA_DAILY_BARS
        assert envelope.source == SYNTHETIC_SOURCE
        assert envelope.rights == SYNTHETIC_RIGHTS
        assert envelope.quality_status is EnvelopeQuality.VALID
        assert envelope.payload["synthetic"] is True
        assert envelope.instrument_id == envelope.payload["ticker"]


def test_sixty_bars_with_ohlc_invariants(envelopes) -> None:
    for envelope in envelopes:
        bars = envelope.payload["bars"]
        assert len(bars) == SYNTHETIC_BAR_COUNT == 60
        previous_day: date | None = None
        for bar in bars:
            open_ = Decimal(bar["open"])
            high = Decimal(bar["high"])
            low = Decimal(bar["low"])
            close = Decimal(bar["close"])
            assert high >= max(open_, close)
            assert low <= min(open_, close)
            assert low >= Decimal("0.01")
            assert isinstance(bar["volume"], int) and bar["volume"] >= 0
            for field in ("open", "high", "low", "close"):
                assert isinstance(bar[field], str)
            day = date.fromisoformat(bar["trading_day"])
            if previous_day is not None:
                assert day > previous_day
            previous_day = day
        assert previous_day is not None
        assert previous_day < BASE_TIME.date()


def test_bars_are_a_continuous_series(envelopes) -> None:
    for envelope in envelopes:
        bars = envelope.payload["bars"]
        for previous, current in zip(bars, bars[1:]):
            assert current["open"] == previous["close"]


def test_unknown_ticker_is_rejected() -> None:
    with pytest.raises(ValueError):
        generate_daily_bar_envelopes(
            seed=SEED, base_time=BASE_TIME, tickers=("NOT-A-SYN",)
        )


def test_naive_base_time_rejected() -> None:
    with pytest.raises(ValueError):
        generate_daily_bar_envelopes(
            seed=SEED, base_time=datetime(2026, 8, 25, 12, 0, 0)
        )
