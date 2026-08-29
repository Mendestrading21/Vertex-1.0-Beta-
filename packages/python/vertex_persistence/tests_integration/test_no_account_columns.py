"""Boundary proof: no broker-account concept exists anywhere in the schema.

IBKR is a market-data source only. The migrated database must contain no
column, table, index or constraint whose name evokes a broker account, order,
execution or broker P&L — scanned from ``information_schema``/catalogs, so the
proof covers the real DDL, not just the ORM models.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

# Forbidden name fragments (case-insensitive substring on object names).
# "order" is checked with word boundaries via ORDER-specific fragments to
# avoid matching "recorded". Account-economics fragments (balance, cash,
# pnl, equity, buying_power, nav) must not over-match the legal manual-ledger
# vocabulary (amount, currency, fees, unit_cost, content_hash, ...) — a
# self-test below pins both directions.
FORBIDDEN_FRAGMENTS = (
    "account",
    "ibkr",
    "broker",
    "balance",
    "cash",
    "pnl",
    "equity",
    "buying_power",
    "nav",
    "execution",
    "order_id",
    "orders",
)


def _offenders(names: list[str]) -> list[str]:
    """Names matching any forbidden fragment (case-insensitive substring)."""
    return [
        name
        for name in names
        if any(fragment in name.lower() for fragment in FORBIDDEN_FRAGMENTS)
    ]


def _fetch_names(engine: Engine, sql: str) -> list[str]:
    with engine.connect() as connection:
        return [row[0] for row in connection.execute(text(sql))]


def test_forbidden_fragments_catch_account_economics_names() -> None:
    """Self-test of the guard: account-economics column names MUST be flagged.

    A schema drift introducing broker-account economics (balance, cash, P&L,
    equity, buying power, NAV) has to trip the scan by substring on the
    column name, whatever prefix/suffix decorates it.
    """
    synthetic_bad = [
        "outbox.cash_balance",
        "portfolios.account_balance",
        "portfolios.cash",
        "position_lots.realized_pnl",
        "portfolios.equity_value",
        "portfolios.buying_power",
        "portfolios.nav_total",
        "portfolios.ibkr_ref",
        "orders.order_id",
    ]
    assert _offenders(synthetic_bad) == synthetic_bad


def test_forbidden_fragments_do_not_flag_legitimate_names() -> None:
    """The manual-ledger vocabulary stays legal: no fragment may over-match."""
    legitimate = [
        "ledger_transactions.amount",
        "ledger_transactions.currency",
        "ledger_transactions.fees",
        "ledger_transactions.quantity",
        "ledger_transactions.price",
        "portfolios.base_currency",
        "position_lots.unit_cost",
        "ledger_transactions.recorded_at",
        "ledger_transactions.compensates",
    ]
    assert _offenders(legitimate) == []


def test_no_account_like_column_anywhere(migrated_engine: Engine) -> None:
    columns = _fetch_names(
        migrated_engine,
        "SELECT table_name || '.' || column_name FROM information_schema.columns "
        "WHERE table_schema = 'public'",
    )
    offenders = _offenders(columns)
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
    offenders = _offenders(names)
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
