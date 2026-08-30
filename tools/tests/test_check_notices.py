"""Preuve d'exécution du volet `notices` de la porte `release`.

Même discipline que pour `tools/check_policy.py` : une arborescence SYNTHETIC
conforme, puis la MÊME arborescence avec une violation injectée. Aucun réseau :
le mode `--refresh` (qui, lui, interroge PyPI et npm) n'est pas exercé ici ;
seule sa fonction de normalisation l'est, sur des chaînes littérales.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

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


# ── 9e audit : le registre n'était jamais confronté à sa source ──────────────
#
# Mesuré sur le dépôt réel : `sed -i '1340s/LGPL-3.0-only/MIT/'
# manifests/licenses.yaml` suivi de `sed -i '87s/LGPL-3.0-only/MIT/'
# THIRD_PARTY_NOTICES.md` transforme la licence de `psycopg` en MIT, et
# `python3 tools/check_notices.py` répond « OK ». Les trois contrôles hors
# ligne comparent le registre aux VERROUS et les notices au REGISTRE ; aucun ne
# regarde la source. `--verify` la regarde.


def _sources(**licences: str) -> Callable[..., tuple[str, str]]:
    """Faux distributeur : rend la licence publiée, sans réseau."""

    def _fetch(component: Any, wheel_url: str | None = None) -> tuple[str, str]:
        cle = f"{component.ecosystem}:{component.name}"
        return licences.get(cle, "UNKNOWN"), f"https://source.invalid/{component.name}"

    return _fetch


_SOURCES_HONNETES = {
    "python:libruntime": "Apache-2.0",
    "python:libtest": "MIT",
    "javascript:widget": "MIT",
    "javascript:linter": "MIT",
}


def test_verify_est_vert_quand_le_registre_dit_la_verite(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anti-vacuité du test suivant : sans ce contrôle positif, un `--verify`
    qui échouerait toujours passerait pour une porte qui marche."""
    monkeypatch.setattr(gate, "fetch_license", _sources(**_SOURCES_HONNETES))
    assert gate.verify(sandbox, POLICY, require_network=True) == 0


def test_verify_refuse_une_licence_reecrite_a_la_main(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """LE reproducteur : le blanchiment LGPL → MIT, rejoué en bac à sable."""
    blanchi = {
        "schema_version": 1,
        "components": [
            dict(entry, license="MIT" if entry["name"] == "libruntime" else entry["license"])
            for entry in REGISTRY["components"]
        ],
    }
    _write(sandbox, registry=blanchi)
    # Le contrôle HORS LIGNE reste vert : registre, verrous et notices sont
    # cohérents entre eux. C'est exactement le trou mesuré.
    assert gate.collect_findings(sandbox) == [], (
        "le contrôle hors ligne doit rester vert ici — sinon ce test ne "
        "démontrerait pas que `--verify` apporte quelque chose"
    )

    monkeypatch.setattr(gate, "fetch_license", _sources(**_SOURCES_HONNETES))
    assert gate.verify(sandbox, POLICY, require_network=True) == 1
    rapporte = capsys.readouterr().err
    assert "libruntime" in rapporte
    assert "Apache-2.0" in rapporte, "le rapport doit nommer la licence réelle"
    assert "MIT" in rapporte, "le rapport doit nommer la licence déclarée"


def test_verify_signale_un_registre_injoignable_sans_echouer(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sans `--require-network`, une panne de registre ne rend pas la CI rouge.

    C'est un choix, écrit ici pour qu'il ne se perde pas : une porte qui rougit
    à chaque incident PyPI est débranchée dans la semaine, et c'est ainsi que
    les quatre contournements de cette session ont commencé.
    """
    monkeypatch.setattr(gate, "fetch_license", _sources())  # tout injoignable
    assert gate.verify(sandbox, POLICY, require_network=False) == 0
    assert "injoignable" in capsys.readouterr().err


def test_verify_echoue_sur_un_registre_injoignable_en_mode_strict(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L'exécution nocturne, elle, doit voir l'indisponibilité."""
    monkeypatch.setattr(gate, "fetch_license", _sources())
    assert gate.verify(sandbox, POLICY, require_network=True) == 1


def test_verify_n_ecrit_rien(sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`--refresh` réécrit, `--verify` compare. Confondre les deux ferait
    qu'une divergence se corrigerait toute seule au lieu d'être signalée."""
    registre = (sandbox / "manifests" / "licenses.yaml").read_text(encoding="utf-8")
    notices = (sandbox / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    monkeypatch.setattr(gate, "fetch_license", _sources(**_SOURCES_HONNETES))
    gate.verify(sandbox, POLICY, require_network=True)
    assert (sandbox / "manifests" / "licenses.yaml").read_text(encoding="utf-8") == registre
    assert (sandbox / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8") == notices


def test_refresh_et_verify_sont_exclusifs() -> None:
    """`--refresh --verify` réécrirait puis comparerait au résultat de la
    réécriture : toujours vert, jamais informatif."""
    with pytest.raises(SystemExit) as leve:
        gate.main(["--refresh", "--verify"])
    assert "--verify" in str(leve.value)
