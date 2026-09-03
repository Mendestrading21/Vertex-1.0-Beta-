"""Une corrélation « la plus opposée » est NÉGATIVE — le garde commun doit l'admettre.

POURQUOI CE FICHIER EXISTE. `docs/08-runbooks/REPRENDRE_ICI.md` §4.3 signale un
500 LATENT sur la page Risques : la clé de feuille `"value"` appartient à
`_DECIMAL_KEYS`, la classe NON SIGNÉE, alors que `extremes.most_opposed.value`
vaut `-0.803` sur données réelles. Une corrélation « la plus opposée » est
négative **par définition** — c'est ce que le mot veut dire.

Le défaut ne se voit pas aujourd'hui parce que `risk.py` appelle son propre
validateur `checked_risk_content`, qui ne traverse pas les classes de feuilles.
Toute uniformisation qui brancherait la route sur `checked_relayed_content` —
le garde commun de tous les autres relais — la mettrait en 500 sur données
réelles, sans qu'aucun test existant ne l'ait vu.

CE QUE CE FICHIER FAIT, ET POURQUOI C'EST LE BON MOTIF. Il n'écrit pas la
charge à la main : il APPELLE le constructeur du worker avec deux séries
**anti-corrélées**, et passe sa sortie au garde commun. C'est le motif de
`test_risk_contract_matches_worker.py`, retenu dans la passation comme la parade
au défaut le plus fréquent de ce dépôt — quelque chose déclaré d'un côté et
jamais branché de l'autre, avec les deux suites au vert parce qu'elles
construisent la charge attendue plutôt que la charge produite.

CE QUE CE FICHIER PROTÈGE AUSSI, ET C'EST LA MOITIÉ QUI COMPTE. Déplacer
`"value"` vers la classe signée DESSERRE une garde : la même clé sert à
`breadth.value` (un ratio de participation, borné à [0, 1]) et à
`coverage.value`. Un desserrage silencieux serait exactement ce que
`.claude/rules/testing.md` interdit. Les tests ci-dessous épinglent donc les
DEUX faces : ce qui doit désormais passer, et ce qui doit continuer d'être
refusé ailleurs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from vertex_api.snapshot_views import SnapshotContentError, checked_relayed_content
from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_worker.analysis import BarRecord
from vertex_worker.risk import RiskConfig, build_risk_matrix_content

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

JOURS = tuple(f"2026-07-{jour:02d}" for jour in range(1, 32))
"""Trente et une séances : trente rendements, le seuil par défaut du worker."""

CONFIG = RiskConfig(
    perimeter=("SYN-UP", "SYN-TWIN", "SYN-DOWN", "SYN-SIDE"),
    labels={
        "SYN-UP": "Indice haussier",
        "SYN-TWIN": "Indice jumeau",
        "SYN-DOWN": "Indice baissier",
        "SYN-SIDE": "Indice latéral",
    },
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)


def barres(ticker: str, closes: list[float]) -> BarRecord:
    """Un enregistrement de barres, clôtures imposées — aucun hasard."""
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
                {"trading_day": jour, "close": f"{close:.4f}"}
                for jour, close in zip(JOURS, closes, strict=True)
            ],
        },
    )


def lot_anticorrele() -> list[BarRecord]:
    """Deux séries en OPPOSITION, une troisième décorrélée.

    `SYN-UP` et `SYN-DOWN` bougent en sens strictement inverse : leur
    corrélation de rendements est proche de -1. C'est le cas RÉEL décrit dans
    la passation (`-0.803` mesuré sur huit indices mondiaux), reproduit ici
    sans aucune donnée de marché.
    """
    montant = [100.0 + 0.9 * index + (index % 3) * 0.7 for index in range(len(JOURS))]
    # Jumeau : même mouvement à l'échelle près, donc corrélation proche de +1.
    # Sans lui, TOUTES les paires étaient négatives et « la plus corrélée »
    # l'était aussi — le refus tombait alors sur la mauvaise paire et le
    # reproducteur ne prouvait pas ce qu'il annonçait.
    jumeau = [40.0 + (valeur - 100.0) * 0.55 for valeur in montant]
    # Opposé exact du mouvement, donc des rendements de signe contraire.
    descendant = [300.0 - (valeur - 100.0) * 1.3 for valeur in montant]
    # Un quatrième profil, pour que la matrice ne soit pas dégénérée.
    lateral = [50.0 + (index % 5) * 0.4 for index in range(len(JOURS))]
    return [
        barres("SYN-UP", montant),
        barres("SYN-TWIN", jumeau),
        barres("SYN-DOWN", descendant),
        barres("SYN-SIDE", lateral),
    ]


def test_le_worker_publie_bien_une_valeur_la_plus_opposee_negative() -> None:
    """Prémisse du reproducteur : sans elle, le test suivant ne prouverait rien.

    Si le lot n'était pas réellement anti-corrélé, `most_opposed.value` serait
    positif et le test d'après passerait pour une mauvaise raison.
    """
    contenu = build_risk_matrix_content(lot_anticorrele(), now=NOW, config=CONFIG)
    opposee = contenu["extremes"]["most_opposed"]
    correlee = contenu["extremes"]["most_correlated"]
    assert Decimal(str(opposee["value"])) < 0, (
        "le lot de test n'est pas anti-corrélé : le reproducteur ne prouverait rien"
    )
    # Et la plus CORRÉLÉE doit être positive, sinon le refus tomberait sur
    # elle et le test suivant passerait pour une mauvaise raison.
    assert Decimal(str(correlee["value"])) > 0


def test_le_garde_commun_accepte_la_correlation_la_plus_opposee() -> None:
    """LE REPRODUCTEUR. Rouge tant que `value` est dans la classe non signée.

    C'est le 500 latent : brancher la route Risques sur le garde commun, comme
    tous les autres relais, la ferait tomber sur données réelles.
    """
    contenu = build_risk_matrix_content(lot_anticorrele(), now=NOW, config=CONFIG)
    valide = checked_relayed_content(contenu)
    assert valide is contenu  # relayé VERBATIM, jamais recopié ni corrigé


def test_une_valeur_hors_forme_reste_refusee() -> None:
    """Le desserrage n'ouvre pas la porte : ce n'est pas « accepter n'importe quoi ».

    Une classe SIGNÉE reste une classe : un décimal est exigé, et une prose
    glissée à la place d'un nombre est toujours refusée.
    """
    contenu = dict(build_risk_matrix_content(lot_anticorrele(), now=NOW, config=CONFIG))
    extremes = dict(contenu["extremes"])
    opposee = dict(extremes["most_opposed"])
    opposee["value"] = "moins zéro virgule huit"
    extremes["most_opposed"] = opposee
    contenu["extremes"] = extremes

    with pytest.raises(SnapshotContentError) as refus:
        checked_relayed_content(contenu)
    assert "most_opposed.value" in str(refus.value)
    # Le message nomme le CHEMIN, jamais la valeur (règle du garde commun).
    assert "moins zéro" not in str(refus.value)


def test_la_borne_de_correlation_reste_tenue_par_le_validateur_de_la_page() -> None:
    """CE QUE LE DESSERRAGE COÛTE, ET QUI LE RATTRAPE.

    Le garde commun classe par NOM DE FEUILLE : il ne peut pas savoir que
    `extremes.*.value` vit dans [-1, 1] et que `breadth.value` vit dans [0, 1].
    Cette connaissance appartient au validateur de la page, qui la garde.

    Ce test épingle la frontière : le garde commun dit « c'est un décimal
    signé », le validateur de page dit « et il est dans sa borne ». Retirer le
    second rendrait le premier insuffisant.
    """
    from vertex_api.risk import checked_risk_content

    contenu = dict(build_risk_matrix_content(lot_anticorrele(), now=NOW, config=CONFIG))
    extremes = dict(contenu["extremes"])
    opposee = dict(extremes["most_opposed"])
    opposee["value"] = "-4.2"  # hors [-1, 1] : impossible pour une corrélation
    extremes["most_opposed"] = opposee
    contenu["extremes"] = extremes

    with pytest.raises(SnapshotContentError):
        checked_risk_content(contenu)


def test_une_cellule_de_matrice_en_prose_est_refusee() -> None:
    """TROU MESURÉ, non signalé par la passation : `abc` passait.

    `_checked_matrix` n'exigeait qu'une CHAÎNE. Une cellule inclassable
    arrivait donc jusqu'à l'écran, où elle serait peinte comme une case de
    corrélation — une invention pure, exactement ce que la bande
    « deny-by-default » de `_checked_bands` refuse un cran plus loin.
    """
    from vertex_api.risk import checked_risk_content

    contenu = dict(build_risk_matrix_content(lot_anticorrele(), now=NOW, config=CONFIG))
    contenu["matrix"] = [list(ligne) for ligne in contenu["matrix"]]
    contenu["matrix"][0][1] = "abc"

    with pytest.raises(SnapshotContentError) as refus:
        checked_risk_content(contenu)
    assert "matrix[0][1]" in str(refus.value)


def test_une_cellule_de_matrice_hors_borne_est_refusee() -> None:
    """Un coefficient de corrélation vit dans [-1, 1]. Toujours.

    `1.4` n'est pas une corrélation faible ou forte : ce n'est pas une
    corrélation. La refuser vaut mieux que la peindre.
    """
    from vertex_api.risk import checked_risk_content

    contenu = dict(build_risk_matrix_content(lot_anticorrele(), now=NOW, config=CONFIG))
    contenu["matrix"] = [list(ligne) for ligne in contenu["matrix"]]
    contenu["matrix"][0][1] = "1.4"

    with pytest.raises(SnapshotContentError):
        checked_risk_content(contenu)


def test_la_participation_de_marches_reste_bornee_a_zero_un() -> None:
    """CE QUE LE DÉPLACEMENT DE `value` AURAIT COÛTÉ AILLEURS.

    `breadth.value` est une PARTICIPATION : le nombre d'instruments au-dessus
    de leur repère, rapporté aux couverts. Elle vit dans [0, 1] et ne peut pas
    être négative.

    Or `_markets_breadth` ne la lit qu'avec `_optional_str` : le garde commun,
    via la classe NON SIGNÉE, était sa SEULE protection. Déplacer `value` vers
    la classe signée sans rien mettre à la place aurait donc troqué un faux
    refus sur Risques contre une vraie perte sur Marchés — un desserrage
    silencieux, que `.claude/rules/testing.md` interdit.
    """
    from vertex_api.snapshot_views import _markets_breadth

    for valeur in ("-0.10", "1.40"):
        with pytest.raises(SnapshotContentError):
            _markets_breadth(
                {
                    "status": "OK",
                    "reason": None,
                    "value": valeur,
                    "value_pct": "50.0",
                    "above_count": 2,
                    "down_count": 1,
                    "flat_count": 1,
                    "covered_count": 4,
                    "universe_size": 4,
                    "coverage_pct": "100.0",
                    "coverage_threshold": "0.8",
                    "coverage_threshold_pct": "80.0",
                    "calculation": {},
                }
            )
