"""Profils de fusion : ce qui a le droit d'atteindre l'écran, et rien d'autre.

CE QUE CES TESTS PROTÈGENT. Les six registres du worker sont deny-by-default :
une observation dont la `source` ou les `rights` ne sont pas déclarés est
refusée avant toute publication. C'est la garantie « rien de non vérifié ne
s'affiche ». Ces tests vérifient que :

1. le réel ne s'active JAMAIS par omission — le défaut reste synthétique ;
2. le profil synthétique refuse toujours IBKR, et réciproquement ;
3. les SIX registres portent la même déclaration — un seul oublié laisserait
   une page bloquée en SYNTHETIC pendant que les autres passent en REAL ;
4. aucun secteur n'est inventé ;
5. IBKR n'est pas promu en confiance sans échelle déclarée ;
6. un instrument sans symbole est refusé AVANT d'atteindre l'écran, où son
   rejet serait invisible.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vertex_core.contracts.market_quote import UNCLASSIFIED_SECTOR_CODE
from vertex_worker.handlers import DEFAULT_SOURCE_TIER
from vertex_worker.profiles import (
    IBKR_RIGHTS,
    IBKR_SOURCE,
    MAX_REAL_INSTRUMENTS,
    PROFILE_ENV_VAR,
    PROFILE_REAL,
    PROFILE_SYNTHETIC,
    REAL_SECTOR_CODE,
    ProfileError,
    RealInstrument,
    WorkerProfile,
    load_real_instruments,
    real_ibkr_profile,
    resolve_profile,
    synthetic_profile,
)

GOOG = RealInstrument(ref="208813720", symbol="GOOG")
AAPL = RealInstrument(ref="265598", symbol="AAPL")
INSTRUMENTS = (GOOG, AAPL)
REFS = ("208813720", "265598")
SYMBOLES = ("GOOG", "AAPL")


def ecrire_univers(tmp_path: Path, *paires: tuple[int, str]) -> Path:
    fichier = tmp_path / "univers.json"
    fichier.write_text(
        json.dumps(
            {"instruments": [{"con_id": c, "symbol": s, "sec_type": "STK"} for c, s in paires]}
        ),
        encoding="utf-8",
    )
    return fichier


def registres(profil: WorkerProfile) -> tuple[object, ...]:
    """Les SIX registres qui décident de ce qui atteint l'écran."""
    return (
        profil.fusion,
        profil.markets,
        profil.options,
        profil.analysis,
        profil.calendar,
        profil.opportunities,
    )


# -- le réel ne s'active jamais par omission -------------------------------


def test_sans_variable_le_profil_est_synthetique() -> None:
    """Le défaut ne doit JAMAIS ouvrir la porte au réel."""
    assert resolve_profile({}).name == PROFILE_SYNTHETIC


@pytest.mark.parametrize("valeur", ["", "  ", "synthetic", "SYNTHETIC", " Synthetic "])
def test_valeurs_synthetiques_acceptees(valeur: str) -> None:
    assert resolve_profile({PROFILE_ENV_VAR: valeur}).name == PROFILE_SYNTHETIC


@pytest.mark.parametrize("valeur", ["reel", "prod", "REAL_", "true", "1"])
def test_un_profil_inconnu_est_refuse(valeur: str) -> None:
    """Une faute de frappe ne doit pas retomber silencieusement sur un défaut."""
    with pytest.raises(ProfileError, match="inconnu"):
        resolve_profile({PROFILE_ENV_VAR: valeur})


def test_le_profil_reel_exige_un_univers_declare() -> None:
    with pytest.raises(ProfileError, match="VERTEX_IBKR_UNIVERSE"):
        resolve_profile({PROFILE_ENV_VAR: PROFILE_REAL})


