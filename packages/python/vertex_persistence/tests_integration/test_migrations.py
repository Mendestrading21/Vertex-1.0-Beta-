"""Migration integrity: upgrade -> downgrade -> upgrade without drift."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from vertex_persistence.models import Base

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


def test_models_match_migrated_schema(migrated_engine: Engine) -> None:
    """The ORM models and the hand-written migration describe the same schema."""
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT table_name, column_name, is_nullable "
                "FROM information_schema.columns WHERE table_schema = 'public'"
            )
        )
        db_columns = {
            (table, column): nullable == "YES"
            for table, column, nullable in rows
            if table != "alembic_version"
        }
    model_columns = {
        (table.name, column.name): bool(column.nullable)
        for table in Base.metadata.tables.values()
        for column in table.columns
    }
    assert db_columns == model_columns
