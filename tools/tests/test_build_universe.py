"""Scanner observé → fichier d'univers : ce qui passe et ce qui est refusé.

CE QUE CES TESTS EMPÊCHENT. Qu'un univers de mille titres se fabrique avec des
identités approximatives. `universe.py` refuse toute résolution réseau, donc
tout ce qui entre dans le fichier doit déjà être exact : un `con_id` inventé
ferait collecter une année d'historique sur le mauvais contrat, sans que rien
ne le signale.

Le test le plus important est `test_un_perimetre_inconnu_est_refuse`. La devise
n'est PAS dans la ligne de scanner : la déduire d'un périmètre non déclaré
écrirait USD sur des titres européens, et tout l'historique serait faux.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_universe import instruments_depuis_scanners, main


def charge(*lignes: dict[str, object], location_code: str = "STK.US.MAJOR") -> dict[str, object]:
    return {
        "scan_code": "MOST_ACTIVE",
        "instrument": "STK",
        "location_code": location_code,
        "rows": list(lignes),
    }


def test_une_ligne_complete_devient_un_instrument_exact() -> None:
    instruments, compteurs, refus = instruments_depuis_scanners(
        [charge({"rank": 0, "con_id": 208813720, "symbol": "GOOG"})]
    )
    assert refus == []
    assert instruments == [
        {
            "con_id": 208813720,
            "sec_type": "STK",
            "symbol": "GOOG",
            "exchange": "SMART",
            "currency": "USD",
        }
    ]
    assert compteurs["lignes"] == 1


def test_une_ligne_sans_con_id_est_ecartee_ET_comptee() -> None:
    """Un symbole seul n'est pas une identité : la sonde a mesuré 32 « GOOG »."""
    instruments, compteurs, _ = instruments_depuis_scanners(
        [charge({"rank": 0, "symbol": "GOOG"}, {"rank": 1, "con_id": 265598, "symbol": "AAPL"})]
    )
    assert [i["symbol"] for i in instruments] == ["AAPL"]
    assert compteurs["sans_con_id"] == 1


def test_une_ligne_sans_symbole_est_ecartee_ET_comptee() -> None:
    """Sans symbole, l'instrument entrerait en base pour rester invisible."""
    instruments, compteurs, _ = instruments_depuis_scanners(
        [charge({"rank": 0, "con_id": 111}, {"rank": 1, "con_id": 265598, "symbol": "AAPL"})]
    )
    assert [i["con_id"] for i in instruments] == [265598]
    assert compteurs["sans_symbole"] == 1


def test_le_meme_contrat_vu_par_deux_scans_n_est_compte_qu_une_fois() -> None:
    instruments, compteurs, _ = instruments_depuis_scanners(
        [
            charge({"rank": 0, "con_id": 208813720, "symbol": "GOOG"}),
            charge({"rank": 0, "con_id": 208813720, "symbol": "GOOG"}),
        ]
    )
    assert len(instruments) == 1
    assert compteurs["doublons"] == 1


def test_un_perimetre_inconnu_est_refuse_jamais_suppose() -> None:
    """Écrire USD sur un scan européen fausserait tout l'historique."""
    instruments, _, refus = instruments_depuis_scanners(
        [charge({"rank": 0, "con_id": 42, "symbol": "AIR"}, location_code="STK.EU")]
    )
    assert instruments == []
    assert refus and "STK.EU" in refus[0]


def test_un_con_id_booleen_est_refuse() -> None:
    """`True` est un `int` en Python : sans garde, il deviendrait con_id=1."""
    instruments, compteurs, _ = instruments_depuis_scanners(
        [charge({"rank": 0, "con_id": True, "symbol": "X"})]
    )
    assert instruments == []
    assert compteurs["sans_con_id"] == 1


