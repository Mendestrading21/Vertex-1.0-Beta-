"""Initial persistence schema: observations, snapshots, outbox, manual ledger.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-28

Immutable migration: enum value lists are frozen here on purpose (a later
vocabulary change is a NEW migration). A unit test guards against drift
between these lists and ``vertex_persistence.enums``.

No broker-account concept exists in this schema: no account identifier,
balance, broker position, order or execution column — an integration test
scans ``information_schema`` to prove it.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen vocabularies (see module docstring).
OBSERVATION_QUALITY_STATUSES = (
    "CONFLICT",
    "INSUFFICIENT_DATA",
    "INVALID",
    "PARTIAL",
    "STALE",
    "VALID",
)
OBSERVATION_DELAY_STATUSES = ("DELAYED", "DELAYED_FROZEN", "FROZEN", "LIVE", "UNKNOWN")
OUTBOX_STATUSES = ("DEAD", "DONE", "FAILED", "IN_PROGRESS", "PENDING")
LEDGER_EVENT_KINDS = (
    "ADJUSTMENT",
    "BUY_RECORDED",
    "CORPORATE_ACTION",
    "DEPOSIT",
    "DIVIDEND",
    "FEE",
    "FX_CONVERSION",
    "INTEREST",
    "OPTION_CLOSE",
    "OPTION_OPEN",
    "SELL_RECORDED",
    "TAX",
    "WITHDRAWAL",
)
POSITION_LOT_SOURCES = ("IMPORT_CONFIRMED", "MANUAL")

CURRENCY_PATTERN = "^[A-Z]{3}$"

APPEND_ONLY_FUNCTION = """
CREATE FUNCTION vertex_forbid_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'table % is append-only: % is forbidden; corrections are new compensating rows',
        TG_TABLE_NAME, TG_OP;
END;
$$;
"""


def _in_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _append_only_triggers(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER {table}_append_only
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION vertex_forbid_mutation();
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {table}_no_truncate
        BEFORE TRUNCATE ON {table}
        FOR EACH STATEMENT EXECUTE FUNCTION vertex_forbid_mutation();
        """
    )


def upgrade() -> None:
    # --- observations (append-only market observations) -------------------
    op.create_table(
        "observations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_event_id", sa.Text(), nullable=True),
        sa.Column("instrument_ref", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quality_status", sa.Text(), nullable=False),
        sa.Column("delay_status", sa.Text(), nullable=False),
        sa.Column("connection_epoch", sa.Integer(), nullable=True),
        sa.Column("rights", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_hash", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_observations"),
        sa.UniqueConstraint("event_id", name="uq_observations_event_id"),
        sa.CheckConstraint(
            f"quality_status IN ({_in_list(OBSERVATION_QUALITY_STATUSES)})",
            name="ck_observations_quality_status_canonical",
        ),
        sa.CheckConstraint(
            f"delay_status IN ({_in_list(OBSERVATION_DELAY_STATUSES)})",
            name="ck_observations_delay_status_canonical",
        ),
    )
    op.create_index("ix_observations_as_of", "observations", ["as_of"])

    # --- snapshots + transactional head pointer ---------------------------
    op.create_table(
        "snapshots",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_snapshots"),
        sa.UniqueConstraint("kind", "key", "version", name="uq_snapshots_kind_key_version"),
        sa.CheckConstraint("version >= 1", name="ck_snapshots_version_positive"),
    )
    op.create_table(
        "snapshot_heads",
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("kind", "key", name="pk_snapshot_heads"),
        sa.ForeignKeyConstraint(
            ["kind", "key", "version"],
            ["snapshots.kind", "snapshots.key", "snapshots.version"],
            name="fk_snapshot_heads_snapshot_version",
        ),
    )

    # --- outbox (ADR-006) -------------------------------------------------
    op.create_table(
        "outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_outbox"),
        sa.CheckConstraint(
            f"status IN ({_in_list(OUTBOX_STATUSES)})", name="ck_outbox_status_canonical"
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_outbox_attempts_non_negative"),
    )
    op.create_index("ix_outbox_status_lease_until", "outbox", ["status", "lease_until"])

    # --- manual ledger ----------------------------------------------------
    op.create_table(
        "portfolios",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_portfolios"),
        sa.UniqueConstraint("name", name="uq_portfolios_name"),
        sa.CheckConstraint(
            f"base_currency ~ '{CURRENCY_PATTERN}'", name="ck_portfolios_base_currency_format"
        ),
    )
    op.create_table(
        "position_lots",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("portfolio_id", sa.BigInteger(), nullable=False),
        sa.Column("instrument", JSONB(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), server_default=sa.text("'MANUAL'"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_position_lots"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], name="fk_position_lots_portfolio_id_portfolios"
        ),
        sa.CheckConstraint(
            f"source IN ({_in_list(POSITION_LOT_SOURCES)})",
            name="ck_position_lots_source_canonical",
        ),
        sa.CheckConstraint(
            f"currency ~ '{CURRENCY_PATTERN}'", name="ck_position_lots_currency_format"
        ),
    )
    op.create_index("ix_position_lots_portfolio_id", "position_lots", ["portfolio_id"])
    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("portfolio_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("instrument", JSONB(), nullable=True),
        sa.Column("quantity", sa.Numeric(), nullable=True),
        sa.Column("price", sa.Numeric(), nullable=True),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("fees", sa.Numeric(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), server_default=sa.text("'MANUAL'"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("compensates", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_transactions"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["portfolios.id"],
            name="fk_ledger_transactions_portfolio_id_portfolios",
        ),
        sa.ForeignKeyConstraint(
            ["compensates"],
            ["ledger_transactions.id"],
            name="fk_ledger_transactions_compensates_ledger_transactions",
        ),
        sa.CheckConstraint(
            f"kind IN ({_in_list(LEDGER_EVENT_KINDS)})",
            name="ck_ledger_transactions_kind_canonical",
        ),
        sa.CheckConstraint(
            f"source IN ({_in_list(POSITION_LOT_SOURCES)})",
            name="ck_ledger_transactions_source_canonical",
        ),
        sa.CheckConstraint(
            f"currency ~ '{CURRENCY_PATTERN}'", name="ck_ledger_transactions_currency_format"
        ),
    )
    op.create_index(
        "ix_ledger_transactions_portfolio_effective",
        "ledger_transactions",
        ["portfolio_id", "effective_at"],
    )

    # --- append-only enforcement (holds for every SQL client) -------------
    op.execute(APPEND_ONLY_FUNCTION)
    _append_only_triggers("observations")
    _append_only_triggers("ledger_transactions")


def downgrade() -> None:
    for table in ("ledger_transactions", "observations"):
        op.execute(f"DROP TRIGGER {table}_append_only ON {table};")
        op.execute(f"DROP TRIGGER {table}_no_truncate ON {table};")
    op.execute("DROP FUNCTION vertex_forbid_mutation();")
    op.drop_index("ix_ledger_transactions_portfolio_effective", table_name="ledger_transactions")
    op.drop_table("ledger_transactions")
    op.drop_index("ix_position_lots_portfolio_id", table_name="position_lots")
    op.drop_table("position_lots")
    op.drop_table("portfolios")
    op.drop_index("ix_outbox_status_lease_until", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("snapshot_heads")
    op.drop_table("snapshots")
    op.drop_index("ix_observations_as_of", table_name="observations")
    op.drop_table("observations")
