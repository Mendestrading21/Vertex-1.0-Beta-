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


# ── Contournements reproduits par le 5e audit adversarial (P1-4) ──────────
#
# Trois défauts distincts, tous prouvés par exécution avant correctif :
#
# 1. Le lookahead d'exemption `(?!.*(?:_location|_path|…)\b)` balayait TOUTE
#    LA FIN DE LA LIGNE au lieu du seul nom capturé. Conséquence : la
#    détection dépendait de l'ORDRE DES CLÉS (`{"tenant_id":…,"client_secret":…}`
#    vu, l'ordre inverse non vu) et un simple commentaire de fin de ligne
#    mentionnant `data_dir` ou `bucket_name` désarmait la règle. Le JSON
#    minifié est précisément le format que le docstring dit viser.
# 2. Les scalaires blocs YAML (`password: |` / `password: >`, valeur portée
#    par les lignes suivantes) n'étaient jamais examinés.
# 3. `DSN_PASSWORD` ancrait le userinfo sur `[A-Za-z0-9._%-]+` : un `+`, une
#    virgule ou un `=` dans le nom d'utilisateur — tous admis par la RFC 3986 —
#    suffisaient à contourner la règle.

_P5 = "aB3xQ7zLmP2vRt9wYc4KdN6hJ1sF8gE5uZ0iO"  # SYNTHETIC, n'ouvre rien


def _codes_at(path: str, text: str) -> set[str]:
    return {finding.code for finding in gate.scan_text(path, text)}


@pytest.mark.parametrize(
    ("label", "path", "text"),
    [
        (
            "json minifié, secret en tête",
            "a.json",
            f'{{"client_secret": "{_P5}", "tenant_id": "x"}}',
        ),
        (
            "commentaire de fin de ligne YAML",
            "compose.yaml",
            f"  POSTGRES_PASSWORD: {_P5}   # voir data_dir",
        ),
        (
            "commentaire de fin de ligne Python",
            "settings.py",
            f'API_TOKEN = "{_P5}"  # bucket_name',
        ),
        ("scalaire bloc YAML replié", "config.yaml", f"password: >\n  {_P5}\n"),
        ("scalaire bloc YAML littéral", "config.yaml", f"password: |\n  {_P5}\n"),
        (
            "scalaire bloc YAML avec indicateur de coupe",
            "config.yaml",
            f"  client_secret: |-\n    {_P5}\n  autre: x\n",
        ),
        (
            "userinfo DSN contenant un +",
            "a.env",
            "postgresql://user+ro:S3cr3tP4ssw0rdXyz@db.invalid:5432/vertex",
        ),
        (
            "scalaire bloc YAML précédé d'un tag",
            "config.yaml",
            f"password: !!binary |\n  {_P5}\n",
        ),
        (
            "scalaire bloc YAML dans un élément de liste",
            "config.yaml",
            f"- api_key: |\n    {_P5}\n",
        ),
    ],
)
def test_les_contournements_du_5e_audit_sont_fermes(label: str, path: str, text: str) -> None:
    assert _codes_at(path, text), label


def test_la_detection_ne_depend_pas_de_l_ordre_des_cles() -> None:
    """Le même contenu doit être vu quelle que soit la position du secret.

    C'est l'invariant que le défaut P1-4 brisait : le lookahead d'exemption
    consommait la fin de la ligne, donc `{"tenant_id":…}` avant ou après
    `client_secret` changeait le verdict sur un contenu identique.
    """
    secret_en_second = _codes_at("a.json", f'{{"tenant_id": "x", "client_secret": "{_P5}"}}')
    secret_en_tete = _codes_at("a.json", f'{{"client_secret": "{_P5}", "tenant_id": "x"}}')
    assert secret_en_second == secret_en_tete
    assert secret_en_tete == {"HIGH_ENTROPY_ASSIGNMENT"}


def test_un_nom_exempte_ailleurs_sur_la_ligne_n_exempte_pas_le_secret() -> None:
    """Un nom d'emplacement présent sur la ligne ne couvre que LUI-MÊME."""
    codes = _codes_at(
        "conf.json",
        f'{{"api_key_file": "/etc/vertex/api_key.pem", "api_key": "{_P5}"}}',
    )
    assert codes == {"HIGH_ENTROPY_ASSIGNMENT"}


@pytest.mark.parametrize(
    ("label", "path", "text"),
    [
        # Le suffixe d'exemption garde tout son effet — sur le nom lui-même.
        (
            "emplacement suivi d'un commentaire",
            "conf.yaml",
            "  api_key_file: /etc/vertex/api_key.pem   # lu au démarrage",
        ),
        ("empreinte en JSON minifié", "conf.json", f'{{"csrf_token_hash": "{_P5}"}}'),
        # Scalaires blocs : la forme est reconnue, la donnée reste absente.
        ("bloc YAML portant une référence", "conf.yaml", "password: |\n  ${VERTEX_DB_PASSWORD}\n"),
        ("bloc YAML à entropie nulle", "conf.yaml", "password: |\n  aaaaaaaaaaaaaaaaaaaaaa\n"),
        (
            "bloc YAML sous un nom d'emplacement",
            "conf.yaml",
            "password_file: |\n  /run/secrets/vertex_db_password\n",
        ),
        (
            "bloc YAML dont le corps est absent",
            "conf.yaml",
            "password: |\nautre_cle: 1\n",
        ),
        # Un fichier de CODE n'a pas de scalaire bloc YAML : la ligne suivante
        # est du code, pas une valeur.
        (
            "deux-points suivi d'une barre en Python",
            "a.py",
            "password: str | None\nCONSTANTE = compute()\n",
        ),
        # La règle DSN élargie ne doit pas mordre sur des URL ordinaires.
        (
            "URL de documentation",
            "README.md",
            "Voir https://api.example.com/v1/quotes?symbol=AAPL&fields=bid,ask",
        ),
        (
            "userinfo DSN portant une référence",
            "a.env",
            "DATABASE_URL=postgresql://user+ro:${VERTEX_DB_PASSWORD}@db.invalid/vertex",
        ),
        # Régression des 73 faux positifs : une expression reste une expression,
        # même quand la ligne porte un commentaire.
        (
            "appel de fonction Python commenté",
            "a.py",
            "session_token = build_session_token(user)  # cf. token_store_path",
        ),
        (
            "expression TypeScript commentée",
            "a.ts",
            "const credential = await navigator.credentials.get()  // voir credential_id",
        ),
    ],
)
def test_aucun_faux_positif_sur_les_formes_du_5e_audit(label: str, path: str, text: str) -> None:
    assert _codes_at(path, text) == set(), label


