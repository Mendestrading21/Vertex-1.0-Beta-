"""Snapshot routes against real PostgreSQL and REAL passkey authentication.

A snapshot is published through the real ``vertex_persistence`` repository
(SYNTHETIC content, worker shape), then read back through the protected API:
no dependency override anywhere — WebAuthn session, database reader and the
committed capability manifest are all real.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from soft_passkey import SoftPasskey, login_passkey, register_passkey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from vertex_api.capability_manifest import load_capability_manifest
from vertex_persistence.repository.snapshots import publish_snapshot

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
MANIFEST = load_capability_manifest()

ATTENTION_CONTENT = {
    "schema_version": "vertex.attention-queue/1.0",
    "as_of": NOW.isoformat(),
    "population": "SYNTHETIC",
    "policy_version": "relevance-policy/1.0",
    "fusion_ruleset_version": "fusion/1.0",
    "items": [
        {
            "item_id": "synthetic-dev:evt:0001",
            "title": "synthetic attention item",
            "synthetic": True,
            "priority_class": "P2",
            "relevance_reasons": ["reason-one", "reason-two"],
            "age_seconds": 120,
            "source_tier": "P4",
            "quality": "VALID",
            "provenance": {
                "cluster_id": "cluster-0001",
                "member_event_ids": ["synthetic-dev:evt:0001"],
                "sources": ["synthetic-dev"],
                "rights": ["SYNTHETIC"],
                "first_published_at": NOW.isoformat(),
                "last_received_at": NOW.isoformat(),
                "instrument_ref": "SYNTH:NASDAQ:STK:USD",
            },
        }
    ],
    "rejected": [],
    "coverage": {
        "lookback_seconds": 259200,
        "max_items": 15,
        "observations_considered": 1,
        "content_observations": 1,
        "non_content_observations": 0,
        "synthetic_observations": 1,
        "non_synthetic_observations": 0,
        "clusters": 1,
        "ranked": 1,
        "rejected": 0,
        "published_items": 1,
        "truncated_ranked": 0,
    },
}

CAPABILITIES_CONTENT = {
    "schema_version": "vertex.capabilities/1.0",
    "as_of": NOW.isoformat(),
    "probed_sources": [
        {
            "source": "edge-demo",
            "event_id": "edge-demo:capability:0001",
            "schema_version": "source-capability/1.0",
            "as_of": (NOW - timedelta(hours=2)).isoformat(),
            "rights": "DEMO",
            "synthetic": True,
            "snapshot": {
                "probe_id": "probe-demo-0001",
                "connection_epoch": 1,
                "tested_at": (NOW - timedelta(hours=2)).isoformat(),
                "fields": [
                    {
                        "capability_id": "underlying_top_of_book",
                        "field": "bid",
                        "status": "DELAYED",
                        "reason_code": None,
                    }
                ],
            },
        }
    ],
}


@pytest.fixture()
def authenticated(client: TestClient, passkey: SoftPasskey) -> TestClient:
    """Real WebAuthn registration + login on the migrated database."""
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


class TestTodayAttention:
    def test_requires_a_real_session(self, client: TestClient) -> None:
        assert client.get("/api/v1/today/attention").status_code == 401

    def test_no_snapshot_is_honest_empty_200(self, authenticated: TestClient) -> None:
        response = authenticated.get("/api/v1/today/attention")
        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "empty"
        assert body["as_of"] is None
        assert body["items"] == []
        assert body["reason"] == "no snapshot published"

    def test_published_snapshot_round_trips_exactly(
        self, authenticated: TestClient, db_session: Session
    ) -> None:
        published = publish_snapshot(
            db_session, kind="attention", key="global", content=ATTENTION_CONTENT, as_of=NOW
        )
        db_session.commit()

        response = authenticated.get("/api/v1/today/attention")
        assert response.status_code == 200
        body = response.json()

        assert body["state"] == "ok"
        assert body["snapshot_version"] == published.version == 1
        assert body["as_of"] == "2026-08-25T12:00:00Z"
        assert body["population"] == "SYNTHETIC"
        assert body["coverage"] == ATTENTION_CONTENT["coverage"]
        assert body["rejected_count"] == 0

        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["id"] == "synthetic-dev:evt:0001"
        assert item["title"] == "synthetic attention item"
        assert item["synthetic"] is True
        assert item["sources"] == ["synthetic-dev"]
        assert item["rights"] == ["SYNTHETIC"]
        assert item["relevance_reasons"] == ["reason-one", "reason-two"]
        assert item["provenance"] == ATTENTION_CONTENT["items"][0]["provenance"]


class TestSystemCapabilities:
    def test_requires_a_real_session(self, client: TestClient) -> None:
        assert client.get("/api/v1/system/capabilities").status_code == 401

    def test_total_equals_manifest_and_never_tested_without_probe(
        self, authenticated: TestClient
    ) -> None:
        response = authenticated.get("/api/v1/system/capabilities")
        assert response.status_code == 200
        body = response.json()

        assert body["total"] == len(MANIFEST.declarations)
        assert len(body["capabilities"]) == len(MANIFEST.declarations)
        assert sorted(c["capability_id"] for c in body["capabilities"]) == sorted(
            MANIFEST.capability_ids
        )
        for capability in body["capabilities"]:
            assert capability["tested_status"] == "ERROR"
            assert capability["reason"] == "NEVER_TESTED"
            assert capability["tested_at"] is None

        assert body["health"]["db"] == {"status": "ok"}
        assert body["health"]["worker"]["method"] == "heartbeat_proxy"
        assert body["health"]["worker"]["last_snapshot_as_of"] is None

    def test_persisted_probe_is_crossed_with_the_manifest(
        self, authenticated: TestClient, db_session: Session
    ) -> None:
        publish_snapshot(
            db_session,
            kind="capabilities",
            key="global",
            content=CAPABILITIES_CONTENT,
            as_of=NOW,
        )
        db_session.commit()

        body = authenticated.get("/api/v1/system/capabilities").json()
        assert body["total"] == len(MANIFEST.declarations)
        assert body["snapshot_version"] == 1
        assert body["as_of"] == "2026-08-25T12:00:00Z"

        by_id = {c["capability_id"]: c for c in body["capabilities"]}
        probed = by_id["underlying_top_of_book"]
        assert probed["tested_status"] == "DELAYED"
        assert probed["tested_at"] == "2026-08-25T10:00:00Z"

        untested = [
            c for c in body["capabilities"] if c["capability_id"] != "underlying_top_of_book"
        ]
        assert len(untested) == len(MANIFEST.declarations) - 1
        for capability in untested:
            assert capability["tested_status"] == "ERROR"
            assert capability["reason"] == "NEVER_TESTED"

        health = body["health"]
        assert health["capabilities_snapshot"]["present"] is True
        assert health["capabilities_snapshot"]["version"] == 1
        assert health["attention_snapshot"]["present"] is False
        assert health["worker"]["last_snapshot_as_of"] == "2026-08-25T12:00:00Z"
