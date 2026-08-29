"""Transactional outbox operations (ADR-006, at-least-once semantics).

Enqueue happens inside the caller's business transaction, so a rollback drops
the business write and its message together. Workers claim rows with
``SELECT .. FOR UPDATE SKIP LOCKED``, hold a lease, then ack or fail. The
clock is always injected (``now``) — no hidden system time — which keeps
lease and backoff behavior deterministic under test.

Lease ownership: every claim stamps the row with an opaque, per-claim
``lease_token`` returned in :class:`ClaimedOutboxMessage`. ``ack_outbox`` and
``fail_outbox`` require that token, so a worker whose lease expired and was
reaped (or whose row was re-claimed by another worker) gets a typed
:class:`~vertex_persistence.errors.OutboxLeaseError` instead of silently
overwriting someone else's state. ``reap_expired_leases`` records the lost
attempt itself (FAILED with backoff, DEAD at ``max_attempts``), so an
attempt is never lost and a poisoned handler that always overruns its lease
still reaches DEAD (ADR-006: record attempt, lease and result).

``last_error`` stores a short technical diagnostic only. Callers must never
put payload fragments, secrets, personal data or account-like data in it; the
value is truncated defensively.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vertex_persistence.backoff import DEFAULT_MAX_ATTEMPTS, compute_backoff_seconds
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.errors import OutboxLeaseError, OutboxStateError, ValidationFailedError
from vertex_persistence.json_codec import to_jsonb_object
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository._validation import (
    require_non_empty_str,
    require_now,
    require_positive_int,
)

__all__ = [
    "ClaimedOutboxMessage",
    "enqueue_outbox",
    "claim_outbox_batch",
    "ack_outbox",
    "fail_outbox",
    "reap_expired_leases",
]

_LAST_ERROR_MAX_CHARS = 500

# Diagnostic recorded by the reaper. Technical only — never payload content.
_LEASE_EXPIRED_ERROR = (
    "lease expired without ack or fail (worker crash, kill, partition or "
    "handler overrun); attempt counted by reap_expired_leases"
)

# Statuses a worker may claim from. IN_PROGRESS rows are recovered only by
# reap_expired_leases, so a crashed worker's rows are re-offered explicitly.
_CLAIMABLE_STATUSES = (OutboxStatus.PENDING.value, OutboxStatus.FAILED.value)


@dataclass(frozen=True)
class ClaimedOutboxMessage:
    """Immutable view of one claimed message handed to a worker.

    ``lease_token`` is the proof of ownership for this claim: ``ack_outbox``
    and ``fail_outbox`` refuse any call that does not present it.
    """

    id: int
    topic: str
    payload: dict[str, Any]
    attempts: int
    lease_until: datetime
    lease_token: str


def enqueue_outbox(session: Session, topic: str, payload: Any) -> int:
    """Enqueue one message inside the caller's transaction; return its id.

    No commit happens here: the message becomes visible if and only if the
    surrounding business transaction commits (outbox atomicity).
    """
    topic = require_non_empty_str("topic", topic)
    encoded = to_jsonb_object("payload", payload)
    row = OutboxMessage(topic=topic, payload=encoded, status=OutboxStatus.PENDING.value)
    session.add(row)
    session.flush()
    return row.id


def claim_outbox_batch(
    session: Session,
    topics: Sequence[str],
    limit: int,
    lease_seconds: int,
    *,
    now: datetime,
) -> list[ClaimedOutboxMessage]:
    """Claim up to ``limit`` due messages on ``topics`` with a lease.

    Uses ``FOR UPDATE SKIP LOCKED`` so concurrent claimers get disjoint
    batches. Claims PENDING messages and FAILED messages whose retry-not-before
    instant (``lease_until``) has passed; claimed rows move to IN_PROGRESS with
    ``lease_until = now + lease_seconds`` and a fresh, unique ``lease_token``
    (an opaque nonce, not an injected clock value: it carries no time or
    ordering semantics). The claim must be committed by the caller before
    processing starts.
    """
    if not isinstance(topics, Sequence) or isinstance(topics, (str, bytes)):
        raise ValidationFailedError("topics: expected a sequence of topic strings")
    topic_list = [require_non_empty_str("topics[]", topic) for topic in topics]
    if not topic_list:
        raise ValidationFailedError("topics: at least one topic is required")
    limit = require_positive_int("limit", limit)
    lease_seconds = require_positive_int("lease_seconds", lease_seconds)
    now = require_now(now)

    rows = (
        session.execute(
            select(OutboxMessage)
            .where(
                OutboxMessage.topic.in_(topic_list),
                OutboxMessage.status.in_(_CLAIMABLE_STATUSES),
                or_(OutboxMessage.lease_until.is_(None), OutboxMessage.lease_until <= now),
            )
            .order_by(OutboxMessage.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .all()
    )
    lease_until = now + timedelta(seconds=lease_seconds)
    claimed: list[ClaimedOutboxMessage] = []
    for row in rows:
        lease_token = uuid.uuid4().hex
        row.status = OutboxStatus.IN_PROGRESS.value
        row.lease_until = lease_until
        row.lease_token = lease_token
        row.updated_at = now
        claimed.append(
            ClaimedOutboxMessage(
                id=row.id,
                topic=row.topic,
                payload=dict(row.payload),
                attempts=row.attempts,
                lease_until=lease_until,
                lease_token=lease_token,
            )
        )
    session.flush()
    return claimed


def _load_owned_in_progress(
    session: Session, message_id: int, lease_token: str
) -> OutboxMessage:
    """Load one message the caller still owns, or raise a typed error.

    Ownership is checked before status so a worker whose lease was reaped or
    re-claimed gets :class:`OutboxLeaseError` (its attempt is already
    recorded; it must discard its result), never a misleading status message.
    """
    row = session.get(OutboxMessage, message_id, with_for_update=True)
    if row is None:
        raise OutboxStateError(f"outbox message {message_id} does not exist")
    if row.lease_token is None or row.lease_token != lease_token:
        raise OutboxLeaseError(
            f"outbox message {message_id} is not held under this lease token: "
            "the lease expired and was reaped (attempt already counted), the "
            "message was re-claimed by another worker, or it was never "
            "claimed; discard the result and do not retry"
        )
    if row.status != OutboxStatus.IN_PROGRESS.value:
        # Defensive: a matching token outside IN_PROGRESS is an impossible
        # state (tokens are cleared on ack, fail and reap) — fail closed.
        raise OutboxStateError(
            f"outbox message {message_id} is {row.status}, expected IN_PROGRESS"
        )
    return row


def _record_failed_attempt(
    row: OutboxMessage, error: str, now: datetime, max_attempts: int
) -> None:
    """Count one failed attempt on ``row`` (shared by fail_outbox and the reaper)."""
    row.attempts = row.attempts + 1
    row.last_error = error[:_LAST_ERROR_MAX_CHARS]
    row.updated_at = now
    row.lease_token = None
    if row.attempts >= max_attempts:
        row.status = OutboxStatus.DEAD.value
        row.lease_until = None
    else:
        row.status = OutboxStatus.FAILED.value
        row.lease_until = now + timedelta(seconds=compute_backoff_seconds(row.attempts))


def ack_outbox(
    session: Session, message_id: int, *, lease_token: str, now: datetime
) -> None:
    """Mark one owned IN_PROGRESS message DONE (successful handling).

    ``lease_token`` must be the token returned by the claim; a stale worker
    (reaped or re-claimed row) gets :class:`OutboxLeaseError` and must
    discard its result.
    """
    now = require_now(now)
    message_id = require_positive_int("message_id", message_id)
    lease_token = require_non_empty_str("lease_token", lease_token)
    row = _load_owned_in_progress(session, message_id, lease_token)
    row.status = OutboxStatus.DONE.value
    row.lease_until = None
    row.lease_token = None
    row.updated_at = now
    session.flush()


def fail_outbox(
    session: Session,
    message_id: int,
    error: str,
    *,
    lease_token: str,
    now: datetime,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    """Record one failed handling attempt; return the resulting status.

    Requires the claim's ``lease_token`` (see :func:`ack_outbox`). Increments
    ``attempts``. Below ``max_attempts`` the message becomes FAILED with
    ``lease_until = now + exponential backoff`` (its retry-not-before
    instant); at ``max_attempts`` it becomes DEAD and is never claimed again.
    ``error`` must be a short technical diagnostic — never payload content,
    secrets or account-like data — and is truncated to a bounded length.
    """
    now = require_now(now)
    message_id = require_positive_int("message_id", message_id)
    lease_token = require_non_empty_str("lease_token", lease_token)
    max_attempts = require_positive_int("max_attempts", max_attempts)
    error = require_non_empty_str("error", error)

    row = _load_owned_in_progress(session, message_id, lease_token)
    _record_failed_attempt(row, error, now, max_attempts)
    session.flush()
    return row.status


def reap_expired_leases(
    session: Session, *, now: datetime, max_attempts: int = DEFAULT_MAX_ATTEMPTS
) -> int:
    """Recover IN_PROGRESS messages whose lease expired; return how many.

    An expired lease means the claiming worker neither acked nor failed the
    message in time (crash, kill, partition, handler overrun). The reaper
    records the lost attempt itself: ``attempts`` is incremented, the lease
    token is invalidated, and the row becomes FAILED with backoff — or DEAD
    at ``max_attempts`` — exactly as an explicit ``fail_outbox`` would do.
    This keeps ADR-006 honest (attempt, lease and result are recorded) and
    guarantees a poisoned message reaches DEAD even when its worker never
    reports. A worker that outlives its lease gets ``OutboxLeaseError`` from
    its late ack/fail and must discard its result.

    Rows locked by a concurrent ack/fail are skipped (``SKIP LOCKED``): the
    owner's explicit result wins over the reaper.
    """
    now = require_now(now)
    max_attempts = require_positive_int("max_attempts", max_attempts)
    rows = (
        session.execute(
            select(OutboxMessage)
            .where(
                OutboxMessage.status == OutboxStatus.IN_PROGRESS.value,
                OutboxMessage.lease_until.is_not(None),
                OutboxMessage.lease_until <= now,
            )
            .order_by(OutboxMessage.id)
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .all()
    )
    for row in rows:
        _record_failed_attempt(row, _LEASE_EXPIRED_ERROR, now, max_attempts)
    session.flush()
    return len(rows)
