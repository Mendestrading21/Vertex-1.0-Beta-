"""GET /api/v1/risk/matrix : relais verbatim, refus lisibles, vide honnête, 401.

Tout est SYNTHÉTIQUE : le lecteur factice est injecté par
``dependency_overrides`` et le contenu des instantanés reproduit exactement la
forme que publie ``vertex_worker.risk.build_risk_matrix_content``.

Trois choses que ces tests protègent, dans l'ordre d'importance :

1. **Un refus reste ``state = "ok"``.** Quand le worker n'a pas pu bâtir la
   matrice — périmètre trop court, séances communes insuffisantes, variance
   nulle — il publie quand même, avec un motif et une conclusion en français.
   Le dégrader en ``empty`` effacerait le motif et l'écran ressemblerait à
   une panne.
2. **Une matrice non carrée est REFUSÉE.** Elle casserait l'écran en silence :
   chaque ligne serait lue en face du mauvais instrument.
3. **L'API ne recalcule rien.** Les coefficients arrivent en chaînes et
   repartent identiques, au caractère près.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.risk import (
    REASON_NO_SNAPSHOT_PUBLISHED,
    RISK_CONTENT_SCHEMA_VERSION,
    RISK_MAX_AGE,
    build_risk_response,
    checked_risk_content,
)
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
NOW = AS_OF + timedelta(minutes=5)
"""Instant de relais de chaque test : aucune assertion ne dépend de l'heure."""

ROUTE = "/api/v1/risk/matrix"


def contenu(
    *,
    instruments: tuple[str, ...] = ("SPX", "NDX"),
    matrix: list[list[str]] | None = None,
    refusal: str | None = None,
    population: str = "REAL",
    data_state: str = "ok",
) -> dict[str, Any]:
    """La forme exacte que publie le worker, refus compris."""
    return {
        "schema_version": RISK_CONTENT_SCHEMA_VERSION,
        "as_of": AS_OF.isoformat(),
        "population": population,
        "data_state": data_state,
        "unit": "correlation_coefficient",
        "engine_version": "0.0.0-test",
        "conclusion": "Matrice synthétique de test.",
        "instruments": [{"ticker": t, "label": t} for t in instruments],
        "matrix": matrix if matrix is not None else [["1.000", "0.927"], ["0.927", "1.000"]],
        "extremes": {
            "most_correlated": {"a": "SPX", "b": "NDX", "value": "0.927"},
            "most_opposed": {"a": "SPX", "b": "NDX", "value": "0.927"},
        },
        "synchronicity_warning": "Les places ne ferment pas à la même heure.",
        "coverage": {
            "perimeter": list(instruments),
            "perimeter_size": len(instruments),
            "retained": list(instruments),
            "retained_count": len(instruments),
            "discarded": [],
            "rejected_records": [],
            "common_trading_days": 243,
            "minimum_common_days": 30,
            "trading_days_per_instrument": {t: 251 for t in instruments},
            "observations_considered": 8,
            "lookback_seconds": 1209600,
            "refusal_reason": refusal,
        },
    }


