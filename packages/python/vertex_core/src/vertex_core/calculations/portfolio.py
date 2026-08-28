"""Portfolio calculations: FX conversion, realized and unrealized P&L, concentration.

Implements the calculation registry entries ``portfolio.fx_conversion``,
``portfolio.realized_pnl``, ``portfolio.unrealized_pnl`` and
``portfolio.concentration``.

Population rule
---------------
Every function operates on exactly ONE population per call: either the user's
manually declared real ledger, or one clearly labelled hypothetical scenario
set. Real and hypothetical lots are never mixed inside a single call; keeping
the populations apart is part of the caller's contract and is deliberately not
re-encoded here as a flag, so a mixed input cannot even be expressed.

Numeric policy
--------------
Money stays ``Decimal`` end to end (no float64 core is needed in this module).
All arithmetic runs in a pinned local context of ``DECIMAL_PRECISION`` (28)
significant digits with ``ROUND_HALF_EVEN``. Multiplication, addition and
subtraction on realistic magnitudes are exact; division (concentration
weights) is correct to 28 significant digits. Documented comparison
tolerances: ``FX_ROUND_TRIP_RELATIVE_TOLERANCE`` and ``WEIGHT_SUM_TOLERANCE``,
both ``1e-20``.

Fail-closed rules
-----------------
Invalid input raises a typed :class:`PortfolioCalculationError` subclass.
Absent data stays absent: a lot without a mark is excluded and reported in
``excluded_lot_ids`` — it is never valued at zero — and a fully unmarked
population yields ``total_unrealized = None``, never ``0``.

This module is analysis-only bookkeeping over user-declared ledger entries.
It contains no transactional capability and no broker account linkage.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Optional

from pydantic import Field, model_validator

from vertex_core.contracts.types import (
    ContractModel,
    CurrencyCode,
    FiniteDecimal,
    FrozenStrMapping,
    NonEmptyStr,
    NonNegativeDecimal,
    PositiveDecimal,
    UtcDatetime,
    ensure_utc,
)

__all__ = [
    "DECIMAL_PRECISION",
    "FX_ROUND_TRIP_RELATIVE_TOLERANCE",
    "WEIGHT_SUM_TOLERANCE",
    "PortfolioCalculationError",
    "LedgerError",
    "LotConservationError",
    "CurrencyMismatchError",
    "MarkError",
    "FxRateError",
    "ConcentrationError",
    "PositionLot",
    "ClosingTransaction",
    "Fee",
    "LotRealizedPnl",
    "RealizedPnlResult",
    "LotUnrealizedPnl",
    "UnrealizedPnlResult",
    "ConcentrationResult",
    "fx_conversion",
    "realized_pnl",
    "unrealized_pnl",
    "concentration",
]

DECIMAL_PRECISION = 28
"""Pinned significant digits for every Decimal computation in this module."""

FX_ROUND_TRIP_RELATIVE_TOLERANCE = Decimal("1e-20")
"""Documented tolerance for the fx round-trip invariant (relative to max(1, |amount|))."""

WEIGHT_SUM_TOLERANCE = Decimal("1e-20")
"""Documented tolerance for ``sum(concentration weights) == 1``."""

_ZERO = Decimal("0")


class PortfolioCalculationError(ValueError):
    """Base typed error for every invalid portfolio-calculation input (fail-closed)."""


class LedgerError(PortfolioCalculationError):
    """The declared ledger is not internally consistent (unknown/duplicate references, empty population)."""


class LotConservationError(LedgerError):
    """Closing transactions attempt to close more quantity than the lot holds."""


class CurrencyMismatchError(LedgerError):
    """Entries of one call must share a single currency; FX conversion is a separate step."""


class MarkError(PortfolioCalculationError):
    """A mark price is present but invalid (wrong type, non-finite or negative)."""


class FxRateError(PortfolioCalculationError):
    """Invalid FX conversion input (type, finiteness, sign or naive quote timestamp)."""


class ConcentrationError(PortfolioCalculationError):
    """Invalid concentration input (empty grouping, negative value, non-positive denominator)."""


class PositionLot(ContractModel):
    """One open lot of the single population being analysed.

    ``quantity`` is the strictly positive number of units held; ``unit_cost``
    is the per-unit acquisition cost in ``currency``. Lots are declared
    manually by the user (source ``MANUAL``); no external account source ever
    creates or mutates them. Short lots are out of scope of this module
    (a capability without a real implementation stays NOT_IMPLEMENTED rather
    than being approximated here).
    """

    lot_id: NonEmptyStr
    quantity: PositiveDecimal
    unit_cost: NonNegativeDecimal
    currency: CurrencyCode
    opened_at: UtcDatetime


class ClosingTransaction(ContractModel):
    """A manually recorded closing of part or all of one lot.

    ``quantity`` is the strictly positive number of units closed from
    ``lot_id`` at ``unit_price`` per unit. This is an after-the-fact ledger
    entry typed by the user; it is a record, never an instruction.
    """

    transaction_id: NonEmptyStr
    lot_id: NonEmptyStr
    quantity: PositiveDecimal
    unit_price: NonNegativeDecimal
    currency: CurrencyCode
    closed_at: UtcDatetime


class Fee(ContractModel):
    """One recorded fee or commission attached to a ledger entry by id.

    ``applies_to`` names the ``transaction_id`` (realized P&L) or the
    ``lot_id`` (unrealized P&L) the fee belongs to. The non-negative amount
    always reduces the corresponding P&L. An absent fee event means "no fee
    was declared" — the ledger is event-based, so this is true absence of an
    event, not a missing measurement.
    """

    fee_id: NonEmptyStr
    applies_to: NonEmptyStr
    amount: NonNegativeDecimal
    currency: CurrencyCode


class LotRealizedPnl(ContractModel):
    """Realized P&L contribution of one lot (only lots actually touched appear)."""

    lot_id: NonEmptyStr
    quantity_closed: PositiveDecimal
    remaining_quantity: NonNegativeDecimal
    gross_proceeds: NonNegativeDecimal
    cost_basis: NonNegativeDecimal
    fees: NonNegativeDecimal
    pnl: FiniteDecimal


class RealizedPnlResult(ContractModel):
    """Balanced realized P&L ledger: total == proceeds - cost basis - fees, exactly."""

    currency: CurrencyCode
    gross_proceeds: NonNegativeDecimal
    cost_basis: NonNegativeDecimal
    total_fees: NonNegativeDecimal
    total_pnl: FiniteDecimal
    lots: tuple[LotRealizedPnl, ...]

    @model_validator(mode="after")
    def _check_balanced_ledger(self) -> "RealizedPnlResult":
        if self.total_pnl != self.gross_proceeds - self.cost_basis - self.total_fees:
            raise ValueError("unbalanced ledger: total_pnl must equal proceeds - cost basis - fees")
        if self.lots:
            if self.total_pnl != sum((entry.pnl for entry in self.lots), _ZERO):
                raise ValueError("unbalanced ledger: total_pnl must equal the sum of per-lot pnl")
        elif self.total_pnl != _ZERO:
            raise ValueError("unbalanced ledger: no closed lot but non-zero total_pnl")
        return self


class LotUnrealizedPnl(ContractModel):
    """Unrealized P&L of one lot valued against its mark."""

    lot_id: NonEmptyStr
    quantity: PositiveDecimal
    unit_cost: NonNegativeDecimal
    mark: NonNegativeDecimal
    fees: NonNegativeDecimal
    unrealized_pnl: FiniteDecimal


class UnrealizedPnlResult(ContractModel):
    """Unrealized P&L over the marked lots only.

    Lots without a mark are listed in ``excluded_lot_ids`` and contribute
    nothing; when no lot could be valued, ``total_unrealized`` is ``None``
    (absence), never ``0``.
    """

    currency: CurrencyCode
    total_unrealized: Optional[FiniteDecimal]
    lots: tuple[LotUnrealizedPnl, ...]
    excluded_lot_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check_absence_is_not_zero(self) -> "UnrealizedPnlResult":
        if (self.total_unrealized is None) != (len(self.lots) == 0):
            raise ValueError("total_unrealized must be None exactly when no lot could be valued")
        if self.lots and self.total_unrealized != sum((entry.unrealized_pnl for entry in self.lots), _ZERO):
            raise ValueError("aggregation must be linear: total must equal the sum of per-lot pnl")
        return self


class ConcentrationResult(ContractModel):
    """Normalized exposure weights per group plus the Herfindahl index."""

    total_value: PositiveDecimal
    weights: FrozenStrMapping
    herfindahl_index: FiniteDecimal


def _as_tuple_of(values: Sequence[object], expected_type: type, name: str) -> tuple:
    if isinstance(values, (str, bytes)):
        raise LedgerError(f"{name} must be a sequence of {expected_type.__name__} instances")
    items = tuple(values)
    for item in items:
        if not isinstance(item, expected_type):
            raise LedgerError(
                f"{name} must contain only {expected_type.__name__} instances, got {type(item).__name__}"
            )
    return items


def _indexed_lots(lots: tuple) -> "dict[str, PositionLot]":
    lot_by_id: dict[str, PositionLot] = {}
    for lot in lots:
        if lot.lot_id in lot_by_id:
            raise LedgerError(f"duplicate lot_id: {lot.lot_id!r}")
        lot_by_id[lot.lot_id] = lot
    return lot_by_id


def _single_currency(lots: tuple) -> str:
    currency = lots[0].currency
    for lot in lots:
        if lot.currency != currency:
            raise CurrencyMismatchError(
                f"lot {lot.lot_id!r} is in {lot.currency}, expected {currency}: "
                "one call handles exactly one currency (convert with fx_conversion first)"
            )
    return currency


def fx_conversion(money: Decimal, fx_rate: Decimal, quote_as_of: datetime) -> Decimal:
    """Convert ``money`` (source currency units) with ``fx_rate`` (target per source).

    Registry: ``portfolio.fx_conversion``. The freshness gate
    (``fx_fresh_for_usage``) is owned by data_quality upstream; here
    ``quote_as_of`` is validated to be timezone-aware (naive input rejected)
    so the caller can always prove which instant the rate belongs to. The
    arithmetic is one Decimal multiplication in a pinned
    ``DECIMAL_PRECISION``-digit context; negative zero is normalized to zero.

    Round-trip invariant (tested): converting with ``fx_rate`` and back with
    ``1/fx_rate`` (inverse taken at 28 significant digits) returns the
    original amount within ``FX_ROUND_TRIP_RELATIVE_TOLERANCE`` relative to
    ``max(1, |money|)``.

    Raises :class:`FxRateError` for non-``Decimal`` input, non-finite values,
    a non-positive rate or a naive ``quote_as_of`` (fail-closed).
    """
    if not isinstance(money, Decimal):
        raise FxRateError(f"money must be a Decimal instance, got {type(money).__name__}")
    if not isinstance(fx_rate, Decimal):
        raise FxRateError(f"fx_rate must be a Decimal instance, got {type(fx_rate).__name__}")
    if not money.is_finite():
        raise FxRateError("money must be finite: NaN and infinities are rejected")
    if not fx_rate.is_finite() or fx_rate <= _ZERO:
        raise FxRateError("fx_rate must be a finite, strictly positive Decimal")
    if not isinstance(quote_as_of, datetime):
        raise FxRateError(f"quote_as_of must be a datetime, got {type(quote_as_of).__name__}")
    try:
        ensure_utc(quote_as_of)
    except ValueError as exc:
        raise FxRateError(str(exc)) from exc
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        result = money * fx_rate
    if result.is_zero() and result.is_signed():
        result = result.copy_negate()
    return result


def realized_pnl(
    lots: Sequence[PositionLot],
    closing_transactions: Sequence[ClosingTransaction],
    fees: Sequence[Fee] = (),
) -> RealizedPnlResult:
    """Realized P&L of one declared population, lot by lot, in one currency.

    Registry: ``portfolio.realized_pnl``. Gates and invariants:

    - balanced ledger: every closing transaction references a declared lot,
      every fee references a declared transaction, ids are unique, and
      ``total_pnl == gross_proceeds - cost_basis - total_fees`` exactly;
    - lot conservation: per lot, the summed closed quantity never exceeds the
      open quantity, otherwise :class:`LotConservationError`;
    - single currency per call (:class:`CurrencyMismatchError` otherwise);
      FX conversion is a separate, explicit step.

    All arithmetic is ``Decimal`` in the pinned 28-digit context. Cost basis
    uses the lot's own ``unit_cost`` (the lot method that produced the lots is
    chosen and versioned upstream). Lots never touched by a closing
    transaction are absent from the breakdown — absence, not zero rows.
    """
    lot_seq = _as_tuple_of(lots, PositionLot, "lots")
    tx_seq = _as_tuple_of(closing_transactions, ClosingTransaction, "closing_transactions")
    fee_seq = _as_tuple_of(fees, Fee, "fees")
    if not lot_seq:
        raise LedgerError("empty lot population: realized P&L requires at least one declared lot")
    lot_by_id = _indexed_lots(lot_seq)
    currency = _single_currency(lot_seq)

    tx_by_id: dict[str, ClosingTransaction] = {}
    for tx in tx_seq:
        if tx.transaction_id in tx_by_id:
            raise LedgerError(f"duplicate transaction_id: {tx.transaction_id!r}")
        lot = lot_by_id.get(tx.lot_id)
        if lot is None:
            raise LedgerError(
                f"closing transaction {tx.transaction_id!r} references unknown lot {tx.lot_id!r}"
            )
        if tx.currency != currency:
            raise CurrencyMismatchError(
                f"closing transaction {tx.transaction_id!r} is in {tx.currency}, expected {currency}"
            )
        tx_by_id[tx.transaction_id] = tx

    fees_by_tx: dict[str, Decimal] = {}
    seen_fee_ids: set = set()
    for fee in fee_seq:
        if fee.fee_id in seen_fee_ids:
            raise LedgerError(f"duplicate fee_id: {fee.fee_id!r}")
        seen_fee_ids.add(fee.fee_id)
        if fee.applies_to not in tx_by_id:
            raise LedgerError(
                f"fee {fee.fee_id!r} references unknown closing transaction {fee.applies_to!r}"
            )
        if fee.currency != currency:
            raise CurrencyMismatchError(f"fee {fee.fee_id!r} is in {fee.currency}, expected {currency}")
        fees_by_tx[fee.applies_to] = fees_by_tx.get(fee.applies_to, _ZERO) + fee.amount

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        closed_by_lot: dict[str, Decimal] = {}
        proceeds_by_lot: dict[str, Decimal] = {}
        cost_by_lot: dict[str, Decimal] = {}
        fees_by_lot: dict[str, Decimal] = {}
        for tx in tx_seq:
            lot = lot_by_id[tx.lot_id]
            closed = closed_by_lot.get(tx.lot_id, _ZERO) + tx.quantity
            if closed > lot.quantity:
                raise LotConservationError(
                    f"lot {tx.lot_id!r}: closed quantity {closed} exceeds open quantity {lot.quantity}"
                )
            closed_by_lot[tx.lot_id] = closed
            # No fee event recorded for this transaction means no fee was
            # declared (true absence of a ledger event, not a missing value).
            fee_amount = fees_by_tx.get(tx.transaction_id, _ZERO)
            proceeds_by_lot[tx.lot_id] = proceeds_by_lot.get(tx.lot_id, _ZERO) + tx.quantity * tx.unit_price
            cost_by_lot[tx.lot_id] = cost_by_lot.get(tx.lot_id, _ZERO) + tx.quantity * lot.unit_cost
            fees_by_lot[tx.lot_id] = fees_by_lot.get(tx.lot_id, _ZERO) + fee_amount

        entries = []
        gross_proceeds = _ZERO
        cost_basis = _ZERO
        total_fees = _ZERO
        total_pnl = _ZERO
        for lot in lot_seq:  # deterministic: input order of the lot declaration
            closed = closed_by_lot.get(lot.lot_id)
            if closed is None:
                continue
            proceeds = proceeds_by_lot[lot.lot_id]
            cost = cost_by_lot[lot.lot_id]
            lot_fees = fees_by_lot[lot.lot_id]
            pnl = proceeds - cost - lot_fees
            entries.append(
                LotRealizedPnl(
                    lot_id=lot.lot_id,
                    quantity_closed=closed,
                    remaining_quantity=lot.quantity - closed,
                    gross_proceeds=proceeds,
                    cost_basis=cost,
                    fees=lot_fees,
                    pnl=pnl,
                )
            )
            gross_proceeds += proceeds
            cost_basis += cost
            total_fees += lot_fees
            total_pnl += pnl

    return RealizedPnlResult(
        currency=currency,
        gross_proceeds=gross_proceeds,
        cost_basis=cost_basis,
        total_fees=total_fees,
        total_pnl=total_pnl,
        lots=tuple(entries),
    )


def unrealized_pnl(
    open_lots: Sequence[PositionLot],
    marks: Mapping[str, Decimal],
    fees: Sequence[Fee] = (),
) -> UnrealizedPnlResult:
    """Unrealized P&L of one declared population against per-lot mark prices.

    Registry: ``portfolio.unrealized_pnl``. ``marks`` maps ``lot_id`` to the
    per-unit mark price (a ``Decimal`` in the population's currency); the
    freshness of those marks (``fresh_mark`` gate) is owned by data_quality
    upstream. Mark keys that match no declared lot are ignored.

    Absence handling (fail-closed, never zero):

    - a lot whose mark is ABSENT is excluded from the aggregate and reported
      in ``excluded_lot_ids`` — its fees are excluded with it;
    - a mark that is PRESENT but invalid (non-``Decimal``, non-finite or
      negative) is corrupt input and raises :class:`MarkError`;
    - when no lot could be valued, ``total_unrealized`` is ``None``.

    Invariant (tested): aggregation is linear — ``total_unrealized`` equals
    the exact sum of the per-lot contributions
    ``quantity * (mark - unit_cost) - fees``.
    """
    lot_seq = _as_tuple_of(open_lots, PositionLot, "open_lots")
    fee_seq = _as_tuple_of(fees, Fee, "fees")
    if not lot_seq:
        raise LedgerError("empty open-lot population: nothing can be valued")
    if not isinstance(marks, Mapping):
        raise MarkError(f"marks must be a mapping of lot_id to Decimal, got {type(marks).__name__}")
    lot_by_id = _indexed_lots(lot_seq)
    currency = _single_currency(lot_seq)

    fees_by_lot: dict[str, Decimal] = {}
    seen_fee_ids: set = set()
    for fee in fee_seq:
        if fee.fee_id in seen_fee_ids:
            raise LedgerError(f"duplicate fee_id: {fee.fee_id!r}")
        seen_fee_ids.add(fee.fee_id)
        if fee.applies_to not in lot_by_id:
            raise LedgerError(f"fee {fee.fee_id!r} references unknown lot {fee.applies_to!r}")
        if fee.currency != currency:
            raise CurrencyMismatchError(f"fee {fee.fee_id!r} is in {fee.currency}, expected {currency}")
        fees_by_lot[fee.applies_to] = fees_by_lot.get(fee.applies_to, _ZERO) + fee.amount

    included = []
    excluded_lot_ids = []
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        total: Optional[Decimal] = None
        for lot in lot_seq:  # deterministic: input order of the lot declaration
            if lot.lot_id not in marks:
                # Absent mark: the lot is excluded and reported, never valued at zero.
                excluded_lot_ids.append(lot.lot_id)
                continue
            mark = marks[lot.lot_id]
            if not isinstance(mark, Decimal):
                raise MarkError(f"mark for lot {lot.lot_id!r} must be a Decimal, got {type(mark).__name__}")
            if not mark.is_finite() or mark < _ZERO:
                raise MarkError(f"mark for lot {lot.lot_id!r} must be finite and non-negative")
            lot_fees = fees_by_lot.get(lot.lot_id, _ZERO)
            pnl = lot.quantity * (mark - lot.unit_cost) - lot_fees
            included.append(
                LotUnrealizedPnl(
                    lot_id=lot.lot_id,
                    quantity=lot.quantity,
                    unit_cost=lot.unit_cost,
                    mark=mark,
                    fees=lot_fees,
                    unrealized_pnl=pnl,
                )
            )
            total = pnl if total is None else total + pnl

    return UnrealizedPnlResult(
        currency=currency,
        total_unrealized=total,
        lots=tuple(included),
        excluded_lot_ids=tuple(excluded_lot_ids),
    )


def concentration(values_by_group: Mapping[str, Decimal]) -> ConcentrationResult:
    """Exposure concentration of one marked population, grouped by the caller.

    Registry: ``portfolio.concentration``. ``values_by_group`` maps a group
    label (sector, issuer, asset class, ...) to its non-negative marked value
    in one common currency; the grouping itself is the caller's choice. If
    the caller already holds weights, passing them unchanged works: weights
    are values normalized by their sum.

    Gate ``positive_denominator``: the summed value must be strictly
    positive, otherwise :class:`ConcentrationError`. Invariant (tested):
    ``sum(weights) == 1`` within ``WEIGHT_SUM_TOLERANCE``. Also returns the
    Herfindahl index ``sum(w**2)`` as a scalar concentration measure.
    """
    if not isinstance(values_by_group, Mapping):
        raise ConcentrationError(
            f"values_by_group must be a mapping of group label to Decimal, got {type(values_by_group).__name__}"
        )
    if not values_by_group:
        raise ConcentrationError("empty grouping: concentration requires at least one group")
    for key, value in values_by_group.items():
        if not isinstance(key, str) or not key:
            raise ConcentrationError("group labels must be non-empty strings")
        if not isinstance(value, Decimal):
            raise ConcentrationError(f"value for group {key!r} must be a Decimal, got {type(value).__name__}")
        if not value.is_finite() or value < _ZERO:
            raise ConcentrationError(f"value for group {key!r} must be finite and non-negative")

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        total = _ZERO
        for value in values_by_group.values():
            total += value
        if total <= _ZERO:
            raise ConcentrationError("positive_denominator gate failed: total group value must be > 0")
        weights = {key: value / total for key, value in values_by_group.items()}
        herfindahl = _ZERO
        for weight in weights.values():
            herfindahl += weight * weight

    return ConcentrationResult(total_value=total, weights=weights, herfindahl_index=herfindahl)
