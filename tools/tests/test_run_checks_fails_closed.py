"""Preuve que `tools/run_checks.sh` échoue FERMÉ.

Le miroir local a longtemps invoqué ses portes ainsi :

    python3 tools/check_financial_boundary.py >/dev/null && echo OK

Sous `set -e`, une commande placée à GAUCHE d'un `&&` est exemptée de l'arrêt
sur erreur, et la liste `&&` ne fait pas échouer le script non plus. Onze
portes — dont la frontière financière et la détection de secrets — pouvaient
donc rendre 1 pendant que le script affichait « TOUT VERT » et sortait 0.
C'était le QUATRIÈME contournement de la frontière financière : les trois
premiers l'avaient débranchée, celui-ci l'a rendue muette.

Ces tests prouvent DEUX choses distinctes, parce que l'une sans l'autre ne
suffirait pas :

1. par ANALYSE : aucune invocation de porte n'est l'opérande d'un `&&` ou d'un
   `||`, et le script ne désarme jamais `set -e` ;
2. par EXÉCUTION : le script réel, avec sa première porte remplacée par un
   échec, s'interrompt et n'imprime jamais « TOUT VERT ».

Le second est le seul qui prouve quelque chose sur le comportement ; le premier
empêche les variantes du motif de revenir sous une autre forme.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "tools" / "run_checks.sh"

#: Toute invocation de porte du miroir. Le motif reste volontairement large :
#: mieux vaut examiner une ligne de plus qu'en manquer une.
_GATE_INVOCATION = re.compile(
    r"""^\s*
    (?:\(\s*cd\s|                    # sous-shell : (cd apps/web && pnpm …)
       python3?\s|uv\s|pnpm\s|node\s|npx\s)
    .*
    (?:tools/(?:check_|verify_|measure_|build_)[a-z_]+\.py
      |compileall
      |lock\s+--check
      |ruff\s+check
      |mypy
      |biome\s+lint
      |--test
      |vite\s+build
      |pytest)
    """,
    re.VERBOSE,
)


def _script_lines() -> list[str]:
    return _SCRIPT.read_text(encoding="utf-8").splitlines()


def _code_lines() -> list[tuple[int, str]]:
    """Lignes de code, commentaires et lignes vides exclus."""
    return [
        (number, line)
        for number, line in enumerate(_script_lines(), start=1)
        if line.strip() and not line.strip().startswith("#")
    ]


# ── 1. analyse ───────────────────────────────────────────────────────────────


def test_aucune_porte_n_est_l_operande_gauche_d_un_et_logique() -> None:
    coupables = [
        f"{number}: {line.strip()}"
        for number, line in _code_lines()
        if _GATE_INVOCATION.search(line) and re.search(r"&&\s*echo|&&\s*\w", line.split("#")[0])
        # Un `&&` INTERNE à un sous-shell `(cd X && commande)` est légitime :
        # c'est le sous-shell entier qui est la commande surveillée.
        and not re.match(r"^\s*\(\s*cd\s.*\)\s*$", line.strip())
    ]
    assert not coupables, (
        "une porte placée à gauche d'un `&&` est exemptée de `set -e` : "
        f"elle peut échouer sans arrêter le script — {coupables}"
    )


def test_aucune_porte_n_est_neutralisee_par_ou_vrai() -> None:
    coupables = [
        f"{number}: {line.strip()}"
        for number, line in _code_lines()
        if _GATE_INVOCATION.search(line) and re.search(r"\|\|\s*(?:true|:)\b", line.split("#")[0])
    ]
    assert not coupables, f"`|| true` avale le code de retour d'une porte — {coupables}"


def test_le_script_n_a_jamais_desarme_l_arret_sur_erreur() -> None:
    desarmements = [
        f"{number}: {line.strip()}"
        for number, line in _code_lines()
        if re.search(r"set\s+\+e|set\s+\+o\s+errexit", line)
    ]
    assert not desarmements, f"`set +e` rend le miroir permissif — {desarmements}"


def test_l_arret_sur_erreur_est_bien_arme() -> None:
    """Anti-vacuité des trois tests précédents : sans `set -e`, ils ne prouvent rien."""
    assert any(
        re.match(r"^set\s+-euo\s+pipefail\s*$", line.strip()) for _, line in _code_lines()
    ), "le script doit armer `set -euo pipefail`"


def test_le_balayage_voit_bien_des_portes() -> None:
    """Anti-vacuité : un motif qui ne reconnaîtrait plus rien rendrait tout vert."""
    reconnues = [line.strip() for _, line in _code_lines() if _GATE_INVOCATION.search(line)]
    assert len(reconnues) >= 10, (
        f"seulement {len(reconnues)} invocations reconnues : le motif d'analyse est "
        "devenu aveugle et les tests ci-dessus ne prouvent plus rien"
    )


# ── 2. exécution ─────────────────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform == "win32", reason="miroir shell POSIX uniquement")
def test_une_porte_en_echec_interrompt_reellement_le_script(tmp_path: Path) -> None:
    """La seule preuve qui porte sur le COMPORTEMENT.

    On substitue la PREMIÈRE porte du script réel par un échec et on exécute.
    Le script doit s'arrêter là : code de retour non nul, et surtout aucune
    ligne « TOUT VERT ».
    """
    original = _SCRIPT.read_text(encoding="utf-8")
    premiere = "python3 tools/check_repository_role.py target ."
    assert premiere in original, (
        "la première porte du miroir a changé de nom ; ce test doit être recalé "
        "sur la nouvelle, sinon il ne substitue plus rien"
    )

    substitue = tmp_path / "run_checks_substitue.sh"
    substitue.write_text(
        original.replace(premiere, "false  # porte substituée par ce test", 1), encoding="utf-8"
    )

    resultat = subprocess.run(  # noqa: S603 - argv littéral, script écrit par le test
        ["/bin/bash", str(substitue)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=_REPO_ROOT,
    )

    assert resultat.returncode != 0, (
        "une porte en échec doit faire échouer le miroir ; code de retour "
        f"{resultat.returncode}"
    )
    assert "TOUT VERT" not in resultat.stdout, (
        "le miroir a annoncé « TOUT VERT » alors qu'une porte a échoué :\n" + resultat.stdout
    )


def test_le_script_substitue_irait_au_bout_sans_l_echec(tmp_path: Path) -> None:
    """Anti-vacuité du test précédent.

    Si le script s'arrêtait pour une raison SANS RAPPORT (chemin cassé,
    interpréteur absent), le test ci-dessus passerait sans rien prouver. On
    vérifie donc que la substitution par une commande qui RÉUSSIT laisse le
    script dépasser cette première porte.
    """
    original = _SCRIPT.read_text(encoding="utf-8")
    premiere = "python3 tools/check_repository_role.py target ."
    substitue = tmp_path / "run_checks_reussite.sh"
    substitue.write_text(
        original.replace(premiere, "true  # porte substituée par ce test", 1), encoding="utf-8"
    )

    resultat = subprocess.run(  # noqa: S603 - argv littéral, script écrit par le test
        ["/bin/bash", str(substitue)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=_REPO_ROOT,
    )
    assert "== blueprint ==" in resultat.stdout, (
        "le script n'a pas dépassé la première porte même en cas de succès : "
        "le test d'échec ci-dessus ne prouverait rien.\n" + resultat.stdout[-2000:]
    )
