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
        "revised": bool(revisions),
        "event_context": {"positions": [], "theses": [], "links": []},
        "synthetic": True,
        "quality": "VALID",
        "source": "synthetic-dev",
        "rights": "SYNTHETIC",
        "source_event_id": f"synthetic-dev:1:{event_id}",
    }


def calendar_content(events: list[dict]) -> dict:
    return {
        "schema_version": "vertex.calendar/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "importance_rule": RULE,
        "agenda": events,
        "categories": {"EARNINGS": len(events)},
        "statuses": {"ESTIMATED": len(events), "CONFIRMED": 0},
        "coverage": {
            "observations_considered": len(events),
            "events_displayed": len(events),
            "events_superseded": 0,
            "rejected_records": [],
            "lookback_seconds": 259200,
        },
    }


def snapshot(events: list[dict], version: int = 1) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="calendar",
        key="global",
        version=version,
        content=calendar_content(events),
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
