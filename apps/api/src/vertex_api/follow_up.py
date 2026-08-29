"""Follow-up API (page 09): thesis writes and the review-queue relay.

Authority boundaries:

- theses and their revisions are USER-WRITTEN statements persisted through
  ``vertex_persistence.repository.theses`` ONLY (``create_thesis`` /
  ``record_thesis_revision``). Revisions are append-only; the current status
  is never stored — it is a pure projection recomputed by the repository;
- every write carries a CLIENT-SUPPLIED ``idempotency_key`` (mandatory):
  replaying the same request writes NOTHING and answers ``created=false``
  with the ORIGINAL ids — never a duplicate row. Reusing a key for a
  different operation is a clean 409 conflict;
- a thesis without a non-blank ``invalidation`` is refused at the wire (and
  again by the repository and the database CHECK): a belief without a stated
  falsifier cannot enter the queue;
- every ACCEPTED write enqueues ``review_queue.refresh`` IN THE SAME
  TRANSACTION (outbox atomicity, ADR-006) so the worker recomputes the
  queue; a replay (no write) enqueues nothing. The topic string is
  re-declared here because the API never imports worker code;
- ``GET /api/v1/follow-up/queue`` relays the worker's ``review_queue/global``
  snapshot VERBATIM, or an honest empty state — the API computes no urgency,
  no ordering and no projection of its own.

FAIL-CLOSED SHAPE CHECK (P1-G). "Verbatim relay" is not "unchecked relay".
The queue relay used to publish ``dict(snapshot.content)`` with no shape check
at all: the only constraint was pydantic's strict typing of the FIRST-LEVEL
KEYS of a ``FrozenStrMapping``, so ANY payload whose keys happened to be
strings was served ``200 state="ok"`` — a nested object where an instant
belongs, a string carrying NUL/BEL/ANSI escapes, a 5000-character value, an
entirely foreign schema. :func:`build_follow_up_queue_response` now validates
the SHAPE of every field the worker publishes
(``vertex_worker.follow_up.build_review_queue_content``), at the same level as
the ``vertex_api.snapshot_views`` relays: the refusal is a typed
:class:`~vertex_api.snapshot_views.SnapshotContentError` naming its FIELD PATH
only, so no stored value reaches the response body or a log record. Nothing is
recomputed, corrected or defaulted — a content that does not match its
published schema is REFUSED, never repaired.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Mapping, Optional, Protocol

from fastapi import FastAPI
from pydantic import StringConstraints, model_validator
from sqlalchemy import text

from vertex_api.auth.db import open_db_session
from vertex_api.snapshot_views import (
    SnapshotContentError,
    _optional_str,
    _parse_utc,
    _require_bool,
    _require_list,
    _require_mapping,
    _require_non_negative_int,
    _require_positive_int,
    _require_str,
    _wire_mapping,
)
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import CurrentSnapshot
from vertex_persistence.repository.theses import (
    CreatedThesis,
    RecordedRevision,
    create_thesis,
    record_thesis_revision,
)

__all__ = [
    "ERROR_IDEMPOTENCY_KEY_REUSED",
    "ERROR_UNKNOWN_PORTFOLIO",
    "ERROR_UNKNOWN_THESIS",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "REVIEW_QUEUE_CONTENT_SCHEMA_VERSION",
    "SNAPSHOT_KEY_REVIEW_QUEUE",
    "SNAPSHOT_KIND_REVIEW_QUEUE",
    "TOPIC_REVIEW_QUEUE_REFRESH",
    "CreateThesisRequest",
    "CreateThesisResponse",
    "DbFollowUpGateway",
    "FollowUpGateway",
    "FollowUpQueueResponse",
    "ThesisInstrumentInput",
    "ThesisRevisionRequest",
    "ThesisRevisionResponse",
    "build_follow_up_queue_response",
    "checked_review_queue_content",
]

TOPIC_REVIEW_QUEUE_REFRESH = "review_queue.refresh"
"""Outbox topic OWNED by the worker (``vertex_worker.follow_up``); the string
is re-declared here because the API enqueues jobs but never imports worker
code (module boundary)."""

OUTBOX_NOTIFY_CHANNEL = "vertex_outbox"
"""Best-effort wake-up channel (signal only; the outbox table is the queue)."""

SNAPSHOT_KIND_REVIEW_QUEUE = "review_queue"
SNAPSHOT_KEY_REVIEW_QUEUE = "global"
"""Snapshot published by the worker's ``review_queue.refresh`` handler."""

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"

