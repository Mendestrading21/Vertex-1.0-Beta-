"""Le relais API accepte-t-il ce que le worker produit RÉELLEMENT ?

POURQUOI CE FICHIER EXISTE. Deux fois le 2026-09-01, un relais a été écrit
contre la charge ATTENDUE au lieu de la charge PRODUITE :

- le champ ``indicators`` relayé avec ``_wire_mapping``, qui refuse ``None`` :
  chaque dossier d'analyse pré-existant est parti en 500 ;
- le champ ``matrix_bands`` déclaré côté API et jamais publié par le chemin
  nominal du worker : les tests du relais passaient, parce qu'ils
  construisaient eux-mêmes une charge qui le contenait.

Les deux fois, la suite était verte. C'est la limite d'un test qui fabrique
son entrée : il vérifie que le validateur accepte ce que le test écrit, pas
ce que le worker écrit.

CE QUE CE FICHIER FAIT DIFFÉREMMENT. Il APPELLE le constructeur du worker et
passe sa sortie au validateur de l'API. Aucune charge fabriquée à la main. Si
les deux côtés divergent — un champ ajouté ici, exigé là — le test rougit.

Il reste unitaire et déterministe : les enregistrements de barres sont bâtis
en mémoire, il n'y a ni base, ni horloge réelle, ni réseau.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vertex_api.risk import RISK_CONTENT_SCHEMA_VERSION, checked_risk_content
from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_worker.analysis import BarRecord
from vertex_worker.risk import RiskConfig, build_risk_matrix_content

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

JOURS = tuple(f"2026-07-{jour:02d}" for jour in range(1, 32))
"""Trente et une séances : trente rendements, le seuil par défaut."""

CONFIG = RiskConfig(
    perimeter=("SYN-A", "SYN-B", "SYN-C"),
    labels={"SYN-A": "Alpha", "SYN-B": "Beta", "SYN-C": "Gamma"},
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)


def barres(ticker: str, depart: float, pas: float) -> BarRecord:
    return BarRecord(
        event_id=f"{SYNTHETIC_SOURCE}:bars:{ticker}",
        source=SYNTHETIC_SOURCE,
        instrument_ref=ticker,
        as_of=NOW - timedelta(hours=1),
        quality_status="VALID",
        rights=SYNTHETIC_RIGHTS,
        schema_version="synthetic-daily-bars/1",
        payload={
            "type": "daily_bars",
            "ticker": ticker,
            "currency": "USD",
            "adjustment_basis": "synthetic-unadjusted",
            "bars": [
                # Une oscillation, pour que les variances soient non nulles et
                # que les trois séries ne soient pas colinéaires.
                {
                    "trading_day": jour,
                    "close": f"{depart + pas * index + (index % 3) * 0.7:.4f}",
                }
                for index, jour in enumerate(JOURS)
            ],
        },
    )


LOT = [
    barres("SYN-A", 100.0, 0.9),
    barres("SYN-B", 50.0, -0.4),
    barres("SYN-C", 200.0, 2.1),
]


def test_le_relais_accepte_la_sortie_du_worker() -> None:
    """LE TEST QUI COMPTE : worker → validateur API, sans intermédiaire.

    Un champ ajouté d'un côté et exigé de l'autre fait rougir ici, avant la
    production — et non en 500 sur un dossier existant.
    """
    contenu = build_risk_matrix_content(LOT, now=NOW, config=CONFIG)
    valide = checked_risk_content(contenu)
    assert valide is contenu  # relayé VERBATIM, jamais recopié ni corrigé


def test_les_deux_cotes_annoncent_la_meme_version_de_schema() -> None:
    """Une version divergente serait une réinterprétation silencieuse."""
    contenu = build_risk_matrix_content(LOT, now=NOW, config=CONFIG)
    assert contenu["schema_version"] == RISK_CONTENT_SCHEMA_VERSION


def test_le_relais_accepte_aussi_un_refus_du_worker() -> None:
    """Le chemin de REFUS a sa propre forme, et elle doit passer aussi.

    C'est exactement là que la bande manquait : le chemin de refus la portait,
    le chemin nominal non. Tester un seul des deux laissait le trou ouvert.
    """
    contenu = build_risk_matrix_content([LOT[0]], now=NOW, config=CONFIG)
    assert contenu["coverage"]["refusal_reason"] == "perimeter_too_small"
    assert checked_risk_content(contenu) is contenu


def test_les_bandes_sont_bien_publiees_par_le_chemin_nominal() -> None:
    """Le défaut précis, épinglé pour qu'il ne revienne pas.

    ``matrix_bands`` était validé par l'API et absent du chemin nominal du
    worker. Les deux suites étaient vertes.
    """
    contenu = build_risk_matrix_content(LOT, now=NOW, config=CONFIG)
    bandes = contenu["matrix_bands"]
    assert len(bandes) == len(contenu["matrix"]) == 3
    for index, ligne in enumerate(bandes):
        assert len(ligne) == 3
        assert ligne[index] == "self"  # la diagonale se nomme, elle aussi


@pytest.mark.parametrize(
    ("seuil_modere", "seuil_fort"),
    [(0.3, 0.7), (0.2, 0.5), (0.45, 0.95)],
)
def test_les_seuils_declares_sont_ceux_qui_sortent(
    seuil_modere: float, seuil_fort: float
) -> None:
    """Les seuils PUBLIÉS sont ceux du registre, pas des constantes cachées.

    Un seuil affiché qui ne serait pas celui appliqué serait pire que pas de
    seuil du tout : il donnerait une explication fausse d'une couleur juste.
    """
    config = RiskConfig(
        perimeter=CONFIG.perimeter,
        labels=CONFIG.labels,
        allowed_sources=CONFIG.allowed_sources,
        usable_rights=CONFIG.usable_rights,
        moderate_threshold=seuil_modere,
        strong_threshold=seuil_fort,
    )
    contenu = build_risk_matrix_content(LOT, now=NOW, config=config)
    couverture = contenu["coverage"]
    assert couverture["moderate_threshold"] == f"{seuil_modere:.2f}"
    assert couverture["strong_threshold"] == f"{seuil_fort:.2f}"
    checked_risk_content(contenu)


def test_seuils_croises_refuses_a_la_construction() -> None:
    """Un seuil « modéré » au-dessus du seuil « fort » rendrait les bandes
    incohérentes : aucune case ne pourrait être forte sans être modérée."""
    with pytest.raises(ValueError, match="thresholds"):
        RiskConfig(
            perimeter=CONFIG.perimeter,
            labels=CONFIG.labels,
            allowed_sources=CONFIG.allowed_sources,
            usable_rights=CONFIG.usable_rights,
            moderate_threshold=0.8,
            strong_threshold=0.5,
        )


# ---------------------------------------------------------------------------
# LOT-S2 — le dossier d'analyse REELLEMENT produit passe le relais
# ---------------------------------------------------------------------------


def _barres_analyse(ticker: str, closes: list[str]) -> BarRecord:
    from decimal import Decimal

    barres = []
    for index, cloture in enumerate(closes):
        valeur = Decimal(cloture)
        barres.append(
            {
                "trading_day": f"2026-07-{index + 1:02d}",
                "open": format(valeur, "f"),
                "high": format(valeur * Decimal("1.01"), "f"),
                "low": format(valeur * Decimal("0.99"), "f"),
                "close": format(valeur, "f"),
                "volume": 1000,
            }
        )
    return BarRecord(
        event_id=f"{SYNTHETIC_SOURCE}:analysis-bars:{ticker}",
        source=SYNTHETIC_SOURCE,
        instrument_ref=ticker,
        as_of=NOW - timedelta(hours=1),
        quality_status="VALID",
        rights=SYNTHETIC_RIGHTS,
        schema_version="synthetic-daily-bars/1",
        payload={
            "type": "daily_bars",
            "ticker": ticker,
            "currency": "USD",
            "adjustment_basis": "split_adjusted",
            "bars": barres,
        },
    )


def test_la_comparaison_base_100_produite_par_le_worker_passe_le_relais() -> None:
    """Aucune charge fabriquée : le VRAI constructeur alimente le VRAI relais."""
    from vertex_api.snapshot_views import build_analysis_response
    from vertex_persistence.repository.snapshots import CurrentSnapshot
    from vertex_worker.analysis import AnalysisConfig, build_analysis_content

    config = AnalysisConfig(
        instruments=("SYN-A",),
        allowed_sources=frozenset({SYNTHETIC_SOURCE}),
        usable_rights=frozenset({SYNTHETIC_RIGHTS}),
        benchmark="SYN-B",
    )
    content = build_analysis_content(
        [
            _barres_analyse("SYN-A", ["100.00", "110.00", "121.00"]),
            _barres_analyse("SYN-B", ["50.00", "52.00", "54.00"]),
        ],
        instrument="SYN-A",
        evidence_records=(),
        option_chain_content=None,
        option_chain_version=None,
        now=NOW,
        config=config,
    )
    comparaison = content["indicators"]["rebased_comparison"]
    assert comparaison["status"] == "OK"
    assert comparaison["common_sessions"] == 3

    reponse = build_analysis_response(
        CurrentSnapshot(
            kind="analysis",
            key="SYN-A",
            version=1,
            content=content,
            content_hash="sha256:" + "f" * 64,
            as_of=NOW,
        ),
        instrument="SYN-A",
        now=NOW,
    )
    assert reponse.state == "ok"
    assert reponse.indicators is not None
    assert reponse.indicators["rebased_comparison"] == comparaison
