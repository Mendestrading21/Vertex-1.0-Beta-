"""Option-chain route against real PostgreSQL and REAL passkey authentication.

A SYNTHETIC ``option_chain/{underlying}`` snapshot (worker shape) is
published through the real repository, then read back through the protected
API: no dependency override anywhere.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from soft_passkey import SoftPasskey, login_passkey, register_passkey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from vertex_persistence.repository.snapshots import publish_snapshot

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

#: Instant de PUBLICATION de la ligne d'instantané, distinct du `as_of` du
#: CONTENU : le relais mesure la fraîcheur sur celui-ci. Le contenu date sa
#: vérité métier, la ligne date sa publication. Ancré sur l'horloge réelle,
#: comme le fait déjà `test_calendar_opportunities_api_e2e.py`, sinon ces
#: tests se déclareraient périmés tout seuls avec le temps.
PUBLIE_A = datetime.now(UTC) - timedelta(minutes=5)
UNDERLYING = "SYN-TECH-01"

CHAIN_CONTENT = {
    "schema_version": "vertex.option-chain/1.0",
    "as_of": NOW.isoformat(),
    "population": "SYNTHETIC",
    "underlying": UNDERLYING,
    "engine_version": "vertex_core@0.1.0",
    "value_nature": "THEORETICAL",
    "spot": {
        "value": "245.50",
        "currency": "SYN",
        "observed_at": NOW.isoformat(),
        "source_event_id": "synthetic-dev:e2e:oc0001",
    },
    "assumptions": {
        "rate": "0.02",
        "dividend_yield": "0.00",
        "quote_side_for_iv": "MID",
        "max_quote_age_seconds": 21600,
    },
    "expirations": [
        {
            "expiration": "2026-09-22",
            "trading_class": UNDERLYING,
            "exchange": "SYNTH",
            "style": "EUROPEAN",
            "settlement": "CASH",
            "multiplier": 100,
            "currency": "SYN",
            "maturity_years": "0.076712",
            "quality": "PARTIAL",
            "source_event_id": "synthetic-dev:e2e:oc0001",
            "contracts": [
                {
                    "con_id": 900000001,
                    "strike": "240.00",
                    "right": "CALL",
                    "expiration": "2026-09-22",
                    "trading_class": UNDERLYING,
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
                        "observed_at": NOW.isoformat(),
                        "age_seconds": 0,
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
                    "greeks": {"status": "ABSENT", "reason": "iv_unresolved"},
                    "synthetic": True,
                },
                {
                    "con_id": 900000002,
                    "strike": "240.00",
                    "right": "PUT",
                    "expiration": "2026-09-22",
                    "trading_class": UNDERLYING,
                    "multiplier": 100,
                    "currency": "SYN",
                    "exchange": "SYNTH",
                    "style": "EUROPEAN",
                    "settlement": "CASH",
                    "quote": {
                        "bid": "5.20",
                        "ask": "5.10",
                        "bid_size": 4,
                        "ask_size": 6,
                        "observed_at": NOW.isoformat(),
                        "age_seconds": 0,
                        "status": "CROSSED",
                    },
                    "volume": 33,
                    "open_interest": 456,
                    "open_interest_status": "OI_DELAYED",
                    "iv": {"status": "ABSENT", "reason": "crossed_quote"},
                    "greeks": {"status": "ABSENT", "reason": "iv_unresolved"},
                    "synthetic": True,
                },
            ],
            "coverage": {
                "expected": 2,
                "quotes_received": 2,
                "quotes_valid": 1,
                "iv_resolved": 1,
                "discarded": [
                    {
                        "con_id": 900000002,
                        "strike": "240.00",
                        "right": "PUT",
                        "reason": "crossed_quote",
                    }
                ],
            },
        }
    ],
    "row_budget": {
        "max_rows": 240,
        "total_rows": 2,
        "published_rows": 2,
        "truncated_rows": 0,
    },
    "coverage": {
        "observations_considered": 1,
        "groups_published": 1,
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
    assert client.get(f"/api/v1/options/{UNDERLYING}/chain").status_code == 401


def test_no_snapshot_is_honest_empty_200(authenticated: TestClient) -> None:
    response = authenticated.get(f"/api/v1/options/{UNDERLYING}/chain")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["underlying"] == UNDERLYING
    assert body["expirations"] == []
    assert body["reason"] == "no snapshot published"


def test_published_chain_round_trips_exactly(
    authenticated: TestClient, db_session: Session
) -> None:
    published = publish_snapshot(
        db_session,
        kind="option_chain",
        key=UNDERLYING,
        content=CHAIN_CONTENT,
        as_of=PUBLIE_A,
    )
    db_session.commit()

    response = authenticated.get(f"/api/v1/options/{UNDERLYING}/chain")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "ok"
    assert body["snapshot_version"] == published.version == 1
    assert body["population"] == "SYNTHETIC"
    assert body["value_nature"] == "THEORETICAL"
    assert body["spot"] == CHAIN_CONTENT["spot"]
    assert body["assumptions"] == CHAIN_CONTENT["assumptions"]
    assert body["row_budget"] == CHAIN_CONTENT["row_budget"]

    (group,) = body["expirations"]
    assert group["trading_class"] == UNDERLYING
    assert group["coverage"] == CHAIN_CONTENT["expirations"][0]["coverage"]
    sane, crossed = group["contracts"]
    assert sane["iv"]["status"] == "OK"
    assert sane["iv"]["value_nature"] == "THEORETICAL"
    assert crossed["quote"]["status"] == "CROSSED"
    assert crossed["iv"] == {"status": "ABSENT", "reason": "crossed_quote"}

    # A different underlying still answers its own honest empty state.
    other = authenticated.get("/api/v1/options/SYN-TECH-02/chain").json()
    assert other["state"] == "empty"
