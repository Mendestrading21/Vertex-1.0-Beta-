"""Follow-up routes against real PostgreSQL, passkey auth, CSRF and worker.

No dependency override anywhere: WebAuthn session cookie, CSRF double-submit
header, the real theses repository (append-only revisions, idempotency by
client key), the real outbox and a bounded REAL worker run publishing the
``review_queue/global`` snapshot read back through
``GET /api/v1/follow-up/queue``. All data is SYNTHETIC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from soft_passkey import SoftPasskey, login_passkey, register_passkey
from vertex_core.contracts import DataEnvelope, canonical_json_hash
from vertex_core.contracts.enums import DelayStatus, EnvelopeQuality
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage, ThesisRevision
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

CSRF_HEADER = "X-Vertex-CSRF"
CSRF_COOKIE = "vertex_csrf"

TOPIC_REVIEW_QUEUE = "review_queue.refresh"
TICKER = "SYN-TECH-01"

NOW = datetime.now(timezone.utc).replace(microsecond=0)
PAST_DUE = (NOW - timedelta(days=2)).isoformat()
OLDER_DUE = (NOW - timedelta(days=6)).isoformat()

THESIS_PAYLOAD = {
    "title": "SYNTHETIC thesis on the synthetic tech sector",
    "hypotheses": "[SYNTHETIC] breadth holds above the coverage threshold",
    "invalidation": "[SYNTHETIC] breadth below 40% for five sessions",
    "idempotency_key": "e2e-thesis-key-1",
    "instrument": {"ticker": TICKER},
    "review_due_at": PAST_DUE,
}


@pytest.fixture()
def authenticated(client: TestClient, passkey: SoftPasskey) -> TestClient:
    register_passkey(client, passkey)
    assert login_passkey(client, passkey).status_code == 200
    return client


@pytest.fixture()
def db_session(database_url: str) -> Iterator[Session]:
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture()
def drain_worker(database_url: str):
    """Bounded REAL worker run over the same database (no daemon thread)."""
    engine = create_engine(database_url)

    def factory() -> Session:
        return Session(engine)

    def drain() -> None:
        runner = WorkerRunner(
            session_factory=factory,
            registry=build_registry(
                clock=lambda: datetime.now(timezone.utc),
                fusion_config=DEV_SYNTHETIC_CONFIG,
            ),
            poll_interval_seconds=0.05,
            clock=lambda: datetime.now(timezone.utc),
        )
        runner.drain(max_batches=30)
        stats = runner.stats()
        assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0
        with factory() as session:
            remaining = session.execute(
                select(func.count())
                .select_from(OutboxMessage)
                .where(OutboxMessage.status != OutboxStatus.DONE.value)
            ).scalar_one()
        assert remaining == 0

    try:
        yield drain
    finally:
        engine.dispose()


def _csrf(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE)
    assert token
    return {CSRF_HEADER: token}


def _review_queue_jobs(session: Session) -> int:
    return session.execute(
        select(func.count())
        .select_from(OutboxMessage)
        .where(OutboxMessage.topic == TOPIC_REVIEW_QUEUE)
    ).scalar_one()


def _revision_count(session: Session, thesis_id: int) -> int:
    return session.execute(
        select(func.count())
        .select_from(ThesisRevision)
        .where(ThesisRevision.thesis_id == thesis_id)
    ).scalar_one()


def _news_envelope(event_id: str, *, received_at: datetime) -> DataEnvelope[dict]:
    payload = {
        "title": f"[SYNTHETIC] contradictory news about {TICKER} ({event_id})",
        "entities": [TICKER],
        "note": "[SYNTHETIC] generated fixture, never real market information",
    }
    return DataEnvelope[dict](
        event_id=event_id,
        schema_version="synthetic-news/1.0",
        source="synthetic-dev",
        source_event_id=f"native-{event_id}",
        instrument_id=TICKER,
        observed_at=received_at - timedelta(minutes=1),
        published_at=received_at - timedelta(minutes=1),
        received_at=received_at,
        as_of=received_at,
        stale_after=received_at + timedelta(hours=6),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.UNKNOWN,
        rights="SYNTHETIC",
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


def test_mutations_without_csrf_are_generic_401(authenticated: TestClient) -> None:
    response = authenticated.post("/api/v1/theses", json=THESIS_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_thesis_write_refreshes_queue_and_new_information_never_writes(
    authenticated: TestClient, db_session: Session, drain_worker
) -> None:
    # --- POST /theses: write + refresh enqueue in the SAME transaction -----
    created = authenticated.post(
        "/api/v1/theses", json=THESIS_PAYLOAD, headers=_csrf(authenticated)
    )
    assert created.status_code == 201, created.text
    body = created.json()
    thesis_id = body["thesis_id"]
    assert body["created"] is True and body["refresh_enqueued"] is True
    assert _review_queue_jobs(db_session) == 1

    # Replaying the SAME idempotency_key writes nothing and enqueues nothing.
    replay = authenticated.post(
        "/api/v1/theses", json=THESIS_PAYLOAD, headers=_csrf(authenticated)
    )
    assert replay.status_code == 200
    assert replay.json() == {
        "thesis_id": thesis_id,
        "revision_id": body["revision_id"],
        "created": False,
        "refresh_enqueued": False,
    }
    db_session.expire_all()
    assert _review_queue_jobs(db_session) == 1
    assert _revision_count(db_session, thesis_id) == 1  # the CREATED revision

    # A second thesis, longer overdue: must rank FIRST in the due queue.
    older = authenticated.post(
        "/api/v1/theses",
        json={
            **THESIS_PAYLOAD,
            "title": "SYNTHETIC older thesis",
            "idempotency_key": "e2e-thesis-key-2",
            "review_due_at": OLDER_DUE,
        },
        headers=_csrf(authenticated),
    )
    assert older.status_code == 201
    older_id = older.json()["thesis_id"]

    # --- drain -> GET /follow-up/queue --------------------------------------
    drain_worker()
    queue = authenticated.get("/api/v1/follow-up/queue")
    assert queue.status_code == 200
    content = queue.json()["content"]
    assert content["schema_version"] == "vertex.review-queue/1.0"
    assert content["populations"]["theses"] == "USER_DECLARED"
    states = {entry["thesis"]["id"]: entry for entry in content["theses"]}
    assert states[thesis_id]["state"]["status"] == "ACTIVE"
    assert states[thesis_id]["state"]["is_due"] is True
    # Documented lexicographic ordering: due the longest first.
    assert [entry["thesis_id"] for entry in content["due"]] == [older_id, thesis_id]
    assert content["due"][0]["rank"] == 1

    # --- revision: 10 replays of one idempotency key => exactly ONE row ----
    revision_payload = {
        "action": "REVIEWED",
        "idempotency_key": "e2e-review-key-1",
        "note": "[SYNTHETIC] reviewed during the e2e run",
    }
    statuses: list[int] = []
    revision_ids: set[int] = set()
    for _ in range(10):
        response = authenticated.post(
            f"/api/v1/theses/{thesis_id}/revisions",
            json=revision_payload,
            headers=_csrf(authenticated),
        )
        statuses.append(response.status_code)
        revision_body = response.json()
        revision_ids.add(revision_body["revision_id"])
        assert revision_body["created"] is (response.status_code == 201)
    assert statuses == [201] + [200] * 9
    assert len(revision_ids) == 1  # every replay returns the SAME revision
    db_session.expire_all()
    assert _revision_count(db_session, thesis_id) == 2  # CREATED + REVIEWED

    drain_worker()
    reviewed = authenticated.get("/api/v1/follow-up/queue").json()["content"]
    reviewed_entry = next(
        entry for entry in reviewed["theses"] if entry["thesis"]["id"] == thesis_id
    )
    assert reviewed_entry["state"]["last_reviewed_at"] is not None
    assert reviewed_entry["has_new_information"] is False

    # --- new contradictory information: urgency up, thesis untouched -------
    ingest_envelope(
        db_session, _news_envelope("e2e-news-1", received_at=datetime.now(timezone.utc))
    )
    db_session.commit()
    drain_worker()

    after = authenticated.get("/api/v1/follow-up/queue").json()["content"]
    entry = next(e for e in after["theses"] if e["thesis"]["id"] == thesis_id)
    assert entry["has_new_information"] is True
    assert entry["urgency_reasons"][0]["code"] == "NEW_INFORMATION_SINCE_LAST_REVIEW"
    clusters = entry["information_context"]["clusters"]
    assert any(
        "e2e-news-1" in cluster["provenance"]["member_event_ids"]
        for cluster in clusters
    )
    assert after["populations"]["information_context"] == "SYNTHETIC"
    # The information changed URGENCY only: the thesis history has exactly
    # the same two revisions — nothing wrote to the thesis.
    db_session.expire_all()
    assert _revision_count(db_session, thesis_id) == 2
    assert entry["state"]["revision_count"] == 2


def test_snooze_defers_then_expires_back_to_due(
    authenticated: TestClient, db_session: Session, drain_worker
) -> None:
    created = authenticated.post(
        "/api/v1/theses",
        json={**THESIS_PAYLOAD, "idempotency_key": "e2e-snooze-thesis"},
        headers=_csrf(authenticated),
    )
    assert created.status_code == 201
    thesis_id = created.json()["thesis_id"]

    # An EXPIRED snooze instant: the thesis is immediately ACTIVE and DUE
    # again, with the snooze instant as its effective due (projection rule).
    snooze_until = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0)
    snoozed = authenticated.post(
        f"/api/v1/theses/{thesis_id}/revisions",
        json={
            "action": "SNOOZED",
            "idempotency_key": "e2e-snooze-key",
            "snooze_until": snooze_until.isoformat(),
        },
        headers=_csrf(authenticated),
    )
    assert snoozed.status_code == 201

    drain_worker()
    content = authenticated.get("/api/v1/follow-up/queue").json()["content"]
    entry = next(e for e in content["theses"] if e["thesis"]["id"] == thesis_id)
    assert entry["state"]["status"] == "ACTIVE"
    assert entry["state"]["is_due"] is True
    assert entry["state"]["review_due_at"] == snooze_until.isoformat()
    assert thesis_id in [e["thesis_id"] for e in content["due"]]
