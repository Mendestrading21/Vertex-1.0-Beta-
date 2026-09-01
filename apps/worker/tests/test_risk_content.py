"""Tests unitaires du constructeur de contenu de la page Risques.

Tout est SYNTHETIQUE et deterministe : les enregistrements sont bâtis en
mémoire à partir de clôtures écrites en clair ; aucune base, aucune horloge,
aucun réseau.

Ce que ces tests protègent, dans l'ordre d'importance :

1. **L'alignement n'est jamais comblé.** Une séance manquante chez un seul
   instrument retire cette séance à TOUS. C'est le contrat de
   ``risk.covariance`` — un trou est refusé, jamais remplacé par zéro — et
   c'est ce que le contenu doit publier plutôt que masquer.
2. **Un périmètre insuffisant refuse au lieu d'inventer.** Moins de deux
   instruments, ou trop peu de séances communes, produit un refus NOMMÉ.
3. **La perte d'alignement est publiée.** ``trading_days_lost_to_alignment``
   dit à l'écran ce que l'intersection a coûté.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_core.version import ENGINE_VERSION
from vertex_worker.analysis import BarRecord
from vertex_worker.risk import (
    REASON_CALCULATION_REFUSED,
    REASON_INSUFFICIENT_COMMON_DAYS,
    REASON_NO_BARS,
    REASON_PERIMETER_TOO_SMALL,
    REASON_RIGHTS_NOT_USABLE,
    REASON_SOURCE_NOT_ALLOWED,
    RISK_SCHEMA_VERSION,
    RiskConfig,
    build_risk_matrix_content,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

CONFIG = RiskConfig(
    perimeter=("SYN-A", "SYN-B", "SYN-C"),
    labels={"SYN-A": "Alpha", "SYN-B": "Beta", "SYN-C": "Gamma"},
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
    minimum_common_days=4,
)

# Cinq séances : quatre rendements, juste au-dessus du seuil déclaré.
JOURS = ("2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21")


def barres(
    ticker: str,
    clotures: dict[str, str],
    *,
    source: str = SYNTHETIC_SOURCE,
    rights: str = SYNTHETIC_RIGHTS,
) -> BarRecord:
    return BarRecord(
        event_id=f"{source}:bars:{ticker}",
        source=source,
        instrument_ref=ticker,
        as_of=NOW - timedelta(hours=1),
        quality_status="VALID",
        rights=rights,
        schema_version="synthetic-daily-bars/1",
        payload={
            "type": "daily_bars",
            "ticker": ticker,
            "currency": "USD",
            "adjustment_basis": "synthetic-unadjusted",
            "bars": [
                {"trading_day": jour, "close": valeur}
                for jour, valeur in sorted(clotures.items())
            ],
        },
    )


def serie(depart: float, pas: float, jours: tuple[str, ...] = JOURS) -> dict[str, str]:
    """Une série croissante déterministe, écrite en clair."""
    return {jour: f"{depart + pas * index:.4f}" for index, jour in enumerate(jours)}


class TestCheminNominal:
    def test_matrice_complete_sur_le_perimetre(self):
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0)),
                barres("SYN-B", serie(50.0, -0.5)),
                barres("SYN-C", serie(200.0, 2.5)),
            ],
            now=NOW,
            config=CONFIG,
        )
        assert contenu["schema_version"] == RISK_SCHEMA_VERSION
        assert contenu["engine_version"] == ENGINE_VERSION
        # Ces barres portent les droits synthetiques : l aveu doit le dire.
        assert contenu["population"] == "SYNTHETIC"
        assert contenu["coverage"]["retained_count"] == 3
        assert contenu["coverage"]["refusal_reason"] is None
        assert [i["ticker"] for i in contenu["instruments"]] == ["SYN-A", "SYN-B", "SYN-C"]
        assert [i["label"] for i in contenu["instruments"]] == ["Alpha", "Beta", "Gamma"]

    def test_diagonale_publiee_a_un(self):
        """La diagonale sort du calcul telle qu'elle y est posée."""
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0)),
                barres("SYN-B", serie(50.0, -0.5)),
                barres("SYN-C", serie(200.0, 2.5)),
            ],
            now=NOW,
            config=CONFIG,
        )
        for index in range(3):
            assert contenu["matrix"][index][index] == "1.000"

    def test_matrice_rendue_en_chaines(self):
        """Le navigateur ne calcule rien : le serveur rend déjà les nombres.

        C'est la règle de ``.claude/rules/frontend.md`` — aucun calcul
        financier en TypeScript. Une matrice de flottants laisserait l'écran
        décider de l'arrondi.
        """
        contenu = build_risk_matrix_content(
            [barres("SYN-A", serie(100.0, 1.0)), barres("SYN-B", serie(50.0, -0.5))],
            now=NOW,
            config=CONFIG,
        )
        for ligne in contenu["matrix"]:
            for valeur in ligne:
                assert isinstance(valeur, str)

    def test_extremes_hors_diagonale(self):
        """La paire la plus liée ne peut pas être un actif avec lui-même."""
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0)),
                barres("SYN-B", serie(50.0, -0.5)),
                barres("SYN-C", serie(200.0, 2.5)),
            ],
            now=NOW,
            config=CONFIG,
        )
        extremes = contenu["extremes"]
        assert extremes["most_correlated"]["a"] != extremes["most_correlated"]["b"]
        assert extremes["most_opposed"]["a"] != extremes["most_opposed"]["b"]

    def test_avertissement_de_synchronicite_present(self):
        """Une matrice publiée sans cet avertissement se lirait de travers.

        Mesuré sur données réelles : SPX/N225 tombe à +0.168 parce que Tokyo
        ferme avant l'ouverture de New York, pas parce que le Japon serait
        décorrélé. L'écran doit porter ce doute.
        """
        contenu = build_risk_matrix_content(
            [barres("SYN-A", serie(100.0, 1.0)), barres("SYN-B", serie(50.0, -0.5))],
            now=NOW,
            config=CONFIG,
        )
        assert contenu["synchronicity_warning"]


