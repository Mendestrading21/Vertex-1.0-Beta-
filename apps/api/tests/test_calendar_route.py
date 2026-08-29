"""GET /api/v1/calendar: verbatim relay, window filter, honest empty, 401.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.calendar.build_calendar_content``).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api.auth import require_session
from vertex_api.calendar import build_calendar_response
from vertex_api.snapshot_reader import get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)

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
def api(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
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
        build_calendar_response(broken, window=None)


def test_missing_rule_version_is_refused() -> None:
    broken = snapshot([event("syn-ev-1")])
    broken.content["importance_rule"] = {"ranks": []}
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=None)


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
        build_calendar_response(broken, window=None)


def test_a_naive_event_time_is_refused_with_and_without_window() -> None:
    """F12 — one snapshot, ONE behaviour: an unusable ``event_time_utc`` is
    refused whether or not a window is requested."""
    broken = snapshot([event("syn-ev-1", when="2026-09-01T15:30:00")])
    window = (
        datetime(2026, 8, 1, tzinfo=timezone.utc),
        datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=None)
    with pytest.raises(SnapshotContentError):
        build_calendar_response(broken, window=window)


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