@pytest.mark.parametrize(
    ("label", "path", "text", "code"),
    [
        (
            "scalaire bloc YAML",
            "config.yaml",
            f"password: |\n  {_P5}\n",
            "HIGH_ENTROPY_ASSIGNMENT",
        ),
        (
            "userinfo DSN élargi",
            "a.env",
            "postgresql://user+ro:S3cr3tP4ssw0rdXyz@db.invalid:5432/vertex",
            "DSN_PASSWORD",
        ),
    ],
)
def test_les_nouveaux_vecteurs_ne_reproduisent_pas_la_valeur(
    label: str, path: str, text: str, code: str
) -> None:
    """L'invariant « aucune valeur reproduite » vaut aussi pour ces chemins."""
    findings = [f for f in gate.scan_text(path, text) if f.code == code]
    assert findings, label
    for finding in findings:
        rendered = finding.render()
        assert finding.match not in rendered
        assert "empreinte" in rendered
        assert finding.match not in str(finding.label)


# ── 7e audit : les exemptions DÉSARMAIENT des noms canoniques ─────────────
#
# Un suffixe suffisait à faire passer un vrai secret : `client_secret` renommé
# `client_secret_ref` n'était plus regardé. L'exemption dépend désormais de ce
# que la VALEUR est, pas de ce que son nom prétend.

_SECRET_MATERIAL = "9f3b7d1c8a2e4056b1d9c7e3f5a80264"  # SYNTHETIC, n'ouvre rien


@pytest.mark.parametrize(
    ("label", "text"),
    [
        ("suffixe _id", f'api_key_id: "{_SECRET_MATERIAL}"'),
        ("suffixe _ref", f'client_secret_ref: "{_SECRET_MATERIAL}"'),
        ("suffixe _file", f'api_key_file: "{_SECRET_MATERIAL}"'),
        ("suffixe _path", f'token_path: "{_SECRET_MATERIAL}"'),
        ("suffixe _name", f'password_name: "{_SECRET_MATERIAL}"'),
    ],
)
def test_un_suffixe_ne_desarme_plus_un_nom_canonique(label: str, text: str) -> None:
    """De la matière secrète sous un nom rassurant reste de la matière."""
    assert {f.code for f in gate.scan_text("conf.yaml", text)}, label


@pytest.mark.parametrize(
    ("label", "path", "text"),
    [
        ("référence d'environnement", "m.yaml", "secret_location: env:VERTEX_NEWS_TOKEN"),
        ("emplacement décrit en mots", "m.yaml", "secret_location: operating_system_secret_store"),
        ("chemin", "c.yaml", "api_key_file: /run/secrets/api_key.txt"),
        ("nom de variable", "c.yaml", "password_env: VERTEX_DB_PASSWORD"),
        ("empreinte non réversible", "a.py", f'csrf_token_hash = "{_SECRET_MATERIAL}"'),
    ],
)
def test_une_vraie_reference_reste_silencieuse(label: str, path: str, text: str) -> None:
    """Anti-vacuité : l'exemption n'a pas disparu, elle est devenue exacte.

    Une empreinte reste exemptée sur son NOM : un hachage n'est pas
    réversible. Un emplacement ne l'est que si la valeur en est vraiment un —
    un chemin, une variable, une URI, ou des mots. Un secret n'est pas
    prononçable.
    """
    assert {f.code for f in gate.scan_text(path, text)} == set(), label


@pytest.mark.parametrize(
    "name", ["SIGNING_KEY", "ENCRYPTION_KEY", "HMAC_KEY", "SESSION_KEY", "MASTER_KEY"]
)
def test_les_cles_cryptographiques_sont_couvertes(name: str) -> None:
    """Leur nom ne contient ni « secret » ni « password », mais leur VALEUR
    est le secret."""
    assert {f.code for f in gate.scan_text("a.py", f'{name} = "{_SECRET_MATERIAL}"')}


def test_un_marqueur_accole_ne_desarme_pas_un_secret() -> None:
    """« synthetic » est le mot le plus courant du dépôt : l'accoler à un vrai
    secret le faisait passer pour un gabarit."""
    assert {f.code for f in gate.scan_text("c.yaml", 'client_secret: "9f3b7d1c8a2e4056b1d9c-synthetic"')}


@pytest.mark.parametrize(
    "value", ['"${VERTEX_API_KEY}"', '"{{ vault_token }}"', "CHANGE_ME", '"api-key-example"']
)
def test_un_vrai_gabarit_reste_silencieux(value: str) -> None:
    """Anti-vacuité : la nouvelle épreuve d'entropie ne s'applique qu'aux
    gabarits par MOT-marqueur, pas aux gabarits par FORME."""
    assert {f.code for f in gate.scan_text("c.yaml", f"api_key: {value}")} == set()
