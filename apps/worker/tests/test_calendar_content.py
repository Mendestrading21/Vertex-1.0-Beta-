"""Unit tests of the pure calendar content builder (SYNTHETIC fixtures only)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from vertex_core.synthetic import (
    EVENT_CATEGORY_DIVIDEND,
    EVENT_CATEGORY_EARNINGS,
    EVENT_CATEGORY_MACRO,
    EVENT_CATEGORY_OPTION_EXPIRATION,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
    generate_calendar_event_envelopes,
)
from vertex_worker.calendar import (
    DEV_SYNTHETIC_CALENDAR_CONFIG,
    IMPORTANCE_RULE_VERSION,
    REASON_INVALID_CATEGORY,
    REASON_INVALID_EVENT_TIME,
    REASON_INVALID_STATUS,
    REASON_SOURCE_NOT_ALLOWED,
    CalendarConfig,
    CalendarEventRecord,
    build_calendar_content,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 20260825


def record_from_envelope(envelope, **overrides: Any) -> CalendarEventRecord:
    fields = dict(
        event_id=envelope.event_id,
        source=envelope.source,
        instrument_ref=envelope.instrument_id,
        as_of=envelope.as_of,
        quality_status=envelope.quality_status.value,
        rights=envelope.rights,
        schema_version=envelope.schema_version,
        payload=dict(envelope.payload),
    )
    fields.update(overrides)
    return CalendarEventRecord(**fields)


@pytest.fixture()
def records() -> list[CalendarEventRecord]:
    envelopes = generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    return [record_from_envelope(envelope) for envelope in envelopes]


def build(records, **kwargs):
    defaults = dict(
        now=NOW,
        config=DEV_SYNTHETIC_CALENDAR_CONFIG,
        positions_by_ticker={},
        theses_by_ticker={},
    )
    defaults.update(kwargs)
    return build_calendar_content(records, **defaults)


def test_empty_population_is_honest() -> None:
    content = build([])
    assert content["population"] == "EMPTY"
    assert content["agenda"] == []
    assert content["coverage"]["observations_considered"] == 0


def test_agenda_is_sorted_and_population_synthetic(records) -> None:
    content = build(records)
    assert content["population"] == "SYNTHETIC"
    instants = [entry["event_time_utc"] for entry in content["agenda"]]
    assert instants == sorted(instants)
    assert content["coverage"]["events_displayed"] == len(records)
    assert content["coverage"]["rejected_records"] == []
    # Estimated and confirmed keep their DISTINCT labels, both present.
    assert content["statuses"]["ESTIMATED"] > 0
    assert content["statuses"]["CONFIRMED"] > 0
    assert set(content["categories"]) == {
        EVENT_CATEGORY_DIVIDEND,
        EVENT_CATEGORY_EARNINGS,
        EVENT_CATEGORY_MACRO,
        EVENT_CATEGORY_OPTION_EXPIRATION,
    }


def test_determinism(records) -> None:
    assert build(records) == build(list(reversed(records)))


def test_importance_comes_from_the_versioned_rule(records) -> None:
    thesis_ticker = "SYN-TECH-01"
    position_ticker = "SYN-ENER-01"
    content = build(
        records,
        positions_by_ticker={position_ticker: [1]},
        theses_by_ticker={
            thesis_ticker: [
                {"thesis_id": 7, "title": "synthetic thesis", "status": "ACTIVE"}
            ]
        },
    )
    assert content["importance_rule"]["version"] == IMPORTANCE_RULE_VERSION
    by_id = {entry["event_id"]: entry for entry in content["agenda"]}

    macro = next(
        e for e in content["agenda"] if e["category"] == EVENT_CATEGORY_MACRO
    )
    assert macro["importance"] == {
        "rank": 1,
        "code": "MACRO_GLOBAL",
        "rule_version": IMPORTANCE_RULE_VERSION,
    }
    assert by_id[f"syn-ev-earnings-{thesis_ticker}"]["importance"]["code"] == (
        "EARNINGS_POSITION_OR_THESIS"
    )
    assert by_id[f"syn-ev-earnings-{position_ticker}"]["importance"]["code"] == (
        "EARNINGS_POSITION_OR_THESIS"
    )
    watchlist_earnings = by_id["syn-ev-earnings-SYN-TECH-02"]
    assert watchlist_earnings["importance"] == {
        "rank": 3,
        "code": "EARNINGS_WATCHLIST",
        "rule_version": IMPORTANCE_RULE_VERSION,
    }
    dividend = next(
        e for e in content["agenda"] if e["category"] == EVENT_CATEGORY_DIVIDEND
    )
    assert dividend["importance"]["rank"] == 4
    expiry = next(
        e
        for e in content["agenda"]
        if e["category"] == EVENT_CATEGORY_OPTION_EXPIRATION
    )
    assert expiry["importance"]["rank"] == 5


def test_event_context_links_positions_and_theses(records) -> None:
    ticker = "SYN-TECH-01"
    content = build(
        records,
        positions_by_ticker={ticker: [1, 3]},
        theses_by_ticker={
            ticker: [{"thesis_id": 9, "title": "t", "status": "ACTIVE"}]
        },
    )
    entry = next(
        e for e in content["agenda"] if e["event_id"] == f"syn-ev-earnings-{ticker}"
    )
    context = entry["event_context"]
    assert context["positions"] == [{"portfolio_id": 1}, {"portfolio_id": 3}]
    assert context["theses"] == [
        {"thesis_id": 9, "title": "t", "status": "ACTIVE"}
    ]
    rels = {link["rel"] for link in context["links"]}
    assert rels == {"analysis", "option_chain", "thesis"}
    macro = next(
        e for e in content["agenda"] if e["category"] == EVENT_CATEGORY_MACRO
    )
    assert macro["event_context"] == {"positions": [], "theses": [], "links": []}


def test_revisions_stay_visible_with_previous_values(records) -> None:
    content = build(records)
    revised = [entry for entry in content["agenda"] if entry["revised"]]
    assert revised
    for entry in revised:
        assert entry["status"] == "CONFIRMED"
        revision = entry["revisions"][0]
        assert revision["previous_status"] == "ESTIMATED"
        assert revision["previous_event_time_utc"] != entry["event_time_utc"]


def test_timezones_are_conserved_verbatim(records) -> None:
    content = build(records)
    for entry in content["agenda"]:
        source = next(
            r for r in records if r.payload["event_id"] == entry["event_id"]
        )
        assert entry["exchange_timezone"] == source.payload["exchange_timezone"]
        assert entry["event_time_local"] == source.payload["event_time_local"]
        assert entry["event_time_utc"] == source.payload["event_time_utc"]


def test_latest_envelope_per_stable_id_wins(records) -> None:
    target = records[0]
    revised_payload = dict(target.payload)
    revised_payload["status"] = "CONFIRMED"
    revised_payload["revisions"] = [
        {
            "revised_at": NOW.isoformat(),
            "previous_status": target.payload["status"],
            "previous_event_time_utc": target.payload["event_time_utc"],
            "reason": "synthetic re-check",
        }
    ]
    revision_record = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:revision:0001",
        as_of=target.as_of + timedelta(minutes=5),
        payload=revised_payload,
    )
    content = build([*records, revision_record])
    entry = next(
        e
        for e in content["agenda"]
        if e["event_id"] == target.payload["event_id"]
    )
    assert entry["source_event_id"] == "synthetic-dev:revision:0001"
    assert entry["revisions"] == revised_payload["revisions"]
    assert content["coverage"]["events_superseded"] == 1
    assert content["coverage"]["events_displayed"] == len(records)


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ({"category": "IPO_UNKNOWN"}, REASON_INVALID_CATEGORY),
        ({"status": "TENTATIVE"}, REASON_INVALID_STATUS),
        ({"event_time_utc": "2026-09-01T12:00:00"}, REASON_INVALID_EVENT_TIME),
    ],
)
def test_invalid_events_are_rejected_with_reason(
    records, mutation: dict[str, Any], reason: str
) -> None:
    target = records[0]
    payload = dict(target.payload)
    payload.update(mutation)
    broken = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:broken:0001",
        payload=payload,
    )
    content = build([broken])
    assert content["agenda"] == []
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "synthetic-dev:broken:0001", "reason": reason}
    ]


def test_undeclared_source_is_rejected(records) -> None:
    foreign = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="foreign:0001",
        source="unknown-source",
    )
    content = build([foreign])
    assert content["agenda"] == []
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "foreign:0001", "reason": REASON_SOURCE_NOT_ALLOWED}
    ]


def test_config_validation_fails_closed() -> None:
    with pytest.raises(ValueError):
        CalendarConfig(
            allowed_sources=frozenset({SYNTHETIC_SOURCE}),
            usable_rights=frozenset({SYNTHETIC_RIGHTS}),
            lookback=timedelta(0),
        )
    with pytest.raises(ValueError):
        CalendarConfig(
            allowed_sources=frozenset({SYNTHETIC_SOURCE}),
            usable_rights=frozenset({SYNTHETIC_RIGHTS}),
            max_observations=0,
        )


def test_naive_clock_is_rejected(records) -> None:
    with pytest.raises(ValueError):
        build(records, now=datetime(2026, 8, 25, 12, 0, 0))
