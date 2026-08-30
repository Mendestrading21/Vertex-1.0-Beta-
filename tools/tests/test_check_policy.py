"""Preuve d'exécution de la porte `tools/check_policy.py`.

Une porte qui ne signale jamais rien ne prouve rien. Chaque contrôle de la
porte est ici exercé DEUX fois : sur une arborescence conforme (elle doit se
taire) puis sur la MÊME arborescence où la violation a été injectée (elle doit
nommer le code attendu).

Aucun réseau : `resolve_remote` est prouvé en remplaçant `subprocess.run` par
une sortie `git ls-remote` fabriquée. Toutes les valeurs sont SYNTHETIC.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE = _REPO_ROOT / "tools" / "check_policy.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_policy_gate", _GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_policy_gate"] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()

# SHA SYNTHETIC : 40 caractères hexadécimaux, aucun dépôt réel derrière.
PINNED = "a" * 40
TAG_OBJECT = "b" * 40
OTHER = "c" * 40

PINS = {
    "demo/action": {
        "repository": "demo/action",
        "tag": "v1.0.0",
        "tag_kind": "annotated",
        "commit_sha": PINNED,
        "tag_object_sha": TAG_OBJECT,
    }
}

CLEAN_WORKFLOW = f"""
name: ci
on:
  push:
    branches: ["main"]
permissions: read-all
jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    services:
      db:
        image: postgres:18@sha256:{"4" * 64}
    steps:
      - uses: demo/action@{PINNED} # v1.0.0
      - run: echo ok
