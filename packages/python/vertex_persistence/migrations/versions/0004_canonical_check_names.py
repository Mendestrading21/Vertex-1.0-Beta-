"""Rename doubled CHECK constraint names to their canonical model names.

Revision ID: 0004_canonical_check_names
Revises: 0003_snapshots_append_only
Create Date: 2026-08-29

Real drift found by the strengthened models<->schema autogenerate test:
0001 passed fully-qualified names (``ck_observations_quality_status_canonical``)
to ``op.create_table`` while ``env.py`` exposes ``target_metadata`` with the
naming convention ``ck_%(table_name)s_%(constraint_name)s``; Alembic re-applied
the template to the already-qualified names, so every CHECK constraint landed
in the database with a doubled prefix, e.g.::

    ck_observations_ck_observations_quality_status_canonical

The behavior of the constraints was always correct — only their names drifted
from the ORM models. This migration renames all 11 CHECK constraints to the
canonical names the models declare. Pure rename: no data, no semantics, no
lock beyond a catalog update. ``downgrade`` restores the doubled names so the
0004 downgrade reproduces the exact prior schema.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0004_canonical_check_names"
down_revision: Union[str, None] = "0003_snapshots_append_only"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, constraint suffix) for every CHECK constraint created by 0001.
_CHECKS: tuple[tuple[str, str], ...] = (
    ("observations", "quality_status_canonical"),
    ("observations", "delay_status_canonical"),
    ("snapshots", "version_positive"),
    ("outbox", "status_canonical"),
    ("outbox", "attempts_non_negative"),
    ("portfolios", "base_currency_format"),
    ("position_lots", "source_canonical"),
    ("position_lots", "currency_format"),
    ("ledger_transactions", "kind_canonical"),
    ("ledger_transactions", "source_canonical"),
    ("ledger_transactions", "currency_format"),
)


def _names(table: str, suffix: str) -> tuple[str, str]:
    canonical = f"ck_{table}_{suffix}"
    doubled = f"ck_{table}_{canonical}"
    return doubled, canonical


def upgrade() -> None:
    for table, suffix in _CHECKS:
        doubled, canonical = _names(table, suffix)
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {doubled} TO {canonical}")


def downgrade() -> None:
    for table, suffix in _CHECKS:
        doubled, canonical = _names(table, suffix)
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {canonical} TO {doubled}")
