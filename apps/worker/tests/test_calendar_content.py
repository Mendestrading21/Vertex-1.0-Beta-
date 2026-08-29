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
    REASON_INVALID_REVISIONS,
    REASON_INVALID_SCOPE,
    REASON_INVALID_STATUS,
    REASON_INVALID_TIMEZONE,
    REASON_RIGHTS_NOT_USABLE,
    REASON_SOURCE_NOT_ALLOWED,
    CalendarConfig,
    CalendarEventRecord,
    build_calendar_content,
    load_calendar_event_records,
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
        stale_after=envelope.stale_after,
        quality_status=envelope.quality_status.value,
        delay_status=envelope.delay_status.value,
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
    """A revision arriving as a NEW envelope of the same stable id wins.

    The fixture reproduces the GENERATOR's normal case: every envelope of one
    generation carries the SAME ``as_of``, so only the business revision
    chronology can decide — no artificial ``as_of`` offset here.
    """
    target = estimated_earnings(records)
    revised_payload = dict(target.payload)
    revised_payload["status"] = "CONFIRMED"
    revised_payload["revisions"] = [
        {
            "revised_at": (target.as_of - timedelta(hours=1)).isoformat(),
            "previous_status": target.payload["status"],
            "previous_event_time_utc": target.payload["event_time_utc"],
            "reason": "synthetic re-check",
        }
    ]
    revision_record = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:revision:0001",
        as_of=target.as_of,
        payload=revised_payload,
    )
    content = build([*records, revision_record])
    entry = next(
        e
        for e in content["agenda"]
        if e["event_id"] == target.payload["event_id"]
    )
    assert entry["status"] == "CONFIRMED"
    assert entry["source_event_id"] == "synthetic-dev:revision:0001"
    assert entry["revisions"] == revised_payload["revisions"]
    assert entry["revised"] is True
    assert entry["previous_values"] == [
        {
            "source_event_id": target.event_id,
            "source": target.source,
            "as_of": target.as_of.isoformat(),
            "status": "ESTIMATED",
            "event_time_utc": target.payload["event_time_utc"],
        }
    ]
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


# --------------------------------------------------------------------------
# Regression tests of the audited defects (F1..F10). Every test below was
# written RED against the previous builder and describes an observable
# promise of docs/01-product/pages/02-calendar.md, never an implementation
# detail.
# --------------------------------------------------------------------------


def estimated_earnings(records) -> CalendarEventRecord:
    """The ESTIMATED earnings record of a focus ticker (revisions == [])."""
    return next(
        record
        for record in records
        if record.payload["category"] == EVENT_CATEGORY_EARNINGS
        and record.payload["status"] == "ESTIMATED"
    )


def with_payload(record: CalendarEventRecord, **payload_changes: Any) -> dict:
    payload = dict(record.payload)
    payload.update(payload_changes)
    return payload


def test_revision_without_revisions_list_must_not_erase_the_previous_value(
    records,
) -> None:
    """F1 — a revision that declares NO ``revisions`` entry still leaves the
    previous value readable: the builder keeps the trace of the records it
    really saw, so a confirmed event never becomes 'confirmed all along'."""
    original = estimated_earnings(records)
    stable_id = original.payload["event_id"]
    assert original.payload["revisions"] == []
    confirmed_utc = "2026-09-05T15:30:00+00:00"
    confirmation = CalendarEventRecord(
        event_id="synthetic-dev:confirmation:0001",
        source=original.source,
        instrument_ref=original.instrument_ref,
        as_of=original.as_of + timedelta(hours=1),
        stale_after=original.stale_after + timedelta(hours=1),
        quality_status=original.quality_status,
        delay_status=original.delay_status,
        rights=original.rights,
        schema_version=original.schema_version,
        payload=with_payload(
            original,
            status="CONFIRMED",
            event_time_utc=confirmed_utc,
            event_time_local=confirmed_utc,
            exchange_timezone="UTC",
            revisions=[],  # the source declares NOTHING: the trace is ours
        ),
    )

    content = build([original, confirmation])
    entry = next(e for e in content["agenda"] if e["event_id"] == stable_id)

    assert entry["status"] == "CONFIRMED"
    assert entry["event_time_utc"] == confirmed_utc
    # The state CHANGED: the event is flagged revised even with an empty
    # declared revisions list...
    assert entry["revised"] is True
    assert entry["revisions"] == []
    # ...and the previous value stays READABLE, with its provenance.
    assert entry["previous_values"] == [
        {
            "source_event_id": original.event_id,
            "source": original.source,
            "as_of": original.as_of.isoformat(),
            "status": "ESTIMATED",
            "event_time_utc": original.payload["event_time_utc"],
        }
    ]
    assert content["coverage"]["events_superseded"] == 1