REVIEW_QUEUE_CONTENT_SCHEMA_VERSION = "vertex.review-queue/1.0"
"""The ONLY content schema this relay knows how to read.

Cross-process exchanges use a versioned contract (``architecture.md``): a
payload announcing another version — or none — is refused rather than read
with rules that no longer describe it. Raising the worker's version is
therefore an explicit, reviewed migration on both sides, never a silent
reinterpretation.
"""

_THESIS_STATUSES = frozenset({"ACTIVE", "SNOOZED", "ARCHIVED"})
"""The projected statuses ``vertex_persistence.repository.theses`` computes.

Deny-by-default: any other label is refused rather than displayed as an
unknown state of a user-written commitment.
"""

_QUEUE_COVERAGE_COUNTS: tuple[str, ...] = (
    "theses_total",
    "due_count",
    "theses_with_instrument",
    "theses_with_new_information",
    "observations_considered",
    "content_observations",
    "clusters",
    "lookback_seconds",
)

# Machine-readable error codes (stable tokens).
ERROR_UNKNOWN_THESIS = "UNKNOWN_THESIS"
ERROR_UNKNOWN_PORTFOLIO = "UNKNOWN_PORTFOLIO"
ERROR_IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"

_TICKER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"

TickerStr = Annotated[str, StringConstraints(pattern=_TICKER_PATTERN)]
NonBlankText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]
NonBlankShort = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
IdempotencyKey = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]
NoteStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]

RevisionAction = Literal[
    "REVIEWED", "SNOOZED", "NOTE_UPDATED", "ARCHIVED", "REACTIVATED"
]
"""Allowlist of the revision route. ``CREATED`` is deliberately absent: the
first revision exists only through ``POST /api/v1/theses``."""


# ---------------------------------------------------------------------------
# Wire DTOs
# ---------------------------------------------------------------------------


class ThesisInstrumentInput(ContractModel):
    """Canonical instrument reference of a thesis (plain ticker for now)."""

    ticker: TickerStr


class CreateThesisRequest(ContractModel):
    """One user-written thesis to append (statement + mandatory falsifier).

    ``invalidation`` is REQUIRED and non-blank: what would prove the thesis
    wrong is part of the statement, never optional. ``idempotency_key`` is
    the CLIENT's replay token: the same key always answers with the same
    thesis, and writes at most once.
    """

    title: NonBlankShort
    hypotheses: NonBlankText
    invalidation: NonBlankText
    idempotency_key: IdempotencyKey
    portfolio_id: Optional[PositiveInt] = None
    instrument: Optional[ThesisInstrumentInput] = None
    horizon: Optional[NonBlankShort] = None
    review_due_at: Optional[UtcDatetime] = None
    note: Optional[NoteStr] = None


class CreateThesisResponse(ContractModel):
    """Receipt: ``created=false`` marks an idempotent replay (nothing written)."""

    thesis_id: PositiveInt
    revision_id: PositiveInt
    created: bool
    refresh_enqueued: bool


class ThesisRevisionRequest(ContractModel):
    """One append-only review-lifecycle revision of an existing thesis.

    ``snooze_until`` is required exactly when ``action`` is SNOOZED and
    forbidden otherwise (also enforced by the repository and by CHECK).
    """

    action: RevisionAction
    idempotency_key: IdempotencyKey
    note: Optional[NoteStr] = None
    snapshot_ref: Optional[NonBlankShort] = None
    snooze_until: Optional[UtcDatetime] = None

    @model_validator(mode="after")
    def _check_snooze_shape(self) -> "ThesisRevisionRequest":
        if self.action == "SNOOZED":
            if self.snooze_until is None:
                raise ValueError("snooze_until: required for a SNOOZED revision")
        elif self.snooze_until is not None:
            raise ValueError(
                f"snooze_until: only a SNOOZED revision carries one, not {self.action}"
            )
        return self


