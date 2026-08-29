"""Vertex AI socle (LOT-21): deterministic template, grounding, boundaries.

Everything here is SYNTHETIC. The tests enforce the ADR-008 contract:
100 % of the claims cite evidence really present in the snapshot (a mutated
reference fails closed), no transactional vocabulary in any produced text,
INSUFFICIENT_DATA is explained with its closed gates, an absent snapshot is
a clean 404, and the whole surface stays behind the session dependency.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api.ai_explain import (
    LIMITATION_PROVIDER_DISABLED,
    AiClaim,
    AiGroundingError,
    AiSubject,
    build_ai_answer,
    validate_claims,
)
from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_snapshot_reader
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
ADVICE_ID = "sha256:" + "d" * 64
CLUSTER_ID = "cluster:" + "e" * 8
SCENARIO_HASH = "sha256:" + "f" * 64
BARS_EVENT_ID = "synthetic-dev:t:db0001"

# Transactional/order vocabulary that must NEVER appear in any produced text
# (word-boundary scan, case-insensitive, French and English).
FORBIDDEN_WORDS = (
    "acheter",
    "achetez",
    "achat",
    "vendre",
    "vendez",
    "vente",
    "buy",
    "sell",
    "ordre",
    "order",
    "exécuter",
    "executer",
    "execute",
    "probabilité",
)


def gate(gate_id: str, status: str, reason_code: str) -> dict:
    return {
        "gate_id": gate_id,
        "version": "1.0.0",
        "status": status,
        "reason_code": reason_code,
        "message": "synthetic gate message",
        "observed_values": {},
        "thresholds": {},
    }


def analysis_content() -> dict:
    return {
        "schema_version": "vertex.analysis/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "instrument": "SYN-TECH-01",
        "engine_version": "vertex_core@0.1.0",
        "bars": {
            "status": "OK",
            "count": 1,
            "currency": "SYN",
            "last_trading_day": "2026-08-24",
            "last_close": "104.50",
            "source_event_id": BARS_EVENT_ID,
        },
        "evidence": {
            "clusters": [
                {"cluster_id": CLUSTER_ID, "title": "[SYNTHETIC] fixture item"}
            ]
        },
        "scenarios": {
            "status": "OK",
            "value_nature": "THEORETICAL",
            "calculation": {"input_hash": SCENARIO_HASH},
        },
        "advice": {
            "advice_id": ADVICE_ID,
            "status": "INSUFFICIENT_DATA",
            "direction": "UNKNOWN",
            "horizon": "1d",
            "gates": [
                gate("instrument_resolved", "DEGRADE", "RESOLVED_WITHOUT_CONID"),
                gate("entitlements_sufficient", "BLOCK", "UNEVALUABLE"),
                gate("session_and_event_known", "BLOCK", "UNEVALUABLE"),
            ],
            "limitations": ["SYNTHETIC development population"],
        },
        "coverage": {},
    }


def portfolio_content() -> dict:
    return {
        "schema_version": "vertex.portfolio-valuation/1.0",
        "as_of": AS_OF.isoformat(),
        "mark_population": "SYNTHETIC",
        "lot_method": "fifo/1.0",
        "marks": {"status": "OK", "reason": None},
        "positions_by_currency": [
            {
                "currency": "SYN",
                "unrealized": {
                    "status": "OK",
                    "total_unrealized": "12.34",
                    "calculation": {"input_hash": "sha256:" + "1" * 64},
                },
                "realized": {
                    "status": "ABSENT",
                    "reason": "no_closing_recorded",
                    "calculation": None,
                },
            }
        ],
        "excluded_lots": [
            {"lot_id": "ledger-9", "reason": "missing_mark"}
        ],
        "coverage": {
            "invalid_positions": [
                {"ticker": "SYN-FINL-01", "reason": "oversold_position"}
            ]
        },
    }


def performance_content() -> dict:
    return {
        "schema_version": "vertex.performance/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC_MARKS_REAL_LEDGER",
        "series": {"status": "OK", "reason": None},
        "metrics": {
            "twr_net": {
                "status": "OK",
                "total_return": "0.0123",
                "calculation": {"input_hash": "sha256:" + "2" * 64},
            },
            "xirr_net": {
                "status": "INSUFFICIENT_DATA",
                "reason": "cashflow_boundary_not_valued",
                "calculation": None,
            },
            "drawdown_net": {
                "status": "OK",
                "max_drawdown": "0.0456",
                "calculation": {"input_hash": "sha256:" + "3" * 64},
            },
        },
    }


def snapshot(kind: str, key: str, content: dict) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind=kind,
        key=key,
        version=3,
        content=content,
        content_hash="sha256:" + "9" * 64,
        as_of=AS_OF,
    )


def all_answers():
    return [
        build_ai_answer(
            AiSubject(kind="analysis", key="SYN-TECH-01"),
            snapshot("analysis", "SYN-TECH-01", analysis_content()),
        ),
        build_ai_answer(
            AiSubject(kind="portfolio_valuation", key="1"),
            snapshot("portfolio_valuation", "1", portfolio_content()),
        ),
        build_ai_answer(
            AiSubject(kind="performance", key="1"),
            snapshot("performance", "1", performance_content()),
        ),
    ]


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def api(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Grounding: 100 % of the claims cite evidence really present
# ---------------------------------------------------------------------------


def test_every_claim_cites_catalog_evidence() -> None:
    for answer in all_answers():
        catalog_ids = {entry.evidence_id for entry in answer.evidence_catalog}
        assert answer.claims  # the template really says something
        for claim in answer.claims:
            assert claim.kind == "FACT"
            assert claim.evidence_refs  # at least one citation each
            for reference in claim.evidence_refs:
                assert reference in catalog_ids


def test_mutated_reference_fails_closed() -> None:
    claim = AiClaim(
        text="Statut du verdict : INSUFFICIENT_DATA.",
        kind="FACT",
        evidence_refs=("sha256:" + "0" * 64,),
    )
    with pytest.raises(AiGroundingError):
        validate_claims([claim], frozenset({ADVICE_ID}))


def test_claim_without_reference_is_impossible_by_contract() -> None:
    with pytest.raises(Exception):
        AiClaim(text="fact", kind="FACT", evidence_refs=())


def test_no_transactional_vocabulary_in_any_produced_text() -> None:
    pattern = re.compile(
        r"\b(" + "|".join(FORBIDDEN_WORDS) + r")\b", re.IGNORECASE
    )
    for answer in all_answers():
        texts = [claim.text for claim in answer.claims]
        texts += [entry.text for entry in answer.contradictions]
        texts += list(answer.missing_data)
        texts += list(answer.limitations)
        for text in texts:
            assert not pattern.search(text), text


def test_numbers_in_claims_are_verbatim_snapshot_strings() -> None:
    contents = {
        "analysis": analysis_content(),
        "portfolio_valuation": portfolio_content(),
        "performance": performance_content(),
    }
    import json

    for answer in all_answers():
        blob = json.dumps(contents[answer.subject.kind])
        for claim in answer.claims:
            for token in re.findall(r"\d+(?:\.\d+)?", claim.text):
                assert token in blob, (claim.text, token)


# ---------------------------------------------------------------------------
# Template semantics
# ---------------------------------------------------------------------------


def test_insufficient_data_is_explained_with_its_gates() -> None:
    answer = build_ai_answer(
        AiSubject(kind="analysis", key="SYN-TECH-01"),
        snapshot("analysis", "SYN-TECH-01", analysis_content()),
    )
    explanation = next(
        claim
        for claim in answer.claims
        if "INSUFFICIENT_DATA" in claim.text and "gates" in claim.text
    )
    assert "entitlements_sufficient" in explanation.text
    assert "session_and_event_known" in explanation.text
    assert explanation.evidence_refs == (ADVICE_ID,)
    codes = {(c.reference, c.code) for c in answer.contradictions}
    assert codes == {
        ("entitlements_sufficient", "UNEVALUABLE"),
        ("session_and_event_known", "UNEVALUABLE"),
    }
    assert any("entitlements_sufficient" in item for item in answer.missing_data)


def test_provider_labels_and_b05_limitation_are_mandatory() -> None:
    for answer in all_answers():
        assert answer.provider == "DETERMINISTIC_TEMPLATE"
        assert answer.limitations[0] == LIMITATION_PROVIDER_DISABLED
        assert answer.as_of == AS_OF
        assert answer.snapshot_version == 3
        assert answer.locale == "fr"


def test_determinism() -> None:
    first = build_ai_answer(
        AiSubject(kind="analysis", key="SYN-TECH-01"),
        snapshot("analysis", "SYN-TECH-01", analysis_content()),
    )
    second = build_ai_answer(
        AiSubject(kind="analysis", key="SYN-TECH-01"),
        snapshot("analysis", "SYN-TECH-01", analysis_content()),
    )
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def test_explain_requires_session(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ai/explain",
        json={"subject": {"kind": "analysis", "key": "SYN-TECH-01"}, "locale": "fr"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_status_requires_session(client: TestClient) -> None:
    assert client.get("/api/v1/ai/status").status_code == 401


def test_status_reports_disabled_provider(api: TestClient) -> None:
    body = api.get("/api/v1/ai/status").json()
    assert body == {
        "provider": "DISABLED",
        "reason": "B-05_HUMAN_DECISION_PENDING",
        "deterministic_template_available": True,
    }


def test_absent_snapshot_is_a_clean_404(api: TestClient) -> None:
    response = api.post(
        "/api/v1/ai/explain",
        json={"subject": {"kind": "analysis", "key": "SYN-TECH-01"}, "locale": "fr"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NO_SNAPSHOT_FOR_SUBJECT"


def test_explain_round_trip_over_the_route(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    reader.snapshots[("analysis", "SYN-TECH-01")] = snapshot(
        "analysis", "SYN-TECH-01", analysis_content()
    )
    response = api.post(
        "/api/v1/ai/explain",
        json={"subject": {"kind": "analysis", "key": "SYN-TECH-01"}, "locale": "fr"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "DETERMINISTIC_TEMPLATE"
    assert body["as_of"] == "2026-08-25T12:00:00Z"
    catalog_ids = {entry["evidence_id"] for entry in body["evidence_catalog"]}
    for claim in body["claims"]:
        assert set(claim["evidence_refs"]) <= catalog_ids
    assert LIMITATION_PROVIDER_DISABLED in body["limitations"]


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": {"kind": "analysis", "key": "SYN-TECH-01"}, "locale": "en"},
        {"subject": {"kind": "verdict", "key": "SYN-TECH-01"}, "locale": "fr"},
        {"subject": {"kind": "analysis", "key": "../etc"}, "locale": "fr"},
        {"subject": {"kind": "analysis"}, "locale": "fr"},
        {"locale": "fr"},
    ],
)
def test_invalid_bodies_are_422(api: TestClient, payload: dict) -> None:
    assert api.post("/api/v1/ai/explain", json=payload).status_code == 422
