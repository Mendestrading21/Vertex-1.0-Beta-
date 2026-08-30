"""Preuve d'exécution du volet `notices` de la porte `release`.

Même discipline que pour `tools/check_policy.py` : une arborescence SYNTHETIC
conforme, puis la MÊME arborescence avec une violation injectée. Aucun réseau :
le mode `--refresh` (qui, lui, interroge PyPI et npm) n'est pas exercé ici ;
seule sa fonction de normalisation l'est, sur des chaînes littérales.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE = _REPO_ROOT / "tools" / "check_notices.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_notices_gate", _GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_notices_gate"] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _codes(findings) -> list[str]:
    return [f.code for f in findings]


# ── Normalisation des licences ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("MIT", "MIT"),
        ("MIT License", "MIT"),
        ("Apache License, Version 2.0", "Apache-2.0"),
        ("SIL OPEN FONT LICENSE", "OFL-1.1"),
        ("BSD-3-Clause", "BSD-3-Clause"),
        (None, "UNKNOWN"),
        ("", "UNKNOWN"),
        ("NOASSERTION", "UNKNOWN"),
        # Un texte de licence complet collé dans la métadonnée n'est PAS un
        # identifiant : il doit rester inconnu, donc bloquant.
        ("Permission is hereby granted, free of charge, " * 5, "UNKNOWN"),
    ],
)
def test_license_normalisation(raw: str | None, expected: str) -> None:
    assert gate.normalize_license(raw) == expected


def test_trove_classifier_is_used_only_as_a_fallback() -> None:
    assert gate.normalize_license(None, ["License :: OSI Approved :: MIT License"]) == "MIT"
    assert gate.normalize_license("BSD-2-Clause", ["License :: OSI Approved :: MIT License"]) == (
        "BSD-2-Clause"
    )


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("MIT", ["MIT"]),
        ("MIT OR Apache-2.0", ["MIT", "Apache-2.0"]),
        ("(MIT OR CC0-1.0)", ["MIT", "CC0-1.0"]),
        ("BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", [
            "BSD-3-Clause", "0BSD", "MIT", "Zlib", "CC0-1.0",
        ]),
        ("Apache-2.0 WITH LLVM-exception", ["Apache-2.0", "LLVM-exception"]),
    ],
)
def test_spdx_expression_is_split_into_identifiers(expression: str, expected: list[str]) -> None:
    assert gate.spdx_identifiers(expression) == expected


# ── Arborescence SYNTHETIC ──────────────────────────────────────────────────

UV_LOCK = """version = 1
revision = 3
requires-python = ">=3.11"

[[package]]
name = "demo-app"
version = "0.1.0"
source = { editable = "." }
dependencies = [{ name = "libruntime" }]

[[package]]
name = "libruntime"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
wheels = [{ url = "https://example.invalid/libruntime.whl", hash = "sha256:aaaa" }]

[[package]]
name = "libtest"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }
wheels = [{ url = "https://example.invalid/libtest.whl", hash = "sha256:bbbb" }]
"""

PNPM_LOCK = """lockfileVersion: '9.0'

importers:

  .:
    dependencies:
      widget:
        specifier: 1.2.3
        version: 1.2.3
    devDependencies:
      linter:
        specifier: 4.5.6
        version: 4.5.6

packages:

  widget@1.2.3:
    resolution: {integrity: sha512-synthetiquewidget}

  linter@4.5.6:
    resolution: {integrity: sha512-synthetiquelinter}

snapshots:

  widget@1.2.3: {}

  linter@4.5.6: {}
