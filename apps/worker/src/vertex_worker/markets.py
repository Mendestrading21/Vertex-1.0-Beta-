"""Markets overview snapshot chain (LOT-13): ``quotes.ingested`` handler.

Topic decision (documented): the existing ``observation.ingested`` topic is
owned by the attention fusion handler and the registry is strictly
one-handler-per-topic. Rather than overloading that handler, ingestion
enqueues an ADDITIONAL ``quotes.ingested`` message when (and only when) the
ingested envelope carries a daily-quote schema (:func:`is_daily_quote_schema`)
— a clean extension of the existing outbox flow: same transaction, same
idempotence (enqueued only when the observation row was actually inserted).

The handler recomputes the ``markets_overview/global`` snapshot from the
recent daily-quote observation window:

- per sector then per ticker: last close (exact decimal string), 1-day
  return through ``vertex_core.calculations.market.simple_return`` (the ONLY
  financial-calculation authority; its :class:`CalculationRecord` lineage —
  ``engine_version`` + ``input_hash`` — is kept in the snapshot), and the
  ticker's synthetic relative weights (share of its sector / of the covered
  universe, plain Decimal shares labeled as descriptive composition data,
  not registry calculations);
- global breadth through ``vertex_core.calculations.market.breadth`` with an
  explicit ``coverage_threshold``: below the threshold the breadth block is
  honestly ``INVALID`` with the typed gate reason — never a value computed
  on a sliver of the universe;
- an expected/received/discarded account (with per-ticker reasons): a ticker
  without BOTH closes is DISCARDED and counted, never interpolated;
- ``population`` propagation (``SYNTHETIC`` as soon as one record is
  synthetic) and a deterministic one-sentence French conclusion (server-side
  text; the UI displays it verbatim);
- percentages used by the UI (return %, weight %, breadth %, coverage %) are
  rendered server-side as strings — the browser never computes them.

Publication follows the same publish-if-changed semantics as the attention
handler; identical inputs and clock republish nothing.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from vertex_core.calculations.market import (
    CalculationInputError,
    breadth,
    simple_return,
)
from vertex_core.contracts import CalculationRecord, make_calculation_record
from vertex_core.synthetic import (
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SECTOR_LABELS_FR,
    SYNTHETIC_SECTOR_TICKERS,
    SYNTHETIC_SOURCE,
)
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.models import Observation
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "DAILY_QUOTE_SCHEMA_PREFIXES",
    "DEV_SYNTHETIC_MARKETS_CONFIG",
    "MARKETS_SCHEMA_VERSION",
    "SNAPSHOT_KIND_MARKETS",
    "TOPIC_QUOTES_INGESTED",
    "MarketsConfig",
    "MarketsOverviewHandler",
    "QuoteRecord",
    "build_markets_overview_content",
    "is_daily_quote_schema",
    "load_daily_quote_records",
    "register_markets_handler",
]

log = logging.getLogger("vertex_worker.markets")

Clock = Callable[[], datetime]

TOPIC_QUOTES_INGESTED = "quotes.ingested"
"""Outbox topic enqueued (in addition to ``observation.ingested``) for every
newly written daily-quote observation."""

SNAPSHOT_KIND_MARKETS = "markets_overview"
MARKETS_SCHEMA_VERSION = "vertex.markets-overview/1.0"

DAILY_QUOTE_SCHEMA_PREFIXES: tuple[str, ...] = ("synthetic-daily-quote/",)
"""Schema families recognized as daily quotes (extensible; deny by default)."""

_CODE_SHA = f"module:vertex_core.calculations.market@{ENGINE_VERSION}"
_WEIGHT_QUANTUM = Decimal("0.000001")
_PCT_QUANTUM = Decimal("0.01")
_PCT_ONE_DP = Decimal("0.1")

# Quality degradation ordering (worst wins per ticker).
_QUALITY_ORDER = ("VALID", "PARTIAL", "STALE")

REASON_MISSING_CLOSE = "missing_close"
REASON_INVALID_PAYLOAD = "invalid_payload"
REASON_SOURCE_NOT_ALLOWED = "source_not_allowed"
REASON_RIGHTS_NOT_USABLE = "rights_not_usable"
REASON_TICKER_NOT_IN_UNIVERSE = "ticker_not_in_universe"


def is_daily_quote_schema(schema_version: str) -> bool:
    """``True`` when ``schema_version`` belongs to a declared daily-quote family."""
    return isinstance(schema_version, str) and schema_version.startswith(
        DAILY_QUOTE_SCHEMA_PREFIXES
    )


@dataclass(frozen=True)
class QuoteRecord:
    """ORM-free view of one persisted daily-quote observation."""

    event_id: str
    source: str
    instrument_ref: str | None
    as_of: datetime
    quality_status: str
    rights: str
    schema_version: str
    payload: Mapping[str, Any]


def _is_synthetic_quote(record: QuoteRecord) -> bool:
    return record.rights == SYNTHETIC_RIGHTS or record.source == SYNTHETIC_SOURCE


@dataclass(frozen=True)
class MarketsConfig:
    """Declared inputs of the markets overview builder (owned upstream).

    ``universe`` is the point-in-time universe: sector code -> tickers; a
    quote for an undeclared ticker is rejected and counted, never silently
    added. ``sector_labels`` carries the display labels (UI French).
    ``allowed_sources``/``usable_rights`` are deny-by-default registries.
    ``coverage_threshold`` is the mandatory ``market.breadth`` gate input.
    """

    universe: Mapping[str, tuple[str, ...]]
    sector_labels: Mapping[str, str]
    allowed_sources: frozenset[str]
    usable_rights: frozenset[str]
    coverage_threshold: Decimal = Decimal("0.8")
    lookback: timedelta = timedelta(hours=72)
    max_observations: int = 500

    def __post_init__(self) -> None:
        if not self.universe:
            raise ValueError("universe: at least one sector required")
        if self.lookback <= timedelta(0):
            raise ValueError("lookback: must be a positive duration")
        if not isinstance(self.max_observations, int) or self.max_observations < 1:
            raise ValueError("max_observations: must be an int >= 1")
        if not (Decimal("0") < self.coverage_threshold <= Decimal("1")):
            raise ValueError("coverage_threshold: must be in (0, 1]")
        object.__setattr__(self, "universe", MappingProxyType(dict(self.universe)))
        object.__setattr__(
            self, "sector_labels", MappingProxyType(dict(self.sector_labels))
        )

    def all_tickers(self) -> tuple[str, ...]:
        return tuple(
            ticker for sector in sorted(self.universe) for ticker in self.universe[sector]
        )


DEV_SYNTHETIC_MARKETS_CONFIG = MarketsConfig(
    universe=dict(SYNTHETIC_SECTOR_TICKERS),
    sector_labels=dict(SYNTHETIC_SECTOR_LABELS_FR),
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)
"""Development-only registry: ONLY the synthetic source/rights and the
synthetic 24-ticker universe. Every snapshot it produces is population
``SYNTHETIC``."""


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def load_daily_quote_records(
    session: Session, *, now: datetime, lookback: timedelta, limit: int
) -> list[QuoteRecord]:
    """Load the bounded recent daily-quote window, deterministically ordered.

    Window is ``[now - lookback, now]`` on ``as_of`` (future rows excluded),
    most recent first, capped at ``limit`` rows, restricted to the declared
    daily-quote schema families.
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
            .where(
                Observation.as_of <= now,
                Observation.as_of >= now - lookback,
                schema_filter,
            )
            .order_by(Observation.as_of.desc(), Observation.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
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
    ]


