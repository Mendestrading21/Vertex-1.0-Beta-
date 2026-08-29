"""Performance chain against real PostgreSQL, passkey auth, CSRF and worker.

No dependency override: daily-quote observations ingested through the real
``ingest_envelope``, ledger facts recorded through the real portfolio routes
(deposit + buy + sell), a bounded REAL worker run rebuilding the
``performance/<id>`` snapshot, read back through ``GET /api/v1/performance``
with the TWR verified BY HAND in this test, and a byte-reproducible export.
All data is SYNTHETIC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from soft_passkey import SoftPasskey, login_passkey, register_passkey
from vertex_core.contracts import DataEnvelope, canonical_json_hash
from vertex_core.contracts.enums import DelayStatus, EnvelopeQuality
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

CSRF_HEADER = "X-Vertex-CSRF"
CSRF_COOKIE = "vertex_csrf"

TICKER = "SYN-TECH-01"
SECTOR = "SYN-TECH"
CURRENCY = "SYN"  # the synthetic mark universe's fictional currency code
TOLERANCE = Decimal("1e-18")

NOW = datetime.now(timezone.utc).replace(microsecond=0)
# Three past synthetic trading days (D1 < D2 < D3), all strictly before now.
DAY1 = (NOW - timedelta(days=3)).date()
DAY2 = (NOW - timedelta(days=2)).date()
DAY3 = (NOW - timedelta(days=1)).date()
CLOSES = {DAY1.isoformat(): "100", DAY2.isoformat(): "110", DAY3.isoformat(): "121"}


def at(day, hour: int) -> datetime:
    return datetime(day.year, day.month, day.day, hour, 0, 0, tzinfo=timezone.utc)


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


@pytest.fixture()
def drain_worker(database_url: str):
    """Bounded REAL worker run over the same database (no daemon thread)."""
    engine = create_engine(database_url)

    def factory() -> Session:
        return Session(engine)

    def drain() -> None:
        runner = WorkerRunner(
            session_factory=factory,
            registry=build_registry(
                clock=lambda: datetime.now(timezone.utc),
                fusion_config=DEV_SYNTHETIC_CONFIG,
            ),
            poll_interval_seconds=0.05,
            clock=lambda: datetime.now(timezone.utc),
        )
        runner.drain(max_batches=40)
        stats = runner.stats()
        assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0
        with factory() as session:
            remaining = session.execute(
                select(func.count())
                .select_from(OutboxMessage)
                .where(OutboxMessage.status != OutboxStatus.DONE.value)
            ).scalar_one()
        assert remaining == 0

    try:
        yield drain
    finally:
        engine.dispose()


def _csrf(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE)
    assert token
    return {CSRF_HEADER: token}


def _quote_envelope(day, close: str) -> DataEnvelope[dict]:
    published = at(day, 21)
    payload = {
        "type": "daily_quote",
        "synthetic": True,
        "ticker": TICKER,
        "sector": SECTOR,
        "trading_day": day.isoformat(),
        "close": close,
        "currency": CURRENCY,
        "adjustment_basis": "synthetic-unadjusted",
        "note": "[SYNTHETIC] fixture daily close; generated, never real data.",
    }
    return DataEnvelope[dict](
        event_id=f"e2e-dq-{TICKER}-{day.isoformat()}",
        schema_version="synthetic-daily-quote/1.0",
        source="synthetic-dev",
        source_event_id=f"syn-dq-{TICKER}-{day.isoformat()}",
        instrument_id=TICKER,
        observed_at=published,
        published_at=published,
        received_at=published + timedelta(seconds=30),
        as_of=published + timedelta(seconds=30),
        stale_after=published + timedelta(hours=12),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.UNKNOWN,
        rights="SYNTHETIC",
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


def _record(client: TestClient, **overrides) -> int:
    payload = {
        "kind": "DEPOSIT",
        "amount": "0",
        "currency": CURRENCY,
        "fees": "0",
        "effective_at": at(DAY1, 9).isoformat(),
        **overrides,
    }
    response = client.post(
        "/api/v1/portfolio/transactions", json=payload, headers=_csrf(client)
    )
    assert response.status_code == 201, response.text
    return response.json()["transaction_id"]


def test_deposit_buy_sell_marks_to_verified_performance_snapshot(
    authenticated: TestClient, db_session: Session, drain_worker
) -> None:
    """Hand-verified TWR over two periods (values recomputed in comments).

    Ledger (all SYNTHETIC, recorded AFTER the facts, outside Vertex):
      D1 09:00  DEPOSIT     +10000
      D1 11:00  BUY 10 @ 100  (amount -1000)
      D2 12:00  DEPOSIT      +1000
      D2 13:00  SELL 5 @ 110  (amount +550)
    Synthetic closes: D1=100, D2=110, D3=121.

    End-of-day valuations (gross):
      V(D1) = cash(10000 - 1000)          + 10 x 100 = 9000  + 1000 = 10000
      V(D2) = cash(9000 + 1000 + 550)     +  5 x 110 = 10550 + 550  = 11100
      V(D3) = cash(10550)                 +  5 x 121 = 10550 + 605  = 11155

    TWR (flows stamped at period start; the D1 deposit is on the first
    valued day, hence part of the opening value; the D2 deposit adjusts the
    period ENDING at D2's close):
      period 1 (D1 -> D2): r1 = 11100 / (10000 + 1000) - 1 = 100/11000
      period 2 (D2 -> D3): r2 = 11155 / 11100 - 1          = 55/11100
      total = (1+r1)(1+r2) - 1 = 11155/11000 - 1            = 155/11000
    """
    # --- marks: 3 daily closes ingested through the real pipeline ----------
    for day, close in ((DAY1, CLOSES[DAY1.isoformat()]),
                       (DAY2, CLOSES[DAY2.isoformat()]),
                       (DAY3, CLOSES[DAY3.isoformat()])):
        result = ingest_envelope(db_session, _quote_envelope(day, close))
        assert result.inserted
    db_session.commit()

    # --- ledger: deposit + buy + sell + second deposit ---------------------
    _record(authenticated, kind="DEPOSIT", amount="10000",
            effective_at=at(DAY1, 9).isoformat())
    _record(authenticated, kind="BUY_RECORDED", amount="-1000",
            instrument={"ticker": TICKER}, quantity="10", price="100",
            effective_at=at(DAY1, 11).isoformat())
    _record(authenticated, kind="DEPOSIT", amount="1000",
            effective_at=at(DAY2, 12).isoformat())
    _record(authenticated, kind="SELL_RECORDED", amount="550",
            instrument={"ticker": TICKER}, quantity="5", price="110",
            effective_at=at(DAY2, 13).isoformat())

    drain_worker()

    # --- GET /performance/{portfolio_id}: relayed snapshot -----------------
    response = authenticated.get("/api/v1/performance/1")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    content = body["content"]
    assert content["schema_version"] == "vertex.performance/1.0"
    assert content["population"] == "SYNTHETIC_MARKS_REAL_LEDGER"
    assert content["currency"] == CURRENCY
    assert content["lot_method"] == "fifo/1.0"

    points = content["series"]["points"]
    assert [p["trading_day"] for p in points] == sorted(CLOSES)
    assert [p["gross_value"] for p in points] == ["10000", "11100", "11155"]
    assert [p["cash"] for p in points] == ["9000", "10550", "10550"]
    assert content["series"]["excluded_days"] == []

    twr = content["metrics"]["twr_gross"]
    assert twr["status"] == "OK"
    assert len(twr["periods"]) == 2
    # Hand values (see docstring): r1 = 100/11000, r2 = 55/11100.
    assert abs(Decimal(twr["periods"][0]["return"]) - Decimal(100) / Decimal(11000)) < TOLERANCE
    assert abs(Decimal(twr["periods"][1]["return"]) - Decimal(55) / Decimal(11100)) < TOLERANCE
    assert abs(Decimal(twr["total_return"]) - Decimal(155) / Decimal(11000)) < TOLERANCE
    assert twr["cashflows_embedded_in_opening"] == 1
    assert twr["calculation"]["calculation_id"] == "performance.twr"
    assert twr["calculation"]["input_hash"].startswith("sha256:")

    # No fees declared: gross and net coincide but stay EXPLICITLY separate.
    twr_net = content["metrics"]["twr_net"]
    assert twr_net["status"] == "OK"
    assert twr_net["total_return"] == twr["total_return"]
    for point in points:
        assert point["net_value"] == point["gross_value"]

    xirr = content["metrics"]["xirr_gross"]
    assert xirr["status"] == "OK"
    assert Decimal(xirr["rate"]) > 0  # 155/11000 gained over ~2 days
    assert xirr["calculation"]["calculation_id"] == "performance.xirr"

    dd = content["metrics"]["drawdown_gross"]
    assert dd["status"] == "OK"
    assert dd["max_drawdown"] == "0"  # 10000 -> 11100 -> 11155: no decline
    assert dd["calculation"]["calculation_id"] == "performance.drawdown"

    coverage = content["coverage"]
    assert coverage["days_with_close"] == 3
    assert coverage["days_valued"] == 3
    assert coverage["coverage_ratio"] == "1.000000"
    assert coverage["external_cashflows"] == 2

    heatmap = content["heatmap"]
    assert heatmap["status"] == "OK"
    # Every month present is honestly marked: the series opens and closes
    # inside the covered window, so no month may claim completeness beyond
    # its own periods.
    for month in heatmap["months"]:
        assert isinstance(month["complete"], bool)
        if not month["complete"]:
            assert month["incomplete_reasons"]

    # --- export: reproducible bytes + audit manifest -----------------------
    first = authenticated.get("/api/v1/performance/1/export")
    second = authenticated.get("/api/v1/performance/1/export")
    assert first.status_code == 200
    # Two calls over the SAME snapshot version: byte-identical bodies.
    # (as_of is the snapshot's own instant — documented — so nothing in the
    # export depends on the request-time clock.)
    assert first.content == second.content
    export = first.json()
    assert export["schema_version"] == "vertex.performance-export/1.0"
    assert export["snapshot_version"] == body["snapshot_version"]

    lines = export["csv"].splitlines()
    assert lines[0] == "# vertex.performance-export/1.0"
    assert lines[1].startswith("trading_day,at,gross_value,net_value,")
    assert len(lines) == 5  # stamp + header + 3 daily points

    manifest = export["manifest"]
    assert manifest["population"] == "SYNTHETIC_MARKS_REAL_LEDGER"
    assert manifest["snapshot"]["kind"] == "performance"
    assert manifest["snapshot"]["version"] == body["snapshot_version"]
    assert manifest["snapshot"]["content_hash"].startswith("sha256:")
    twr_manifest = manifest["calculations"]["twr_gross"]["calculation"]
    assert twr_manifest["input_hash"] == twr["calculation"]["input_hash"]
    assert twr_manifest["result_hash"] == twr["calculation"]["result_hash"]
    assert manifest["conventions"]["net_definition"].startswith("net_value(day)")


def test_empty_state_and_export_404_before_any_snapshot(
    authenticated: TestClient,
) -> None:
    empty = authenticated.get("/api/v1/performance/1")
    assert empty.status_code == 200
    assert empty.json()["state"] == "empty"
    assert empty.json()["content"] is None

    export = authenticated.get("/api/v1/performance/1/export")
    assert export.status_code == 404
    assert export.json()["detail"]["code"] == "NO_PERFORMANCE_SNAPSHOT"