class TestAlignement:
    def test_une_seance_manquante_est_retiree_a_tous(self):
        """LE POINT CENTRAL : l'intersection est stricte.

        SYN-C n'a pas coté le 2026-08-19. Cette séance disparaît donc AUSSI
        pour SYN-A et SYN-B — pas parce que c'est commode, mais parce que
        ``risk.covariance`` exige une matrice complète et refuse un trou. La
        seule alternative serait de combler, c'est-à-dire d'inventer.
        """
        incomplet = {j: v for j, v in serie(200.0, 2.5).items() if j != "2026-08-19"}
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0)),
                barres("SYN-B", serie(50.0, -0.5)),
                barres("SYN-C", incomplet),
            ],
            now=NOW,
            config=RiskConfig(
                perimeter=CONFIG.perimeter,
                labels=CONFIG.labels,
                allowed_sources=CONFIG.allowed_sources,
                usable_rights=CONFIG.usable_rights,
                minimum_common_days=3,
            ),
        )
        couverture = contenu["coverage"]
        assert couverture["common_trading_days"] == 4  # 5 séances moins celle qui manque
        assert couverture["trading_days_per_instrument"]["SYN-A"] == 5
        assert couverture["trading_days_per_instrument"]["SYN-C"] == 4

    def test_la_perte_d_alignement_est_publiee(self):
        """Ce que l'intersection coûte doit être LU, pas déduit."""
        incomplet = {j: v for j, v in serie(200.0, 2.5).items() if j != "2026-08-19"}
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0)),
                barres("SYN-B", serie(50.0, -0.5)),
                barres("SYN-C", incomplet),
            ],
            now=NOW,
            config=RiskConfig(
                perimeter=CONFIG.perimeter,
                labels=CONFIG.labels,
                allowed_sources=CONFIG.allowed_sources,
                usable_rights=CONFIG.usable_rights,
                minimum_common_days=3,
            ),
        )
        perdues = contenu["coverage"]["trading_days_lost_to_alignment"]
        assert perdues["SYN-A"] == 1  # avait 5 séances, n'en garde que 4
        assert perdues["SYN-C"] == 0  # c'est lui qui impose l'intersection


class TestRefus:
    def test_perimetre_reduit_a_un_instrument(self):
        """Une matrice de corrélation COMPARE ; elle ne décrit pas."""
        contenu = build_risk_matrix_content(
            [barres("SYN-A", serie(100.0, 1.0))], now=NOW, config=CONFIG
        )
        assert contenu["matrix"] == []
        assert contenu["coverage"]["refusal_reason"] == REASON_PERIMETER_TOO_SMALL
        motifs = {e["reason"] for e in contenu["coverage"]["discarded"]}
        assert motifs == {REASON_NO_BARS}

    def test_trop_peu_de_seances_communes(self):
        """Un nombre qui sort n'est pas un nombre qui veut dire quelque chose.

        ``risk.covariance`` accepte deux observations. Le seuil déclaré, lui,
        refuse une corrélation sur trois séances : ce serait du bruit présenté
        comme une mesure.
        """
        courtes = ("2026-08-17", "2026-08-18", "2026-08-19")
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0, courtes)),
                barres("SYN-B", serie(50.0, -0.5, courtes)),
            ],
            now=NOW,
            config=CONFIG,  # exige 4 rendements
        )
        assert contenu["coverage"]["refusal_reason"] == REASON_INSUFFICIENT_COMMON_DAYS
        assert contenu["coverage"]["minimum_common_days"] == 4
        assert contenu["matrix"] == []

    def test_serie_constante_refusee_par_le_calcul(self):
        """Variance nulle : ``risk.correlation`` refuse, et le refus remonte.

        Un titre suspendu à la cote ne bouge pas. Le contenu porte alors le
        motif du calcul plutôt qu'une matrice trouée.
        """
        plate = dict.fromkeys(JOURS, "100.0000")
        contenu = build_risk_matrix_content(
            [barres("SYN-A", serie(100.0, 1.0)), barres("SYN-B", plate)],
            now=NOW,
            config=CONFIG,
        )
        assert contenu["coverage"]["refusal_reason"] == REASON_CALCULATION_REFUSED
        assert "variance nulle" in contenu["conclusion"]

    def test_source_non_declaree_rejetee_et_comptee(self):
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0)),
                barres("SYN-B", serie(50.0, -0.5), source="inconnue"),
            ],
            now=NOW,
            config=CONFIG,
        )
        motifs = {r["reason"] for r in contenu["coverage"]["rejected_records"]}
        assert motifs == {REASON_SOURCE_NOT_ALLOWED}
        assert contenu["coverage"]["refusal_reason"] == REASON_PERIMETER_TOO_SMALL

    def test_droits_inutilisables_rejetes_et_comptes(self):
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0)),
                barres("SYN-B", serie(50.0, -0.5), rights="AUCUN"),
            ],
            now=NOW,
            config=CONFIG,
        )
        motifs = {r["reason"] for r in contenu["coverage"]["rejected_records"]}
        assert motifs == {REASON_RIGHTS_NOT_USABLE}


