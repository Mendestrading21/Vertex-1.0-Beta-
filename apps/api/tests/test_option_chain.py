"""GET /api/v1/options/{underlying}/chain: verbatim relay, honest empty, 401.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.options.build_option_chain_content``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_snapshot_reader
from vertex_api.snapshot_views import (
    SnapshotContentError,
    build_option_chain_response,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
UNDERLYING = "SYN-TECH-01"


def contract_entry(con_id: int, strike: str, right: str, trading_class: str) -> dict:
    return {
        "con_id": con_id,
        "strike": strike,
        "right": right,
        "expiration": "2026-09-22",
        "trading_class": trading_class,
        "multiplier": 100,
        "currency": "SYN",
        "exchange": "SYNTH",
        "style": "EUROPEAN",
        "settlement": "CASH",
        "quote": {
            "bid": "8.10",
            "ask": "8.60",
            "bid_size": 10,
            "ask_size": 12,
            "observed_at": (AS_OF - timedelta(minutes=30)).isoformat(),
            "age_seconds": 1800,
            "status": "OK",
        },
        "volume": 154,
        "open_interest": 1200,
        "open_interest_status": "OI_DELAYED",
        "iv": {
            "status": "OK",
            "value": "0.251234",
            "quote_side": "MID",
            "value_nature": "THEORETICAL",
            "calculation": {
                "calculation_id": "options.implied_volatility",
                "engine_version": "vertex_core@0.1.0",
                "method": "brentq bracketed BSM inversion on the quote MID",
                "input_hash": "sha256:" + "a" * 64,
                "result_hash": "sha256:" + "b" * 64,
                "status": "OK",
            },
        },
        "greeks": {
            "status": "ABSENT",
            "reason": "iv_unresolved",
        },
        "synthetic": True,
    }


def expiration_group(trading_class: str, contracts: list[dict]) -> dict:
    return {
        "expiration": "2026-09-22",
        "trading_class": trading_class,
        "exchange": "SYNTH",
        "style": "EUROPEAN",
        "settlement": "CASH",
        "multiplier": 100,
        "currency": "SYN",
        "maturity_years": "0.076712",
        "quality": "VALID",
        "source_event_id": f"synthetic-dev:t:{trading_class}",
        "contracts": contracts,
        "coverage": {
            "expected": len(contracts),
            "quotes_received": len(contracts),
            "quotes_valid": len(contracts),
            "iv_resolved": len(contracts),
            "discarded": [],
        },
    }


def chain_content() -> dict:
    """SYNTHETIC copy of the worker's published option-chain content shape."""
    return {
        "schema_version": "vertex.option-chain/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "underlying": UNDERLYING,
        "engine_version": "vertex_core@0.1.0",
        "value_nature": "THEORETICAL",
        "spot": {
            "value": "245.50",
            "currency": "SYN",
            "observed_at": AS_OF.isoformat(),
            "source_event_id": "synthetic-dev:t:oc0001",
        },
        "assumptions": {
            "rate": "0.02",
            "dividend_yield": "0.00",
            "quote_side_for_iv": "MID",
            "max_quote_age_seconds": 21600,
        },
        "expirations": [
            expiration_group(
                UNDERLYING,
                [contract_entry(1, "240.00", "CALL", UNDERLYING)],
            ),
            expiration_group(
                f"{UNDERLYING}W",
                [contract_entry(2, "240.00", "CALL", f"{UNDERLYING}W")],
            ),
        ],
        "row_budget": {
            "max_rows": 240,
            "total_rows": 2,
            "published_rows": 2,
            "truncated_rows": 0,
        },
        "coverage": {
            "observations_considered": 2,
            "groups_published": 2,
            "rejected_records": [],
            "lookback_seconds": 259200,
        },
    }


def snapshot(content: dict, *, key: str = UNDERLYING) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="option_chain",
        key=key,
        version=3,
        content=content,
        content_hash="sha256:" + "c" * 64,
        as_of=AS_OF,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def option_client(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def test_requires_a_session(client: TestClient) -> None:
    assert client.get(f"/api/v1/options/{UNDERLYING}/chain").status_code == 401


def test_invalid_underlying_shape_is_rejected(option_client: TestClient) -> None:
    assert option_client.get("/api/v1/options/a%20b/chain").status_code == 422


def test_no_snapshot_is_honest_empty_200(option_client: TestClient) -> None:
    response = option_client.get(f"/api/v1/options/{UNDERLYING}/chain")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["underlying"] == UNDERLYING
    assert body["as_of"] is None
    assert body["spot"] is None
    assert body["expirations"] == []
    assert body["reason"] == "no snapshot published"


def test_published_snapshot_is_relayed_verbatim(
    option_client: TestClient, reader: FakeSnapshotReader
) -> None:
    content = chain_content()
    reader.snapshots[("option_chain", UNDERLYING)] = snapshot(content)

    response = option_client.get(f"/api/v1/options/{UNDERLYING}/chain")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "ok"
    assert body["snapshot_version"] == 3
    assert body["population"] == "SYNTHETIC"
    assert body["value_nature"] == "THEORETICAL"
    assert body["spot"] == content["spot"]
    assert body["assumptions"] == content["assumptions"]
    assert body["row_budget"] == content["row_budget"]
    assert body["coverage"] == content["coverage"]

    # The two trading classes of the SAME expiration stay separated.
    groups = [(g["expiration"], g["trading_class"]) for g in body["expirations"]]
    assert groups == [
        ("2026-09-22", UNDERLYING),
        ("2026-09-22", f"{UNDERLYING}W"),
    ]

    entry = body["expirations"][0]["contracts"][0]
    published = content["expirations"][0]["contracts"][0]
    assert entry["con_id"] == 1
    assert entry["quote"] == published["quote"]
    assert entry["iv"] == published["iv"]
    assert entry["greeks"] == published["greeks"]
    assert entry["trading_class"] == UNDERLYING


def test_snapshot_for_another_underlying_is_refused(reader) -> None:
    content = chain_content()
    with pytest.raises(SnapshotContentError):
        build_option_chain_response(snapshot(content), underlying="SYN-TECH-02")


def test_missing_value_nature_is_refused() -> None:
    content = chain_content()
    del content["value_nature"]
    with pytest.raises(SnapshotContentError):
        build_option_chain_response(snapshot(content), underlying=UNDERLYING)


def test_iv_block_without_status_is_refused() -> None:
    content = chain_content()
    del content["expirations"][0]["contracts"][0]["iv"]["status"]
    with pytest.raises(SnapshotContentError):
        build_option_chain_response(snapshot(content), underlying=UNDERLYING)
