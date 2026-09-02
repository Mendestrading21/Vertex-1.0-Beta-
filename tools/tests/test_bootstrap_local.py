"""Preuve d'exécution du premier démarrage local.

`tools/bootstrap_local.py` et `tools/start_local.sh` sont la moitié manquante
du produit : la pile démarrait en CI depuis l'échafaudage Playwright et jamais
pour son utilisateur. Ces tests vérifient les deux choses qui, ratées, feraient
plus de mal que l'absence de démarrage :

1. le bootstrap **ne détruit rien** et **refuse** d'écraser un journal ;
2. le démarreur n'écoute **que** sur la boucle locale.

Les tests qui touchent la base exigent PostgreSQL réel et sont sautés sinon —
un test sauté qui prétend prouver quelque chose serait pire qu'aucun test.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP = _REPO_ROOT / "tools" / "bootstrap_local.py"
_START = _REPO_ROOT / "tools" / "start_local.sh"


def _load_bootstrap() -> Any:
    spec = importlib.util.spec_from_file_location("bootstrap_local_tool", _BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = _load_bootstrap()


# ── 1. Le démarreur n'expose rien ────────────────────────────────────────────


def _script() -> str:
    return _START.read_text(encoding="utf-8")


def test_le_demarreur_n_ecoute_que_sur_la_boucle_locale() -> None:
    """`.claude/rules/security.md` : l'API locale n'est jamais exposée.

    Un `--host 0.0.0.0` publierait l'API et l'interface sur le réseau du
    logement. Ce test lit les hôtes RÉELLEMENT passés, pas l'intention.
    """
    hotes = re.findall(r"--host\s+(\S+)", _script())
    assert hotes, "aucun `--host` trouvé : le balayage est devenu aveugle"
    non_loopback = [h for h in hotes if h != "127.0.0.1"]
    assert non_loopback == [], (
        f"ces services écouteraient hors de la boucle locale : {non_loopback}"
    )


def test_le_demarreur_refuse_de_deviner_une_base() -> None:
    """Sans DSN, il s'arrête au lieu d'inventer une base."""
    environnement = {
        cle: valeur
        for cle, valeur in os.environ.items()
        if cle not in ("VERTEX_DATABASE_URL", "VERTEX_TEST_DATABASE_URL")
    }
    resultat = subprocess.run(  # noqa: S603 - argv littéral, script du dépôt
        ["/bin/bash", str(_START)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        cwd=_REPO_ROOT,
        env=environnement,
    )
    assert resultat.returncode == 2, resultat.stdout + resultat.stderr
    assert "VERTEX_DATABASE_URL" in resultat.stderr


def test_le_demarreur_utilise_lenvironnement_python_verrouille() -> None:
    """Le poste ne doit jamais retomber silencieusement sur le Python système."""
    script = _script()
    assert 'PYTHON="${RACINE}/.venv/bin/python"' in script
    assert '"${PYTHON}" -m uvicorn' in script
    assert '"${PYTHON}" -m vertex_worker' in script
    assert "python3 -m uvicorn" not in script
    assert "python3 -m vertex_worker" not in script


def test_la_chute_dun_service_arrete_toute_la_pile() -> None:
    """Une interface survivante sur une API morte serait trompeuse."""
    script = _script()
    assert 'wait -n "${PIDS[@]}"' in script
    assert "arrêt coordonné de la pile" in script


def _lignes_de_code(chemin: Path) -> list[str]:
    """Lignes exécutables : commentaires et docstrings écartés.

    Sans cela le balayage lirait les phrases qui expliquent qu'on ne détruit
    RIEN, et échouerait sur sa propre documentation.
    """
    lignes: list[str] = []
    dans_docstring = False
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        nue = ligne.strip()
        if nue.count('"""') == 1:
            dans_docstring = not dans_docstring
            continue
        if dans_docstring or nue.startswith("#") or not nue:
            continue
        lignes.append(ligne.split("  #")[0])
    return lignes


