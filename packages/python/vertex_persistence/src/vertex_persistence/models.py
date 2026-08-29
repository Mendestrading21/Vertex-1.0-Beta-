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
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
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
)

__all__ = [
    "Base",
    "Observation",
    "Snapshot",
    "SnapshotHead",
    "OutboxMessage",
    "Portfolio",
    "PositionLot",
    "LedgerTransaction",
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
    source_event_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instrument_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality_status: Mapped[str] = mapped_column(Text, nullable=False)
    delay_status: Mapped[str] = mapped_column(Text, nullable=False)
    connection_epoch: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
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
    lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Short technical diagnostic only — never a payload, secret or account datum.
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(sql_enum_check("source", POSITION_LOT_SOURCES), name="source_canonical"),
        CheckConstraint(f"currency ~ '{CURRENCY_PATTERN}'", name="currency_format"),
        Index("ix_position_lots_portfolio_id", "portfolio_id"),
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
    instrument: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'MANUAL'"))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compensates: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("ledger_transactions.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(sql_enum_check("kind", LEDGER_EVENT_KINDS), name="kind_canonical"),
        CheckConstraint(sql_enum_check("source", POSITION_LOT_SOURCES), name="source_canonical"),
        CheckConstraint(f"currency ~ '{CURRENCY_PATTERN}'", name="currency_format"),
        Index("ix_ledger_transactions_portfolio_effective", "portfolio_id", "effective_at"),
    )
