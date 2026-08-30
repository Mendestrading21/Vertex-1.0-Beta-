"""Preuve d'exécution de la porte `tools/check_traceability.py`.

Une matrice de traçabilité est le genre de document qui se dégrade sans bruit :
une règle est reformulée, une preuve est déplacée, une entrée reste là et
continue d'annoncer une couverture qui n'existe plus. Ces tests prouvent par
injection que chacune de ces dégradations est détectée.

Le contrôle symétrique est prouvé aussi : une matrice complète et exacte doit
passer, sinon le verdict de la porte ne veut rien dire.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE = _REPO_ROOT / "tools" / "check_traceability.py"


def _load_gate() -> Any:
    spec = importlib.util.spec_from_file_location("check_traceability_gate", _GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()

TODAY = dt.date(2026, 8, 30)

REGLE_A = "Ne jamais faire la chose interdite numéro un."
REGLE_B = "Ne jamais faire la chose interdite numéro deux."


def _depot(
    tmp_path: Path,
    invariants: list[dict[str, Any]],
    *,
    regles: tuple[str, ...] = (REGLE_A, REGLE_B),
    avec_test: bool = True,
) -> Path:
    """Construit un dépôt minimal : deux sources de règles et une matrice."""
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(
        "# Titre\n\n## Interdictions absolues\n\n" + "".join(f"- {r}\n" for r in regles),
        encoding="utf-8",
    )
    safety = tmp_path / ".claude" / "rules" / "financial-safety.md"
    safety.parent.mkdir(parents=True, exist_ok=True)
    safety.write_text("# Sécurité\n\n- Une règle de sécurité.\n", encoding="utf-8")

    if avec_test:
        preuve = tmp_path / "tests" / "test_preuve.py"
        preuve.parent.mkdir(parents=True, exist_ok=True)
        preuve.write_text("def test_la_regle_est_prouvee() -> None:\n    assert True\n", "utf-8")

    manifest = tmp_path / "manifests" / "traceability.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        yaml.safe_dump({"schema_version": 1, "invariants": invariants}, sort_keys=False),
        encoding="utf-8",
    )
    return tmp_path


def _entree_prouvee(texte: str, ident: str, proofs: list[str]) -> dict[str, Any]:
    return {
        "id": ident,
        "digest": gate.digest(texte),
        "text": texte,
        "status": "PROVEN",
        "proofs": proofs,
    }


def _matrice_complete(tmp_path: Path) -> Path:
    return _depot(
        tmp_path,
        [
            _entree_prouvee(REGLE_A, "A", ["tests/test_preuve.py::test_la_regle_est_prouvee"]),
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )


def _codes(root: Path) -> set[str]:
    return {f["code"] for f in gate.check(root, TODAY)["findings"]}


# ── contrôle symétrique ──────────────────────────────────────────────────────


def test_une_matrice_complete_et_exacte_passe(tmp_path: Path) -> None:
    resultat = gate.check(_matrice_complete(tmp_path), TODAY)
    assert resultat["ok"], resultat["findings"]
    assert resultat["proven"] == 3


# ── couverture dans les deux sens ────────────────────────────────────────────


def test_une_interdiction_non_declaree_echoue(tmp_path: Path) -> None:
    root = _depot(
        tmp_path,
        [_entree_prouvee(REGLE_A, "A", ["tests/test_preuve.py"])],
    )
    assert "invariant_not_declared" in _codes(root)


def test_une_entree_sans_interdiction_correspondante_echoue(tmp_path: Path) -> None:
    """Une matrice périmée annonce une couverture qui n'existe plus."""
    root = _depot(
        tmp_path,
        [
            _entree_prouvee(REGLE_A, "A", ["tests/test_preuve.py"]),
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle supprimée depuis.", "Z", ["tests/test_preuve.py"]),
        ],
    )
    assert "invariant_no_longer_exists" in _codes(root)


