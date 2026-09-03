"""Le relais d'analyse accepte-t-il ce que le worker produit RÉELLEMENT ?

Même méthode que ``test_risk_contract_matches_worker.py`` : le constructeur
du worker est APPELÉ et sa sortie passe au relais de l'API — aucune charge
fabriquée à la main. Un champ ajouté d'un côté et refusé de l'autre rougit
ici, avant de partir en 500 sur un dossier existant.

LOT S3 : les séries glissantes des indicateurs (``indicators.<nom>.series``,
une valeur rendue par séance servie) traversent le relais VERBATIM — ni
recalculées, ni tronquées, ni réordonnées. L'interface trace ce qu'elle
reçoit ; le serveur reste la seule autorité de calcul.

Unitaire et déterministe : barres en mémoire, horloge injectée, ni base ni
réseau.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import build_analysis_response
from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_persistence.repository.snapshots import CurrentSnapshot
from vertex_worker.analysis import (
    ATR_LOOKBACK,
    RELATIVE_STRENGTH_HORIZON,
    VOLATILITY_WINDOW,
    AnalysisConfig,
    BarRecord,
    build_analysis_content,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
#: Horloge du relais : trente minutes après la publication, dans le budget.
_RELAIS = NOW + timedelta(minutes=30)
INSTRUMENT = "SYN-TECH-01"
BENCHMARK = "SYN-TECH-02"
SEANCES = 80
INDICATEURS = ("realized_volatility", "atr", "relative_strength")

CONFIG = AnalysisConfig(
    instruments=(INSTRUMENT, BENCHMARK),
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
    benchmark=BENCHMARK,
)


def _barres(nombre: int, pas: float, depart: float = 100.0) -> list[dict]:
    premier = date(2026, 1, 2)
    barres = []
    for index in range(nombre):
        cloture = depart * (1.0 + pas) ** index
        barres.append(
            {
                "trading_day": (premier + timedelta(days=index)).isoformat(),
                "open": f"{cloture:.4f}",
                "high": f"{cloture * 1.01:.4f}",
                "low": f"{cloture * 0.99:.4f}",
                "close": f"{cloture:.4f}",
                "volume": 1000,
            }
        )
    return barres


def _enregistrement(ticker: str, pas: float, *, barres: list[dict] | None = None) -> BarRecord:
    return BarRecord(
        event_id=f"{SYNTHETIC_SOURCE}:bars:{ticker}",
        source=SYNTHETIC_SOURCE,
        instrument_ref=ticker,
        as_of=NOW - timedelta(hours=1),
        quality_status="VALID",
        rights=SYNTHETIC_RIGHTS,
        schema_version="synthetic-daily-bars/1.0",
        payload={
            "type": "daily_bars",
            "synthetic": True,
            "ticker": ticker,
            "currency": "SYN",
            "adjustment_basis": "synthetic-unadjusted",
            "bars": barres if barres is not None else _barres(SEANCES, pas),
        },
    )


def _contenu(enregistrements: list[BarRecord] | None = None) -> dict:
    """La sortie RÉELLE du worker, jamais une copie écrite à la main."""
    return build_analysis_content(
        enregistrements
        if enregistrements is not None
        else [_enregistrement(INSTRUMENT, 0.002), _enregistrement(BENCHMARK, 0.001)],
        instrument=INSTRUMENT,
        evidence_records=(),
        option_chain_content=None,
        option_chain_version=None,
        now=NOW,
        config=CONFIG,
    )


def _instantane(contenu: dict) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="analysis",
        key=INSTRUMENT,
        version=1,
        content=contenu,
        content_hash="sha256:" + "e" * 64,
        as_of=NOW,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def analysis_client(app: FastAPI, reader: FakeSnapshotReader) -> Iterator[TestClient]:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    app.dependency_overrides[get_clock] = lambda: (lambda: _RELAIS)
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def test_le_worker_publie_bien_les_trois_series() -> None:
    """Le fait amont, épinglé ici : sans lui, les tests de relais ci-dessous
    vérifieraient le passage d'une clé que personne n'écrit."""
    indicateurs = _contenu()["indicators"]
    for nom in INDICATEURS:
        assert indicateurs[nom]["status"] == "OK"
        assert indicateurs[nom]["series"]["status"] == "OK"
    assert indicateurs["realized_volatility"]["series"]["sessions"] == SEANCES - VOLATILITY_WINDOW
    assert indicateurs["atr"]["series"]["sessions"] == SEANCES - ATR_LOOKBACK
    assert (
        indicateurs["relative_strength"]["series"]["sessions"]
        == SEANCES - RELATIVE_STRENGTH_HORIZON
    )


def test_le_relais_accepte_la_sortie_du_worker() -> None:
    """LE TEST QUI COMPTE : worker → relais API, sans intermédiaire."""
    contenu = _contenu()
    reponse = build_analysis_response(_instantane(contenu), instrument=INSTRUMENT, now=_RELAIS)
    assert reponse.state == "ok"
    assert reponse.indicators is not None
    assert dict(reponse.indicators) == contenu["indicators"]


def test_les_series_traversent_le_relais_verbatim() -> None:
    """Chaque série arrive telle quelle : mêmes points, même ordre, mêmes
    chaînes, même lignée. Rien n'est recalculé ni « arrangé » côté API."""
    contenu = _contenu()
    reponse = build_analysis_response(_instantane(contenu), instrument=INSTRUMENT, now=_RELAIS)
    assert reponse.indicators is not None
    for nom in INDICATEURS:
        attendu = contenu["indicators"][nom]["series"]
        relaye = reponse.indicators[nom]["series"]
        assert relaye == attendu
        assert relaye["points"] == attendu["points"]
        assert relaye["calculation"] == attendu["calculation"]


