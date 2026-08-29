"""Calendar snapshot chain (page 02): ``calendar.ingested`` handler.

Topic decision (documented, same pattern as ``quotes.ingested`` /
``analysis.ingested``): ``vertex_worker.ingest.ingest_envelope`` enqueues one
ADDITIONAL ``calendar.ingested`` message for every newly written
calendar-event observation (same transaction, same idempotence). The registry
stays one-handler-per-topic.

The handler recomputes ONE ``calendar/global`` snapshot:

- the agenda is the chronologically sorted list of the persisted
  calendar-event observations. Several envelopes may share one stable
  ``event_id``; the displayed one is chosen by the BUSINESS chronology —
  the most recent declared ``revisions[].revised_at`` first, then ``as_of``,
  then the envelope ``event_id`` as an explicitly documented LAST-RESORT
  deterministic tie-break (one generation gives all its envelopes the same
  ``as_of``, so equality is the normal case). Nothing is erased: the builder
  BUILDS ``previous_values`` from the records it really saw (status, instant,
  source, ``as_of``) beside the ``revisions`` the source declares, and an
  event whose state changed is flagged ``revised``;
- every event is validated FAIL-CLOSED (declared source/rights, known
  category, canonical ``ESTIMATED``/``CONFIRMED`` status, aware UTC instant,
  allowlisted ``scope`` coherent with the ticker presence, RESOLVABLE IANA
  exchange timezone whose offset matches ``event_time_local``, dated
  revisions); an invalid event is rejected WITH its reason, never repaired —
  estimated and confirmed dates keep their distinct labels end to end;
- the importance of each event comes from the VERSIONED rule
  :data:`IMPORTANCE_RULE_VERSION` (documented in
  :data:`IMPORTANCE_RULE_RANKS`); nothing here invents an importance:
  1. global macro event;
  2. earnings of a ticker carrying a declared OPEN manual position OR a
     non-archived user thesis (an empty position list and an ARCHIVED thesis
     escalate nothing);
  3. earnings of a ticker really present in the DECLARED watchlist;
  4. dividend;
  5. option expiration;
  6. non-global macro event (defensive, generator never emits one today);
  7. earnings of any other observed ticker (outside the declared watchlist:
     the snapshot never claims a watchlist membership it did not verify);
- the ``event_context`` block crosses each ticker event with the MANUAL
  ledger positions (through the same versioned ``fifo/1.0`` derivation as
  the valuation snapshot — ``derive_open_position_tickers``) and the user
  theses (repository projection), plus resource links toward the analysis
  and option-chain snapshots of the ticker — read-derived context only,
  nothing is written back;
- freshness travels to the agenda: every event carries its observation
  ``stale_after``, ``delay_status`` and the derived ``fresh`` flag, so a
  stale event is never displayed as a plain valid one;
- the published ``population`` is computed over ALL considered records
  (displayed AND rejected), and ``agenda_state`` says why an agenda is empty
  (``EMPTY`` nothing observed, ``NOT_ENTITLED`` rights rejection,
  ``REJECTED`` every record invalid, ``OK`` otherwise): an empty agenda is
  never published as a silent success;
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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_core.synthetic import (
    EVENT_CATEGORY_DIVIDEND,
    EVENT_CATEGORY_EARNINGS,
    EVENT_CATEGORY_MACRO,
    EVENT_CATEGORY_OPTION_EXPIRATION,
    EVENT_SCOPE_GLOBAL,
    EVENT_SCOPE_TICKER,
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
    "REASON_INVALID_SCOPE",
    "REASON_INVALID_STATUS",
    "REASON_INVALID_TIMEZONE",
    "REASON_MISSING_TIMEZONE",
    "REASON_RIGHTS_NOT_USABLE",
    "REASON_SOURCE_NOT_ALLOWED",
    "SNAPSHOT_KEY_GLOBAL",
    "SNAPSHOT_KIND_CALENDAR",
    "TOPIC_CALENDAR_INGESTED",
    "AGENDA_STATES",
    "CalendarConfig",
    "CalendarEventRecord",
    "CalendarEventWindow",
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

IMPORTANCE_RULE_VERSION = "importance_rule/1.1"
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
        "description": (
            "resultats d'un ticker present dans la watchlist declaree"
        ),
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
    {
        "rank": 7,
        "code": "EARNINGS_OTHER",
        "description": (
            "resultats d'un autre ticker observe, hors watchlist declaree"
        ),
    },
)
"""The documented ranks of :data:`IMPORTANCE_RULE_VERSION` (1 = highest).

