"""Manual-ledger storage: user-declared portfolios, lots and past facts.

The ledger records **facts the user typed in after they happened outside
Vertex** (``docs/03-domain/PORTFOLIO_MANUAL.md``). Nothing here creates,
previews or transmits an order, and nothing reads a broker account: the only
provenance values are ``MANUAL`` and ``IMPORT_CONFIRMED``.

``ledger_transactions`` is append-only (SQL trigger): a mistake is corrected
by a compensating row referencing the corrected row via ``compensates``,
never by editing history. No financial rule lives here — valuation, P&L and
lot methodology belong to ``vertex_core``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_persistence.enums import (
    LEDGER_EVENT_KINDS,
    POSITION_LOT_SOURCES,
    PositionLotSource,
    validate_enum_value,
)
from vertex_persistence.errors import (
    AlreadyCompensatedError,
    LedgerError,
    UnknownLedgerEventError,
    UnknownPortfolioError,
)
from vertex_persistence.json_codec import to_jsonb_object
from vertex_persistence.models import LedgerTransaction, Portfolio, PositionLot
from vertex_persistence.repository._validation import (
    require_aware_utc,
    require_currency,
    require_decimal,
    require_non_empty_str,
    require_optional_decimal,
    require_optional_str,
    require_positive_int,
)

__all__ = [
    "PositionLotRecord",
    "create_portfolio",
    "add_position_lot",
    "record_ledger_event",
    "compensate_ledger_event",
    "list_position_lots",
]


@dataclass(frozen=True)
class PositionLotRecord:
    """Immutable view of one user-declared lot."""

    id: int
    portfolio_id: int
    instrument: dict[str, Any]
    quantity: Decimal
    unit_cost: Decimal
    currency: str
    opened_at: datetime
    source: str
    note: Optional[str]


def _require_portfolio(session: Session, portfolio_id: int) -> Portfolio:
    portfolio_id = require_positive_int("portfolio_id", portfolio_id)
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise UnknownPortfolioError(f"portfolio {portfolio_id} does not exist")
    return portfolio


def create_portfolio(session: Session, *, name: str, base_currency: str) -> int:
    """Create one user-declared portfolio; return its id (no commit here)."""
    row = Portfolio(
        name=require_non_empty_str("name", name),
        base_currency=require_currency("base_currency", base_currency),
    )
    session.add(row)
    session.flush()
    return row.id


def add_position_lot(
    session: Session,
    *,
    portfolio_id: int,
    instrument: Any,
    quantity: Decimal,
    unit_cost: Decimal,
    currency: str,
    opened_at: datetime,
    source: str = PositionLotSource.MANUAL.value,
    note: Optional[str] = None,
) -> int:
    """Record one user-declared lot; return its id (no commit here)."""
    _require_portfolio(session, portfolio_id)
    row = PositionLot(
        portfolio_id=portfolio_id,
        instrument=to_jsonb_object("instrument", instrument),
        quantity=require_decimal("quantity", quantity),
        unit_cost=require_decimal("unit_cost", unit_cost),
        currency=require_currency("currency", currency),
        opened_at=require_aware_utc("opened_at", opened_at),
        source=validate_enum_value("source", source, POSITION_LOT_SOURCES),
        note=require_optional_str("note", note),
    )
    session.add(row)
    session.flush()
    return row.id


def record_ledger_event(
    session: Session,
    *,
    portfolio_id: int,
    kind: str,
    amount: Decimal,
    currency: str,
    fees: Decimal,
    effective_at: datetime,
    recorded_at: datetime,
    instrument: Any = None,
    quantity: Optional[Decimal] = None,
    price: Optional[Decimal] = None,
    source: str = PositionLotSource.MANUAL.value,
    note: Optional[str] = None,
    compensates: Optional[int] = None,
) -> int:
    """Append one past fact to the ledger; return its id (no commit here).

    ``amount`` and ``fees`` are required exact Decimals — an unknown amount is
    an error, never zero. Optional fields stay ``None`` when absent.
    ``compensates`` must reference an existing event of the same portfolio
    that has no compensating entry yet.
    """
    _require_portfolio(session, portfolio_id)
    kind = validate_enum_value("kind", kind, LEDGER_EVENT_KINDS)
    compensated: Optional[LedgerTransaction] = None
    if compensates is not None:
        compensates = require_positive_int("compensates", compensates)
        compensated = session.get(LedgerTransaction, compensates)
        if compensated is None:
            raise UnknownLedgerEventError(f"ledger event {compensates} does not exist")
        if compensated.portfolio_id != portfolio_id:
            raise LedgerError(
                f"ledger event {compensates} belongs to portfolio "
                f"{compensated.portfolio_id}, not {portfolio_id}"
            )
        existing = session.execute(
            select(LedgerTransaction.id).where(LedgerTransaction.compensates == compensates)
        ).first()
        if existing is not None:
            raise AlreadyCompensatedError(
                f"ledger event {compensates} is already compensated by event {existing[0]}"
            )

    row = LedgerTransaction(
        portfolio_id=portfolio_id,
        kind=kind,
        instrument=(
            to_jsonb_object("instrument", instrument) if instrument is not None else None
        ),
        quantity=require_optional_decimal("quantity", quantity),
        price=require_optional_decimal("price", price),
        amount=require_decimal("amount", amount),
        currency=require_currency("currency", currency),
        fees=require_decimal("fees", fees),
        effective_at=require_aware_utc("effective_at", effective_at),
        recorded_at=require_aware_utc("recorded_at", recorded_at),
        source=validate_enum_value("source", source, POSITION_LOT_SOURCES),
        note=require_optional_str("note", note),
        compensates=compensates,
    )
    session.add(row)
    session.flush()
    return row.id


def compensate_ledger_event(
    session: Session,
    *,
    event_id: int,
    note: str,
    recorded_at: datetime,
) -> int:
    """Append the compensating entry of one recorded event; return the new id.

    The compensating row has the same portfolio, kind, instrument, currency
    and effective instant, with ``amount``, ``fees`` and ``quantity`` negated
    (exact Decimal negation) and ``compensates`` pointing at the corrected
    row. ``note`` is mandatory: a correction always states why. History is
    never edited; an already-compensated event cannot be compensated again.
    """
    event_id = require_positive_int("event_id", event_id)
    note = require_non_empty_str("note", note)
    recorded_at = require_aware_utc("recorded_at", recorded_at)

    original = session.get(LedgerTransaction, event_id)
    if original is None:
        raise UnknownLedgerEventError(f"ledger event {event_id} does not exist")

    return record_ledger_event(
        session,
        portfolio_id=original.portfolio_id,
        kind=original.kind,
        amount=-original.amount,
        currency=original.currency,
        fees=-original.fees,
        effective_at=original.effective_at,
        recorded_at=recorded_at,
        instrument=original.instrument,
        quantity=-original.quantity if original.quantity is not None else None,
        price=original.price,
        source=original.source,
        note=note,
        compensates=event_id,
    )


def list_position_lots(session: Session, portfolio_id: int) -> list[PositionLotRecord]:
    """Return the user-declared lots of one portfolio, oldest first.

    An empty portfolio returns an empty list — never fabricated rows.
    """
    _require_portfolio(session, portfolio_id)
    rows = (
        session.execute(
            select(PositionLot)
            .where(PositionLot.portfolio_id == portfolio_id)
            .order_by(PositionLot.opened_at, PositionLot.id)
        )
        .scalars()
        .all()
    )
    return [
        PositionLotRecord(
            id=row.id,
            portfolio_id=row.portfolio_id,
            instrument=dict(row.instrument),
            quantity=row.quantity,
            unit_cost=row.unit_cost,
            currency=row.currency,
            opened_at=row.opened_at,
            source=row.source,
            note=row.note,
        )
        for row in rows
    ]
