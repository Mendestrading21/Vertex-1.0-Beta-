"""GET /api/v1/markets/overview against real PostgreSQL and real passkey auth.

The snapshot content is built by the REAL worker builder
(``vertex_worker.markets.build_markets_overview_content``) over synthetic
daily-quote records, persisted through the real repository, then read back
through the protected API — no dependency override anywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from soft_passkey import SoftPasskey, login_passkey, register_passkey
from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_persistence.repository.snapshots import publish_snapshot
from vertex_worker.markets import (
    MarketsConfig,
    QuoteRecord,
    build_markets_overview_content,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)

CONFIG = MarketsConfig(
    universe={"SYN-AAA": ("SYN-AAA-01", "SYN-AAA-02")},
    sector_labels={"SYN-AAA": "Secteur AAA"},
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
    coverage_threshold=Decimal("0.5"),
)


def quote(ticker: str, day: str, close: str) -> QuoteRecord:
    return QuoteRecord(
        event_id=f"{SYNTHETIC_SOURCE}:it:{ticker}:{day}",
        source=SYNTHETIC_SOURCE,
        instrument_ref=ticker,
        as_of=NOW,
        quality_status="VALID",
        rights=SYNTHETIC_RIGHTS,
        schema_version="synthetic-daily-quote/1.0",
        payload={
            "type": "daily_quote",
            "synthetic": True,
            "ticker": ticker,
            "sector": "SYN-AAA",
            "trading_day": day,
            "close": close,
            "currency": "SYN",
            "adjustment_basis": "synthetic-unadjusted",
        },
    )


MARKETS_CONTENT = build_markets_overview_content(
    [
        quote("SYN-AAA-01", "2026-08-23", "100.00"),
        quote("SYN-AAA-01", "2026-08-24", "104.00"),
        quote("SYN-AAA-02", "2026-08-24", "50.00"),  # missing older close
    ],
    now=NOW,
    config=CONFIG,
)


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


class TestMarketsOverview:
    def test_requires_a_real_session(self, client: TestClient) -> None:
        assert client.get("/api/v1/markets/overview").status_code == 401

    def test_no_snapshot_is_honest_empty_200(self, authenticated: TestClient) -> None:
        response = authenticated.get("/api/v1/markets/overview")
        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "empty"
        assert body["as_of"] is None
        assert body["sectors"] == []
        assert body["breadth"] is None
        assert body["reason"] == "no snapshot published"

    def test_published_snapshot_round_trips_exactly(
        self, authenticated: TestClient, db_session: Session
    ) -> None:
        published = publish_snapshot(
            db_session,
            kind="markets_overview",
            key="global",
            content=MARKETS_CONTENT,
            as_of=NOW,
        )
        db_session.commit()

        response = authenticated.get("/api/v1/markets/overview")
        assert response.status_code == 200
        body = response.json()

        assert body["state"] == "ok"
        assert body["snapshot_version"] == published.version == 1
        assert body["as_of"] == "2026-08-25T12:00:00Z"
        assert body["population"] == "SYNTHETIC"
        assert body["data_state"] == "partial"  # one ticker discarded
        assert body["unit"] == "return_ratio"
        assert body["display_unit"] == "%"
        assert body["conclusion"] == MARKETS_CONTENT["conclusion"]

        assert len(body["sectors"]) == 1
        sector = body["sectors"][0]
        assert sector["sector"] == "SYN-AAA"
        assert sector["label"] == "Secteur AAA"
        assert sector["covered_count"] == 1

        ticker = sector["tickers"][0]
        assert ticker["ticker"] == "SYN-AAA-01"
        assert ticker["last_close"] == "104.00"
        assert ticker["previous_close"] == "100.00"
        assert ticker["return_1d_pct"] == "+4.00"
        assert ticker["weight_in_sector"] == "1.000000"
        assert ticker["synthetic"] is True
        assert ticker["calculation"]["calculation_id"] == "market.simple_return"
        assert ticker["calculation"]["input_hash"].startswith("sha256:")

        breadth = body["breadth"]
        assert breadth["status"] == "OK"  # coverage 1/2 >= 0.5
        assert breadth["above_count"] == 1
        assert breadth["value"] == "1.0"
        assert breadth["calculation"]["calculation_id"] == "market.breadth"

        coverage = body["coverage"]
        assert coverage["expected"] == 2
        assert coverage["covered"] == 1
        assert coverage["discarded"] == 1
        assert coverage["discarded_tickers"] == [
            {"ticker": "SYN-AAA-02", "reason": "missing_close"}
        ]