"""


def _codes(findings) -> list[str]:
    return [f.code for f in findings]


def _policy() -> dict:
    return yaml.safe_load((_REPO_ROOT / "manifests" / "policy.yaml").read_text(encoding="utf-8"))


# ── 1. Épinglage des Actions ────────────────────────────────────────────────


def test_clean_workflow_raises_nothing() -> None:
    assert gate.check_uses("w.yml", CLEAN_WORKFLOW, PINS) == []
    assert gate.check_workflow("w.yml", CLEAN_WORKFLOW, _policy()) == []


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("demo/action@v1.0.0", "ACTION_NOT_PINNED"),
        ("demo/action@main", "ACTION_NOT_PINNED"),
        ("demo/action@" + PINNED[:39], "ACTION_NOT_PINNED"),
        ("demo/action", "ACTION_NOT_PINNED"),
        ("inconnu/action@" + PINNED, "ACTION_PIN_UNKNOWN"),
        ("demo/action@" + OTHER, "ACTION_PIN_UNKNOWN"),
        ("demo/action@" + TAG_OBJECT, "ACTION_PIN_IS_TAG_OBJECT"),
    ],
)
def test_injected_action_pin_is_reported(reference: str, expected: str) -> None:
    injected = CLEAN_WORKFLOW.replace(f"demo/action@{PINNED}", reference)
    assert expected in _codes(gate.check_uses("w.yml", injected, PINS))


def test_annotated_tag_object_is_distinguished_from_its_commit() -> None:
    """Le cœur du contrôle : un objet-tag annoté N'EST PAS un commit.

    `pnpm/action-setup@v4.2.0` du dépôt est exactement ce cas ; épingler
    l'objet-tag serait accepté par GitHub et invisible à l'œil nu.
    """
    good = gate.check_uses("w.yml", CLEAN_WORKFLOW, PINS)
    bad = gate.check_uses(
        "w.yml", CLEAN_WORKFLOW.replace(PINNED, TAG_OBJECT), PINS
    )
    assert good == []
    assert _codes(bad) == ["ACTION_PIN_IS_TAG_OBJECT"]


def test_local_action_needs_no_sha() -> None:
    text = CLEAN_WORKFLOW.replace(f"demo/action@{PINNED}", "./.github/actions/local")
    assert gate.check_uses("w.yml", text, PINS) == []


def test_docker_uses_is_checked_as_an_image() -> None:
    text = CLEAN_WORKFLOW.replace(f"demo/action@{PINNED}", "docker://alpine:latest")
    assert "IMAGE_LATEST" in _codes(gate.check_uses("w.yml", text, PINS))


# ── 2. Résolution distante (réseau simulé, jamais appelé) ───────────────────


def _fake_ls_remote(monkeypatch, stdout: str) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)


def test_resolve_remote_accepts_a_manifest_that_matches(monkeypatch) -> None:
    _fake_ls_remote(
        monkeypatch,
        f"{TAG_OBJECT}\trefs/tags/v1.0.0\n{PINNED}\trefs/tags/v1.0.0^{{}}\n",
    )
    assert gate.resolve_remote(PINS) == []


def test_resolve_remote_reports_a_moved_tag(monkeypatch) -> None:
    _fake_ls_remote(
        monkeypatch,
        f"{TAG_OBJECT}\trefs/tags/v1.0.0\n{OTHER}\trefs/tags/v1.0.0^{{}}\n",
    )
    assert "ACTION_PIN_DRIFT" in _codes(gate.resolve_remote(PINS))


def test_resolve_remote_reports_a_deleted_tag(monkeypatch) -> None:
    _fake_ls_remote(monkeypatch, "")
    assert "ACTION_PIN_DRIFT" in _codes(gate.resolve_remote(PINS))


def test_resolve_remote_reports_a_tag_that_became_lightweight(monkeypatch) -> None:
    _fake_ls_remote(monkeypatch, f"{PINNED}\trefs/tags/v1.0.0\n")
    assert "ACTION_PIN_DRIFT" in _codes(gate.resolve_remote(PINS))


# ── 3. Permissions, timeouts, runners, pull_request_target ─────────────────


def test_missing_permissions_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace("permissions: read-all\n", "")
    assert "WORKFLOW_NO_PERMISSIONS" in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_write_permission_without_motive_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace(
        "permissions: read-all", "permissions:\n  contents: write\n  actions: read"
    )
    assert "PERMISSION_ELEVATION" in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_write_all_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace("permissions: read-all", "permissions: write-all")
    assert "PERMISSION_ELEVATION" in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_write_permission_with_a_written_motive_is_accepted() -> None:
    injected = CLEAN_WORKFLOW.replace(
        "permissions: read-all",
        "# MOTIF-PERMISSION: contents — publication de la note de version.\n"
        "permissions:\n  contents: write",
    )
    assert gate.check_workflow("w.yml", injected, _policy()) == []


def test_motive_naming_another_scope_does_not_cover_this_one() -> None:
    injected = CLEAN_WORKFLOW.replace(
        "permissions: read-all",
        "# MOTIF-PERMISSION: packages — publication d'image.\npermissions:\n  contents: write",
    )
    assert "PERMISSION_ELEVATION" in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_job_without_timeout_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace("    timeout-minutes: 10\n", "")
    assert "JOB_NO_TIMEOUT" in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_step_that_cannot_fail_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace(
        "      - run: echo ok\n", "      - run: echo ok\n        continue-on-error: true\n"
    )
    assert "CONTINUE_ON_ERROR" in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_job_that_cannot_fail_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace(
        "    timeout-minutes: 10\n", "    timeout-minutes: 10\n    continue-on-error: true\n"
    )
    assert "CONTINUE_ON_ERROR" in _codes(gate.check_workflow("w.yml", injected, _policy()))


@pytest.mark.parametrize(
    ("runner", "expected"),
    [
        ("self-hosted", "SELF_HOSTED_RUNNER"),
        ("[self-hosted, linux, tws]", "SELF_HOSTED_RUNNER"),
        ("windows-2019", "SELF_HOSTED_RUNNER"),
        ("${{ matrix.os }}", "RUNNER_UNVERIFIABLE"),
    ],
)
def test_injected_runner_is_reported(runner: str, expected: str) -> None:
    injected = CLEAN_WORKFLOW.replace("runs-on: ubuntu-24.04", f"runs-on: {runner}")
    assert expected in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_self_hosted_runner_group_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace(
        "    runs-on: ubuntu-24.04\n", "    runs-on:\n      group: tws-machine\n"
    )
    assert "SELF_HOSTED_RUNNER" in _codes(gate.check_workflow("w.yml", injected, _policy()))


PR_TARGET = f"""
name: dangereux
on: pull_request_target
permissions: read-all
jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@{PINNED}
        with:
          ref: ${{{{ github.event.pull_request.head.sha }}}}
