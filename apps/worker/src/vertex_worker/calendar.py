"""Calendar snapshot chain (page 02): ``calendar.ingested`` handler.

Topic decision (documented, same pattern as ``quotes.ingested`` /
``analysis.ingested``): ``vertex_worker.ingest.ingest_envelope`` enqueues one
ADDITIONAL ``calendar.ingested`` message for every newly written
calendar-event observation (same transaction, same idempotence). The registry
stays one-handler-per-topic.

The handler recomputes ONE ``calendar/global`` snapshot:

- the agenda is the chronologically sorted list of the persisted
  calendar-event observations (latest envelope per stable ``event_id`` wins —
  a revision arrives as a NEW envelope of the same stable id and replaces the
  displayed event while its ``revisions`` list keeps every previous value);
- every event is validated FAIL-CLOSED (declared source/rights, known
  category, canonical ``ESTIMATED``/``CONFIRMED`` status, aware UTC instant,
  present exchange timezone); an invalid event is rejected WITH its reason,
  never repaired — estimated and confirmed dates keep their distinct labels
  end to end;
- the importance of each event comes from the VERSIONED rule
  :data:`IMPORTANCE_RULE_VERSION` (documented in
  :data:`IMPORTANCE_RULE_RANKS`); nothing here invents an importance:
  1. global macro event;
  2. earnings of a ticker carrying a declared manual position OR a user
     thesis;
  3. earnings of a watchlist ticker (any other declared ticker);
  4. dividend;
  5. option expiration;
  6. non-global macro event (defensive, generator never emits one today);
- the ``event_context`` block crosses each ticker event with the MANUAL
  ledger positions (through the same versioned ``fifo/1.0`` derivation as
  the valuation snapshot — ``derive_open_position_tickers``) and the user
  theses (repository projection), plus resource links toward the analysis
  and option-chain snapshots of the ticker — read-derived context only,
  nothing is written back;
- timezone conservation: ``event_time_utc``, ``event_time_local`` and
  ``exchange_timezone`` are relayed VERBATIM.

Publication follows publish-if-changed: identical inputs and clock republish
nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_core.synthetic import (
    EVENT_CATEGORY_DIVIDEND,
    EVENT_CATEGORY_EARNINGS,
    EVENT_CATEGORY_MACRO,
    EVENT_CATEGORY_OPTION_EXPIRATION,
    EVENT_SCOPE_GLOBAL,
    EVENT_STATUS_CONFIRMED,
    EVENT_STATUS_ESTIMATED,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
)
from vertex_persistence.models import Observation, Portfolio
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_persistence.repository.theses import list_theses

from vertex_worker.registry import HandlerRegistry

__all__ = [
    "CALENDAR_EVENT_SCHEMA_PREFIXES",
    "CALENDAR_SCHEMA_VERSION",
    "DEV_SYNTHETIC_CALENDAR_CONFIG",
    "IMPORTANCE_RULE_RANKS",
    "IMPORTANCE_RULE_VERSION",
    "REASON_INVALID_CATEGORY",
    "REASON_INVALID_EVENT_TIME",
    "REASON_INVALID_PAYLOAD",
    "REASON_INVALID_REVISIONS",
    "REASON_INVALID_STATUS",
    "REASON_MISSING_TIMEZONE",
    "REASON_RIGHTS_NOT_USABLE",
    "REASON_SOURCE_NOT_ALLOWED",
    "SNAPSHOT_KEY_GLOBAL",
    "SNAPSHOT_KIND_CALENDAR",
    "TOPIC_CALENDAR_INGESTED",
    "CalendarConfig",
    "CalendarEventRecord",
    "CalendarHandler",
    "build_calendar_content",
    "is_calendar_event_schema",
    "load_calendar_event_records",
    "register_calendar_handler",
]

log = logging.getLogger("vertex_worker.calendar")

Clock = Callable[[], datetime]

TOPIC_CALENDAR_INGESTED = "calendar.ingested"
"""Outbox topic enqueued (in addition to ``observation.ingested``) for every
newly written calendar-event observation."""

SNAPSHOT_KIND_CALENDAR = "calendar"
SNAPSHOT_KEY_GLOBAL = "global"
CALENDAR_SCHEMA_VERSION = "vertex.calendar/1.0"

CALENDAR_EVENT_SCHEMA_PREFIXES: tuple[str, ...] = ("synthetic-calendar-event/",)
"""Schema families recognized as calendar events (deny by default)."""

IMPORTANCE_RULE_VERSION = "importance_rule/1.0"
"""Versioned importance rule. The importance of an event comes from THIS
rule, never from an invention: changing a rank is a rule version change."""

IMPORTANCE_RULE_RANKS: tuple[dict[str, Any], ...] = (
    {
        "rank": 1,
        "code": "MACRO_GLOBAL",
        "description": "evenement macro global",
    },
    {
        "rank": 2,
        "code": "EARNINGS_POSITION_OR_THESIS",
        "description": (
            "resultats d'un ticker avec position manuelle ou these declaree"
        ),
    },
    {
        "rank": 3,
        "code": "EARNINGS_WATCHLIST",
        "description": "resultats d'un ticker de la watchlist declaree",
    },
    {"rank": 4, "code": "DIVIDEND", "description": "dividende"},
    {
        "rank": 5,
        "code": "OPTION_EXPIRATION",
        "description": "expiration d'options",
    },
    {
        "rank": 6,
        "code": "MACRO_TICKER",
        "description": "evenement macro non global (defensif)",
    },
)
"""The documented ranks of :data:`IMPORTANCE_RULE_VERSION` (1 = highest)."""

_KNOWN_CATEGORIES = frozenset(
    {
        EVENT_CATEGORY_EARNINGS,
        EVENT_CATEGORY_DIVIDEND,
        EVENT_CATEGORY_OPTION_EXPIRATION,
        EVENT_CATEGORY_MACRO,
    }
)
_KNOWN_STATUSES = frozenset({EVENT_STATUS_ESTIMATED, EVENT_STATUS_CONFIRMED})

REASON_INVALID_PAYLOAD = "invalid_payload"
REASON_INVALID_CATEGORY = "invalid_category"
REASON_INVALID_STATUS = "invalid_status"
REASON_INVALID_EVENT_TIME = "invalid_event_time"
REASON_INVALID_REVISIONS = "invalid_revisions"
REASON_MISSING_TIMEZONE = "missing_exchange_timezone"
REASON_SOURCE_NOT_ALLOWED = "source_not_allowed"
REASON_RIGHTS_NOT_USABLE = "rights_not_usable"


def is_calendar_event_schema(schema_version: str) -> bool:
    """``True`` when ``schema_version`` belongs to a declared event family."""
    return isinstance(schema_version, str) and schema_version.startswith(
        CALENDAR_EVENT_SCHEMA_PREFIXES
    )


@dataclass(frozen=True)
class CalendarEventRecord:
    """ORM-free view of one persisted calendar-event observation."""

    event_id: str
    source: str
    instrument_ref: Optional[str]
    as_of: datetime
    quality_status: str
    rights: str
    schema_version: str
    payload: Mapping[str, Any]


def _is_synthetic_record(record: CalendarEventRecord) -> bool:
    return record.rights == SYNTHETIC_RIGHTS or record.source == SYNTHETIC_SOURCE


@dataclass(frozen=True)
class CalendarConfig:
    """Declared inputs of the calendar builder (owned upstream, injected)."""

    allowed_sources: frozenset[str]
    usable_rights: frozenset[str]
    watchlist: tuple[str, ...] = ()
    lookback: timedelta = timedelta(hours=72)
    max_observations: int = 500

    def __post_init__(self) -> None:
        if self.lookback <= timedelta(0):
            raise ValueError("lookback: must be a positive duration")
        if not isinstance(self.max_observations, int) or self.max_observations < 1:
            raise ValueError("max_observations: must be an int >= 1")


def _dev_watchlist() -> tuple[str, ...]:
    from vertex_core.synthetic import SYNTHETIC_SECTOR_TICKERS

    return tuple(
        ticker
        for tickers in SYNTHETIC_SECTOR_TICKERS.values()
        for ticker in tickers
    )


DEV_SYNTHETIC_CALENDAR_CONFIG = CalendarConfig(
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
    watchlist=_dev_watchlist(),
)
"""Development-only registry: ONLY the synthetic source/rights; the declared
24-ticker synthetic universe is the watchlist. Every snapshot it produces is
population ``SYNTHETIC``."""


def _require_aware_utc(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError(f"now: expected datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    return now.astimezone(timezone.utc)


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def load_calendar_event_records(
    session: Session, *, now: datetime, lookback: timedelta, limit: int
) -> list[CalendarEventRecord]:
    """Load the bounded recent calendar-event window, deterministically ordered."""
    now = _require_aware_utc(now)
    filters = [
        Observation.schema_version.like(f"{prefix}%")
        for prefix in CALENDAR_EVENT_SCHEMA_PREFIXES
    ]
    schema_filter = filters[0]
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
            .order_by(Observation.as_of.asc(), Observation.id.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        CalendarEventRecord(
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
# Pure content helpers (no session, fully deterministic)
# --------------------------------------------------------------------------


def _aware_iso_or_none(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return None
    return parsed


def _validate_event(
    record: CalendarEventRecord, config: CalendarConfig
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Fail-closed validation of one event record: (validated, reason)."""
    if record.source not in config.allowed_sources:
        return None, REASON_SOURCE_NOT_ALLOWED
    if record.rights not in config.usable_rights:
        return None, REASON_RIGHTS_NOT_USABLE
    payload = record.payload
    if not isinstance(payload, Mapping):
        return None, REASON_INVALID_PAYLOAD
    stable_id = payload.get("event_id")
    title = payload.get("title")
    if (
        not isinstance(stable_id, str)
        or not stable_id
        or not isinstance(title, str)
        or not title
    ):
        return None, REASON_INVALID_PAYLOAD
    category = payload.get("category")
    if category not in _KNOWN_CATEGORIES:
        return None, REASON_INVALID_CATEGORY
    status = payload.get("status")
    if status not in _KNOWN_STATUSES:
        return None, REASON_INVALID_STATUS
    event_time_utc = _aware_iso_or_none(payload.get("event_time_utc"))
    event_time_local = _aware_iso_or_none(payload.get("event_time_local"))
    if event_time_utc is None or event_time_local is None:
        return None, REASON_INVALID_EVENT_TIME
    if event_time_utc != event_time_local:
        # The two representations must denote the SAME instant.
        return None, REASON_INVALID_EVENT_TIME
    exchange_timezone = payload.get("exchange_timezone")
    if not isinstance(exchange_timezone, str) or not exchange_timezone:
        return None, REASON_MISSING_TIMEZONE
    ticker = payload.get("ticker")
    if ticker is not None and (not isinstance(ticker, str) or not ticker):
        return None, REASON_INVALID_PAYLOAD
    revisions = payload.get("revisions")
    if not isinstance(revisions, list) or any(
        not isinstance(entry, Mapping) for entry in revisions
    ):
        return None, REASON_INVALID_REVISIONS
    return {
        "stable_id": stable_id,
        "category": category,
        "status": status,
        "title": title,
        "ticker": ticker,
        "scope": payload.get("scope"),
        "event_time_utc": payload["event_time_utc"],
        "event_time_local": payload["event_time_local"],
        "exchange_timezone": exchange_timezone,
        "event_time_utc_parsed": event_time_utc.astimezone(timezone.utc),
        "revisions": [dict(entry) for entry in revisions],
        "extra": {
            key: payload[key]
            for key in ("amount", "currency", "expiration")
            if key in payload
        },
    }, None


