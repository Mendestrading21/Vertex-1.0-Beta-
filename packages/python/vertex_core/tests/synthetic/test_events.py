"""Tests of the synthetic calendar-event generator (SYNTHETIC fixtures only)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from vertex_core.synthetic import (
    EVENT_CATEGORY_DIVIDEND,
    EVENT_CATEGORY_EARNINGS,
    EVENT_CATEGORY_MACRO,
    EVENT_CATEGORY_OPTION_EXPIRATION,
    EVENT_SCOPE_GLOBAL,
    EVENT_SCOPE_TICKER,
    EVENT_STATUS_CONFIRMED,
    EVENT_STATUS_ESTIMATED,
    SYNTHETIC_EXCHANGE_TIMEZONE,
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_MACRO_EVENT_COUNT,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SCHEMA_CALENDAR_EVENT,
    SYNTHETIC_SOURCE,
    SYNTHETIC_TITLE_PREFIX,
    generate_calendar_event_envelopes,
    generate_option_chain_envelopes,
)

BASE_TIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
SEED = 20260825


@pytest.fixture()
def envelopes():
    return generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)


def _by_category(envelopes, category):
    return [e for e in envelopes if e.payload["category"] == category]


def test_deterministic_byte_identical() -> None:
    first = generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    second = generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    assert [e.model_dump(mode="json") for e in first] == [
        e.model_dump(mode="json") for e in second
    ]


def test_every_envelope_is_labeled_synthetic(envelopes) -> None:
    for envelope in envelopes:
        assert envelope.source == SYNTHETIC_SOURCE
        assert envelope.rights == SYNTHETIC_RIGHTS
        assert envelope.schema_version == SYNTHETIC_SCHEMA_CALENDAR_EVENT
        assert envelope.payload["synthetic"] is True
        assert envelope.payload["title"].startswith(SYNTHETIC_TITLE_PREFIX)


def test_envelope_timestamps_precede_base_time(envelopes) -> None:
    for envelope in envelopes:
        assert envelope.published_at < BASE_TIME
        assert envelope.received_at < BASE_TIME
        assert envelope.as_of < BASE_TIME


def test_stable_unique_event_ids(envelopes) -> None:
    stable_ids = [e.payload["event_id"] for e in envelopes]
    assert len(stable_ids) == len(set(stable_ids))
    # Stable ids are reproducible: a second generation yields the same set.
    again = generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    assert stable_ids == [e.payload["event_id"] for e in again]
    # And every envelope's source_event_id is the stable calendar id.
    assert stable_ids == [e.source_event_id for e in envelopes]


def test_statuses_are_only_estimated_or_confirmed(envelopes) -> None:
    for envelope in envelopes:
        assert envelope.payload["status"] in (
            EVENT_STATUS_ESTIMATED,
            EVENT_STATUS_CONFIRMED,
        )


def test_earnings_cover_focus_tickers_with_dated_revisions(envelopes) -> None:
    earnings = _by_category(envelopes, EVENT_CATEGORY_EARNINGS)
    assert sorted(e.payload["ticker"] for e in earnings) == sorted(
        SYNTHETIC_FOCUS_TICKERS
    )
    confirmed = [
        e for e in earnings if e.payload["status"] == EVENT_STATUS_CONFIRMED
    ]
    estimated = [
        e for e in earnings if e.payload["status"] == EVENT_STATUS_ESTIMATED
    ]
    assert confirmed and estimated  # both labels really exist, never merged
    for envelope in confirmed:
        revisions = envelope.payload["revisions"]
        assert len(revisions) == 1
        revision = revisions[0]
        # The revision is DATED and preserves the previous value verbatim.
        assert datetime.fromisoformat(revision["revised_at"]) < BASE_TIME
        assert revision["previous_status"] == EVENT_STATUS_ESTIMATED
        assert (
            revision["previous_event_time_utc"]
            != envelope.payload["event_time_utc"]
        )
    for envelope in estimated:
        assert envelope.payload["revisions"] == []


def test_expirations_are_derived_from_the_generated_chains(envelopes) -> None:
    chains = generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME)
    chain_pairs = {
        (c.payload["underlying"], c.payload["expiration"]) for c in chains
    }
    event_pairs = {
        (e.payload["ticker"], e.payload["expiration"])
        for e in _by_category(envelopes, EVENT_CATEGORY_OPTION_EXPIRATION)
    }
    assert event_pairs == chain_pairs
    for envelope in _by_category(envelopes, EVENT_CATEGORY_OPTION_EXPIRATION):
        assert envelope.payload["status"] == EVENT_STATUS_CONFIRMED
        assert envelope.payload["event_time_utc"].startswith(
            envelope.payload["expiration"][:4]
        )


def test_macro_events_are_global(envelopes) -> None:
    macro = _by_category(envelopes, EVENT_CATEGORY_MACRO)
    assert len(macro) == SYNTHETIC_MACRO_EVENT_COUNT
    for envelope in macro:
        assert envelope.payload["ticker"] is None
        assert envelope.payload["scope"] == EVENT_SCOPE_GLOBAL
        assert envelope.instrument_id is None


def test_dividends_exist_with_decimal_string_amounts(envelopes) -> None:
    dividends = _by_category(envelopes, EVENT_CATEGORY_DIVIDEND)
    assert len(dividends) == 2
    for envelope in dividends:
        assert envelope.payload["scope"] == EVENT_SCOPE_TICKER
        assert isinstance(envelope.payload["amount"], str)
        assert envelope.payload["currency"] == "SYN"
        assert envelope.payload["status"] == EVENT_STATUS_CONFIRMED


def test_timezone_fields_denote_the_same_instant(envelopes) -> None:
    for envelope in envelopes:
        payload = envelope.payload
        assert payload["exchange_timezone"] == SYNTHETIC_EXCHANGE_TIMEZONE
        utc_instant = datetime.fromisoformat(payload["event_time_utc"])
        local_instant = datetime.fromisoformat(payload["event_time_local"])
        assert utc_instant.tzinfo is not None
        assert utc_instant.utcoffset().total_seconds() == 0
        assert local_instant.tzinfo is not None
        assert utc_instant == local_instant
        # The local field genuinely lives in the declared exchange timezone.
        assert local_instant.utcoffset() == local_instant.astimezone(
            ZoneInfo(SYNTHETIC_EXCHANGE_TIMEZONE)
        ).utcoffset()


def test_input_validation_fails_closed() -> None:
    with pytest.raises(TypeError):
        generate_calendar_event_envelopes(seed="1", base_time=BASE_TIME)
    with pytest.raises(TypeError):
        generate_calendar_event_envelopes(seed=1, base_time="2026-08-25")
    with pytest.raises(ValueError):
        generate_calendar_event_envelopes(
            seed=1, base_time=datetime(2026, 8, 25, 12, 0, 0)  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
        )


# --------------------------------------------------------------------------
# Contract pinned by the calendar chain: the consumer (worker builder)
# validates scope, timezone and revision dating fail-closed. These tests keep
# the generator honest about what it promises downstream.
# --------------------------------------------------------------------------


def test_scope_is_always_coherent_with_the_ticker_presence(envelopes) -> None:
    """A ticker event is TICKER-scoped, a ticker-less event is GLOBAL: the
    scope can never promote an event's importance by contradiction."""
    for envelope in envelopes:
        payload = envelope.payload
        expected = (
            EVENT_SCOPE_GLOBAL if payload["ticker"] is None else EVENT_SCOPE_TICKER
        )
        assert payload["scope"] == expected


def test_every_revision_entry_is_dated_with_an_aware_revised_at(envelopes) -> None:
    """The business chronology of a revision is its ``revised_at``: every
    declared entry carries one, aware and strictly before the envelope."""
    for envelope in envelopes:
        for entry in envelope.payload["revisions"]:
            revised_at = datetime.fromisoformat(entry["revised_at"])
            assert revised_at.tzinfo is not None
            assert revised_at.utcoffset() is not None
            assert revised_at < envelope.as_of


def test_one_generation_shares_a_single_as_of(envelopes) -> None:
    """All envelopes of ONE generation share one ``as_of``.

    Documented on purpose: equality of ``as_of`` is the NORMAL case, so the
    consumer must never let an arbitrary tie-break (envelope id order) decide
    which value of a stable event id is displayed.
    """
    assert len({envelope.as_of for envelope in envelopes}) == 1
