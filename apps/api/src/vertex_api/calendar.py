"""Calendar API (page 02): snapshot relay with a bounded display window.

The API computes NO importance, NO status and NO date here: it relays the
worker's ``calendar/global`` snapshot verbatim (or an honest empty state).
The only presentation operation is the OPTIONAL ``from``/``to`` window
filter over ``event_time_utc`` — a pure selection of already-published
events, bounded to :data:`MAX_WINDOW_DAYS` days, requiring BOTH bounds and
aware datetimes (fail-closed 422 otherwise). Estimated/confirmed labels,
revisions, previous values, freshness and exchange timezones are conserved
exactly as published.

Four honesty rules govern the relayed state:

- the ``state`` comes from the worker's published ``agenda_state`` (single
  authority). An agenda emptied by a rights rejection is served as
  ``not_entitled`` WITH its reason — page 02 forbids the misleading empty
  agenda — a wholly stale agenda as ``stale``, and an unknown state value
  fails closed instead of being shown ``ok``;
- BACKWARD COMPATIBILITY — GENERAL RULE (documented choice): **an ABSENT
  field is a KNOWN earlier contract and degrades the response; a PRESENT but
  unreadable VALUE is a claim the relay cannot verify and still fails
  closed.** Publication is publish-if-changed, so a snapshot published under
  an earlier contract is never republished until a new calendar observation
  arrives — which may be never. Refusing it would leave page 02 in a
  PERMANENT 500 for a snapshot that is otherwise readable. The rule
  therefore applies IDENTICALLY to ``agenda_state`` and to the event fields
  listed in :data:`LEGACY_EVENT_FIELDS` (``previous_values``, ``revisions``,
  ``stale_after``): each absence is named in the served ``reason``, the
  published agenda is relayed as usual, and the served state is the explicit
  ``degraded`` — never ``ok``. Everything else keeps failing closed exactly
  as before;
- FRESHNESS (fail-closed, ``financial-safety.md``: never silently keep an
  old verdict). ``agenda_state`` and the per-event ``fresh`` flag are
  computed at CONSTRUCTION time and frozen in the snapshot; publish-if-
  changed means no recomputation ever happens afterwards. Two clock-relative
  claims are therefore re-evaluated HERE against the server clock and the
  server ``as_of`` COLUMN (never the ``as_of`` string inside the content,
  which is persisted data like any other): past
  :data:`CALENDAR_MAX_AGE` the snapshot is served ``stale`` with its age and
  its cause, and every event's ``fresh`` boolean is RECOMPUTED from its
  published ``stale_after`` — or REMOVED when the snapshot publishes no
  ``stale_after`` to verify it against. It is the single value the relay
  derives instead of relaying: a frozen ``fresh: true`` is a false statement
  about the reader's present, not a published fact;
- every relayed event is shape-checked IDENTICALLY with and without a
  window (``event_time_utc`` included), so one snapshot always yields ONE
  behaviour; the counters of what is really displayed travel in ``window``
  beside the published snapshot-wide totals; and a window that selects NONE
  of the published events is served ``empty_window`` — the API states the
  result of its OWN selection instead of relaying ``ok`` with an empty list,
  and never overwrites a non-ok worker verdict.

No response FIELD is added by any of this (the served ``reason`` carries the
age in seconds beside its budget), so the published contract — and the
committed ``apps/api/openapi.json`` rendered from it — is unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException

from vertex_api.snapshot_views import (
    SnapshotContentError,
    _parse_utc,
    _relayed_timezone,
    _require_list,
    _require_mapping,
    _require_str,
    checked_relayed_content,
)
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_core.data.freshness import get_freshness_policy
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "AGENDA_STATE_TO_RESPONSE_STATE",
    "CALENDAR_FRESHNESS_POLICY",
    "CALENDAR_MAX_AGE",
    "ERROR_WINDOW_INCOMPLETE",
    "ERROR_WINDOW_INVERTED",
    "ERROR_WINDOW_NAIVE_DATETIME",
    "ERROR_WINDOW_TOO_LARGE",
    "LEGACY_EVENT_FIELDS",
    "MAX_WINDOW_DAYS",
    "REASON_EVERY_SERVED_EVENT_STALE",
    "REASON_LEGACY_EVENT_FIELDS",
    "REASON_MISSING_AGENDA_STATE",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "REASON_SNAPSHOT_STALE",
    "SNAPSHOT_KIND_CALENDAR",
    "STATE_DEGRADED",
    "STATE_EMPTY_WINDOW",
    "CalendarResponse",
    "CalendarWindow",
    "build_calendar_response",
    "validate_window",
]

SNAPSHOT_KIND_CALENDAR = "calendar"
SNAPSHOT_KEY_GLOBAL = "global"

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"

CalendarState = Literal[
    "ok", "empty", "not_entitled", "rejected", "stale", "empty_window", "degraded"
]
"""États servis par la page Calendrier — le contrat, pas une chaîne libre."""

STATE_DEGRADED: CalendarState = "degraded"
"""Served when the snapshot omits a field of a LATER contract — the
``agenda_state`` itself or one of :data:`LEGACY_EVENT_FIELDS`: the agenda is
relayed, the state is honestly incomplete — never ``ok``."""

STATE_EMPTY_WINDOW: CalendarState = "empty_window"
"""Served when the REQUESTED window selects none of the published events."""

REASON_MISSING_AGENDA_STATE = (
    "state field missing: snapshot predates the current agenda_state contract"
)

AGENDA_STATE_TO_RESPONSE_STATE: Mapping[str, CalendarState] = {
    "OK": "ok",
    "EMPTY": "empty",
    "NOT_ENTITLED": "not_entitled",
    "REJECTED": "rejected",
    "STALE": "stale",
}
"""Published worker state -> served state. The worker OWNS the verdict; an
``agenda_state`` VALUE outside this mapping is refused, never downgraded to
ok (an ABSENT field is the documented legacy case, served ``degraded``)."""

LEGACY_EVENT_FIELDS: tuple[str, ...] = (
    "previous_values",
    "revisions",
    "stale_after",
)
"""Event fields a snapshot of an EARLIER contract may not carry.

