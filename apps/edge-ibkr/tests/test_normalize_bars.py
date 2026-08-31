"""Barre quotidienne IBKR → enregistrement de barres : la page Analyse.

CE QUE CES TESTS EMPÊCHENT. Que la page Analyse reste vide alors que la donnée
est en base — le défaut réellement mesuré le 2026-08-31 : 251 barres IBKR
ingérées, zéro lue, parce que le schéma produit n'était déclaré nulle part côté
consommateur. Une page vide sans message est le pire des échecs : elle
ressemble à « pas de données » alors qu'elle signifie « données ignorées ».

Le test le plus important est `test_le_consommateur_REEL_accepte`. Il ne
vérifie pas une forme que j'aurais inventée : il fait relire la charge utile
produite par le validateur RÉEL de `vertex_worker.analysis`. Producteur et
consommateur vivent dans deux paquets qui ne se connaissent pas ; sans cet
appariement, ils dérivent en silence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vertex_core.contracts.market_quote import (
    DAILY_BARS_REQUIRED_FIELDS,
    DAILY_BARS_TYPE,
)
from vertex_edge_ibkr.normalize import (
    IBKR_TRADES_ADJUSTMENT_BASIS,
    REASON_BAR_SIZE_NOT_DAILY,
    REASON_CURRENCY_MISSING,
    REASON_NO_USABLE_BAR,
    REASON_SYMBOL_MISSING,
    REASON_WHAT_TO_SHOW_NOT_TRADES,
    daily_bars_event_id,
    daily_bars_payload_from_bars,
)
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec

SPEC = ContractSpec(
    sec_type="STK", con_id=208813720, symbol="GOOG", exchange="SMART", currency="USD"
)

#: Valeurs RÉELLES relevées sur le contrat GOOG le 2026-08-31.
BARRE_REELLE = BarObservation(
    time=datetime(2025, 8, 29, tzinfo=UTC),
    open=Decimal("211.27"),
    high=Decimal("215.34"),
    low=Decimal("210.97"),
    close=Decimal("213.53"),
    volume=Decimal("11006698.0"),
    average=Decimal("213.229"),
    bar_count=62967,
)


def barres(*observations: BarObservation, **surcharges: object) -> BarsPayload:
    parametres: dict[str, object] = {
        "con_id": 208813720,
        "bar_size": "1 day",
        "what_to_show": "TRADES",
        "use_rth": True,
        "bars": observations or (BARRE_REELLE,),
    }
    parametres.update(surcharges)
    return BarsPayload(**parametres)  # type: ignore[arg-type]


def test_le_consommateur_REEL_accepte_ce_que_l_edge_produit() -> None:
    """L'appariement producteur/consommateur, mesuré et non supposé."""
    from vertex_worker.analysis import (
        _basis_code_or_none,
        _currency_or_none,
        _validate_bar,
    )

    resultat = daily_bars_payload_from_bars(barres(), SPEC)
    assert resultat.refused_reason is None
    charge = resultat.payload
    assert charge is not None

    for champ in DAILY_BARS_REQUIRED_FIELDS:
        assert champ in charge, f"champ {champ!r} absent de la charge produite"
    assert charge["type"] == DAILY_BARS_TYPE
    assert _currency_or_none(charge["currency"]) is not None
    assert _basis_code_or_none(charge["adjustment_basis"]) is not None

    barre, raison = _validate_bar(charge["bars"][0])
    assert barre is not None, f"le consommateur refuse la barre produite : {raison}"
    assert barre["close"] == "213.53", "le centime n'a pas survécu au trajet"
    assert barre["volume"] == 11006698, "le volume doit être un entier exact"


def test_la_base_d_ajustement_avoue_que_TRADES_n_est_pas_ajuste() -> None:
    resultat = daily_bars_payload_from_bars(barres(), SPEC)
    assert resultat.payload is not None
    assert resultat.payload["adjustment_basis"] == IBKR_TRADES_ADJUSTMENT_BASIS
    assert "unadjusted" in IBKR_TRADES_ADJUSTMENT_BASIS


