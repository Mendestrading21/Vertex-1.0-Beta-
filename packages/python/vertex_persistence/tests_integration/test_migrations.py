"""Migration integrity: upgrade -> downgrade -> upgrade without drift.

The base downgrade is DESTRUCTIVE (it drops the append-only ledger and the
observations); it must refuse to run on a populated database unless
``VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE=1`` is exported explicitly.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from vertex_persistence.models import Base

_SYNTHETIC_OBSERVATION_SQL = (
    "INSERT INTO observations (event_id, schema_version, source, received_at,"
    " as_of, stale_after, quality_status, delay_status, rights, payload,"
    " payload_hash) VALUES ('evt-guard', '1', 'SYNTHETIC_TEST', now(), now(),"
    " now(), 'VALID', 'LIVE', 'X', '{}'::jsonb, 'sha256:0')"
)
_SYNTHETIC_LEDGER_SQL = (
    "INSERT INTO portfolios (name, base_currency) VALUES ('synthetic', 'USD');"
    "INSERT INTO ledger_transactions (portfolio_id, kind, amount, currency,"
    " fees, effective_at, recorded_at) SELECT id, 'DEPOSIT', 1, 'USD', 0,"
    " now(), now() FROM portfolios WHERE name = 'synthetic'"
)

_SCHEMA_SQL = {
    "columns": """
        SELECT table_name, column_name, data_type, is_nullable,
               COALESCE(identity_generation, ''), COALESCE(column_default, '')
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, column_name
    """,
    "constraints": """
        SELECT table_name, constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND constraint_name NOT LIKE '%_not_null'
        ORDER BY table_name, constraint_name
    """,
    "indexes": """
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """,
    "triggers": """
        SELECT event_object_table, trigger_name, event_manipulation, action_statement
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        ORDER BY event_object_table, trigger_name, event_manipulation
    """,
    "checks": """
        SELECT tc.table_name, tc.constraint_name, cc.check_clause
        FROM information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc
          ON cc.constraint_schema = tc.constraint_schema
         AND cc.constraint_name = tc.constraint_name
        WHERE tc.table_schema = 'public' AND tc.constraint_type = 'CHECK'
          AND tc.constraint_name NOT LIKE '%_not_null'
        ORDER BY tc.table_name, tc.constraint_name
    """,
}


def _schema_fingerprint(engine: Engine) -> dict[str, list[tuple]]:
    with engine.connect() as connection:
        return {
            name: [tuple(row) for row in connection.execute(text(sql))]
            for name, sql in _SCHEMA_SQL.items()
        }


def _table_names(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        return {row[0] for row in rows}


def test_upgrade_downgrade_upgrade_without_drift(
    clean_database: None, alembic_config: Config, database_url: str
) -> None:
    engine = create_engine(database_url)
    try:
        command.upgrade(alembic_config, "head")
        first = _schema_fingerprint(engine)
        assert _table_names(engine) == {
            "alembic_version",
            "observations",
            "snapshots",
            "snapshot_heads",
            "outbox",
            "portfolios",
            "position_lots",
            "ledger_transactions",
            "webauthn_credentials",
            "auth_sessions",
            "theses",
            "thesis_revisions",
        }

        command.downgrade(alembic_config, "base")
        assert _table_names(engine) == {"alembic_version"}
        with engine.connect() as connection:
            leftover = connection.execute(
                text("SELECT count(*) FROM pg_proc WHERE proname = 'vertex_forbid_mutation'")
            ).scalar()
        assert leftover == 0  # downgrade removes the trigger function too

        command.upgrade(alembic_config, "head")
        second = _schema_fingerprint(engine)
        assert first == second  # byte-identical schema: no drift across the cycle
    finally:
        engine.dispose()


def _seed(engine: Engine, sql: str) -> None:
    with engine.connect() as connection:
        for statement in filter(None, sql.split(";")):
            connection.execute(text(statement))
        connection.commit()


def test_downgrade_refuses_populated_observations(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    """A base downgrade on a database holding observations is refused."""
    _seed(migrated_engine, _SYNTHETIC_OBSERVATION_SQL)
    with pytest.raises(RuntimeError, match="observations"):
        command.downgrade(alembic_config, "base")
    # The refusal aborted the whole downgrade: nothing was dropped.
    assert "observations" in _table_names(migrated_engine)
    assert "ledger_transactions" in _table_names(migrated_engine)


def test_downgrade_refuses_populated_ledger(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    """A base downgrade on a database holding ledger rows is refused."""
    _seed(migrated_engine, _SYNTHETIC_LEDGER_SQL)
    with pytest.raises(RuntimeError, match="ledger_transactions"):
        command.downgrade(alembic_config, "base")
    assert "ledger_transactions" in _table_names(migrated_engine)


def test_downgrade_refuses_populated_thesis_revisions(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    """A downgrade through 0006 on a database holding thesis revisions is refused."""
    _seed(
        migrated_engine,
        "INSERT INTO theses (title, hypotheses, invalidation, created_at)"
        " VALUES ('synthetic thesis', 'synthetic hypothesis', 'synthetic invalidation', now());"
        "INSERT INTO thesis_revisions (thesis_id, action, content_hash,"
        " idempotency_key, recorded_at) SELECT id, 'CREATED', 'sha256:0',"
        " 'synthetic-key-1', now() FROM theses",
    )
    with pytest.raises(RuntimeError, match="thesis_revisions"):
        command.downgrade(alembic_config, "base")
    # The refusal aborted the whole downgrade: nothing was dropped.
    assert "thesis_revisions" in _table_names(migrated_engine)
    assert "theses" in _table_names(migrated_engine)


def test_downgrade_error_names_the_explicit_override(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    _seed(migrated_engine, _SYNTHETIC_OBSERVATION_SQL)
    with pytest.raises(RuntimeError, match="VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE=1"):
        command.downgrade(alembic_config, "base")


def test_downgrade_populated_proceeds_only_with_explicit_override(
    migrated_engine: Engine,
    alembic_config: Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE=1 is the only way through, and it works."""
    _seed(migrated_engine, _SYNTHETIC_OBSERVATION_SQL)
    monkeypatch.setenv("VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE", "1")
    command.downgrade(alembic_config, "base")
    assert _table_names(migrated_engine) == {"alembic_version"}


def test_models_match_migrated_schema(migrated_engine: Engine) -> None:
    """The ORM models and the hand-written migrations describe the same schema.

    Full Alembic autogenerate comparison (``compare_type=True``): any drift a
    real ``alembic revision --autogenerate`` would emit — missing/extra table,
    column, index, unique or foreign-key constraint, type or nullability
    change, server-default change — fails this test. The assertion is
    literally "no difference detected".
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    with migrated_engine.connect() as connection:
        migration_context = MigrationContext.configure(
            connection,
            opts={
                "compare_type": True,
                "compare_server_default": True,
                # Alembic's own bookkeeping table is not an ORM model.
                "include_name": (
                    lambda name, type_, parent_names: not (
                        type_ == "table" and name == "alembic_version"
                    )
                ),
            },
        )
        diffs = compare_metadata(migration_context, Base.metadata)
    assert diffs == [], f"models and migrated schema drifted: {diffs}"
