"""La recherche ne peut pas atteindre le runtime.

« Aucune donnée de recherche ou de notebook ne peut écrire dans le runtime
live » (`.claude/rules/architecture.md`). Une règle écrite dans un document
n'empêche rien ; ce fichier l'applique par exécution sur l'arbre des sources.

CE QUE CETTE FRONTIÈRE GARANTIT
-------------------------------

Par analyse statique (AST) de chaque fichier `.py` de `research/` et de chaque
cellule de code de chaque notebook `.ipynb` :

* les imports écrits en clair — ``import X``, ``from X import Y`` ;
* les imports dynamiques dont le nom de module est un LITTÉRAL —
  ``importlib.import_module("X")``, ``__import__("X")``,
  ``importlib.util.find_spec("X")`` ;
* les lancements de sous-processus dont l'exécutable est un LITTÉRAL et
  désigne un outil de base de données ou un service runtime — ``psql``,
  ``pg_dump``, ``alembic``, ``uvicorn``… via ``subprocess``, ``os.system``,
  ``os.popen``, ``os.exec*``, ``os.spawn*`` ;
* dans les notebooks, les lignes d'échappement shell (``!cmd``) et les
  cellules ``%%bash``/``%%sh``, scannées TEXTUELLEMENT pour les mêmes
  exécutables.

CE QU'ELLE NE GARANTIT PAS
--------------------------

Une analyse statique ne décide pas ce qu'un programme fait à l'exécution. Ne
sont PAS détectés, et ne peuvent pas l'être ici :

* un nom de module CONSTRUIT au lieu d'être écrit — concaténation, `format`,
  variable, table de correspondance, lecture d'un fichier ou d'une variable
  d'environnement, encodage (`base64`) ;
* ``exec``/``eval`` d'une source assemblée à l'exécution ;
* l'accès à PostgreSQL par un pilote non listé, un tunnel, une socket brute,
  un client HTTP visant l'API locale, ou un exécutable renommé ;
* l'écriture directe dans un fichier ou un volume que le runtime relit.

Cette frontière rend donc le chemin évident IMPOSSIBLE PAR INADVERTANCE. Elle
n'arrête pas quelqu'un qui cherche délibérément à la contourner : cela relève
de la revue humaine et des droits d'accès, pas d'un test.
"""

from __future__ import annotations

import ast
import json
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


# Exécutables dont l'appel depuis `research/` signifierait un effet de
# production : clients et outils PostgreSQL, migrations, serveurs runtime.
FORBIDDEN_EXECUTABLES = frozenset(
    {
        "psql",
        "pgcli",
        "pg_dump",
        "pg_dumpall",
        "pg_restore",
        "pg_ctl",
        "pg_isready",
        "createdb",
        "dropdb",
        "createuser",
        "dropuser",
        "alembic",
        "uvicorn",
        "gunicorn",
    }
)

# Fonctions qui lancent un processus. Nom complet ET nom simple : `from
# subprocess import run` reste un lancement de processus.
PROCESS_ENTRY_POINTS = frozenset(
    {
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
        "subprocess.Popen",
        "os.system",
        "os.popen",
        "os.execl",
        "os.execlp",
        "os.execv",
        "os.execvp",
        "os.spawnl",
        "os.spawnv",
        "os.spawnvp",
        "os.posix_spawn",
        "run",
        "check_call",
        "check_output",
        "Popen",
        "system",
    }
)

# Fonctions qui résolvent un module par son nom.
DYNAMIC_IMPORT_ENTRY_POINTS = frozenset(
    {
        "__import__",
        "importlib.import_module",
        "importlib.__import__",
        "importlib.util.find_spec",
        "importlib.util.module_from_spec",
        "pkgutil.resolve_name",
        "import_module",
        "find_spec",
    }
)

SHELL_CELL_MAGICS = frozenset({"%%bash", "%%sh", "%%script"})