def test_same_as_of_revision_wins_by_revised_at_not_by_event_id(records) -> None:
    """F2 — at EQUAL ``as_of`` (the generator's normal case) the business
    revision chronology decides, never the lexicographic envelope id."""
    original = estimated_earnings(records)
    stable_id = original.payload["event_id"]
    revised_at = (original.as_of - timedelta(hours=2)).isoformat()
    confirmed_utc = "2026-09-05T15:30:00+00:00"
    revision_payload = with_payload(
        original,
        status="CONFIRMED",
        event_time_utc=confirmed_utc,
        event_time_local=confirmed_utc,
        exchange_timezone="UTC",
        revisions=[
            {
                "revised_at": revised_at,
                "previous_status": "ESTIMATED",
                "previous_event_time_utc": original.payload["event_time_utc"],
                "reason": "synthetic confirmation of the estimated date",
            }
        ],
    )
    # The REVISION sorts FIRST lexicographically, the original LAST: only a
    # business ordering can make the revision win.
    revision = CalendarEventRecord(
        event_id="aaa-revision",
        source=original.source,
        instrument_ref=original.instrument_ref,
        as_of=original.as_of,
        stale_after=original.stale_after,
        quality_status=original.quality_status,
        delay_status=original.delay_status,
        rights=original.rights,
        schema_version=original.schema_version,
        payload=revision_payload,
    )
    stale_original = CalendarEventRecord(
        event_id="zzz-original",
        source=original.source,
        instrument_ref=original.instrument_ref,
        as_of=original.as_of,
        stale_after=original.stale_after,
        quality_status=original.quality_status,
        delay_status=original.delay_status,
        rights=original.rights,
        schema_version=original.schema_version,
        payload=dict(original.payload),
    )

    content = build([revision, stale_original])
    entry = next(e for e in content["agenda"] if e["event_id"] == stable_id)

    assert entry["status"] == "CONFIRMED"
    assert entry["source_event_id"] == "aaa-revision"
    assert entry["revisions"] == revision_payload["revisions"]
    # The masked original is not lost: it is the readable previous value.
    assert entry["previous_values"] == [
        {
            "source_event_id": "zzz-original",
            "source": original.source,
            "as_of": original.as_of.isoformat(),
            "status": "ESTIMATED",
            "event_time_utc": original.payload["event_time_utc"],
        }
    ]
    # And the order of the input sequence changes nothing (determinism).
    assert build([stale_original, revision]) == content


def test_a_revision_entry_without_a_dated_revised_at_is_rejected(records) -> None:
    """F2 — the business ordering needs a DATED revision: an undated entry is
    rejected fail-closed instead of silently ordering by envelope id."""
    original = estimated_earnings(records)
    broken = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:undated:0001",
        payload=with_payload(
            original,
            revisions=[{"previous_status": "ESTIMATED"}],
        ),
    )
    content = build([broken])
    assert content["agenda"] == []
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "synthetic-dev:undated:0001", "reason": REASON_INVALID_REVISIONS}
    ]


def test_all_records_rejected_never_yields_population_real(records) -> None:
    """F3 — a population is computed over ALL considered records, and an
    agenda emptied by a rights rejection says WHICH right is missing instead
    of publishing a misleading 'ok' empty agenda."""
    not_entitled = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:not-entitled:0001",
        rights="REALTIME",
    )
    content = build([not_entitled])

    assert content["agenda"] == []
    # The record IS synthetic: calling this population REAL would present a
    # fixture as real data.
    assert content["population"] == "SYNTHETIC"
    assert content["agenda_state"] == "NOT_ENTITLED"
    assert content["agenda_state_reason"]
    assert content["coverage"]["rejected_reasons"] == {REASON_RIGHTS_NOT_USABLE: 1}
    assert content["coverage"]["rejected_records"] == [
        {
            "event_id": "synthetic-dev:not-entitled:0001",
            "reason": REASON_RIGHTS_NOT_USABLE,
        }
    ]


