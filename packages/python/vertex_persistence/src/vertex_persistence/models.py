"""SQLAlchemy 2 Declarative models of the Vertex persistence schema.

Storage shapes only — no financial rule, no decision logic, no broker-account
concept. The authoritative DDL lives in the Alembic migrations; these models
must stay column-for-column identical to it (an integration test compares
both). Append-only enforcement (observations, ledger_transactions) is done by
SQL triggers created in the migration, so it holds for every client, not only
for this ORM.

All timestamps are ``timestamptz`` (aware, stored in UTC). NUMERIC columns are
unconstrained PostgreSQL ``numeric`` mapped to :class:`decimal.Decimal` — no
float ever represents money or a contractual quantity.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from vertex_persistence.enums import (
    LEDGER_EVENT_KINDS,
    OBSERVATION_DELAY_STATUSES,
    OBSERVATION_QUALITY_STATUSES,
    OUTBOX_STATUSES,
    POSITION_LOT_SOURCES,
    THESIS_REVISION_ACTIONS,
)

__all__ = [
    "AuthSession",
    "Base",
    "LedgerTransaction",
    "Observation",
    "OutboxMessage",
    "Portfolio",
    "PositionLot",
    "Snapshot",
    "SnapshotHead",
    "Thesis",
    "ThesisRevision",
    "WebauthnCredential",
    "sql_enum_check",
]

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

CURRENCY_PATTERN = "^[A-Z]{3}$"


def sql_enum_check(column: str, allowed: frozenset[str]) -> str:
    """Render the SQL body of a CHECK constraint pinning ``column`` to ``allowed``."""
    values = ", ".join(f"'{value}'" for value in sorted(allowed))
    return f"{column} IN ({values})"


class Base(DeclarativeBase):
    """Declarative base with a deterministic naming convention."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Observation(Base):
    """One immutable, sourced market observation (append-only).

    Carries the full provenance contract: source, timestamps, freshness bound,
    quality and delay status, entitlement rights and payload hash. Corrections
    are new observations; UPDATE/DELETE are forbidden by trigger.
    """

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    instrument_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality_status: Mapped[str] = mapped_column(Text, nullable=False)
    delay_status: Mapped[str] = mapped_column(Text, nullable=False)
    connection_epoch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rights: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id"),
        CheckConstraint(
            sql_enum_check("quality_status", OBSERVATION_QUALITY_STATUSES),
            name="quality_status_canonical",
        ),
        CheckConstraint(
            sql_enum_check("delay_status", OBSERVATION_DELAY_STATUSES),
            name="delay_status_canonical",
        ),
        Index("ix_observations_as_of", "as_of"),
    )


class Snapshot(Base):
    """One immutable version of a derived snapshot, addressed by (kind, key, version)."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("kind", "key", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
    )


class SnapshotHead(Base):
    """Current-version pointer per (kind, key), moved transactionally with each publish."""

    __tablename__ = "snapshot_heads"

    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["kind", "key", "version"],
            ["snapshots.kind", "snapshots.key", "snapshots.version"],
            name="fk_snapshot_heads_snapshot_version",
        ),
    )


class OutboxMessage(Base):
    """One at-least-once outbox message (ADR-006), enqueued with the business write."""

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'PENDING'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Opaque per-claim ownership nonce: set on claim, required by ack/fail,
    # cleared on every transition out of IN_PROGRESS (ack, fail, reap).
    lease_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Short technical diagnostic only — never a payload, secret or account datum.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(sql_enum_check("status", OUTBOX_STATUSES), name="status_canonical"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        Index("ix_outbox_status_lease_until", "status", "lease_until"),
    )


class Portfolio(Base):
    """One user-declared portfolio (manual ledger authority; never a broker feed)."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_currency: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("name"),
        CheckConstraint(f"base_currency ~ '{CURRENCY_PATTERN}'", name="base_currency_format"),
    )


class PositionLot(Base):
    """One user-declared position lot (canonical instrument as JSON, Decimal amounts)."""

    __tablename__ = "position_lots"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("portfolios.id"), nullable=False
    )
    instrument: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'MANUAL'"))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(sql_enum_check("source", POSITION_LOT_SOURCES), name="source_canonical"),
        CheckConstraint(f"currency ~ '{CURRENCY_PATTERN}'", name="currency_format"),
        Index("ix_position_lots_portfolio_id", "portfolio_id"),
    )


