"""Ledger compensation uniqueness under concurrency (append-only registry).

Reproducer for a confirmed P1 defect: ``record_ledger_event`` checked
"already compensated" with SELECT-then-INSERT and no UNIQUE constraint on
``ledger_transactions.compensates``, so two concurrent transactions could both
pass the check and commit two compensating rows — net sum +amount instead of
0, silently corrupting the append-only ledger that is the portfolio's only
authority.

Contract under test: a partial unique index on ``compensates`` makes the
database itself reject the second compensating row whatever the interleaving,
and the application converts that violation to ``AlreadyCompensatedError``.

This is a real-concurrency test (ADR-006 requires concurrency tests for the
persistence layer): it uses two live sessions and a worker thread, with a
bounded lock-wait poll — no fixed sleep, no unbounded wait. All data is
SYNTHETIC user input.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vertex_persistence.errors import AlreadyCompensatedError
from vertex_persistence.models import LedgerTransaction
from vertex_persistence.repository import (
    compensate_ledger_event,
    create_portfolio,
    record_ledger_event,
)

UTC = UTC
T0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)
INSTRUMENT = {"symbol": "SYN", "asset_class": "STOCK", "exchange": "SYNTH", "currency": "USD"}

_LOCK_WAIT_TIMEOUT_SECONDS = 15.0
_LOCK_POLL_INTERVAL_SECONDS = 0.01


def _record_original_event(session: Session) -> int:
    portfolio_id = create_portfolio(session, name="synthetic-race", base_currency="CHF")
    return record_ledger_event(
        session,
        portfolio_id=portfolio_id,
        kind="BUY_RECORDED",
        amount=Decimal("-1012.50"),
        currency="USD",
        fees=Decimal("1.25"),
        effective_at=T0,
        recorded_at=T0,
        instrument=INSTRUMENT,
        quantity=Decimal("10"),
        price=Decimal("101.25"),
        note="user-typed past fact",
    )


def _count_compensations(session: Session, event_id: int) -> int:
    return session.execute(
        select(func.count())
        .select_from(LedgerTransaction)
        .where(LedgerTransaction.compensates == event_id)
    ).scalar_one()


def test_second_compensating_row_rejected_by_database(db_session: Session) -> None:
    """The unique index holds for EVERY SQL client, not only for this ORM."""
    event_id = _record_original_event(db_session)
    db_session.commit()
    compensate_ledger_event(
        db_session, event_id=event_id, note="first correction", recorded_at=T0
    )
    db_session.commit()

    # A rogue direct INSERT (bypassing the application pre-check) must fail.
    with pytest.raises(IntegrityError, match="uq_ledger_transactions_compensates"):
        db_session.execute(
            text(
                "INSERT INTO ledger_transactions "
                "(portfolio_id, kind, amount, currency, fees, effective_at, "
                " recorded_at, source, note, compensates) "
                "SELECT portfolio_id, kind, -amount, currency, -fees, effective_at, "
                "       recorded_at, source, 'rogue duplicate compensation', id "
                "FROM ledger_transactions WHERE id = :event_id"
            ),
            {"event_id": event_id},
        )
    db_session.rollback()
    assert _count_compensations(db_session, event_id) == 1


def _wait_until_blocked_or_done(engine: Engine, thread: threading.Thread) -> None:
    """Bounded poll: return once the worker thread finished or waits on a lock."""
    deadline = time.monotonic() + _LOCK_WAIT_TIMEOUT_SECONDS
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        while time.monotonic() < deadline:
            if not thread.is_alive():
                return
            waiting = connection.execute(
                text("SELECT count(*) FROM pg_locks WHERE granted = false")
            ).scalar_one()
            if waiting:
                return
            time.sleep(_LOCK_POLL_INTERVAL_SECONDS)
    raise AssertionError(
        "worker thread neither finished nor blocked on a lock within the timeout"
    )


def test_concurrent_double_compensation_yields_single_row(migrated_engine: Engine) -> None:
    """Two racing compensations: exactly one row lands, the other is rejected typed."""
    with Session(migrated_engine) as setup:
        event_id = _record_original_event(setup)
        setup.commit()

    outcome: dict[str, str] = {}

    def concurrent_compensator() -> None:
        with Session(migrated_engine) as session_b:
            try:
                compensate_ledger_event(
                    session_b,
                    event_id=event_id,
                    note="concurrent correction B",
                    recorded_at=T0,
                )
                session_b.commit()
                outcome["b"] = "committed"
            except AlreadyCompensatedError:
                session_b.rollback()
                outcome["b"] = "rejected"

    with Session(migrated_engine) as session_a:
        # A passes the pre-check and flushes its compensating row, uncommitted:
        # the classic window in which B's own pre-check cannot see A's row.
        compensate_ledger_event(
            session_a, event_id=event_id, note="concurrent correction A", recorded_at=T0
        )
        worker = threading.Thread(target=concurrent_compensator)
        worker.start()
        _wait_until_blocked_or_done(migrated_engine, worker)
        session_a.commit()
    worker.join(timeout=_LOCK_WAIT_TIMEOUT_SECONDS)
    assert not worker.is_alive()

    with Session(migrated_engine) as check:
        # The append-only registry stayed coherent: one compensation, net zero.
        assert _count_compensations(check, event_id) == 1
        total = check.execute(select(func.sum(LedgerTransaction.amount))).scalar_one()
        assert total == Decimal("0.00")
    assert outcome["b"] == "rejected"
