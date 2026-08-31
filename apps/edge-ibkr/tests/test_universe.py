"""Univers d'abonnement : toute ambiguïté ARRÊTE l'ingestion.

La règle du dépôt est « Si l'identité ou la session est ambiguë, la sonde
s'arrête » (`docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md`). Ces tests
vérifient que l'ingestion CONTINUE applique la même règle, et qu'aucun défaut
de configuration ne se transforme en abonnement approximatif.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from vertex_edge_ibkr.universe import (
    MAX_HISTORICAL_UNIVERSE_SIZE,
    MAX_UNIVERSE_SIZE,
    UniverseError,
    load_universe,
    parse_universe,
)


def _doc(*instruments: dict[str, Any]) -> dict[str, Any]:
    return {"instruments": list(instruments)}


_ACTION = {"con_id": 265598, "sec_type": "STK", "symbol": "XYZ", "exchange": "SMART"}


def test_univers_valide_rend_des_contrats_exacts() -> None:
    specs = parse_universe(_doc(_ACTION))
    assert len(specs) == 1
    assert specs[0].con_id == 265598
    assert specs[0].sec_type == "STK"
    assert specs[0].symbol == "XYZ"
    assert specs[0].exchange == "SMART"


def test_con_id_absent_est_refuse() -> None:
    """Un symbole seul n'est JAMAIS une identité."""
    with pytest.raises(UniverseError, match="con_id"):
        parse_universe(_doc({"sec_type": "STK", "symbol": "XYZ"}))


@pytest.mark.parametrize("mauvais", [0, -1, "265598", 1.5, True, None])
def test_con_id_non_entier_positif_est_refuse(mauvais: Any) -> None:
    with pytest.raises(UniverseError, match="con_id"):
        parse_universe(_doc({"con_id": mauvais, "sec_type": "STK"}))


def test_con_id_duplique_est_refuse() -> None:
    """Deux entrées pour le même contrat rendraient la provenance ambiguë."""
    with pytest.raises(UniverseError, match="dupliqu"):
        parse_universe(_doc(_ACTION, dict(_ACTION)))


def test_cle_inconnue_est_refusee() -> None:
    """Une faute de frappe sur `trading_class` fabriquerait un AUTRE contrat."""
    with pytest.raises(UniverseError, match="inconnues"):
        parse_universe(_doc({**_ACTION, "tradingclass": "XYZ"}))


def test_sec_type_absent_est_refuse() -> None:
    with pytest.raises(UniverseError, match="sec_type"):
        parse_universe(_doc({"con_id": 1}))


def test_liste_vide_est_refusee() -> None:
    """Un univers vide n'est pas neutre : c'est une configuration incomplète."""
    with pytest.raises(UniverseError, match="non vide"):
        parse_universe({"instruments": []})


def test_racine_non_objet_est_refusee() -> None:
    with pytest.raises(UniverseError, match="objet JSON"):
        parse_universe([_ACTION])


def test_au_dela_de_la_borne_est_refuse() -> None:
    """Le budget de messages IBKR est borné AVANT même la connexion."""
    trop = [{"con_id": 1000 + i, "sec_type": "STK"} for i in range(MAX_UNIVERSE_SIZE + 1)]
    with pytest.raises(UniverseError, match="maximum"):
        parse_universe({"instruments": trop})


def test_la_borne_exacte_passe() -> None:
    pile = [{"con_id": 1000 + i, "sec_type": "STK"} for i in range(MAX_UNIVERSE_SIZE)]
    assert len(parse_universe({"instruments": pile})) == MAX_UNIVERSE_SIZE


def test_strike_en_flottant_est_refuse() -> None:
    """Un strike en `float` perdrait l'exactitude décimale du contrat."""
    with pytest.raises(UniverseError, match="flottant"):
        parse_universe(_doc({"con_id": 1, "sec_type": "OPT", "strike": 187.5}))


def test_strike_en_chaine_devient_un_decimal_exact() -> None:
    specs = parse_universe(
        _doc({"con_id": 1, "sec_type": "OPT", "strike": "187.5", "right": "C"})
    )
    assert specs[0].strike == Decimal("187.5")
    assert specs[0].right == "C"


def test_right_invalide_est_refuse() -> None:
    """`ContractSpec` n'accepte que C ou P ; le refus doit remonter clairement."""
    with pytest.raises(UniverseError):
        parse_universe(_doc({"con_id": 1, "sec_type": "OPT", "right": "X"}))


def test_max_size_au_dela_du_plafond_ABSOLU_est_refuse() -> None:
    with pytest.raises(UniverseError, match="max_size"):
        parse_universe(_doc(_ACTION), max_size=MAX_HISTORICAL_UNIVERSE_SIZE + 1)


def test_le_plafond_historique_depasse_celui_du_temps_reel() -> None:
    """Deux régimes, deux contraintes : les lignes de données d'un côté, le temps de l'autre."""
    assert MAX_HISTORICAL_UNIVERSE_SIZE > MAX_UNIVERSE_SIZE
    # Un univers de 500 titres est légitime pour l'historique...
    gros = [{"con_id": 3000 + i, "sec_type": "STK"} for i in range(500)]
    assert len(parse_universe({"instruments": gros}, max_size=1000)) == 500
    # ...et refusé pour le temps réel.
    with pytest.raises(UniverseError, match="maximum"):
        parse_universe({"instruments": gros}, max_size=MAX_UNIVERSE_SIZE)


def test_fichier_absent_est_refuse(tmp_path: Path) -> None:
    with pytest.raises(UniverseError, match="illisible"):
        load_universe(tmp_path / "inexistant.json")


def test_json_invalide_est_refuse(tmp_path: Path) -> None:
    fichier = tmp_path / "univers.json"
    fichier.write_text("{ ceci n'est pas du JSON", encoding="utf-8")
    with pytest.raises(UniverseError, match="JSON invalide"):
        load_universe(fichier)


def test_chargement_depuis_un_fichier_reel(tmp_path: Path) -> None:
    fichier = tmp_path / "univers.json"
    fichier.write_text(json.dumps(_doc(_ACTION)), encoding="utf-8")
    specs = load_universe(fichier)
    assert specs[0].con_id == 265598