def research_sources(root: Path | None = None) -> list[Path]:
    """Tous les fichiers analysables : modules Python ET notebooks.

    Le notebook est nommément visé par la règle ; l'oublier laisserait la
    frontière ouverte exactement là où elle est le plus utile.
    """
    base = root or RESEARCH_ROOT
    return sorted(
        path
        for pattern in ("*.py", "*.ipynb")
        for path in base.rglob(pattern)
        if "__pycache__" not in path.parts and ".ipynb_checkpoints" not in path.parts
    )


def python_sources() -> list[Path]:
    return sorted(
        path
        for path in RESEARCH_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _dotted_name(node: ast.expr) -> str | None:
    """`subprocess.run` → "subprocess.run" ; une expression calculée → None."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _string_literals(node: ast.expr) -> list[str]:
    """Littéraux textuels DIRECTEMENT présents dans une expression.

    Volontairement limité aux littéraux et aux listes/tuples de littéraux :
    une chaîne assemblée à l'exécution n'est pas lisible ici, et prétendre
    l'inspecter serait mentir sur la portée du contrôle.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [
            element.value
            for element in node.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        ]
    return []


def _executables_in(text: str) -> set[str]:
    """Exécutables interdits nommés dans une ligne de commande littérale."""
    found: set[str] = set()
    for token in text.replace(";", " ").replace("|", " ").replace("&", " ").split():
        name = token.rsplit("/", 1)[-1]
        if name in FORBIDDEN_EXECUTABLES:
            found.add(name)
    return found


def _findings_from_tree(tree: ast.AST) -> set[str]:
    findings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_ROOTS:
                    findings.add(f"import:{root}")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                root = node.module.split(".", 1)[0]
                if root in FORBIDDEN_ROOTS:
                    findings.add(f"import:{root}")
        elif isinstance(node, ast.Call):
            called = _dotted_name(node.func)
            if called is None:
                continue
            # Positionnels ET nommés : `import_module(name="…")` et
            # `subprocess.run(args=[…])` sont des littéraux écrits en clair,
            # que la portée revendiquée couvre — n'itérer que `node.args` les
            # laissait passer (6e audit).
            arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
            if called in DYNAMIC_IMPORT_ENTRY_POINTS:
                for argument in arguments:
                    for literal in _string_literals(argument):
                        root = literal.split(".", 1)[0]
                        if root in FORBIDDEN_ROOTS:
                            findings.add(f"import-dynamique:{root}")
            if called in PROCESS_ENTRY_POINTS:
                for argument in arguments:
                    for literal in _string_literals(argument):
                        for executable in _executables_in(literal):
                            findings.add(f"sous-processus:{executable}")
    return findings


def _split_notebook_cell(source: str) -> tuple[list[str], list[str]]:
    """Sépare le Python analysable des lignes IPython non-Python.

    `!cmd`, `%magie` et `%%magie` ne sont pas du Python : les passer à `ast`
    lèverait une erreur de syntaxe et masquerait tout le reste de la cellule.
    """
    python: list[str] = []
    shell: list[str] = []
    lines = source.splitlines()
    cell_magic = lines[0].strip().split(" ", 1)[0] if lines else ""
    if cell_magic in SHELL_CELL_MAGICS:
        return [], lines[1:]
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("!"):
            shell.append(stripped[1:])
        elif stripped.startswith("%"):
            shell.append(stripped.lstrip("%"))
        elif stripped.endswith("?") and not any(c in stripped for c in " '\"("):
            # Aide IPython (`objet?`) : non-Python, mais sans commande.
            continue
        else:
            python.append(line)
    return python, shell


def notebook_findings(path: Path) -> set[str]:
    """Analyse un notebook : ses cellules de code SONT du Python."""
    document = json.loads(path.read_text(encoding="utf-8"))
    findings: set[str] = set()
    for cell in document.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        python, shell = _split_notebook_cell(source)
        for line in shell:
            for executable in _executables_in(line):
                findings.add(f"sous-processus:{executable}")
        try:
            tree = ast.parse("\n".join(python), filename=str(path))
        except SyntaxError:
            # Une cellule incomplète ne doit pas éteindre le contrôle : elle
            # est signalée, pas ignorée.
            findings.add("cellule-illisible")
            continue
        findings |= _findings_from_tree(tree)
    return findings


