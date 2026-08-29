"""Tests of the deterministic synthetic daily-quote generator (LOT-13)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from vertex_core.contracts import EnvelopeQuality
from vertex_core.synthetic import (
    SYNTHETIC_ADJUSTMENT_BASIS,
    SYNTHETIC_MARKET_CURRENCY,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SCHEMA_DAILY_QUOTE,
    SYNTHETIC_SECTOR_LABELS_FR,
    SYNTHETIC_SECTOR_TICKERS,
    SYNTHETIC_SECTORS,
    SYNTHETIC_SOURCE,
    generate_daily_quote_envelopes,
    is_synthetic,
)

BASE_TIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
SEED = 424242

DECIMAL_STRING = re.compile(r"^\d+\.\d{2}$")


def test_universe_is_24_tickers_in_6_sectors() -> None:
    assert len(SYNTHETIC_SECTORS) == 6
    assert set(SYNTHETIC_SECTOR_TICKERS) == set(SYNTHETIC_SECTORS)
    all_tickers = [t for sector in SYNTHETIC_SECTORS for t in SYNTHETIC_SECTOR_TICKERS[sector]]
    assert len(all_tickers) == 24
    assert len(set(all_tickers)) == 24
    for sector, tickers in SYNTHETIC_SECTOR_TICKERS.items():
        assert len(tickers) == 4
        assert all(ticker.startswith(f"{sector}-") for ticker in tickers)
    assert set(SYNTHETIC_SECTOR_LABELS_FR) == set(SYNTHETIC_SECTORS)


def test_determinism_same_inputs_same_envelopes() -> None:
    first = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    second = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    assert first == second
    other_seed = generate_daily_quote_envelopes(seed=SEED + 1, base_time=BASE_TIME)
    assert other_seed != first


def test_every_envelope_is_labeled_synthetic() -> None:
    envelopes = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    for envelope in envelopes:
        assert envelope.source == SYNTHETIC_SOURCE
        assert envelope.rights == SYNTHETIC_RIGHTS
        assert envelope.schema_version == SYNTHETIC_SCHEMA_DAILY_QUOTE
        assert envelope.payload["synthetic"] is True
        assert is_synthetic(envelope)


def test_two_days_of_decimal_string_closes_per_covered_ticker() -> None:
    envelopes = generate_daily_quote_envelopes(
        seed=SEED, base_time=BASE_TIME, missing_close_count=2
    )
    by_ticker: dict[str, list] = {}
    for envelope in envelopes:
        payload = envelope.payload
        assert DECIMAL_STRING.match(payload["close"]), payload["close"]
        assert Decimal(payload["close"]) > 0
        assert payload["currency"] == SYNTHETIC_MARKET_CURRENCY
        assert payload["adjustment_basis"] == SYNTHETIC_ADJUSTMENT_BASIS
        assert payload["type"] == "daily_quote"
        assert envelope.instrument_id == payload["ticker"]
        assert payload["ticker"].startswith(payload["sector"])
        by_ticker.setdefault(payload["ticker"], []).append(envelope)

    assert len(by_ticker) == 24
    with_both = [t for t, group in by_ticker.items() if len(group) == 2]
    with_one = [t for t, group in by_ticker.items() if len(group) == 1]
    assert len(with_both) == 22
    assert len(with_one) == 2
    for ticker in with_both:
        days = {e.payload["trading_day"] for e in by_ticker[ticker]}
        assert len(days) == 2


def test_qualities_include_partial_and_stale() -> None:
    envelopes = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    qualities = [envelope.quality_status for envelope in envelopes]
    assert qualities.count(EnvelopeQuality.PARTIAL) == 2
    assert qualities.count(EnvelopeQuality.STALE) == 2
    assert qualities.count(EnvelopeQuality.VALID) == len(envelopes) - 4
    # STALE envelopes are honestly already stale (stale_after == received_at).
    for envelope in envelopes:
        if envelope.quality_status is EnvelopeQuality.STALE:
            assert envelope.stale_after == envelope.received_at
        else:
            assert envelope.stale_after > envelope.received_at


def test_latest_moves_contain_both_signs_among_covered() -> None:
    envelopes = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    closes: dict[str, dict[str, Decimal]] = {}
    for envelope in envelopes:
        payload = envelope.payload
        closes.setdefault(payload["ticker"], {})[payload["trading_day"]] = Decimal(
            payload["close"]
        )
    signs = set()
    for days in closes.values():
        if len(days) != 2:
            continue
        older_day, latest_day = sorted(days)
        move = days[latest_day] - days[older_day]
        if move > 0:
            signs.add("up")
        elif move < 0:
            signs.add("down")
    assert {"up", "down"} <= signs


def test_all_timestamps_strictly_before_base_time_and_aware_utc() -> None:
    envelopes = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    for envelope in envelopes:
        for value in (envelope.published_at, envelope.received_at, envelope.as_of):
            assert value is not None
            assert value.tzinfo is not None
            assert value < BASE_TIME


def test_event_ids_unique_and_disjoint_from_news_generator_ids() -> None:
    envelopes = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    ids = [envelope.event_id for envelope in envelopes]
    assert len(set(ids)) == len(ids)
    assert all(f"{SYNTHETIC_SOURCE}:{SEED}:dq" in event_id for event_id in ids)


def test_input_validation_fails_closed() -> None:
    with pytest.raises(TypeError):
        generate_daily_quote_envelopes(seed="1", base_time=BASE_TIME)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        generate_daily_quote_envelopes(seed=True, base_time=BASE_TIME)
    with pytest.raises(TypeError):
        generate_daily_quote_envelopes(seed=1, base_time="now")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        generate_daily_quote_envelopes(
            seed=1, base_time=BASE_TIME.replace(tzinfo=None)
        )
    with pytest.raises(ValueError):
        generate_daily_quote_envelopes(seed=1, base_time=BASE_TIME, missing_close_count=-1)
    with pytest.raises(ValueError):
        generate_daily_quote_envelopes(seed=1, base_time=BASE_TIME, missing_close_count=21)


def test_zero_missing_closes_supported() -> None:
    envelopes = generate_daily_quote_envelopes(
        seed=SEED, base_time=BASE_TIME, missing_close_count=0
    )
    assert len(envelopes) == 48