# --------------------------------------------------------------------------
# Pure content builder (no session, fully deterministic)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _ParsedQuote:
    ticker: str
    sector: str
    trading_day: str
    close: Decimal
    close_text: str
    currency: str | None
    adjustment_basis: str
    quality: str
    synthetic: bool
    event_id: str
    as_of: datetime


def _parse_quote(
    record: QuoteRecord, config: MarketsConfig
) -> tuple[_ParsedQuote | None, str | None]:
    """Parse one record fail-closed; returns (quote, None) or (None, reason)."""
    if record.source not in config.allowed_sources:
        return None, REASON_SOURCE_NOT_ALLOWED
    if record.rights not in config.usable_rights:
        return None, REASON_RIGHTS_NOT_USABLE
    payload = record.payload
    if not isinstance(payload, Mapping):
        return None, REASON_INVALID_PAYLOAD
    ticker = payload.get("ticker")
    sector = payload.get("sector")
    trading_day = payload.get("trading_day")
    close_text = payload.get("close")
    basis = payload.get("adjustment_basis")
    if not all(
        isinstance(value, str) and value
        for value in (ticker, sector, trading_day, close_text, basis)
    ):
        return None, REASON_INVALID_PAYLOAD
    # narrowing mypy, garde réelle au-dessus
    assert isinstance(ticker, str) and isinstance(sector, str)  # narrowed above  # noqa: S101
    assert isinstance(trading_day, str) and isinstance(close_text, str)  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
    assert isinstance(basis, str)  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
    declared = config.universe.get(sector)
    if declared is None or ticker not in declared:
        return None, REASON_TICKER_NOT_IN_UNIVERSE
    try:
        close = Decimal(close_text)
    except InvalidOperation:
        return None, REASON_INVALID_PAYLOAD
    if not close.is_finite() or close <= 0:
        return None, REASON_INVALID_PAYLOAD
    raw_currency = payload.get("currency")
    currency = raw_currency if isinstance(raw_currency, str) and raw_currency else None
    return (
        _ParsedQuote(
            ticker=ticker,
            sector=sector,
            trading_day=trading_day,
            close=close,
            close_text=close_text,
            currency=currency,
            adjustment_basis=basis,
            quality=record.quality_status,
            synthetic=_is_synthetic_quote(record),
            event_id=record.event_id,
            as_of=record.as_of,
        ),
        None,
    )


