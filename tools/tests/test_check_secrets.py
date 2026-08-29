"""Preuve d'exécution de la porte `tools/check_secrets.py`.

Une porte de sécurité qui ne signale jamais rien est une porte fermée à clé
sur une pièce vide. Ces tests prouvent par exécution que chaque catégorie est
réellement détectée, ET qu'aucun motif légitime du dépôt ne l'est.

Périmètre prouvé ici : le comportement de `scan_text` et le fonctionnement de
l'allowlist. Ces tests ne prouvent PAS l'exhaustivité de la détection — un
secret d'une forme non listée passera (voir docs/99-status/DEBT.md).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE = _REPO_ROOT / "tools" / "check_secrets.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_secrets_gate", _GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _codes(text: str) -> set[str]:
    return {finding.code for finding in gate.scan_text("probe.txt", text)}


# Valeurs SYNTHETIC construites pour ce test : aucune n'ouvre quoi que ce soit.
@pytest.mark.parametrize(
    ("label", "text", "expected"),
    [
        ("clé privée", "-----BEGIN RSA PRIVATE KEY-----\nMIIE", "PRIVATE_KEY"),
        ("jeton GitHub", 'T = "ghp_' + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8" + '"', "GITHUB_TOKEN"),
        ("clé AWS", "aws_key: AKIAIOSFODNN7EXAMPLE", "AWS_ACCESS_KEY"),
        (
            "JWT",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpM",
            "JWT",
        ),
        (
            "DSN avec mot de passe",
            'DSN = "postgresql://vertex:R7h!qZ2mPx9Lw4Tv@db.internal:5432/vertex"',
            "DSN_PASSWORD",
        ),
        ("clé de fournisseur d'IA", 'k="sk-ant-api03-' + "z9Y8x7W6v5U4t3S2r1Q0p9O8" + '"', "ANTHROPIC_KEY"),
        (
            "affectation à forte entropie",
            'CLIENT_SECRET = "9f3Kd2Lm8Qz7Xv4Bn1Rt6Yw0Hs5Jp"',
            "HIGH_ENTROPY_ASSIGNMENT",
        ),
    ],
)
def test_chaque_categorie_est_reellement_detectee(label: str, text: str, expected: str) -> None:
    assert expected in _codes(text), label


@pytest.mark.parametrize(
    ("label", "text"),
    [
        ("référence d'environnement", 'API_KEY = "${VERTEX_API_KEY}"'),
        ("DSN d'exemple", 'url = "postgresql://vertex:CHANGE_ME@127.0.0.1:5432/vertex"'),
        ("lecture d'environnement", "SECRET = os.environ['VERTEX_SESSION_SECRET']"),
        ("prose française", "Le jeton de session est révocable et n'est jamais journalisé."),
        ("valeur à entropie nulle", 'password = "aaaaaaaaaaaaaaaaaaaa"'),
        ("gabarit", 'token = "{{ vault_token }}"'),
    ],
)
def test_aucun_faux_positif_sur_les_motifs_legitimes(label: str, text: str) -> None:
    assert _codes(text) == set(), label


def test_l_extrait_n_est_jamais_reproduit_dans_le_rapport() -> None:
    """Un journal de CI ne doit pas publier le secret qu'il dénonce."""
    secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    (finding,) = [f for f in gate.scan_text("probe.txt", f'T = "{secret}"') if f.code == "GITHUB_TOKEN"]
    rendered = finding.render()
    assert secret not in rendered
    assert "empreinte" in rendered


def test_la_porte_est_verte_sur_le_depot_suivi() -> None:
    """Exécution réelle : le dépôt tel qu'il est suivi par Git ne contient
    aucun secret vraisemblable non exempté, et aucune exemption morte."""
    completed = subprocess.run(
        [sys.executable, str(_GATE)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_l_allowlist_exige_un_motif_ecrit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Une exemption sans `reason` est refusée : pas d'exemption muette."""
    incomplete = tmp_path / "secret-allowlist.yaml"
    incomplete.write_text(
        "allow:\n  - path: a.py\n    code: JWT\n    match: x\n", encoding="utf-8"
    )
    monkeypatch.setattr(gate, "ALLOWLIST_PATH", incomplete)
    with pytest.raises(SystemExit) as raised:
        gate.load_allowlist()
    assert "reason" in str(raised.value)
