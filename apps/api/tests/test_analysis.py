"""GET /api/v1/analysis/{instrument}: verbatim relay, honest empty, 401.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.analysis.build_analysis_content``).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError, build_analysis_response
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
INSTRUMENT = "SYN-TECH-01"


def gate(gate_id: str, status: str, reason_code: str) -> dict:
    return {
        "gate_id": gate_id,
        "version": "1.0.0",
        "status": status,
        "reason_code": reason_code,
        "message": "synthetic gate message",
        "observed_values": {},
        "thresholds": {},
    }


def analysis_content() -> dict:
    """SYNTHETIC copy of the worker's published analysis content shape."""
    return {
        "schema_version": "vertex.analysis/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "instrument": INSTRUMENT,
        "engine_version": "vertex_core@0.1.0",
        "bars": {
            "status": "OK",
            "count": 2,
            "currency": "SYN",
            "adjustment_basis": "synthetic-unadjusted",
            "first_trading_day": "2026-08-23",
            "last_trading_day": "2026-08-24",
            "last_close": "104.50",
            "quality": "VALID",
            "fresh": True,
            "source_event_id": "synthetic-dev:t:db0001",
            "observed_as_of": AS_OF.isoformat(),
            "discarded": [],
            "bars": [
                {
                    "trading_day": "2026-08-23",
                    "open": "100.00",
                    "high": "103.00",
                    "low": "99.00",
                    "close": "102.00",
                    "volume": 1000,
                },
                {
                    "trading_day": "2026-08-24",
                    "open": "102.00",
                    "high": "105.00",
                    "low": "101.00",
                    "close": "104.50",
                    "volume": 1200,
                },
            ],
        },
        "evidence": {
            "source": "fusion",
            "ruleset_version": "fusion/1.0",
            "considered": 1,
            "clusters_total": 1,
            "clusters": [
                {
                    "cluster_id": "cluster-0001",
                    "title": "[SYNTHETIC] item",
                    "sources": ["synthetic-dev"],
                    "rights": ["SYNTHETIC"],
                    "member_count": 1,
                    "member_event_ids": ["e1"],
                    "last_received_at": AS_OF.isoformat(),
                    "synthetic": True,
                }
            ],
        },
        "scenarios": {"status": "ABSENT", "reason": "no_option_chain_snapshot"},
        "advice": {
            "advice_id": "sha256:" + "d" * 64,
            "instrument_id": INSTRUMENT,
            "as_of": AS_OF.isoformat(),
            "valid_until": AS_OF.isoformat(),
            "input_snapshot_id": "synthetic-dev:t:db0001",
            "engine_version": "vertex_core@0.1.0",
            "status": "INSUFFICIENT_DATA",
            "direction": "UNKNOWN",
            "horizon": "1d",
            "gates": [
                gate("instrument_resolved", "DEGRADE", "RESOLVED_WITHOUT_CONID"),
                gate("entitlements_sufficient", "BLOCK", "UNEVALUABLE"),
            ],
            "evidence_ids": ["cluster-0001"],
            "risk_summary": "synthetic",
            "scenario_ids": [],
            "probability_evidence": None,
            "limitations": ["SYNTHETIC development population"],
            "explanation_facts": ["2 synthetic daily bars"],
            "supersedes": None,
        },
        "coverage": {
            "observations_considered": 1,
            "rejected_records": [],
            "lookback_seconds": 259200,
        },
    }


def snapshot(content: dict) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="analysis",
        key=INSTRUMENT,
        version=2,
        content=content,
        content_hash="sha256:" + "e" * 64,
        as_of=AS_OF,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def analysis_client(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def test_requires_a_session(client: TestClient) -> None:
    assert client.get(f"/api/v1/analysis/{INSTRUMENT}").status_code == 401


def test_no_snapshot_is_honest_empty_200(analysis_client: TestClient) -> None:
    response = analysis_client.get(f"/api/v1/analysis/{INSTRUMENT}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["instrument"] == INSTRUMENT
    assert body["advice"] is None
    assert body["bars"] is None
    assert body["reason"] == "no snapshot published"


def test_published_dossier_is_relayed_verbatim(
    analysis_client: TestClient, reader: FakeSnapshotReader
) -> None:
    content = analysis_content()
    reader.snapshots[("analysis", INSTRUMENT)] = snapshot(content)

    response = analysis_client.get(f"/api/v1/analysis/{INSTRUMENT}")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "ok"
    assert body["snapshot_version"] == 2
    assert body["population"] == "SYNTHETIC"
    assert body["bars"] == content["bars"]
    assert body["evidence"] == content["evidence"]
    assert body["scenarios"] == content["scenarios"]
    assert body["advice"] == content["advice"]
    assert body["coverage"] == content["coverage"]
    # The verdict and its gates travel untouched.
    assert body["advice"]["status"] == "INSUFFICIENT_DATA"
    assert body["advice"]["gates"][1]["reason_code"] == "UNEVALUABLE"


def test_snapshot_for_another_instrument_is_refused() -> None:
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(analysis_content()), instrument="SYN-TECH-02")


def test_non_canonical_advice_status_is_refused() -> None:
    content = analysis_content()
    content["advice"]["status"] = "APPROVED"  # not a canonical AdviceStatus
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT)


def test_gate_without_reason_code_is_refused() -> None:
    content = analysis_content()
    del content["advice"]["gates"][0]["reason_code"]
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT)


def test_computed_scenarios_must_be_theoretical() -> None:
    content = analysis_content()
    content["scenarios"] = {"status": "OK", "grid": []}  # missing value_nature
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT)