"""


def test_pull_request_target_checking_out_pr_code_is_reported() -> None:
    assert "PR_TARGET_CHECKOUT" in _codes(gate.check_workflow("w.yml", PR_TARGET, _policy()))


def test_pull_request_target_without_pr_ref_is_accepted() -> None:
    safe = PR_TARGET.replace(
        "        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n", ""
    )
    assert "PR_TARGET_CHECKOUT" not in _codes(gate.check_workflow("w.yml", safe, _policy()))


def test_same_checkout_under_pull_request_is_not_reported() -> None:
    """Le danger vient du déclencheur, pas du `ref` : la porte doit le savoir."""
    ordinary = PR_TARGET.replace("on: pull_request_target", "on: pull_request")
    assert "PR_TARGET_CHECKOUT" not in _codes(gate.check_workflow("w.yml", ordinary, _policy()))


# ── 4. Images de conteneur ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (f"postgres:18@sha256:{'4' * 64}", None),
        ("postgres:18", "IMAGE_NO_DIGEST"),
        ("postgres:latest", "IMAGE_LATEST"),
        (f"postgres:latest@sha256:{'4' * 64}", "IMAGE_LATEST"),
        ("postgres", "IMAGE_NO_DIGEST"),
        ("postgres:18@sha256:tropcourt", "IMAGE_NO_DIGEST"),
        ("${{ env.IMAGE }}", "IMAGE_UNVERIFIABLE"),
    ],
)
def test_image_reference(reference: str, expected: str | None) -> None:
    codes = _codes(gate.check_image_ref("where", reference))
    assert codes == ([] if expected is None else [expected])


def test_service_image_without_digest_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace(f"postgres:18@sha256:{'4' * 64}", "postgres:18")
    assert "IMAGE_NO_DIGEST" in _codes(gate.check_workflow("w.yml", injected, _policy()))


def test_job_container_without_digest_is_reported() -> None:
    injected = CLEAN_WORKFLOW.replace(
        "    services:\n", "    container:\n      image: python:3.13-slim\n    services:\n"
    )
    assert "IMAGE_NO_DIGEST" in _codes(gate.check_workflow("w.yml", injected, _policy()))


CLEAN_DOCKERFILE = f"""
FROM python:3.13-slim@sha256:{'7' * 64} AS base
RUN true
FROM base AS runtime
COPY . .
"""


def test_clean_dockerfile_raises_nothing() -> None:
    assert gate.check_dockerfile("Dockerfile", CLEAN_DOCKERFILE) == []


def test_dockerfile_without_digest_is_reported() -> None:
    injected = CLEAN_DOCKERFILE.replace(f"python:3.13-slim@sha256:{'7' * 64}", "python:3.13-slim")
    assert "IMAGE_NO_DIGEST" in _codes(gate.check_dockerfile("Dockerfile", injected))


def test_dockerfile_latest_is_reported() -> None:
    injected = CLEAN_DOCKERFILE.replace(f"python:3.13-slim@sha256:{'7' * 64}", "python:latest")
    assert "IMAGE_LATEST" in _codes(gate.check_dockerfile("Dockerfile", injected))


def test_dockerfile_stage_reference_is_not_an_image() -> None:
    assert "IMAGE_NO_DIGEST" not in _codes(gate.check_dockerfile("Dockerfile", CLEAN_DOCKERFILE))


# ── 5. Arborescence minimale : dépendances, verrous, câblage ────────────────

UV_LOCK = """version = 1
revision = 3
requires-python = ">=3.11"

