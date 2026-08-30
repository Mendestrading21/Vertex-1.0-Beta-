"""Portfolio journal routes against real PostgreSQL, passkey auth and CSRF.

No dependency override anywhere: WebAuthn session cookie, CSRF double-submit
header, the real ledger repository (get-or-create ``main``, append-only
compensation), the real outbox and a bounded REAL worker run
(``vertex_worker``) that publishes the ``portfolio_valuation/<id>`` snapshot
read back through ``GET /api/v1/portfolio``. All data is SYNTHETIC.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from soft_passkey import SoftPasskey, login_passkey, register_passkey
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.snapshots import publish_snapshot
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.runner import WorkerRunner

CSRF_HEADER = "X-Vertex-CSRF"
CSRF_COOKIE = "vertex_csrf"

TOPIC_REFRESH = "portfolio.valuation.refresh"
TICKER = "SYN-TECH-01"
CURRENCY = "SYN"  # the synthetic mark universe's fictional currency code

NOW = datetime.now(UTC).replace(microsecond=0)
EFFECTIVE_AT = (NOW - timedelta(days=1)).isoformat()

MARKETS_CONTENT = {
    "schema_version": "vertex.markets-overview/1.0",
    "as_of": NOW.isoformat(),
    "population": "SYNTHETIC",
    "sectors": [
        {
            "sector": "SYN-TECH",
            "tickers": [
                {
                    "ticker": TICKER,
                    "last_close": "120.5",
                    "currency": CURRENCY,
                    "trading_day": "2026-08-24",
                }
            ],
        }
    ],
}

BUY_PAYLOAD = {
    "kind": "BUY_RECORDED",
    "instrument": {"ticker": TICKER},
    "quantity": "10",
    "price": "100",
    "amount": "-1000",
    "currency": CURRENCY,
    "fees": "0",
    "effective_at": EFFECTIVE_AT,
    "note": "SYNTHETIC fact recorded after an execution outside Vertex",
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
                clock=lambda: datetime.now(UTC),
                fusion_config=DEV_SYNTHETIC_CONFIG,
            ),
            poll_interval_seconds=0.05,
            clock=lambda: datetime.now(UTC),
        )
        runner.drain(max_batches=30)
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


def _publish_marks(db_session: Session) -> None:
    publish_snapshot(
        db_session,
        kind="markets_overview",
        key="global",
        content=MARKETS_CONTENT,
        as_of=NOW,
    )
    db_session.commit()


def test_mutations_without_csrf_are_generic_401(authenticated: TestClient) -> None:
    response = authenticated.post("/api/v1/portfolio/transactions", json=BUY_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    forged = authenticated.post(
        "/api/v1/portfolio/transactions",
        json=BUY_PAYLOAD,
        headers={CSRF_HEADER: "forged"},
    )
    assert forged.status_code == 401


def test_record_then_drain_then_get_is_coherent(
    authenticated: TestClient, db_session: Session, drain_worker
) -> None:
    _publish_marks(db_session)

    response = authenticated.post(
        "/api/v1/portfolio/transactions", json=BUY_PAYLOAD, headers=_csrf(authenticated)
    )
    assert response.status_code == 201, response.text
    transaction_id = response.json()["transaction_id"]

    # The refresh job was enqueued in the SAME transaction as the write.
    pending = db_session.execute(
        select(func.count())
        .select_from(OutboxMessage)
        .where(OutboxMessage.topic == TOPIC_REFRESH)
    ).scalar_one()
    assert pending == 1

    drain_worker()

    overview = authenticated.get("/api/v1/portfolio")
    assert overview.status_code == 200
    body = overview.json()
    assert body["portfolio"]["name"] == "main"  # created on first use
    assert [t["id"] for t in body["transactions"]] == [transaction_id]
    assert body["transactions"][0]["quantity"] == "10"
    assert body["transactions"][0]["source"] == "MANUAL"

    valuation = body["valuation"]
    assert valuation["state"] == "ok"
    content = valuation["content"]
    assert content["mark_population"] == "SYNTHETIC"
    group = content["positions_by_currency"][0]
    assert group["currency"] == CURRENCY
    # (120.5 - 100) * 10, computed by vertex_core, relayed verbatim.
    assert Decimal(group["unrealized"]["total_unrealized"]) == Decimal("205.0")
    assert group["unrealized"]["lots"][0]["lot_id"] == f"ledger-{transaction_id}"
    assert content["excluded_lots"] == []


def test_compensation_nets_to_zero_and_double_compensation_conflicts(
    authenticated: TestClient, db_session: Session, drain_worker
) -> None:
    _publish_marks(db_session)
    recorded = authenticated.post(
        "/api/v1/portfolio/transactions", json=BUY_PAYLOAD, headers=_csrf(authenticated)
    )
    assert recorded.status_code == 201
    transaction_id = recorded.json()["transaction_id"]
    drain_worker()

    compensated = authenticated.post(
        f"/api/v1/portfolio/transactions/{transaction_id}/compensate",
        json={"note": "SYNTHETIC correction: wrong quantity typed"},
        headers=_csrf(authenticated),
    )
    assert compensated.status_code == 201
    assert compensated.json()["compensates"] == transaction_id
    drain_worker()

    body = authenticated.get("/api/v1/portfolio").json()
    # The ledger keeps BOTH rows (append-only) and links them.
    assert len(body["transactions"]) == 2
    assert body["transactions"][0]["compensated_by"] == body["transactions"][1]["id"]
    # The valuation nets to zero open lots: nothing valued, nothing invented.
    content = body["valuation"]["content"]
    assert content["coverage"]["compensation_pairs"] == 1
    assert content["coverage"]["lots_open"] == 0
    assert content["positions_by_currency"] == []

    again = authenticated.post(
        f"/api/v1/portfolio/transactions/{transaction_id}/compensate",
        json={"note": "second correction attempt"},
        headers=_csrf(authenticated),
    )
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "ALREADY_COMPENSATED"


def test_import_preview_confirm_end_to_end(
    authenticated: TestClient, db_session: Session, drain_worker
) -> None:
    _publish_marks(db_session)
    csv_text = "\n".join(
        [
            "kind,ticker,quantity,price,amount,currency,fees,effective_at,note",
            f"BUY_RECORDED,{TICKER},4,90,-360,{CURRENCY},0,{EFFECTIVE_AT},imported buy",
            f"DIVIDEND,,,,12.5,{CURRENCY},0,{EFFECTIVE_AT},imported dividend",
            f"BUY_RECORDED,{TICKER},abc,90,-360,{CURRENCY},0,{EFFECTIVE_AT},broken row",
        ]
    )
    preview = authenticated.post(
        "/api/v1/portfolio/import/preview",
        json={"csv": csv_text},
        headers=_csrf(authenticated),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert [row["row_number"] for row in preview_body["rows_valid"]] == [1, 2]
    assert [row["row_number"] for row in preview_body["rows_invalid"]] == [3]
    # Preview wrote NOTHING.
    assert authenticated.get("/api/v1/portfolio").json()["transactions"] == []

    confirm = authenticated.post(
        "/api/v1/portfolio/import/confirm",
        json={"rows": preview_body["rows_valid"]},
        headers=_csrf(authenticated),
    )
    assert confirm.status_code == 201
    confirm_body = confirm.json()
    assert confirm_body["source"] == "IMPORT_CONFIRMED"
    assert len(confirm_body["recorded_transaction_ids"]) == 2

    drain_worker()
    body = authenticated.get("/api/v1/portfolio").json()
    assert [t["source"] for t in body["transactions"]] == [
        "IMPORT_CONFIRMED",
        "IMPORT_CONFIRMED",
    ]
    content = body["valuation"]["content"]
    group = content["positions_by_currency"][0]
    # (120.5 - 90) * 4 on the imported lot; the dividend stays a cash event.
    assert Decimal(group["unrealized"]["total_unrealized"]) == Decimal("122.0")
    assert content["coverage"]["cash_events"] == 1

    # An altered echo is rejected fail-closed and writes nothing more.
    tampered = [dict(preview_body["rows_valid"][0], amount="-1")]
    rejected = authenticated.post(
        "/api/v1/portfolio/import/confirm",
        json={"rows": tampered},
        headers=_csrf(authenticated),
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "ECHO_HASH_MISMATCH"
    assert len(authenticated.get("/api/v1/portfolio").json()["transactions"]) == 2


def test_export_returns_versioned_ledger_csv(
    authenticated: TestClient, db_session: Session, drain_worker
) -> None:
    recorded = authenticated.post(
        "/api/v1/portfolio/transactions", json=BUY_PAYLOAD, headers=_csrf(authenticated)
    )
    assert recorded.status_code == 201
    response = authenticated.get("/api/v1/portfolio/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.splitlines()
    assert lines[0] == "# vertex.portfolio-ledger-export/1.0"
    assert lines[1].startswith("id,kind,ticker,")
    assert len(lines) == 3  # stamp + header + the single ledger row
    assert TICKER in lines[2]
    assert "'-1000" in lines[2]  # formula-injection neutralization
