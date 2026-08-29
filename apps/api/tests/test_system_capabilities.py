"""GET /api/v1/system/capabilities: manifest x probed snapshot + health.

SYNTHETIC fixtures only. The route must render EVERY manifest entry
(``total`` equals the exact manifest size), answer ``ERROR/NEVER_TESTED``
for capabilities never probed, and cross really-probed statuses from a fake
persisted snapshot without inventing anything.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api.auth import AUTH_REQUIRED, require_session
from vertex_api.capability_manifest import load_capability_manifest
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_persistence.repository.snapshots import CurrentSnapshot

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
PROBE_AT = NOW - timedelta(hours=2)
SNAPSHOT_AS_OF = NOW - timedelta(hours=1)

MANIFEST = load_capability_manifest()
MANIFEST_IDS = sorted(MANIFEST.capability_ids)


def capabilities_content(fields: list[dict]) -> dict:
    """SYNTHETIC copy of the worker's published capabilities content shape."""
    return {
        "schema_version": "vertex.capabilities/1.0",
        "as_of": SNAPSHOT_AS_OF.isoformat(),
        "probed_sources": [
            {
                "source": "edge-demo",
                "event_id": "edge-demo:capability:0001",
                "schema_version": "source-capability/1.0",
                "as_of": PROBE_AT.isoformat(),
                "rights": "DEMO",
                "synthetic": True,
                "snapshot": {
                    "probe_id": "probe-demo-0001",
                    "connection_epoch": 1,
                    "tested_at": PROBE_AT.isoformat(),
                    "fields": fields,
                },
            }
        ],
    }


def capabilities_snapshot(fields: list[dict], version: int = 2) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="capabilities",
        key="global",
        version=version,
        content=capabilities_content(fields),
        content_hash="sha256:" + "1" * 64,
        as_of=SNAPSHOT_AS_OF,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def capabilities_client(app: FastAPI, reader: FakeSnapshotReader) -> Iterator[TestClient]:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    app.dependency_overrides[get_clock] = lambda: (lambda: NOW)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_without_session_is_generic_401(client: TestClient) -> None:
    response = client.get("/api/v1/system/capabilities")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_REQUIRED


class TestNeverTested:
    def test_no_snapshot_renders_every_capability_never_tested(
        self, capabilities_client: TestClient
    ) -> None:
        body = capabilities_client.get("/api/v1/system/capabilities").json()

        assert body["total"] == len(MANIFEST.declarations)
        assert len(body["capabilities"]) == body["total"]
        assert [c["capability_id"] for c in body["capabilities"]] == MANIFEST_IDS

        for capability in body["capabilities"]:
            assert capability["tested_status"] == "ERROR"
            assert capability["reason"] == "NEVER_TESTED"
            assert capability["tested_at"] is None
            assert capability["family"]
            assert capability["declared_mode"]

        assert body["snapshot_version"] is None
        assert body["as_of"] is None
        assert body["unknown_probed_capability_ids"] == []

    def test_declared_modes_and_families_come_from_the_manifest(
        self, capabilities_client: TestClient
    ) -> None:
        body = capabilities_client.get("/api/v1/system/capabilities").json()
        by_id = {c["capability_id"]: c for c in body["capabilities"]}
        # The two capabilities the TWS API does not provide declare it.
        assert by_id["live_option_tick_by_tick"]["declared_mode"] == "UNSUPPORTED"
        assert by_id["live_option_tick_by_tick"]["family"] == "not_provided_by_source"
        assert by_id["option_top_of_book"]["declared_mode"] == "INFORMATION_ONLY"
        assert by_id["option_top_of_book"]["family"] == "market_data"
        assert by_id["option_chain_definition"]["family"] == "contract_reference"
        assert by_id["option_historical_bars"]["family"] == "historical_data"


