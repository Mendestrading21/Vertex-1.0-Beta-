"""GET /api/v1/today/attention: last published snapshot verbatim, honest empty.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.handlers.build_attention_content``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import AUTH_REQUIRED, require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError, build_attention_response
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

#: Horloge du relais, injectée : une horloge RÉELLE rendrait l'instantané
#: périmé au fil des jours et ferait échouer ces tests sans qu'aucun
#: comportement ait changé. L'âge servi doit rester mesuré, pas subi.
_NOW = AS_OF + timedelta(minutes=30)


def attention_content() -> dict:
    """SYNTHETIC copy of the worker's published attention content shape."""
    return {
        "schema_version": "vertex.attention-queue/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "policy_version": "relevance-policy/1.0",
        "fusion_ruleset_version": "fusion/1.0",
        "items": [
            {
                "item_id": "synthetic-dev:evt:0001",
                "title": "synthetic attention item",
                "synthetic": True,
                "priority_class": "P2",
                "relevance_reasons": [
                    "reason-one",
                    "reason-two",
                    "reason-three",
                    "reason-four-must-be-truncated",
                ],
                "age_seconds": 120,
                "source_tier": "P4",
                "quality": "VALID",
                "provenance": {
                    "cluster_id": "cluster-0001",
                    "member_event_ids": ["synthetic-dev:evt:0001"],
                    "sources": ["synthetic-dev"],
                    "rights": ["SYNTHETIC"],
                    "first_published_at": AS_OF.isoformat(),
                    "last_received_at": AS_OF.isoformat(),
                    "instrument_ref": "SYNTH:NASDAQ:STK:USD",
                },
            }
        ],
        "rejected": [
            {
                "item_id": "synthetic-dev:evt:0002",
                "filtered_reason": "RIGHTS",
                "failed_gates": ["RIGHTS_OK"],
            }
        ],
        "coverage": {
            "lookback_seconds": 259200,
            "max_items": 15,
            "observations_considered": 2,
            "content_observations": 2,
            "non_content_observations": 0,
            "synthetic_observations": 2,
            "non_synthetic_observations": 0,
            "clusters": 2,
            "ranked": 1,
            "rejected": 1,
            "published_items": 1,
            "truncated_ranked": 0,
        },
    }


def attention_snapshot(version: int = 3) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="attention",
        key="global",
        version=version,
        content=attention_content(),
        content_hash="sha256:" + "0" * 64,
        as_of=AS_OF,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def snapshot_client(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    # Horloge FIXE : sans elle, le relais mesurerait l'âge de l'instantané
    # contre l'heure réelle et le déclarerait périmé quelques jours après
    # l'écriture de ce test, sans qu'aucun code ait changé.
    app.dependency_overrides[get_clock] = lambda: (lambda: _NOW)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_without_session_is_generic_401(client: TestClient) -> None:
    response = client.get("/api/v1/today/attention")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_REQUIRED


def test_no_snapshot_published_is_honest_200_empty(snapshot_client: TestClient) -> None:
    response = snapshot_client.get("/api/v1/today/attention")
    assert response.status_code == 200
    assert response.json() == {
        "state": "empty",
        "snapshot_version": None,
        "as_of": None,
        "age_seconds": None,
        "population": None,
        "coverage": None,
        "items": [],
        "rejected_count": None,
        "reason": "no snapshot published",
    }


def test_published_snapshot_is_served_verbatim(
    snapshot_client: TestClient, reader: FakeSnapshotReader
) -> None:
    reader.snapshots[("attention", "global")] = attention_snapshot(version=3)
    response = snapshot_client.get("/api/v1/today/attention")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "ok"
    assert body["snapshot_version"] == 3
    assert body["as_of"] == "2026-08-25T12:00:00Z"
    assert body["population"] == "SYNTHETIC"  # shown exactly as published
    assert body["rejected_count"] == 1
    assert body["reason"] is None
    assert body["coverage"] == attention_content()["coverage"]

    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == "synthetic-dev:evt:0001"
    assert item["title"] == "synthetic attention item"
    assert item["synthetic"] is True
    assert item["sources"] == ["synthetic-dev"]
    assert item["rights"] == ["SYNTHETIC"]
    # At most three relevance reasons cross the wire.
    assert item["relevance_reasons"] == ["reason-one", "reason-two", "reason-three"]
    assert item["provenance"] == attention_content()["items"][0]["provenance"]


def test_response_carries_complete_metadata_fields(
    snapshot_client: TestClient, reader: FakeSnapshotReader
) -> None:
    reader.snapshots[("attention", "global")] = attention_snapshot()
    body = snapshot_client.get("/api/v1/today/attention").json()
    assert set(body) == {
        "state",
        "snapshot_version",
        "as_of",
        "age_seconds",
        "population",
        "coverage",
        "items",
        "rejected_count",
        "reason",
    }


def test_malformed_persisted_content_fails_closed() -> None:
    broken = CurrentSnapshot(
        kind="attention",
        key="global",
        version=1,
        content={"schema_version": "vertex.attention-queue/1.0"},  # no items/as_of
        content_hash="sha256:" + "0" * 64,
        as_of=AS_OF,
    )
    with pytest.raises(SnapshotContentError):
        build_attention_response(broken, now=_NOW)
