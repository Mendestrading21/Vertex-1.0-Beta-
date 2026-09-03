"""GET /api/v1/analysis/{instrument}: verbatim relay, honest empty, 401.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.analysis.build_analysis_content``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError, build_analysis_response
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

#: Horloge du relais, injectée (voir test_today_attention.py).
_NOW = AS_OF + timedelta(minutes=30)
INSTRUMENT = "SYN-TECH-01"


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
    """SYNTHETIC copy of the worker's published analysis content shape."""
    return {
        "schema_version": "vertex.analysis/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "instrument": INSTRUMENT,
        "engine_version": "vertex_core@0.1.0",
        "bars": {
            "status": "OK",
            "count": 2,
            "currency": "SYN",
            "adjustment_basis": "synthetic-unadjusted",
            "first_trading_day": "2026-08-23",
            "last_trading_day": "2026-08-24",
            "last_close": "104.50",
            "quality": "VALID",
            "fresh": True,
            "source_event_id": "synthetic-dev:t:db0001",
            "observed_as_of": AS_OF.isoformat(),
            "discarded": [],
            "bars": [
                {
                    "trading_day": "2026-08-23",
                    "open": "100.00",
                    "high": "103.00",
                    "low": "99.00",
                    "close": "102.00",
                    "volume": 1000,
                },
                {
                    "trading_day": "2026-08-24",
                    "open": "102.00",
                    "high": "105.00",
                    "low": "101.00",
                    "close": "104.50",
                    "volume": 1200,
                },
            ],
        },
        "indicators": {
            "rebased_comparison": {
                "status": "OK",
                "benchmark": "SPX",
                "unit": "index",
                "base_value": "100",
                "currency": "SYN",
                "adjustment_basis": "synthetic-unadjusted",
                "common_sessions": 2,
                "first_trading_day": "2026-08-23",
                "last_trading_day": "2026-08-24",
                "series": [
                    {
                        "trading_day": "2026-08-23",
                        "instrument": "100.0",
                        "benchmark": "100.0",
                    },
                    {
                        "trading_day": "2026-08-24",
                        "instrument": "102.45098039215686",
                        "benchmark": "101.0",
                    },
                ],
                "calculation": {
                    "calculation_id": "market.rebased_series",
                    "engine_version": "vertex_core@0.1.0",
                    "method": (
                        "base_value * p_i / p_0 sur les seules séances "
                        "communes aux deux séries"
                    ),
                    "input_hash": "sha256:" + "1" * 64,
                    "result_hash": "sha256:" + "2" * 64,
                    "status": "OK",
                },
                "benchmark_calculation": {
                    "calculation_id": "market.rebased_series",
                    "engine_version": "vertex_core@0.1.0",
                    "method": (
                        "base_value * p_i / p_0 sur les seules séances "
                        "communes aux deux séries"
                    ),
                    "input_hash": "sha256:" + "3" * 64,
                    "result_hash": "sha256:" + "4" * 64,
                    "status": "OK",
                },
            }
        },
        "evidence": {
            "source": "fusion",
            "ruleset_version": "fusion/1.0",
            "considered": 1,
            "clusters_total": 1,
            "clusters": [
                {
                    "cluster_id": "cluster-0001",
                    "title": "[SYNTHETIC] item",
                    "sources": ["synthetic-dev"],
                    "rights": ["SYNTHETIC"],
                    "member_count": 1,
                    "member_event_ids": ["e1"],
                    "last_received_at": AS_OF.isoformat(),
                    "synthetic": True,
                }
            ],
        },
        "scenarios": {"status": "ABSENT", "reason": "no_option_chain_snapshot"},
        "advice": {
            "advice_id": "sha256:" + "d" * 64,
            "instrument_id": INSTRUMENT,
            "as_of": AS_OF.isoformat(),
            "valid_until": AS_OF.isoformat(),
            "input_snapshot_id": "synthetic-dev:t:db0001",
            "engine_version": "vertex_core@0.1.0",
            "status": "INSUFFICIENT_DATA",
            "direction": "UNKNOWN",
            "horizon": "1d",
            "gates": [
                gate("instrument_resolved", "DEGRADE", "RESOLVED_WITHOUT_CONID"),
                gate("entitlements_sufficient", "BLOCK", "UNEVALUABLE"),
            ],
            "evidence_ids": ["cluster-0001"],
            "risk_summary": "synthetic",
            "scenario_ids": [],
            "probability_evidence": None,
            "limitations": ["SYNTHETIC development population"],
            "explanation_facts": ["2 synthetic daily bars"],
            "supersedes": None,
        },
        "coverage": {
            "observations_considered": 1,
            "rejected_records": [],
            "lookback_seconds": 259200,
        },
    }