def test_une_regle_reformulee_fait_echouer_dans_les_deux_sens(tmp_path: Path) -> None:
    """Reformuler une règle doit forcer à relire la correspondance."""
    root = _depot(
        tmp_path,
        [
            _entree_prouvee(REGLE_A, "A", ["tests/test_preuve.py"]),
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
        regles=(REGLE_A + " Et une précision ajoutée.", REGLE_B),
    )
    codes = _codes(root)
    assert "invariant_not_declared" in codes
    assert "invariant_no_longer_exists" in codes


def test_un_bullet_replie_sur_plusieurs_lignes_reste_une_seule_regle(tmp_path: Path) -> None:
    """Sinon le condensé changerait à chaque reformatage du document."""
    claude = tmp_path / "CLAUDE.md"
    claude.parent.mkdir(parents=True, exist_ok=True)
    claude.write_text(
        "## Interdictions absolues\n\n- Une règle longue\n  qui continue sur une autre ligne.\n",
        encoding="utf-8",
    )
    regles = gate._paragraph_bullets(claude.read_text(encoding="utf-8"), "Interdictions absolues")
    assert regles == ["Une règle longue qui continue sur une autre ligne."]


# ── qualité des preuves ──────────────────────────────────────────────────────


def test_une_entree_prouvee_sans_preuve_echoue(tmp_path: Path) -> None:
    root = _depot(
        tmp_path,
        [
            _entree_prouvee(REGLE_A, "A", []),
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    assert "proof_missing" in _codes(root)


def test_un_fichier_de_preuve_inexistant_echoue(tmp_path: Path) -> None:
    root = _depot(
        tmp_path,
        [
            _entree_prouvee(REGLE_A, "A", ["tests/test_absent.py"]),
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    assert "proof_file_absent" in _codes(root)


def test_un_nom_de_test_inexistant_echoue(tmp_path: Path) -> None:
    """Une citation qui ne résout pas ressemble à une couverture."""
    root = _depot(
        tmp_path,
        [
            _entree_prouvee(REGLE_A, "A", ["tests/test_preuve.py::test_qui_n_existe_pas"]),
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    assert "proof_test_absent" in _codes(root)


def test_un_test_playwright_est_reconnu_par_son_titre(tmp_path: Path) -> None:
    root = _matrice_complete(tmp_path)
    spec = root / "e2e" / "parcours.spec.ts"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("test('la page refuse une valeur absente', async () => {});\n", "utf-8")
    assert gate._proof_resolves(root, "e2e/parcours.spec.ts::refuse une valeur absente") is None
    assert (
        gate._proof_resolves(root, "e2e/parcours.spec.ts::un titre absent") == "proof_test_absent"
    )


# ── écarts déclarés ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("champ", ["owner", "reason", "expires_at", "closure_criterion"])
def test_un_ecart_sans_exception_complete_echoue(tmp_path: Path, champ: str) -> None:
    entree = {
        "id": "A",
        "digest": gate.digest(REGLE_A),
        "status": "NOT_YET_PROVEN",
        "owner": "équipe",
        "reason": "motif écrit",
        "expires_at": "2026-12-31",
        "closure_criterion": "critère écrit",
    }
    del entree[champ]
    root = _depot(
        tmp_path,
        [
            entree,
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    assert "gap_without_exception" in _codes(root)


def test_un_ecart_perime_echoue(tmp_path: Path) -> None:
    root = _depot(
        tmp_path,
        [
            {
                "id": "A",
                "digest": gate.digest(REGLE_A),
                "status": "NOT_YET_PROVEN",
                "owner": "équipe",
                "reason": "motif écrit",
                "expires_at": "2026-08-29",
                "closure_criterion": "critère écrit",
            },
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    assert "expired_exception" in _codes(root)


def test_une_regle_declaree_intestable_sans_argument_echoue(tmp_path: Path) -> None:
    """Déclarer une règle intestable doit coûter un argument écrit."""
    root = _depot(
        tmp_path,
        [
            {"id": "A", "digest": gate.digest(REGLE_A), "status": "NOT_PROVABLE_BY_TEST"},
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    assert "unprovable_without_argument" in _codes(root)


def test_un_ecart_valide_passe_mais_reste_visible(tmp_path: Path) -> None:
    root = _depot(
        tmp_path,
        [
            {
                "id": "A",
                "digest": gate.digest(REGLE_A),
                "status": "NOT_YET_PROVEN",
                "owner": "équipe",
                "reason": "motif écrit",
                "expires_at": "2026-12-31",
                "closure_criterion": "critère écrit",
            },
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    resultat = gate.check(root, TODAY)
    assert resultat["ok"]
    # Un manque qui cesse d'être visible cesse d'être un manque.
    assert [g["id"] for g in resultat["gaps"]] == ["A"]


def test_un_statut_invente_est_refuse(tmp_path: Path) -> None:
    root = _depot(
        tmp_path,
        [
            {"id": "A", "digest": gate.digest(REGLE_A), "status": "PLUS_TARD"},
            _entree_prouvee(REGLE_B, "B", ["tests/test_preuve.py"]),
            _entree_prouvee("Une règle de sécurité.", "S", ["tests/test_preuve.py"]),
        ],
    )
    assert "unknown_status" in _codes(root)


# ── documents inutilisables ──────────────────────────────────────────────────


def test_une_matrice_vide_est_refusee(tmp_path: Path) -> None:
    root = _depot(tmp_path, [])
    with pytest.raises(gate.DocumentError):
        gate.check(root, TODAY)


def test_une_source_sans_interdiction_est_refusee(tmp_path: Path) -> None:
    """Vider la section des interdictions est l'autre façon de vider la porte."""
    root = _matrice_complete(tmp_path)
    (root / "CLAUDE.md").write_text("# Titre\n\n## Interdictions absolues\n\n", encoding="utf-8")
    with pytest.raises(gate.DocumentError):
        gate.check(root, TODAY)


# ── le dépôt réel ────────────────────────────────────────────────────────────


def test_la_matrice_reelle_du_depot_est_verte() -> None:
    """Anti-vacuité : la matrice réelle couvre bien des interdictions réelles."""
    resultat = gate.check(_REPO_ROOT, dt.datetime.now(dt.UTC).date())
    assert resultat["ok"], resultat["findings"]
    assert resultat["prohibitions_found"] >= 30
    assert resultat["proven"] >= 20