[[package]]
name = "demo-app"
version = "0.1.0"
source = { editable = "." }
dependencies = [{ name = "httpx" }]

[package.metadata]
requires-dist = [
    { name = "httpx", specifier = ">=0.27" },
    { name = "ruff", marker = "extra == 'dev'", specifier = "==0.15.8" },
]

[[package]]
name = "httpx"
version = "0.28.1"
source = { registry = "https://pypi.org/simple" }
wheels = [{ url = "https://example.invalid/httpx.whl", hash = "sha256:aaaa" }]

[[package]]
name = "ruff"
version = "0.15.8"
source = { registry = "https://pypi.org/simple" }
wheels = [{ url = "https://example.invalid/ruff.whl", hash = "sha256:bbbb" }]
"""

PYPROJECT = """[project]
name = "demo-app"
version = "0.1.0"
dependencies = ["httpx>=0.27"]

[project.optional-dependencies]
dev = ["ruff==0.15.8"]

[tool.uv.workspace]
members = []
"""

PACKAGE_JSON = {
    "name": "demo-web",
    "dependencies": {"react": "19.2.8"},
    "devDependencies": {"typescript": "5.9.3"},
}

PNPM_LOCK = """lockfileVersion: '9.0'

importers:

  .:
    dependencies:
      react:
        specifier: 19.2.8
        version: 19.2.8
    devDependencies:
      typescript:
        specifier: 5.9.3
        version: 5.9.3

packages:

  react@19.2.8:
    resolution: {integrity: sha512-synthetiquereact}

  typescript@5.9.3:
    resolution: {integrity: sha512-synthetiquets}

snapshots:

  react@19.2.8: {}

  typescript@5.9.3: {}
