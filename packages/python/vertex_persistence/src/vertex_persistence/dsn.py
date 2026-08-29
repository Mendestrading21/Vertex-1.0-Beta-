"""Fail-closed database DSN resolution for Alembic migrations and tooling.

No DSN is ever hardcoded in the repository. Resolution order:

1. a programmatic URL passed by the caller (tests, application bootstrap) —
   an explicit, code-level choice that always wins;
2. ``VERTEX_DATABASE_URL`` — the normal migration target;
3. ``VERTEX_TEST_DATABASE_URL`` — accepted **only** when
   ``VERTEX_ALLOW_TEST_DB=1`` is exported explicitly. A test DSN lying around
   in the environment must never silently become a migration target: the test
   database is throwaway (its schema is dropped by the integration fixtures),
   so falling back to it implicitly could run production migrations against a
   disposable database or vice versa.

Anything else raises :class:`~vertex_persistence.errors.ConfigurationError`.
"""

from __future__ import annotations

from typing import Mapping, Optional

from vertex_persistence.errors import ConfigurationError

__all__ = [
    "DATABASE_URL_ENV_VAR",
    "TEST_DATABASE_URL_ENV_VAR",
    "ALLOW_TEST_DB_ENV_VAR",
    "resolve_migration_url",
]

DATABASE_URL_ENV_VAR = "VERTEX_DATABASE_URL"
TEST_DATABASE_URL_ENV_VAR = "VERTEX_TEST_DATABASE_URL"
ALLOW_TEST_DB_ENV_VAR = "VERTEX_ALLOW_TEST_DB"


def resolve_migration_url(
    environ: Mapping[str, str], *, programmatic: Optional[str] = None
) -> str:
    """Resolve the migration DSN fail-closed (see module docstring).

    Empty strings — programmatic or environment — count as absent, never as a
    configured value.
    """
    if programmatic:
        return str(programmatic)

    main_url = environ.get(DATABASE_URL_ENV_VAR)
    if main_url:
        return main_url

    test_url = environ.get(TEST_DATABASE_URL_ENV_VAR)
    if test_url:
        if environ.get(ALLOW_TEST_DB_ENV_VAR) == "1":
            return test_url
        raise ConfigurationError(
            f"{TEST_DATABASE_URL_ENV_VAR} is set but {DATABASE_URL_ENV_VAR} is "
            "not: refusing to run migrations against the test database "
            f"implicitly. Set {DATABASE_URL_ENV_VAR} for normal migrations, or "
            f"export {ALLOW_TEST_DB_ENV_VAR}=1 to explicitly target the "
            "throwaway test database."
        )

    raise ConfigurationError(
        f"no database URL configured: set {DATABASE_URL_ENV_VAR} in the "
        f"environment (or {TEST_DATABASE_URL_ENV_VAR} together with "
        f"{ALLOW_TEST_DB_ENV_VAR}=1 for the throwaway test database); DSNs "
        "are never stored in the repository"
    )