Version 1.1 splits the former catch-all ``EARNINGS_WATCHLIST`` in two: the
label is reserved for a ticker really present in the DECLARED watchlist, every
other observed ticker falling to ``EARNINGS_OTHER``. Adding a rank IS a rule
change, hence the version bump.
"""

_KNOWN_CATEGORIES = frozenset(
    {
        EVENT_CATEGORY_EARNINGS,
        EVENT_CATEGORY_DIVIDEND,
        EVENT_CATEGORY_OPTION_EXPIRATION,
        EVENT_CATEGORY_MACRO,
    }
)
_KNOWN_STATUSES = frozenset({EVENT_STATUS_ESTIMATED, EVENT_STATUS_CONFIRMED})
_KNOWN_SCOPES = frozenset({EVENT_SCOPE_GLOBAL, EVENT_SCOPE_TICKER})

_ESCALATING_THESIS_STATUSES = frozenset({"ACTIVE", "SNOOZED"})
"""Thesis statuses that still escalate an earnings event. An ARCHIVED thesis
stays VISIBLE in the event context but escalates nothing."""

AGENDA_STATES: tuple[str, ...] = ("OK", "EMPTY", "NOT_ENTITLED", "REJECTED")
"""Published agenda states: an empty agenda always names its cause."""

AGENDA_STATE_REASONS: Mapping[str, Optional[str]] = {
    "OK": None,
    "EMPTY": "no calendar observation in the considered window",
    "NOT_ENTITLED": "every considered record was rejected: rights not usable",
    "REJECTED": "every considered record was rejected",
}

REASON_INVALID_PAYLOAD = "invalid_payload"
REASON_INVALID_CATEGORY = "invalid_category"
REASON_INVALID_STATUS = "invalid_status"
REASON_INVALID_EVENT_TIME = "invalid_event_time"
REASON_INVALID_REVISIONS = "invalid_revisions"
REASON_INVALID_SCOPE = "invalid_scope"
REASON_INVALID_TIMEZONE = "invalid_exchange_timezone"
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
    stale_after: datetime
    quality_status: str
    delay_status: str
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


@dataclass(frozen=True)
class CalendarEventWindow:
    """The loaded window and whether the bound TRUNCATED it.

    ``truncated`` is a FACT, not an inference on a count equality: the query
    asks for one row more than the bound and the extra row is dropped here.
    """

    records: tuple[CalendarEventRecord, ...]
    truncated: bool


def load_calendar_event_records(
    session: Session, *, now: datetime, lookback: timedelta, limit: int
) -> CalendarEventWindow:
    """Load the bounded recent calendar-event window, newest first.

    Ordering is ``as_of DESC, id DESC``: beyond ``limit`` the window keeps the
    MOST RECENT observations — a revision is always the newest record of its
    stable id — and reports the truncation instead of silently keeping the
    oldest ones.
    """
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
            .order_by(Observation.as_of.desc(), Observation.id.desc())
            .limit(limit + 1)
        )
        .scalars()
        .all()
    )
    truncated = len(rows) > limit
    return CalendarEventWindow(
        records=tuple(
            CalendarEventRecord(
                event_id=row.event_id,
                source=row.source,
                instrument_ref=row.instrument_ref,
                as_of=row.as_of,
                stale_after=row.stale_after,
                quality_status=row.quality_status,
                delay_status=row.delay_status,
                rights=row.rights,
                schema_version=row.schema_version,
                payload=row.payload,
            )
            for row in rows[:limit]
        ),
        truncated=truncated,
    )


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


def _validated_revisions(
    revisions: Any,
) -> tuple[Optional[list[dict[str, Any]]], Optional[datetime]]:
    """Declared revisions, each DATED with an aware ``revised_at``.

    Returns ``(None, None)`` when the list is unusable: the business ordering
    of a stable id relies on ``revised_at``, so an undated revision cannot be
    accepted and silently fall back to an arbitrary tie-break.
    """
    if not isinstance(revisions, list):
        return None, None
    entries: list[dict[str, Any]] = []
    latest: Optional[datetime] = None
    for entry in revisions:
        if not isinstance(entry, Mapping):
            return None, None
        revised_at = _aware_iso_or_none(entry.get("revised_at"))
        if revised_at is None:
            return None, None
        revised_at = revised_at.astimezone(timezone.utc)
        latest = revised_at if latest is None else max(latest, revised_at)
        entries.append(dict(entry))
    return entries, latest


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
    try:
        zone = ZoneInfo(exchange_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        # An unresolvable label is NOT a timezone: no display could convert
        # the instant with it.
        return None, REASON_INVALID_TIMEZONE
    if event_time_local.utcoffset() != event_time_local.astimezone(
        zone
    ).utcoffset():
        # The declared zone contradicts the local offset: the pair is
        # unusable, and repairing it would invent a wall-clock time.
        return None, REASON_INVALID_TIMEZONE
    ticker = payload.get("ticker")
    if ticker is not None and (not isinstance(ticker, str) or not ticker):
        return None, REASON_INVALID_PAYLOAD
    scope = payload.get("scope")
    if scope not in _KNOWN_SCOPES:
        return None, REASON_INVALID_SCOPE
    expected_scope = EVENT_SCOPE_GLOBAL if ticker is None else EVENT_SCOPE_TICKER
    if scope != expected_scope:
        # A scope contradicting the ticker presence would promote the
        # importance of an event that is not global.
        return None, REASON_INVALID_SCOPE
    revisions, latest_revised_at = _validated_revisions(payload.get("revisions"))
    if revisions is None:
        return None, REASON_INVALID_REVISIONS
    return {
        "stable_id": stable_id,
        "category": category,
        "status": status,
        "title": title,
        "ticker": ticker,
        "scope": scope,
        "event_time_utc": payload["event_time_utc"],
        "event_time_local": payload["event_time_local"],
        "exchange_timezone": exchange_timezone,
        "event_time_utc_parsed": event_time_utc.astimezone(timezone.utc),
        "revisions": revisions,
        "latest_revised_at": latest_revised_at,
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
    watchlist: frozenset[str],
) -> dict[str, Any]:
    """Apply the versioned importance rule (never an invention).

    Every label is VERIFIED before being applied: ``MACRO_GLOBAL`` needs a
    ticker-less event (the scope was validated against the ticker presence)
    and ``EARNINGS_WATCHLIST`` needs a ticker really present in the declared
    watchlist — any other observed ticker is ``EARNINGS_OTHER``.
    """
    category = event["category"]
    ticker = event["ticker"]
    if category == EVENT_CATEGORY_MACRO:
        code = "MACRO_GLOBAL" if ticker is None else "MACRO_TICKER"
    elif category == EVENT_CATEGORY_EARNINGS:
        if ticker is not None and (
            ticker in position_tickers or ticker in thesis_tickers
        ):
            code = "EARNINGS_POSITION_OR_THESIS"
        elif ticker is not None and ticker in watchlist:
            code = "EARNINGS_WATCHLIST"
        else:
            code = "EARNINGS_OTHER"
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


_NO_DECLARED_REVISION = datetime.min.replace(tzinfo=timezone.utc)
"""Business instant of a record declaring NO revision: any dated revision of
the same stable id is later business knowledge than an undated original."""


def _business_order_key(
    record: CalendarEventRecord, event: Mapping[str, Any]
) -> tuple[datetime, datetime, str]:
    """Business chronology of one record of a stable id.

    1. the most recent declared ``revisions[].revised_at`` (a record carrying
       a dated revision states later business knowledge than an original
       carrying none — the two share the SAME ``as_of`` in the normal case);
    2. then the envelope ``as_of`` (reception chronology);
    3. then the envelope ``event_id``, documented as the LAST-RESORT
       deterministic tie-break — it decides nothing else.
    """
    return (
        event["latest_revised_at"] or _NO_DECLARED_REVISION,
        record.as_of,
        record.event_id,
    )


def _previous_value(
    record: CalendarEventRecord, event: Mapping[str, Any]
) -> dict[str, Any]:
    """One READABLE previous value, built from a record really seen."""
    return {
        "source_event_id": record.event_id,
        "source": record.source,
        "as_of": record.as_of.isoformat(),
        "status": event["status"],
        "event_time_utc": event["event_time_utc"],
    }


def build_calendar_content(
    records: Sequence[CalendarEventRecord],
    *,
    now: datetime,
    config: CalendarConfig,
    positions_by_ticker: Mapping[str, Sequence[int]],
    theses_by_ticker: Mapping[str, Sequence[Mapping[str, Any]]],
    truncated: bool = False,
) -> dict[str, Any]:
    """Build the ``calendar/global`` snapshot content (pure, deterministic).

    Identical inputs produce an identical dict. Every considered record is
    either displayed, superseded by another record of the same stable id, or
    rejected with a reason. Estimated and confirmed statuses are relayed
    verbatim (distinct labels); a superseded record is NEVER erased — it
    becomes a readable ``previous_values`` entry beside the ``revisions`` the
    source declares —; freshness and the exchange timezone are conserved.
    """
    now = _require_aware_utc(now)

    rejected: list[dict[str, str]] = []
    rejected_reasons: dict[str, int] = {}
    Candidate = tuple[
        tuple[datetime, datetime, str], CalendarEventRecord, dict[str, Any]
    ]
    by_stable_id: dict[str, list[Candidate]] = {}
    for record in records:
        validated, reason = _validate_event(record, config)
        if validated is None:
            assert reason is not None
            rejected.append({"event_id": record.event_id, "reason": reason})
            rejected_reasons[reason] = rejected_reasons.get(reason, 0) + 1
            continue
        by_stable_id.setdefault(validated["stable_id"], []).append(
            (_business_order_key(record, validated), record, validated)
        )
    rejected.sort(key=lambda entry: (entry["event_id"], entry["reason"]))

    superseded = 0
    latest_by_stable_id: dict[
        str, tuple[CalendarEventRecord, dict[str, Any], list[dict[str, Any]]]
    ] = {}
    for stable_id, candidates in by_stable_id.items():
        candidates.sort(key=lambda item: item[0])
        superseded += len(candidates) - 1
        _, winner_record, winner_event = candidates[-1]
        # The records the winner supersedes stay READABLE, oldest first.
        previous_values = [
            _previous_value(record, event) for _, record, event in candidates[:-1]
        ]
        latest_by_stable_id[stable_id] = (
            winner_record,
            winner_event,
            previous_values,
        )

    # An EMPTY position list is not a position, and an ARCHIVED thesis is not
    # a live one: only verified content escalates the importance.
    position_tickers = frozenset(
        ticker
        for ticker, portfolio_ids in positions_by_ticker.items()
        if tuple(portfolio_ids)
    )
    thesis_tickers = frozenset(
        ticker
        for ticker, theses in theses_by_ticker.items()
        if any(
            isinstance(entry, Mapping)
            and entry.get("status") in _ESCALATING_THESIS_STATUSES
            for entry in theses
        )
    )
    watchlist = frozenset(config.watchlist)

    agenda: list[dict[str, Any]] = []
    categories: dict[str, int] = {}
    statuses: dict[str, int] = {
        EVENT_STATUS_ESTIMATED: 0,
        EVENT_STATUS_CONFIRMED: 0,
    }
    stale_events = 0
    entries = sorted(
        latest_by_stable_id.values(),
        key=lambda item: (item[1]["event_time_utc_parsed"], item[1]["stable_id"]),
    )
    for record, event, previous_values in entries:
        is_synthetic = _is_synthetic_record(record)
        categories[event["category"]] = categories.get(event["category"], 0) + 1
        statuses[event["status"]] += 1
        fresh = now < record.stale_after
        if not fresh:
            stale_events += 1
        # The state CHANGED when the source declares a revision OR when a
        # record really seen carried another status/instant.
        revised = bool(event["revisions"]) or any(
            previous["status"] != event["status"]
            or previous["event_time_utc"] != event["event_time_utc"]
            for previous in previous_values
        )
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
                watchlist=watchlist,
            ),
            "revisions": event["revisions"],
            "previous_values": previous_values,
            "revised": revised,
            "event_context": _event_context(
                event["ticker"],
                positions_by_ticker=positions_by_ticker,
                theses_by_ticker=theses_by_ticker,
            ),
            "synthetic": is_synthetic,
            "quality": record.quality_status,
            "fresh": fresh,
            "stale_after": record.stale_after.isoformat(),
            "delay_status": record.delay_status,
            "source": record.source,
            "rights": record.rights,
            "source_event_id": record.event_id,
        }
        item.update(event["extra"])
        agenda.append(item)

    # The population describes ALL considered records, displayed AND
    # rejected: a fully rejected synthetic population is never called REAL.
    if not records:
        population = "EMPTY"
    elif any(_is_synthetic_record(record) for record in records):
        population = "SYNTHETIC"
    else:
        population = "REAL"

    if agenda:
        agenda_state = "OK"
    elif not records:
        agenda_state = "EMPTY"
    elif REASON_RIGHTS_NOT_USABLE in rejected_reasons:
        agenda_state = "NOT_ENTITLED"
    else:
        agenda_state = "REJECTED"

    return {
        "schema_version": CALENDAR_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "agenda_state": agenda_state,
        "agenda_state_reason": AGENDA_STATE_REASONS[agenda_state],
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
            "events_stale": stale_events,
            "rejected_records": rejected,
            "rejected_reasons": dict(sorted(rejected_reasons.items())),
            "window_truncated": truncated,
            "max_observations": config.max_observations,
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
        window = load_calendar_event_records(
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
            window.records,
            now=now,
            config=self._config,
            positions_by_ticker=positions_by_ticker,
            theses_by_ticker=theses_by_ticker,
            truncated=window.truncated,
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