def test_le_demarreur_ne_detruit_aucun_schema() -> None:
    """Le `DROP SCHEMA` appartient aux fixtures de test, sur base jetable.

    Ici la base peut contenir le journal de l'utilisateur : une destruction
    serait irréversible et silencieuse.
    """
    code = _lignes_de_code(_START) + _lignes_de_code(_BOOTSTRAP)
    assert len(code) > 40, "le découpage ne voit presque rien : balayage aveugle"
    for interdit in ("DROP SCHEMA", "DROP DATABASE", "TRUNCATE"):
        coupables = [
            ligne for ligne in code if re.search(interdit, ligne, re.IGNORECASE)
        ]
        assert coupables == [], (
            f"une instruction {interdit} exécutable existe dans le chemin de "
            f"démarrage : {coupables}"
        )


# ── 2. Le bootstrap, sur PostgreSQL réel ─────────────────────────────────────


def _dsn_administrateur() -> str | None:
    """DSN d'une base jetable, dérivé de celui des tests d'intégration."""
    return os.environ.get("VERTEX_TEST_DATABASE_URL")


besoin_postgres = pytest.mark.skipif(
    _dsn_administrateur() is None,
    reason="VERTEX_TEST_DATABASE_URL absent : PostgreSQL réel requis",
)


@pytest.fixture
def base_jetable() -> Any:
    """Crée une base VIDE et la supprime après le test."""
    modele = _dsn_administrateur()
    assert modele is not None
    url = make_url(modele)
    nom = f"vertex_boot_{uuid.uuid4().hex[:10]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{nom}"'))
    finally:
        admin.dispose()
    try:
        # `str(URL)` masque le mot de passe par `***` : le rendu explicite
        # est obligatoire, sinon la connexion échoue à l'authentification.
        yield url.set(database=nom).render_as_string(hide_password=False)
    finally:
        admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
        try:
            with admin.connect() as connection:
                connection.execute(
                    text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)')
                )
        finally:
            admin.dispose()


def _executer(dsn: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv littéral, script du dépôt
        [sys.executable, str(_BOOTSTRAP), *arguments],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
        cwd=_REPO_ROOT,
        env={**os.environ, "VERTEX_DATABASE_URL": dsn},
    )


@besoin_postgres
def test_une_base_vide_devient_migree(base_jetable: str) -> None:
    resultat = _executer(base_jetable)
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "migrations" in resultat.stdout

    engine = create_engine(base_jetable)
    try:
        with engine.connect() as connection:
            tables = connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            ).scalar_one()
    finally:
        engine.dispose()
    assert tables > 5, f"seulement {tables} tables après migration"


@besoin_postgres
def test_relancer_le_bootstrap_est_sans_effet(base_jetable: str) -> None:
    """Idempotence : le runbook peut être rejoué sans conséquence."""
    assert _executer(base_jetable).returncode == 0
    second = _executer(base_jetable)
    assert second.returncode == 0, second.stdout + second.stderr


@besoin_postgres
def test_le_semis_refuse_d_ecraser_un_journal_utilisateur(base_jetable: str) -> None:
    """LA garde qui compte : le journal est saisi à la main, il est irremplaçable."""
    assert _executer(base_jetable, "--with-demo-data").returncode == 0

    engine = create_engine(base_jetable)
    try:
        with engine.connect() as connection:
            lignes = connection.execute(
                text("SELECT count(*) FROM ledger_transactions")
            ).scalar_one()
    finally:
        engine.dispose()
    assert lignes > 0, "le semis n'a rien écrit : le refus suivant ne prouverait rien"

    refus = _executer(base_jetable, "--with-demo-data")
    assert refus.returncode == 2, refus.stdout + refus.stderr
    assert "données utilisateur" in refus.stderr
    assert "ledger_transactions" in refus.stderr


@besoin_postgres
def test_le_semis_publie_une_population_synthetic(base_jetable: str) -> None:
    """Un semis qui n'affiche rien ne rend pas le produit opérationnel.

    On vérifie que des snapshots sont RÉELLEMENT publiés — sinon les 13 pages
    seraient vides, ce que le semis existe précisément pour éviter.
    """
    resultat = _executer(base_jetable, "--with-demo-data")
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "SYNTHETIC" in resultat.stdout

    engine = create_engine(base_jetable)
    try:
        with engine.connect() as connection:
            kinds = connection.execute(
                text("SELECT DISTINCT kind FROM snapshot_heads")
            ).scalars().all()
    finally:
        engine.dispose()
    # Les DIX familles publiées par le semis : si l'une manque, une page
    # entière est vide alors que l'utilisateur croit voir le produit.
    attendues = {
        "analysis",
        "attention",
        "calendar",
        "capabilities",
        "markets_overview",
        "opportunities",
        "option_chain",
        "performance",
        "portfolio_valuation",
        "review_queue",
    }
    manquantes = attendues - set(kinds)
    assert manquantes == set(), (
        f"ces familles de snapshot ne sont pas publiées : {sorted(manquantes)} — "
        "les pages correspondantes seraient vides"
    )


