"""Barre quotidienne IBKR → cotation : ce qui passe, et surtout ce qui ne passe pas.

CE QUE CES TESTS EMPÊCHENT. Qu'une donnée IBKR arrive à l'écran en se faisant
passer pour ce qu'elle n'est pas. Un carnet haut instantané n'est pas une
clôture ; une barre horaire n'a pas de clôture de séance ; un `MIDPOINT` n'est
pas un cours de transaction. Chaque refus ci-dessous correspond à une manière
précise dont l'écran pourrait mentir.

Le dernier test est le plus important à long terme : il compare le contrat
produit ici à celui du générateur synthétique. Deux producteurs de cotations
existent désormais ; sans cet invariant, ils dériveraient en silence et la
page Marchés deviendrait vide sans message d'erreur.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vertex_core.contracts.market_quote import (
    DAILY_QUOTE_REQUIRED_FIELDS,
    DAILY_QUOTE_TYPE,
    UNCLASSIFIED_SECTOR_CODE,
)
from vertex_edge_ibkr.normalize import (
    IBKR_TRADES_ADJUSTMENT_BASIS,
    REASON_BAR_SIZE_NOT_DAILY,
    REASON_SYMBOL_MISSING,
    REASON_WHAT_TO_SHOW_NOT_TRADES,
    daily_quotes_from_bars,
)
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec

SPEC = ContractSpec(
    sec_type="STK", con_id=208813720, symbol="GOOG", exchange="SMART", currency="USD"
)


def barre(jour: int, close: str | None) -> BarObservation:
    return BarObservation(
        time=datetime(2026, 8, jour, 20, 0, 0, tzinfo=UTC),
        close=Decimal(close) if close is not None else None,
    )


def charge(
    *barres: BarObservation, bar_size: str = "1 day", what_to_show: str = "TRADES"
) -> BarsPayload:
    return BarsPayload(
        con_id=SPEC.con_id,
        bar_size=bar_size,
        what_to_show=what_to_show,
        use_rth=True,
        bars=barres,
    )


# -- chemin nominal --------------------------------------------------------


def test_une_barre_quotidienne_devient_une_cotation() -> None:
    resultat = daily_quotes_from_bars(
        charge(barre(28, "201.25")), SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    )
    assert resultat.refused_reason is None
    assert resultat.produced == 1
    (cotation,) = resultat.payloads
    assert cotation["type"] == DAILY_QUOTE_TYPE
    assert cotation["ticker"] == "GOOG"
    assert cotation["sector"] == UNCLASSIFIED_SECTOR_CODE
    assert cotation["trading_day"] == "2026-08-28"
    assert cotation["close"] == "201.25"
    assert cotation["currency"] == "USD"
    assert cotation["adjustment_basis"] == IBKR_TRADES_ADJUSTMENT_BASIS


def test_plusieurs_barres_donnent_plusieurs_cotations() -> None:
    resultat = daily_quotes_from_bars(
        charge(barre(26, "199.00"), barre(27, "200.50"), barre(28, "201.25")),
        SPEC,
        sector=UNCLASSIFIED_SECTOR_CODE,
    )
    assert [c["trading_day"] for c in resultat.payloads] == [
        "2026-08-26",
        "2026-08-27",
        "2026-08-28",
    ]


def test_le_centime_survit_au_trajet() -> None:
    """Un float perdrait l'exactitude ; la clôture voyage en texte décimal."""
    resultat = daily_quotes_from_bars(
        charge(barre(28, "0.0001")), SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    )
    assert resultat.payloads[0]["close"] == "0.0001"


def test_sans_devise_le_champ_est_absent_et_non_invente() -> None:
    sans_devise = ContractSpec(
        sec_type="STK", con_id=1, symbol="AAA", exchange="SMART", currency=None
    )
    resultat = daily_quotes_from_bars(
        charge(barre(28, "10")), sans_devise, sector=UNCLASSIFIED_SECTOR_CODE
    )
    assert "currency" not in resultat.payloads[0]


# -- les quatre refus ------------------------------------------------------


