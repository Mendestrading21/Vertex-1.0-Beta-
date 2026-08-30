"""Integration fixtures: real PostgreSQL, real Alembic migrations.

Requires ``VERTEX_TEST_DATABASE_URL`` in the environment (a dedicated,
throwaway test database). The DSN is NEVER stored in the repository; tests
fail closed with a clear message when the variable is absent.

Environment note: the local development database is PostgreSQL 16 while the
production target is PostgreSQL 18 (ADR-006). Nothing in this schema uses a
16-only or 18-only feature, but the gap is real and must be revalidated on 18
before release (identity columns, JSONB, triggers, SKIP LOCKED and
``timestamptz`` semantics used here are stable across 16-18).

Isolation: every test function gets a freshly dropped and recreated ``public``
schema, then a real ``alembic upgrade head``. Slower than transaction
rollback, but it also exercises the migrations and the SQL triggers exactly as
production would run them.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

_ENV_VAR = "VERTEX_TEST_DATABASE_URL"
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_ALEMBIC_INI = _PACKAGE_DIR / "alembic.ini"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get(_ENV_VAR)
    if not url:
        pytest.fail(
            f"{_ENV_VAR} is not set. Integration tests need a dedicated, "
            "throwaway PostgreSQL test database, e.g.: "
            f"export {_ENV_VAR}="
            "'postgresql+psycopg://<user>:<password>@127.0.0.1:5432/vertex_test'. "
            "Never point it at a production database: the public schema is "
            "dropped and recreated for every test.",
            pytrace=False,
        )
    return url


@pytest.fixture()
def alembic_config(database_url: str) -> Config:
    config = Config(str(_ALEMBIC_INI))
    # Explicit programmatic URL — the sanctioned path for tests. env.py no
    # longer falls back on VERTEX_TEST_DATABASE_URL implicitly: outside this
    # fixture, targeting the throwaway test database requires an explicit
    # VERTEX_ALLOW_TEST_DB=1 opt-in (see vertex_persistence.dsn).
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
