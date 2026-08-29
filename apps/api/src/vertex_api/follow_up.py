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
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Optional, Protocol

from fastapi import FastAPI
from pydantic import StringConstraints, model_validator
from sqlalchemy import text

from vertex_api.auth.db import open_db_session
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


def build_follow_up_queue_response(
    snapshot: Optional[CurrentSnapshot],
) -> FollowUpQueueResponse:
    """Relay the last review queue snapshot verbatim, or the honest empty state."""
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
        content=dict(snapshot.content),
        reason=None,
    )
