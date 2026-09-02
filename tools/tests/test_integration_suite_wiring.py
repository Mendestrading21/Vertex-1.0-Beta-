"""La CI distante et le miroir local exécutent chaque suite PostgreSQL réelle."""

from __future__ import annotations

import re
import shlex
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHELL_SEPARATORS = {"\n", ";", "&&", "||", "|", "&"}
_PYTHON_EXECUTABLE = re.compile(r"(?:python|python3)(?:\.\d+)?$")


def _postgres_integration_suites(repo_root: Path = _REPO_ROOT) -> tuple[str, ...]:
    suites = (
        path
        for path in repo_root.rglob("tests_integration")
        if path.is_dir()
        and ".venv" not in path.parts
        and any(candidate.is_file() for candidate in path.rglob("test_*.py"))
    )
    return tuple(sorted(str(path.relative_to(repo_root)) for path in suites))


def _shell_tokens(source: str) -> list[str]:
    """Tokeniser du shell sans laisser un commentaire devenir une preuve."""
    lexer = shlex.shlex(source, posix=True, punctuation_chars=";&|\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = "#"
    return list(lexer)


def _commands(tokens: Iterable[str]) -> tuple[tuple[str, ...], ...]:
    commands: list[tuple[str, ...]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SHELL_SEPARATORS:
            if current:
                commands.append(tuple(current))
                current = []
        else:
            current.append(token)
    if current:
        commands.append(tuple(current))
    return tuple(commands)


def _pytest_argument_index(command: tuple[str, ...]) -> int | None:
    """Retourner l'index de pytest seulement pour une véritable invocation."""
    for index, token in enumerate(command):
        executable = Path(token).name
        if executable in {"pytest", "py.test"}:
            if index == 0 or "run" in command[:index]:
                return index
        if token == "pytest" and index >= 2 and command[index - 1] == "-m":
            if _PYTHON_EXECUTABLE.fullmatch(Path(command[index - 2]).name):
                return index
    return None


def _normalise_path_token(token: str) -> str:
    while token.startswith("./"):
        token = token[2:]
    return token.rstrip("/")


def _direct_pytest_targets(source: str, known_suites: set[str]) -> set[str]:
    targets: set[str] = set()
    for command in _commands(_shell_tokens(source)):
        pytest_index = _pytest_argument_index(command)
        if pytest_index is None:
            continue
        arguments = {_normalise_path_token(token) for token in command[pytest_index + 1 :]}
        targets.update(known_suites & arguments)
    return targets


def _loop_pytest_targets(source: str, known_suites: set[str]) -> set[str]:
    """Reconnaître ``for suite in ...; pytest "$suite"`` du miroir local."""
    tokens = _shell_tokens(source)
    targets: set[str] = set()
    cursor = 0
    while cursor < len(tokens):
        if tokens[cursor] != "for" or cursor + 3 >= len(tokens):
            cursor += 1
            continue
        variable = tokens[cursor + 1]
        if tokens[cursor + 2] != "in":
            cursor += 1
            continue
        try:
            do_index = tokens.index("do", cursor + 3)
            done_index = tokens.index("done", do_index + 1)
        except ValueError:
            cursor += 1
            continue

        references = {f"${variable}", f"${{{variable}}}"}
        body_commands = _commands(tokens[do_index + 1 : done_index])
        invokes_variable = any(
            (pytest_index := _pytest_argument_index(command)) is not None
            and bool(references & set(command[pytest_index + 1 :]))
            for command in body_commands
        )
        if invokes_variable:
            values = {
                _normalise_path_token(token)
                for token in tokens[cursor + 3 : do_index]
                if token not in _SHELL_SEPARATORS
            }
            targets.update(known_suites & values)
        cursor = done_index + 1
    return targets


def _shell_pytest_targets(source: str, known_suites: set[str]) -> set[str]:
    return _direct_pytest_targets(source, known_suites) | _loop_pytest_targets(
        source, known_suites
    )


def _yaml_run_scripts(workflow: str) -> tuple[str, ...]:
    """Lire uniquement les commandes ``run`` actives des étapes GitHub Actions."""
    document: Any = yaml.safe_load(workflow)
    if not isinstance(document, dict):
        return ()
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return ()

    scripts: list[str] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                scripts.append(step["run"])
    return tuple(scripts)


def _ci_pytest_targets(workflow: str, known_suites: set[str]) -> set[str]:
    targets: set[str] = set()
    for script in _yaml_run_scripts(workflow):
        targets.update(_shell_pytest_targets(script, known_suites))
    return targets


def test_every_postgres_integration_suite_is_wired_in_ci_and_local_runner() -> None:
    """Ajouter une suite sans la CI ne doit plus laisser sept checks trompeusement verts."""
    ci = (_REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    local = (_REPO_ROOT / "tools" / "run_checks.sh").read_text(encoding="utf-8")
    suites = set(_postgres_integration_suites())

    assert suites
    assert _ci_pytest_targets(ci, suites) == suites
    assert _shell_pytest_targets(local, suites) == suites


def test_un_commentaire_shell_ne_compte_jamais_comme_invocation() -> None:
    suite = "apps/example/tests_integration"
    source = f"""
    # python -m pytest -q {suite}
    echo "pytest {suite}"
    """

    assert _shell_pytest_targets(source, {suite}) == set()


def test_une_suite_avec_tests_imbriques_est_decouverte(tmp_path: Path) -> None:
    nested_test = tmp_path / "apps" / "example" / "tests_integration" / "cases" / "test_db.py"
    nested_test.parent.mkdir(parents=True)
    nested_test.write_text("def test_db() -> None:\n    assert True\n", encoding="utf-8")

    assert _postgres_integration_suites(tmp_path) == ("apps/example/tests_integration",)


def test_un_chemin_yaml_sans_invocation_run_active_ne_compte_pas() -> None:
    suite = "apps/example/tests_integration"
    workflow = f"""
    jobs:
      integration:
        steps:
          - name: ancien appel de {suite}
            # run: python -m pytest -q {suite}
            shell: bash
    """

    assert _ci_pytest_targets(workflow, {suite}) == set()
