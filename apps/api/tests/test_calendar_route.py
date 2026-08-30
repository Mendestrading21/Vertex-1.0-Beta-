"""GET /api/v1/calendar: verbatim relay, window filter, honest empty, 401.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.calendar.build_calendar_content``).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api.auth import require_session
from vertex_api import calendar as calendar_module
from vertex_api.calendar import (
    CALENDAR_FRESHNESS_POLICY,
    CALENDAR_MAX_AGE,
    build_calendar_response,
)
from vertex_api.snapshot_reader import get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
NOW = AS_OF + timedelta(minutes=5)
"""Relay instant of every test: no assertion here depends on real time."""

RULE = {
    "version": "importance_rule/1.0",
    "ranks": [
        {"rank": 1, "code": "MACRO_GLOBAL", "description": "macro"},
        {"rank": 3, "code": "EARNINGS_WATCHLIST", "description": "earnings"},
    ],
}


def event(
    event_id: str,
    *,
    category: str = "EARNINGS",
    status: str = "ESTIMATED",
    when: str = "2026-09-01T15:30:00+00:00",
    revisions: list | None = None,
    previous_values: list | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "category": category,
        "status": status,
        "title": f"[SYNTHETIC] event {event_id}",
        "ticker": "SYN-TECH-01" if category != "MACRO" else None,
        "scope": "TICKER" if category != "MACRO" else "GLOBAL",
        "event_time_utc": when,
        "event_time_local": when,
        "exchange_timezone": "Europe/Zurich",
        "importance": {
            "rank": 3,
            "code": "EARNINGS_WATCHLIST",
            "rule_version": "importance_rule/1.0",
        },
        "revisions": revisions if revisions is not None else [],
        "previous_values": previous_values if previous_values is not None else [],
        "revised": bool(revisions) or bool(previous_values),
        "event_context": {"positions": [], "theses": [], "links": []},
        "synthetic": True,
        "quality": "VALID",
        "fresh": True,
        "stale_after": "2026-08-25T18:00:00+00:00",
        "delay_status": "UNKNOWN",
        "source": "synthetic-dev",
        "rights": "SYNTHETIC",
        "source_event_id": f"synthetic-dev:1:{event_id}",
    }


def calendar_content(
    events: list[dict],
    *,
    agenda_state: str | None = None,
    agenda_state_reason: str | None = None,
    coverage: dict | None = None,
    population: str = "SYNTHETIC",
) -> dict:
    """The exact content shape the worker publishes (counters included)."""
    categories: dict[str, int] = {}
    statuses = {"ESTIMATED": 0, "CONFIRMED": 0}
    for entry in events:
        categories[entry["category"]] = categories.get(entry["category"], 0) + 1
        # A deliberately broken fixture status stays counted apart: the
        # helper never repairs what a test wants the API to refuse.
        statuses[entry["status"]] = statuses.get(entry["status"], 0) + 1
    return {
        "schema_version": "vertex.calendar/1.0",
        "as_of": AS_OF.isoformat(),
        "population": population,
        "agenda_state": agenda_state or ("OK" if events else "EMPTY"),
        "agenda_state_reason": agenda_state_reason,
        "importance_rule": RULE,
        "agenda": events,
        "categories": dict(sorted(categories.items())),
        "statuses": statuses,
        "coverage": coverage
        or {
            "observations_considered": len(events),
            "events_displayed": len(events),
            "events_superseded": 0,
            "events_stale": 0,
            "rejected_records": [],
            "rejected_reasons": {},
            "window_truncated": False,
            "lookback_seconds": 259200,
        },
    }


def snapshot(events: list[dict], version: int = 1, **kwargs) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="calendar",
        key="global",
        version=version,
        content=calendar_content(events, **kwargs),
        content_hash="sha256:" + "a" * 64,
        as_of=AS_OF,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def api(
    app: FastAPI, reader: FakeSnapshotReader, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    # The route owns no clock dependency: the relay's own clock seam is
    # replaced by a FIXED instant so no test depends on the real time.
    monkeypatch.setattr(calendar_module, "_utc_now", lambda: NOW)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_requires_session(client: TestClient) -> None:
    assert client.get("/api/v1/calendar").status_code == 401


def test_empty_state_is_honest_200(api: TestClient) -> None:
    body = api.get("/api/v1/calendar").json()
    assert body["state"] == "empty"
    assert body["agenda"] == []
    assert body["reason"] == "no snapshot published"
    assert body["window"]["applied"] is False
    assert body["window"]["max_days"] == 90


def test_relay_is_verbatim(api: TestClient, reader: FakeSnapshotReader) -> None:
    revisions = [
        {
            "revised_at": "2026-08-24T10:00:00+00:00",
            "previous_status": "ESTIMATED",
            "previous_event_time_utc": "2026-09-01T15:30:00+00:00",
            "reason": "synthetic confirmation",
        }
    ]
    events = [
        event("syn-ev-1", status="CONFIRMED", revisions=revisions),
        event("syn-ev-2", when="2026-09-10T15:30:00+00:00"),
    ]
    reader.snapshots[("calendar", "global")] = snapshot(events)

    body = api.get("/api/v1/calendar").json()
    assert body["state"] == "ok"
    assert body["snapshot_version"] == 1
    assert body["population"] == "SYNTHETIC"
    assert body["importance_rule"] == RULE
    assert body["agenda"] == events
    assert body["window"]["events_total"] == 2
    assert body["window"]["events_in_window"] == 2
    # Distinct labels and preserved revisions relayed exactly.
    assert body["agenda"][0]["status"] == "CONFIRMED"
    assert body["agenda"][0]["revisions"] == revisions
    assert body["agenda"][1]["status"] == "ESTIMATED"
    assert body["agenda"][0]["exchange_timezone"] == "Europe/Zurich"


def test_window_filter_selects_without_altering(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    events = [
        event("syn-ev-1", when="2026-09-01T15:30:00+00:00"),
        event("syn-ev-2", when="2026-10-10T15:30:00+00:00"),
    ]
    reader.snapshots[("calendar", "global")] = snapshot(events)

    body = api.get(
        "/api/v1/calendar",
        params={
            "from": "2026-08-30T00:00:00Z",
            "to": "2026-09-30T00:00:00Z",
        },
    ).json()
    assert [e["event_id"] for e in body["agenda"]] == ["syn-ev-1"]
    assert body["agenda"][0] == events[0]
    assert body["window"]["applied"] is True
    assert body["window"]["events_total"] == 2
    assert body["window"]["events_in_window"] == 1


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"from": "2026-08-30T00:00:00Z"}, "WINDOW_INCOMPLETE"),
        ({"to": "2026-08-30T00:00:00Z"}, "WINDOW_INCOMPLETE"),
        (
            {"from": "2026-09-30T00:00:00Z", "to": "2026-08-30T00:00:00Z"},
            "WINDOW_INVERTED",
        ),
        (
            {"from": "2026-01-01T00:00:00Z", "to": "2026-12-31T00:00:00Z"},
            "WINDOW_TOO_LARGE",
        ),
        (
            {"from": "2026-08-30T00:00:00", "to": "2026-09-30T00:00:00Z"},
            "WINDOW_NAIVE_DATETIME",
        ),
    ],
)
def test_window_violations_are_typed_422(
    api: TestClient, reader: FakeSnapshotReader, params: dict, code: str
) -> None:
    reader.snapshots[("calendar", "global")] = snapshot([event("syn-ev-1")])
    response = api.get("/api/v1/calendar", params=params)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code


def test_invalid_status_in_snapshot_is_refused() -> None:
    broken = snapshot([event("syn-ev-1", status="TENTATIVE")])
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=None, now=NOW)


def test_missing_rule_version_is_refused() -> None:
    broken = snapshot([event("syn-ev-1")])
    broken.content["importance_rule"] = {"ranks": []}
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=None, now=NOW)


# --------------------------------------------------------------------------
# Regression tests of the audited defects (F3 route side, F12, F13).
# --------------------------------------------------------------------------


def test_an_agenda_emptied_by_a_rights_rejection_is_never_reported_ok(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """F3 — page 02: 'une absence de droit affiche le droit manquant, pas un
    agenda vide trompeur'. The relayed state says NOT_ENTITLED and names the
    reason, never ``ok`` with an empty list."""
    reader.snapshots[("calendar", "global")] = snapshot(
        [],
        agenda_state="NOT_ENTITLED",
        agenda_state_reason="every considered record was rejected: rights not usable",
        population="SYNTHETIC",
        coverage={
            "observations_considered": 2,
            "events_displayed": 0,
            "events_superseded": 0,
            "events_stale": 0,
            "rejected_records": [
                {"event_id": "synthetic-dev:1:ev0000", "reason": "rights_not_usable"},
                {"event_id": "synthetic-dev:1:ev0001", "reason": "rights_not_usable"},
            ],
            "rejected_reasons": {"rights_not_usable": 2},
            "window_truncated": False,
            "lookback_seconds": 259200,
        },
    )

    response = api.get("/api/v1/calendar")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "not_entitled"
    assert body["agenda"] == []
    assert body["reason"] == (
        "every considered record was rejected: rights not usable"
    )
    # The published facts stay relayed: the missing right is READABLE.
    assert body["coverage"]["rejected_reasons"] == {"rights_not_usable": 2}
    assert body["population"] == "SYNTHETIC"


def test_an_agenda_emptied_by_invalid_records_is_never_reported_ok(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """F3 — same honesty for a fully rejected (non-rights) population."""
    reader.snapshots[("calendar", "global")] = snapshot(
        [],
        agenda_state="REJECTED",
        agenda_state_reason="every considered record was rejected",
        coverage={
            "observations_considered": 1,
            "events_displayed": 0,
            "events_superseded": 0,
            "events_stale": 0,
            "rejected_records": [
                {"event_id": "synthetic-dev:1:ev0000", "reason": "invalid_category"}
            ],
            "rejected_reasons": {"invalid_category": 1},
            "window_truncated": False,
            "lookback_seconds": 259200,
        },
    )
    body = api.get("/api/v1/calendar").json()
    assert body["state"] == "rejected"
    assert body["reason"] == "every considered record was rejected"


def test_an_unknown_agenda_state_is_refused() -> None:
    """F3 — an unreadable state fails CLOSED instead of being shown ok."""
    broken = snapshot([event("syn-ev-1")])
    broken.content["agenda_state"] = "PROBABLY_FINE"
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=None, now=NOW)


def test_a_naive_event_time_is_refused_with_and_without_window() -> None:
    """F12 — one snapshot, ONE behaviour: an unusable ``event_time_utc`` is
    refused whether or not a window is requested."""
    broken = snapshot([event("syn-ev-1", when="2026-09-01T15:30:00")])
    window = (
        datetime(2026, 8, 1, tzinfo=timezone.utc),
        datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=None, now=NOW)
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=window, now=NOW)


def test_window_counters_do_not_contradict_the_displayed_list(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """F13 — under a window the response carries counters of the DISPLAYED
    list; the snapshot-wide totals stay published, explicitly separated."""
    events = [
        event("syn-ev-1", when="2026-09-01T15:30:00+00:00"),
        event(
            "syn-ev-2",
            category="MACRO",
            status="CONFIRMED",
            when="2026-10-10T15:30:00+00:00",
        ),
    ]
    reader.snapshots[("calendar", "global")] = snapshot(events)

    body = api.get(
        "/api/v1/calendar",
        params={"from": "2026-08-30T00:00:00Z", "to": "2026-09-30T00:00:00Z"},
    ).json()

    assert [e["event_id"] for e in body["agenda"]] == ["syn-ev-1"]
    # The counters of what is REALLY displayed.
    assert body["window"]["categories"] == {"EARNINGS": 1}
    assert body["window"]["statuses"] == {"ESTIMATED": 1, "CONFIRMED": 0}
    assert body["window"]["events_in_window"] == 1
    # The snapshot-wide totals remain published and unchanged.
    assert body["categories"] == {"EARNINGS": 1, "MACRO": 1}
    assert body["statuses"] == {"ESTIMATED": 1, "CONFIRMED": 1}
    assert body["window"]["events_total"] == 2


def test_window_counters_without_window_match_the_whole_agenda(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """F13 — with no window the displayed counters equal the published ones."""
    events = [event("syn-ev-1"), event("syn-ev-2", status="CONFIRMED")]
    reader.snapshots[("calendar", "global")] = snapshot(events)
    body = api.get("/api/v1/calendar").json()
    assert body["window"]["categories"] == body["categories"]
    assert body["window"]["statuses"] == body["statuses"]


# --------------------------------------------------------------------------
# Regression tests of the adversarial RE-AUDIT (P1-6, P2-6 relay, P2-7).
# Availability of a legitimate page and honesty of the served state are the
# promises under test.
# --------------------------------------------------------------------------


def test_a_snapshot_predating_the_state_contract_is_served_degraded_not_500(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """P1-6 — publication is publish-if-changed: a snapshot published BEFORE
    ``agenda_state`` existed is never republished until a new observation
    arrives. Refusing it would keep page 02 in a permanent 500, so it is
    served DEGRADED with its cause — and never as ``ok``."""
    legacy = snapshot([event("syn-ev-1"), event("syn-ev-2", status="CONFIRMED")])
    legacy.content.pop("agenda_state")
    legacy.content.pop("agenda_state_reason")
    reader.snapshots[("calendar", "global")] = legacy

    response = api.get("/api/v1/calendar")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "degraded"
    assert body["state"] != "ok"
    assert body["reason"] == (
        "state field missing: snapshot predates the current agenda_state "
        "contract"
    )
    # The published events stay AVAILABLE and verbatim: the missing field
    # degrades the STATE, not the agenda.
    assert [entry["event_id"] for entry in body["agenda"]] == [
        "syn-ev-1",
        "syn-ev-2",
    ]
    assert body["window"]["events_total"] == 2
    assert body["snapshot_version"] == 1


def test_a_legacy_snapshot_keeps_failing_closed_on_its_events(
    reader: FakeSnapshotReader,
) -> None:
    """P1-6 — backward compatibility covers the ABSENT state field ONLY: an
    unusable event of the same legacy snapshot is still refused."""
    legacy = snapshot([event("syn-ev-1", status="TENTATIVE")])
    legacy.content.pop("agenda_state")
    with pytest.raises(SnapshotContentError):
        build_calendar_response(legacy, window=None, now=NOW)


def test_a_window_that_selects_nothing_is_not_reported_ok(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """P2-7 — a window emptying the agenda must not be served ``ok`` with an
    empty list and no reason: the served state carries the distinction, not
    only the counters."""
    events = [
        event("syn-ev-1", when="2026-09-01T15:30:00+00:00"),
        event("syn-ev-2", when="2026-09-10T15:30:00+00:00"),
    ]
    reader.snapshots[("calendar", "global")] = snapshot(events)

    body = api.get(
        "/api/v1/calendar",
        params={"from": "2026-11-01T00:00:00Z", "to": "2026-11-30T00:00:00Z"},
    ).json()

    assert body["agenda"] == []
    assert body["state"] == "empty_window"
    assert body["reason"] == (
        "the requested window selects none of the 2 published events "
        "(published agenda_state: OK)"
    )
    # The published totals stay readable: the events EXIST, out of window.
    assert body["window"]["events_total"] == 2
    assert body["window"]["events_in_window"] == 0
    assert body["window"]["applied"] is True


def test_a_window_selecting_nothing_never_hides_a_non_ok_state(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """P2-7 — the window state never overwrites a worker verdict: a rights
    rejection stays ``not_entitled`` with its own reason."""
    reader.snapshots[("calendar", "global")] = snapshot(
        [],
        agenda_state="NOT_ENTITLED",
        agenda_state_reason="every considered record was rejected: "
        "rights_not_usable x2",
    )
    body = api.get(
        "/api/v1/calendar",
        params={"from": "2026-11-01T00:00:00Z", "to": "2026-11-30T00:00:00Z"},
    ).json()
    assert body["state"] == "not_entitled"
    assert body["reason"] == (
        "every considered record was rejected: rights_not_usable x2"
    )


def test_a_wholly_stale_agenda_is_relayed_as_stale(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """P2-6 — the worker owns the verdict: a published ``STALE`` agenda is
    relayed as ``stale`` with its reason, never flattened into ``ok``."""
    stale_event = event("syn-ev-1")
    stale_event["fresh"] = False
    # The fixture is COHERENT with the verdict it publishes: the event is
    # really past its ``stale_after`` at the relay instant.
    stale_event["stale_after"] = (NOW - timedelta(minutes=1)).isoformat()
    reader.snapshots[("calendar", "global")] = snapshot(
        [stale_event],
        agenda_state="STALE",
        agenda_state_reason="every displayed event is stale (1/1)",
    )
    body = api.get("/api/v1/calendar").json()
    assert body["state"] == "stale"
    assert body["reason"] == "every displayed event is stale (1/1)"
    assert [entry["event_id"] for entry in body["agenda"]] == ["syn-ev-1"]
    assert body["agenda"][0]["fresh"] is False


def test_every_state_the_worker_can_publish_is_mapped() -> None:
    """P1-6 (root cause) — the relay must know EVERY state the worker can
    publish: an unmapped one would fail closed at runtime and take page 02
    down, exactly like the missing field did."""
    from vertex_worker.calendar import AGENDA_STATES

    from vertex_api.calendar import AGENDA_STATE_TO_RESPONSE_STATE

    assert set(AGENDA_STATES) == set(AGENDA_STATE_TO_RESPONSE_STATE)


# --------------------------------------------------------------------------
# Regression tests of the THIRD adversarial audit (P1-F, P1-E).
# --------------------------------------------------------------------------


def legacy_event(event_id: str, **kwargs) -> dict:
    """One agenda entry in the FIRST published worker format (dafadb9).

    That builder published neither ``previous_values`` (its trace of the
    superseded records did not exist yet) nor the freshness triplet
    (``fresh``/``stale_after``/``delay_status``) nor the version state; only
    ``revisions`` and the value fields existed. Snapshots in that exact shape
    are still the CURRENT row of a deployment that has not observed a new
    calendar event since, because publication is publish-if-changed.
    """
    entry = event(event_id, **kwargs)
    for absent in (
        "previous_values",
        "fresh",
        "stale_after",
        "delay_status",
    ):
        entry.pop(absent, None)
    return entry


def test_a_snapshot_in_the_first_worker_format_is_served_degraded_not_500(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    """P1-F — the snapshot the FIRST calendar worker published carries no
    ``agenda_state`` and no ``previous_values``. Publication being
    publish-if-changed, refusing it leaves page 02 in a PERMANENT 500 until
    the next calendar observation. It is served degraded, with its cause."""
    legacy = snapshot([legacy_event("syn-ev-1"), legacy_event("syn-ev-2")])
    legacy.content.pop("agenda_state")
    legacy.content.pop("agenda_state_reason")
    reader.snapshots[("calendar", "global")] = legacy

    response = api.get("/api/v1/calendar")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "degraded"
    assert [entry["event_id"] for entry in body["agenda"]] == [
        "syn-ev-1",
        "syn-ev-2",
    ]
    assert body["window"]["events_total"] == 2
    # Both causes are NAMED, never silently swallowed.
    assert "agenda_state" in body["reason"]
    assert "previous_values" in body["reason"]


@pytest.mark.parametrize("field", ["previous_values", "revisions"])
def test_an_absent_event_field_is_degraded_never_a_500(
    api: TestClient, reader: FakeSnapshotReader, field: str
) -> None:
    """P1-F — absence is a KNOWN older contract: the readable agenda is
    served degraded with its cause, exactly like an absent ``agenda_state``,
    instead of taking the page down."""
    entry = event("syn-ev-1")
    entry.pop(field)
    reader.snapshots[("calendar", "global")] = snapshot([entry])

    response = api.get("/api/v1/calendar")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "degraded"
    assert field in body["reason"]
    assert [e["event_id"] for e in body["agenda"]] == ["syn-ev-1"]


@pytest.mark.parametrize("field", ["previous_values", "revisions"])
@pytest.mark.parametrize("value", ["", 0, {}, "[]"])
def test_an_invalid_event_field_value_is_still_refused(
    field: str, value: object
) -> None:
    """P1-F — the symmetric half of the rule: a PRESENT but unreadable value
    is a claim the relay cannot verify, and keeps failing closed."""
    broken = snapshot([event("syn-ev-1")])
    broken.content["agenda"][0][field] = value
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=None, now=NOW)


def test_an_agenda_past_its_budget_is_served_stale_not_ok(
    reader: FakeSnapshotReader,
) -> None:
    """P1-E — ``fresh`` and ``agenda_state`` are computed at CONSTRUCTION and
    frozen in the snapshot; publish-if-changed means no recomputation ever
    happens. Without a relay-side budget a three-day-old agenda is served
    ``ok``. Past the budget the relay serves ``stale`` with age and cause."""
    published = snapshot([event("syn-ev-1")])
    late = AS_OF + CALENDAR_MAX_AGE + timedelta(seconds=1)

    response = build_calendar_response(published, window=None, now=late)

    assert response.state == "stale"
    assert response.state != "ok"
    assert response.reason is not None
    assert str(int((late - AS_OF).total_seconds())) in response.reason
    assert str(int(CALENDAR_MAX_AGE.total_seconds())) in response.reason
    assert CALENDAR_FRESHNESS_POLICY in response.reason
    # The content stays AVAILABLE: the budget qualifies it, it never hides it.
    assert [entry["event_id"] for entry in response.agenda] == ["syn-ev-1"]


def test_a_snapshot_inside_its_budget_stays_ok() -> None:
    """P1-E — the bound is not a trap: at EXACTLY the budget a snapshot whose
    events are still inside their own ``stale_after`` is served ok."""
    limit = AS_OF + CALENDAR_MAX_AGE
    entry = event("syn-ev-1")
    entry["stale_after"] = (limit + timedelta(hours=1)).isoformat()
    response = build_calendar_response(snapshot([entry]), window=None, now=limit)
    assert response.state == "ok"
    assert response.reason is None
    assert response.agenda[0]["fresh"] is True


def test_the_fresh_flag_is_never_a_frozen_lie() -> None:
    """P1-E — ``fresh`` is a claim ABOUT THE RELAY CLOCK. Relayed verbatim it
    keeps asserting ``true`` days after its ``stale_after``. It is recomputed
    at the relay from ``stale_after`` and the server clock."""
    entry = event("syn-ev-1")
    entry["fresh"] = True
    entry["stale_after"] = "2026-08-25T18:00:00+00:00"
    published = snapshot([entry])

    before = build_calendar_response(
        published,
        window=None,
        now=datetime(2026, 8, 25, 17, 0, tzinfo=timezone.utc),
    )
    assert before.agenda[0]["fresh"] is True

    after = build_calendar_response(
        published,
        window=None,
        now=datetime(2026, 8, 25, 19, 0, tzinfo=timezone.utc),
    )
    assert after.agenda[0]["fresh"] is False
    # ...and the published ``stale_after`` stays relayed verbatim beside it.
    assert after.agenda[0]["stale_after"] == "2026-08-25T18:00:00+00:00"


def test_an_event_without_stale_after_never_claims_freshness() -> None:
    """P1-E — an older contract publishes no ``stale_after``: the relay
    cannot verify ``fresh``, so it REMOVES the unverifiable claim instead of
    relaying it."""
    entry = event("syn-ev-1")
    entry["fresh"] = True
    entry.pop("stale_after")
    published = snapshot([entry])

    response = build_calendar_response(published, window=None, now=NOW)
    assert "fresh" not in response.agenda[0]
    assert response.state == "degraded"
    assert "stale_after" in (response.reason or "")


def test_an_agenda_whose_every_served_event_is_stale_is_not_ok() -> None:
    """P1-E — the worker's ``STALE`` verdict is frozen too: an agenda
    published ``OK`` whose events have ALL passed their ``stale_after`` since
    is served ``stale``, never ``ok`` with false ``fresh`` flags."""
    entry = event("syn-ev-1")
    entry["stale_after"] = "2026-08-25T18:00:00+00:00"
    published = snapshot([entry])

    response = build_calendar_response(
        published,
        window=None,
        now=datetime(2026, 8, 25, 19, 0, tzinfo=timezone.utc),
    )
    assert response.state == "stale"
    assert response.agenda[0]["fresh"] is False
    assert response.reason is not None


def test_a_snapshot_dated_in_the_future_is_refused() -> None:
    """P1-E — a negative age is a temporal incoherence, never 'very fresh'."""
    published = snapshot([event("syn-ev-1")])
    with pytest.raises(SnapshotContentError):
        build_calendar_response(
            published, window=None, now=AS_OF - timedelta(seconds=1)
        )


def test_the_freshness_budget_comes_from_the_versioned_registry() -> None:
    """P1-E — the bound is the registry's own versioned value, not a number
    invented in the relay."""
    from vertex_core.data.freshness import get_freshness_policy

    policy = get_freshness_policy(CALENDAR_FRESHNESS_POLICY)
    assert CALENDAR_MAX_AGE == timedelta(seconds=policy.ttl_closed_seconds)


def test_a_naive_relay_clock_is_refused() -> None:
    """P1-E — a naive clock would be read as local time and silently shift
    every age and every recomputed ``fresh`` flag."""
    published = snapshot([event("syn-ev-1")])
    with pytest.raises(ValueError):
        build_calendar_response(
            published, window=None, now=datetime(2026, 8, 25, 12, 5)
        )
