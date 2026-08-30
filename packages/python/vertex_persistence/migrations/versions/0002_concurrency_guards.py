"""Concurrency guards: outbox lease ownership token, unique compensation.

Revision ID: 0002_concurrency_guards
Revises: 0001_initial
Create Date: 2026-08-29

Two database-level guarantees that closed confirmed P1 defects:

- ``outbox.lease_token``: opaque per-claim ownership nonce. Set on claim,
  required by ack/fail, cleared on every transition out of IN_PROGRESS, so a
  worker whose lease was reaped or re-claimed can no longer ack/fail a row it
  does not own (ADR-006: record attempt, lease and result).
- partial unique index on ``ledger_transactions.compensates``: at most one
  compensating row per ledger event, enforced by PostgreSQL itself so the
  append-only ledger stays coherent under concurrent corrections and for
  every SQL client, not only the ORM.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_concurrency_guards"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("outbox", sa.Column("lease_token", sa.Text(), nullable=True))
    op.create_index(
        "uq_ledger_transactions_compensates",
        "ledger_transactions",
        ["compensates"],
        unique=True,
        postgresql_where=sa.text("compensates IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_ledger_transactions_compensates", table_name="ledger_transactions")
    op.drop_column("outbox", "lease_token")