"""

TMP_POLICY = {
    "schema_version": 1,
    "runners": {"allowed": ["ubuntu-24.04"]},
    "permissions": {"workflow_default": "read-all", "motive_marker": "MOTIF-PERMISSION:"},
    "dependencies": {
        "exact_pin_required": ["ruff", "typescript"],
        "first_party_python": ["demo-app"],
    },
    "gates": {"must_be_wired": ["tools/check_alpha.py"]},
    "licenses": {"allowed_spdx": ["MIT"], "denied_spdx": []},
}


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """Dépôt SYNTHETIC minimal, conforme, prêt à recevoir une injection."""
    (tmp_path / "manifests").mkdir()
    (tmp_path / "tools" / "tests").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (tmp_path / "uv.lock").write_text(UV_LOCK, encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps(PACKAGE_JSON), encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text(PNPM_LOCK, encoding="utf-8")
    (tmp_path / "manifests" / "policy.yaml").write_text(
        yaml.safe_dump(TMP_POLICY), encoding="utf-8"
    )
    (tmp_path / "manifests" / "actions-pins.yaml").write_text(
        yaml.safe_dump({"actions": list(PINS.values())}), encoding="utf-8"
    )
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        CLEAN_WORKFLOW + "      - run: python tools/check_alpha.py\n", encoding="utf-8"
    )
    (tmp_path / "tools" / "check_alpha.py").write_text("# porte SYNTHETIC\n", encoding="utf-8")
    (tmp_path / "tools" / "run_checks.sh").write_text(
        "#!/usr/bin/env bash\npython3 tools/check_alpha.py\n", encoding="utf-8"
    )
    return tmp_path


def test_sandbox_is_clean(sandbox: Path) -> None:
    assert gate.collect_findings(sandbox) == []


def test_python_dependency_without_constraint_is_reported(sandbox: Path) -> None:
    (sandbox / "pyproject.toml").write_text(
        PYPROJECT.replace('"httpx>=0.27"', '"httpx"'), encoding="utf-8"
    )
    assert "DEP_UNPINNED" in _codes(gate.collect_findings(sandbox))


def test_python_wildcard_is_reported(sandbox: Path) -> None:
    (sandbox / "pyproject.toml").write_text(
        PYPROJECT.replace('"httpx>=0.27"', '"httpx==*"'), encoding="utf-8"
    )
    assert "DEP_FLOATING" in _codes(gate.collect_findings(sandbox))


def test_verdict_tool_that_is_not_exactly_pinned_is_reported(sandbox: Path) -> None:
    (sandbox / "pyproject.toml").write_text(
        PYPROJECT.replace('"ruff==0.15.8"', '"ruff>=0.15"'), encoding="utf-8"
    )
    assert "DEP_NOT_EXACT" in _codes(gate.collect_findings(sandbox))


def test_python_dependency_absent_from_the_lock_is_reported(sandbox: Path) -> None:
    (sandbox / "pyproject.toml").write_text(
        PYPROJECT.replace(
            'dependencies = ["httpx>=0.27"]', 'dependencies = ["httpx>=0.27", "requests>=2"]'
        ),
        encoding="utf-8",
    )
    assert "DEP_NOT_LOCKED" in _codes(gate.collect_findings(sandbox))


def test_uv_lock_desynchronised_from_the_manifest_is_reported(sandbox: Path) -> None:
    """Le manifeste bouge, le verrou ne suit pas : la porte le voit hors ligne."""
    (sandbox / "pyproject.toml").write_text(
        PYPROJECT.replace('"httpx>=0.27"', '"httpx>=0.28"'), encoding="utf-8"
    )
    assert "LOCK_DESYNC" in _codes(gate.collect_findings(sandbox))


def test_uv_lock_package_without_hash_is_reported(sandbox: Path) -> None:
    (sandbox / "uv.lock").write_text(
        UV_LOCK.replace(
            'wheels = [{ url = "https://example.invalid/httpx.whl", hash = "sha256:aaaa" }]',
            'wheels = [{ url = "https://example.invalid/httpx.whl" }]',
        ),
        encoding="utf-8",
    )
    assert "LOCK_NO_HASH" in _codes(gate.collect_findings(sandbox))


def test_missing_uv_lock_is_reported(sandbox: Path) -> None:
    (sandbox / "uv.lock").unlink()
    assert "LOCK_MISSING" in _codes(gate.collect_findings(sandbox))


@pytest.mark.parametrize("specifier", ["^19.2.8", "~19.2.8", ">=19", "latest", "*"])
def test_floating_npm_dependency_is_reported(sandbox: Path, specifier: str) -> None:
    manifest = json.loads(json.dumps(PACKAGE_JSON))
    manifest["dependencies"]["react"] = specifier
    (sandbox / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert "DEP_FLOATING" in _codes(gate.collect_findings(sandbox))


def test_floating_npm_verdict_tool_is_reported_as_not_exact(sandbox: Path) -> None:
    manifest = json.loads(json.dumps(PACKAGE_JSON))
    manifest["devDependencies"]["typescript"] = "^5.9.3"
    (sandbox / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert "DEP_NOT_EXACT" in _codes(gate.collect_findings(sandbox))


def test_pnpm_lock_desynchronised_from_package_json_is_reported(sandbox: Path) -> None:
    manifest = json.loads(json.dumps(PACKAGE_JSON))
    manifest["dependencies"]["react"] = "19.2.9"
    (sandbox / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert "LOCK_DESYNC" in _codes(gate.collect_findings(sandbox))


def test_dependency_added_without_relocking_is_reported(sandbox: Path) -> None:
    manifest = json.loads(json.dumps(PACKAGE_JSON))
    manifest["dependencies"]["zustand"] = "5.0.0"
    (sandbox / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert "LOCK_DESYNC" in _codes(gate.collect_findings(sandbox))


def test_pnpm_package_without_integrity_is_reported(sandbox: Path) -> None:
    (sandbox / "pnpm-lock.yaml").write_text(
        PNPM_LOCK.replace(
            "    resolution: {integrity: sha512-synthetiquereact}", "    resolution: {}"
        ),
        encoding="utf-8",
    )
    assert "LOCK_NO_HASH" in _codes(gate.collect_findings(sandbox))


def test_package_json_without_lockfile_is_reported(sandbox: Path) -> None:
    (sandbox / "pnpm-lock.yaml").unlink()
    assert "LOCK_MISSING" in _codes(gate.collect_findings(sandbox))


def test_gate_removed_from_ci_is_reported(sandbox: Path) -> None:
    text = (sandbox / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    (sandbox / ".github" / "workflows" / "ci.yml").write_text(
        text.replace("      - run: python tools/check_alpha.py\n", ""), encoding="utf-8"
    )
    assert "GATE_NOT_WIRED" in _codes(gate.collect_findings(sandbox))


def test_gate_removed_from_run_checks_is_reported(sandbox: Path) -> None:
    (sandbox / "tools" / "run_checks.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    assert "GATE_NOT_WIRED" in _codes(gate.collect_findings(sandbox))


def test_undeclared_gate_script_is_reported(sandbox: Path) -> None:
    (sandbox / "tools" / "check_beta.py").write_text("# porte SYNTHETIC\n", encoding="utf-8")
    assert "GATE_NOT_DECLARED" in _codes(gate.collect_findings(sandbox))


def test_dormant_gate_without_reason_is_reported(sandbox: Path) -> None:
    policy = json.loads(json.dumps(TMP_POLICY))
    policy["gates"]["known_not_wired"] = [{"script": "tools/check_beta.py", "reason": ""}]
    (sandbox / "manifests" / "policy.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    (sandbox / "tools" / "check_beta.py").write_text("# porte SYNTHETIC\n", encoding="utf-8")
    assert "GATE_DORMANT_WITHOUT_REASON" in _codes(gate.collect_findings(sandbox))


def test_dormant_gate_that_is_actually_wired_is_reported(sandbox: Path) -> None:
    policy = json.loads(json.dumps(TMP_POLICY))
    policy["gates"]["known_not_wired"] = [
        {"script": "tools/check_alpha.py", "reason": "motif SYNTHETIC"}
    ]
    policy["gates"]["must_be_wired"] = []
    (sandbox / "manifests" / "policy.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    assert "GATE_DORMANT_BUT_WIRED" in _codes(gate.collect_findings(sandbox))


def test_compose_image_without_digest_is_reported(sandbox: Path) -> None:
    (sandbox / "compose.yaml").write_text(
        yaml.safe_dump({"services": {"db": {"image": "postgres:18"}}}), encoding="utf-8"
    )
    assert "IMAGE_NO_DIGEST" in _codes(gate.collect_findings(sandbox))


def test_missing_policy_manifest_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        gate.collect_findings(tmp_path)


def test_missing_actions_pins_manifest_fails_closed(sandbox: Path) -> None:
    (sandbox / "manifests" / "actions-pins.yaml").unlink()
    with pytest.raises(SystemExit):
        gate.collect_findings(sandbox)


# ── 6. Le dépôt réel doit satisfaire sa propre porte ────────────────────────


def test_the_repository_itself_satisfies_the_policy_gate() -> None:
    """Sentinelle : la porte est verte ICI, sur l'arbre commité.

    Si ce test rougit, ce n'est pas le test qu'il faut changer : le message
    nomme l'anomalie de politique introduite.
    """
    findings = gate.collect_findings(_REPO_ROOT)
    assert findings == [], "\n".join(f.render() for f in findings)