class ThesisRevisionResponse(ContractModel):
    """Receipt: ``created=false`` marks an idempotent replay (nothing written)."""

    thesis_id: PositiveInt
    revision_id: PositiveInt
    created: bool
    refresh_enqueued: bool


class FollowUpQueueResponse(ContractModel):
    """The last published review queue snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted content VERBATIM (projected states,
    documented ordering, urgency flags, populations kept separate); the API
    recomputes nothing. ``state = "empty"`` means the worker never published
    the queue: nothing is invented, ``reason`` says why.
    """

    state: Literal["ok", "empty"]
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    content: Optional[FrozenStrMapping]
    reason: Optional[NonEmptyStr]


# ---------------------------------------------------------------------------
# Gateway (protocol + real database implementation)
# ---------------------------------------------------------------------------


class FollowUpGateway(Protocol):
    """Narrow write boundary of the thesis routes (tests substitute fakes)."""

    def create(self, request: CreateThesisRequest, *, now: datetime) -> CreatedThesis:
        """Insert thesis + CREATED revision + refresh enqueue, one transaction."""
        ...

    def record_revision(
        self, thesis_id: int, request: ThesisRevisionRequest, *, now: datetime
    ) -> RecordedRevision:
        """Append one revision + refresh enqueue, one transaction."""
        ...


class DbFollowUpGateway:
    """Real gateway over the application's engine (one session per call).

    Writes go EXCLUSIVELY through ``vertex_persistence.repository.theses``;
    the ``review_queue.refresh`` enqueue shares the write's transaction and
    happens only when a row was actually written (a replay enqueues nothing).
    """

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    @staticmethod
    def _enqueue_refresh(session, *, reason: str, thesis_id: int) -> None:
        enqueue_outbox(
            session,
            TOPIC_REVIEW_QUEUE_REFRESH,
            {"reason": reason, "thesis_id": thesis_id},
        )
        # Wake-up signal only, delivered on commit; polling remains the
        # delivery guarantee (ADR-006: NOTIFY is never the queue).
        session.execute(
            text("SELECT pg_notify(:channel, :topic)"),
            {"channel": OUTBOX_NOTIFY_CHANNEL, "topic": TOPIC_REVIEW_QUEUE_REFRESH},
        )

    def create(self, request: CreateThesisRequest, *, now: datetime) -> CreatedThesis:
        with open_db_session(self._app) as session:
            result = create_thesis(
                session,
                title=request.title,
                hypotheses=request.hypotheses,
                invalidation=request.invalidation,
                idempotency_key=request.idempotency_key,
                now=now,
                portfolio_id=request.portfolio_id,
                instrument=(
                    {"ticker": request.instrument.ticker}
                    if request.instrument is not None
                    else None
                ),
                horizon=request.horizon,
                review_due_at=request.review_due_at,
                note=request.note,
            )
            if result.created:
                self._enqueue_refresh(
                    session, reason="thesis_created", thesis_id=result.thesis_id
                )
            session.commit()
            return result

    def record_revision(
        self, thesis_id: int, request: ThesisRevisionRequest, *, now: datetime
    ) -> RecordedRevision:
        with open_db_session(self._app) as session:
            result = record_thesis_revision(
                session,
                thesis_id=thesis_id,
                action=request.action,
                idempotency_key=request.idempotency_key,
                recorded_at=now,
                note=request.note,
                snapshot_ref=request.snapshot_ref,
                snooze_until=request.snooze_until,
            )
            if result.created:
                self._enqueue_refresh(
                    session, reason="thesis_revised", thesis_id=thesis_id
                )
            session.commit()
            return result


# ---------------------------------------------------------------------------
# Response builder (pure presentation, no computation)
# ---------------------------------------------------------------------------