def snapshot(content: dict) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="analysis",
        key=INSTRUMENT,
        version=2,
        content=content,
        content_hash="sha256:" + "e" * 64,
        as_of=AS_OF,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def analysis_client(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    # Horloge FIXE : sans elle, le relais mesurerait l'âge de l'instantané
    # contre l'heure réelle et le déclarerait périmé quelques jours après
    # l'écriture de ce test, sans qu'aucun code ait changé.
    app.dependency_overrides[get_clock] = lambda: (lambda: _NOW)
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def test_requires_a_session(client: TestClient) -> None:
    assert client.get(f"/api/v1/analysis/{INSTRUMENT}").status_code == 401


def test_no_snapshot_is_honest_empty_200(analysis_client: TestClient) -> None:
    response = analysis_client.get(f"/api/v1/analysis/{INSTRUMENT}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["instrument"] == INSTRUMENT
    assert body["advice"] is None
    assert body["bars"] is None
    assert body["reason"] == "no snapshot published"


def test_published_dossier_is_relayed_verbatim(
    analysis_client: TestClient, reader: FakeSnapshotReader
) -> None:
    content = analysis_content()
    reader.snapshots[("analysis", INSTRUMENT)] = snapshot(content)

    response = analysis_client.get(f"/api/v1/analysis/{INSTRUMENT}")
    assert response.status_code == 200
    body = response.json()

    assert body["state"] == "ok"
    assert body["snapshot_version"] == 2
    assert body["population"] == "SYNTHETIC"
    assert body["bars"] == content["bars"]
    assert body["evidence"] == content["evidence"]
    assert body["scenarios"] == content["scenarios"]
    assert body["advice"] == content["advice"]
    assert body["coverage"] == content["coverage"]
    # The verdict and its gates travel untouched.
    assert body["advice"]["status"] == "INSUFFICIENT_DATA"
    assert body["advice"]["gates"][1]["reason_code"] == "UNEVALUABLE"


def test_snapshot_for_another_instrument_is_refused() -> None:
    with pytest.raises(SnapshotContentError):
        build_analysis_response(
            snapshot(analysis_content()), instrument="SYN-TECH-02", now=_NOW
        )


def test_non_canonical_advice_status_is_refused() -> None:
    content = analysis_content()
    content["advice"]["status"] = "APPROVED"  # not a canonical AdviceStatus
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)


def test_gate_without_reason_code_is_refused() -> None:
    content = analysis_content()
    del content["advice"]["gates"][0]["reason_code"]
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)


def test_computed_scenarios_must_be_theoretical() -> None:
    content = analysis_content()
    content["scenarios"] = {"status": "OK", "grid": []}  # missing value_nature
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)


# ---------------------------------------------------------------------------
# LOT-S2 — la comparaison base 100 SERVIE traverse le relais telle quelle
# ---------------------------------------------------------------------------


def test_la_comparaison_base_100_est_relayee_verbatim(
    analysis_client: TestClient, reader: FakeSnapshotReader
) -> None:
    """Le relais ne rebase rien et ne réaligne rien : il transporte."""
    content = analysis_content()
    reader.snapshots[("analysis", INSTRUMENT)] = snapshot(content)

    body = analysis_client.get(f"/api/v1/analysis/{INSTRUMENT}").json()

    assert body["indicators"] == content["indicators"]
    comparaison = body["indicators"]["rebased_comparison"]
    assert comparaison["base_value"] == "100"
    assert comparaison["series"][0] == {
        "trading_day": "2026-08-23",
        "instrument": "100.0",
        "benchmark": "100.0",
    }


def test_une_comparaison_servie_sans_base_declaree_est_refusee() -> None:
    """Une série d'index sans sa base n'est pas relayable : deux courbes dont
    personne ne pourrait dire de quoi elles partent."""
    content = analysis_content()
    del content["indicators"]["rebased_comparison"]["base_value"]
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)


def test_une_comparaison_servie_sans_lignee_est_refusee() -> None:
    content = analysis_content()
    del content["indicators"]["rebased_comparison"]["benchmark_calculation"]
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)


def test_une_comparaison_servie_sans_serie_est_refusee() -> None:
    content = analysis_content()
    del content["indicators"]["rebased_comparison"]["series"]
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)


def test_une_comparaison_absente_SANS_MOTIF_est_refusee() -> None:
    """Une absence muette est pire qu'une absence : l'écran ne saurait pas
    quoi dire à la place."""
    content = analysis_content()
    content["indicators"]["rebased_comparison"] = {"benchmark": "SPX"}
    with pytest.raises(SnapshotContentError):
        build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)


def test_un_dossier_publie_AVANT_la_comparaison_reste_relayable() -> None:
    """Une absence légitime n'est jamais une erreur : un dossier plus ancien
    ne porte pas ce bloc, et doit continuer d'être servi."""
    content = analysis_content()
    del content["indicators"]["rebased_comparison"]
    reponse = build_analysis_response(snapshot(content), instrument=INSTRUMENT, now=_NOW)
    assert reponse.state == "ok"
    assert reponse.indicators == {}
