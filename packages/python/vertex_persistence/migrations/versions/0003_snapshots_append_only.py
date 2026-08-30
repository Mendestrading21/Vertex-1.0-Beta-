"""Append-only triggers on snapshots (snapshot_heads stays mutable).

Revision ID: 0003_snapshots_append_only
Revises: 0002_concurrency_guards
Create Date: 2026-08-29

``snapshots`` rows are immutable versions addressed by (kind, key, version):
a correction is a NEW version plus a head move, never an UPDATE or DELETE of
a stored version. This migration closes a confirmed P2 gap by attaching the
same ``vertex_forbid_mutation`` triggers (created in 0001) that already
protect ``observations`` and ``ledger_transactions``, so the guarantee holds
for every SQL client, not only the ORM.

``snapshot_heads`` deliberately gets NO trigger: it is the moving
current-version pointer and must remain updatable.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_snapshots_append_only"
down_revision: str | None = "0002_concurrency_guards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Same trigger shape as 0001's _append_only_triggers("observations")/
    # ("ledger_transactions"); the trigger function already exists since 0001.
    op.execute(
        """
        CREATE TRIGGER snapshots_append_only
        BEFORE UPDATE OR DELETE ON snapshots
        FOR EACH ROW EXECUTE FUNCTION vertex_forbid_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER snapshots_no_truncate
        BEFORE TRUNCATE ON snapshots
        FOR EACH STATEMENT EXECUTE FUNCTION vertex_forbid_mutation();
        """
    )


def downgrade() -> None:
    # Non-destructive for data: only the immutability guard is removed.
    op.execute("DROP TRIGGER snapshots_append_only ON snapshots;")
    op.execute("DROP TRIGGER snapshots_no_truncate ON snapshots;")
