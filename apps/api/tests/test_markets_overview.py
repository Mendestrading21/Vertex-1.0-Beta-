"""GET /api/v1/markets/overview: last published snapshot verbatim, honest empty.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.markets.build_markets_overview_content``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import (
    SnapshotContentError,
    build_markets_overview_response,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

#: Horloge du relais, injectée (voir test_today_attention.py) : une horloge
#: RÉELLE rendrait l'instantané périmé au fil des jours et ferait échouer ces
#: tests sans qu'aucun comportement ait changé.
_NOW = AS_OF + timedelta(minutes=30)


def ticker_entry(ticker: str, sector: str, *, pct: str = "+10.00") -> dict:
    return {
        "ticker": ticker,
        "sector": sector,
        "trading_day": "2026-08-24",
        "previous_trading_day": "2026-08-23",
        "last_close": "110.00",
        "previous_close": "100.00",
        "currency": "SYN",
        "return_1d": "0.10000000000000009",
        "return_1d_pct": pct,
        "weight_in_sector": "0.709677",
        "weight_in_sector_pct": "70.97",
        "weight_global": "0.354838",
        "weight_global_pct": "35.48",
        "quality": "VALID",
        "synthetic": True,
        "calculation": {
            "calculation_id": "market.simple_return",
            "engine_version": "vertex_core@0.1.0",
            "method": "simple_return p1/p0 - 1 (1 trading day)",
            "input_hash": "sha256:" + "a" * 64,
            "result_hash": "sha256:" + "b" * 64,
            "status": "OK",
        },
    }


def markets_content() -> dict:
    """SYNTHETIC copy of the worker's published markets content shape."""
    return {
        "schema_version": "vertex.markets-overview/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "data_state": "partial",
        "unit": "return_ratio",
        "display_unit": "%",
        "engine_version": "vertex_core@0.1.0",
        "conclusion": (
            "Sur 4 instruments synthétiques attendus, 2 sont couverts et 2 "
            "écartés ; 2 en hausse, 0 en baisse, 0 stables ; breadth 100.0 % "
            "(seuil de couverture 50.0 %)."
        ),
        "sectors": [
            {
                "sector": "SYN-AAA",
                "label": "Secteur AAA",
                "declared_count": 2,
                "covered_count": 2,
                "tickers": [
                    ticker_entry("SYN-AAA-01", "SYN-AAA"),
                    ticker_entry("SYN-AAA-02", "SYN-AAA"),
                ],
            },
            {
                "sector": "SYN-BBB",
                "label": "Secteur BBB",
                "declared_count": 2,
                "covered_count": 0,
                "tickers": [],
            },
        ],
        "breadth": {
            "status": "OK",
            "reason": None,
            "value": "1",
            "value_pct": "100.0",
            "above_count": 2,
            "covered_count": 2,
            "universe_size": 4,
            "coverage_pct": "50.0",
            "coverage_threshold": "0.5",
            "coverage_threshold_pct": "50.0",
            "calculation": {
                "calculation_id": "market.breadth",
                "engine_version": "vertex_core@0.1.0",
                "method": "participation ratio above_count / covered_count",
                "input_hash": "sha256:" + "c" * 64,
                "result_hash": "sha256:" + "d" * 64,
                "status": "OK",
            },
        },
        "coverage": {
            "expected": 4,
            "received": 3,
            "covered": 2,
            "discarded": 2,
            "discarded_tickers": [
                {"ticker": "SYN-BBB-01", "reason": "missing_close"},
                {"ticker": "SYN-BBB-02", "reason": "missing_close"},
            ],
            "rejected_records": [
                {"event_id": "x:rights", "reason": "rights_not_usable"}
            ],
            "observations_considered": 7,
            "lookback_seconds": 259200,
        },
    }


def markets_snapshot(version: int = 3) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="markets_overview",
        key="global",
        version=version,
        content=markets_content(),
        content_hash="sha256:" + "e" * 64,
        as_of=AS_OF,
    )


def override(app: FastAPI, reader: FakeSnapshotReader) -> None:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    # Horloge FIXE : sans elle, le relais mesurerait l'âge de l'instantané
    # contre l'heure réelle et le déclarerait périmé quelques jours après
    # l'écriture de ce test, sans qu'aucun code ait changé.
    app.dependency_overrides[get_clock] = lambda: (lambda: _NOW)