@pytest.mark.parametrize(
    ("surcharges", "attendu"),
    [
        ({"bar_size": "1 hour"}, REASON_BAR_SIZE_NOT_DAILY),
        ({"what_to_show": "MIDPOINT"}, REASON_WHAT_TO_SHOW_NOT_TRADES),
    ],
)
def test_refus_de_structure(surcharges: dict[str, object], attendu: str) -> None:
    """Une bougie de 60 minutes n'est pas une séance ; un MIDPOINT n'est pas
    un cours de transaction. Les deux doivent être refusés en le disant."""
    resultat = daily_bars_payload_from_bars(barres(**surcharges), SPEC)
    assert resultat.refused_reason == attendu
    assert resultat.payload is None


def test_sans_symbole_l_instrument_entier_est_refuse() -> None:
    spec = ContractSpec(sec_type="STK", con_id=208813720, exchange="SMART", currency="USD")
    resultat = daily_bars_payload_from_bars(barres(), spec)
    assert resultat.refused_reason == REASON_SYMBOL_MISSING


def test_sans_devise_l_enregistrement_est_refuse_AVANT_la_base() -> None:
    """Le consommateur rejette l'enregistrement entier sans devise. Refuser
    ici nomme la cause ; laisser passer produirait une page vide muette."""
    spec = ContractSpec(sec_type="STK", con_id=208813720, symbol="GOOG", exchange="SMART")
    resultat = daily_bars_payload_from_bars(barres(), spec)
    assert resultat.refused_reason == REASON_CURRENCY_MISSING


def test_une_barre_partielle_est_ecartee_ET_comptee() -> None:
    """L'OHLC est un tout : une barre sans haut n'est pas réparable."""
    partielle = BarObservation(
        time=datetime(2025, 8, 28, tzinfo=UTC),
        open=Decimal("210"),
        high=None,
        low=Decimal("209"),
        close=Decimal("211"),
        volume=Decimal("1000"),
    )
    resultat = daily_bars_payload_from_bars(barres(partielle, BARRE_REELLE), SPEC)
    assert resultat.payload is not None
    assert resultat.produced == 1, "seule la barre complète doit passer"
    assert resultat.skipped_bars == 1, "l'écart doit être compté, jamais silencieux"


def test_un_volume_fractionnaire_est_ecarte_jamais_arrondi() -> None:
    fractionnaire = BarObservation(
        time=datetime(2025, 8, 28, tzinfo=UTC),
        open=Decimal("210"),
        high=Decimal("212"),
        low=Decimal("209"),
        close=Decimal("211"),
        volume=Decimal("1000.5"),
    )
    resultat = daily_bars_payload_from_bars(barres(fractionnaire), SPEC)
    assert resultat.refused_reason == REASON_NO_USABLE_BAR
    assert resultat.skipped_bars == 1


def test_aucune_barre_utilisable_refuse_au_lieu_de_publier_du_vide() -> None:
    vide = BarObservation(time=datetime(2025, 8, 28, tzinfo=UTC))
    resultat = daily_bars_payload_from_bars(barres(vide), SPEC)
    assert resultat.refused_reason == REASON_NO_USABLE_BAR
    assert resultat.payload is None


def test_l_identite_est_STABLE_donc_une_relance_ne_duplique_rien() -> None:
    """`ingest_envelope` est idempotent sur `event_id` : un identifiant tiré
    au hasard ferait doubler tout l'historique à chaque remplissage."""
    premier = daily_bars_event_id(208813720, "2025-08-29", "2026-08-28")
    second = daily_bars_event_id(208813720, "2025-08-29", "2026-08-28")
    assert premier == second
    assert premier == "ibkr:daily-bars:208813720:2025-08-29:2026-08-28"
    autre = daily_bars_event_id(208813720, "2025-08-29", "2026-08-27")
    assert autre != premier, "une fenêtre différente est un enregistrement différent"
