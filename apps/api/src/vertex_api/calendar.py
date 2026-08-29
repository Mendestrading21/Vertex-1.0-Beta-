"""Calendar API (page 02): snapshot relay with a bounded display window.

The API computes NO importance, NO status and NO date here: it relays the
worker's ``calendar/global`` snapshot verbatim (or an honest empty state).
The only presentation operation is the OPTIONAL ``from``/``to`` window
filter over ``event_time_utc`` — a pure selection of already-published
events, bounded to :data:`MAX_WINDOW_DAYS` days, requiring BOTH bounds and
aware datetimes (fail-closed 422 otherwise). Estimated/confirmed labels,
revisions and exchange timezones are conserved exactly as published.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping, Optional

from fastapi import HTTPException

from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot

from vertex_api.snapshot_views import (
    SnapshotContentError,
    _parse_utc,
    _require_list,
    _require_mapping,
    _require_str,
)

__all__ = [
    "ERROR_WINDOW_INCOMPLETE",
    "ERROR_WINDOW_INVERTED",
    "ERROR_WINDOW_NAIVE_DATETIME",
    "ERROR_WINDOW_TOO_LARGE",
    "MAX_WINDOW_DAYS",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "SNAPSHOT_KIND_CALENDAR",
    "CalendarResponse",
    "CalendarWindow",
    "build_calendar_response",
    "validate_window",
]

SNAPSHOT_KIND_CALENDAR = "calendar"
SNAPSHOT_KEY_GLOBAL = "global"

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"

MAX_WINDOW_DAYS = 90
"""Hard bound of the from/to query window (inclusive bounds)."""

ERROR_WINDOW_INCOMPLETE = "WINDOW_INCOMPLETE"
ERROR_WINDOW_INVERTED = "WINDOW_INVERTED"
ERROR_WINDOW_TOO_LARGE = "WINDOW_TOO_LARGE"
ERROR_WINDOW_NAIVE_DATETIME = "WINDOW_NAIVE_DATETIME"


class CalendarWindow(ContractModel):
    """Echo of the applied (or absent) display window."""

    applied: bool
    from_utc: Optional[UtcDatetime]
    to_utc: Optional[UtcDatetime]
    max_days: PositiveInt
    events_total: int
    events_in_window: int


class CalendarResponse(ContractModel):
    """The last published calendar snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted agenda VERBATIM (importance from
    the versioned rule, distinct ESTIMATED/CONFIRMED labels, revisions with
    their preserved previous values, exchange timezones); the API invents no
    event and recomputes no importance. ``state = "empty"`` means the worker
    never published: nothing is invented, ``reason`` says why.
    """

    state: Literal["ok", "empty"]
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    population: Optional[NonEmptyStr]
    importance_rule: Optional[FrozenStrMapping]
    agenda: tuple[FrozenStrMapping, ...]
    categories: Optional[FrozenStrMapping]
    statuses: Optional[FrozenStrMapping]
    coverage: Optional[FrozenStrMapping]
    window: CalendarWindow
    reason: Optional[NonEmptyStr]


def _window_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422, detail={"code": code, "message": message}
    )


def validate_window(
    window_from: Optional[datetime], window_to: Optional[datetime]
) -> Optional[tuple[datetime, datetime]]:
    """Validate the from/to pair fail-closed; ``None`` when absent.

    Both bounds or none; aware datetimes only; ``from <= to``; at most
    :data:`MAX_WINDOW_DAYS` days. Every violation is a typed 422.
    """
    if window_from is None and window_to is None:
        return None
    if window_from is None or window_to is None:
        raise _window_error(
            ERROR_WINDOW_INCOMPLETE,
            "the window requires BOTH 'from' and 'to' query parameters",
        )
    for label, value in (("from", window_from), ("to", window_to)):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise _window_error(
                ERROR_WINDOW_NAIVE_DATETIME,
                f"'{label}' must be a timezone-aware datetime",
            )
    start = window_from.astimezone(timezone.utc)
    end = window_to.astimezone(timezone.utc)
    if end < start:
        raise _window_error(
            ERROR_WINDOW_INVERTED, "'to' must not precede 'from'"
        )
    if end - start > timedelta(days=MAX_WINDOW_DAYS):
        raise _window_error(
            ERROR_WINDOW_TOO_LARGE,
            f"the window is bounded to {MAX_WINDOW_DAYS} days",
        )
    return start, end


def _event_in_window(
    event: Mapping[str, Any], start: datetime, end: datetime
) -> bool:
    raw = event.get("event_time_utc")
    instant = _parse_utc(raw, field="agenda[].event_time_utc")
    return start <= instant <= end


def build_calendar_response(
    snapshot: Optional[CurrentSnapshot],
    *,
    window: Optional[tuple[datetime, datetime]],
) -> CalendarResponse:
    """Render the last calendar snapshot, or the honest empty state.

    Presentation only: the persisted content is shape-checked fail-closed
    and relayed VERBATIM; the optional window filter SELECTS events without
    altering any of them. Absence of a published snapshot is a NORMAL state
    (200 with ``state = "empty"``), never a 500 and never an invented agenda.
    """
    if snapshot is None:
        return CalendarResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            importance_rule=None,
            agenda=(),
            categories=None,
            statuses=None,
            coverage=None,
            window=CalendarWindow(
                applied=window is not None,
                from_utc=None if window is None else window[0],
                to_utc=None if window is None else window[1],
                max_days=MAX_WINDOW_DAYS,
                events_total=0,
                events_in_window=0,
            ),
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = _require_mapping(snapshot.content, field="content")
    agenda_raw = _require_list(content.get("agenda"), field="agenda")
    importance_rule = _require_mapping(
        content.get("importance_rule"), field="importance_rule"
    )
    _require_str(importance_rule.get("version"), field="importance_rule.version")
    events: list[Mapping[str, Any]] = []
    for index, raw in enumerate(agenda_raw):
        event = _require_mapping(raw, field=f"agenda[{index}]")
        status = event.get("status")
        if status not in ("ESTIMATED", "CONFIRMED"):
            raise SnapshotContentError(
                f"agenda[{index}].status: 'ESTIMATED' or 'CONFIRMED' required"
            )
        importance = _require_mapping(
            event.get("importance"), field=f"agenda[{index}].importance"
        )
        _require_str(
            importance.get("rule_version"),
            field=f"agenda[{index}].importance.rule_version",
        )
        _require_str(
            event.get("exchange_timezone"),
            field=f"agenda[{index}].exchange_timezone",
        )
        if not isinstance(event.get("revisions"), list):
            raise SnapshotContentError(
                f"agenda[{index}].revisions: list required"
            )
        events.append(event)

    if window is None:
        selected = events
    else:
        start, end = window
        selected = [
            event for event in events if _event_in_window(event, start, end)
        ]

    return CalendarResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=_require_str(content.get("population"), field="population"),
        importance_rule=dict(importance_rule),
        agenda=tuple(dict(event) for event in selected),
        categories=dict(
            _require_mapping(content.get("categories"), field="categories")
        ),
        statuses=dict(
            _require_mapping(content.get("statuses"), field="statuses")
        ),
        coverage=dict(
            _require_mapping(content.get("coverage"), field="coverage")
        ),
        window=CalendarWindow(
            applied=window is not None,
            from_utc=None if window is None else window[0],
            to_utc=None if window is None else window[1],
            max_days=MAX_WINDOW_DAYS,
            events_total=len(events),
            events_in_window=len(selected),
        ),
        reason=None,
    )
