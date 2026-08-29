"""API integration fixtures: real PostgreSQL, real migrations, soft passkey.

Requires ``VERTEX_TEST_DATABASE_URL`` (dedicated throwaway database) exactly
like the persistence integration suite; the DSN never lives in the
repository and tests fail closed when it is absent.

``SoftPasskey`` is an explicitly SYNTHETIC software authenticator (ES256,
attestation ``none``) that performs the real WebAuthn ceremonies against the
API so the whole chain — options, browser-side response shape, py_webauthn
verification, storage, cookies, CSRF — is exercised without any hardware. It
never crosses a production boundary.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from soft_passkey import SoftPasskey
from vertex_api.app import create_app

_ENV_VAR = "VERTEX_TEST_DATABASE_URL"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _REPO_ROOT / "packages" / "python" / "vertex_persistence" / "alembic.ini"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get(_ENV_VAR)
    if not url:
        pytest.fail(
            f"{_ENV_VAR} is not set. API integration tests need the dedicated, "
            "throwaway PostgreSQL test database (its public schema is dropped "
            "for every test). DSNs are never stored in the repository.",
            pytrace=False,
        )
    return url


@pytest.fixture()
def migrated_database(database_url: str) -> Iterator[None]:
    """Fresh public schema migrated to head by real Alembic for each test."""
    admin = create_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        admin.dispose()
    config = Config(str(_ALEMBIC_INI))
    config.attributes["sqlalchemy_url"] = database_url
    command.upgrade(config, "head")
    yield


@pytest.fixture()
def client(
    migrated_database: None, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """Client on a real app wired to the migrated test database.

    ``VERTEX_AUTH_COOKIE_INSECURE_DEV=1`` is the documented loopback-dev
    opt-out: the test client speaks plain http, and the standard cookie jar
    refuses to send ``Secure`` cookies over http (which is exactly what the
    flag exists for). The default-``Secure`` behavior is asserted separately.
    """
    monkeypatch.setenv("VERTEX_DATABASE_URL", database_url)
    monkeypatch.delenv("VERTEX_AUTH_DEV_ORIGIN_PORTS", raising=False)
    monkeypatch.setenv("VERTEX_AUTH_COOKIE_INSECURE_DEV", "1")
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def secure_client(
    migrated_database: None, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """Client with the DEFAULT cookie config (Secure on): header assertions."""
    monkeypatch.setenv("VERTEX_DATABASE_URL", database_url)
    monkeypatch.delenv("VERTEX_AUTH_DEV_ORIGIN_PORTS", raising=False)
    monkeypatch.delenv("VERTEX_AUTH_COOKIE_INSECURE_DEV", raising=False)
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def passkey() -> SoftPasskey:
    """A fresh SYNTHETIC software authenticator per test."""
    return SoftPasskey()