def test_le_profil_reel_se_construit_depuis_l_univers(tmp_path: Path) -> None:
    chemin = ecrire_univers(tmp_path, (208813720, "GOOG"), (265598, "AAPL"))
    profil = resolve_profile({PROFILE_ENV_VAR: PROFILE_REAL, "VERTEX_IBKR_UNIVERSE": str(chemin)})
    assert profil.name == PROFILE_REAL
    assert profil.is_real is True
    assert profil.analysis.instruments == SYMBOLES
    assert profil.markets.all_tickers() == SYMBOLES


# -- les deux profils s'excluent -------------------------------------------


def test_le_profil_synthetique_refuse_toujours_ibkr() -> None:
    for registre in registres(synthetic_profile()):
        assert IBKR_SOURCE not in registre.allowed_sources  # type: ignore[attr-defined]
        assert IBKR_RIGHTS not in registre.usable_rights  # type: ignore[attr-defined]


def test_le_profil_reel_refuse_le_synthetique() -> None:
    """Sinon un semis de démonstration oublié figerait la population en SYNTHETIC."""
    for registre in registres(real_ibkr_profile(INSTRUMENTS)):
        assert "synthetic-dev" not in registre.allowed_sources  # type: ignore[attr-defined]
        assert "SYNTHETIC" not in registre.usable_rights  # type: ignore[attr-defined]


# -- les SIX registres portent la même déclaration -------------------------


def test_les_six_registres_declarent_exactement_ibkr() -> None:
    """Un seul registre oublié laisserait sa page bloquée en SYNTHETIC."""
    for registre in registres(real_ibkr_profile(INSTRUMENTS)):
        assert registre.allowed_sources == frozenset({IBKR_SOURCE})  # type: ignore[attr-defined]
        assert registre.usable_rights == frozenset({IBKR_RIGHTS})  # type: ignore[attr-defined]


def test_deux_identifiants_pour_deux_usages() -> None:
    """TOUTES les pages comparent un TICKER, jamais `instrument_id`.

    `analysis` compare `payload["ticker"]` et `options`
    `payload["underlying"]` a leur univers declare. Le `con_id` reste
    l'identite technique : il dedoublonne l'univers et voyage dans
    `instrument_id`, sans jamais atteindre l'ecran ni les URL.

    Cette assertion a dit le contraire, et la page Analyse est restee
    vide avec 251 barres reelles en base.
    """
    profil = real_ibkr_profile(INSTRUMENTS)
    # Affichage : symboles.
    assert profil.markets.all_tickers() == SYMBOLES
    # Identité : références de contrat.
    assert profil.analysis.instruments == SYMBOLES
    assert profil.opportunities.instruments == SYMBOLES
    assert profil.options.underlyings == SYMBOLES
    assert profil.calendar.watchlist == SYMBOLES
    # Le con_id ne doit atteindre AUCUNE de ces configs.
    for declare in (
        profil.analysis.instruments,
        profil.opportunities.instruments,
        profil.options.underlyings,
        profil.calendar.watchlist,
    ):
        assert not set(declare) & set(REFS), (
            "un identifiant de contrat a fuite dans un univers d'affichage"
        )


# -- aucune invention ------------------------------------------------------


def test_aucun_secteur_n_est_invente() -> None:
    """Vertex n'a AUCUNE source de classification sectorielle réelle."""
    profil = real_ibkr_profile(INSTRUMENTS)
    assert list(profil.markets.universe) == [REAL_SECTOR_CODE]
    assert REAL_SECTOR_CODE == UNCLASSIFIED_SECTOR_CODE
    assert "non déclaré" in profil.markets.sector_labels[REAL_SECTOR_CODE]


def test_le_secteur_est_partage_avec_le_producteur() -> None:
    """Deux constantes séparées dériveraient, et la page deviendrait vide."""
    assert REAL_SECTOR_CODE == UNCLASSIFIED_SECTOR_CODE


def test_ibkr_n_est_pas_promu_en_confiance() -> None:
    """Un niveau supérieur sans échelle déclarée serait une autorité inventée."""
    profil = real_ibkr_profile(INSTRUMENTS)
    assert profil.fusion.source_tiers[IBKR_SOURCE] == DEFAULT_SOURCE_TIER


