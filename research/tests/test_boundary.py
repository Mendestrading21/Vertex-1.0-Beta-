"""La recherche ne peut pas atteindre le runtime.

« Aucune donnée de recherche ou de notebook ne peut écrire dans le runtime
live » (`.claude/rules/architecture.md`). Une règle écrite dans un document
n'empêche rien ; ce test l'applique par exécution sur l'arbre des sources.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RESEARCH_ROOT = Path(__file__).resolve().parents[1]

# Modules dont un import depuis `research/` signifierait que la recherche peut
# déclencher un effet de production : persistance, API, worker, adaptateur
# IBKR, ingress. `vertex_core` n'y figure pas : c'est le domaine PUR, sans
# base ni réseau, et le réutiliser vaut mieux que réécrire une formule.
FORBIDDEN_ROOTS = frozenset(
    {
        "vertex_api",
        "vertex_persistence",
        "vertex_worker",
        "vertex_edge_ibkr",
        "vertex_ingress_tv",
        "alembic",
        "sqlalchemy",
        "psycopg",
        "fastapi",
        "ib_async",
    }
)


def python_sources() -> list[Path]:
    return sorted(
        path
        for path in RESEARCH_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


def test_l_arbre_de_recherche_n_est_pas_vide() -> None:
    """Anti-vacuité : un test de frontière sur zéro fichier ne prouve rien."""
    sources = python_sources()
    assert len(sources) >= 3, sources


@pytest.mark.parametrize("path", python_sources(), ids=lambda p: p.name)
def test_aucun_import_de_runtime(path: Path) -> None:
    forbidden = imported_roots(path) & FORBIDDEN_ROOTS
    assert not forbidden, (
        f"{path.relative_to(RESEARCH_ROOT)} importe {sorted(forbidden)} : "
        "la recherche ne doit pas pouvoir atteindre le runtime"
    )


def test_le_test_de_frontiere_detecte_reellement_un_import(tmp_path: Path) -> None:
    """Anti-vacuité : la détection fonctionne sur un cas fabriqué."""
    offender = tmp_path / "fuite.py"
    offender.write_text(
        "from vertex_persistence.repositories import SnapshotRepository\n"
        "import sqlalchemy\n",
        encoding="utf-8",
    )
    assert imported_roots(offender) & FORBIDDEN_ROOTS == {
        "vertex_persistence",
        "sqlalchemy",
    }


def test_le_manifeste_de_donnees_reste_vide() -> None:
    """B-04 non tranché : aucune donnée d'options historiques n'est ici."""
    manifest = RESEARCH_ROOT / "datasets-manifest"
    assert manifest.is_dir()
    contents = [p for p in manifest.iterdir() if p.name != ".gitkeep"]
    assert contents == [], f"données présentes sans licence tranchée : {contents}"
