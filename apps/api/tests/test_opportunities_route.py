"""GET /api/v1/opportunities: verbatim relay, honest empty, guard, 401.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.opportunities.build_opportunities_content``).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api.auth import require_session
from vertex_api.opportunities import build_opportunities_response
from vertex_api.snapshot_reader import get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


def candidate(ticker: str, status: str) -> dict:
    return {
        "ticker": ticker,
        "sector": "SYN-TECH",
        "advice": {
            "advice_id": "sha256:" + "b" * 64,
            "status": status,
            "direction": "UNKNOWN",
            "horizon": "1d",
            "as_of": AS_OF.isoformat(),
            "valid_until": AS_OF.isoformat(),
            "engine_version": "vertex_core@0.1.0",
        },
        "gates": [
            {
                "gate_id": "entitlements_sufficient",
                "status": "BLOCK" if status == "INSUFFICIENT_DATA" else "PASS",
                "reason_code": "UNEVALUABLE"
                if status == "INSUFFICIENT_DATA"
                else "OK",
            }
        ],
        "required_evidence": {"sector": {"present": True, "detail": "SYN-TECH"}},
        "missing_evidence": [],
        "evidence_cluster_ids": [],
        "scenario_ids": [],
        "bars_status": "OK",
        "scenarios_status": "ABSENT",
        "synthetic": True,
        "primary_exclusion_reason": (
            {"gate_id": "entitlements_sufficient", "reason_code": "UNEVALUABLE"}
            if status == "INSUFFICIENT_DATA"
            else None
        ),
    }


def opportunities_content(qualified: list[dict], excluded: list[dict]) -> dict:
    return {
        "schema_version": "vertex.opportunities/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "engine_version": "vertex_core@0.1.0",
        "profile_ref": {
            "id": "equity_etf_swing_3_12m",
            "version": "1.0.0",
            "source": "manifests/strategy-profiles.yaml",
        },
        "ordering": {"method": "lexicographic", "keys": [], "note": "documented"},
        "qualified": qualified,
        "excluded": excluded,
        "exclusion_reasons": {
            "entitlements_sufficient:UNEVALUABLE": len(excluded)
        },
        "limitations": ["SYNTHETIC development population"],
        "coverage": {
            "universe_size": 24,
            "qualified_count": len(qualified),
            "excluded_count": len(excluded),
            "status_counts": {},
            "observations_considered": 4,
            "lookback_seconds": 259200,
        },
    }


def snapshot(content: dict, version: int = 1) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="opportunities",
        key="global",
        version=version,
        content=content,
        content_hash="sha256:" + "c" * 64,
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
    assert client.get("/api/v1/opportunities").status_code == 401


def test_empty_state_is_honest_200(api: TestClient) -> None:
    body = api.get("/api/v1/opportunities").json()
    assert body == {
        "state": "empty",
        "snapshot_version": None,
        "as_of": None,
        "content": None,
        "reason": "no snapshot published",
    }


def test_relay_is_verbatim(api: TestClient, reader: FakeSnapshotReader) -> None:
    content = opportunities_content(
        qualified=[candidate("SYN-TECH-01", "OBSERVE")],
        excluded=[candidate("SYN-TECH-02", "INSUFFICIENT_DATA")],
    )
    reader.snapshots[("opportunities", "global")] = snapshot(content)

    body = api.get("/api/v1/opportunities").json()
    assert body["state"] == "ok"
    assert body["snapshot_version"] == 1
    assert body["content"] == content
    assert body["content"]["profile_ref"]["version"] == "1.0.0"
    assert body["content"]["exclusion_reasons"]


def test_closed_candidate_in_qualified_group_is_refused() -> None:
    content = opportunities_content(
        qualified=[candidate("SYN-TECH-01", "INSUFFICIENT_DATA")],
        excluded=[],
    )
    with pytest.raises(SnapshotContentError):
        build_opportunities_response(snapshot(content))


def test_non_canonical_excluded_status_is_refused() -> None:
    content = opportunities_content(
        qualified=[],
        excluded=[candidate("SYN-TECH-01", "OBSERVE")],
    )
    with pytest.raises(SnapshotContentError):
        build_opportunities_response(snapshot(content))