def test_requires_authentication(app: FastAPI, client: TestClient) -> None:
    response = client.get("/api/v1/markets/overview")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_empty_state_when_never_published(app: FastAPI) -> None:
    override(app, FakeSnapshotReader())
    with TestClient(app) as client:
        response = client.get("/api/v1/markets/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["snapshot_version"] is None
    assert body["as_of"] is None
    assert body["population"] is None
    assert body["data_state"] is None
    assert body["sectors"] == []
    assert body["breadth"] is None
    assert body["coverage"] is None
    assert body["reason"] == "no snapshot published"


def test_relays_published_snapshot_verbatim(app: FastAPI) -> None:
    reader = FakeSnapshotReader({("markets_overview", "global"): markets_snapshot()})
    override(app, reader)
    with TestClient(app) as client:
        response = client.get("/api/v1/markets/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert body["snapshot_version"] == 3
    assert body["population"] == "SYNTHETIC"
    assert body["data_state"] == "partial"
    assert body["unit"] == "return_ratio"
    assert body["display_unit"] == "%"
    assert body["conclusion"].startswith("Sur 4 instruments synthétiques")

    sectors = body["sectors"]
    assert [s["sector"] for s in sectors] == ["SYN-AAA", "SYN-BBB"]
    ticker = sectors[0]["tickers"][0]
    # Decimal strings relayed VERBATIM — never re-parsed into floats.
    assert ticker["last_close"] == "110.00"
    assert ticker["return_1d"] == "0.10000000000000009"
    assert ticker["return_1d_pct"] == "+10.00"
    assert ticker["weight_in_sector"] == "0.709677"
    assert ticker["synthetic"] is True
    assert ticker["calculation"]["engine_version"] == "vertex_core@0.1.0"
    assert ticker["calculation"]["input_hash"].startswith("sha256:")

    breadth = body["breadth"]
    assert breadth["status"] == "OK"
    assert breadth["value_pct"] == "100.0"
    assert breadth["calculation"]["calculation_id"] == "market.breadth"

    coverage = body["coverage"]
    assert coverage["expected"] == 4
    assert coverage["discarded"] == 2
    assert coverage["discarded_tickers"][0] == {
        "ticker": "SYN-BBB-01",
        "reason": "missing_close",
    }
    assert coverage["rejected_records"][0]["reason"] == "rights_not_usable"


def test_invalid_breadth_block_is_relayed_honestly(app: FastAPI) -> None:
    content = markets_content()
    content["breadth"] = {
        "status": "INVALID",
        "reason": "coverage_below_threshold",
        "value": None,
        "value_pct": None,
        "above_count": 1,
        "covered_count": 1,
        "universe_size": 4,
        "coverage_pct": "25.0",
        "coverage_threshold": "0.5",
        "coverage_threshold_pct": "50.0",
        "calculation": None,
    }
    snapshot = CurrentSnapshot(
        kind="markets_overview",
        key="global",
        version=1,
        content=content,
        content_hash="sha256:" + "f" * 64,
        as_of=AS_OF,
    )
    reader = FakeSnapshotReader({("markets_overview", "global"): snapshot})
    override(app, reader)
    with TestClient(app) as client:
        response = client.get("/api/v1/markets/overview")
    body = response.json()
    assert body["breadth"]["status"] == "INVALID"
    assert body["breadth"]["value"] is None
    assert body["breadth"]["reason"] == "coverage_below_threshold"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.pop("population"),
        lambda c: c.pop("conclusion"),
        lambda c: c.update(data_state="great"),
        lambda c: c.update(as_of="2026-08-25T12:00:00"),  # naive datetime
        lambda c: c["sectors"][0]["tickers"][0].pop("last_close"),
        lambda c: c["sectors"][0]["tickers"][0].update(synthetic="yes"),
        lambda c: c["breadth"].update(status="MAYBE"),
        lambda c: c["coverage"].pop("discarded_tickers"),
    ],
)
def test_malformed_content_fails_closed(mutate) -> None:
    content = markets_content()
    mutate(content)
    snapshot = CurrentSnapshot(
        kind="markets_overview",
        key="global",
        version=1,
        content=content,
        content_hash="sha256:" + "0" * 64,
        as_of=AS_OF,
    )
    with pytest.raises(SnapshotContentError):
        build_markets_overview_response(snapshot, now=_NOW)