The first published calendar builder emitted none of ``previous_values``
(its own trace of the superseded records did not exist yet) nor the
freshness pair ``stale_after``/``fresh``. Their ABSENCE is that known
earlier contract — degradation, named in the reason — while a PRESENT but
unreadable value stays a refusal.
"""

REASON_LEGACY_EVENT_FIELDS = (
    "event fields missing ({fields}): snapshot predates the current agenda "
    "contract"
)

CALENDAR_FRESHNESS_POLICY = "corporate_event"
"""Freshness policy of the observations an agenda is built from.

An agenda entry IS a corporate/economic event observation (earnings,
dividend, option expiration, macro release), so the versioned registry
policy of that observation family — not a number invented here — bounds how
long a published agenda may be relayed as current. ``corporate_event``
declares the same TTL for an open and a closed session, so the relay (which
knows no session state) needs no conservative pick between the two.
"""

_FRESHNESS_POLICY = get_freshness_policy(CALENDAR_FRESHNESS_POLICY)

CALENDAR_MAX_AGE = timedelta(seconds=_FRESHNESS_POLICY.ttl_closed_seconds)
"""Freshness budget of the relayed snapshot. Past it the agenda is served
``stale``: an agenda published days ago is not a current one, whatever the
frozen ``agenda_state`` says."""

REASON_SNAPSHOT_STALE = (
    "snapshot older than its freshness budget: age {age} s for a budget of "
    "{budget} s ({policy}@{version} closed-session TTL); the worker "
    "published nothing newer"
)

REASON_EVERY_SERVED_EVENT_STALE = (
    "every served event is past its published stale_after ({count}/{count} "
    "at the relay clock)"
)
"""Served when the frozen ``OK`` verdict outlived every event it vouched
for: the recomputed flags and the served state must never disagree."""

_ZERO = timedelta(0)

MAX_WINDOW_DAYS = 90
"""Hard bound of the from/to query window (inclusive bounds)."""

ERROR_WINDOW_INCOMPLETE = "WINDOW_INCOMPLETE"
ERROR_WINDOW_INVERTED = "WINDOW_INVERTED"
ERROR_WINDOW_TOO_LARGE = "WINDOW_TOO_LARGE"
ERROR_WINDOW_NAIVE_DATETIME = "WINDOW_NAIVE_DATETIME"


class CalendarWindow(ContractModel):
    """Echo of the applied (or absent) display window.

    ``categories`` and ``statuses`` count the events REALLY displayed, so the
    counters never contradict the served list; the snapshot-wide totals stay
    published beside them in ``categories``/``statuses``/``coverage``.
    """

    applied: bool
    from_utc: UtcDatetime | None
    to_utc: UtcDatetime | None
    max_days: PositiveInt
    events_total: int
    events_in_window: int
    categories: FrozenStrMapping
    statuses: FrozenStrMapping


class CalendarResponse(ContractModel):
    """The last published calendar snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted agenda VERBATIM (importance from
    the versioned rule, distinct ESTIMATED/CONFIRMED labels, revisions and
    previous values, freshness, exchange timezones); the API invents no event
    and recomputes no importance. ``state = "empty"`` means nothing to show
    (never published, or nothing observed), ``state = "not_entitled"`` that
    the considered records were rejected for missing rights,
    ``state = "rejected"`` that they were all invalid, ``state = "stale"``
    that the agenda is no longer current — the worker published ``STALE``,
    the snapshot is past :data:`CALENDAR_MAX_AGE`, or every served event has
    passed its published ``stale_after`` at the relay clock —,
    ``state = "empty_window"`` that the REQUESTED window selects none of the
    published events, and ``state = "degraded"`` that the snapshot predates
    a field of the current contract and is therefore incomplete. Every
    non-ok state carries its ``reason``: an empty agenda never passes for a
    success, and a relayed ``fresh`` flag is recomputed against the server
    clock — never a frozen boolean.
    """

    state: CalendarState
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    population: NonEmptyStr | None
    importance_rule: FrozenStrMapping | None
    agenda: tuple[FrozenStrMapping, ...]
    categories: FrozenStrMapping | None
    statuses: FrozenStrMapping | None
    coverage: FrozenStrMapping | None
    window: CalendarWindow
    reason: NonEmptyStr | None


def _window_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422, detail={"code": code, "message": message}
    )


def validate_window(
    window_from: datetime | None, window_to: datetime | None
) -> tuple[datetime, datetime] | None:
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
    start = window_from.astimezone(UTC)
    end = window_to.astimezone(UTC)
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


def _counters(
    events: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    """Category and status counters of the events REALLY served."""
    categories: dict[str, int] = {}
    statuses: dict[str, int] = {"ESTIMATED": 0, "CONFIRMED": 0}
    for event in events:
        category = event.get("category")
        if isinstance(category, str) and category:
            categories[category] = categories.get(category, 0) + 1
        statuses[str(event["status"])] += 1
    return dict(sorted(categories.items())), statuses


def _window_echo(
    window: tuple[datetime, datetime] | None,
    *,
    events_total: int,
    selected: Sequence[Mapping[str, Any]],
) -> CalendarWindow:
    categories, statuses = _counters(selected)
    return CalendarWindow(
        applied=window is not None,
        from_utc=None if window is None else window[0],
        to_utc=None if window is None else window[1],
        max_days=MAX_WINDOW_DAYS,
        events_total=events_total,
        events_in_window=len(selected),
        categories=categories,
        statuses=statuses,
    )


def _utc_now() -> datetime:
    """Relay clock seam.

    The calendar route carries no clock dependency, so the default instant is
    read here; every caller may inject ``now`` instead (tests always do — no
    test depends on the real time).
    """
    return datetime.now(UTC)


def _snapshot_age(snapshot: CurrentSnapshot, *, now: datetime) -> timedelta:
    """Age measured on SERVER timestamps only (never on stored content)."""
    as_of = snapshot.as_of
    if not isinstance(as_of, datetime):
        raise SnapshotContentError(
            "snapshot.as_of: datetime required", field="snapshot.as_of"
        )
    if as_of.tzinfo is None or as_of.tzinfo.utcoffset(as_of) is None:
        raise SnapshotContentError(
            "snapshot.as_of: naive datetime rejected", field="snapshot.as_of"
        )
    age = now.astimezone(UTC) - as_of.astimezone(UTC)
    if age < _ZERO:
        raise SnapshotContentError(
            "snapshot.as_of: a snapshot dated in the future cannot be served",
            field="snapshot.as_of",
        )
    return age


def build_calendar_response(
    snapshot: CurrentSnapshot | None,
    *,
    window: tuple[datetime, datetime] | None,
    now: datetime | None = None,
) -> CalendarResponse:
    """Render the last calendar snapshot, or the honest empty state.

    Presentation only: the persisted content is shape-checked fail-closed
    and relayed VERBATIM — the single exception being the clock-relative
    ``fresh`` flag, RECOMPUTED here (or removed when unverifiable), because a
    frozen boolean about the reader's present is not a published fact. The
    optional window filter SELECTS events without altering any of them.
    Absence of a published snapshot is a NORMAL state (200 with
    ``state = "empty"``), never a 500 and never an invented agenda.

    Two symmetric halves of ONE rule govern an incomplete snapshot: an
    ABSENT field of :data:`LEGACY_EVENT_FIELDS` (or an absent
    ``agenda_state``) is an earlier contract — served ``degraded``, its
    cause named — while a PRESENT but unreadable value is refused. Past
    :data:`CALENDAR_MAX_AGE` the (still readable) agenda is served ``stale``
    with its age; so is an agenda every served event of which has passed its
    published ``stale_after``.
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
            window=_window_echo(window, events_total=0, selected=()),
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    relay_clock = _utc_now() if now is None else now
    if relay_clock.tzinfo is None or relay_clock.tzinfo.utcoffset(relay_clock) is None:
        # A naive clock would be read as local time and silently shift every
        # age and every recomputed ``fresh`` flag.
        raise ValueError("now must be a timezone-aware datetime")
    age = _snapshot_age(snapshot, now=relay_clock)

    content = checked_relayed_content(snapshot.content)
    agenda_raw = _require_list(content.get("agenda"), field="agenda")
    # Fields an EARLIER contract may not carry. Absence degrades (and is
    # named); a present but unreadable value still fails closed.
    legacy_fields: set[str] = set()
    importance_rule = _require_mapping(
        content.get("importance_rule"), field="importance_rule"
    )
    _require_str(importance_rule.get("version"), field="importance_rule.version")
    events: list[Mapping[str, Any]] = []
    instants: list[datetime] = []
    for index, raw in enumerate(agenda_raw):
        event = dict(_require_mapping(raw, field=f"agenda[{index}]"))
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
        # P2-1: a PRESENT exchange timezone must be a RESOLVABLE IANA zone.
        # ``_require_str`` alone accepted ``Mars/Olympus`` and page 02 served
        # it 200 ``state = "ok"`` — the single leak of the rule "a present
        # but unreadable value fails closed". Every local instant published
        # beside it (``event_time_local``, the revision history) is stated in
        # that zone, so a zone nothing resolves makes them unverifiable.
        _relayed_timezone(
            _require_str(
                event.get("exchange_timezone"),
                field=f"agenda[{index}].exchange_timezone",
            ),
            field=f"agenda[{index}].exchange_timezone",
        )
        for field in ("previous_values", "revisions"):
            if field not in event:
                # Earlier contract: degrade, never take the page down.
                legacy_fields.add(field)
            elif not isinstance(event[field], list):
                raise SnapshotContentError(
                    f"agenda[{index}].{field}: list required",
                    field=f"agenda[{index}].{field}",
                )
        # ``fresh`` is a claim about the RELAY clock, not a published fact:
        # it is recomputed from the published ``stale_after``, and removed
        # outright when the snapshot carries none to verify it against.
        if "stale_after" not in event:
            legacy_fields.add("stale_after")
            event.pop("fresh", None)
        else:
            stale_after = _parse_utc(
                event["stale_after"], field=f"agenda[{index}].stale_after"
            )
            event["fresh"] = relay_clock < stale_after
        # Checked for EVERY event, window or not: one snapshot, ONE
        # behaviour. An unusable instant can never be served as valid.
        instant = _parse_utc(
            event.get("event_time_utc"), field=f"agenda[{index}].event_time_utc"
        )
        instants.append(instant)
        events.append(event)

    published_state = content.get("agenda_state")
    agenda_state: str | None
    reason: str | None
    if published_state is None:
        # Documented backward compatibility: publish-if-changed would keep an
        # older snapshot in place indefinitely, so its readable agenda is
        # served DEGRADED instead of turning page 02 into a permanent 500.
        agenda_state = None
        state = STATE_DEGRADED
        reason = REASON_MISSING_AGENDA_STATE
    else:
        agenda_state = _require_str(published_state, field="agenda_state")
        if agenda_state not in AGENDA_STATE_TO_RESPONSE_STATE:
            raise SnapshotContentError(
                "agenda_state: one of "
                + ", ".join(sorted(AGENDA_STATE_TO_RESPONSE_STATE))
                + " required"
            )
        state = AGENDA_STATE_TO_RESPONSE_STATE[agenda_state]
        reason = content.get("agenda_state_reason")
        if reason is not None and (not isinstance(reason, str) or not reason):
            raise SnapshotContentError(
                "agenda_state_reason: non-empty string or null required"
            )
        if agenda_state != "OK" and reason is None:
            # A non-ok state without its cause would be an unexplained empty
            # agenda: refuse it rather than serve it.
            raise SnapshotContentError(
                "agenda_state_reason: required for a non-OK agenda_state"
            )

    if window is None:
        selected = events
    else:
        start, end = window
        selected = [
            event
            for event, instant in zip(events, instants, strict=True)
            if start <= instant <= end
        ]

    empties_the_window = window is not None and bool(events) and not selected
    if empties_the_window and state in ("ok", "stale"):
        # The API states the result of its OWN selection: the events exist,
        # outside the requested window. A non-ok worker verdict is never
        # overwritten — its cause stays the served reason.
        reason = (
            f"the requested window selects none of the {len(events)} "
            f"published events (published agenda_state: {agenda_state})"
        )
        state = STATE_EMPTY_WINDOW

    if legacy_fields:
        # Same rule as the absent ``agenda_state``: the earlier contract is
        # NAMED and degrades the state; it never hides the agenda, and it
        # never overwrites a non-ok worker verdict either.
        degradation = REASON_LEGACY_EVENT_FIELDS.format(
            fields=", ".join(sorted(legacy_fields))
        )
        if state == "ok":
            state = STATE_DEGRADED
        reason = degradation if reason is None else f"{reason}; {degradation}"

    # Frozen freshness re-evaluated against the SERVER clock: the snapshot's
    # own budget first, then the recomputed per-event flags. Neither may
    # leave a state saying ``ok`` about an agenda nothing vouches for.
    if age > CALENDAR_MAX_AGE:
        freshness_reason: str | None = REASON_SNAPSHOT_STALE.format(
            age=int(age.total_seconds()),
            budget=int(CALENDAR_MAX_AGE.total_seconds()),
            policy=_FRESHNESS_POLICY.name,
            version=_FRESHNESS_POLICY.version,
        )
        if state in ("ok", STATE_DEGRADED, STATE_EMPTY_WINDOW):
            state = "stale"
    elif (
        state in ("ok", STATE_DEGRADED)
        and selected
        and all(entry.get("fresh") is False for entry in selected)
    ):
        # The worker's ``OK`` verdict outlived every event it vouched for.
        freshness_reason = REASON_EVERY_SERVED_EVENT_STALE.format(
            count=len(selected)
        )
        state = "stale"
    else:
        freshness_reason = None
    if freshness_reason is not None:
        reason = (
            freshness_reason if reason is None else f"{freshness_reason}; {reason}"
        )

    return CalendarResponse(
        state=state,
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
        window=_window_echo(
            window, events_total=len(events), selected=selected
        ),
        reason=reason,
    )
