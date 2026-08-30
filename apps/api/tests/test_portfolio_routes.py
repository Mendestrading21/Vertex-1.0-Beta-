"""Unit tests of the manual portfolio journal routes (SYNTHETIC fakes only).

The gateway and the clock are injected through ``app.dependency_overrides``;
the real database path (get-or-create, ledger repository, outbox atomicity,
worker drain) is exercised in ``apps/api/tests_integration``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator

import pytest
import sqlalchemy.exc as sa_exc
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


# ---------------------------------------------------------------------------
# P0-6 — `mark_population` est une NATURE, pas du texte libre
# ---------------------------------------------------------------------------
#
# Le 6e audit a relayé, jusqu'au bandeau « DONNÉES RÉELLES » de
# `PortfolioPage`, une valorisation étiquetée `mark_population = "REAL"` qui
# portait TOUJOURS `rights = SYNTHETIC`. Le garde de contradiction interne
# posé à la vague précédente ne regardait que la clé littérale `population` ;
# `vertex_worker.portfolio` publie la sienne sous `mark_population`.
#
# Ces tests passent par la VRAIE route et le VRAI garde. Aucune fixture n'est
# rendue permissive : la valorisation saine (`SYNTHETIC`) reste servie.


def _valuation(content: dict) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="portfolio_valuation",
        key="1",
        version=4,
        content=content,
        content_hash="sha256:" + "0" * 64,
        as_of=FIXED_NOW,
    )


FORGED_MARK_POPULATIONS = [
    "REAL",
    "DELAYED",
    "LIVE",
    "PRODUCTION",
    "real",
    "IBKR_REALTIME_ENTITLED",
    "DONNEES REELLES 100% FIABLES",
]


@pytest.mark.parametrize("forged", FORGED_MARK_POPULATIONS)
def test_a_forged_mark_population_fails_the_valuation_relay_closed(
    portfolio_client, gateway, forged: str
) -> None:
    """Contenu SAIN du worker, dont la seule nature a été réétiquetée.

    Les marks restent ceux du snapshot markets synthétique (`rights =
    SYNTHETIC`) : la charge se contredit et ne peut pas être servie.
    """
    gateway.valuation = _valuation(
        {
            "schema_version": "vertex.portfolio-valuation/1.0",
            "as_of": FIXED_NOW.isoformat(),
            "mark_population": forged,
            "marks": {"provenance": {"rights": ["SYNTHETIC"]}},
            "excluded_lots": [],
        }
    )
    response = portfolio_client.get("/api/v1/portfolio")
    assert response.status_code == 500
    assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"
    assert forged not in response.text


@pytest.mark.parametrize("forged", ["LIVE", "PRODUCTION", "DONNEES REELLES"])
def test_a_mark_population_outside_the_vocabulary_is_refused_alone(
    portfolio_client, gateway, forged: str
) -> None:
    """Même sans marqueur en regard : une nature hors vocabulaire ne sort pas."""
    gateway.valuation = _valuation(
        {
            "schema_version": "vertex.portfolio-valuation/1.0",
            "mark_population": forged,
            "excluded_lots": [],
        }
    )
    response = portfolio_client.get("/api/v1/portfolio")
    assert response.status_code == 500
    assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"


def test_the_mark_population_refusal_leaks_no_value_to_the_logs(
    portfolio_client, gateway, caplog
) -> None:
    """`.claude/rules/security.md` : un refus nomme un CHEMIN, jamais la valeur."""
    forged = "DONNEES REELLES 100% FIABLES"
    gateway.valuation = _valuation(
        {
            "schema_version": "vertex.portfolio-valuation/1.0",
            "mark_population": forged,
            "excluded_lots": [],
        }
    )
    with caplog.at_level(logging.DEBUG):
        response = portfolio_client.get("/api/v1/portfolio")
    assert response.status_code == 500
    emitted = "\n".join(record.getMessage() for record in caplog.records)
    emitted += "\n" + "\n".join(str(record.exc_info) for record in caplog.records)
    assert forged not in emitted
    assert forged not in response.text
    assert "mark_population" in emitted  # le CHEMIN, lui, doit être tracé


def test_a_synthetic_marks_source_still_contradicts_a_real_claim(
    portfolio_client, gateway
) -> None:
    """Le marqueur n'est pas seulement `rights` : le `schema_version` du
    générateur en est un aussi (`vertex_core.synthetic`)."""
    gateway.valuation = _valuation(
        {
            "schema_version": "vertex.portfolio-valuation/1.0",
            "mark_population": "REAL",
            "marks": {"source": {"schema_version": "synthetic-daily-quote/1.0"}},
            "excluded_lots": [],
        }
    )
    response = portfolio_client.get("/api/v1/portfolio")
    assert response.status_code == 500
    assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"


def test_the_honest_synthetic_valuation_is_still_served(
    portfolio_client, gateway
) -> None:
    """Anti-vacuité : la valorisation que le worker publie VRAIMENT passe."""
    gateway.valuation = _valuation(
        {
            "schema_version": "vertex.portfolio-valuation/1.0",
            "as_of": FIXED_NOW.isoformat(),
            "mark_population": "SYNTHETIC",
            "marks": {"provenance": {"rights": ["SYNTHETIC"]}},
            "excluded_lots": [],
        }
    )
    response = portfolio_client.get("/api/v1/portfolio")
    assert response.status_code == 200
    assert response.json()["valuation"]["content"]["mark_population"] == "SYNTHETIC"


# ---------------------------------------------------------------------------
# P1-4 — amplification x3566 sur POST /portfolio/import/preview
# ---------------------------------------------------------------------------
#
# Mesure du 7e audit, rejouée ici par la VRAIE route : 500 lignes (le maximum)
# portant `1E+200000` tenaient dans 26 565 octets — très en dessous du budget
# déclaré de 262 144 — et sortaient 100 126 003 octets (95,5 Mio) en 1,51 s,
# pic RSS 474 Mo. Le budget de la requête ne protégeait donc rien : le seul
# plafond réel était la mémoire de la machine.

_AMPLIFYING_AMOUNT = "1E+200000"


def _preview_row(amount: str = "-1000", **overrides: str) -> str:
    cells = {
        "kind": "BUY_RECORDED",
        "ticker": "SYN-A",
        "quantity": "10",
        "price": "100",
        "amount": amount,
        "currency": "SYN",
        "fees": "0",
        "effective_at": "2026-08-20T10:00:00+00:00",
        "note": "",
    }
    cells.update(overrides)
    return ",".join(cells[column] for column in CSV_HEADER.split(","))


def test_the_full_row_budget_of_giant_exponents_does_not_amplify(
    portfolio_client, gateway
) -> None:
    """Le vecteur exact de l'audit, par la route, avec mesure d'amplification."""
    csv_text = "\n".join(
        [CSV_HEADER] + [_preview_row(amount=_AMPLIFYING_AMOUNT)] * 500
    )
    request_bytes = len(json.dumps({"csv": csv_text}).encode("utf-8"))
    assert request_bytes < 262_144  # sous le budget déclaré, comme à l'audit

    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": csv_text}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows_valid"] == []
    assert len(body["rows_invalid"]) == 500
    assert body["rows_invalid"][0]["errors"] == ["AMOUNT_OUT_OF_RANGE"]
    # La réponse reste proportionnée à l'entrée : plus d'amplification.
    assert len(response.content) < request_bytes
    # Et elle ne matérialise jamais la magnitude déclarée.
    assert _AMPLIFYING_AMOUNT not in response.text
    assert gateway.imported == [] and gateway.recorded == []


@pytest.mark.parametrize(
    "field, code",
    [
        ("amount", "AMOUNT_OUT_OF_RANGE"),
        ("quantity", "QUANTITY_OUT_OF_RANGE"),
        ("price", "PRICE_OUT_OF_RANGE"),
        ("fees", "FEES_OUT_OF_RANGE"),
    ],
)
def test_the_preview_refusal_names_the_row_and_the_field(
    portfolio_client, field: str, code: str
) -> None:
    """Refus TYPÉ nommant la LIGNE et le CHAMP, jamais la valeur."""
    csv_text = "\n".join(
        [
            CSV_HEADER,
            _preview_row(),
            _preview_row(**{field: _AMPLIFYING_AMOUNT}),
        ]
    )
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": csv_text}
    )
    assert response.status_code == 200
    body = response.json()
    assert [row["row_number"] for row in body["rows_valid"]] == [1]
    assert body["rows_invalid"] == [{"row_number": 2, "errors": [code]}]
    assert _AMPLIFYING_AMOUNT not in response.text


def test_the_confirm_replay_also_refuses_an_out_of_range_echo(
    portfolio_client, gateway
) -> None:
    """L'écho ne contourne pas la borne : le confirm rejoue la validation."""
    from vertex_api.portfolio import import_row_hash

    fields = {
        "kind": "DIVIDEND",
        "ticker": "",
        "quantity": "",
        "price": "",
        "amount": _AMPLIFYING_AMOUNT,
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
    detail = response.json()["detail"]
    assert detail["code"] == "IMPORT_ROW_INVALID"
    assert detail["errors"] == ["AMOUNT_OUT_OF_RANGE"]
    assert gateway.imported == []


def test_the_confirm_replay_refuses_a_literal_out_of_range_echo(
    portfolio_client, gateway
) -> None:
    """L'écho JSON ne passe PAS par `csv.reader` : 200 000 chiffres l'atteignent.

    C'est la seule voie par laquelle une magnitude écrite en toutes lettres
    arrive au validateur ; elle doit être refusée typée et bornée.
    """
    from vertex_api.portfolio import import_row_hash

    fields = {
        "kind": "DIVIDEND",
        "ticker": "",
        "quantity": "",
        "price": "",
        "amount": "1" * 200000,
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
    assert response.json()["detail"]["errors"] == ["AMOUNT_OUT_OF_RANGE"]
    assert len(response.content) < 4096  # aucune amplification dans le refus
    assert gateway.imported == []


def test_an_unreadable_csv_is_a_typed_422_not_an_untyped_500(portfolio_client) -> None:
    """Une cellule au-delà de la limite de champ de `csv.reader` (131 072).

    Elle tient sous le budget de 256 Kio et faisait remonter un `_csv.Error`
    jusqu'au gestionnaire par défaut — même classe de défaut que P1-5.
    """
    csv_text = CSV_HEADER + "\n" + _preview_row(note="x" * 200000)
    response = portfolio_client.post(
        "/api/v1/portfolio/import/preview", json={"csv": csv_text}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CSV_MALFORMED"
    assert "x" * 100 not in response.text


# -- POST /portfolio/transactions : même borne sur le DTO du journal --------


@pytest.mark.parametrize(
    "field",
    ["amount", "quantity", "price", "fees"],
)
@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("1E+200000", id="huge-positive-exponent"),
        pytest.param("1E-200000", id="huge-negative-exponent"),
        pytest.param("1." + "0" * 200000 + "1", id="huge-coefficient"),
    ],
)
def test_record_transaction_refuses_an_out_of_range_magnitude(
    portfolio_client, gateway, field: str, raw: str
) -> None:
    payload = dict(VALID_PAYLOAD, **{field: raw})
    response = portfolio_client.post("/api/v1/portfolio/transactions", json=payload)
    assert response.status_code == 422
    assert gateway.recorded == []
    # Le refus nomme le CHAMP et reste borné ; il ne cite pas la valeur.
    assert len(response.content) < 4096
    assert raw not in response.text
    assert field in response.text


# -- Question ouverte tranchée : 1E+100 USD n'est PAS une saisie plausible --
#
# Le portefeuille est déclaré par l'utilisateur : Vertex ne décide pas à sa
# place de ce qui est « trop grand ». Mais 10^100 unités monétaires dépassent
# de ~86 décades le plus gros nominal jamais émis dans une monnaie réelle
# (billet de 10^20 pengő, Hongrie 1946) et de ~86 décades la masse monétaire
# mondiale (~10^14 USD). Ce n'est donc pas une déclaration : c'est une faute
# de frappe ou un collage, et l'écrire au journal corrompt silencieusement
# toute valorisation et toute série de performance en aval.


def test_ten_power_hundred_is_no_longer_accepted(portfolio_client, gateway) -> None:
    """`1E+100` était accepté et ÉCRIT au journal (HTTP 201) ; plus maintenant."""
    response = portfolio_client.post(
        "/api/v1/portfolio/transactions",
        json=dict(VALID_PAYLOAD, amount="1E+100"),
    )
    assert response.status_code == 422
    assert gateway.recorded == []


@pytest.mark.parametrize(
    "field, raw",
    [
        # Le plus gros nominal monétaire réellement émis (pengő 1946).
        ("amount", "-100000000000000000000"),
        # Portefeuille libellé en IDR/VND : dix milliards d'unités.
        ("amount", "-10000000000.00"),
        ("amount", "-1005.75"),
        # Fraction de titre au grain le plus fin d'un courtier.
        ("quantity", "0.00000001"),
        ("price", "0.000001"),
        ("fees", "0.0001"),
        # Artefact d'export tableur (float rendu sur 17 chiffres).
        ("price", "100.50000000000001"),
    ],
)
def test_a_legitimate_declaration_is_still_recorded_by_the_route(
    portfolio_client, gateway, field: str, raw: str
) -> None:
    """Anti-vacuité : la borne ne refuse aucune saisie défendable."""
    response = portfolio_client.post(
        "/api/v1/portfolio/transactions", json=dict(VALID_PAYLOAD, **{field: raw})
    )
    assert response.status_code == 201, response.text
    assert gateway.recorded[0][field] == Decimal(raw)


# ---------------------------------------------------------------------------
# P1-5 — 500 non typé et JOURNAL DE L'UTILISATEUR en clair dans les logs
# ---------------------------------------------------------------------------
#
# `sqlalchemy.exc.DataError` n'était couvert par AUCUN `@app.exception_handler`
# alors que `app.py` en déclarait déjà trois pour cette raison exacte. Sous
# uvicorn réel, `amount='1E+200000'` répondait `HTTP 500 : Internal Server
# Error` et uvicorn écrivait la trace complète, c'est-à-dire :
#
#     sqlalchemy.exc.DataError: (psycopg.errors.NumericValueOutOfRange) …
#     [SQL: INSERT INTO ledger_transactions (portfolio_id, kind, …) VALUES …]
#     [parameters: {… 'note': '<compte de l'utilisateur> - achat perso', …}]
#
# soit le JOURNAL FINANCIER de l'utilisateur, nom de compte compris, en clair
# dans le log serveur — violation directe de `.claude/rules/security.md`.
#
# La classe fautive n'est pas `DataError` mais `sqlalchemy.exc.StatementError` :
# c'est elle qui porte `.statement` et `.params`, et dont la représentation
# textuelle cite le SQL et les paramètres liés. Toutes ses sous-classes
# fuiraient identiquement ; les tests couvrent donc la CLASSE, sur CHAQUE
# route qui écrit.

SYNTHETIC_ACCOUNT_LABEL = "SYNTH-BROKER 40312"
"""Étiquette SYNTHETIC tenant lieu du nom de compte de l'utilisateur."""

SYNTHETIC_LEDGER_PARAMS = {
    "portfolio_id": 1,
    "kind": "BUY_RECORDED",
    "amount": Decimal("-1005"),
    "currency": "USD",
    "note": f"{SYNTHETIC_ACCOUNT_LABEL} - achat perso",
}

SYNTHETIC_INSERT = (
    "INSERT INTO ledger_transactions (portfolio_id, kind, amount, currency, "
    "note) VALUES (%(portfolio_id)s, %(kind)s, %(amount)s, %(currency)s, "
    "%(note)s) RETURNING ledger_transactions.id"
)

STATEMENT_ERROR_CLASSES = [
    sa_exc.DataError,
    sa_exc.IntegrityError,
    sa_exc.OperationalError,
    sa_exc.ProgrammingError,
    sa_exc.InternalError,
    sa_exc.NotSupportedError,
]


def _statement_error(cls) -> Exception:
    """A REAL SQLAlchemy statement error carrying the SQL and its parameters."""
    return cls(
        SYNTHETIC_INSERT,
        dict(SYNTHETIC_LEDGER_PARAMS),
        Exception("value overflows numeric format"),
    )


class FailingGateway(FakePortfolioGateway):
    """SYNTHETIC gateway whose every write raises a real statement error."""

    def __init__(self, error: Exception, **kwargs) -> None:
        super().__init__(**kwargs)
        self._error = error

    def overview(self):
        # GET /portfolio écrit aussi : le get-or-create de ``main``.
        raise self._error

    def record_transaction(self, **kwargs) -> int:
        raise self._error

    def compensate_transaction(self, **kwargs) -> int:
        raise self._error

    def record_import(self, rows, *, now) -> list[int]:
        raise self._error


def _failing_client(app: FastAPI, error: Exception) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_portfolio_gateway] = lambda: FailingGateway(error)
    app.dependency_overrides[get_clock] = lambda: fixed_clock
    return TestClient(app, raise_server_exceptions=False)


