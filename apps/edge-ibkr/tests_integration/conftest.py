"""Fixtures d'intégration de l'edge IBKR : PostgreSQL réel, migrations réelles.

Mêmes conventions que ``apps/worker/tests_integration`` (motif réutilisé, ce
paquet n'est jamais modifié) : ``VERTEX_TEST_DATABASE_URL`` doit désigner une
base de test JETABLE et dédiée — le DSN n'est JAMAIS stocké dans le dépôt et
son absence échoue fermé. Chaque test repart d'un schéma ``public`` détruit
puis recréé, suivi d'un vrai ``alembic upgrade head``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

_ENV_VAR = "VERTEX_TEST_DATABASE_URL"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PERSISTENCE_DIR = _REPO_ROOT / "packages" / "python" / "vertex_persistence"
_ALEMBIC_INI = _PERSISTENCE_DIR / "alembic.ini"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get(_ENV_VAR)
    if not url:
        pytest.fail(
            f"{_ENV_VAR} n'est pas défini. Les tests d'intégration exigent une base "
            "PostgreSQL de test dédiée et jetable, par exemple : "
            f"export {_ENV_VAR}="
            "'postgresql+psycopg://<user>:<motdepasse>@127.0.0.1:5432/vertex_test'. "
            "Ne jamais la pointer vers une base réelle : le schéma public est "
            "détruit et recréé à chaque test.",
            pytrace=False,
        )
    return url


@pytest.fixture()
def alembic_config(database_url: str) -> Config:
    config = Config(str(_ALEMBIC_INI))
    config.attributes["sqlalchemy_url"] = database_url
    return config


@pytest.fixture()
def clean_database(database_url: str) -> Iterator[None]:
    admin = create_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        yield
    finally:
        admin.dispose()


@pytest.fixture()
def migrated_engine(
    clean_database: None, alembic_config: Config, database_url: str
) -> Iterator[Engine]:
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        engine.dispose()
