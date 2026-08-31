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
