"""Shared fixtures for the Vertex One API tests.

Every payload here is SYNTHETIC and deterministic — no real market data, no
network, no clock, no database. Sessions are injected through
``app.dependency_overrides`` with an explicit test-only ``SessionContext``;
the REAL authentication path (WebAuthn ceremony, database session, CSRF) is
exercised end-to-end in ``apps/api/tests_integration`` against PostgreSQL.
"""

from typing import Any, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vertex_api.app import create_app
from vertex_api.auth import SessionContext, require_session


def _synthetic_test_session() -> SessionContext:
    """Explicit SYNTHETIC session: only reachable via dependency_overrides."""
    return SessionContext(subject="synthetic-test-user", established_via="TEST_OVERRIDE")


@pytest.fixture()
def app() -> FastAPI:
    """A fresh application per test (no shared state between tests)."""
    return create_app()


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    """Client with NO session override nor cookie: the fail-closed 401 path."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def authenticated_client(app: FastAPI) -> Iterator[TestClient]:
    """Client with an EXPLICIT synthetic test session (never a production path)."""
    app.dependency_overrides[require_session] = _synthetic_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def build_all_pass_payload() -> dict[str, Any]:
    """SYNTHETIC advice inputs that make all ten gates PASS (QUALIFIED)."""
    return {
        "instrument_id": "SYNTH:NASDAQ:STK:USD",
        "as_of": "2026-08-01T12:00:00Z",
        "valid_until": "2026-08-01T13:00:00Z",
        "input_snapshot_id": "synthetic-snapshot-1",
        "horizon": "1d",
        "direction": "NEUTRAL",
        "risk_summary": "synthetic risk summary for tests",
        "evidence_ids": ["synthetic-evidence-1"],
        "scenario_ids": ["synthetic-scenario-1"],
        "explanation_facts": ["synthetic explanation fact"],
        "instrument": {"identity_status": "RESOLVED", "resolved_with_conid": True},
        "entitlements": {"capability_status": "AVAILABLE"},
        "snapshot": {"quality": "GOOD", "fresh": True},
        "session_event": {"session_known": True, "event_calendar_known": True},
        "liquidity": {
            "asset_class": "STOCK",
            "observed_liquidity": "1000000.50",
            "required_minimum": "500000",
            "observation_delayed": False,
        },
        "calculations": {"calculation_statuses": {"synthetic_calculation": "OK"}},
        "portfolio_risk": {
            "risk_required": True,
            "portfolio_risk_available": True,
            "declarations_current": True,
        },
        "probability": {"probability_used": False},
        "contradictions": {
            "unresolved_critical_count": 0,
            "explicit_contradiction_count": 0,
        },
        "constraints": {"constraints_version": "v1", "constraints_current": True},
    }


@pytest.fixture()
def all_pass_payload() -> dict[str, Any]:
    """Fresh copy of the all-PASS synthetic payload."""
    return build_all_pass_payload()
