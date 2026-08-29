"""Manual ledger: append-only facts, compensating corrections, declared lots.

All data is SYNTHETIC user input — no broker feed exists or is simulated.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from vertex_persistence.errors import (
    AlreadyCompensatedError,
    EnumValidationError,
    UnknownLedgerEventError,
    UnknownPortfolioError,
    ValidationFailedError,
)
from vertex_persistence.models import LedgerTransaction
from vertex_persistence.repository import (
    add_position_lot,
    compensate_ledger_event,
    create_portfolio,
    list_position_lots,
    record_ledger_event,
)

UTC = timezone.utc
T0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)
INSTRUMENT = {"symbol": "SYN", "asset_class": "STOCK", "exchange": "SYNTH", "currency": "USD"}


@pytest.fixture()
def portfolio_id(db_session: Session) -> int:
    identifier = create_portfolio(db_session, name="synthetic-main", base_currency="CHF")
    db_session.commit()
    return identifier


def _record_buy(session: Session, portfolio_id: int, **overrides) -> int:
    values = dict(
        portfolio_id=portfolio_id,
        kind="BUY_RECORDED",
        amount=Decimal("-1012.50"),
        currency="USD",
        fees=Decimal("1.25"),
        effective_at=T0,
        recorded_at=T0 + timedelta(hours=1),
        instrument=INSTRUMENT,
        quantity=Decimal("10"),
        price=Decimal("101.25"),
        note="user-typed past fact",
    )
    values.update(overrides)
    return record_ledger_event(session, **values)


def test_record_ledger_event_stores_exact_decimals(db_session: Session, portfolio_id: int) -> None:
    event_id = _record_buy(db_session, portfolio_id)
    db_session.commit()
    row = db_session.get(LedgerTransaction, event_id)
    assert row is not None
    assert row.amount == Decimal("-1012.50")
    assert row.quantity == Decimal("10")
    assert row.fees == Decimal("1.25")
    assert row.source == "MANUAL"
    assert row.compensates is None
    assert row.instrument == INSTRUMENT


def test_ledger_update_and_delete_forbidden(db_session: Session, portfolio_id: int) -> None:
    _record_buy(db_session, portfolio_id)
    db_session.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("UPDATE ledger_transactions SET amount = 0"))
    db_session.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("DELETE FROM ledger_transactions"))
    db_session.rollback()
    count = db_session.execute(select(func.count()).select_from(LedgerTransaction)).scalar_one()
    assert count == 1


def test_compensation_negates_and_links(db_session: Session, portfolio_id: int) -> None:
    original_id = _record_buy(db_session, portfolio_id)
    db_session.commit()
    compensating_id = compensate_ledger_event(
        db_session,
        event_id=original_id,
        note="typo in quantity, re-recording",
        recorded_at=T0 + timedelta(days=1),
    )
    db_session.commit()
    compensating = db_session.get(LedgerTransaction, compensating_id)
    original = db_session.get(LedgerTransaction, original_id)
    assert compensating is not None and original is not None
    assert compensating.compensates == original_id
    assert compensating.kind == original.kind
    assert compensating.amount == -original.amount
    assert compensating.fees == -original.fees
    assert compensating.quantity == -original.quantity
    assert compensating.effective_at == original.effective_at
    assert compensating.currency == original.currency
    # The pair sums to zero: correction happened without touching history.
    total = db_session.execute(select(func.sum(LedgerTransaction.amount))).scalar_one()
    assert total == Decimal("0.00")


def test_double_compensation_rejected(db_session: Session, portfolio_id: int) -> None:
    original_id = _record_buy(db_session, portfolio_id)
    db_session.commit()
    compensate_ledger_event(
        db_session, event_id=original_id, note="first correction", recorded_at=T0
    )
    db_session.commit()
    with pytest.raises(AlreadyCompensatedError):
        compensate_ledger_event(
            db_session, event_id=original_id, note="second correction", recorded_at=T0
        )
    db_session.rollback()


def test_compensating_missing_event_rejected(db_session: Session, portfolio_id: int) -> None:
    with pytest.raises(UnknownLedgerEventError):
        compensate_ledger_event(db_session, event_id=424242, note="nope", recorded_at=T0)
    db_session.rollback()


def test_unknown_portfolio_rejected(db_session: Session) -> None:
    with pytest.raises(UnknownPortfolioError):
        _record_buy(db_session, 424242)
    db_session.rollback()


def test_absent_amount_is_error_never_zero(db_session: Session, portfolio_id: int) -> None:
    with pytest.raises(ValidationFailedError):
        _record_buy(db_session, portfolio_id, amount=None)
    db_session.rollback()


def test_float_money_rejected(db_session: Session, portfolio_id: int) -> None:
    with pytest.raises(ValidationFailedError):
        _record_buy(db_session, portfolio_id, amount=-1012.50)
    db_session.rollback()


def test_non_canonical_kind_and_source_rejected(db_session: Session, portfolio_id: int) -> None:
    with pytest.raises(EnumValidationError):
        _record_buy(db_session, portfolio_id, kind="BUY")  # not a canonical recorded-fact kind
    db_session.rollback()
    with pytest.raises(EnumValidationError):
        _record_buy(db_session, portfolio_id, source="IBKR_SYNC")  # broker sync does not exist
    db_session.rollback()


def test_position_lots_roundtrip_ordered(db_session: Session, portfolio_id: int) -> None:
    later = add_position_lot(
        db_session,
        portfolio_id=portfolio_id,
        instrument=INSTRUMENT,
        quantity=Decimal("5"),
        unit_cost=Decimal("110.00"),
        currency="USD",
        opened_at=T0 + timedelta(days=2),
        note="second declared lot",
    )
    earlier = add_position_lot(
        db_session,
        portfolio_id=portfolio_id,
        instrument=INSTRUMENT,
        quantity=Decimal("10"),
        unit_cost=Decimal("101.25"),
        currency="USD",
        opened_at=T0,
        source="IMPORT_CONFIRMED",
    )
    db_session.commit()
    lots = list_position_lots(db_session, portfolio_id)
    assert [lot.id for lot in lots] == [earlier, later]  # oldest first
    assert lots[0].quantity == Decimal("10")
    assert lots[0].source == "IMPORT_CONFIRMED"
    assert lots[1].note == "second declared lot"
    assert lots[0].instrument == INSTRUMENT


def test_empty_portfolio_lists_no_lots(db_session: Session, portfolio_id: int) -> None:
    assert list_position_lots(db_session, portfolio_id) == []