def forbidden_findings(path: Path) -> set[str]:
    """Chemins vers le runtime détectables statiquement dans un fichier."""
    if path.suffix == ".ipynb":
        return notebook_findings(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return _findings_from_tree(tree)


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
    assert set(python_sources()).issubset(set(research_sources()))


@pytest.mark.parametrize("path", python_sources(), ids=lambda p: p.name)
def test_aucun_import_de_runtime(path: Path) -> None:
    forbidden = imported_roots(path) & FORBIDDEN_ROOTS
    assert not forbidden, (
        f"{path.relative_to(RESEARCH_ROOT)} importe {sorted(forbidden)} : "
        "la recherche ne doit pas pouvoir atteindre le runtime"
    )


@pytest.mark.parametrize("path", research_sources(), ids=lambda p: p.name)
def test_aucun_chemin_statique_vers_le_runtime(path: Path) -> None:
    """Portée exacte : voir le docstring du module. Ce contrôle couvre les
    imports écrits, les imports dynamiques par littéral et les sous-processus
    par littéral — pas un nom de module construit à l'exécution."""
    findings = forbidden_findings(path)
    assert not findings, (
        f"{path.relative_to(RESEARCH_ROOT)} atteint le runtime par "
        f"{sorted(findings)}"
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


# ── Contournements ────────────────────────────────────────────────────────
#
# Un import statique est le chemin le plus lisible vers le runtime, pas le
# seul. Les tests qui suivent fabriquent les contournements connus et exigent
# qu'ils soient détectés.

def test_un_import_dynamique_par_litteral_est_detecte(tmp_path: Path) -> None:
    offender = tmp_path / "dynamique.py"
    offender.write_text(
        "import importlib\n"
        'repo = importlib.import_module("vertex_persistence.repositories")\n'
        'sa = __import__("sqlalchemy")\n',
        encoding="utf-8",
    )
    assert forbidden_findings(offender) == {
        "import-dynamique:sqlalchemy",
        "import-dynamique:vertex_persistence",
    }


def test_un_appel_a_psql_est_detecte(tmp_path: Path) -> None:
    offender = tmp_path / "shell.py"
    offender.write_text(
        "import subprocess\n"
        'subprocess.run(["psql", "-c", "UPDATE advice SET verdict = \'QUALIFIED\'"])\n',
        encoding="utf-8",
    )
    assert forbidden_findings(offender) == {"sous-processus:psql"}


def test_un_notebook_qui_atteint_le_runtime_est_detecte(tmp_path: Path) -> None:
    notebook = tmp_path / "fuite.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "source": ["import sqlalchemy\n"]},
                    {"cell_type": "code", "source": ["import sqlalchemy\n"]},
                    {"cell_type": "code", "source": ["!psql -c 'DELETE FROM advice'\n"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert forbidden_findings(notebook) == {
        "import:sqlalchemy",
        "sous-processus:psql",
    }


def test_l_inventaire_ramasse_les_notebooks(tmp_path: Path) -> None:
    """Anti-vacuité : `research/notebooks/` est vide aujourd'hui ; on prouve
    sur un arbre fabriqué que le scan les ramasserait."""
    (tmp_path / "notebooks").mkdir()
    (tmp_path / "notebooks" / "etude.ipynb").write_text("{}", encoding="utf-8")
    (tmp_path / "pipelines").mkdir()
    (tmp_path / "pipelines" / "module.py").write_text("", encoding="utf-8")
    noms = {path.name for path in research_sources(tmp_path)}
    assert noms == {"etude.ipynb", "module.py"}


def test_aucun_notebook_n_atteint_le_runtime() -> None:
    for path in research_sources():
        if path.suffix != ".ipynb":
            continue
        assert not forbidden_findings(path), path.relative_to(RESEARCH_ROOT)
