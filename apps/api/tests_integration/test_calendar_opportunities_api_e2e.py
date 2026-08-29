"""Calendar and Opportunities routes against real PostgreSQL and passkey auth.

No dependency override anywhere: SYNTHETIC calendar events, daily bars and
option chains are ingested through ``ingest_envelope``, a bounded run of the
REAL worker publishes ``calendar/global`` and ``opportunities/global``, and
both snapshots are read back through the protected API with a real WebAuthn
session cookie.

Hard proofs:

- the served content equals the PUBLISHED snapshot verbatim (agenda,
  categories, statuses, coverage, importance rule / candidates, ordering,
  profile reference, exclusion reasons) — the API relays and computes
  nothing;
- the optional ``from``/``to`` display window SELECTS already-published
  events and its bound is enforced fail-closed (incomplete, naive,
  inverted and over-90-days windows are typed 422s);
- with nothing published both routes answer an HONEST empty state (200,
  ``state = "empty"``, explicit reason) instead of inventing content.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from soft_passkey import SoftPasskey, login_passkey, register_passkey
from vertex_core.synthetic import (
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.calendar import SNAPSHOT_KIND_CALENDAR
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.opportunities import SNAPSHOT_KIND_OPPORTUNITIES
from vertex_worker.runner import WorkerRunner

NOW = datetime.now(timezone.utc).replace(microsecond=0)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 20260825

MAX_WINDOW_DAYS = 90


@pytest.fixture()
def authenticated(client: TestClient, passkey: SoftPasskey) -> TestClient:
    register_passkey(client, passkey)
    assert login_passkey(client, passkey).status_code == 200
    return client


@pytest.fixture()
def published(database_url: str) -> Iterator[dict[str, Any]]:
    """Seed SYNTHETIC observations and run the REAL worker to completion."""
    engine = create_engine(database_url)

    def factory() -> Session:
        return Session(engine)

    try:
        with factory() as session:
            for envelope in (
                *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
                *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
                *generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME),
            ):
                ingest_envelope(session, envelope)
            session.commit()

        clock = lambda: datetime.now(timezone.utc)  # noqa: E731
        runner = WorkerRunner(
            session_factory=factory,
            registry=build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG),
            poll_interval_seconds=0.05,
            clock=clock,
        )
        runner.drain(max_batches=80)
        stats = runner.stats()
        assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0
        with factory() as session:
            remaining = session.execute(
                select(func.count())
                .select_from(OutboxMessage)
                .where(OutboxMessage.status != OutboxStatus.DONE.value)
            ).scalar_one()
            assert remaining == 0
            calendar = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_CALENDAR, key="global"
            )
            opportunities = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_OPPORTUNITIES, key="global"
            )
        assert calendar is not None and opportunities is not None
        yield {"calendar": calendar, "opportunities": opportunities}
    finally:
        engine.dispose()


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class TestCalendarRoute:
    def test_requires_a_real_session(self, client: TestClient) -> None:
        response = client.get("/api/v1/calendar")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_no_snapshot_is_honest_empty_200(self, authenticated: TestClient) -> None:
        response = authenticated.get("/api/v1/calendar")
        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "empty"
        assert body["agenda"] == []
        assert body["as_of"] is None
        assert body["snapshot_version"] is None
        assert body["population"] is None
        assert body["importance_rule"] is None
        assert body["categories"] is None
        assert body["statuses"] is None
        assert body["coverage"] is None
        assert body["reason"] == "no snapshot published"
        # ``categories``/``statuses`` count the list ACTUALLY served (F13 fix):
        # with no snapshot the served list is empty, so no category is claimed
        # and every status counter is zero.
        assert body["window"] == {
            "applied": False,
            "from_utc": None,
            "to_utc": None,
            "max_days": MAX_WINDOW_DAYS,
            "events_total": 0,
            "events_in_window": 0,
            "categories": {},
            "statuses": {"ESTIMATED": 0, "CONFIRMED": 0},
        }
        assert not any(body["window"]["statuses"].values())

    def test_served_agenda_is_the_published_snapshot_verbatim(
        self, authenticated: TestClient, published: dict[str, Any]
    ) -> None:
        snapshot = published["calendar"]
        content = snapshot.content

        response = authenticated.get("/api/v1/calendar")
        assert response.status_code == 200
        body = response.json()

        assert body["state"] == "ok"
        assert body["snapshot_version"] == snapshot.version
        assert datetime.fromisoformat(
            body["as_of"].replace("Z", "+00:00")
        ) == datetime.fromisoformat(content["as_of"])
        assert body["population"] == content["population"] == "SYNTHETIC"
        # Verbatim relay of every published block.
        assert body["agenda"] == content["agenda"]
        assert body["importance_rule"] == content["importance_rule"]
        assert body["categories"] == content["categories"]
        assert body["statuses"] == content["statuses"]
        assert body["coverage"] == content["coverage"]
        assert body["reason"] is None
        assert body["window"]["applied"] is False
        assert body["window"]["events_total"] == len(content["agenda"])
        assert body["window"]["events_in_window"] == len(content["agenda"])
        assert body["window"]["max_days"] == MAX_WINDOW_DAYS

        # Distinct ESTIMATED/CONFIRMED labels and preserved revisions survive
        # the whole chain untouched.
        statuses = {event["status"] for event in body["agenda"]}
        assert statuses <= {"ESTIMATED", "CONFIRMED"}
        assert "ESTIMATED" in statuses and "CONFIRMED" in statuses
        revised = [event for event in body["agenda"] if event["revised"]]
        assert revised
        for event in revised:
            assert event["revisions"]
            assert all(
                entry["previous_status"] == "ESTIMATED" for entry in event["revisions"]
            )

    def test_bounded_window_selects_without_altering(
        self, authenticated: TestClient, published: dict[str, Any]
    ) -> None:
        agenda = published["calendar"].content["agenda"]
        instants = [
            datetime.fromisoformat(event["event_time_utc"]) for event in agenda
        ]
        # Bounds strictly BETWEEN two published instants: the selection can
        # never depend on a boundary coincidence (no clock sensitivity).
        distinct = sorted(set(instants))
        assert len(distinct) > 1
        start = distinct[0]
        end = start + (distinct[1] - start) / 2
        expected = [
            event
            for event, instant in zip(agenda, instants)
            if start <= instant <= end
        ]
        assert 0 < len(expected) < len(agenda)  # a real, strict selection

        response = authenticated.get(
            "/api/v1/calendar", params={"from": _iso(start), "to": _iso(end)}
        )
        assert response.status_code == 200
        body = response.json()
        # The selection returns the published events UNCHANGED.
        assert body["agenda"] == expected
        assert body["window"]["applied"] is True
        assert body["window"]["events_total"] == len(agenda)
        assert body["window"]["events_in_window"] == len(expected)
        assert datetime.fromisoformat(
            body["window"]["from_utc"].replace("Z", "+00:00")
        ) == start
        assert datetime.fromisoformat(
            body["window"]["to_utc"].replace("Z", "+00:00")
        ) == end
        # Everything else stays the published snapshot (counts are NOT
        # recomputed over the selection: the totals remain honest).
        assert body["categories"] == published["calendar"].content["categories"]
        assert body["statuses"] == published["calendar"].content["statuses"]

        # A window with no event is an empty selection, never an invention.
        far = max(instants) + timedelta(days=1)
        empty = authenticated.get(
            "/api/v1/calendar",
            params={"from": _iso(far), "to": _iso(far + timedelta(days=1))},
        )
        assert empty.status_code == 200
        assert empty.json()["agenda"] == []
        assert empty.json()["window"]["events_in_window"] == 0
        assert empty.json()["state"] == "ok"

    def test_window_violations_are_typed_422(
        self, authenticated: TestClient, published: dict[str, Any]
    ) -> None:
        start = NOW
        # 1. one bound without the other.
        incomplete = authenticated.get(
            "/api/v1/calendar", params={"from": _iso(start)}
        )
        assert incomplete.status_code == 422
        assert incomplete.json()["detail"]["code"] == "WINDOW_INCOMPLETE"

        # 2. naive datetimes.
        naive = authenticated.get(
            "/api/v1/calendar",
            params={
                "from": start.replace(tzinfo=None).isoformat(),
                "to": (start + timedelta(days=1)).replace(tzinfo=None).isoformat(),
            },
        )
        assert naive.status_code == 422
        assert naive.json()["detail"]["code"] == "WINDOW_NAIVE_DATETIME"

        # 3. inverted bounds.
        inverted = authenticated.get(
            "/api/v1/calendar",
            params={"from": _iso(start), "to": _iso(start - timedelta(days=1))},
        )
        assert inverted.status_code == 422
        assert inverted.json()["detail"]["code"] == "WINDOW_INVERTED"

        # 4. beyond the declared bound — rejected, never truncated silently.
        too_large = authenticated.get(
            "/api/v1/calendar",
            params={
                "from": _iso(start),
                "to": _iso(start + timedelta(days=MAX_WINDOW_DAYS, seconds=1)),
            },
        )
        assert too_large.status_code == 422
        assert too_large.json()["detail"]["code"] == "WINDOW_TOO_LARGE"

        # The bound itself is INCLUSIVE and accepted.
        at_bound = authenticated.get(
            "/api/v1/calendar",
            params={
                "from": _iso(start),
                "to": _iso(start + timedelta(days=MAX_WINDOW_DAYS)),
            },
        )
        assert at_bound.status_code == 200
        assert at_bound.json()["window"]["applied"] is True


class TestOpportunitiesRoute:
    def test_requires_a_real_session(self, client: TestClient) -> None:
        response = client.get("/api/v1/opportunities")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_no_snapshot_is_honest_empty_200(self, authenticated: TestClient) -> None:
        response = authenticated.get("/api/v1/opportunities")
        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "empty"
        assert body["content"] is None
        assert body["as_of"] is None
        assert body["snapshot_version"] is None
        assert body["reason"] == "no snapshot published"

    def test_served_candidates_are_the_published_snapshot_verbatim(
        self, authenticated: TestClient, published: dict[str, Any]
    ) -> None:
        snapshot = published["opportunities"]
        content = snapshot.content

        response = authenticated.get("/api/v1/opportunities")
        assert response.status_code == 200
        body = response.json()

        assert body["state"] == "ok"
        assert body["snapshot_version"] == snapshot.version
        assert body["reason"] is None
        assert datetime.fromisoformat(
            body["as_of"].replace("Z", "+00:00")
        ) == datetime.fromisoformat(content["as_of"])
        # Whole-content verbatim relay: nothing added, nothing recomputed.
        assert body["content"] == content

        served = body["content"]
        assert served["profile_ref"]["id"] == content["profile_ref"]["id"]
        assert served["profile_ref"]["version"] == content["profile_ref"]["version"]
        assert served["ordering"]["method"] == "lexicographic"
        assert served["exclusion_reasons"] == content["exclusion_reasons"]

        # The relayed groups keep the page's core invariant.
        for candidate in served["qualified"]:
            assert candidate["advice"]["status"] in ("OBSERVE", "REVIEW", "QUALIFIED")
        for candidate in served["excluded"]:
            assert candidate["advice"]["status"] in (
                "BLOCKED",
                "INSUFFICIENT_DATA",
            )
        assert (
            served["coverage"]["qualified_count"]
            + served["coverage"]["excluded_count"]
            == served["coverage"]["universe_size"]
        )
        assert sum(served["exclusion_reasons"].values()) == len(served["excluded"])
