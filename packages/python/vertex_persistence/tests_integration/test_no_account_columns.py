"""Boundary proof: no broker-account concept exists anywhere in the schema.

IBKR is a market-data source only. The migrated database must contain no
column, table, index or constraint whose name evokes a broker account, order,
execution or broker P&L — scanned from ``information_schema``/catalogs, so the
proof covers the real DDL, not just the ORM models.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

# Forbidden name fragments (case-insensitive). "order" is checked with word
# boundaries via ORDER-specific fragments to avoid matching "recorded".
FORBIDDEN_FRAGMENTS = (
    "account",
    "ibkr",
    "broker",
    "nav",
    "execution",
    "order_id",
    "orders",
)


def _fetch_names(engine: Engine, sql: str) -> list[str]:
    with engine.connect() as connection:
        return [row[0] for row in connection.execute(text(sql))]


def test_no_account_like_column_anywhere(migrated_engine: Engine) -> None:
    columns = _fetch_names(
        migrated_engine,
        "SELECT table_name || '.' || column_name FROM information_schema.columns "
        "WHERE table_schema = 'public'",
    )
    offenders = [
        name
        for name in columns
        if any(fragment in name.lower() for fragment in FORBIDDEN_FRAGMENTS)
    ]
    assert offenders == [], f"broker-account-like columns found: {offenders}"


def test_no_account_like_table_index_or_constraint(migrated_engine: Engine) -> None:
    names = (
        _fetch_names(
            migrated_engine,
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
        )
        + _fetch_names(
            migrated_engine, "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
        )
        + _fetch_names(
            migrated_engine,
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_schema = 'public'",
        )
    )
    offenders = [
        name
        for name in names
        if any(fragment in name.lower() for fragment in FORBIDDEN_FRAGMENTS)
    ]
    assert offenders == [], f"broker-account-like schema objects found: {offenders}"


def test_ledger_sources_exclude_broker_sync(migrated_engine: Engine) -> None:
    """The CHECK constraints only allow user-declared provenance values."""
    with migrated_engine.connect() as connection:
        clauses = [
            row[0]
            for row in connection.execute(
                text(
                    "SELECT cc.check_clause FROM information_schema.check_constraints cc "
                    "JOIN information_schema.table_constraints tc "
                    "ON tc.constraint_name = cc.constraint_name "
                    "AND tc.constraint_schema = cc.constraint_schema "
                    "WHERE tc.table_schema = 'public' "
                    "AND cc.constraint_name LIKE '%source_canonical'"
                )
            )
        ]
    assert len(clauses) == 2  # position_lots and ledger_transactions
    for clause in clauses:
        assert "MANUAL" in clause
        assert "IMPORT_CONFIRMED" in clause
        assert "IBKR" not in clause.upper()