def _optional_utc(value: Any, *, field: str) -> None:
    """An instant that may be absent — but never malformed when present.

    ``None`` is a legitimate published value (no review scheduled, no snooze,
    never reviewed); a present value must be a real aware ISO-8601 instant.
    The parsed result is discarded: the relay validates, it never rewrites
    the verbatim content.
    """
    if value is None:
        return
    _parse_utc(value, field=field)


def _checked_thesis_entry(raw: Any, *, index: int) -> None:
    """One queue entry: the user's statement and its PROJECTED state."""
    field = f"theses[{index}]"
    entry = _require_mapping(raw, field=field)

    thesis = _require_mapping(entry.get("thesis"), field=f"{field}.thesis")
    _require_positive_int(thesis.get("id"), field=f"{field}.thesis.id")
    portfolio_id = thesis.get("portfolio_id")
    if portfolio_id is not None:
        _require_positive_int(portfolio_id, field=f"{field}.thesis.portfolio_id")
    instrument = thesis.get("instrument")
    if instrument is not None:
        _wire_mapping(instrument, field=f"{field}.thesis.instrument")
    _require_str(thesis.get("title"), field=f"{field}.thesis.title")
    _require_str(thesis.get("hypotheses"), field=f"{field}.thesis.hypotheses")
    # The falsifier is mandatory at the wire, in the repository and in the
    # database CHECK: a belief without one may not be displayed either.
    _require_str(thesis.get("invalidation"), field=f"{field}.thesis.invalidation")
    _optional_str(thesis.get("horizon"), field=f"{field}.thesis.horizon")
    _optional_utc(thesis.get("review_due_at"), field=f"{field}.thesis.review_due_at")
    _parse_utc(thesis.get("created_at"), field=f"{field}.thesis.created_at")

    state = _require_mapping(entry.get("state"), field=f"{field}.state")
    if state.get("status") not in _THESIS_STATUSES:
        raise SnapshotContentError(
            f"{field}.state.status: ACTIVE/SNOOZED/ARCHIVED required",
            field=f"{field}.state.status",
        )
    _optional_utc(state.get("review_due_at"), field=f"{field}.state.review_due_at")
    _require_bool(state.get("is_due"), field=f"{field}.state.is_due")
    _optional_utc(state.get("snooze_until"), field=f"{field}.state.snooze_until")
    _optional_utc(
        state.get("last_reviewed_at"), field=f"{field}.state.last_reviewed_at"
    )
    _require_str(state.get("last_action"), field=f"{field}.state.last_action")
    _parse_utc(
        state.get("last_recorded_at"), field=f"{field}.state.last_recorded_at"
    )
    _require_non_negative_int(
        state.get("revision_count"), field=f"{field}.state.revision_count"
    )

    _optional_str(
        entry.get("instrument_ticker"), field=f"{field}.instrument_ticker"
    )
    context = _require_mapping(
        entry.get("information_context"), field=f"{field}.information_context"
    )
    # The information population is kept SEPARATE from the theses population
    # and must always be named: sourced information never borrows the label
    # of a user-declared statement.
    _require_str(
        context.get("population"), field=f"{field}.information_context.population"
    )
    clusters = _require_list(
        context.get("clusters"), field=f"{field}.information_context.clusters"
    )
    for cluster_index, cluster in enumerate(clusters):
        _wire_mapping(
            cluster,
            field=f"{field}.information_context.clusters[{cluster_index}]",
        )
    _require_bool(
        entry.get("has_new_information"), field=f"{field}.has_new_information"
    )
    reasons = _require_list(
        entry.get("urgency_reasons"), field=f"{field}.urgency_reasons"
    )
    for reason_index, reason in enumerate(reasons):
        _wire_mapping(reason, field=f"{field}.urgency_reasons[{reason_index}]")