def _worst_quality(a: str, b: str) -> str:
    def rank(value: str) -> int:
        try:
            return _QUALITY_ORDER.index(value)
        except ValueError:
            return len(_QUALITY_ORDER)  # unknown quality ranks worst

    return a if rank(a) >= rank(b) else b


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


def _pct_string(value: Decimal, quantum: Decimal, *, signed: bool = False) -> str:
    quantized = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if quantized.is_zero() and quantized.is_signed():
        quantized = quantized.copy_negate()
    text = format(quantized, "f")
    if signed and quantized > 0:
        return f"+{text}"
    return text


def _french_conclusion(
    *,
    universe_size: int,
    covered: int,
    discarded: int,
    up: int,
    down: int,
    flat: int,
    breadth_pct: str | None,
    threshold_pct: str,
) -> str:
    head = (
        f"Sur {universe_size} instruments synthétiques attendus, {covered} sont "
        f"couverts et {discarded} écartés ; {up} en hausse, {down} en baisse, "
        f"{flat} stables"
    )
    if breadth_pct is None:
        return (
            f"{head} ; breadth non calculable, couverture sous le seuil de "
            f"{threshold_pct} %."
        )
    return f"{head} ; breadth {breadth_pct} % (seuil de couverture {threshold_pct} %)."


