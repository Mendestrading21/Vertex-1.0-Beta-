"""Analysis route against real PostgreSQL and REAL passkey authentication.

A SYNTHETIC ``analysis/{instrument}`` snapshot (worker shape) is published
through the real repository, then read back through the protected API: no
dependency override anywhere.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from soft_passkey import SoftPasskey, login_passkey, register_passkey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from vertex_persistence.repository.snapshots import publish_snapshot

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
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


ANALYSIS_CONTENT = {
    "schema_version": "vertex.analysis/1.0",
    "as_of": NOW.isoformat(),
    "population": "SYNTHETIC",
    "instrument": INSTRUMENT,
    "engine_version": "vertex_core@0.1.0",
    "bars": {
        "status": "OK",
        "count": 1,
        "currency": "SYN",
        "adjustment_basis": "synthetic-unadjusted",
        "first_trading_day": "2026-08-24",
        "last_trading_day": "2026-08-24",
        "last_close": "104.50",
        "quality": "VALID",
        "fresh": True,
        "source_event_id": "synthetic-dev:e2e:db0001",
        "observed_as_of": NOW.isoformat(),
        "discarded": [],
        "bars": [
            {
                "trading_day": "2026-08-24",
                "open": "102.00",
                "high": "105.00",
                "low": "101.00",
                "close": "104.50",
                "volume": 1200,
            }
        ],
    },
    "evidence": {
        "source": "fusion",
        "ruleset_version": "fusion/1.0",
        "considered": 0,
        "clusters_total": 0,
        "clusters": [],
    },
    "scenarios": {"status": "ABSENT", "reason": "no_healthy_option_contract"},
    "advice": {
        "advice_id": "sha256:" + "d" * 64,
        "instrument_id": INSTRUMENT,
        "as_of": NOW.isoformat(),
        "valid_until": NOW.isoformat(),
        "input_snapshot_id": "synthetic-dev:e2e:db0001",
        "engine_version": "vertex_core@0.1.0",
        "status": "INSUFFICIENT_DATA",
        "direction": "UNKNOWN",
        "horizon": "1d",
        "gates": [
            gate("instrument_resolved", "DEGRADE", "RESOLVED_WITHOUT_CONID"),
            gate("entitlements_sufficient", "BLOCK", "UNEVALUABLE"),
        ],
        "evidence_ids": [],
        "risk_summary": "synthetic",
        "scenario_ids": [],
        "probability_evidence": None,
        "limitations": ["SYNTHETIC development population"],
        "explanation_facts": [],
        "supersedes": None,
    },
    "coverage": {
        "observations_considered": 1,
        "rejected_records": [],
        "lookback_seconds": 259200,
    },
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


def test_requires_a_real_session(client: TestClient) -> None:
    assert client.get(f"/api/v1/analysis/{INSTRUMENT}").status_code == 401


def test_no_snapshot_is_honest_empty_200(authenticated: TestClient) -> None:
    body = authenticated.get(f"/api/v1/analysis/{INSTRUMENT}").json()
    assert body["state"] == "empty"
    assert body["instrument"] == INSTRUMENT
    assert body["advice"] is None
    assert body["reason"] == "no snapshot published"


def test_published_dossier_round_trips_exactly(
    authenticated: TestClient, db_session: Session
) -> None:
    published = publish_snapshot(
        db_session,
        kind="analysis",
        key=INSTRUMENT,
        content=ANALYSIS_CONTENT,
        as_of=NOW,
    )
    db_session.commit()

    response = authenticated.get(f"/api/v1/analysis/{INSTRUMENT}")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "ok"
    assert body["snapshot_version"] == published.version == 1
    assert body["population"] == "SYNTHETIC"
    assert body["bars"] == ANALYSIS_CONTENT["bars"]
    assert body["evidence"] == ANALYSIS_CONTENT["evidence"]
    assert body["scenarios"] == ANALYSIS_CONTENT["scenarios"]
    assert body["advice"] == ANALYSIS_CONTENT["advice"]
    assert body["advice"]["status"] == "INSUFFICIENT_DATA"

    other = authenticated.get("/api/v1/analysis/SYN-TECH-02").json()
    assert other["state"] == "empty"