@pytest.mark.parametrize("taille", ["1 hour", "5 mins", "1 week", "1 min"])
def test_une_barre_non_quotidienne_est_refusee(taille: str) -> None:
    """Une barre horaire n'a pas de clôture de séance."""
    resultat = daily_quotes_from_bars(
        charge(barre(28, "201.25"), bar_size=taille),
        SPEC,
        sector=UNCLASSIFIED_SECTOR_CODE,
    )
    assert resultat.refused_reason == REASON_BAR_SIZE_NOT_DAILY
    assert resultat.produced == 0


@pytest.mark.parametrize("nature", ["MIDPOINT", "BID_ASK", "BID", "ASK"])
def test_un_prix_de_carnet_n_est_pas_un_cours_de_transaction(nature: str) -> None:
    resultat = daily_quotes_from_bars(
        charge(barre(28, "201.25"), what_to_show=nature),
        SPEC,
        sector=UNCLASSIFIED_SECTOR_CODE,
    )
    assert resultat.refused_reason == REASON_WHAT_TO_SHOW_NOT_TRADES
    assert resultat.produced == 0


def test_un_instrument_sans_symbole_est_refuse() -> None:
    """Sans symbole la cotation n'appartiendrait à aucun univers déclaré."""
    anonyme = ContractSpec(sec_type="STK", con_id=42, exchange="SMART", currency="USD")
    resultat = daily_quotes_from_bars(
        charge(barre(28, "10")), anonyme, sector=UNCLASSIFIED_SECTOR_CODE
    )
    assert resultat.refused_reason == REASON_SYMBOL_MISSING
    assert resultat.produced == 0


def test_une_cloture_absente_est_ecartee_et_COMPTEE() -> None:
    """Jamais changée en zéro, jamais perdue en silence."""
    resultat = daily_quotes_from_bars(
        charge(barre(27, "200.00"), barre(28, None)),
        SPEC,
        sector=UNCLASSIFIED_SECTOR_CODE,
    )
    assert resultat.produced == 1
    assert resultat.skipped_bars == 1
    assert resultat.refused_reason is None


@pytest.mark.parametrize("mauvaise", ["0", "-1", "-0.01"])
def test_une_cloture_nulle_ou_negative_est_ecartee(mauvaise: str) -> None:
    resultat = daily_quotes_from_bars(
        charge(barre(28, mauvaise)), SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    )
    assert resultat.produced == 0
    assert resultat.skipped_bars == 1


def test_aucune_barre_ne_produit_rien_sans_refus() -> None:
    """Zéro barre n'est pas une anomalie : c'est un instrument sans historique."""
    resultat = daily_quotes_from_bars(charge(), SPEC, sector=UNCLASSIFIED_SECTOR_CODE)
    assert resultat.produced == 0
    assert resultat.skipped_bars == 0
    assert resultat.refused_reason is None


# -- l'invariant anti-dérive ----------------------------------------------


def test_le_contrat_produit_couvre_tous_les_champs_requis() -> None:
    resultat = daily_quotes_from_bars(
        charge(barre(28, "201.25")), SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    )
    cotation = resultat.payloads[0]
    manquants = [champ for champ in DAILY_QUOTE_REQUIRED_FIELDS if champ not in cotation]
    assert not manquants, f"champs requis absents : {manquants}"


def test_meme_contrat_que_le_producteur_SYNTHETIQUE() -> None:
    """Deux producteurs de cotations existent : ils ne doivent pas diverger.

    Sans cet invariant, une dérive rendrait la page Marchés vide pour une des
    deux sources, sans aucun message d'erreur — le pire mode de panne.
    """
    from vertex_core.synthetic.market import _quote_payload

    synthetique = _quote_payload(
        ticker="SYN-TECH-01", sector="TECH", trading_day="2026-08-28", close_cents=20125
    )
    reelle = daily_quotes_from_bars(
        charge(barre(28, "201.25")), SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    ).payloads[0]

    for champ in DAILY_QUOTE_REQUIRED_FIELDS:
        assert champ in synthetique, f"le producteur synthétique a perdu {champ}"
        assert champ in reelle, f"le producteur réel a perdu {champ}"
    # Et la nature déclarée est la même des deux côtés.
    assert synthetique["type"] == reelle["type"] == DAILY_QUOTE_TYPE
