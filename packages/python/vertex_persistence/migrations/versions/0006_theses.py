"""Theses and their append-only review revisions (page 09 — follow-up).

Revision ID: 0006_theses
Revises: 0005_auth_tables
Create Date: 2026-08-29

V4-T1 storage for user-written investment theses and their review history:

- ``theses`` holds the immutable statement of each thesis: what the user
  believes (``hypotheses``) and, mandatorily, what would prove it wrong
  (``invalidation`` — a blank invalidation criterion is refused by CHECK).
  There is deliberately NO status column and NO effective-review-due column:
  the current status (ACTIVE / SNOOZED / ARCHIVED) and the effective review
  due are a pure PROJECTION of the revisions, recomputed by
  ``vertex_persistence.repository.theses.project_thesis_state``. Nothing
  mutable to drift, nothing cached to go stale.
- ``thesis_revisions`` is APPEND-ONLY by the same ``vertex_forbid_mutation``
  triggers (created in 0001) that protect ``observations`` and
  ``ledger_transactions``, so the guarantee holds for every SQL client.
  ``idempotency_key`` is UNIQUE: replaying a recording writes nothing new.
  ``snooze_until`` is present exactly on SNOOZED revisions (CHECK).

The revision-action list is frozen here on purpose (a vocabulary change is a
NEW migration); a unit test guards against drift from
``vertex_persistence.enums.THESIS_REVISION_ACTIONS``.

CHECK constraints are passed with their BARE suffix on purpose: ``env.py``
exposes the ``ck_%(table_name)s_%(constraint_name)s`` naming convention which
prefixes them at create time — a fully-qualified name would double the prefix
(the 0001/0004 lesson).

The downgrade is DESTRUCTIVE for the append-only review history: like 0001 it
fails closed when ``thesis_revisions`` still holds rows, unless
``VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE=1`` is exported explicitly. An empty
database (the up→down→up integrity cycle) downgrades without friction.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0006_theses"
down_revision: str | None = "0005_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen vocabulary (see module docstring).
THESIS_REVISION_ACTIONS = (
    "ARCHIVED",
    "CREATED",
    "NOTE_UPDATED",
    "REACTIVATED",
    "REVIEWED",
    "SNOOZED",
)


def _in_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "theses",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("portfolio_id", sa.BigInteger(), nullable=True),
        sa.Column("instrument", JSONB(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("hypotheses", sa.Text(), nullable=False),
        sa.Column("invalidation", sa.Text(), nullable=False),
        sa.Column("horizon", sa.Text(), nullable=True),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_theses"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], name="fk_theses_portfolio_id_portfolios"
        ),
        # A thesis without a non-blank invalidation criterion is refused.
        sa.CheckConstraint("length(btrim(invalidation)) > 0", name="invalidation_not_blank"),
    )
    op.create_index("ix_theses_portfolio_id", "theses", ["portfolio_id"])

    op.create_table(
        "thesis_revisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("thesis_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("snapshot_ref", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), server_default=sa.text("'local-user'"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snooze_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_thesis_revisions"),
        sa.ForeignKeyConstraint(
            ["thesis_id"], ["theses.id"], name="fk_thesis_revisions_thesis_id_theses"
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_thesis_revisions_idempotency_key"),
        sa.CheckConstraint(
            f"action IN ({_in_list(THESIS_REVISION_ACTIONS)})", name="action_canonical"
        ),
        sa.CheckConstraint(
            "(action = 'SNOOZED') = (snooze_until IS NOT NULL)",
            name="snooze_until_only_when_snoozed",
        ),
    )
    op.create_index("ix_thesis_revisions_thesis_id", "thesis_revisions", ["thesis_id"])

    # Append-only enforcement — same trigger shape as 0001's
    # _append_only_triggers(); the trigger function exists since 0001.
    op.execute(
        """
        CREATE TRIGGER thesis_revisions_append_only
        BEFORE UPDATE OR DELETE ON thesis_revisions
        FOR EACH ROW EXECUTE FUNCTION vertex_forbid_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER thesis_revisions_no_truncate
        BEFORE TRUNCATE ON thesis_revisions
        FOR EACH STATEMENT EXECUTE FUNCTION vertex_forbid_mutation();
        """
    )


def downgrade() -> None:
    """DESTRUCTIVE — drops the theses and their append-only review history.

    Fail-closed guard (same policy as 0001): when ``thesis_revisions`` still
    holds rows, this downgrade raises :class:`RuntimeError` instead of
    destroying the user's review history. The only way through is the
    explicit ``VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE=1`` opt-in. A revision
    always exists for a created thesis (they are inserted transactionally),
    so guarding the revisions table guards the theses too.
    """
    if os.environ.get("VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE") != "1":
        if context.is_offline_mode():
            raise RuntimeError(
                "destructive downgrade refused: offline (--sql) mode cannot "
                "verify that thesis_revisions is empty; export "
                "VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE=1 to override explicitly"
            )
        bind = op.get_bind()
        populated = bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM thesis_revisions)")
        ).scalar()
        if populated:
            raise RuntimeError(
                "destructive downgrade refused: thesis_revisions still "
                "contains rows that would be destroyed forever. Back the "
                "data up first, then export "
                "VERTEX_ALLOW_DESTRUCTIVE_DOWNGRADE=1 to override explicitly."
            )
    op.execute("DROP TRIGGER thesis_revisions_append_only ON thesis_revisions;")
    op.execute("DROP TRIGGER thesis_revisions_no_truncate ON thesis_revisions;")
    op.drop_index("ix_thesis_revisions_thesis_id", table_name="thesis_revisions")
    op.drop_table("thesis_revisions")
    op.drop_index("ix_theses_portfolio_id", table_name="theses")
    op.drop_table("theses")
