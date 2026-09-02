"""Portfolio valuation snapshot chain: ``portfolio.valuation.refresh`` handler.

Authority boundaries (docs/03-domain/PORTFOLIO_MANUAL.md):

- the MANUAL LEDGER is the ONLY source of positions. Every position is
  derived from ``ledger_transactions`` rows the user typed in after the fact
  outside Vertex (sources ``MANUAL``/``IMPORT_CONFIRMED``). No broker account,
  position, P&L or order API is read — ever;
- corrections are compensating rows only: an event and its compensating row
  NET OUT of the derived positions (both are dropped as a pair), history is
  never edited;
- marks are the LAST SYNTHETIC CLOSES published in the
  ``markets_overview/global`` snapshot. Every valuation therefore carries
  ``mark_population = "SYNTHETIC"`` — a synthetic mark never masquerades as a
  live or real quote;
- a lot WITHOUT a usable mark is EXCLUDED and listed with its reason — it is
  never valued at zero; with nothing valued the totals stay ``None``;
- every financial figure comes from ``vertex_core.calculations.portfolio``
  (``portfolio.realized_pnl``, ``portfolio.unrealized_pnl``,
  ``portfolio.concentration``) and keeps its :class:`CalculationRecord`
  lineage (engine_version + input_hash) in the snapshot. This module only
  assembles inputs and relays results.

Enqueue topology (documented choice): ``portfolio.valuation.refresh`` is
enqueued from TWO producers —

1. the API, in the SAME transaction as every accepted ledger write (record,
   compensation, confirmed import), so a new declared fact revalues the
   portfolio;
2. the markets overview handler (``vertex_worker.markets``), after it
   PUBLISHES a changed ``markets_overview/global`` snapshot — the marks are
   read from that snapshot, so revaluation follows the quotes exactly when
   the marks actually changed (an unchanged snapshot enqueues nothing; the
   ingest path was NOT chosen because a quote that changes no published close
   cannot change any valuation).

Lot derivation (versioned, documented method ``fifo/1.0``): active
``BUY_RECORDED`` events each open one lot (``lot_id = "ledger-<event id>"``);
active ``SELL_RECORDED`` events close quantity FIFO (oldest lot first) within
one (ticker, currency) position. A sell exceeding the open quantity marks the
whole position ``oversold_position`` and excludes it fail-closed. A sell's
fee attaches to the first closing slice of that sell (the per-currency total
is independent of the attachment). Buy fees are declared cash facts and are
NOT silently folded into unrealized P&L. Every other kind (dividend, fee,
deposit, ...) is a cash event: counted, never a position.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_core.calculations.portfolio import (
    DECIMAL_PRECISION,
    ClosingTransaction,
    Fee,
    PortfolioCalculationError,
    PositionLot,
    concentration,
    realized_pnl,
    unrealized_pnl,
)
from vertex_core.contracts import CalculationRecord, make_calculation_record
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.models import LedgerTransaction, Portfolio
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.errors import HandlerError
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "LOT_METHOD_VERSION",
    "MARK_POPULATION_SYNTHETIC",
    "MARK_POPULATION_UNQUALIFIED",
    "PORTFOLIO_VALUATION_SCHEMA_VERSION",
    "REASON_INVALID_MARK",
    "REASON_MARK_CURRENCY_MISMATCH",
    "REASON_MISSING_MARK",
    "REASON_NO_MARK_SOURCE",
    "REASON_OVERSOLD_POSITION",
    "SNAPSHOT_KIND_MARKETS_SOURCE",
    "SNAPSHOT_KIND_PORTFOLIO_VALUATION",
    "TOPIC_PORTFOLIO_VALUATION_REFRESH",
    "LedgerEventView",
    "MarkQuote",
    "MarksView",
    "PortfolioValuationHandler",
    "PortfolioView",
    "build_portfolio_valuation_content",
    "derive_open_position_tickers",
    "extract_marks_from_markets_content",
    "load_ledger_event_views",
    "register_portfolio_handler",
]

log = logging.getLogger("vertex_worker.portfolio")

Clock = Callable[[], datetime]

TOPIC_PORTFOLIO_VALUATION_REFRESH = "portfolio.valuation.refresh"
"""Outbox topic: revalue one portfolio (payload ``{"portfolio_id": <int>}``)."""

SNAPSHOT_KIND_PORTFOLIO_VALUATION = "portfolio_valuation"
"""Snapshot kind; the key is the decimal portfolio id (one head per portfolio)."""

SNAPSHOT_KIND_MARKETS_SOURCE = "markets_overview"
"""The snapshot the marks are read from (``markets_overview/global``)."""

PORTFOLIO_VALUATION_SCHEMA_VERSION = "vertex.portfolio-valuation/1.0"

MARK_POPULATION_SYNTHETIC = "SYNTHETIC"
"""Retenu pour compatibilite d'import ; ce n'est PLUS la nature ecrite.