def test_le_fichier_ecrit_est_relu_par_le_chargeur_REEL(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un univers que l'ingestion refuserait ne doit jamais atteindre le disque."""
    import build_universe

    monkeypatch.setattr(
        build_universe,
        "_charger_scanners",
        lambda dsn, limite: [charge({"rank": 0, "con_id": 208813720, "symbol": "GOOG"})],
    )
    monkeypatch.setenv(
        "VERTEX_DATABASE_URL", "postgresql+psycopg://vertex:x@127.0.0.1:5432/vertex_live"
    )
    destination = tmp_path / "univers.json"
    assert main(["--out", str(destination)]) == 0

    document = json.loads(destination.read_text(encoding="utf-8"))
    from vertex_edge_ibkr.universe import parse_universe

    contrats = parse_universe(document, max_size=5000)
    assert len(contrats) == 1
    assert contrats[0].con_id == 208813720
    assert contrats[0].symbol == "GOOG"
    assert contrats[0].currency == "USD"


def test_ecraser_un_univers_existant_exige_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un univers écrasé par accident fait perdre le lien avec l'historique."""
    import build_universe

    monkeypatch.setattr(
        build_universe,
        "_charger_scanners",
        lambda dsn, limite: [charge({"rank": 0, "con_id": 1, "symbol": "A"})],
    )
    monkeypatch.setenv(
        "VERTEX_DATABASE_URL", "postgresql+psycopg://vertex:x@127.0.0.1:5432/vertex_live"
    )
    destination = tmp_path / "univers.json"
    destination.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as capture:
        main(["--out", str(destination)])
    assert capture.value.code == 2
    assert destination.read_text(encoding="utf-8") == "{}", "le fichier a été touché"

    assert main(["--out", str(destination), "--force"]) == 0


def test_sans_scanner_en_base_le_refus_dit_quoi_faire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import build_universe

    monkeypatch.setattr(build_universe, "_charger_scanners", lambda dsn, limite: [])
    monkeypatch.setenv(
        "VERTEX_DATABASE_URL", "postgresql+psycopg://vertex:x@127.0.0.1:5432/vertex_live"
    )
    with pytest.raises(SystemExit) as capture:
        main(["--out", str(tmp_path / "u.json")])
    assert capture.value.code == 2


# --------------------------------------------------------------------------
# --merge : un univers reconstruit n'efface pas ce qui était déclaré
# --------------------------------------------------------------------------


def _univers(tmp_path: Path, *entrees: dict[str, object]) -> Path:
    fichier = tmp_path / "declare.json"
    fichier.write_text(json.dumps({"instruments": list(entrees)}), encoding="utf-8")
    return fichier


def test_un_instrument_declare_survit_a_la_reconstruction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le défaut mesuré : GOOG déclaré à la main a disparu, et ses 251
    cotations sont devenues `ticker_not_in_universe` du jour au lendemain."""
    import build_universe

    declare = _univers(
        tmp_path,
        {
            "con_id": 208813720,
            "sec_type": "STK",
            "symbol": "GOOG",
            "exchange": "SMART",
            "currency": "USD",
        },
    )
    monkeypatch.setattr(
        build_universe,
        "_charger_scanners",
        lambda dsn, limite: [charge({"rank": 0, "con_id": 111, "symbol": "AAA"})],
    )
    monkeypatch.setenv(
        "VERTEX_DATABASE_URL", "postgresql+psycopg://vertex:x@127.0.0.1:5432/vertex_live"
    )
    sortie = tmp_path / "univers-large.json"
    assert main(["--out", str(sortie), "--merge", str(declare)]) == 0

    document = json.loads(sortie.read_text(encoding="utf-8"))
    symboles = [i["symbol"] for i in document["instruments"]]
    assert "GOOG" in symboles, "l'instrument déclaré a été effacé"
    assert "AAA" in symboles, "la découverte a été perdue"
    # Le déclaré passe EN TÊTE : il fait autorité.
    assert symboles[0] == "GOOG"


def test_le_declare_gagne_sur_le_meme_con_id_venu_du_scanner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import build_universe

    declare = _univers(
        tmp_path,
        {
            "con_id": 111,
            "sec_type": "STK",
            "symbol": "DECLARE",
            "exchange": "SMART",
            "currency": "USD",
        },
    )
    monkeypatch.setattr(
        build_universe,
        "_charger_scanners",
        lambda dsn, limite: [charge({"rank": 0, "con_id": 111, "symbol": "SCANNER"})],
    )
    monkeypatch.setenv(
        "VERTEX_DATABASE_URL", "postgresql+psycopg://vertex:x@127.0.0.1:5432/vertex_live"
    )
    sortie = tmp_path / "u.json"
    assert main(["--out", str(sortie), "--merge", str(declare)]) == 0
    document = json.loads(sortie.read_text(encoding="utf-8"))
    assert len(document["instruments"]) == 1
    assert document["instruments"][0]["symbol"] == "DECLARE"


def test_un_fichier_merge_absent_est_un_REFUS(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le silence ferait perdre des instruments sans que personne le sache."""
    import build_universe

    monkeypatch.setattr(
        build_universe,
        "_charger_scanners",
        lambda dsn, limite: [charge({"rank": 0, "con_id": 111, "symbol": "AAA"})],
    )
    monkeypatch.setenv(
        "VERTEX_DATABASE_URL", "postgresql+psycopg://vertex:x@127.0.0.1:5432/vertex_live"
    )
    with pytest.raises(SystemExit) as capture:
        main(
            [
                "--out",
                str(tmp_path / "u.json"),
                "--merge",
                str(tmp_path / "absent.json"),
            ]
        )
    assert capture.value.code == 2


def test_un_symbole_avec_espace_est_refuse_ET_compte() -> None:
    """Defaut mesure :  (privilegiee IBKR) faisait refuser par lAPI
    le dossier Opportunites ENTIER — une ligne sur 153 cassait la page."""
    instruments, compteurs, _ = instruments_depuis_scanners(
        [
            charge(
                {"rank": 0, "con_id": 42, "symbol": "GNL PRE"},
                {"rank": 1, "con_id": 265598, "symbol": "AAPL"},
            )
        ]
    )
    assert [i["symbol"] for i in instruments] == ["AAPL"]
    assert compteurs["symbole_hors_forme"] == 1


def test_les_formes_admises_par_lAPI_passent() -> None:
    """Points et tirets sont admis par la forme des codes techniques."""
    instruments, compteurs, _ = instruments_depuis_scanners(
        [
            charge(
                {"rank": 0, "con_id": 1, "symbol": "BRK.B"},
                {"rank": 1, "con_id": 2, "symbol": "RDS-A"},
            )
        ]
    )
    assert [i["symbol"] for i in instruments] == ["BRK.B", "RDS-A"]
    assert compteurs["symbole_hors_forme"] == 0