class TestContrats:
    def test_horodatage_naif_refuse(self):
        """Un instant sans fuseau est ambigu ; le contenu le refuse."""
        naif = NOW.replace(tzinfo=None)
        with pytest.raises(ValueError, match="naive"):
            build_risk_matrix_content([], now=naif, config=CONFIG)

    def test_perimetre_a_un_seul_membre_refuse_a_la_construction(self):
        with pytest.raises(ValueError, match="at least two"):
            RiskConfig(
                perimeter=("SEUL",),
                labels={},
                allowed_sources=frozenset({SYNTHETIC_SOURCE}),
                usable_rights=frozenset({SYNTHETIC_RIGHTS}),
            )

    def test_perimetre_avec_doublon_refuse(self):
        with pytest.raises(ValueError, match="duplicate"):
            RiskConfig(
                perimeter=("A", "B", "A"),
                labels={},
                allowed_sources=frozenset({SYNTHETIC_SOURCE}),
                usable_rights=frozenset({SYNTHETIC_RIGHTS}),
            )

    def test_seuil_sous_deux_refuse(self):
        """``ddof = 1`` : sous deux observations, il n'y a pas de variance."""
        with pytest.raises(ValueError, match="ddof"):
            RiskConfig(
                perimeter=("A", "B"),
                labels={},
                allowed_sources=frozenset({SYNTHETIC_SOURCE}),
                usable_rights=frozenset({SYNTHETIC_RIGHTS}),
                minimum_common_days=1,
            )

    def test_deterministe_quel_que_soit_l_ordre(self):
        """Mêmes enregistrements dans un autre ordre : même contenu."""
        lot = [
            barres("SYN-A", serie(100.0, 1.0)),
            barres("SYN-B", serie(50.0, -0.5)),
            barres("SYN-C", serie(200.0, 2.5)),
        ]
        premier = build_risk_matrix_content(lot, now=NOW, config=CONFIG)
        second = build_risk_matrix_content(list(reversed(lot)), now=NOW, config=CONFIG)
        assert premier == second


class TestPopulation:
    """`population` est un AVEU sur la fenetre d entree, jamais une etiquette."""

    def test_fenetre_vide_avouee(self):
        contenu = build_risk_matrix_content([], now=NOW, config=CONFIG)
        assert contenu["population"] == "EMPTY"

    def test_une_seule_barre_synthetique_contamine_tout(self):
        """Une matrice batie sur des rendements synthetiques EST synthetique.

        Ce n est pas une precaution : les rendements de l instrument
        synthetique entrent dans CHAQUE coefficient de la matrice, y compris
        ceux qui relient deux instruments reels — l intersection des seances
        est commune. Etiqueter REAL serait faux pour toute la grille.
        """
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0), source="ibkr", rights="ibkr:live"),
                barres("SYN-B", serie(50.0, -0.5), source="ibkr", rights="ibkr:live"),
                barres("SYN-C", serie(200.0, 2.5)),  # synthetique
            ],
            now=NOW,
            config=RiskConfig(
                perimeter=CONFIG.perimeter,
                labels=CONFIG.labels,
                allowed_sources=frozenset({SYNTHETIC_SOURCE, "ibkr"}),
                usable_rights=frozenset({SYNTHETIC_RIGHTS, "ibkr:live"}),
                minimum_common_days=4,
            ),
        )
        assert contenu["coverage"]["retained_count"] == 3
        assert contenu["population"] == "SYNTHETIC"

    def test_barres_entierement_reelles_avouees_reelles(self):
        contenu = build_risk_matrix_content(
            [
                barres("SYN-A", serie(100.0, 1.0), source="ibkr", rights="ibkr:live"),
                barres("SYN-B", serie(50.0, -0.5), source="ibkr", rights="ibkr:live"),
            ],
            now=NOW,
            config=RiskConfig(
                perimeter=CONFIG.perimeter,
                labels=CONFIG.labels,
                allowed_sources=frozenset({"ibkr"}),
                usable_rights=frozenset({"ibkr:live"}),
                minimum_common_days=4,
            ),
        )
        assert contenu["population"] == "REAL"