def test_les_exigences_des_opportunites_sont_conservees() -> None:
    """La porte 7 doit rester OBSERVÉE, jamais satisfaite par déclaration."""
    assert real_ibkr_profile(INSTRUMENTS).opportunities.portfolio_risk_required is True


# -- bornes et refus -------------------------------------------------------


def test_un_univers_vide_est_refuse() -> None:
    with pytest.raises(ProfileError, match="univers vide"):
        real_ibkr_profile(())


def test_un_univers_demesure_est_refuse() -> None:
    trop = tuple(
        RealInstrument(ref=str(i), symbol=f"S{i}") for i in range(MAX_REAL_INSTRUMENTS + 1)
    )
    with pytest.raises(ProfileError, match="maximum"):
        real_ibkr_profile(trop)


def test_les_doublons_sont_dedoublonnes_en_gardant_l_ordre() -> None:
    profil = real_ibkr_profile((GOOG, AAPL, GOOG))
    assert profil.analysis.instruments == SYMBOLES
    assert profil.markets.all_tickers() == SYMBOLES


# -- lecture de l'univers --------------------------------------------------


def test_lecture_d_un_univers_valide(tmp_path: Path) -> None:
    lus = load_real_instruments(ecrire_univers(tmp_path, (42, "AAA"), (7, "BBB")))
    assert lus == (RealInstrument(ref="42", symbol="AAA"), RealInstrument(ref="7", symbol="BBB"))


def test_un_instrument_SANS_SYMBOLE_est_refuse(tmp_path: Path) -> None:
    """Sans symbole, son rejet serait invisible à l'écran — donc refus ici."""
    fichier = tmp_path / "univers.json"
    fichier.write_text(
        json.dumps({"instruments": [{"con_id": 42, "sec_type": "STK"}]}), encoding="utf-8"
    )
    with pytest.raises(ProfileError, match="symbol"):
        load_real_instruments(fichier)


def test_fichier_absent_est_refuse(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="illisible"):
        load_real_instruments(tmp_path / "absent.json")


def test_json_invalide_est_refuse(tmp_path: Path) -> None:
    fichier = tmp_path / "univers.json"
    fichier.write_text("{pas du json", encoding="utf-8")
    with pytest.raises(ProfileError, match="JSON invalide"):
        load_real_instruments(fichier)


def test_liste_vide_est_refusee(tmp_path: Path) -> None:
    fichier = tmp_path / "univers.json"
    fichier.write_text(json.dumps({"instruments": []}), encoding="utf-8")
    with pytest.raises(ProfileError, match="non vide"):
        load_real_instruments(fichier)


@pytest.mark.parametrize("mauvais", [0, -1, "42", 1.5, True, None])
def test_con_id_invalide_est_refuse(tmp_path: Path, mauvais: object) -> None:
    """Un symbole seul n'est jamais une identité — ici non plus."""
    fichier = tmp_path / "univers.json"
    fichier.write_text(
        json.dumps({"instruments": [{"con_id": mauvais, "symbol": "AAA"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ProfileError, match="con_id"):
        load_real_instruments(fichier)


@pytest.mark.parametrize("mauvais", ["208813720", 42, None, ("ref", "sym")])
def test_un_instrument_du_MAUVAIS_TYPE_est_refuse_clairement(mauvais: object) -> None:
    """Une AttributeError en profondeur ne dit pas quoi corriger.

    Ce garde est né d'un vrai échec : la signature est passée de `str` à
    `RealInstrument`, un appelant est resté sur l'ancienne forme, et l'erreur
    obtenue était `'str' object has no attribute 'ref'` — exacte, mais muette
    sur le remède.
    """
    with pytest.raises(ProfileError, match="RealInstrument attendu"):
        real_ibkr_profile((mauvais,))  # type: ignore[arg-type]
