"""Unit tests of the performance routes (SYNTHETIC fakes only).

Snapshot reader injected through ``app.dependency_overrides``; the real chain
(ledger writes -> worker -> snapshot -> export) runs in
``tests_integration/test_performance_api_e2e.py``.

Third re-audit (P1-G): this relay published ``dict(snapshot.content)`` with
no shape check, so any string-keyed payload was served ``200 state="ok"``.
The fixture below is therefore the COMPLETE shape
``vertex_worker.performance.build_performance_content`` really publishes —
an approximate fixture would have made the new shape check look satisfied
while proving nothing. The forged variants live in
``test_snapshot_content_errors.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_persistence.repository.snapshots import CurrentSnapshot

FIXED_NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

def _insufficient_metric() -> dict:
    """A metric the worker could not compute: reason, never an invented zero."""
    return {
        "status": "INSUFFICIENT_DATA",
        "reason": "not enough valued days on the synthetic series",
        "calculation": None,
    }


PERFORMANCE_CONTENT = {
    "schema_version": "vertex.performance/1.0",
    "as_of": FIXED_NOW.isoformat(),
    "engine_version": "0.1.0",
    "portfolio": {"id": 1, "name": "SYNTHETIC portfolio", "base_currency": "SYN"},
    "population": "SYNTHETIC_MARKS_REAL_LEDGER",
    "population_components": {"marks": "SYNTHETIC", "ledger": "USER_DECLARED"},
    "currency": "SYN",
    "lot_method": "fifo/1.0",
    "conventions": {"net_definition": "net = gross - cumulative declared fees"},
    "series": {
        "status": "OK",
        "reason": None,
        "points": [
            {
                "trading_day": "2026-08-24",
                "at": "2026-08-24T23:59:59+00:00",
                "gross_value": "10000",
                "net_value": "9995",
                "cash": "9000",
                "position_value": "1000",
                "fees_cumulative": "5",
                "lots_valued": 1,
            },
            {
                "trading_day": "2026-08-25",
                "at": "2026-08-25T23:59:59+00:00",
                "gross_value": "-10100",  # crafted to exercise CSV neutralization
                "net_value": "10095",
                "cash": "9000",
                "position_value": "1100",
                "fees_cumulative": "5",
                "lots_valued": 1,
            },
        ],
        "excluded_days": [],
    },
    "external_cashflows": [],
    "metrics": {
        "twr_net": _insufficient_metric(),
        "xirr_net": _insufficient_metric(),
        "drawdown_gross": _insufficient_metric(),
        "drawdown_net": _insufficient_metric(),
        "twr_gross": {
            "status": "OK",
            "reason": None,
            "total_return": "0.01",
            "calculation": {
                "calculation_id": "performance.twr",
                "engine_version": "0.1.0",
                "method": "chain-linked",
                "input_hash": "sha256:" + "1" * 64,
                "result_hash": "sha256:" + "2" * 64,
                "status": "OK",
            },
        },
        "xirr_gross": {
            "status": "INVALID",
            "reason": "no NPV sign change on the documented search grid",
            "calculation": None,
        },
    },
    "heatmap": {
        "status": "OK",
        "reason": None,
        "months": [],
        "derived_from_calculation": {"input_hash": "sha256:" + "1" * 64},
    },
    "coverage": {
        "days_with_close": 2,
        "days_valued": 2,
        "days_excluded": 0,
        "days_before_first_ledger_event": 0,
        "coverage_ratio": "1",
        "events_considered": 3,
        "external_cashflows": 0,
        "observations_considered": 4,
        "observations_truncated": False,
        "rejected_records": [],
    },
}

SNAPSHOT = CurrentSnapshot(
    kind="performance",
    key="1",
    version=7,
    content=PERFORMANCE_CONTENT,
    content_hash="sha256:" + "a" * 64,
    as_of=FIXED_NOW,
)


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader({("performance", "1"): SNAPSHOT})


@pytest.fixture()
def performance_client(app: FastAPI, reader: FakeSnapshotReader) -> Iterator[TestClient]:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    # Horloge FIXE : le relais publie désormais l'âge de l'instantané et
    # bascule en `stale` au-delà du budget. Sans horloge injectée, ce test
    # deviendrait rouge tout seul quelques jours après son écriture.
    app.dependency_overrides[get_clock] = lambda: (lambda: FIXED_NOW)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# -- fail-closed authentication ---------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/api/v1/performance/1", "/api/v1/performance/1/export"],
)
def test_every_performance_route_requires_a_session(client, path) -> None:
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


# -- GET /performance/{portfolio_id} -----------------------------------------


def test_performance_relays_snapshot_verbatim(performance_client) -> None:
    response = performance_client.get("/api/v1/performance/1")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert body["portfolio_id"] == 1
    assert body["snapshot_version"] == 7
    # VERBATIM: gates, INVALID reasons and population are relayed as-is.
    assert body["content"] == PERFORMANCE_CONTENT
    assert body["content"]["metrics"]["xirr_gross"]["status"] == "INVALID"
    assert body["reason"] is None


def test_performance_empty_state_is_honest(performance_client) -> None:
    response = performance_client.get("/api/v1/performance/2")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["portfolio_id"] == 2
    assert body["snapshot_version"] is None
    assert body["content"] is None
    assert body["reason"] == "no snapshot published"


def test_performance_rejects_non_positive_portfolio_id(performance_client) -> None:
    assert performance_client.get("/api/v1/performance/0").status_code == 422


# -- GET /performance/{portfolio_id}/export ----------------------------------


def test_export_is_reproducible_and_carries_the_lineage(performance_client) -> None:
    first = performance_client.get("/api/v1/performance/1/export")
    second = performance_client.get("/api/v1/performance/1/export")
    assert first.status_code == 200
    # Reproducible: identical snapshot version => identical bytes (as_of is
    # the snapshot's own instant, no request-time clock is injected).
    assert first.content == second.content

    body = first.json()
    assert body["schema_version"] == "vertex.performance-export/1.0"
    assert body["snapshot_version"] == 7
    # Wire encoding of the contract layer: UTC instants serialize with 'Z'.
    assert body["as_of"] == "2026-08-25T12:00:00Z"

    lines = body["csv"].splitlines()
    assert lines[0] == "# vertex.performance-export/1.0"
    assert lines[1].startswith("trading_day,at,gross_value,net_value,")
    assert len(lines) == 4  # stamp + header + 2 points
    assert "2026-08-24" in lines[2]
    assert "'-10100" in lines[3]  # spreadsheet formula-injection guard

    manifest = body["manifest"]
    assert manifest["snapshot"] == {
        "kind": "performance",
        "key": "1",
        "version": 7,
        "content_hash": "sha256:" + "a" * 64,
        "as_of": FIXED_NOW.isoformat(),
        "schema_version": "vertex.performance/1.0",
    }
    assert manifest["population"] == "SYNTHETIC_MARKS_REAL_LEDGER"
    twr = manifest["calculations"]["twr_gross"]
    assert twr["calculation"]["method"] == "chain-linked"
    assert twr["calculation"]["input_hash"] == "sha256:" + "1" * 64
    # A gate outcome without a computation is exported as-is: reason, no hash.
    xirr = manifest["calculations"]["xirr_gross"]
    assert xirr["status"] == "INVALID" and xirr["calculation"] is None
    assert manifest["coverage"] == PERFORMANCE_CONTENT["coverage"]


def test_export_without_snapshot_is_404(performance_client) -> None:
    response = performance_client.get("/api/v1/performance/2/export")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NO_PERFORMANCE_SNAPSHOT"
