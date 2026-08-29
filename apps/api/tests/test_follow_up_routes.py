"""Unit tests of the follow-up routes (SYNTHETIC fakes only).

Gateway, snapshot reader and clock are injected through
``app.dependency_overrides``; the real path (repository idempotence, outbox
atomicity, worker drain) runs in ``tests_integration/test_follow_up_api_e2e.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api.auth import require_session
from vertex_api.follow_up import CreateThesisRequest, ThesisRevisionRequest
from vertex_api.routes import get_follow_up_gateway
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_persistence.errors import IdempotencyKeyReuseError, UnknownThesisError
from vertex_persistence.repository.snapshots import CurrentSnapshot
from vertex_persistence.repository.theses import CreatedThesis, RecordedRevision

FIXED_NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)

VALID_THESIS = {
    "title": "SYNTHETIC thesis",
    "hypotheses": "[SYNTHETIC] the synthetic sector keeps its breadth",
    "invalidation": "[SYNTHETIC] breadth below 40% for five sessions",
    "idempotency_key": "client-key-1",
    "instrument": {"ticker": "SYN-TECH-01"},
}

QUEUE_SNAPSHOT = CurrentSnapshot(
    kind="review_queue",
    key="global",
    version=3,
    content={
        "schema_version": "vertex.review-queue/1.0",
        "as_of": FIXED_NOW.isoformat(),
        "populations": {"theses": "USER_DECLARED", "information_context": "SYNTHETIC"},
        "theses": [{"thesis": {"id": 1}}],
        "due": [{"rank": 1, "thesis_id": 1, "has_new_information": True}],
    },
    content_hash="sha256:" + "0" * 64,
    as_of=FIXED_NOW,
)


class FakeFollowUpGateway:
    """SYNTHETIC in-memory gateway with scriptable replay behavior."""

    def __init__(self) -> None:
        self.created: list[CreateThesisRequest] = []
        self.revisions: list[tuple[int, ThesisRevisionRequest]] = []
        self.create_result = CreatedThesis(thesis_id=1, revision_id=1, created=True)
        self.revision_result = RecordedRevision(revision_id=2, created=True)
        self.raise_on_create: Optional[Exception] = None
        self.raise_on_revision: Optional[Exception] = None

    def create(self, request: CreateThesisRequest, *, now: datetime) -> CreatedThesis:
        if self.raise_on_create is not None:
            raise self.raise_on_create
        self.created.append(request)
        return self.create_result

    def record_revision(
        self, thesis_id: int, request: ThesisRevisionRequest, *, now: datetime
    ) -> RecordedRevision:
        if self.raise_on_revision is not None:
            raise self.raise_on_revision
        self.revisions.append((thesis_id, request))
        return self.revision_result


@pytest.fixture()
def gateway() -> FakeFollowUpGateway:
    return FakeFollowUpGateway()


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader({("review_queue", "global"): QUEUE_SNAPSHOT})


@pytest.fixture()
def follow_up_client(
    app: FastAPI, gateway: FakeFollowUpGateway, reader: FakeSnapshotReader
) -> Iterator[TestClient]:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_follow_up_gateway] = lambda: gateway
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    app.dependency_overrides[get_clock] = lambda: (lambda: FIXED_NOW)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# -- fail-closed authentication ---------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/api/v1/follow-up/queue"),
        ("POST", "/api/v1/theses"),
        ("POST", "/api/v1/theses/1/revisions"),
    ],
)
def test_every_follow_up_route_requires_a_session(client, method, path) -> None:
    response = client.request(method, path, json={})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


# -- GET /follow-up/queue: verbatim relay + honest empty ---------------------


def test_queue_relays_snapshot_verbatim(follow_up_client) -> None:
    response = follow_up_client.get("/api/v1/follow-up/queue")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert body["snapshot_version"] == 3
    # VERBATIM: the exact persisted content, populations kept separate.
    assert body["content"] == QUEUE_SNAPSHOT.content
    assert body["reason"] is None


def test_queue_empty_state_is_honest(follow_up_client, reader) -> None:
    reader.snapshots.clear()
    response = follow_up_client.get("/api/v1/follow-up/queue")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["snapshot_version"] is None
    assert body["content"] is None
    assert body["reason"] == "no snapshot published"


# -- POST /theses ------------------------------------------------------------


def test_create_thesis_is_201_with_receipt(follow_up_client, gateway) -> None:
    response = follow_up_client.post("/api/v1/theses", json=VALID_THESIS)
    assert response.status_code == 201
    body = response.json()
    assert body == {
        "thesis_id": 1,
        "revision_id": 1,
        "created": True,
        "refresh_enqueued": True,
    }
    assert gateway.created[0].idempotency_key == "client-key-1"


def test_create_thesis_replay_is_200_created_false(follow_up_client, gateway) -> None:
    gateway.create_result = CreatedThesis(thesis_id=1, revision_id=1, created=False)
    response = follow_up_client.post("/api/v1/theses", json=VALID_THESIS)
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is False
    assert body["refresh_enqueued"] is False  # a replay writes and enqueues nothing
    assert body["thesis_id"] == 1  # the ORIGINAL ids, never a duplicate


@pytest.mark.parametrize(
    "mutation",
    [
        {"invalidation": ""},  # blank falsifier
        {"invalidation": "   "},  # whitespace-only falsifier
        {"idempotency_key": None},  # idempotency key is mandatory
        {"idempotency_key": ""},
        {"title": ""},
        {"unknown_field": "x"},  # strict contract: unknown fields rejected
    ],
)
def test_create_thesis_contract_violations_are_422(follow_up_client, gateway, mutation) -> None:
    payload = dict(VALID_THESIS)
    payload.update(mutation)
    payload = {key: value for key, value in payload.items() if value is not None}
    if "idempotency_key" in mutation and mutation["idempotency_key"] is None:
        payload.pop("idempotency_key", None)
    response = follow_up_client.post("/api/v1/theses", json=payload)
    assert response.status_code == 422
    assert gateway.created == []  # nothing reached the gateway


def test_create_thesis_idempotency_key_reuse_is_409(follow_up_client, gateway) -> None:
    gateway.raise_on_create = IdempotencyKeyReuseError("key names a REVIEWED revision")
    response = follow_up_client.post("/api/v1/theses", json=VALID_THESIS)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"


# -- POST /theses/{id}/revisions ---------------------------------------------


def test_record_revision_is_201_with_receipt(follow_up_client, gateway) -> None:
    response = follow_up_client.post(
        "/api/v1/theses/1/revisions",
        json={"action": "REVIEWED", "idempotency_key": "rev-key-1"},
    )
    assert response.status_code == 201
    assert response.json() == {
        "thesis_id": 1,
        "revision_id": 2,
        "created": True,
        "refresh_enqueued": True,
    }
    thesis_id, request = gateway.revisions[0]
    assert thesis_id == 1 and request.action == "REVIEWED"


def test_record_revision_replay_is_200_created_false(follow_up_client, gateway) -> None:
    gateway.revision_result = RecordedRevision(revision_id=2, created=False)
    response = follow_up_client.post(
        "/api/v1/theses/1/revisions",
        json={"action": "REVIEWED", "idempotency_key": "rev-key-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is False
    assert body["revision_id"] == 2  # the SAME revision id on every replay
    assert body["refresh_enqueued"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "CREATED", "idempotency_key": "k"},  # reserved to POST /theses
        {"action": "DELETED", "idempotency_key": "k"},  # outside the allowlist
        {"action": "SNOOZED", "idempotency_key": "k"},  # SNOOZED without snooze_until
        {  # snooze_until on a non-SNOOZED action
            "action": "REVIEWED",
            "idempotency_key": "k",
            "snooze_until": "2026-09-01T00:00:00Z",
        },
        {"action": "REVIEWED"},  # idempotency key is mandatory
    ],
)
def test_revision_allowlist_and_snooze_rules_are_422(follow_up_client, gateway, payload) -> None:
    response = follow_up_client.post("/api/v1/theses/1/revisions", json=payload)
    assert response.status_code == 422
    assert gateway.revisions == []


def test_snoozed_revision_requires_and_accepts_snooze_until(follow_up_client, gateway) -> None:
    response = follow_up_client.post(
        "/api/v1/theses/1/revisions",
        json={
            "action": "SNOOZED",
            "idempotency_key": "rev-key-2",
            "snooze_until": "2026-09-01T00:00:00Z",
        },
    )
    assert response.status_code == 201
    _, request = gateway.revisions[0]
    assert request.snooze_until is not None


def test_unknown_thesis_is_404(follow_up_client, gateway) -> None:
    gateway.raise_on_revision = UnknownThesisError("thesis 99 does not exist")
    response = follow_up_client.post(
        "/api/v1/theses/99/revisions",
        json={"action": "REVIEWED", "idempotency_key": "k"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "UNKNOWN_THESIS"