WRITE_CALLS = [
    pytest.param("GET", "/api/v1/portfolio", None, id="get-or-create"),
    pytest.param(
        "POST", "/api/v1/portfolio/transactions", VALID_PAYLOAD, id="record"
    ),
    pytest.param(
        "POST",
        "/api/v1/portfolio/transactions/7/compensate",
        {"note": "correction"},
        id="compensate",
    ),
    pytest.param(
        "POST",
        "/api/v1/portfolio/import/confirm",
        None,  # rempli par le test à partir d'un vrai preview
        id="import-confirm",
    ),
]


@pytest.mark.parametrize("error_class", STATEMENT_ERROR_CLASSES)
@pytest.mark.parametrize("method, path, payload", WRITE_CALLS)
def test_a_failed_write_never_leaks_the_users_journal(
    app, portfolio_client, caplog, error_class, method, path, payload
) -> None:
    """Aucune route d'écriture ne journalise la requête sur échec base."""
    if payload is None and method == "POST":
        payload = {
            "rows": _previewed_rows(
                portfolio_client,
                CSV_HEADER
                + "\nBUY_RECORDED,SYN-A,10,100,-1000,SYN,0,"
                "2026-08-20T10:00:00+00:00,ok",
            )
        }
    app.dependency_overrides.clear()
    client = _failing_client(app, _statement_error(error_class))
    with caplog.at_level(logging.DEBUG):
        with client:
            response = client.request(method, path, json=payload)
    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["code"] == "DATABASE_STATEMENT_REJECTED"

    emitted = "\n".join(record.getMessage() for record in caplog.records)
    emitted += "\n" + "\n".join(str(record.exc_info) for record in caplog.records)
    emitted += "\n" + "\n".join(
        logging.Formatter().format(record) for record in caplog.records
    )
    for leaked in (
        SYNTHETIC_ACCOUNT_LABEL,
        "INSERT INTO ledger_transactions",
        "achat perso",
        "-1005",
    ):
        assert leaked not in emitted, leaked
        assert leaked not in response.text, leaked
    # La trace reste utile : la route et la classe technique, rien de plus.
    assert path in emitted
    assert error_class.__name__ in emitted


