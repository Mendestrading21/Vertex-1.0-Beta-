"""Performance snapshot chain (page 10): ``performance.refresh`` handler.

The handler rebuilds, for ONE portfolio, the DAILY valuation series and the
registry performance calculations, then publishes ``performance/{portfolio_id}``:

- one valuation point per synthetic trading day carrying a close (from the
  persisted daily-quote observations), starting at the first ledger fact:
  portfolio value = FIFO open lots marked at that day's closes + cumulative
  ledger cash. The FIFO lots are derived by the SAME versioned method as the
  portfolio valuation chain — ``vertex_worker.portfolio._derive_positions``
  (``fifo/1.0``) is imported and reused, never duplicated;
- a day whose marks cannot value every open lot (missing close, currency
  mismatch, oversold/contradictory ledger) is EXCLUDED with its reason — it
  is never valued at zero and never interpolated;
- external cashflows are the dated ``DEPOSIT``/``WITHDRAWAL`` ledger facts
  (compensating pairs net out arithmetically);
- TWR, XIRR and drawdown all run through ``vertex_core.calculations
  .performance`` (registry ``performance.twr`` / ``performance.xirr`` /
  ``performance.drawdown``) and each keeps its :class:`CalculationRecord`
  lineage in the snapshot. Gates are relayed honestly: incomplete cashflow
  boundaries yield ``INSUFFICIENT_DATA`` with a reason, an unbracketable or
  non-unique XIRR root yields ``INVALID`` with a reason — never a number;
- GROSS and NET are explicit and separate. Documented net convention:
  ``net_value(day) = gross_value(day) - cumulative declared ledger fees up
  to that day`` (the ``fees`` column of every ledger fact); external flows
  are identical for both series. Fees are never silently folded anywhere else;
- the monthly heatmap regroups the AUTHORITATIVE gross TWR period returns by
  period-end month (chain-linked product — the same formula that defines the
  total, no second engine); incomplete months are explicitly marked;
- population is exactly ``SYNTHETIC_MARKS_REAL_LEDGER``: synthetic marks
  crossed with the user's real declared ledger. This population is NEVER
  aggregated with any other (no real-mark, hypothetical or demo figure ever
  blends into this snapshot);
- coverage reports valuable days / total close days, with every exclusion.

Valuation conventions (documented, tested):

- valuation instant of a trading day D = D at 23:59:59 UTC (end of day): all
  ledger facts effective on or before that instant are included;
- TWR cashflow timing: a flow effective on day D (thus before D's close)
  adjusts the capital of the period ENDING at D's close, so it is stamped at
  the valuation instant of the PREVIOUS valued day (``vertex_core`` stamps
  flows at period start). Flows on or before the first valued day are part
  of the opening valuation; flows after the last valued day cannot affect
  any measured period and are counted, not used. TWR requires every flow day
  strictly inside the series to BE a valued day (complete boundaries),
  otherwise ``INSUFFICIENT_DATA``;
- XIRR sign convention: investor perspective — a deposit is a negative flow,
  a withdrawal positive, plus the terminal portfolio value as final positive
  flow at the last valuation instant.

Enqueue topology (documented choice): ``performance.refresh`` is enqueued by

1. the API, in the SAME transaction as every accepted ledger write
   (``vertex_api.portfolio._enqueue_refresh``): a new declared fact changes
   the series;
2. the markets overview handler (``vertex_worker.markets``), after it
   publishes a CHANGED ``markets_overview/global`` snapshot — the same
   trigger as ``portfolio.valuation.refresh``: new daily closes exist
   exactly when the published overview moved.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from vertex_core.calculations.performance import (
    DECIMAL_PRECISION,
    CashflowEvent,
    PerformanceCalculationError,
    Valuation,
    drawdown,
    twr,
    xirr,
)
from vertex_core.contracts import CalculationRecord, make_calculation_record
from vertex_core.contracts.enums import CalculationStatus
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.models import Observation, Portfolio
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_worker.errors import HandlerError
from vertex_worker.markets import (
    DAILY_QUOTE_SCHEMA_PREFIXES,
    MarketsConfig,
    QuoteRecord,
    _parse_quote,
)
from vertex_worker.portfolio import (
    LOT_METHOD_VERSION,
    LedgerEventView,
    PortfolioView,
    _derive_positions,
    load_ledger_event_views,
)
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "MAX_QUOTE_OBSERVATIONS",
    "PERFORMANCE_SCHEMA_VERSION",
    "POPULATION_SYNTHETIC_MARKS_REAL_LEDGER",
    "REASON_CASHFLOW_BOUNDARY",
    "REASON_INSUFFICIENT_VALUATIONS",
    "REASON_MULTI_CURRENCY",
    "REASON_NO_EXTERNAL_CASHFLOW",
    "REASON_NO_LEDGER_EVENT",
    "REASON_NO_VALUATION",
    "SNAPSHOT_KIND_PERFORMANCE",
    "TOPIC_PERFORMANCE_REFRESH",
    "PerformanceHandler",
    "build_performance_content",
    "load_all_daily_quote_records",
    "register_performance_handler",
]

log = logging.getLogger("vertex_worker.performance")

Clock = Callable[[], datetime]

TOPIC_PERFORMANCE_REFRESH = "performance.refresh"
"""Outbox topic: rebuild one portfolio's performance (payload
``{"portfolio_id": <int>}``)."""

SNAPSHOT_KIND_PERFORMANCE = "performance"
"""Snapshot kind; the key is the decimal portfolio id."""

PERFORMANCE_SCHEMA_VERSION = "vertex.performance/1.0"

POPULATION_SYNTHETIC_MARKS_REAL_LEDGER = "SYNTHETIC_MARKS_REAL_LEDGER"
"""The ONLY population this chain can produce: synthetic daily closes as
marks crossed with the user's really-declared manual ledger. Never merged,
averaged or blended with any other population."""

MAX_QUOTE_OBSERVATIONS = 10_000
"""Hard bound on the daily-quote history read per run; hitting it marks the
whole series INSUFFICIENT_DATA (a silently truncated history would lie)."""

_CODE_SHA = f"module:vertex_core.calculations.performance@{ENGINE_VERSION}"
_PCT_QUANTUM = Decimal("0.01")
_RATIO_QUANTUM = Decimal("0.000001")

_KIND_DEPOSIT = "DEPOSIT"
_KIND_WITHDRAWAL = "WITHDRAWAL"
_EXTERNAL_FLOW_KINDS = frozenset({_KIND_DEPOSIT, _KIND_WITHDRAWAL})

# Machine reasons (stable tokens).
REASON_NO_LEDGER_EVENT = "no_ledger_event"
REASON_MULTI_CURRENCY = "multi_currency_ledger_unsupported"
REASON_OBSERVATIONS_TRUNCATED = "observation_window_truncated"
REASON_INSUFFICIENT_VALUATIONS = "insufficient_valuations"
REASON_CASHFLOW_BOUNDARY = "cashflow_boundary_missing_valuation"
REASON_NO_VALUATION = "no_valuation"
REASON_NO_EXTERNAL_CASHFLOW = "no_external_cashflow"
REASON_DAY_INVALID_LEDGER = "invalid_ledger_event"
REASON_DAY_OVERSOLD = "oversold_position"
REASON_DAY_MISSING_MARK = "missing_mark"
REASON_DAY_MARK_CURRENCY = "mark_currency_mismatch"
REASON_DAY_NON_POSITIVE = "non_positive_value"
REASON_DAY_BAD_TRADING_DAY = "invalid_trading_day"

STATUS_OK = "OK"
STATUS_INVALID = "INVALID"
STATUS_INSUFFICIENT = "INSUFFICIENT_DATA"


def _require_aware_utc(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError(f"now: expected datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    return now.astimezone(UTC)


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _pct_string(value: Decimal, *, signed: bool = True) -> str:
    quantized = value.quantize(_PCT_QUANTUM, rounding=ROUND_HALF_EVEN)
    if quantized.is_zero() and quantized.is_signed():
        quantized = quantized.copy_negate()
    text = format(quantized, "f")
    if signed and quantized > 0:
        return f"+{text}"
    return text


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


def _insufficient(reason: str, detail: Any | None = None) -> dict[str, Any]:
    block: dict[str, Any] = {
        "status": STATUS_INSUFFICIENT,
        "reason": reason,
        "calculation": None,
    }
    if detail is not None:
        block["detail"] = detail
    return block


def _invalid(reason: str) -> dict[str, Any]:
    return {"status": STATUS_INVALID, "reason": reason, "calculation": None}


def _valuation_instant(trading_day: str) -> datetime | None:
    try:
        day = date.fromisoformat(trading_day)
    except ValueError:
        return None
    return datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=UTC)


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def load_all_daily_quote_records(
    session: Session, *, now: datetime, limit: int = MAX_QUOTE_OBSERVATIONS
) -> tuple[list[QuoteRecord], bool]:
    """Load the full persisted daily-quote history up to ``now``.

    Oldest first, deterministic order, bounded at ``limit`` rows; the second
    return value is ``True`` when the bound truncated the history (the caller
    must then fail closed instead of computing on a partial past).
    """
    filters = [
        Observation.schema_version.like(f"{prefix}%")
        for prefix in DAILY_QUOTE_SCHEMA_PREFIXES
    ]
    schema_filter: ColumnElement[bool] = filters[0]
    for extra in filters[1:]:
        schema_filter = schema_filter | extra
    rows = (
        session.execute(
            select(Observation)
            .where(Observation.as_of <= now, schema_filter)
            .order_by(Observation.as_of.asc(), Observation.id.asc())
            .limit(limit + 1)
        )
        .scalars()
        .all()
    )
    truncated = len(rows) > limit
    rows = rows[:limit]
    return (
        [
            QuoteRecord(
                event_id=row.event_id,
                source=row.source,
                instrument_ref=row.instrument_ref,
                as_of=row.as_of,
                quality_status=row.quality_status,
                rights=row.rights,
                schema_version=row.schema_version,
                payload=row.payload,
            )
            for row in rows
        ],
        truncated,
    )


# --------------------------------------------------------------------------
# Pure series derivation (no session)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _DayPoint:
    trading_day: str
    at: datetime
    gross_value: Decimal
    net_value: Decimal
    cash: Decimal
    position_value: Decimal
    fees_cumulative: Decimal
    lots_valued: int


def _marks_by_day(
    quotes: Sequence[QuoteRecord], config: MarketsConfig
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    """Latest record wins per (ticker, trading_day) — same rule as markets."""
    rejected: list[dict[str, str]] = []
    by_day: dict[str, dict[str, Any]] = {}
    for record in sorted(quotes, key=lambda r: (r.as_of, r.event_id)):
        quote, reason = _parse_quote(record, config)
        if quote is None:
            assert reason is not None  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
            rejected.append({"event_id": record.event_id, "reason": reason})
            continue
        by_day.setdefault(quote.trading_day, {})[quote.ticker] = quote
    return by_day, rejected


def _derive_daily_points(
    events: Sequence[LedgerEventView],
    marks_by_day: Mapping[str, Mapping[str, Any]],
) -> tuple[list[_DayPoint], list[dict[str, Any]], int]:
    """Value the portfolio at each close day; exclude un-valuable days.

    Returns ``(points, excluded_days, days_before_window)``. Days strictly
    before the first ledger fact are outside the measurable window and only
    counted. Nothing absent is replaced by zero.
    """
    ordered_events = sorted(events, key=lambda e: (e.effective_at, e.id))
    first_event_day = ordered_events[0].effective_at.astimezone(UTC).date()

    points: list[_DayPoint] = []
    excluded: list[dict[str, Any]] = []
    days_before_window = 0
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        for trading_day in sorted(marks_by_day):
            at = _valuation_instant(trading_day)
            if at is None:
                excluded.append(
                    {"trading_day": trading_day, "reason": REASON_DAY_BAD_TRADING_DAY}
                )
                continue
            if at.date() < first_event_day:
                days_before_window += 1
                continue
            day_events = [e for e in ordered_events if e.effective_at <= at]
            derived = _derive_positions(day_events)
            if derived.invalid_events:
                excluded.append(
                    {
                        "trading_day": trading_day,
                        "reason": REASON_DAY_INVALID_LEDGER,
                        "detail": list(derived.invalid_events),
                    }
                )
                continue
            if derived.invalid_positions:
                excluded.append(
                    {
                        "trading_day": trading_day,
                        "reason": REASON_DAY_OVERSOLD,
                        "detail": list(derived.invalid_positions),
                    }
                )
                continue
            marks = marks_by_day[trading_day]
            open_lots = [lot for lot in derived.lots if lot.remaining > 0]
            position_value = Decimal("0")
            day_reason: dict[str, Any] | None = None
            lots_valued = 0
            for lot in open_lots:
                quote = marks.get(lot.ticker)
                if quote is None:
                    day_reason = {
                        "trading_day": trading_day,
                        "reason": REASON_DAY_MISSING_MARK,
                        "detail": {"ticker": lot.ticker},
                    }
                    break
                if quote.currency is None or quote.currency != lot.currency:
                    day_reason = {
                        "trading_day": trading_day,
                        "reason": REASON_DAY_MARK_CURRENCY,
                        "detail": {"ticker": lot.ticker},
                    }
                    break
                position_value += lot.remaining * quote.close
                lots_valued += 1
            if day_reason is not None:
                excluded.append(day_reason)
                continue
            cash = sum((e.amount for e in day_events), Decimal("0"))
            fees_cumulative = sum((e.fees for e in day_events), Decimal("0"))
            gross_value = cash + position_value
            if gross_value <= 0:
                # A non-positive portfolio value makes every ratio of the
                # registry undefined; the day is excluded, never forced.
                excluded.append(
                    {"trading_day": trading_day, "reason": REASON_DAY_NON_POSITIVE}
                )
                continue
            points.append(
                _DayPoint(
                    trading_day=trading_day,
                    at=at,
                    gross_value=gross_value,
                    net_value=gross_value - fees_cumulative,
                    cash=cash,
                    position_value=position_value,
                    fees_cumulative=fees_cumulative,
                    lots_valued=lots_valued,
                )
            )
    return points, excluded, days_before_window


# --------------------------------------------------------------------------
# Metric blocks (each a registry calculation with its CalculationRecord)
# --------------------------------------------------------------------------


def _twr_flow_mapping(
    points: Sequence[_DayPoint], flow_events: Sequence[LedgerEventView]
) -> tuple[list[CashflowEvent] | None, list[str], int, int]:
    """Map dated external flows onto the valuation boundaries (docstring).

    Returns ``(flows, missing_boundary_days, embedded_count, after_count)``;
    ``flows`` is ``None`` exactly when a flow day inside the series is not a
    valued day (incomplete boundaries).
    """
    valued_days = {point.trading_day: point for point in points}
    ordered_days = [point.trading_day for point in points]
    first_day, last_day = ordered_days[0], ordered_days[-1]
    embedded = 0
    after = 0
    missing: list[str] = []
    flows: list[CashflowEvent] = []
    for event in sorted(flow_events, key=lambda e: (e.effective_at, e.id)):
        flow_day = event.effective_at.astimezone(UTC).date().isoformat()
        if flow_day <= first_day:
            embedded += 1  # part of the opening valuation's capital
            continue
        if flow_day > last_day:
            after += 1  # starts no measured period
            continue
        if flow_day not in valued_days:
            missing.append(flow_day)
            continue
        # Stamp at the previous valued day's instant: the flow arrived before
        # flow_day's close, so it adjusts the period ENDING at that close.
        previous_day = max(day for day in ordered_days if day < flow_day)
        flows.append(
            CashflowEvent(at=valued_days[previous_day].at, amount=event.amount)
        )
    if missing:
        return None, sorted(set(missing)), embedded, after
    return flows, [], embedded, after


def _twr_block(
    points: Sequence[_DayPoint],
    flow_events: Sequence[LedgerEventView],
    *,
    value_of: Callable[[_DayPoint], Decimal],
    basis: str,
    now: datetime,
) -> tuple[dict[str, Any], list[tuple[str, str, Decimal]] | None]:
    """One TWR computation (gross or net). Returns (block, periods|None)."""
    if len(points) < 2:
        return _insufficient(REASON_INSUFFICIENT_VALUATIONS), None
    if any(value_of(point) <= 0 for point in points):
        # Reachable on the NET basis only (fees exceeding the gross value);
        # a non-positive capital base leaves every ratio undefined.
        return _invalid(f"non-positive {basis} value in the series"), None
    flows, missing, embedded, after = _twr_flow_mapping(points, flow_events)
    if flows is None:
        return (
            _insufficient(REASON_CASHFLOW_BOUNDARY, detail={"missing_days": missing}),
            None,
        )
    valuations = [Valuation(at=point.at, value=value_of(point)) for point in points]
    try:
        result = twr(valuations, flows)
    except PerformanceCalculationError as exc:
        return _invalid(str(exc)), None
    record = make_calculation_record(
        calculation_id="performance.twr",
        calculation_type="performance",
        code_sha=_CODE_SHA,
        method=(
            "chain-linked daily time-weighted return over end-of-day "
            f"valuations ({basis}; flows stamped at period start)"
        ),
        inputs={
            "valuations": [v.model_dump(mode="json") for v in valuations],
            "external_cashflows": [f.model_dump(mode="json") for f in flows],
        },
        result=result.model_dump(mode="json"),
        started_at=now,
        completed_at=now,
        assumptions=(
            "end-of-day valuation instants (23:59:59 UTC)",
            "a flow on day D adjusts the period ending at D's close",
            f"basis: {basis}",
        ),
    )
    periods = [
        (points[i].trading_day, points[i + 1].trading_day, sub_return)
        for i, sub_return in enumerate(result.period_returns)
    ]
    block = {
        "status": STATUS_OK,
        "reason": None,
        "total_return": _decimal_text(result.total_return),
        "total_return_pct": _pct_string(result.total_return * 100),
        "periods": [
            {
                "from_day": from_day,
                "to_day": to_day,
                "return": _decimal_text(sub_return),
            }
            for from_day, to_day, sub_return in periods
        ],
        "cashflows_embedded_in_opening": embedded,
        "cashflows_after_last_valuation": after,
        "calculation": _calculation_meta(record),
    }
    return block, periods


def _xirr_block(
    points: Sequence[_DayPoint],
    flow_events: Sequence[LedgerEventView],
    *,
    value_of: Callable[[_DayPoint], Decimal],
    basis: str,
    now: datetime,
) -> dict[str, Any]:
    """One XIRR computation (gross or net terminal value)."""
    if not points:
        return _insufficient(REASON_NO_VALUATION)
    terminal_at = points[-1].at
    investor_flows = [
        CashflowEvent(at=event.effective_at, amount=-event.amount)
        for event in sorted(flow_events, key=lambda e: (e.effective_at, e.id))
        if event.effective_at <= terminal_at
    ]
    skipped_after = len(flow_events) - len(investor_flows)
    if not investor_flows:
        return _insufficient(REASON_NO_EXTERNAL_CASHFLOW)
    flows = [*investor_flows, CashflowEvent(at=terminal_at, amount=value_of(points[-1]))]
    try:
        result = xirr(flows)
    except PerformanceCalculationError as exc:
        return _invalid(str(exc))
    status = (
        CalculationStatus.OK
        if result.status is CalculationStatus.OK
        else CalculationStatus.INVALID
    )
    record = make_calculation_record(
        calculation_id="performance.xirr",
        calculation_type="performance",
        code_sha=_CODE_SHA,
        method=(
            "annualized money-weighted return, ACT/365F, brentq on the "
            f"documented bracket grid ({basis} terminal value)"
        ),
        inputs={"dated_cashflows": [f.model_dump(mode="json") for f in flows]},
        result=result.model_dump(mode="json"),
        started_at=now,
        completed_at=now,
        status=status,
        assumptions=(
            "investor sign convention: deposit negative, withdrawal positive",
            "terminal portfolio value as final positive flow",
            f"basis: {basis}",
        ),
    )
    if result.status is not CalculationStatus.OK:
        return {
            "status": STATUS_INVALID,
            "reason": result.reason,
            "calculation": _calculation_meta(record),
        }
    assert result.rate is not None and result.npv_at_rate is not None  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
    return {
        "status": STATUS_OK,
        "reason": None,
        "rate": _decimal_text(Decimal(repr(result.rate))),
        "rate_pct": _pct_string(Decimal(repr(result.rate)) * 100),
        "npv_at_rate": repr(result.npv_at_rate),
        "cashflows_after_last_valuation": skipped_after,
        "calculation": _calculation_meta(record),
    }


def _drawdown_block(
    points: Sequence[_DayPoint],
    *,
    value_of: Callable[[_DayPoint], Decimal],
    basis: str,
    now: datetime,
) -> dict[str, Any]:
    if not points:
        return _insufficient(REASON_NO_VALUATION)
    if any(value_of(point) <= 0 for point in points):
        # Reachable on the NET basis only (fees exceeding the gross value).
        return _invalid(f"non-positive {basis} value in the series")
    valuations = [Valuation(at=point.at, value=value_of(point)) for point in points]
    try:
        result = drawdown(valuations)
    except PerformanceCalculationError as exc:
        return _invalid(str(exc))
    record = make_calculation_record(
        calculation_id="performance.drawdown",
        calculation_type="performance",
        code_sha=_CODE_SHA,
        method=f"running-maximum drawdown over the daily {basis} value series",
        inputs={"equity_curve": [v.model_dump(mode="json") for v in valuations]},
        result=result.model_dump(mode="json"),
        started_at=now,
        completed_at=now,
        assumptions=(f"basis: {basis}",),
    )
    return {
        "status": STATUS_OK,
        "reason": None,
        "max_drawdown": _decimal_text(result.max_drawdown),
        "max_drawdown_pct": _pct_string(result.max_drawdown * 100),
        "peak_at": None if result.peak_at is None else result.peak_at.isoformat(),
        "trough_at": None if result.trough_at is None else result.trough_at.isoformat(),
        "points": [
            {"trading_day": point.trading_day, "drawdown": _decimal_text(dd)}
            for point, dd in zip(points, result.drawdowns, strict=True)
        ],
        "calculation": _calculation_meta(record),
    }


def _heatmap_block(
    twr_gross: Mapping[str, Any],
    periods: Sequence[tuple[str, str, Decimal]] | None,
    excluded_days: Sequence[Mapping[str, Any]],
    points: Sequence[_DayPoint],
) -> dict[str, Any]:
    """Monthly TWR heatmap: chain-linked regrouping of the gross TWR periods.

    Derived from the AUTHORITATIVE ``performance.twr`` period returns (month
    factor = product of (1 + r) over periods ending in that month, minus 1) —
    the same chain-link formula that defines the total; no second engine. A
    month is marked incomplete when it opens the series, closes the series,
    or contains an excluded close day.
    """
    if periods is None or twr_gross["status"] != STATUS_OK:
        return {
            "status": twr_gross["status"],
            "reason": twr_gross["reason"],
            "months": [],
            "derived_from_calculation": None,
        }
    excluded_months = {
        str(entry["trading_day"])[:7] for entry in excluded_days
    }
    first_month = points[0].trading_day[:7]
    last_month = points[-1].trading_day[:7]
    factors: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        for _from_day, to_day, sub_return in periods:
            month = to_day[:7]
            factors[month] = factors.get(month, Decimal("1")) * (
                Decimal("1") + sub_return
            )
            counts[month] = counts.get(month, 0) + 1
        months = []
        for month in sorted(factors):
            incomplete_reasons = []
            if month == first_month:
                incomplete_reasons.append("first_month_of_series")
            if month == last_month:
                incomplete_reasons.append("last_month_of_series")
            if month in excluded_months:
                incomplete_reasons.append("excluded_days_in_month")
            month_return = factors[month] - Decimal("1")
            months.append(
                {
                    "month": month,
                    "return": _decimal_text(month_return),
                    "return_pct": _pct_string(month_return * 100),
                    "periods": counts[month],
                    "complete": not incomplete_reasons,
                    "incomplete_reasons": incomplete_reasons,
                }
            )
    return {
        "status": STATUS_OK,
        "reason": None,
        "months": months,
        "method": (
            "chain-linked product of the authoritative performance.twr period "
            "returns grouped by period-end month"
        ),
        "derived_from_calculation": dict(twr_gross["calculation"]),
    }


# --------------------------------------------------------------------------
# Content builder (pure, fully deterministic)
# --------------------------------------------------------------------------


def build_performance_content(
    events: Sequence[LedgerEventView],
    quotes: Sequence[QuoteRecord],
    *,
    portfolio: PortfolioView,
    now: datetime,
    config: MarketsConfig,
    observations_truncated: bool = False,
) -> dict[str, Any]:
    """Build the performance snapshot content. Pure and deterministic.

    Identical ``events``, ``quotes`` (any order), ``portfolio``, ``now`` and
    ``config`` produce an identical dict. Every close day is either valued or
    excluded with a reason; every gate failure carries its reason; nothing is
    interpolated and nothing absent becomes zero.
    """
    now = _require_aware_utc(now)
    marks_by_day, rejected_records = _marks_by_day(quotes, config)

    series_reason: str | None = None
    if observations_truncated:
        series_reason = REASON_OBSERVATIONS_TRUNCATED
    elif not events:
        series_reason = REASON_NO_LEDGER_EVENT
    else:
        currencies = sorted({event.currency for event in events})
        if len(currencies) > 1:
            # No FX authority exists in Vertex 1.0 Beta: a multi-currency
            # ledger cannot be collapsed into one honest value series.
            series_reason = REASON_MULTI_CURRENCY

    if series_reason is not None:
        points: list[_DayPoint] = []
        excluded_days: list[dict[str, Any]] = []
        days_before_window = 0
        currency: str | None = None
    else:
        currency = events[0].currency
        points, excluded_days, days_before_window = _derive_daily_points(
            events, marks_by_day
        )

    flow_events = [
        event
        for event in sorted(events, key=lambda e: (e.effective_at, e.id))
        if event.kind in _EXTERNAL_FLOW_KINDS
    ]

    if series_reason is not None:
        twr_gross: dict[str, Any] = _insufficient(series_reason)
        twr_net: dict[str, Any] = _insufficient(series_reason)
        xirr_gross: dict[str, Any] = _insufficient(series_reason)
        xirr_net: dict[str, Any] = _insufficient(series_reason)
        drawdown_gross: dict[str, Any] = _insufficient(series_reason)
        drawdown_net: dict[str, Any] = _insufficient(series_reason)
        gross_periods: list[tuple[str, str, Decimal]] | None = None
    else:
        twr_gross, gross_periods = _twr_block(
            points, flow_events, value_of=lambda p: p.gross_value, basis="gross", now=now
        )
        twr_net, _ = _twr_block(
            points, flow_events, value_of=lambda p: p.net_value, basis="net", now=now
        )
        xirr_gross = _xirr_block(
            points, flow_events, value_of=lambda p: p.gross_value, basis="gross", now=now
        )
        xirr_net = _xirr_block(
            points, flow_events, value_of=lambda p: p.net_value, basis="net", now=now
        )
        drawdown_gross = _drawdown_block(
            points, value_of=lambda p: p.gross_value, basis="gross", now=now
        )
        drawdown_net = _drawdown_block(
            points, value_of=lambda p: p.net_value, basis="net", now=now
        )

    heatmap = _heatmap_block(twr_gross, gross_periods, excluded_days, points)

    days_total = len(points) + len(excluded_days)
    coverage_ratio: str | None = None
    if days_total > 0:
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            coverage_ratio = _decimal_text(
                (Decimal(len(points)) / Decimal(days_total)).quantize(
                    _RATIO_QUANTUM, rounding=ROUND_HALF_EVEN
                )
            )

    return {
        "schema_version": PERFORMANCE_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "engine_version": ENGINE_VERSION,
        "portfolio": {
            "id": portfolio.id,
            "name": portfolio.name,
            "base_currency": portfolio.base_currency,
        },
        # ONE population, never aggregated with any other; its two components
        # are labeled so neither side can masquerade as the other.
        "population": POPULATION_SYNTHETIC_MARKS_REAL_LEDGER,
        "population_components": {"marks": "SYNTHETIC", "ledger": "USER_DECLARED"},
        "currency": currency,
        "lot_method": LOT_METHOD_VERSION,
        "conventions": {
            "valuation_instant": "trading day at 23:59:59 UTC (end of day)",
            "cashflow_timing": (
                "a DEPOSIT/WITHDRAWAL effective on day D adjusts the capital "
                "of the period ending at D's close (stamped at the previous "
                "valued day's instant); flows on or before the first valued "
                "day are part of the opening valuation"
            ),
            "net_definition": (
                "net_value(day) = gross_value(day) - cumulative declared "
                "ledger fees up to that day; external flows identical for "
                "gross and net"
            ),
            "external_cashflow_kinds": sorted(_EXTERNAL_FLOW_KINDS),
            "xirr_sign_convention": (
                "investor perspective: deposit negative, withdrawal positive, "
                "terminal portfolio value as final positive flow"
            ),
        },
        "series": {
            "status": STATUS_OK if series_reason is None else STATUS_INSUFFICIENT,
            "reason": series_reason,
            "points": [
                {
                    "trading_day": point.trading_day,
                    "at": point.at.isoformat(),
                    "gross_value": _decimal_text(point.gross_value),
                    "net_value": _decimal_text(point.net_value),
                    "cash": _decimal_text(point.cash),
                    "position_value": _decimal_text(point.position_value),
                    "fees_cumulative": _decimal_text(point.fees_cumulative),
                    "lots_valued": point.lots_valued,
                }
                for point in points
            ],
            "excluded_days": excluded_days,
        },
        "external_cashflows": [
            {
                "event_id": event.id,
                "kind": event.kind,
                "amount": _decimal_text(event.amount),
                "currency": event.currency,
                "effective_at": event.effective_at.astimezone(UTC).isoformat(),
            }
            for event in flow_events
        ],
        "metrics": {
            "twr_gross": twr_gross,
            "twr_net": twr_net,
            "xirr_gross": xirr_gross,
            "xirr_net": xirr_net,
            "drawdown_gross": drawdown_gross,
            "drawdown_net": drawdown_net,
        },
        "heatmap": heatmap,
        "coverage": {
            "days_with_close": days_total,
            "days_valued": len(points),
            "days_excluded": len(excluded_days),
            "days_before_first_ledger_event": days_before_window,
            "coverage_ratio": coverage_ratio,
            "events_considered": len(events),
            "external_cashflows": len(flow_events),
            "observations_considered": len(quotes),
            "observations_truncated": observations_truncated,
            "rejected_records": rejected_records,
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class PerformanceHandler:
    """Handler of ``performance.refresh``: rebuild one portfolio's series."""

    def __init__(self, *, config: MarketsConfig, clock: Clock) -> None:
        self._config = config
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
        quotes, truncated = load_all_daily_quote_records(session, now=now)
        content = build_performance_content(
            events,
            quotes,
            portfolio=portfolio,
            now=now,
            config=self._config,
            observations_truncated=truncated,
        )
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_PERFORMANCE,
            key=str(portfolio.id),
            content=content,
            as_of=now,
        )
        if published is None:
            log.info(
                "performance snapshot unchanged (portfolio_id=%s, message_id=%s)",
                portfolio.id,
                message.id,
            )
        else:
            log.info(
                "performance snapshot published version=%s (portfolio_id=%s, message_id=%s)",
                published.version,
                portfolio.id,
                message.id,
            )


def register_performance_handler(
    registry: HandlerRegistry, *, clock: Clock, config: MarketsConfig
) -> None:
    """Register the performance handler on ``performance.refresh``."""
    registry.register(
        TOPIC_PERFORMANCE_REFRESH, PerformanceHandler(config=config, clock=clock)
    )