"""

POLICY = {
    "dependencies": {"first_party_python": ["demo-app"]},
    "licenses": {
        "allowed_spdx": ["MIT", "Apache-2.0"],
        "denied_spdx": ["AGPL-3.0-only"],
        "acknowledged_spdx": [
            {"id": "LGPL-3.0-only", "reason": "motif SYNTHETIC écrit pour ce test"}
        ],
    },
}

REGISTRY = {
    "schema_version": 1,
    "components": [
        {
            "ecosystem": "javascript",
            "name": "linter",
            "version": "4.5.6",
            "license": "MIT",
            "role": "development",
            "source": "https://registry.npmjs.example/linter/4.5.6",
        },
        {
            "ecosystem": "javascript",
            "name": "widget",
            "version": "1.2.3",
            "license": "MIT",
            "role": "runtime",
            "source": "https://registry.npmjs.example/widget/1.2.3",
        },
        {
            "ecosystem": "python",
            "name": "libruntime",
            "version": "1.0.0",
            "license": "Apache-2.0",
            "role": "runtime",
            "source": "https://pypi.example/libruntime/1.0.0",
        },
        {
            "ecosystem": "python",
            "name": "libtest",
            "version": "2.0.0",
            "license": "MIT",
            "role": "development",
            "source": "https://pypi.example/libtest/2.0.0",
        },
    ],
}


def _write(root: Path, *, registry: dict | None = None, policy: dict | None = None) -> None:
    (root / "manifests").mkdir(exist_ok=True)
    (root / "apps" / "web").mkdir(parents=True, exist_ok=True)
    (root / "uv.lock").write_text(UV_LOCK, encoding="utf-8")
    (root / "apps" / "web" / "pnpm-lock.yaml").write_text(PNPM_LOCK, encoding="utf-8")
    (root / "manifests" / "policy.yaml").write_text(
        yaml.safe_dump(policy or POLICY), encoding="utf-8"
    )
    (root / "manifests" / "licenses.yaml").write_text(
        yaml.safe_dump(registry or REGISTRY), encoding="utf-8"
    )
    components = gate.inventory(root, policy or POLICY)
    loaded = gate.load_registry(root)
    (root / "THIRD_PARTY_NOTICES.md").write_text(
        "# Notices SYNTHETIC\n\n" + gate.render_table(components, loaded) + "\n", encoding="utf-8"
    )


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    _write(tmp_path)
    return tmp_path


def test_sandbox_is_clean(sandbox: Path) -> None:
    assert gate.collect_findings(sandbox) == []


def test_role_is_derived_from_the_lock_graph(sandbox: Path) -> None:
    """`runtime` doit venir du graphe, pas d'une déclaration à la main."""
    components = {(c.name, c.role) for c in gate.inventory(sandbox, POLICY)}
    assert ("libruntime", "runtime") in components
    assert ("libtest", "development") in components
    assert ("widget", "runtime") in components
    assert ("linter", "development") in components


def test_component_added_to_the_lock_without_a_licence_is_reported(sandbox: Path) -> None:
    (sandbox / "uv.lock").write_text(
        UV_LOCK
        + '\n[[package]]\nname = "libnouveau"\nversion = "3.0.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        'wheels = [{ url = "https://example.invalid/n.whl", hash = "sha256:cccc" }]\n',
        encoding="utf-8",
    )
    assert "NOTICE_MISSING_COMPONENT" in _codes(gate.collect_findings(sandbox))


def test_version_bump_without_regenerating_is_reported(sandbox: Path) -> None:
    (sandbox / "uv.lock").write_text(
        UV_LOCK.replace(
            'name = "libruntime"\nversion = "1.0.0"', 'name = "libruntime"\nversion = "1.1.0"'
        ),
        encoding="utf-8",
    )
    codes = _codes(gate.collect_findings(sandbox))
    assert "NOTICE_MISSING_COMPONENT" in codes
    assert "NOTICE_GHOST_COMPONENT" in codes


def test_registry_entry_absent_from_the_locks_is_reported(sandbox: Path) -> None:
    registry = {"schema_version": 1, "components": [*REGISTRY["components"], {
        "ecosystem": "python",
        "name": "fantome",
        "version": "9.9.9",
        "license": "MIT",
        "role": "runtime",
        "source": "https://pypi.example/fantome/9.9.9",
    }]}
    (sandbox / "manifests" / "licenses.yaml").write_text(
        yaml.safe_dump(registry), encoding="utf-8"
    )
    assert "NOTICE_GHOST_COMPONENT" in _codes(gate.collect_findings(sandbox))


@pytest.mark.parametrize("value", ["", "UNKNOWN", "NOASSERTION"])
def test_unknown_licence_blocks(sandbox: Path, value: str) -> None:
    registry = yaml.safe_load((sandbox / "manifests" / "licenses.yaml").read_text())
    registry["components"][2]["license"] = value
    (sandbox / "manifests" / "licenses.yaml").write_text(
        yaml.safe_dump(registry), encoding="utf-8"
    )
    assert "LICENSE_UNKNOWN" in _codes(gate.collect_findings(sandbox))