def test_the_typed_database_refusal_is_not_an_untyped_500(app) -> None:
    """Avant : `HTTP 500 : Internal Server Error`, corps non typé."""
    app.dependency_overrides.clear()
    client = _failing_client(app, _statement_error(sa_exc.DataError))
    with client:
        response = client.post(
            "/api/v1/portfolio/transactions", json=VALID_PAYLOAD
        )
    app.dependency_overrides.clear()
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "DATABASE_STATEMENT_REJECTED"
    assert body["detail"]  # message statique, sans valeur ni SQL
    assert "INSERT" not in response.text


def test_every_sqlalchemy_statement_error_resolves_to_the_typed_handler(app) -> None:
    """La CLASSE est couverte, pas seulement le vecteur signalé.

    Starlette résout un gestionnaire par MRO : l'enregistrer sur
    `StatementError` couvre ses dix sous-classes — ce sont exactement celles
    qui portent `.statement` et `.params` — sur TOUTES les routes de
    l'application, y compris les écritures d'authentification
    (`webauthn_credentials`) et de suivi (`theses`), qui portent elles aussi
    du texte libre de l'utilisateur.
    """
    handlers = app.exception_handlers
    assert sa_exc.StatementError in handlers
    covered = []
    for candidate in vars(sa_exc).values():
        if not isinstance(candidate, type) or not issubclass(candidate, BaseException):
            continue
        if not issubclass(candidate, sa_exc.StatementError):
            continue
        resolved = next(
            (handlers[base] for base in candidate.__mro__ if base in handlers), None
        )
        assert resolved is handlers[sa_exc.StatementError], candidate.__name__
        covered.append(candidate.__name__)
    # Anti-vacuité : la famille entière, pas une classe isolée.
    assert set(covered) >= {
        "DBAPIError",
        "DataError",
        "DatabaseError",
        "IntegrityError",
        "InterfaceError",
        "InternalError",
        "NotSupportedError",
        "OperationalError",
        "ProgrammingError",
        "StatementError",
    }