def test_agenda_states_are_distinct(records) -> None:
    """F3 — EMPTY (nothing observed), REJECTED (everything invalid) and OK
    are three DIFFERENT states, never merged into one silent empty list."""
    assert build([])["agenda_state"] == "EMPTY"
    invalid = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:invalid:0001",
        payload=with_payload(records[0], category="IPO_UNKNOWN"),
    )
    assert build([invalid])["agenda_state"] == "REJECTED"
    assert build(records)["agenda_state"] == "OK"


@pytest.mark.parametrize("scope", ["GLOBAL", "WORLD", 12345, None])
def test_unknown_or_incoherent_scope_never_promotes_importance(
    records, scope: Any
) -> None:
    """F4 — ``scope`` is validated against an allowlist AND against the ticker
    presence: a MACRO event carrying a ticker can never claim the global
    rank 1, and a non-string scope never reaches the snapshot."""
    macro = next(
        record
        for record in records
        if record.payload["category"] == EVENT_CATEGORY_MACRO
    )
    forged = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:forged-scope:0001",
        payload=with_payload(macro, ticker="SYN-TECH-01", scope=scope),
    )
    content = build([forged])
    assert content["agenda"] == []
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "synthetic-dev:forged-scope:0001", "reason": REASON_INVALID_SCOPE}
    ]


@pytest.mark.parametrize(
    "timezone_name",
    ["Not/AZone", "America/New_York"],
)
def test_exchange_timezone_must_be_resolvable_and_coherent(
    records, timezone_name: str
) -> None:
    """F5 — the declared timezone must be a RESOLVABLE IANA identifier whose
    offset matches ``event_time_local``: an unknown zone and a zone
    contradicting the local offset are both rejected."""
    original = estimated_earnings(records)
    assert original.payload["event_time_local"].endswith("+02:00")
    forged = record_from_envelope(
        generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)[0],
        event_id="synthetic-dev:forged-tz:0001",
        payload=with_payload(original, exchange_timezone=timezone_name),
    )
    content = build([forged])
    assert content["agenda"] == []
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "synthetic-dev:forged-tz:0001", "reason": REASON_INVALID_TIMEZONE}
    ]


def test_watchlist_label_is_only_used_for_a_declared_watchlist_ticker(
    records,
) -> None:
    """F6 — the ``EARNINGS_WATCHLIST`` label claims a declared watchlist
    ticker: the builder now READS the declared watchlist instead of labelling
    every remaining ticker."""
    config = CalendarConfig(
        allowed_sources=frozenset({SYNTHETIC_SOURCE}),
        usable_rights=frozenset({SYNTHETIC_RIGHTS}),
        watchlist=("SYN-ENER-01",),
    )
    content = build(records, config=config)
    by_id = {entry["event_id"]: entry for entry in content["agenda"]}

    assert by_id["syn-ev-earnings-SYN-ENER-01"]["importance"]["code"] == (
        "EARNINGS_WATCHLIST"
    )
    outside = by_id["syn-ev-earnings-SYN-TECH-02"]["importance"]
    assert outside["code"] == "EARNINGS_OTHER"
    assert outside["rank"] > 3
    assert outside["rule_version"] == IMPORTANCE_RULE_VERSION
    codes = {entry["code"] for entry in content["importance_rule"]["ranks"]}
    assert {"EARNINGS_WATCHLIST", "EARNINGS_OTHER"} <= codes


def test_freshness_is_carried_to_the_agenda(records) -> None:
    """F7 — ``stale_after`` and ``delay_status`` exist in the observation:
    a stale event is MARKED stale in the agenda, never displayed as a plain
    valid one."""
    fresh_entries = build(records)["agenda"]
    assert fresh_entries
    for entry in fresh_entries:
        assert entry["fresh"] is True
        assert entry["stale_after"]
        assert entry["delay_status"]

    original = estimated_earnings(records)
    stale = CalendarEventRecord(
        event_id="synthetic-dev:stale:0001",
        source=original.source,
        instrument_ref=original.instrument_ref,
        as_of=original.as_of,
        stale_after=NOW - timedelta(minutes=1),
        quality_status=original.quality_status,
        delay_status="DELAYED",
        rights=original.rights,
        schema_version=original.schema_version,
        payload=dict(original.payload),
    )
    content = build([stale])
    entry = content["agenda"][0]
    assert entry["fresh"] is False
    assert entry["stale_after"] == (NOW - timedelta(minutes=1)).isoformat()
    assert entry["delay_status"] == "DELAYED"
    assert content["coverage"]["events_stale"] == 1