def build_markets_overview_content(
    records: Sequence[QuoteRecord], *, now: datetime, config: MarketsConfig
) -> dict[str, Any]:
    """Build the markets overview snapshot content. Pure and deterministic.

    Identical ``records`` (in any order), ``now`` and ``config`` produce an
    identical dict. Every considered record is accounted for: parsed into a
    ticker day, or rejected with a reason; every universe ticker is either
    covered or discarded with a reason. Nothing is interpolated.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")

    universe = config.all_tickers()
    universe_set = set(universe)

    # -- parse and de-duplicate: latest record wins per (ticker, trading_day)
    rejected_records: list[dict[str, str]] = []
    by_ticker_day: dict[str, dict[str, _ParsedQuote]] = {}
    synthetic_count = 0
    for record in sorted(records, key=lambda r: (r.as_of, r.event_id)):
        quote, reason = _parse_quote(record, config)
        if quote is None:
            assert reason is not None  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
            rejected_records.append({"event_id": record.event_id, "reason": reason})
            continue
        if quote.synthetic:
            synthetic_count += 1
        by_ticker_day.setdefault(quote.ticker, {})[quote.trading_day] = quote

    received = sorted(by_ticker_day)

    # -- per ticker: need the two most recent distinct trading days ---------
    discarded: list[dict[str, str]] = []
    covered: dict[str, dict[str, Any]] = {}
    up = down = flat = 0
    for ticker in sorted(universe_set):
        days = by_ticker_day.get(ticker)
        if days is None or len(days) < 2:
            discarded.append({"ticker": ticker, "reason": REASON_MISSING_CLOSE})
            continue
        older_day, latest_day = sorted(days)[-2:]
        older, latest = days[older_day], days[latest_day]
        try:
            value = simple_return(
                older.close,
                latest.close,
                adjustment_basis_t0=older.adjustment_basis,
                adjustment_basis_t1=latest.adjustment_basis,
            )
        except CalculationInputError as exc:
            discarded.append({"ticker": ticker, "reason": exc.reason})
            continue
        calculation_record = make_calculation_record(
            calculation_id="market.simple_return",
            calculation_type="market",
            code_sha=_CODE_SHA,
            method="simple_return p1/p0 - 1 (1 trading day)",
            inputs={
                "price_t0": older.close,
                "price_t1": latest.close,
                "adjustment_basis_t0": older.adjustment_basis,
                "adjustment_basis_t1": latest.adjustment_basis,
            },
            result=value,
            started_at=now,
            completed_at=now,
            source_event_ids=(older.event_id, latest.event_id),
            assumptions=("consecutive synthetic trading days",),
        )
        if value > 0:
            up += 1
        elif value < 0:
            down += 1
        else:
            flat += 1
        return_decimal = Decimal(repr(value))
        covered[ticker] = {
            "ticker": ticker,
            "sector": older.sector,
            "trading_day": latest_day,
            "previous_trading_day": older_day,
            "last_close": latest.close_text,
            "previous_close": older.close_text,
            "currency": latest.currency,
            "return_1d": format(return_decimal, "f"),
            "return_1d_pct": _pct_string(
                return_decimal * 100, _PCT_QUANTUM, signed=True
            ),
            "quality": _worst_quality(older.quality, latest.quality),
            "synthetic": older.synthetic or latest.synthetic,
            "calculation": _calculation_meta(calculation_record),
            "_close_decimal": latest.close,  # stripped below
        }

    # -- weights: descriptive Decimal shares (labeled, not registry calcs) --
    sector_totals: dict[str, Decimal] = {}
    universe_total = Decimal("0")
    for entry in covered.values():
        sector_totals[entry["sector"]] = (
            sector_totals.get(entry["sector"], Decimal("0")) + entry["_close_decimal"]
        )
        universe_total += entry["_close_decimal"]
    for entry in covered.values():
        close = entry.pop("_close_decimal")
        sector_total = sector_totals[entry["sector"]]
        weight_in_sector = (close / sector_total).quantize(
            _WEIGHT_QUANTUM, rounding=ROUND_HALF_EVEN
        )
        weight_global = (close / universe_total).quantize(
            _WEIGHT_QUANTUM, rounding=ROUND_HALF_EVEN
        )
        entry["weight_in_sector"] = format(weight_in_sector, "f")
        entry["weight_in_sector_pct"] = _pct_string(weight_in_sector * 100, _PCT_QUANTUM)
        entry["weight_global"] = format(weight_global, "f")
        entry["weight_global_pct"] = _pct_string(weight_global * 100, _PCT_QUANTUM)

    # -- sectors (declared order = sorted codes; every declared sector kept) -
    sectors: list[dict[str, Any]] = []
    for sector in sorted(config.universe):
        declared = config.universe[sector]
        tickers = [
            covered[ticker] for ticker in sorted(declared) if ticker in covered
        ]
        sectors.append(
            {
                "sector": sector,
                "label": config.sector_labels.get(sector, sector),
                "declared_count": len(declared),
                "covered_count": len(tickers),
                "tickers": tickers,
            }
        )

    # -- breadth (single authority; INVALID below the coverage gate) --------
    covered_count = len(covered)
    universe_size = len(universe_set)
    threshold_pct = _pct_string(config.coverage_threshold * 100, _PCT_ONE_DP)
    coverage_pct = _pct_string(
        Decimal(covered_count) / Decimal(universe_size) * 100, _PCT_ONE_DP
    )
    breadth_block: dict[str, Any]
    breadth_pct: str | None = None
    try:
        breadth_value = breadth(
            up,
            universe_size,
            covered_count=covered_count,
            coverage_threshold=config.coverage_threshold,
        )
    except CalculationInputError as exc:
        breadth_block = {
            "status": "INVALID",
            "reason": exc.reason,
            "value": None,
            "value_pct": None,
            "above_count": up,
            "covered_count": covered_count,
            "universe_size": universe_size,
            "coverage_pct": coverage_pct,
            "coverage_threshold": format(config.coverage_threshold, "f"),
            "coverage_threshold_pct": threshold_pct,
            "calculation": None,
        }
    else:
        breadth_record = make_calculation_record(
            calculation_id="market.breadth",
            calculation_type="market",
            code_sha=_CODE_SHA,
            method="participation ratio above_count / covered_count",
            inputs={
                "above_count": up,
                "universe_size": universe_size,
                "covered_count": covered_count,
                "coverage_threshold": config.coverage_threshold,
            },
            result=breadth_value,
            started_at=now,
            completed_at=now,
        )
        breadth_decimal = Decimal(repr(breadth_value))
        breadth_pct = _pct_string(breadth_decimal * 100, _PCT_ONE_DP)
        breadth_block = {
            "status": "OK",
            "reason": None,
            "value": format(breadth_decimal, "f"),
            "value_pct": breadth_pct,
            "above_count": up,
            "covered_count": covered_count,
            "universe_size": universe_size,
            "coverage_pct": coverage_pct,
            "coverage_threshold": format(config.coverage_threshold, "f"),
            "coverage_threshold_pct": threshold_pct,
            "calculation": _calculation_meta(breadth_record),
        }

    # -- population, data state, conclusion ---------------------------------
    if not records:
        population = "EMPTY"
    elif synthetic_count > 0:
        population = "SYNTHETIC"
    else:
        population = "REAL"

    qualities = [entry["quality"] for entry in covered.values()]
    if covered and all(q == "STALE" for q in qualities):
        data_state = "stale"
    elif discarded or rejected_records or any(q != "VALID" for q in qualities):
        data_state = "partial"
    else:
        data_state = "ok"

    conclusion = _french_conclusion(
        universe_size=universe_size,
        covered=covered_count,
        discarded=len(discarded),
        up=up,
        down=down,
        flat=flat,
        breadth_pct=breadth_pct,
        threshold_pct=threshold_pct,
    )

    return {
        "schema_version": MARKETS_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "data_state": data_state,
        "unit": "return_ratio",
        "display_unit": "%",
        "engine_version": ENGINE_VERSION,
        "conclusion": conclusion,
        "sectors": sectors,
        "breadth": breadth_block,
        "coverage": {
            "expected": universe_size,
            "received": len(received),
            "covered": covered_count,
            "discarded": len(discarded),
            "discarded_tickers": discarded,
            "rejected_records": rejected_records,
            "observations_considered": len(records),
            "lookback_seconds": int(config.lookback.total_seconds()),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class MarketsOverviewHandler:
    """Handler of ``quotes.ingested``: recompute the markets overview."""

    def __init__(self, *, config: MarketsConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local import avoids a module cycle (handlers imports this module).
        from vertex_worker.handlers import publish_if_changed

        now = self._clock()
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("clock returned a naive datetime; aware UTC required")
        records = load_daily_quote_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )
        content = build_markets_overview_content(records, now=now, config=self._config)
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_MARKETS,
            key="global",
            content=content,
            as_of=now,
        )
        if published is None:
            log.info("markets snapshot unchanged (message_id=%s)", message.id)
        else:
            log.info(
                "markets snapshot published version=%s (message_id=%s)",
                published.version,
                message.id,
            )
            self._enqueue_portfolio_revaluations(session)

    @staticmethod
    def _enqueue_portfolio_revaluations(session: Session) -> None:
        """Enqueue one revaluation AND one performance job per portfolio.

        Documented topology choice (see ``vertex_worker.portfolio`` and
        ``vertex_worker.performance``): the marks of every portfolio valuation
        are the closes of the ``markets_overview/global`` snapshot, so both
        ``portfolio.valuation.refresh`` and ``performance.refresh`` are
        enqueued HERE, in the same transaction as a CHANGED publication of
        that snapshot — an unchanged snapshot (publish-if-changed no-op)
        changes no mark and enqueues nothing. The ingest path was
        deliberately not used: a quote that does not move a published close
        cannot move any valuation, and new daily closes exist exactly when
        the published overview moved.
        """
        from vertex_persistence.models import Portfolio
        from vertex_persistence.repository.outbox import enqueue_outbox
        from vertex_worker.performance import TOPIC_PERFORMANCE_REFRESH
        from vertex_worker.portfolio import TOPIC_PORTFOLIO_VALUATION_REFRESH

        portfolio_ids = session.execute(
            select(Portfolio.id).order_by(Portfolio.id)
        ).scalars().all()
        for portfolio_id in portfolio_ids:
            enqueue_outbox(
                session,
                TOPIC_PORTFOLIO_VALUATION_REFRESH,
                {"portfolio_id": portfolio_id},
            )
            enqueue_outbox(
                session,
                TOPIC_PERFORMANCE_REFRESH,
                {"portfolio_id": portfolio_id},
            )


def register_markets_handler(
    registry: HandlerRegistry, *, clock: Clock, config: MarketsConfig
) -> None:
    """Register the markets overview handler on ``quotes.ingested``."""
    registry.register(
        TOPIC_QUOTES_INGESTED, MarketsOverviewHandler(config=config, clock=clock)
    )