def instantane(charge: dict[str, Any], *, as_of: datetime = AS_OF) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="risk_matrix",
        key="global",
        version=1,
        content=charge,
        content_hash="synthetic-hash",
        as_of=as_of,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def api(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    # Horloge FIXE : le relais publie l'âge et bascule en `stale` au-delà du
    # budget. Sans horloge injectée, ce test deviendrait rouge tout seul.
    app.dependency_overrides[get_clock] = lambda: (lambda: NOW)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


class TestRoute:
    def test_session_exigee(self, client: TestClient) -> None:
        assert client.get(ROUTE).status_code == 401

    def test_vide_honnete_en_200(self, api: TestClient) -> None:
        """Aucun instantané publié : absent reste absent, avec son motif."""
        body = api.get(ROUTE).json()
        assert body["state"] == "empty"
        assert body["content"] is None
        assert body["snapshot_version"] is None
        assert body["reason"] == REASON_NO_SNAPSHOT_PUBLISHED

    def test_relais_verbatim(self, api: TestClient, reader: FakeSnapshotReader) -> None:
        """Les coefficients repartent au caractère près."""
        charge = contenu()
        reader.snapshots[("risk_matrix", "global")] = instantane(charge)

        body = api.get(ROUTE).json()
        assert body["state"] == "ok"
        assert body["snapshot_version"] == 1
        assert body["content"]["matrix"] == charge["matrix"]
        assert body["content"]["extremes"] == charge["extremes"]
        assert body["content"]["coverage"] == charge["coverage"]

    def test_avertissement_de_synchronicite_relaye(
        self, api: TestClient, reader: FakeSnapshotReader
    ) -> None:
        """Sans lui, une corrélation entre continents se lirait de travers."""
        reader.snapshots[("risk_matrix", "global")] = instantane(contenu())
        body = api.get(ROUTE).json()
        assert body["content"]["synchronicity_warning"]

    def test_refus_du_worker_reste_ok(
        self, api: TestClient, reader: FakeSnapshotReader
    ) -> None:
        """LE POINT CENTRAL : un refus motivé n'est pas une absence.

        Le worker A publié ; ce qu'il a publié est un refus. Le rendre
        ``empty`` effacerait le motif, et l'écran ressemblerait à une panne
        au lieu de dire « pas assez de séances communes ».
        """
        charge = contenu(
            instruments=(),
            matrix=[],
            refusal="insufficient_common_days",
            data_state="insufficient",
        )
        reader.snapshots[("risk_matrix", "global")] = instantane(charge)

        body = api.get(ROUTE).json()
        assert body["state"] == "ok"
        assert body["content"]["matrix"] == []
        assert body["content"]["coverage"]["refusal_reason"] == "insufficient_common_days"
        assert body["content"]["conclusion"]

    def test_instantane_perime_signale(
        self, api: TestClient, reader: FakeSnapshotReader
    ) -> None:
        """Une corrélation de trois jours ne doit pas se lire comme fraîche."""
        vieux = NOW - RISK_MAX_AGE - timedelta(hours=1)
        reader.snapshots[("risk_matrix", "global")] = instantane(contenu(), as_of=vieux)

        body = api.get(ROUTE).json()
        assert body["state"] == "stale"
        assert body["reason"]
        assert body["age_seconds"] > int(RISK_MAX_AGE.total_seconds())
        # Le contenu est relayé QUAND MÊME : périmé n'est pas absent.
        assert body["content"]["matrix"]


class TestFormeRefusee:
    """Relais verbatim n'est pas relais non vérifié (P1-G)."""

    def test_matrice_non_carree_refusee(self) -> None:
        """Elle casserait l'écran en silence, ligne contre mauvais instrument."""
        with pytest.raises(SnapshotContentError, match="carrée"):
            checked_risk_content(
                contenu(instruments=("SPX", "NDX"), matrix=[["1.000", "0.927"], ["0.927"]])
            )

    def test_matrice_de_taille_incoherente_refusee(self) -> None:
        with pytest.raises(SnapshotContentError, match="lignes attendues"):
            checked_risk_content(
                contenu(instruments=("SPX", "NDX", "DAX"), matrix=[["1.000", "0.927"]])
            )

    def test_coefficient_numerique_refuse(self) -> None:
        """La grille arrive en CHAÎNES : un flottant laisserait l'écran arrondir.

        C'est la règle de ``.claude/rules/frontend.md`` — aucun calcul
        financier en TypeScript, arrondi compris.
        """
        with pytest.raises(SnapshotContentError):
            checked_risk_content(contenu(matrix=[[1.0, 0.927], [0.927, 1.0]]))

    def test_autre_version_de_schema_refusee(self) -> None:
        """Une charge annonçant une autre version n'est pas relue de force."""
        charge = contenu()
        charge["schema_version"] = "vertex.risk-matrix/2.0"
        with pytest.raises(SnapshotContentError, match="schema_version"):
            checked_risk_content(charge)

    def test_population_inconnue_refusee(self) -> None:
        """Deny-by-default : « pas REAL » ne veut pas dire « inoffensif »."""
        with pytest.raises(SnapshotContentError, match="population"):
            checked_risk_content(contenu(population="PROBABLEMENT_REEL"))

    def test_etat_inconnu_refuse(self) -> None:
        with pytest.raises(SnapshotContentError, match="data_state"):
            checked_risk_content(contenu(data_state="a_peu_pres"))

    def test_couverture_absente_refusee(self) -> None:
        charge = contenu()
        del charge["coverage"]
        with pytest.raises(SnapshotContentError, match="coverage"):
            checked_risk_content(charge)


class TestRelaisPur:
    def test_absence_ne_devient_pas_erreur(self) -> None:
        reponse = build_risk_response(None, now=NOW)
        assert reponse.state == "empty"
        assert reponse.content is None
        assert reponse.age_seconds is None

    def test_deux_appels_rendent_la_meme_chose(self) -> None:
        """Le relais est pur : il n'injecte aucune horloge dans le contenu."""
        snap = instantane(contenu())
        premier = build_risk_response(snap, now=NOW)
        second = build_risk_response(snap, now=NOW)
        assert premier.content == second.content
