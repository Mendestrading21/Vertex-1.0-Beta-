"""Passkey authentication tables: webauthn_credentials and auth_sessions.

Revision ID: 0005_auth_tables
Revises: 0004_canonical_check_names
Create Date: 2026-08-29

LOT-09 storage for the real WebAuthn authentication of the single local user:

- ``webauthn_credentials`` holds the registered passkeys — the opaque
  authenticator ``credential_id`` and COSE ``public_key`` (bytes, unique),
  the monotonic ``sign_count`` used for clone detection, an operator label
  and a ``revoked_at`` timestamp. Nothing here is a server secret.
- ``auth_sessions`` holds server-side sessions bound to a credential. The
  opaque bearer token handed to the browser is NEVER stored: only its
  SHA-256 hash (``session_id_hash``, unique) is persisted, and the CSRF
  double-submit token is stored the same way (``csrf_token_hash``).

Constraint names follow the canonical naming convention of the ORM models
(``vertex_persistence.models``); the autogenerate drift test compares both.
CHECK constraints are passed with their BARE suffix on purpose: ``env.py``
exposes the ``ck_%(table_name)s_%(constraint_name)s`` naming convention, which
prefixes them at create time — passing a fully-qualified name would double the
prefix (the 0001/0004 lesson).

The downgrade drops both tables: it destroys registered passkeys and open
sessions (recoverable by re-registering — no market or ledger data is lost),
so no populated-data guard is required here.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_auth_tables"
down_revision: Union[str, None] = "0004_canonical_check_names"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False),
        sa.Column("transports", sa.Text(), nullable=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_webauthn_credentials"),
        sa.UniqueConstraint("credential_id", name="uq_webauthn_credentials_credential_id"),
        sa.CheckConstraint("sign_count >= 0", name="sign_count_non_negative"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("session_id_hash", sa.Text(), nullable=False),
        sa.Column("credential_id", sa.BigInteger(), nullable=False),
        sa.Column("csrf_token_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint("session_id_hash", name="uq_auth_sessions_session_id_hash"),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["webauthn_credentials.id"],
            name="fk_auth_sessions_credential_id_webauthn_credentials",
        ),
        sa.CheckConstraint("expires_at > created_at", name="expires_after_created"),
    )
    op.create_index("ix_auth_sessions_credential_id", "auth_sessions", ["credential_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_credential_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("webauthn_credentials")