def test_les_series_sortent_sur_le_fil_http_verbatim(
    analysis_client: TestClient, reader: FakeSnapshotReader
) -> None:
    """Sur GET /api/v1/analysis/{instrument}, après l'aller-retour JSON, le
    bloc `indicators` est celui que le worker a écrit — séries comprises."""
    contenu = _contenu()
    reader.snapshots[("analysis", INSTRUMENT)] = _instantane(contenu)

    response = analysis_client.get(f"/api/v1/analysis/{INSTRUMENT}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert body["indicators"] == contenu["indicators"]
    for nom in INDICATEURS:
        serie = body["indicators"][nom]["series"]
        assert serie["status"] == "OK"
        assert serie["points"][-1]["value"] == body["indicators"][nom]["value"]
        # Des chaînes, jamais des nombres flottants : l'interface n'arrondit rien.
        assert all(isinstance(point["value"], str) for point in serie["points"])


def test_un_refus_de_serie_traverse_le_relais_verbatim(
    analysis_client: TestClient, reader: FakeSnapshotReader
) -> None:
    """Une séance servie deux fois refuse les trois séries chez le worker
    (porte d'ordre strict, revue adverse du lot S3) ; le refus — statut,
    raison, séance en défaut — arrive tel quel sur le fil, sans point, jamais
    « arrangé » en OK par le relais."""
    barres = _barres(SEANCES, 0.002)
    barres.append(dict(barres[30]))
    contenu = _contenu(
        [_enregistrement(INSTRUMENT, 0.002, barres=barres), _enregistrement(BENCHMARK, 0.001)]
    )
    reader.snapshots[("analysis", INSTRUMENT)] = _instantane(contenu)

    response = analysis_client.get(f"/api/v1/analysis/{INSTRUMENT}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert body["indicators"] == contenu["indicators"]
    for nom in INDICATEURS:
        serie = body["indicators"][nom]["series"]
        assert serie["status"] == "REFUSED", nom
        assert serie["reason"] == "unordered_bars", nom
        assert serie["trading_day"] == barres[30]["trading_day"], nom
        assert "points" not in serie, nom