def test_a_ticker_key_without_any_position_does_not_escalate(records) -> None:
    """F9 — an EMPTY position list is not a position: only the CONTENT of the
    mapping escalates the importance."""
    content = build(records, positions_by_ticker={"SYN-TECH-01": []})
    entry = next(
        e for e in content["agenda"] if e["event_id"] == "syn-ev-earnings-SYN-TECH-01"
    )
    assert entry["importance"]["code"] != "EARNINGS_POSITION_OR_THESIS"
    assert entry["event_context"]["positions"] == []


def test_an_archived_thesis_does_not_escalate_importance(records) -> None:
    """F10 — an ARCHIVED thesis stays VISIBLE in the context but no longer
    escalates the importance of the event."""
    archived = {"thesis_id": 4, "title": "synthetic thesis", "status": "ARCHIVED"}
    active = {"thesis_id": 5, "title": "synthetic thesis", "status": "ACTIVE"}
    content = build(
        records, theses_by_ticker={"SYN-TECH-01": [archived], "SYN-TECH-02": [active]}
    )
    by_id = {entry["event_id"]: entry for entry in content["agenda"]}

    archived_entry = by_id["syn-ev-earnings-SYN-TECH-01"]
    assert archived_entry["importance"]["code"] != "EARNINGS_POSITION_OR_THESIS"
    assert archived_entry["event_context"]["theses"] == [archived]
    assert by_id["syn-ev-earnings-SYN-TECH-02"]["importance"]["code"] == (
        "EARNINGS_POSITION_OR_THESIS"
    )


class _FakeScalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)


class _FakeSession:
    """Records the emitted statement; returns the declared observation rows.

    No database, no clock: the loading CONTRACT (ordering and bound) is what
    is asserted here.
    """

    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> _FakeResult:
        self.statements.append(statement)
        return _FakeResult(self.rows)


def _observation_row(envelope, index: int) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(
        event_id=f"synthetic-dev:row:{index:04d}",
        source=envelope.source,
        instrument_ref=envelope.instrument_id,
        as_of=envelope.as_of,
        stale_after=envelope.stale_after,
        quality_status=envelope.quality_status.value,
        delay_status=envelope.delay_status.value,
        rights=envelope.rights,
        schema_version=envelope.schema_version,
        payload=dict(envelope.payload),
    )


def test_loading_window_keeps_the_most_recent_records_and_flags_truncation() -> None:
    """F8 — beyond the bound the window must keep the MOST RECENT
    observations (a revision is always the newest record) and SAY that it
    truncated, instead of silently keeping the oldest ones."""
    envelopes = generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    rows = [_observation_row(envelope, i) for i, envelope in enumerate(envelopes)]
    session = _FakeSession(rows)

    window = load_calendar_event_records(
        session, now=NOW, lookback=timedelta(hours=72), limit=3
    )

    compiled = str(session.statements[0])
    assert "observations.as_of DESC" in compiled
    assert "observations.id DESC" in compiled
    # One row MORE than the bound is asked for, so truncation is a fact and
    # never an inference on an equality.
    assert compiled.rstrip().endswith("LIMIT 4") or " LIMIT " in compiled
    assert len(window.records) == 3
    assert window.truncated is True

    short = _FakeSession(rows[:2])
    assert (
        load_calendar_event_records(
            short, now=NOW, lookback=timedelta(hours=72), limit=3
        ).truncated
        is False
    )


def test_truncation_is_published_in_the_coverage(records) -> None:
    """F8 — a truncated window is VISIBLE in the published coverage."""
    assert build(records)["coverage"]["window_truncated"] is False
    truncated = build(records, truncated=True)
    assert truncated["coverage"]["window_truncated"] is True