class TestCrossedWithProbedSnapshot:
    def test_probed_capability_reports_persisted_status(
        self, capabilities_client: TestClient, reader: FakeSnapshotReader
    ) -> None:
        reader.snapshots[("capabilities", "global")] = capabilities_snapshot(
            [
                {
                    "capability_id": "underlying_top_of_book",
                    "field": "bid",
                    "status": "DELAYED",
                    "reason_code": None,
                },
                {
                    "capability_id": "option_chain_definition",
                    "field": "expirations",
                    "status": "AVAILABLE",
                    "reason_code": None,
                },
                {
                    "capability_id": "option_computations_live",
                    "field": "delta",
                    "status": "NOT_ENTITLED",
                    "reason_code": "LIVE_MARKET_DATA_NOT_SUBSCRIBED",
                },
            ]
        )
        body = capabilities_client.get("/api/v1/system/capabilities").json()
        by_id = {c["capability_id"]: c for c in body["capabilities"]}

        assert body["total"] == len(MANIFEST.declarations)
        assert body["snapshot_version"] == 2
        assert body["as_of"] == "2026-08-25T11:00:00Z"

        assert by_id["underlying_top_of_book"]["tested_status"] == "DELAYED"
        assert by_id["underlying_top_of_book"]["tested_at"] == "2026-08-25T10:00:00Z"
        assert by_id["underlying_top_of_book"]["reason"] is None

        assert by_id["option_chain_definition"]["tested_status"] == "AVAILABLE"

        entry = by_id["option_computations_live"]
        assert entry["tested_status"] == "NOT_ENTITLED"
        assert entry["reason"] == "LIVE_MARKET_DATA_NOT_SUBSCRIBED"

        # Everything not probed stays fail-closed NEVER_TESTED.
        untested = [
            c
            for c in body["capabilities"]
            if c["capability_id"]
            not in {
                "underlying_top_of_book",
                "option_chain_definition",
                "option_computations_live",
            }
        ]
        assert len(untested) == len(MANIFEST.declarations) - 3
        for capability in untested:
            assert capability["tested_status"] == "ERROR"
            assert capability["reason"] == "NEVER_TESTED"

    def test_invalid_probe_status_fails_closed_to_error(
        self, capabilities_client: TestClient, reader: FakeSnapshotReader
    ) -> None:
        reader.snapshots[("capabilities", "global")] = capabilities_snapshot(
            [
                {
                    "capability_id": "underlying_top_of_book",
                    "field": "bid",
                    "status": "TOTALLY_FINE",  # not a canonical status
                    "reason_code": None,
                }
            ]
        )
        body = capabilities_client.get("/api/v1/system/capabilities").json()
        by_id = {c["capability_id"]: c for c in body["capabilities"]}
        assert by_id["underlying_top_of_book"]["tested_status"] == "ERROR"
        assert by_id["underlying_top_of_book"]["reason"] == "INVALID_STATUS"

    def test_conflicting_field_statuses_fail_closed_to_error(
        self, capabilities_client: TestClient, reader: FakeSnapshotReader
    ) -> None:
        reader.snapshots[("capabilities", "global")] = capabilities_snapshot(
            [
                {
                    "capability_id": "underlying_top_of_book",
                    "field": "bid",
                    "status": "AVAILABLE",
                    "reason_code": None,
                },
                {
                    "capability_id": "underlying_top_of_book",
                    "field": "ask",
                    "status": "NOT_ENTITLED",
                    "reason_code": "LIVE_MARKET_DATA_NOT_SUBSCRIBED",
                },
            ]
        )
        body = capabilities_client.get("/api/v1/system/capabilities").json()
        by_id = {c["capability_id"]: c for c in body["capabilities"]}
        assert by_id["underlying_top_of_book"]["tested_status"] == "ERROR"
        assert by_id["underlying_top_of_book"]["reason"] == "CONFLICTING_FIELD_STATUSES"

    def test_unknown_probed_capability_is_listed_never_merged(
        self, capabilities_client: TestClient, reader: FakeSnapshotReader
    ) -> None:
        reader.snapshots[("capabilities", "global")] = capabilities_snapshot(
            [
                {
                    "capability_id": "quotes",  # not a declared capability
                    "field": "bid",
                    "status": "DELAYED",
                    "reason_code": None,
                }
            ]
        )
        body = capabilities_client.get("/api/v1/system/capabilities").json()
        assert body["unknown_probed_capability_ids"] == ["quotes"]
        assert body["total"] == len(MANIFEST.declarations)
        assert all(c["capability_id"] != "quotes" for c in body["capabilities"])


class TestHealthBlocks:
    def test_health_with_database_ok_and_no_snapshot(
        self, capabilities_client: TestClient
    ) -> None:
        health = capabilities_client.get("/api/v1/system/capabilities").json()["health"]
        assert health["db"] == {"status": "ok"}
        assert health["attention_snapshot"] == {
            "present": False,
            "version": None,
            "as_of": None,
            "age_seconds": None,
        }
        assert health["capabilities_snapshot"]["present"] is False
        assert health["worker"] == {
            "method": "heartbeat_proxy",
            "last_snapshot_as_of": None,
            "age_seconds": None,
        }

    def test_health_reports_snapshot_ages_and_worker_proxy(
        self, capabilities_client: TestClient, reader: FakeSnapshotReader
    ) -> None:
        reader.snapshots[("capabilities", "global")] = capabilities_snapshot([])
        body = capabilities_client.get("/api/v1/system/capabilities").json()
        health = body["health"]
        assert health["capabilities_snapshot"] == {
            "present": True,
            "version": 2,
            "as_of": "2026-08-25T11:00:00Z",
            "age_seconds": 3600,
        }
        assert health["worker"] == {
            "method": "heartbeat_proxy",
            "last_snapshot_as_of": "2026-08-25T11:00:00Z",
            "age_seconds": 3600,
        }

    def test_database_failure_is_an_honest_error_status(
        self, capabilities_client: TestClient, reader: FakeSnapshotReader
    ) -> None:
        reader.db_ok = False
        health = capabilities_client.get("/api/v1/system/capabilities").json()["health"]
        assert health["db"] == {"status": "error"}
