"""Worker integration fixtures: real PostgreSQL, real Alembic migrations.

Same conventions as ``packages/python/vertex_persistence/tests_integration``
(reused pattern, that package is never modified): ``VERTEX_TEST_DATABASE_URL``
must point at a dedicated, throwaway test database (the DSN is NEVER stored
in the repository; absence fails closed), every test function gets a freshly
dropped and recreated ``public`` schema, then a real ``alembic upgrade head``
run from the ``vertex_persistence`` package (owner of the migrations).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

_ENV_VAR = "VERTEX_TEST_DATABASE_URL"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PERSISTENCE_DIR = _REPO_ROOT / "packages" / "python" / "vertex_persistence"
_ALEMBIC_INI = _PERSISTENCE_DIR / "alembic.ini"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get(_ENV_VAR)
    if not url:
        pytest.fail(
            f"{_ENV_VAR} is not set. Integration tests need a dedicated, "
            "throwaway PostgreSQL test database, e.g.: "
            f"export {_ENV_VAR}='postgresql+psycopg://<user>:<password>@127.0.0.1:5432/vertex_test'. "
            "Never point it at a production database: the public schema is "
            "dropped and recreated for every test.",
            pytrace=False,
        )
    return url


@pytest.fixture()
def alembic_config(database_url: str) -> Config:
    config = Config(str(_ALEMBIC_INI))
    # Explicit programmatic URL — the sanctioned path for tests (see the
    # vertex_persistence integration conftest).
    config.attributes["sqlalchemy_url"] = database_url
    return config


@pytest.fixture()
def clean_database(database_url: str) -> Iterator[None]:
    """Drop and recreate the public schema so each test starts from nothing."""
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
    """Yield an engine on a database migrated to head by real Alembic."""
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as session:
        yield session


@pytest.fixture()
def session_factory(migrated_engine: Engine):
    """Session factory for the worker runner (one Session per transaction)."""

    def factory() -> Session:
        return Session(migrated_engine)

    return factory
