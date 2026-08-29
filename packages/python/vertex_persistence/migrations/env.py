"""Alembic environment for vertex_persistence.

The database URL is read from the environment — ``VERTEX_DATABASE_URL`` first,
then ``VERTEX_TEST_DATABASE_URL`` — or from ``config.attributes["sqlalchemy_url"]``
when a caller (tests, application bootstrap) passes it programmatically.
No DSN is ever hardcoded in the repository. Missing configuration fails
closed with a typed error.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Make the package importable when alembic runs from the CLI without the
# monorepo pythonpath (prepend_sys_path also covers this; belt and braces).
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vertex_persistence.errors import ConfigurationError  # noqa: E402
from vertex_persistence.models import Base  # noqa: E402

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    """Resolve the database URL fail-closed (attributes, then environment)."""
    programmatic = config.attributes.get("sqlalchemy_url")
    if programmatic:
        return str(programmatic)
    for variable in ("VERTEX_DATABASE_URL", "VERTEX_TEST_DATABASE_URL"):
        value = os.environ.get(variable)
        if value:
            return value
    raise ConfigurationError(
        "no database URL configured: set VERTEX_DATABASE_URL (or "
        "VERTEX_TEST_DATABASE_URL for tests) in the environment; DSNs are "
        "never stored in the repository"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script emission)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
