"""DSN resolution for migrations: fail-closed, test DB only on explicit opt-in.

All DSN strings here are SYNTHETIC fixtures — no real credentials.
"""

from __future__ import annotations

import pytest

from vertex_persistence.dsn import (
    ALLOW_TEST_DB_ENV_VAR,
    DATABASE_URL_ENV_VAR,
    TEST_DATABASE_URL_ENV_VAR,
    resolve_migration_url,
)
from vertex_persistence.errors import ConfigurationError

_MAIN_DSN = "postgresql+psycopg://synthetic-main/db"
_TEST_DSN = "postgresql+psycopg://synthetic-test/db"


def test_env_var_names_are_the_documented_contract() -> None:
    assert DATABASE_URL_ENV_VAR == "VERTEX_DATABASE_URL"
    assert TEST_DATABASE_URL_ENV_VAR == "VERTEX_TEST_DATABASE_URL"
    assert ALLOW_TEST_DB_ENV_VAR == "VERTEX_ALLOW_TEST_DB"


def test_programmatic_url_wins_over_everything() -> None:
    environ = {DATABASE_URL_ENV_VAR: _MAIN_DSN, TEST_DATABASE_URL_ENV_VAR: _TEST_DSN}
    assert (
        resolve_migration_url(environ, programmatic="postgresql+psycopg://synthetic-prog/db")
        == "postgresql+psycopg://synthetic-prog/db"
    )


def test_normal_migrations_use_vertex_database_url() -> None:
    assert resolve_migration_url({DATABASE_URL_ENV_VAR: _MAIN_DSN}) == _MAIN_DSN


def test_main_url_wins_over_test_url_even_with_opt_in() -> None:
    environ = {
        DATABASE_URL_ENV_VAR: _MAIN_DSN,
        TEST_DATABASE_URL_ENV_VAR: _TEST_DSN,
        ALLOW_TEST_DB_ENV_VAR: "1",
    }
    assert resolve_migration_url(environ) == _MAIN_DSN


def test_test_url_alone_is_refused_without_explicit_opt_in() -> None:
    with pytest.raises(ConfigurationError, match="VERTEX_ALLOW_TEST_DB=1"):
        resolve_migration_url({TEST_DATABASE_URL_ENV_VAR: _TEST_DSN})


def test_test_url_refused_when_opt_in_has_any_other_value() -> None:
    for not_an_opt_in in ("0", "true", "yes", "", " 1"):
        with pytest.raises(ConfigurationError):
            resolve_migration_url(
                {TEST_DATABASE_URL_ENV_VAR: _TEST_DSN, ALLOW_TEST_DB_ENV_VAR: not_an_opt_in}
            )


def test_test_url_allowed_with_explicit_opt_in() -> None:
    environ = {TEST_DATABASE_URL_ENV_VAR: _TEST_DSN, ALLOW_TEST_DB_ENV_VAR: "1"}
    assert resolve_migration_url(environ) == _TEST_DSN


def test_no_configuration_fails_closed_with_clear_message() -> None:
    with pytest.raises(ConfigurationError, match="VERTEX_DATABASE_URL"):
        resolve_migration_url({})


def test_empty_env_values_are_treated_as_absent() -> None:
    with pytest.raises(ConfigurationError):
        resolve_migration_url(
            {DATABASE_URL_ENV_VAR: "", TEST_DATABASE_URL_ENV_VAR: ""}, programmatic=""
        )
