"""Unit tests of the manual portfolio journal routes (SYNTHETIC fakes only).

The gateway and the clock are injected through ``app.dependency_overrides``;
the real database path (get-or-create, ledger repository, outbox atomicity,
worker drain) is exercised in ``apps/api/tests_integration``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from portfolio_fakes import FIXED_NOW, FakePortfolioGateway, fixed_clock, make_entry
from snapshot_fakes import synthetic_session
from vertex_api.auth import require_session
from vertex_api.routes import get_portfolio_gateway
from vertex_api.snapshot_reader import get_clock
from vertex_persistence.errors import AlreadyCompensatedError, UnknownLedgerEventError
from vertex_persistence.repository.snapshots import CurrentSnapshot

VALID_PAYLOAD = {
    "kind": "BUY_RECORDED",
    "instrument": {"ticker": "SYN-A"},
    "quantity": "10",
    "price": "100.50",
    "amount": "-1005",
    "currency": "SYN",
    "fees": "1.25",
    "effective_at": "2026-08-20T10:00:00Z",
    "note": "recorded after an execution outside Vertex",
}

SYNTHETIC_VALUATION = CurrentSnapshot(
    kind="portfolio_valuation",
    key="1",
    version=4,
    content={
        "schema_version": "vertex.portfolio-valuation/1.0",
        "as_of": FIXED_NOW.isoformat(),
        "mark_population": "SYNTHETIC",
        "excluded_lots": [],
    },
    content_hash="sha256:" + "0" * 64,
    as_of=FIXED_NOW,
)


@pytest.fixture()
def gateway() -> FakePortfolioGateway:
    return FakePortfolioGateway(valuation=SYNTHETIC_VALUATION)


@pytest.fixture()
def portfolio_client(
    app: FastAPI, gateway: FakePortfolioGateway
) -> Iterator[TestClient]:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_portfolio_gateway] = lambda: gateway
    app.dependency_overrides[get_clock] = lambda: fixed_clock
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# -- fail-closed authentication ---------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/api/v1/portfolio"),
        ("POST", "/api/v1/portfolio/transactions"),
        ("POST", "/api/v1/portfolio/transactions/1/compensate"),
        ("POST", "/api/v1/portfolio/import/preview"),
        ("POST", "/api/v1/portfolio/import/confirm"),
        ("GET", "/api/v1/portfolio/export"),
    ],
)
def test_every_portfolio_route_requires_a_session(client, method, path) -> None:
    response = client.request(method, path, json={})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


# -- GET /portfolio ----------------------------------------------------------


def test_get_portfolio_relays_ledger_and_valuation_verbatim(
    portfolio_client, gateway
) -> None:
    gateway.transactions = (
        make_entry(1),
        make_entry(2, kind="BUY_RECORDED", compensates=None),
        make_entry(3, kind="BUY_RECORDED", amount="1000", compensates=2),
    )
    response = portfolio_client.get("/api/v1/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert body["portfolio"] == {"id": 1, "name": "main", "base_currency": "USD"}
    assert [t["id"] for t in body["transactions"]] == [1, 2, 3]
    assert body["transactions"][0]["amount"] == "-1000"  # decimal string
    assert body["transactions"][1]["compensated_by"] == 3
    assert body["transactions"][2]["compensates"] == 2
    valuation = body["valuation"]
    assert valuation["state"] == "ok"
    assert valuation["snapshot_version"] == 4
    assert valuation["content"]["mark_population"] == "SYNTHETIC"


def test_get_portfolio_valuation_empty_state_is_honest(portfolio_client, gateway) -> None:
    gateway.valuation = None
    response = portfolio_client.get("/api/v1/portfolio")
    assert response.status_code == 200
    valuation = response.json()["valuation"]
    assert valuation["state"] == "empty"
    assert valuation["snapshot_version"] is None
    assert valuation["content"] is None
    assert valuation["reason"] == "no valuation snapshot published"


# -- POST /portfolio/transactions -------------------------------------------


def test_record_transaction_writes_exact_decimals(portfolio_client, gateway) -> None:
    response = portfolio_client.post(
        "/api/v1/portfolio/transactions", json=VALID_PAYLOAD
    )
    assert response.status_code == 201
    body = response.json()
    assert body["transaction_id"] == 101
    assert body["refresh_enqueued"] is True
    recorded = gateway.recorded[0]
    assert recorded["kind"] == "BUY_RECORDED"
    assert recorded["quantity"] == Decimal("10")
    assert recorded["price"] == Decimal("100.50")
    assert recorded["amount"] == Decimal("-1005")
    assert recorded["fees"] == Decimal("1.25")
    assert recorded["instrument"] == {"ticker": "SYN-A"}
    assert recorded["now"] == FIXED_NOW


def test_record_transaction_rejects_future_effective_at(portfolio_client, gateway) -> None:
    payload = dict(VALID_PAYLOAD, effective_at="2026-08-25T12:00:01Z")  # now + 1s
    response = portfolio_client.post("/api/v1/portfolio/transactions", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EFFECTIVE_AT_IN_FUTURE"
    assert gateway.recorded == []


@pytest.mark.parametrize(
    "mutation",
    [
        {"instrument": None},  # position fact without instrument
        {"quantity": None},
        {"price": None},
        {"quantity": "-1"},
        {"fees": "-0.5"},
        {"amount": "NaN"},
        {"currency": "usd"},
        {"effective_at": "2026-08-20T10:00:00"},  # naive datetime
        {"unknown_field": True},
        {"kind": "PLACE_ORDER"},  # not a journal kind — no such capability
    ],
)
def test_record_transaction_contract_violations_are_422(
    portfolio_client, gateway, mutation
) -> None:
    payload = dict(VALID_PAYLOAD, **mutation)
    payload = {k: v for k, v in payload.items() if v is not None}
    response = portfolio_client.post("/api/v1/portfolio/transactions", json=payload)
    assert response.status_code == 422
    assert gateway.recorded == []


# -- POST /portfolio/transactions/{id}/compensate ----------------------------


def test_compensation_appends_a_row(portfolio_client, gateway) -> None:
    response = portfolio_client.post(
        "/api/v1/portfolio/transactions/7/compensate",
        json={"note": "typed the wrong quantity"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["compensates"] == 7
    assert body["compensation_id"] == 101
    assert gateway.compensated == [
        {"event_id": 7, "note": "typed the wrong quantity", "now": FIXED_NOW}
    ]


def test_double_compensation_is_a_clean_409(app, gateway) -> None:
    gateway.compensate_error = AlreadyCompensatedError(
        "ledger event 7 is already compensated by event 8"
    )
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_portfolio_gateway] = lambda: gateway
    app.dependency_overrides[get_clock] = lambda: fixed_clock
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/portfolio/transactions/7/compensate", json={"note": "again"}
        )
    app.dependency_overrides.clear()
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ALREADY_COMPENSATED"


def test_unknown_transaction_is_404(app, gateway) -> None:
    gateway.compensate_error = UnknownLedgerEventError("ledger event 99 does not exist")
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_portfolio_gateway] = lambda: gateway
    app.dependency_overrides[get_clock] = lambda: fixed_clock
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/portfolio/transactions/99/compensate", json={"note": "why"}
        )
    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "UNKNOWN_TRANSACTION"


def test_compensation_requires_a_note(portfolio_client, gateway) -> None:
    response = portfolio_client.post(
        "/api/v1/portfolio/transactions/7/compensate", json={}
    )
    assert response.status_code == 422
    assert gateway.compensated == []


# -- import preview / confirm ------------------------------------------------

CSV_HEADER = "kind,ticker,quantity,price,amount,currency,fees,effective_at,note"


def test_import_preview_types_rows_and_writes_nothing(portfolio_client, gateway) -> None:
    csv_text = "\n".join(
        [
            CSV_HEADER,
            "BUY_RECORDED,SYN-A,10,100,-1000,SYN,0,2026-08-20T10:00:00+00:00,first",
            "BUY_RECORDED,SYN-B,abc,100,-1000,SYN,0,2026-08-20T10:00:00+00:00,",
            "DIVIDEND,,,,12.5,SYN,0,2026-08-21T10:00:00+00:00,",
        ]
    )
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": csv_text}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows_total"] == 3
    assert [row["row_number"] for row in body["rows_valid"]] == [1, 3]
    assert body["rows_valid"][0]["row_hash"].startswith("sha256:")
    assert body["rows_invalid"] == [{"row_number": 2, "errors": ["INVALID_QUANTITY"]}]
    # NO write happened: preview never touches the ledger.
    assert gateway.imported == [] and gateway.recorded == []


def test_import_preview_flags_potential_duplicates(portfolio_client, gateway) -> None:
    gateway.transactions = (make_entry(42),)  # BUY SYN-A 10 @ 100, -1000 SYN
    csv_text = "\n".join(
        [
            CSV_HEADER,
            "BUY_RECORDED,SYN-A,10,100,-1000,SYN,0,2026-08-20T10:00:00+00:00,dup",
        ]
    )
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": csv_text}
    )
    assert response.status_code == 200
    assert response.json()["potential_duplicates"] == [
        {"row_number": 1, "matching_transaction_ids": [42]}
    ]


def test_import_preview_rejects_oversized_csv(portfolio_client) -> None:
    big = CSV_HEADER + "\n" + ("x" * (256 * 1024))
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": big}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CSV_TOO_LARGE"


def test_import_preview_rejects_too_many_rows(portfolio_client) -> None:
    rows = [CSV_HEADER] + [
        "DIVIDEND,,,,1,SYN,0,2026-08-20T10:00:00+00:00,"
    ] * 501
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": "\n".join(rows)}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CSV_TOO_MANY_ROWS"


def test_import_preview_rejects_wrong_header(portfolio_client) -> None:
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview",
        json={"csv": "a,b,c\n1,2,3"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CSV_HEADER_INVALID"


def _previewed_rows(portfolio_client, csv_text: str) -> list[dict]:
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": csv_text}
    )
    assert response.status_code == 200
    return [dict(row) for row in response.json()["rows_valid"]]


def test_import_confirm_records_the_intact_echo(portfolio_client, gateway) -> None:
    rows = _previewed_rows(
        portfolio_client,
        CSV_HEADER
        + "\nBUY_RECORDED,SYN-A,10,100,-1000,SYN,0,2026-08-20T10:00:00+00:00,ok",
    )
    response = portfolio_client.post(
        "/api/v1/portfolio/import/confirm", json={"rows": rows}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "IMPORT_CONFIRMED"
    assert body["recorded_transaction_ids"] == [101]
    assert len(gateway.imported) == 1
    imported_row = gateway.imported[0][0]
    assert imported_row.kind == "BUY_RECORDED"
    assert imported_row.quantity == Decimal("10")


def test_import_confirm_rejects_an_altered_echo(portfolio_client, gateway) -> None:
    rows = _previewed_rows(
        portfolio_client,
        CSV_HEADER
        + "\nBUY_RECORDED,SYN-A,10,100,-1000,SYN,0,2026-08-20T10:00:00+00:00,ok",
    )
    rows[0]["amount"] = "-1"  # tampered after the preview
    response = portfolio_client.post(
        "/api/v1/portfolio/import/confirm", json={"rows": rows}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ECHO_HASH_MISMATCH"
    assert gateway.imported == []  # nothing written


def test_import_confirm_rejects_a_forged_hash(portfolio_client, gateway) -> None:
    rows = _previewed_rows(
        portfolio_client,
        CSV_HEADER
        + "\nBUY_RECORDED,SYN-A,10,100,-1000,SYN,0,2026-08-20T10:00:00+00:00,ok",
    )
    rows[0]["amount"] = "-1"
    rows[0]["row_hash"] = "sha256:" + hashlib.sha256(b"forged").hexdigest()
    response = portfolio_client.post(
        "/api/v1/portfolio/import/confirm", json={"rows": rows}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ECHO_HASH_MISMATCH"
    assert gateway.imported == []


def test_import_confirm_replays_validation(portfolio_client, gateway) -> None:
    # A structurally intact echo whose fields would no longer validate
    # (unknown kind) — the replayed validation must reject it even with a
    # freshly computed hash over the altered fields.
    from vertex_api.portfolio import import_row_hash

    fields = {
        "kind": "NOT_A_KIND",
        "ticker": "SYN-A",
        "quantity": "10",
        "price": "100",
        "amount": "-1000",
        "currency": "SYN",
        "fees": "0",
        "effective_at": "2026-08-20T10:00:00+00:00",
        "note": "",
    }
    row = dict(fields, row_number=1, row_hash=import_row_hash(fields))
    response = portfolio_client.post(
        "/api/v1/portfolio/import/confirm", json={"rows": [row]}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IMPORT_ROW_INVALID"
    assert gateway.imported == []


# -- export ------------------------------------------------------------------


def test_export_is_versioned_csv_of_the_ledger_only(portfolio_client, gateway) -> None:
    gateway.transactions = (
        make_entry(1, note="=SUM(A1:A9)"),
        make_entry(2, kind="DIVIDEND", ticker=None, quantity=None, price=None, amount="12.5"),
    )
    response = portfolio_client.get("/api/v1/portfolio/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.splitlines()
    assert lines[0] == "# vertex.portfolio-ledger-export/1.0"
    assert lines[1].startswith("id,kind,ticker,quantity,price,amount,")
    # Formula injection neutralized: '=' and '-' prefixed cells get a quote.
    assert "'=SUM(A1:A9)" in response.text
    assert "'-1000" in response.text
    assert len(lines) == 4  # stamp + header + 2 ledger rows, nothing else