class WebauthnCredential(Base):
    """One registered WebAuthn (passkey) credential of the single local user.

    Stores only what the WebAuthn verification needs: the authenticator's
    credential id and COSE public key (both opaque bytes — never a secret of
    the server), the monotonic signature counter used for clone detection, an
    operator-chosen label and the revocation timestamp. No password, no
    recoverable secret and no broker-account concept lives here.
    """

    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transports: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("credential_id"),
        CheckConstraint("sign_count >= 0", name="sign_count_non_negative"),
    )


class AuthSession(Base):
    """One server-side authenticated session bound to a WebAuthn credential.

    The opaque session token handed to the browser is NEVER stored: only its
    SHA-256 hash (``session_id_hash``) lands in the database, so a database
    read can never be replayed as a cookie. The CSRF double-submit token is
    stored the same way (``csrf_token_hash``). Expiry and revocation are both
    explicit timestamps — validation fails closed on either.
    """

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    session_id_hash: Mapped[str] = mapped_column(Text, nullable=False)
    credential_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("webauthn_credentials.id"), nullable=False
    )
    csrf_token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("session_id_hash"),
        CheckConstraint("expires_at > created_at", name="expires_after_created"),
        Index("ix_auth_sessions_credential_id", "credential_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )


class Thesis(Base):
    """One user-written investment thesis (page 09 — follow-up queue).

    The immutable statement of the thesis: what the user believes
    (``hypotheses``) and, mandatorily, what would prove it wrong
    (``invalidation`` — a thesis without an invalidation criterion is refused
    by CHECK). There is deliberately NO mutable status column here: the
    current status (ACTIVE / SNOOZED / ARCHIVED) and the effective review-due
    instant are a pure projection of the append-only ``thesis_revisions``
    history, recomputed by
    :func:`vertex_persistence.repository.theses.project_thesis_state`.
    """

    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    portfolio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("portfolios.id"), nullable=True
    )
    instrument: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    hypotheses: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation: Mapped[str] = mapped_column(Text, nullable=False)
    horizon: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        # A thesis without a non-blank invalidation criterion is refused.
        CheckConstraint("length(btrim(invalidation)) > 0", name="invalidation_not_blank"),
        Index("ix_theses_portfolio_id", "portfolio_id"),
    )


class ThesisRevision(Base):
    """One immutable revision of a thesis's review lifecycle (append-only).

    Records what the user did (reviewed, snoozed, archived, ...), never what
    the system decided. UPDATE/DELETE/TRUNCATE are forbidden by the same SQL
    triggers that protect ``observations`` and ``ledger_transactions``.
    ``idempotency_key`` is UNIQUE: replaying the same recording writes
    nothing new. ``snooze_until`` is present exactly on SNOOZED revisions
    (CHECK) — a snooze without a wake-up instant is meaningless, and a
    wake-up instant on any other action would be contradictory.
    """

    __tablename__ = "thesis_revisions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    thesis_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("theses.id"), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'local-user'")
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snooze_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        CheckConstraint(
            sql_enum_check("action", THESIS_REVISION_ACTIONS), name="action_canonical"
        ),
        CheckConstraint(
            "(action = 'SNOOZED') = (snooze_until IS NOT NULL)",
            name="snooze_until_only_when_snoozed",
        ),
        Index("ix_thesis_revisions_thesis_id", "thesis_id"),
    )


class LedgerTransaction(Base):
    """One immutable, user-recorded past fact (append-only).

    Records what already happened outside Vertex. Corrections are compensating
    rows referencing the corrected row via ``compensates``; UPDATE/DELETE are
    forbidden by trigger.
    """

    __tablename__ = "ledger_transactions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("portfolios.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    instrument: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'MANUAL'"))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    compensates: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ledger_transactions.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(sql_enum_check("kind", LEDGER_EVENT_KINDS), name="kind_canonical"),
        CheckConstraint(sql_enum_check("source", POSITION_LOT_SOURCES), name="source_canonical"),
        CheckConstraint(f"currency ~ '{CURRENCY_PATTERN}'", name="currency_format"),
        Index("ix_ledger_transactions_portfolio_effective", "portfolio_id", "effective_at"),
        # At most one compensating row per event, enforced by the database
        # itself so the guarantee holds under concurrency and for every client.
        Index(
            "uq_ledger_transactions_compensates",
            "compensates",
            unique=True,
            postgresql_where=text("compensates IS NOT NULL"),
        ),
    )