def _checked_due_entry(raw: Any, *, index: int) -> None:
    """One due item of the documented ordering."""
    field = f"due[{index}]"
    entry = _require_mapping(raw, field=field)
    _require_positive_int(entry.get("rank"), field=f"{field}.rank")
    _require_positive_int(entry.get("thesis_id"), field=f"{field}.thesis_id")
    _require_str(entry.get("title"), field=f"{field}.title")
    _parse_utc(entry.get("review_due_at"), field=f"{field}.review_due_at")
    _require_non_negative_int(
        entry.get("overdue_seconds"), field=f"{field}.overdue_seconds"
    )
    _parse_utc(entry.get("last_recorded_at"), field=f"{field}.last_recorded_at")
    _require_bool(
        entry.get("has_new_information"), field=f"{field}.has_new_information"
    )
    reasons = _require_list(
        entry.get("urgency_reasons"), field=f"{field}.urgency_reasons"
    )
    for reason_index, reason in enumerate(reasons):
        _wire_mapping(reason, field=f"{field}.urgency_reasons[{reason_index}]")


def checked_review_queue_content(content: Any) -> Mapping[str, Any]:
    """Fail-closed shape check of ONE persisted review-queue content.

    Validates the shape of every field the worker publishes and returns the
    content UNCHANGED — the relay stays verbatim. Any deviation raises a
    :class:`~vertex_api.snapshot_views.SnapshotContentError` naming its field
    path only; no urgency, ordering, status or count is ever recomputed,
    corrected or defaulted here.
    """
    mapping = _wire_mapping(content, field="content")
    schema_version = _require_str(
        mapping.get("schema_version"), field="schema_version"
    )
    if schema_version != REVIEW_QUEUE_CONTENT_SCHEMA_VERSION:
        raise SnapshotContentError(
            "schema_version: this relay reads "
            f"{REVIEW_QUEUE_CONTENT_SCHEMA_VERSION} only",
            field="schema_version",
        )
    _parse_utc(mapping.get("as_of"), field="as_of")

    populations = _require_mapping(mapping.get("populations"), field="populations")
    _require_str(populations.get("theses"), field="populations.theses")
    _require_str(
        populations.get("information_context"),
        field="populations.information_context",
    )

    ordering = _require_mapping(mapping.get("ordering"), field="ordering")
    _require_str(ordering.get("method"), field="ordering.method")
    keys = _require_list(ordering.get("keys"), field="ordering.keys")
    for key_index, key in enumerate(keys):
        _require_str(key, field=f"ordering.keys[{key_index}]")
    _require_str(ordering.get("note"), field="ordering.note")

    theses = _require_list(mapping.get("theses"), field="theses")
    for index, raw in enumerate(theses):
        _checked_thesis_entry(raw, index=index)
    due = _require_list(mapping.get("due"), field="due")
    for index, raw in enumerate(due):
        _checked_due_entry(raw, index=index)

    coverage = _require_mapping(mapping.get("coverage"), field="coverage")
    for name in _QUEUE_COVERAGE_COUNTS:
        _require_non_negative_int(coverage.get(name), field=f"coverage.{name}")
    # A coverage block contradicting the payload it describes (a truncated
    # queue shown under a full count) is a defect, not a display detail.
    # CONSISTENCY check only — no urgency or ordering is derived here.
    if coverage["theses_total"] != len(theses):
        raise SnapshotContentError(
            "coverage.theses_total: contradicts the published theses",
            field="coverage.theses_total",
        )
    if coverage["due_count"] != len(due):
        raise SnapshotContentError(
            "coverage.due_count: contradicts the published due items",
            field="coverage.due_count",
        )
    return mapping


def build_follow_up_queue_response(
    snapshot: Optional[CurrentSnapshot],
) -> FollowUpQueueResponse:
    """Relay the last review queue snapshot verbatim, or the honest empty state.

    Verbatim, but never unchecked (P1-G): the persisted content is validated
    fail-closed by :func:`checked_review_queue_content` and relayed UNCHANGED.
    A content that does not match its published schema raises a typed
    :class:`~vertex_api.snapshot_views.SnapshotContentError` — it is never
    served as ``state = "ok"``.
    """
    if snapshot is None:
        return FollowUpQueueResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            content=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )
    return FollowUpQueueResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=snapshot.as_of,
        content=dict(checked_review_queue_content(snapshot.content)),
        reason=None,
    )