Ce nom portait une affirmation devenue fausse : « the only marks Vertex 1.0
Beta has are the synthetic last closes ». Le poste de travail sert
`markets_overview` en `population = "REAL"` sur 161 instruments IBKR, dont
zero synthetique. La nature est desormais RELAYEE depuis l'instantane source
(`MarksView.population`), jamais decidee ici.
"""

MARK_POPULATION_UNQUALIFIED = "EMPTY"
"""Nature ecrite quand la source ne declare pas la sienne — FAIL-CLOSED.

Une marque dont on ignore la nature ne peut valoriser aucune position : le
lecteur ne saurait pas ce qu'il regarde. `EMPTY` est le membre du vocabulaire
qui dit « aucune observation retenue », et c'est exactement le cas. Choisir
`SYNTHETIC` ou `REAL` par defaut fabriquerait une etiquette que personne n'a
ecrite.
"""

LOT_METHOD_VERSION = "fifo/1.0"
"""Versioned lot derivation method (module docstring); changing it is a
contract change, never a silent retroactive rewrite."""

_CODE_SHA = f"module:vertex_core.calculations.portfolio@{ENGINE_VERSION}"

# Position kinds derived into lots; every other canonical kind is cash-side.
_KIND_BUY = "BUY_RECORDED"
_KIND_SELL = "SELL_RECORDED"
_POSITION_KINDS = frozenset({_KIND_BUY, _KIND_SELL})

# Exclusion / invalidity reasons (machine tokens, stable).
REASON_MISSING_MARK = "missing_mark"
REASON_INVALID_MARK = "invalid_mark"
REASON_MARK_CURRENCY_MISMATCH = "mark_currency_mismatch"
REASON_NO_MARK_SOURCE = "no_markets_snapshot"
REASON_OVERSOLD_POSITION = "oversold_position"
REASON_MISSING_TICKER = "missing_instrument_ticker"
REASON_MISSING_QUANTITY = "missing_or_non_positive_quantity"
REASON_MISSING_PRICE = "missing_or_negative_price"
REASON_NEGATIVE_FEES = "negative_fees"


@dataclass(frozen=True)
class LedgerEventView:
    """ORM-free view of one persisted ledger transaction (append-only fact)."""

    id: int
    kind: str
    instrument: Mapping[str, Any] | None
    quantity: Decimal | None
    price: Decimal | None
    amount: Decimal
    currency: str
    fees: Decimal
    effective_at: datetime
    source: str
    compensates: int | None


@dataclass(frozen=True)
class PortfolioView:
    """ORM-free view of the portfolio being valued."""

    id: int
    name: str
    base_currency: str


@dataclass(frozen=True)
class MarkQuote:
    """One synthetic close usable as a mark (exact Decimal, labeled currency)."""

    ticker: str
    close: Decimal
    currency: str | None
    trading_day: str | None


@dataclass(frozen=True)
class MarksView:
    """Marks extracted from one published markets overview snapshot."""

    snapshot_version: int
    as_of_text: str
    closes: Mapping[str, MarkQuote]
    invalid_tickers: tuple[str, ...]
    population: str | None = None
    """Nature DECLAREE par l'instantane source, relayee verbatim.

    `None` = la source ne l'a pas declaree, ou l'a declaree hors texte. Le
    worker ne juge pas le vocabulaire ferme : il appartient a la frontiere API
    (`POPULATION_LABELS`), qui refuse une etiquette hors contrat au relais. Le
    dupliquer ici creerait un second proprietaire de la meme verite et un
    import inverse worker -> api.
    """


def _require_aware_utc(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError(f"now: expected datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    return now.astimezone(UTC)


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else _decimal_text(value)


def _calculation_meta(record: CalculationRecord) -> dict[str, Any]:
    """Lineage subset kept in the snapshot: version + hashes, no result blob."""
    return {
        "calculation_id": record.calculation_id,
        "engine_version": record.engine_version,
        "method": record.method,
        "input_hash": record.input_hash,
        "result_hash": record.result_hash,
        "status": record.status.value,
    }


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def load_ledger_event_views(session: Session, portfolio_id: int) -> list[LedgerEventView]:
    """Load every ledger event of one portfolio, oldest effective first."""
    rows = (
        session.execute(
            select(LedgerTransaction)
            .where(LedgerTransaction.portfolio_id == portfolio_id)
            .order_by(LedgerTransaction.effective_at, LedgerTransaction.id)
        )
        .scalars()
        .all()
    )
    return [
        LedgerEventView(
            id=row.id,
            kind=row.kind,
            instrument=row.instrument,
            quantity=row.quantity,
            price=row.price,
            amount=row.amount,
            currency=row.currency,
            fees=row.fees,
            effective_at=row.effective_at,
            source=row.source,
            compensates=row.compensates,
        )
        for row in rows
    ]


def extract_marks_from_markets_content(
    content: Mapping[str, Any], *, snapshot_version: int
) -> MarksView:
    """Extract per-ticker synthetic closes from a markets overview content.

    Fail-closed parsing: a ticker whose ``last_close`` is absent, not a
    decimal string, non-finite or non-positive is listed in
    ``invalid_tickers`` and yields NO mark — never a zero, never a guess.
    """
    closes: dict[str, MarkQuote] = {}
    invalid: list[str] = []
    as_of = content.get("as_of")
    as_of_text = as_of if isinstance(as_of, str) else ""
    # La nature est lue AVANT les cours : sans elle, aucun cours n'est
    # qualifiable, et un cours non qualifiable ne vaut aucune position.
    raw_population = content.get("population")
    population = (
        raw_population if isinstance(raw_population, str) and raw_population else None
    )
    if population is None:
        return MarksView(
            snapshot_version=snapshot_version,
            as_of_text=as_of_text,
            closes={},
            invalid_tickers=(),
            population=None,
        )
    sectors = content.get("sectors")
    if isinstance(sectors, Sequence) and not isinstance(sectors, (str, bytes)):
        for sector in sectors:
            if not isinstance(sector, Mapping):
                continue
            tickers = sector.get("tickers")
            if not isinstance(tickers, Sequence) or isinstance(tickers, (str, bytes)):
                continue
            for entry in tickers:
                if not isinstance(entry, Mapping):
                    continue
                ticker = entry.get("ticker")
                if not isinstance(ticker, str) or not ticker:
                    continue
                raw_close = entry.get("last_close")
                try:
                    close = Decimal(raw_close) if isinstance(raw_close, str) else None
                except InvalidOperation:
                    close = None
                if close is None or not close.is_finite() or close <= 0:
                    invalid.append(ticker)
                    continue
                raw_currency = entry.get("currency")
                currency = (
                    raw_currency if isinstance(raw_currency, str) and raw_currency else None
                )
                raw_day = entry.get("trading_day")
                trading_day = raw_day if isinstance(raw_day, str) and raw_day else None
                closes[ticker] = MarkQuote(
                    ticker=ticker, close=close, currency=currency, trading_day=trading_day
                )
    return MarksView(
        snapshot_version=snapshot_version,
        as_of_text=as_of_text,
        closes=closes,
        invalid_tickers=tuple(sorted(set(invalid))),
        population=population,
    )


# --------------------------------------------------------------------------
# Pure derivation: manual ledger -> lots and closings (no session)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _DerivedLot:
    lot_id: str
    event_id: int
    ticker: str
    currency: str
    quantity: Decimal  # original opened quantity
    remaining: Decimal  # after FIFO closings
    unit_cost: Decimal
    opened_at: datetime


@dataclass(frozen=True)
class _DerivedClosing:
    transaction_id: str
    sell_event_id: int
    lot_id: str
    ticker: str
    currency: str
    quantity: Decimal
    unit_price: Decimal
    closed_at: datetime
    fee: Decimal  # attached fee slice (whole sell fee on the first slice)


@dataclass(frozen=True)
class _DerivedPositions:
    lots: tuple[_DerivedLot, ...]
    closings: tuple[_DerivedClosing, ...]
    invalid_events: tuple[dict[str, Any], ...]
    invalid_positions: tuple[dict[str, Any], ...]
    position_events: int
    cash_events: int
    compensation_pairs: int


def _event_ticker(event: LedgerEventView) -> str | None:
    instrument = event.instrument
    if not isinstance(instrument, Mapping):
        return None
    ticker = instrument.get("ticker")
    if isinstance(ticker, str) and ticker:
        return ticker
    return None


def _position_event_error(event: LedgerEventView) -> str | None:
    if _event_ticker(event) is None:
        return REASON_MISSING_TICKER
    if event.quantity is None or event.quantity <= 0:
        return REASON_MISSING_QUANTITY
    if event.price is None or event.price < 0:
        return REASON_MISSING_PRICE
    if event.fees < 0:
        return REASON_NEGATIVE_FEES
    return None


def _derive_positions(events: Sequence[LedgerEventView]) -> _DerivedPositions:
    """Derive FIFO lots and closings from the active (non-compensated) ledger.

    A compensated event and its compensating row are dropped as a PAIR: the
    correction nets to nothing, exactly like the append-only ledger intends
    ("compensation -> net zero in the lots"). Nothing else is inferred.
    """
    compensated_ids = {e.compensates for e in events if e.compensates is not None}
    active = [
        e for e in events if e.id not in compensated_ids and e.compensates is None
    ]
    compensation_pairs = sum(1 for e in events if e.compensates is not None)

    invalid_events: list[dict[str, Any]] = []
    position_events = 0
    cash_events = 0

    # Per (ticker, currency) FIFO books, in deterministic ledger order.
    open_lots: dict[tuple[str, str], list[dict[str, Any]]] = {}
    closings: list[_DerivedClosing] = []
    oversold: dict[tuple[str, str], str] = {}

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        for event in sorted(active, key=lambda e: (e.effective_at, e.id)):
            if event.kind not in _POSITION_KINDS:
                cash_events += 1
                continue
            position_events += 1
            error = _position_event_error(event)
            if error is not None:
                invalid_events.append({"event_id": event.id, "reason": error})
                continue
            ticker = _event_ticker(event)
            # narrowing mypy, garde réelle au-dessus
            assert ticker is not None  # narrowed by _position_event_error  # noqa: S101
            book_key = (ticker, event.currency)
            if book_key in oversold:
                # The position is already invalid; keep counting, add nothing.
                continue
            if event.kind == _KIND_BUY:
                open_lots.setdefault(book_key, []).append(
                    {
                        "event_id": event.id,
                        "quantity": event.quantity,
                        "remaining": event.quantity,
                        "unit_cost": event.price,
                        "opened_at": event.effective_at,
                    }
                )
                continue
            # SELL_RECORDED: FIFO assignment against the open lots.
            to_close = event.quantity
            assert to_close is not None  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
            first_slice = True
            for lot in open_lots.get(book_key, []):
                if to_close <= 0:
                    break
                if lot["remaining"] <= 0:
                    continue
                slice_quantity = min(lot["remaining"], to_close)
                lot["remaining"] = lot["remaining"] - slice_quantity
                to_close = to_close - slice_quantity
                assert event.price is not None  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
                closings.append(
                    _DerivedClosing(
                        transaction_id=f"ledger-{event.id}:lot-{lot['event_id']}",
                        sell_event_id=event.id,
                        lot_id=f"ledger-{lot['event_id']}",
                        ticker=ticker,
                        currency=event.currency,
                        quantity=slice_quantity,
                        unit_price=event.price,
                        closed_at=event.effective_at,
                        fee=event.fees if first_slice else Decimal("0"),
                    )
                )
                first_slice = False
            if to_close > 0:
                # More sold than ever declared bought: the whole position is
                # contradictory and is excluded fail-closed, never truncated.
                oversold[book_key] = REASON_OVERSOLD_POSITION

    lots: list[_DerivedLot] = []
    for (ticker, currency), book in open_lots.items():
        if (ticker, currency) in oversold:
            continue
        for lot in book:
            lots.append(
                _DerivedLot(
                    lot_id=f"ledger-{lot['event_id']}",
                    event_id=lot["event_id"],
                    ticker=ticker,
                    currency=currency,
                    quantity=lot["quantity"],
                    remaining=lot["remaining"],
                    unit_cost=lot["unit_cost"],
                    opened_at=lot["opened_at"],
                )
            )
    kept_closings = tuple(
        c for c in closings if (c.ticker, c.currency) not in oversold
    )
    invalid_positions = tuple(
        {"ticker": ticker, "currency": currency, "reason": reason}
        for (ticker, currency), reason in sorted(oversold.items())
    )
    lots.sort(key=lambda lot: (lot.opened_at, lot.event_id))
    return _DerivedPositions(
        lots=tuple(lots),
        closings=kept_closings,
        invalid_events=tuple(invalid_events),
        invalid_positions=invalid_positions,
        position_events=position_events,
        cash_events=cash_events,
        compensation_pairs=compensation_pairs,
    )


def derive_open_position_tickers(
    events: Sequence[LedgerEventView],
) -> frozenset[str]:
    """Tickers holding at least one OPEN lot in the active manual ledger.

    Pure reuse of the SAME versioned ``fifo/1.0`` derivation the valuation
    snapshot uses (:func:`_derive_positions`) — no second lot authority. A
    position excluded fail-closed there (oversold, invalid event) yields no
    open lot here either. Consumed by the calendar chain to cross events with
    the user's declared positions; strictly read-derived, never a broker read.
    """
    derived = _derive_positions(events)
    return frozenset(lot.ticker for lot in derived.lots if lot.remaining > 0)


# --------------------------------------------------------------------------
# Pure content builder (no session, fully deterministic)
# --------------------------------------------------------------------------


def _realized_block(
    lots: Sequence[_DerivedLot],
    closings: Sequence[_DerivedClosing],
    *,
    currency: str,
    now: datetime,
) -> dict[str, Any]:
    if not closings:
        # True absence of closing events in the ledger — nothing was realized,
        # which is reported as ABSENT (no computation), never as an invented 0.
        return {"status": "ABSENT", "reason": "no_closing_recorded", "calculation": None}
    core_lots = [
        PositionLot(
            lot_id=lot.lot_id,
            quantity=lot.quantity,
            unit_cost=lot.unit_cost,
            currency=currency,
            opened_at=lot.opened_at,
        )
        for lot in lots
    ]
    core_closings = [
        ClosingTransaction(
            transaction_id=closing.transaction_id,
            lot_id=closing.lot_id,
            quantity=closing.quantity,
            unit_price=closing.unit_price,
            currency=currency,
            closed_at=closing.closed_at,
        )
        for closing in closings
    ]
    core_fees = [
        Fee(
            fee_id=f"fee-{closing.transaction_id}",
            applies_to=closing.transaction_id,
            amount=closing.fee,
            currency=currency,
        )
        for closing in closings
        if closing.fee > 0
    ]
    result = realized_pnl(core_lots, core_closings, core_fees)
    record = make_calculation_record(
        calculation_id="portfolio.realized_pnl",
        calculation_type="portfolio",
        code_sha=_CODE_SHA,
        method=f"per-lot realized P&L over the manual ledger ({LOT_METHOD_VERSION})",
        inputs={
            "lots": [lot.model_dump(mode="json") for lot in core_lots],
            "closing_transactions": [tx.model_dump(mode="json") for tx in core_closings],
            "fees": [fee.model_dump(mode="json") for fee in core_fees],
        },
        result=result.model_dump(mode="json"),
        started_at=now,
        completed_at=now,
        assumptions=(f"lot method {LOT_METHOD_VERSION}",),
    )
    return {
        "status": "OK",
        "reason": None,
        "gross_proceeds": _decimal_text(result.gross_proceeds),
        "cost_basis": _decimal_text(result.cost_basis),
        "total_fees": _decimal_text(result.total_fees),
        "total_pnl": _decimal_text(result.total_pnl),
        "lots": [
            {
                "lot_id": entry.lot_id,
                "quantity_closed": _decimal_text(entry.quantity_closed),
                "remaining_quantity": _decimal_text(entry.remaining_quantity),
                "gross_proceeds": _decimal_text(entry.gross_proceeds),
                "cost_basis": _decimal_text(entry.cost_basis),
                "fees": _decimal_text(entry.fees),
                "pnl": _decimal_text(entry.pnl),
            }
            for entry in result.lots
        ],
        "calculation": _calculation_meta(record),
    }


def build_portfolio_valuation_content(
    events: Sequence[LedgerEventView],
    *,
    portfolio: PortfolioView,
    marks: MarksView | None,
    now: datetime,
) -> dict[str, Any]:
    """Build the portfolio valuation snapshot content. Pure and deterministic.

    Identical ``events``, ``marks``, ``portfolio`` and ``now`` produce an
    identical dict. Every ledger event is accounted for (position, cash,
    compensated pair or invalid with reason); every open lot is either valued
    or excluded with a reason. Nothing is interpolated and nothing absent is
    replaced by zero.
    """
    now = _require_aware_utc(now)
    derived = _derive_positions(events)

    # -- per-lot mark resolution (fail-closed, reasons recorded) ------------
    lot_marks: dict[str, Decimal] = {}
    exclusion_reasons: dict[str, str] = {}
    open_lots = [lot for lot in derived.lots if lot.remaining > 0]
    for lot in open_lots:
        if marks is None:
            exclusion_reasons[lot.lot_id] = REASON_NO_MARK_SOURCE
            continue
        quote = marks.closes.get(lot.ticker)
        if quote is None:
            exclusion_reasons[lot.lot_id] = (
                REASON_INVALID_MARK
                if lot.ticker in marks.invalid_tickers
                else REASON_MISSING_MARK
            )
            continue
        if quote.currency is None or quote.currency != lot.currency:
            exclusion_reasons[lot.lot_id] = REASON_MARK_CURRENCY_MISMATCH
            continue
        lot_marks[lot.lot_id] = quote.close

    # -- per-currency computation through vertex_core ------------------------
    currencies = sorted(
        {lot.currency for lot in derived.lots}
        | {closing.currency for closing in derived.closings}
    )
    by_currency: list[dict[str, Any]] = []
    excluded_entries: list[dict[str, Any]] = []
    lots_valued = 0
    for currency in currencies:
        currency_lots = [lot for lot in derived.lots if lot.currency == currency]
        currency_open = [lot for lot in currency_lots if lot.remaining > 0]
        currency_closings = [
            closing for closing in derived.closings if closing.currency == currency
        ]

        realized_block = _realized_block(
            currency_lots, currency_closings, currency=currency, now=now
        )

        unrealized_block: dict[str, Any]
        concentration_block: dict[str, Any]
        if not currency_open:
            unrealized_block = {
                "status": "ABSENT",
                "reason": "no_open_lot",
                "total_unrealized": None,
                "lots": [],
                "calculation": None,
            }
            concentration_block = {
                "status": "ABSENT",
                "reason": "no_open_lot",
                "calculation": None,
            }
        else:
            core_open = [
                PositionLot(
                    lot_id=lot.lot_id,
                    quantity=lot.remaining,
                    unit_cost=lot.unit_cost,
                    currency=currency,
                    opened_at=lot.opened_at,
                )
                for lot in currency_open
            ]
            currency_marks = {
                lot.lot_id: lot_marks[lot.lot_id]
                for lot in currency_open
                if lot.lot_id in lot_marks
            }
            result = unrealized_pnl(core_open, currency_marks)
            record = make_calculation_record(
                calculation_id="portfolio.unrealized_pnl",
                calculation_type="portfolio",
                code_sha=_CODE_SHA,
                method=(
                    "per-lot unrealized P&L against synthetic last closes "
                    f"({LOT_METHOD_VERSION})"
                ),
                inputs={
                    "open_lots": [lot.model_dump(mode="json") for lot in core_open],
                    "marks": {
                        lot_id: _decimal_text(mark)
                        for lot_id, mark in sorted(currency_marks.items())
                    },
                },
                result=result.model_dump(mode="json"),
                started_at=now,
                completed_at=now,
                assumptions=(
                    "marks are SYNTHETIC last closes from markets_overview/global",
                ),
            )
            ticker_by_lot = {lot.lot_id: lot.ticker for lot in currency_open}
            lot_entries = []
            values_by_ticker: dict[str, Decimal] = {}
            with localcontext() as ctx:
                ctx.prec = DECIMAL_PRECISION
                for entry in result.lots:
                    ticker = ticker_by_lot[entry.lot_id]
                    # Descriptive marked value (quantity x mark): assembled
                    # here ONLY as the declared input of
                    # ``portfolio.concentration`` — not a registry result.
                    market_value = entry.quantity * entry.mark
                    values_by_ticker[ticker] = (
                        values_by_ticker.get(ticker, Decimal("0")) + market_value
                    )
                    lot_entries.append(
                        {
                            "lot_id": entry.lot_id,
                            "ticker": ticker,
                            "quantity": _decimal_text(entry.quantity),
                            "unit_cost": _decimal_text(entry.unit_cost),
                            "mark": _decimal_text(entry.mark),
                            "market_value": _decimal_text(market_value),
                            "unrealized_pnl": _decimal_text(entry.unrealized_pnl),
                        }
                    )
            lots_valued += len(result.lots)
            for lot_id in result.excluded_lot_ids:
                excluded_entries.append(
                    {
                        "lot_id": lot_id,
                        "ticker": ticker_by_lot[lot_id],
                        "currency": currency,
                        "reason": exclusion_reasons.get(lot_id, REASON_MISSING_MARK),
                    }
                )
            unrealized_block = {
                "status": "OK" if result.total_unrealized is not None else "ABSENT",
                "reason": None if result.total_unrealized is not None else "no_lot_valued",
                "total_unrealized": _optional_decimal_text(result.total_unrealized),
                "lots": lot_entries,
                "calculation": _calculation_meta(record),
            }
            if not values_by_ticker:
                concentration_block = {
                    "status": "ABSENT",
                    "reason": "no_lot_valued",
                    "calculation": None,
                }
            else:
                concentration_result = concentration(values_by_ticker)
                concentration_record = make_calculation_record(
                    calculation_id="portfolio.concentration",
                    calculation_type="portfolio",
                    code_sha=_CODE_SHA,
                    method="normalized marked-value weights per ticker + Herfindahl",
                    inputs={
                        "values_by_group": {
                            ticker: _decimal_text(value)
                            for ticker, value in sorted(values_by_ticker.items())
                        }
                    },
                    result=concentration_result.model_dump(mode="json"),
                    started_at=now,
                    completed_at=now,
                )
                concentration_block = {
                    "status": "OK",
                    "reason": None,
                    "total_value": _decimal_text(concentration_result.total_value),
                    "weights": {
                        ticker: _decimal_text(weight)
                        for ticker, weight in sorted(
                            concentration_result.weights.items()
                        )
                    },
                    "herfindahl_index": _decimal_text(
                        concentration_result.herfindahl_index
                    ),
                    "calculation": _calculation_meta(concentration_record),
                }

        by_currency.append(
            {
                "currency": currency,
                "unrealized": unrealized_block,
                "realized": realized_block,
                "concentration": concentration_block,
            }
        )

    excluded_entries.sort(key=lambda entry: entry["lot_id"])
    lots_open = len(open_lots)

    marks_block: dict[str, Any]
    if marks is None:
        marks_block = {
            "status": "ABSENT",
            "reason": REASON_NO_MARK_SOURCE,
            "source": None,
            "tickers_marked": 0,
            "invalid_mark_tickers": [],
        }
    else:
        marks_block = {
            "status": "OK",
            "reason": None,
            "source": {
                "kind": SNAPSHOT_KIND_MARKETS_SOURCE,
                "key": "global",
                "snapshot_version": marks.snapshot_version,
                "as_of": marks.as_of_text or None,
            },
            "tickers_marked": len(marks.closes),
            "invalid_mark_tickers": list(marks.invalid_tickers),
        }

    return {
        "schema_version": PORTFOLIO_VALUATION_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "engine_version": ENGINE_VERSION,
        "portfolio": {
            "id": portfolio.id,
            "name": portfolio.name,
            "base_currency": portfolio.base_currency,
        },
        # RELAYEE, jamais decidee : une valorisation batie sur des marques
        # reelles se declare reelle, et l'inverse aussi. Sans nature declaree
        # a la source, `EMPTY` — et aucun lot n'a ete valorise plus haut.
        "mark_population": (
            marks.population
            if marks is not None and marks.population is not None
            else MARK_POPULATION_UNQUALIFIED
        ),
        "lot_method": LOT_METHOD_VERSION,
        "marks": marks_block,
        "positions_by_currency": by_currency,
        "excluded_lots": excluded_entries,
        "coverage": {
            "events_considered": len(events),
            "position_events": derived.position_events,
            "cash_events": derived.cash_events,
            "compensation_pairs": derived.compensation_pairs,
            "invalid_events": list(derived.invalid_events),
            "invalid_positions": list(derived.invalid_positions),
            "lots_open": lots_open,
            "lots_valued": lots_valued,
            "lots_excluded": len(excluded_entries),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class PortfolioValuationHandler:
    """Handler of ``portfolio.valuation.refresh``: revalue one portfolio."""

    def __init__(self, *, clock: Clock) -> None:
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local import avoids a module cycle (handlers imports this module).
        from vertex_worker.handlers import publish_if_changed

        now = _require_aware_utc(self._clock())
        payload = message.payload
        portfolio_id = payload.get("portfolio_id") if isinstance(payload, Mapping) else None
        if not isinstance(portfolio_id, int) or isinstance(portfolio_id, bool) or portfolio_id < 1:
            raise HandlerError(
                f"message {message.id}: payload carries no valid portfolio_id",
                code="PORTFOLIO_ID_INVALID",
            )
        portfolio_row = session.get(Portfolio, portfolio_id)
        if portfolio_row is None:
            raise HandlerError(
                f"message {message.id}: portfolio {portfolio_id} does not exist",
                code="PORTFOLIO_UNKNOWN",
            )
        portfolio = PortfolioView(
            id=portfolio_row.id,
            name=portfolio_row.name,
            base_currency=portfolio_row.base_currency,
        )
        events = load_ledger_event_views(session, portfolio_id)
        markets_snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_MARKETS_SOURCE, key="global"
        )
        marks = (
            None
            if markets_snapshot is None
            else extract_marks_from_markets_content(
                markets_snapshot.content, snapshot_version=markets_snapshot.version
            )
        )
        try:
            content = build_portfolio_valuation_content(
                events, portfolio=portfolio, marks=marks, now=now
            )
        except PortfolioCalculationError as exc:
            # Contradictory ledger input the derivation could not pre-screen:
            # fail the message with a typed code, never publish a partial lie.
            raise HandlerError(str(exc), code="PORTFOLIO_CALCULATION_REJECTED") from exc
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_PORTFOLIO_VALUATION,
            key=str(portfolio.id),
            content=content,
            as_of=now,
        )
        if published is None:
            log.info(
                "portfolio valuation unchanged (portfolio_id=%s, message_id=%s)",
                portfolio.id,
                message.id,
            )
        else:
            log.info(
                "portfolio valuation published version=%s (portfolio_id=%s, message_id=%s)",
                published.version,
                portfolio.id,
                message.id,
            )


def register_portfolio_handler(registry: HandlerRegistry, *, clock: Clock) -> None:
    """Register the portfolio valuation handler on its topic."""
    registry.register(
        TOPIC_PORTFOLIO_VALUATION_REFRESH, PortfolioValuationHandler(clock=clock)
    )
