"""Thesis storage and pure state projection (page 09 — follow-up queue).

A thesis is a **user-written statement**: what the user believes
(``hypotheses``) and, mandatorily, what would prove it wrong
(``invalidation``). Its review lifecycle (reviewed, snoozed, archived,
reactivated) is recorded as APPEND-ONLY ``thesis_revisions`` rows — SQL
triggers forbid UPDATE/DELETE for every client.

**The current status is never stored.** ACTIVE / SNOOZED / ARCHIVED and the
effective review-due instant are a pure projection of the revision history,
recomputed by :func:`project_thesis_state`. One authority, nothing mutable to
drift, nothing cached to go stale. The projection rules are:

- the first revision is CREATED (anything else is corrupt history and fails
  closed with :class:`ThesisProjectionError`); the thesis starts ACTIVE;
- REVIEWED marks ``last_reviewed_at`` and, unless the thesis is archived,
  clears any pending snooze (reviewing consumes the deferral). It does NOT
  silently move ``review_due_at``: deferring the next review is an explicit
  SNOOZED revision;
- SNOOZED (ignored on an archived thesis) defers the review: while
  ``snooze_until`` is in the future the status is SNOOZED and the effective
  review due is ``snooze_until``; once ``now`` reaches ``snooze_until`` the
  thesis is ACTIVE and DUE again (the expired snooze instant stays the
  effective due);
- NOTE_UPDATED changes nothing in the projection (content history only);
- ARCHIVED parks the thesis: never due, snooze cleared;
- REACTIVATED returns it to ACTIVE with the base ``review_due_at``.

**Idempotency.** Every write carries a caller-supplied ``idempotency_key``,
UNIQUE in ``thesis_revisions``. :func:`create_thesis` inserts the thesis and
its CREATED revision in the caller's SAME transaction (a rollback removes
both), inside a SAVEPOINT around ``INSERT .. ON CONFLICT (idempotency_key)
DO NOTHING``: a replayed create finds the existing CREATED revision by its
key — before inserting for the committed case, or via the conflict for the
concurrent case (the savepoint rollback then discards the extra thesis row)
— and returns the existing thesis with ``created=False``. Replaying
:func:`record_thesis_revision` with the same key writes nothing and returns
``created=False``; reusing a key for a DIFFERENT operation fails closed with
:class:`IdempotencyKeyReuseError`.

Like every repository function, nothing here commits: the caller owns the
transaction boundary. No financial rule lives here — urgency scoring and any
verdict belong to ``vertex_core`` / ``AdviceEngine``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vertex_core.contracts import canonical_json_hash

from vertex_persistence.enums import (
    THESIS_REVISION_ACTIONS,
    ThesisRevisionAction,
    validate_enum_value,
)
from vertex_persistence.errors import (
    IdempotencyKeyReuseError,
    ThesisProjectionError,
    UnknownPortfolioError,
    UnknownThesisError,
    ValidationFailedError,
)
from vertex_persistence.json_codec import to_jsonb_object
from vertex_persistence.models import Portfolio, Thesis, ThesisRevision
from vertex_persistence.repository._validation import (
    require_aware_utc,
    require_non_empty_str,
    require_now,
    require_optional_str,
    require_positive_int,
)

__all__ = [
    "ThesisStatus",
    "ThesisRecord",
    "ThesisRevisionRecord",
    "ThesisState",
    "ProjectedThesis",
    "CreatedThesis",
    "RecordedRevision",
    "create_thesis",
    "record_thesis_revision",
    "project_thesis_state",
    "list_theses",
    "list_revisions",
    "review_queue_due",
]

_DEFAULT_AUTHOR = "local-user"


@unique
class ThesisStatus(str, Enum):
    """Projected — never stored — status of a thesis."""

    ACTIVE = "ACTIVE"
    SNOOZED = "SNOOZED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class ThesisRecord:
    """Immutable view of one stored thesis (statement only, no status)."""

    id: int
    portfolio_id: Optional[int]
    instrument: Optional[dict[str, Any]]
    title: str
    hypotheses: str
    invalidation: str
    horizon: Optional[str]
    review_due_at: Optional[datetime]
    created_at: datetime


@dataclass(frozen=True)
class ThesisRevisionRecord:
    """Immutable view of one append-only revision row."""

    id: int
    thesis_id: int
    action: str
    note: Optional[str]
    snapshot_ref: Optional[str]
    content_hash: str
    idempotency_key: str
    author: str
    recorded_at: datetime
    snooze_until: Optional[datetime]


@dataclass(frozen=True)
class ThesisState:
    """Pure projection of a revision history at one instant ``now``.

    ``review_due_at`` is the EFFECTIVE due instant (an unconsumed snooze
    overrides the thesis's base ``review_due_at``); ``None`` means no review
    is scheduled. ``is_due`` is ``True`` only for a non-archived thesis whose
    effective due instant has been reached.
    """

    status: str
    review_due_at: Optional[datetime]
    is_due: bool
    snooze_until: Optional[datetime]
    last_reviewed_at: Optional[datetime]
    last_action: str
    last_recorded_at: datetime
    revision_count: int


@dataclass(frozen=True)
class ProjectedThesis:
    """One thesis with its projected state."""

    thesis: ThesisRecord
    state: ThesisState


@dataclass(frozen=True)
class CreatedThesis:
    """Result of :func:`create_thesis`; ``created=False`` marks a replay."""

    thesis_id: int
    revision_id: int
    created: bool


@dataclass(frozen=True)
class RecordedRevision:
    """Result of :func:`record_thesis_revision`; ``created=False`` marks a replay."""

    revision_id: int
    created: bool


def _thesis_record(row: Thesis) -> ThesisRecord:
    return ThesisRecord(
        id=row.id,
        portfolio_id=row.portfolio_id,
        instrument=dict(row.instrument) if row.instrument is not None else None,
        title=row.title,
        hypotheses=row.hypotheses,
        invalidation=row.invalidation,
        horizon=row.horizon,
        review_due_at=row.review_due_at,
        created_at=row.created_at,
    )


def _revision_record(row: ThesisRevision) -> ThesisRevisionRecord:
    return ThesisRevisionRecord(
        id=row.id,
        thesis_id=row.thesis_id,
        action=row.action,
        note=row.note,
        snapshot_ref=row.snapshot_ref,
        content_hash=row.content_hash,
        idempotency_key=row.idempotency_key,
        author=row.author,
        recorded_at=row.recorded_at,
        snooze_until=row.snooze_until,
    )


def _find_revision_by_key(session: Session, idempotency_key: str) -> Optional[ThesisRevision]:
    return session.execute(
        select(ThesisRevision).where(ThesisRevision.idempotency_key == idempotency_key)
    ).scalar_one_or_none()


def _require_thesis(session: Session, thesis_id: int) -> Thesis:
    thesis_id = require_positive_int("thesis_id", thesis_id)
    thesis = session.get(Thesis, thesis_id)
    if thesis is None:
        raise UnknownThesisError(f"thesis {thesis_id} does not exist")
    return thesis


def _content_hash(label: str, content: dict[str, Any]) -> str:
    """Canonical hash of the fail-closed JSONB encoding of ``content``.

    Same canonicalization as observation payloads: Decimal -> exact string,
    aware datetime -> UTC ISO, naive/NaN rejected. The hash makes every
    revision's content tamper-evident and replay-comparable.
    """
    return canonical_json_hash(to_jsonb_object(label, content))


def create_thesis(
    session: Session,
    *,
    title: str,
    hypotheses: str,
    invalidation: str,
    idempotency_key: str,
    now: datetime,
    portfolio_id: Optional[int] = None,
    instrument: Any = None,
    horizon: Optional[str] = None,
    review_due_at: Optional[datetime] = None,
    note: Optional[str] = None,
    author: str = _DEFAULT_AUTHOR,
) -> CreatedThesis:
    """Insert one thesis AND its CREATED revision in the same transaction.

    A thesis without a non-blank ``invalidation`` is refused (here and by
    CHECK). Idempotent by ``idempotency_key`` (see module docstring):
    replaying returns the existing thesis with ``created=False`` and writes
    nothing; reusing the key for a non-CREATED revision fails closed. No
    commit happens here — a caller rollback removes thesis and revision
    together (they can never exist separately).
    """
    title = require_non_empty_str("title", title)
    hypotheses = require_non_empty_str("hypotheses", hypotheses)
    invalidation = require_non_empty_str("invalidation", invalidation)
    idempotency_key = require_non_empty_str("idempotency_key", idempotency_key)
    now = require_now(now)
    horizon = require_optional_str("horizon", horizon)
    note = require_optional_str("note", note)
    author = require_non_empty_str("author", author)
    if review_due_at is not None:
        review_due_at = require_aware_utc("review_due_at", review_due_at)
    encoded_instrument = (
        to_jsonb_object("instrument", instrument) if instrument is not None else None
    )
    if portfolio_id is not None:
        portfolio_id = require_positive_int("portfolio_id", portfolio_id)
        if session.get(Portfolio, portfolio_id) is None:
            raise UnknownPortfolioError(f"portfolio {portfolio_id} does not exist")

    existing = _find_revision_by_key(session, idempotency_key)
    if existing is not None:
        if existing.action != ThesisRevisionAction.CREATED.value:
            raise IdempotencyKeyReuseError(
                f"idempotency key already names a {existing.action} revision, not a create"
            )
        return CreatedThesis(thesis_id=existing.thesis_id, revision_id=existing.id, created=False)

    content_hash = _content_hash(
        "thesis",
        {
            "action": ThesisRevisionAction.CREATED.value,
            "portfolio_id": portfolio_id,
            "instrument": encoded_instrument,
            "title": title,
            "hypotheses": hypotheses,
            "invalidation": invalidation,
            "horizon": horizon,
            "review_due_at": review_due_at,
            "note": note,
            "author": author,
        },
    )

    # SAVEPOINT: if a concurrent replay of the same key commits first, the
    # ON CONFLICT below returns no row and the rollback discards the extra
    # thesis row inserted here — the caller's outer transaction survives.
    nested = session.begin_nested()
    thesis = Thesis(
        portfolio_id=portfolio_id,
        instrument=encoded_instrument,
        title=title,
        hypotheses=hypotheses,
        invalidation=invalidation,
        horizon=horizon,
        review_due_at=review_due_at,
        created_at=now,
    )
    session.add(thesis)
    session.flush()
    revision_id = session.execute(
        pg_insert(ThesisRevision)
        .values(
            thesis_id=thesis.id,
            action=ThesisRevisionAction.CREATED.value,
            note=note,
            snapshot_ref=None,
            content_hash=content_hash,
            idempotency_key=idempotency_key,
            author=author,
            recorded_at=now,
            snooze_until=None,
        )
        .on_conflict_do_nothing(index_elements=[ThesisRevision.idempotency_key])
        # Explicit RETURNING makes idempotence observable (rowcount is
        # unreliable with ON CONFLICT DO NOTHING).
        .returning(ThesisRevision.id)
    ).scalar_one_or_none()
    if revision_id is None:
        nested.rollback()
        winner = _find_revision_by_key(session, idempotency_key)
        if winner is None or winner.action != ThesisRevisionAction.CREATED.value:
            raise IdempotencyKeyReuseError(
                "idempotency key conflicted with a concurrent non-create revision"
            )
        return CreatedThesis(thesis_id=winner.thesis_id, revision_id=winner.id, created=False)
    nested.commit()
    return CreatedThesis(thesis_id=thesis.id, revision_id=revision_id, created=True)


def record_thesis_revision(
    session: Session,
    *,
    thesis_id: int,
    action: str,
    idempotency_key: str,
    recorded_at: datetime,
    note: Optional[str] = None,
    snapshot_ref: Optional[str] = None,
    snooze_until: Optional[datetime] = None,
    author: str = _DEFAULT_AUTHOR,
) -> RecordedRevision:
    """Append one review-lifecycle revision; idempotent by ``idempotency_key``.

    CREATED is reserved to :func:`create_thesis`. ``snooze_until`` is
    required exactly when ``action`` is SNOOZED (also enforced by CHECK).
    Ten replays with the same key produce one row: the first call returns
    ``created=True``, every replay returns the SAME revision id with
    ``created=False``. A key reused for a different thesis or action fails
    closed with :class:`IdempotencyKeyReuseError`. No commit happens here.
    """
    thesis = _require_thesis(session, thesis_id)
    action = validate_enum_value("action", action, THESIS_REVISION_ACTIONS)
    if action == ThesisRevisionAction.CREATED.value:
        raise ValidationFailedError(
            "action: CREATED is reserved to create_thesis (thesis and first "
            "revision are inserted together)"
        )
    idempotency_key = require_non_empty_str("idempotency_key", idempotency_key)
    recorded_at = require_aware_utc("recorded_at", recorded_at)
    note = require_optional_str("note", note)
    snapshot_ref = require_optional_str("snapshot_ref", snapshot_ref)
    author = require_non_empty_str("author", author)
    if action == ThesisRevisionAction.SNOOZED.value:
        if snooze_until is None:
            raise ValidationFailedError("snooze_until: required for a SNOOZED revision")
        snooze_until = require_aware_utc("snooze_until", snooze_until)
    elif snooze_until is not None:
        raise ValidationFailedError(
            f"snooze_until: only a SNOOZED revision carries one, not {action}"
        )

    content_hash = _content_hash(
        "revision",
        {
            "action": action,
            "thesis_id": thesis.id,
            "note": note,
            "snapshot_ref": snapshot_ref,
            "snooze_until": snooze_until,
            "author": author,
        },
    )
    revision_id = session.execute(
        pg_insert(ThesisRevision)
        .values(
            thesis_id=thesis.id,
            action=action,
            note=note,
            snapshot_ref=snapshot_ref,
            content_hash=content_hash,
            idempotency_key=idempotency_key,
            author=author,
            recorded_at=recorded_at,
            snooze_until=snooze_until,
        )
        .on_conflict_do_nothing(index_elements=[ThesisRevision.idempotency_key])
        .returning(ThesisRevision.id)
    ).scalar_one_or_none()
    if revision_id is not None:
        return RecordedRevision(revision_id=revision_id, created=True)

    existing = _find_revision_by_key(session, idempotency_key)
    if existing is None:
        raise IdempotencyKeyReuseError(
            "idempotency key conflicted but the existing revision is not visible"
        )
    if existing.thesis_id != thesis.id or existing.action != action:
        raise IdempotencyKeyReuseError(
            f"idempotency key already names a {existing.action} revision of "
            f"thesis {existing.thesis_id}, not a {action} of thesis {thesis.id}"
        )
    return RecordedRevision(revision_id=existing.id, created=False)


def project_thesis_state(
    revisions: Sequence[ThesisRevisionRecord],
    *,
    review_due_at: Optional[datetime],
    now: datetime,
) -> ThesisState:
    """Pure fold of a revision history into the thesis state at ``now``.

    Deterministic, no I/O, no hidden clock: the ONLY authority for thesis
    status and effective review due (rules in the module docstring).
    Revisions are ordered by ``(recorded_at, id)`` defensively; corrupt
    history (empty, not starting with CREATED, duplicate CREATED, SNOOZED
    without ``snooze_until``, unknown action) fails closed with
    :class:`ThesisProjectionError`.
    """
    now = require_now(now)
    if review_due_at is not None:
        review_due_at = require_aware_utc("review_due_at", review_due_at)
    if not revisions:
        raise ThesisProjectionError("empty revision history cannot be projected")

    ordered = sorted(revisions, key=lambda rev: (rev.recorded_at, rev.id))
    if ordered[0].action != ThesisRevisionAction.CREATED.value:
        raise ThesisProjectionError(
            f"history must start with CREATED, got {ordered[0].action}"
        )

    status = ThesisStatus.ACTIVE
    snooze_until: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    for revision in ordered[1:]:
        action = revision.action
        if action not in THESIS_REVISION_ACTIONS:
            raise ThesisProjectionError(f"unknown revision action {action!r}")
        if action == ThesisRevisionAction.CREATED.value:
            raise ThesisProjectionError("duplicate CREATED revision in history")
        if action == ThesisRevisionAction.REVIEWED.value:
            last_reviewed_at = revision.recorded_at
            if status is not ThesisStatus.ARCHIVED:
                status = ThesisStatus.ACTIVE
                snooze_until = None
        elif action == ThesisRevisionAction.SNOOZED.value:
            if revision.snooze_until is None:
                raise ThesisProjectionError("SNOOZED revision without snooze_until")
            if status is not ThesisStatus.ARCHIVED:
                status = ThesisStatus.SNOOZED
                snooze_until = revision.snooze_until
        elif action == ThesisRevisionAction.NOTE_UPDATED.value:
            pass  # content history only; no lifecycle effect
        elif action == ThesisRevisionAction.ARCHIVED.value:
            status = ThesisStatus.ARCHIVED
            snooze_until = None
        elif action == ThesisRevisionAction.REACTIVATED.value:
            status = ThesisStatus.ACTIVE
            snooze_until = None

    # Resolve the now-dependent part: an expired snooze makes the thesis
    # ACTIVE and DUE again (the snooze instant IS the effective due).
    if status is ThesisStatus.SNOOZED:
        assert snooze_until is not None  # guaranteed by the fold above
        effective_due: Optional[datetime] = snooze_until
        if snooze_until <= now:
            status = ThesisStatus.ACTIVE
    elif status is ThesisStatus.ACTIVE:
        effective_due = review_due_at
    else:  # ARCHIVED: never due
        effective_due = None

    is_due = (
        status is not ThesisStatus.ARCHIVED
        and effective_due is not None
        and effective_due <= now
    )
    last = ordered[-1]
    return ThesisState(
        status=status.value,
        review_due_at=effective_due,
        is_due=is_due,
        snooze_until=snooze_until,
        last_reviewed_at=last_reviewed_at,
        last_action=last.action,
        last_recorded_at=last.recorded_at,
        revision_count=len(ordered),
    )


def list_revisions(session: Session, thesis_id: int) -> tuple[ThesisRevisionRecord, ...]:
    """All revisions of one thesis, oldest first (recorded_at, then id)."""
    thesis = _require_thesis(session, thesis_id)
    rows = (
        session.execute(
            select(ThesisRevision)
            .where(ThesisRevision.thesis_id == thesis.id)
            .order_by(ThesisRevision.recorded_at, ThesisRevision.id)
        )
        .scalars()
        .all()
    )
    return tuple(_revision_record(row) for row in rows)


def _project_all(session: Session, *, now: datetime) -> list[ProjectedThesis]:
    now = require_now(now)
    theses = session.execute(select(Thesis).order_by(Thesis.id)).scalars().all()
    revisions = (
        session.execute(
            select(ThesisRevision).order_by(ThesisRevision.recorded_at, ThesisRevision.id)
        )
        .scalars()
        .all()
    )
    by_thesis: dict[int, list[ThesisRevisionRecord]] = {}
    for row in revisions:
        by_thesis.setdefault(row.thesis_id, []).append(_revision_record(row))
    return [
        ProjectedThesis(
            thesis=_thesis_record(row),
            state=project_thesis_state(
                by_thesis.get(row.id, ()), review_due_at=row.review_due_at, now=now
            ),
        )
        for row in theses
    ]


def list_theses(session: Session, *, now: datetime) -> tuple[ProjectedThesis, ...]:
    """All theses with their projected state at ``now``, oldest first.

    The state is recomputed by :func:`project_thesis_state` on every call —
    it is never read from a stored column, so it cannot go stale.
    """
    return tuple(_project_all(session, now=now))


def review_queue_due(session: Session, *, now: datetime) -> tuple[ProjectedThesis, ...]:
    """Theses whose review is due at ``now``, most overdue first.

    Due means: not archived, and the EFFECTIVE review-due instant (base
    ``review_due_at``, or the snooze instant of an expired snooze) has been
    reached. The filter runs over :func:`project_thesis_state` in Python on
    purpose: duplicating the projection in SQL would create a second,
    concurrent authority for the same truth.
    """
    due = [entry for entry in _project_all(session, now=now) if entry.state.is_due]
    due.sort(key=lambda entry: (entry.state.review_due_at, entry.thesis.id))
    return tuple(due)