# ── 3. Les runbooks disent-ils ce que le démarreur fait RÉELLEMENT ? ─────────
#
# Ces trois gardes existent parce que la documentation et le démarreur avaient
# DIVERGÉ sans qu'aucune mesure ne le voie. Le script avait raison ; les
# runbooks avaient tort ; et c'est le runbook que l'utilisateur lit.

_RUNBOOKS = sorted((_REPO_ROOT / "docs" / "08-runbooks").glob("*.md"))
_PASSATION = _REPO_ROOT / "docs" / "08-runbooks" / "REPRENDRE_ICI.md"

#: Une URL d'interface À OUVRIR : schéma, IP de boucle, port, puis un chemin de
#: page. Le motif exige le chemin, ce qui distingue « ouvrir cette page » de
#: « le service ÉCOUTE sur 127.0.0.1:4173 » — la seconde est correcte et doit
#: rester telle quelle.
_URL_A_OUVRIR = re.compile(r"http://127\.0\.0\.1:\d+/(?!api/)\S*")


def test_aucun_runbook_n_envoie_le_navigateur_sur_l_adresse_ip() -> None:
    """`auth/config.py` fixe le RP ID WebAuthn à `localhost`.

    La spécification WebAuthn exige que le RP ID soit un suffixe de domaine
    enregistrable de l'origine. Une origine en ADRESSE IP ne peut donc pas
    porter le RP ID `localhost`. Séquence réelle (`AuthPage.tsx:60,64,68`) :
    `/api/v1/auth/register/options` est appelé et répond, PUIS
    `navigator.credentials.create` échoue dans le navigateur, avant
    `/register/verify` ; un message générique d'échec apparaît.

    `tools/start_local.sh` imprime la bonne URL et l'explique. Les runbooks,
    eux, envoyaient tous sur `http://127.0.0.1:4173/...`. Cette garde interdit
    la rechute, et l'ancre sur l'hôte que la campagne e2e — la seule qui crée
    RÉELLEMENT une passkey, via CDP — utilise pour le navigateur.
    """
    assert _RUNBOOKS, "aucun runbook trouvé : le balayage est devenu aveugle"

    # L'ancre : la campagne qui exerce la passkey vise `localhost` pour le
    # navigateur et l'IP pour l'API. Les runbooks doivent dire la même chose.
    config_e2e = (_REPO_ROOT / "apps" / "web" / "playwright.config.ts").read_text(
        encoding="utf-8"
    )
    assert "WEB_BASE_URL = 'http://localhost:" in config_e2e, (
        "la campagne e2e ne vise plus `localhost` pour le navigateur : cette "
        "garde et les runbooks reposent sur cet ancrage, le revérifier"
    )

    coupables: list[str] = []
    for runbook in _RUNBOOKS:
        for ligne_no, ligne in enumerate(
            runbook.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for url in _URL_A_OUVRIR.findall(ligne):
                coupables.append(f"{runbook.name}:{ligne_no} → {url}")
    assert coupables == [], (
        "ces runbooks envoient le navigateur sur l'adresse IP, où la création "
        "de passkey est refusée par le navigateur lui-même (RP ID `localhost`, "
        f"apps/api/src/vertex_api/auth/config.py) : {coupables}. "
        "Utiliser `http://localhost:<port>/...`. L'adresse d'ÉCOUTE, elle, "
        "reste 127.0.0.1 et n'est pas concernée."
    )


def test_la_passation_nomme_le_demarreur_au_lieu_de_le_reinventer() -> None:
    """Une passation qui ne nomme pas le lanceur ne permet pas de REGARDER.

    `REPRENDRE_ICI.md` avait décrit une séquence de démarrage à lui, plus
    courte et fausse, sans jamais citer `tools/start_local.sh` — un second
    chemin d'autorité, que `.claude/rules/architecture.md` interdit.
    """
    texte = _PASSATION.read_text(encoding="utf-8")
    assert "tools/start_local.sh" in texte, (
        "REPRENDRE_ICI.md ne nomme pas `tools/start_local.sh` : la session "
        "suivante ne saurait pas comment lancer et regarder le logiciel"
    )
    assert "START_LOCAL.md" in texte, (
        "REPRENDRE_ICI.md doit DÉLÉGUER le démarrage à START_LOCAL.md plutôt "
        "que de le dupliquer"
    )


def test_aucun_runbook_n_appelle_le_bootstrap_avec_le_python_systeme() -> None:
    """`start_local.sh` REFUSE le Python système ; les runbooks doivent suivre.

    Un `python tools/bootstrap_local.py` documenté échoue ou, pire, réussit
    sur un interpréteur non verrouillé — deux jeux de dépendances pour un
    seul produit.
    """
    motif = re.compile(r"(?<![\w/])python3?\s+tools/(bootstrap_local\.py|start_local)")
    coupables: list[str] = []
    for runbook in _RUNBOOKS:
        for ligne_no, ligne in enumerate(
            runbook.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if motif.search(ligne):
                coupables.append(f"{runbook.name}:{ligne_no} → {ligne.strip()}")
    assert coupables == [], (
        "ces runbooks invoquent le bootstrap par un Python non verrouillé, que "
        f"`tools/start_local.sh` refuse : {coupables}. Utiliser "
        "`.venv/bin/python`."
    )


#: Formulations FAUSSES sur la cérémonie WebAuthn, interdites dans les runbooks.
#: Tracé dans le code (`AuthPage.tsx:60,64,68`, `client.ts:287-298`,
#: `routes.py:192-216`) : depuis une origine en adresse IP,
#: `POST /api/v1/auth/register/options` EST appelé et répond 200 avec
#: `rp.id = "localhost"` ; c'est `navigator.credentials.create` qui échoue
#: ensuite, dans le navigateur, avant `/register/verify`. Et un message
#: générique d'échec APPARAÎT (`AuthPage.tsx:88-93`), qui accuse à tort un
#: 401 serveur. Dire « avant d'appeler l'API » ou « aucun message de Vertex »
#: est donc faux, et l'a été dans quatre fichiers.
_FORMULATIONS_FAUSSES_WEBAUTHN = (
    re.compile(r"avant\s+(?:même\s+)?d['’]appeler\s+l['’]API", re.IGNORECASE),
    re.compile(r"aucun\s+appel\s+(?:à\s+l['’])?API", re.IGNORECASE),
    re.compile(r"aucun\s+message\s+(?:d['’]erreur\s+)?de\s+Vertex", re.IGNORECASE),
)


def test_aucun_runbook_ne_pretend_que_l_api_n_est_pas_appelee() -> None:
    """La séquence réelle : `/register/options` répond, PUIS `create` échoue.

    Une version antérieure de ces runbooks affirmait que le navigateur refusait
    la passkey « avant d'appeler l'API » et qu'« aucun message de Vertex »
    n'apparaissait. Les deux sont faux (voir `_FORMULATIONS_FAUSSES_WEBAUTHN`).
    Test DOCUMENTAIRE : il lit des fichiers Markdown, il ne pilote aucun
    navigateur et ne prétend pas reproduire le refus WebAuthn.
    """
    assert _RUNBOOKS, "aucun runbook trouvé : le balayage est devenu aveugle"
    coupables: list[str] = []
    for runbook in _RUNBOOKS:
        for ligne_no, ligne in enumerate(
            runbook.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for motif in _FORMULATIONS_FAUSSES_WEBAUTHN:
                for trouve in motif.findall(ligne):
                    coupables.append(f"{runbook.name}:{ligne_no} → « {trouve} »")
    assert coupables == [], (
        "ces runbooks décrivent faussement la cérémonie WebAuthn : "
        f"{coupables}. Séquence réelle : `/api/v1/auth/register/options` est "
        "appelé et répond ; `navigator.credentials.create` échoue ensuite dans "
        "le navigateur, avant `/register/verify` ; un message générique "
        "d'échec apparaît (AuthPage.tsx)."
    )