def test_denied_licence_blocks(sandbox: Path) -> None:
    registry = yaml.safe_load((sandbox / "manifests" / "licenses.yaml").read_text())
    registry["components"][2]["license"] = "AGPL-3.0-only"
    (sandbox / "manifests" / "licenses.yaml").write_text(
        yaml.safe_dump(registry), encoding="utf-8"
    )
    assert "LICENSE_DENIED" in _codes(gate.collect_findings(sandbox))


def test_licence_unknown_to_the_policy_blocks(sandbox: Path) -> None:
    registry = yaml.safe_load((sandbox / "manifests" / "licenses.yaml").read_text())
    registry["components"][2]["license"] = "SSPL-1.0"
    (sandbox / "manifests" / "licenses.yaml").write_text(
        yaml.safe_dump(registry), encoding="utf-8"
    )
    assert "LICENSE_NOT_ALLOWED" in _codes(gate.collect_findings(sandbox))


def test_one_denied_identifier_inside_a_compound_expression_blocks(sandbox: Path) -> None:
    registry = yaml.safe_load((sandbox / "manifests" / "licenses.yaml").read_text())
    registry["components"][2]["license"] = "MIT AND AGPL-3.0-only"
    (sandbox / "manifests" / "licenses.yaml").write_text(
        yaml.safe_dump(registry), encoding="utf-8"
    )
    assert "LICENSE_DENIED" in _codes(gate.collect_findings(sandbox))


def test_acknowledged_licence_does_not_block_but_is_named(tmp_path: Path, capsys) -> None:
    registry = yaml.safe_load(yaml.safe_dump(REGISTRY))
    registry["components"][2]["license"] = "LGPL-3.0-only"
    _write(tmp_path, registry=registry)
    assert gate.collect_findings(tmp_path) == []
    assert "LICENSE_ACKNOWLEDGED" in capsys.readouterr().out


def test_acknowledged_licence_without_a_written_reason_blocks(tmp_path: Path) -> None:
    policy = {
        "dependencies": POLICY["dependencies"],
        "licenses": {
            "allowed_spdx": ["MIT", "Apache-2.0"],
            "denied_spdx": [],
            "acknowledged_spdx": [{"id": "LGPL-3.0-only", "reason": "   "}],
        },
    }
    _write(tmp_path, policy=policy)
    assert "LICENSE_ACK_WITHOUT_REASON" in _codes(gate.collect_findings(tmp_path))


def test_role_change_in_the_lock_graph_is_reported(sandbox: Path) -> None:
    """Un paquet de test promu en dépendance runtime doit rouvrir la question."""
    (sandbox / "uv.lock").write_text(
        UV_LOCK.replace(
            'dependencies = [{ name = "libruntime" }]',
            'dependencies = [{ name = "libruntime" }, { name = "libtest" }]',
        ),
        encoding="utf-8",
    )
    assert "NOTICE_STALE" in _codes(gate.collect_findings(sandbox))


def test_hand_edited_notices_table_is_reported(sandbox: Path) -> None:
    path = sandbox / "THIRD_PARTY_NOTICES.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("| `widget` |", "| `widgets` |"), encoding="utf-8"
    )
    assert "NOTICE_STALE" in _codes(gate.collect_findings(sandbox))


def test_notices_document_without_the_generated_block_is_reported(sandbox: Path) -> None:
    (sandbox / "THIRD_PARTY_NOTICES.md").write_text("# Notices\n", encoding="utf-8")
    assert "NOTICE_MISSING_DOCUMENT" in _codes(gate.collect_findings(sandbox))


def test_missing_notices_document_is_reported(sandbox: Path) -> None:
    (sandbox / "THIRD_PARTY_NOTICES.md").unlink()
    assert "NOTICE_MISSING_DOCUMENT" in _codes(gate.collect_findings(sandbox))


def test_missing_registry_fails_closed(sandbox: Path) -> None:
    (sandbox / "manifests" / "licenses.yaml").unlink()
    with pytest.raises(SystemExit):
        gate.collect_findings(sandbox)


def test_missing_policy_fails_closed(sandbox: Path) -> None:
    (sandbox / "manifests" / "policy.yaml").unlink()
    with pytest.raises(SystemExit):
        gate.collect_findings(sandbox)


# ── Le dépôt réel doit satisfaire sa propre porte ──────────────────────────


def test_the_repository_itself_satisfies_the_notices_gate() -> None:
    findings = gate.collect_findings(_REPO_ROOT)
    assert findings == [], "\n".join(f.render() for f in findings)