def test_a_pending_rollback_error_does_not_relay_the_original_statement(
    app, caplog
) -> None:
    """`PendingRollbackError` n'est PAS un `StatementError`, mais il cite
    l'exception d'origine dans son propre message — donc les mêmes
    `[parameters: …]`. Une session réutilisée après une erreur base rattrapée
    (la forme de `record_ledger_event`) emprunte ce chemin."""
    original = _statement_error(sa_exc.IntegrityError)
    leaking = sa_exc.PendingRollbackError(
        "This Session's transaction has been rolled back due to a previous "
        f"exception during flush. Original exception was: {original}"
    )
    assert SYNTHETIC_ACCOUNT_LABEL in str(leaking)  # la fuite existe bien

    app.dependency_overrides.clear()
    client = _failing_client(app, leaking)
    with caplog.at_level(logging.DEBUG):
        with client:
            response = client.post(
                "/api/v1/portfolio/transactions", json=VALID_PAYLOAD
            )
    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["code"] == "DATABASE_STATEMENT_REJECTED"
    emitted = "\n".join(record.getMessage() for record in caplog.records)
    emitted += "\n" + "\n".join(str(record.exc_info) for record in caplog.records)
    assert SYNTHETIC_ACCOUNT_LABEL not in emitted
    assert SYNTHETIC_ACCOUNT_LABEL not in response.text
    assert "INSERT INTO ledger_transactions" not in emitted
