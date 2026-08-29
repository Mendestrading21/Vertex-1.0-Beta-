"""SYNTHETIC test doubles for the portfolio routes (unit tests only).

Everything here carries explicit SYNTHETIC status and reaches the
application exclusively through ``app.dependency_overrides`` — no production
code path can construct or receive these objects.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from vertex_persistence.repository.snapshots import CurrentSnapshot

from vertex_api.portfolio import (
    LedgerEntryView,
    LotView,
    PortfolioOverview,
    ValidatedImportRow,
)

__all__ = ["FIXED_NOW", "FakePortfolioGateway", "fixed_clock", "make_entry"]

FIXED_NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


def fixed_clock() -> datetime:
    return FIXED_NOW


def make_entry(
    entry_id: int = 1,
    *,
    kind: str = "BUY_RECORDED",
    ticker: Optional[str] = "SYN-A",
    quantity: Optional[str] = "10",
    price: Optional[str] = "100",
    amount: str = "-1000",
    currency: str = "SYN",
    fees: str = "0",
    effective_at: Optional[datetime] = None,
    note: Optional[str] = None,
    compensates: Optional[int] = None,
) -> LedgerEntryView:
    at = effective_at or datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)
    return LedgerEntryView(
        id=entry_id,
        kind=kind,
        instrument=None if ticker is None else {"ticker": ticker},
        quantity=None if quantity is None else Decimal(quantity),
        price=None if price is None else Decimal(price),
        amount=Decimal(amount),
        currency=currency,
        fees=Decimal(fees),
        effective_at=at,
        recorded_at=at,
        source="MANUAL",
        note=note,
        compensates=compensates,
    )


class FakePortfolioGateway:
    """SYNTHETIC in-memory implementation of the ``PortfolioGateway`` protocol.

    Records every write call so tests assert exactly what would have been
    persisted; scriptable exceptions emulate the repository's typed errors.
    """

    def __init__(
        self,
        *,
        transactions: Sequence[LedgerEntryView] = (),
        lots: Sequence[LotView] = (),
        valuation: Optional[CurrentSnapshot] = None,
        compensate_error: Optional[Exception] = None,
    ) -> None:
        self.transactions = tuple(transactions)
        self.lots = tuple(lots)
        self.valuation = valuation
        self.compensate_error = compensate_error
        self.recorded: list[dict[str, Any]] = []
        self.compensated: list[dict[str, Any]] = []
        self.imported: list[Sequence[ValidatedImportRow]] = []
        self._next_id = 100

    def overview(self) -> PortfolioOverview:
        return PortfolioOverview(
            portfolio_id=1,
            name="main",
            base_currency="USD",
            transactions=self.transactions,
            lots=self.lots,
            valuation=self.valuation,
        )

    def record_transaction(
        self,
        *,
        kind: str,
        instrument: Optional[Mapping[str, Any]],
        quantity: Optional[Decimal],
        price: Optional[Decimal],
        amount: Decimal,
        currency: str,
        fees: Decimal,
        effective_at: datetime,
        note: Optional[str],
        now: datetime,
    ) -> int:
        self._next_id += 1
        self.recorded.append(
            {
                "kind": kind,
                "instrument": instrument,
                "quantity": quantity,
                "price": price,
                "amount": amount,
                "currency": currency,
                "fees": fees,
                "effective_at": effective_at,
                "note": note,
                "now": now,
            }
        )
        return self._next_id

    def compensate_transaction(self, *, event_id: int, note: str, now: datetime) -> int:
        if self.compensate_error is not None:
            raise self.compensate_error
        self._next_id += 1
        self.compensated.append({"event_id": event_id, "note": note, "now": now})
        return self._next_id

    def record_import(
        self, rows: Sequence[ValidatedImportRow], *, now: datetime
    ) -> list[int]:
        self.imported.append(tuple(rows))
        ids = []
        for _ in rows:
            self._next_id += 1
            ids.append(self._next_id)
        return ids
