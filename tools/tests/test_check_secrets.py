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


def test_l_allowlist_ne_peut_pas_servir_de_cachette(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L'allowlist n'est pas scannée — mais une entrée dont la valeur
    n'apparaît nulle part ailleurs est rejetée comme exemption morte.
    Garer un secret dans l'allowlist est donc impossible : il faudrait qu'il
    existe aussi dans un vrai fichier, là où le relecteur le verrait."""
    cachette = tmp_path / "secret-allowlist.yaml"
    cachette.write_text(
        "allow:\n"
        "  - path: nulle/part.py\n"
        "    code: AWS_ACCESS_KEY\n"
        "    match: AKIAIOSFODNN7EXAMPLE\n"
        "    reason: tentative de dissimulation\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "ALLOWLIST_PATH", cachette)
    completed = subprocess.run(
        [sys.executable, "-c", "import sys; sys.exit(0)"], capture_output=True
    )
    assert completed.returncode == 0  # garde-fou de l'environnement de test

    # L'entrée n'est utilisée par aucun fichier réel du dépôt : la porte doit
    # refuser, en nommant l'exemption morte.
    allowlist = gate.load_allowlist()
    assert set(allowlist) == {"nulle/part.py:AWS_ACCESS_KEY:AKIAIOSFODNN7EXAMPLE"}
    # `main` compare les exemptions déclarées aux exemptions réellement
    # consommées ; ici aucune ne l'est.
    assert gate.main() == 1


# ── Contournements reproduits par le 4e audit adversarial ─────────────────
#
# Le détecteur ne couvrait que `NOM = "valeur"` : il ratait les formats de
# configuration DU DÉPÔT LUI-MÊME (JSON, YAML à clé quotée, valeur non quotée,
# `.env`, TOML), le suffixe `-sample` accolé à un vrai secret, la ligne longue
# et la phrase de passe en mots ordinaires. Ces tests figent leur fermeture.

_PROBE = "9f3Kd2Lm8Qz7Xv4Bn1Rt6Yw0Hs5Jp"  # SYNTHETIC, n'ouvre rien


@pytest.mark.parametrize(
    ("label", "path", "text"),
    [
        ("json clé quotée", "conf.json", f'  "api_key": "{_PROBE}",'),
        ("json compact", "conf.json", f'{{"client_secret":"{_PROBE}"}}'),
        ("yaml clé quotée", "conf.yaml", f'  "password": "{_PROBE}"'),
        ("yaml valeur nue", "conf.yaml", "password: R7h!qZ2mPx9Lw4Tv0Ab"),
        ("env valeur nue", ".env", "VERTEX_API_TOKEN=R7hqZ2mPx9Lw4Tv0AbCd"),
        ("toml valeur nue", "conf.toml", "client_secret = R7hqZ2mPx9Lw4Tv0AbCd"),
        ("suffixe -sample sur un vrai secret", "a.py", f'CLIENT_SECRET = "{_PROBE}-sample"'),
        ("au-delà de la colonne 4000", "a.py", "x" * 4200 + f' API_KEY = "{_PROBE}"'),
        ("phrase de passe en mots", "a.py", 'TWS_PASSWORD = "correcthorsebatterystaple"'),
    ],
)
def test_les_contournements_du_4e_audit_sont_fermes(label: str, path: str, text: str) -> None:
    codes = {finding.code for finding in gate.scan_text(path, text)}
    assert codes, label


@pytest.mark.parametrize(
    ("label", "path", "text"),
    [
        # Une valeur NUE dans du CODE est une expression, pas un secret.
        ("appel de fonction Python", "a.py", "session_token = build_session_token(user)"),
        ("attribut TypeScript", "a.ts", "const credential = await navigator.credentials.get()"),
        # Expansion shell « valeur requise » : c'est un message, pas un secret.
        ("garde-fou shell", "s.sh", ': "${VERTEX_BACKUP_PASSPHRASE:?VERTEX_BACKUP_PASSPHRASE requis}"'),
        ("référence compose", "compose.yaml", "  POSTGRES_PASSWORD: ${VERTEX_DB_PASSWORD:?requis}"),
        # Le nom désigne l'emplacement, l'identifiant ou l'empreinte, pas le secret.
        ("emplacement d'un secret", "m.yaml", "  secret_location: env:VERTEX_NEWS_API_TOKEN_PRIMARY"),
        ("identifiant", "a.py", 'credential_id = "0123456789abcdef0123456789abcdef"'),
        ("empreinte", "a.py", 'csrf_token_hash = "3b1f9c2e8d7a6b5c4d3e2f1a0b9c8d7e"'),
    ],
)
def test_aucun_faux_positif_sur_ces_formes(label: str, path: str, text: str) -> None:
    assert {f.code for f in gate.scan_text(path, text)} == set(), label


def test_une_ligne_longue_n_est_pas_signalee_deux_fois() -> None:
    """Le découpage avec recouvrement ne doit pas dupliquer un signalement."""
    line = "y" * 3900 + f' API_KEY = "{_PROBE}" ' + "y" * 3900
    findings = [f for f in gate.scan_text("a.py", line) if f.code == "HIGH_ENTROPY_ASSIGNMENT"]
    assert len(findings) == 1