def _importance(
    event: Mapping[str, Any],
    *,
    position_tickers: frozenset[str],
    thesis_tickers: frozenset[str],
) -> dict[str, Any]:
    """Apply the versioned importance rule (never an invention)."""
    category = event["category"]
    ticker = event["ticker"]
    if category == EVENT_CATEGORY_MACRO:
        code = (
            "MACRO_GLOBAL"
            if ticker is None or event.get("scope") == EVENT_SCOPE_GLOBAL
            else "MACRO_TICKER"
        )
    elif category == EVENT_CATEGORY_EARNINGS:
        if ticker is not None and (
            ticker in position_tickers or ticker in thesis_tickers
        ):
            code = "EARNINGS_POSITION_OR_THESIS"
        else:
            code = "EARNINGS_WATCHLIST"
    elif category == EVENT_CATEGORY_DIVIDEND:
        code = "DIVIDEND"
    else:
        code = "OPTION_EXPIRATION"
    rank = next(
        entry["rank"] for entry in IMPORTANCE_RULE_RANKS if entry["code"] == code
    )
    return {"rank": rank, "code": code, "rule_version": IMPORTANCE_RULE_VERSION}


def _event_context(
    ticker: Optional[str],
    *,
    positions_by_ticker: Mapping[str, Sequence[int]],
    theses_by_ticker: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    if ticker is None:
        return {"positions": [], "theses": [], "links": []}
    portfolio_ids = sorted(positions_by_ticker.get(ticker, ()))
    theses = [
        {
            "thesis_id": entry["thesis_id"],
            "title": entry["title"],
            "status": entry["status"],
        }
        for entry in theses_by_ticker.get(ticker, ())
    ]
    links = [
        {"rel": "analysis", "resource": f"analysis/{ticker}"},
        {"rel": "option_chain", "resource": f"option_chain/{ticker}"},
    ]
    for entry in theses:
        links.append(
            {"rel": "thesis", "resource": f"theses/{entry['thesis_id']}"}
        )
    return {
        "positions": [{"portfolio_id": pid} for pid in portfolio_ids],
        "theses": theses,
        "links": links,
    }


def build_calendar_content(
    records: Sequence[CalendarEventRecord],
    *,
    now: datetime,
    config: CalendarConfig,
    positions_by_ticker: Mapping[str, Sequence[int]],
    theses_by_ticker: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Build the ``calendar/global`` snapshot content (pure, deterministic).

    Identical inputs produce an identical dict. Every considered record is
    either displayed, superseded by a later envelope of the same stable id,
    or rejected with a reason. Estimated and confirmed statuses are relayed
    verbatim (distinct labels), revisions keep their previous values and the
    exchange timezone is conserved.
    """
    now = _require_aware_utc(now)

    rejected: list[dict[str, str]] = []
    latest_by_stable_id: dict[str, tuple[CalendarEventRecord, dict[str, Any]]] = {}
    superseded = 0
    for record in sorted(records, key=lambda r: (r.as_of, r.event_id)):
        validated, reason = _validate_event(record, config)
        if validated is None:
            assert reason is not None
            rejected.append({"event_id": record.event_id, "reason": reason})
            continue
        if validated["stable_id"] in latest_by_stable_id:
            superseded += 1
        # Ascending (as_of, id) order: the LATEST envelope of a stable id
        # wins — a revision replaces the displayed event, never edits history.
        latest_by_stable_id[validated["stable_id"]] = (record, validated)

    position_tickers = frozenset(positions_by_ticker)
    thesis_tickers = frozenset(theses_by_ticker)

    agenda: list[dict[str, Any]] = []
    categories: dict[str, int] = {}
    statuses: dict[str, int] = {
        EVENT_STATUS_ESTIMATED: 0,
        EVENT_STATUS_CONFIRMED: 0,
    }
    synthetic = False
    entries = sorted(
        latest_by_stable_id.values(),
        key=lambda pair: (pair[1]["event_time_utc_parsed"], pair[1]["stable_id"]),
    )
    for record, event in entries:
        is_synthetic = _is_synthetic_record(record)
        synthetic = synthetic or is_synthetic
        categories[event["category"]] = categories.get(event["category"], 0) + 1
        statuses[event["status"]] += 1
        item: dict[str, Any] = {
            "event_id": event["stable_id"],
            "category": event["category"],
            "status": event["status"],
            "title": event["title"],
            "ticker": event["ticker"],
            "scope": event["scope"],
            "event_time_utc": event["event_time_utc"],
            "event_time_local": event["event_time_local"],
            "exchange_timezone": event["exchange_timezone"],
            "importance": _importance(
                event,
                position_tickers=position_tickers,
                thesis_tickers=thesis_tickers,
            ),
            "revisions": event["revisions"],
            "revised": bool(event["revisions"]),
            "event_context": _event_context(
                event["ticker"],
                positions_by_ticker=positions_by_ticker,
                theses_by_ticker=theses_by_ticker,
            ),
            "synthetic": is_synthetic,
            "quality": record.quality_status,
            "source": record.source,
            "rights": record.rights,
            "source_event_id": record.event_id,
        }
        item.update(event["extra"])
        agenda.append(item)

    if not records:
        population = "EMPTY"
    elif synthetic:
        population = "SYNTHETIC"
    else:
        population = "REAL"

    return {
        "schema_version": CALENDAR_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "importance_rule": {
            "version": IMPORTANCE_RULE_VERSION,
            "ranks": [dict(entry) for entry in IMPORTANCE_RULE_RANKS],
        },
        "agenda": agenda,
        "categories": dict(sorted(categories.items())),
        "statuses": statuses,
        "coverage": {
            "observations_considered": len(records),
            "events_displayed": len(agenda),
            "events_superseded": superseded,
            "rejected_records": rejected,
            "lookback_seconds": int(config.lookback.total_seconds()),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class CalendarHandler:
    """Handler of ``calendar.ingested``: recompute the global agenda.

    Read-only over the ledger (position derivation) and the theses
    (projection); the ONLY write is the snapshot publication.
    """

    def __init__(self, *, config: CalendarConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local imports avoid module cycles (handlers -> ingest -> here).
        from vertex_worker.handlers import publish_if_changed
        from vertex_worker.portfolio import (
            derive_open_position_tickers,
            load_ledger_event_views,
        )

        now = _require_aware_utc(self._clock())
        records = load_calendar_event_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )

        positions_by_ticker: dict[str, list[int]] = {}
        portfolio_ids = (
            session.execute(select(Portfolio.id).order_by(Portfolio.id))
            .scalars()
            .all()
        )
        for portfolio_id in portfolio_ids:
            events = load_ledger_event_views(session, portfolio_id)
            for ticker in sorted(derive_open_position_tickers(events)):
                positions_by_ticker.setdefault(ticker, []).append(portfolio_id)

        theses_by_ticker: dict[str, list[dict[str, Any]]] = {}
        for entry in list_theses(session, now=now):
            instrument = entry.thesis.instrument
            ticker = (
                instrument.get("ticker") if isinstance(instrument, Mapping) else None
            )
            if not isinstance(ticker, str) or not ticker:
                continue
            theses_by_ticker.setdefault(ticker, []).append(
                {
                    "thesis_id": entry.thesis.id,
                    "title": entry.thesis.title,
                    "status": entry.state.status,
                }
            )

        content = build_calendar_content(
            records,
            now=now,
            config=self._config,
            positions_by_ticker=positions_by_ticker,
            theses_by_ticker=theses_by_ticker,
        )
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_CALENDAR,
            key=SNAPSHOT_KEY_GLOBAL,
            content=content,
            as_of=now,
        )
        if published is None:
            log.info("calendar snapshot unchanged (message_id=%s)", message.id)
        else:
            log.info(
                "calendar snapshot published version=%s (message_id=%s)",
                published.version,
                message.id,
            )


def register_calendar_handler(
    registry: HandlerRegistry, *, clock: Clock, config: CalendarConfig
) -> None:
    """Register the calendar handler on ``calendar.ingested``."""
    registry.register(
        TOPIC_CALENDAR_INGESTED, CalendarHandler(config=config, clock=clock)
    )
