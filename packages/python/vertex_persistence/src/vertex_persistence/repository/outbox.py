"""Transactional outbox operations (ADR-006, at-least-once semantics).

Enqueue happens inside the caller's business transaction, so a rollback drops
the business write and its message together. Workers claim rows with
``SELECT .. FOR UPDATE SKIP LOCKED``, hold a lease, then ack or fail. The
clock is always injected (``now``) — no hidden system time — which keeps
lease and backoff behavior deterministic under test.

``last_error`` stores a short technical diagnostic only. Callers must never
put payload fragments, secrets, personal data or account-like data in it; the
value is truncated defensively.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, Sequence

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from vertex_persistence.backoff import DEFAULT_MAX_ATTEMPTS, compute_backoff_seconds
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.errors import OutboxStateError, ValidationFailedError
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

# Statuses a worker may claim from. IN_PROGRESS rows are recovered only by
# reap_expired_leases, so a crashed worker's rows are re-offered explicitly.
_CLAIMABLE_STATUSES = (OutboxStatus.PENDING.value, OutboxStatus.FAILED.value)


@dataclass(frozen=True)
class ClaimedOutboxMessage:
    """Immutable view of one claimed message handed to a worker."""

    id: int
    topic: str
    payload: dict[str, Any]
    attempts: int
    lease_until: datetime


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
    ``lease_until = now + lease_seconds``. The claim must be committed by the
    caller before processing starts.
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
        row.status = OutboxStatus.IN_PROGRESS.value
        row.lease_until = lease_until
        row.updated_at = now
        claimed.append(
            ClaimedOutboxMessage(
                id=row.id,
                topic=row.topic,
                payload=dict(row.payload),
                attempts=row.attempts,
                lease_until=lease_until,
            )
        )
    session.flush()
    return claimed


def _load_in_progress(session: Session, message_id: int) -> OutboxMessage:
    row = session.get(OutboxMessage, message_id, with_for_update=True)
    if row is None:
        raise OutboxStateError(f"outbox message {message_id} does not exist")
    if row.status != OutboxStatus.IN_PROGRESS.value:
        raise OutboxStateError(
            f"outbox message {message_id} is {row.status}, expected IN_PROGRESS"
        )
    return row


def ack_outbox(session: Session, message_id: int, *, now: datetime) -> None:
    """Mark one IN_PROGRESS message DONE (successful handling)."""
    now = require_now(now)
    message_id = require_positive_int("message_id", message_id)
    row = _load_in_progress(session, message_id)
    row.status = OutboxStatus.DONE.value
    row.lease_until = None
    row.updated_at = now
    session.flush()


def fail_outbox(
    session: Session,
    message_id: int,
    error: str,
    *,
    now: datetime,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    """Record one failed handling attempt; return the resulting status.

    Increments ``attempts``. Below ``max_attempts`` the message becomes FAILED
    with ``lease_until = now + exponential backoff`` (its retry-not-before
    instant); at ``max_attempts`` it becomes DEAD and is never claimed again.
    ``error`` must be a short technical diagnostic — never payload content,
    secrets or account-like data — and is truncated to a bounded length.
    """
    now = require_now(now)
    message_id = require_positive_int("message_id", message_id)
    max_attempts = require_positive_int("max_attempts", max_attempts)
    error = require_non_empty_str("error", error)

    row = _load_in_progress(session, message_id)
    row.attempts = row.attempts + 1
    row.last_error = error[:_LAST_ERROR_MAX_CHARS]
    row.updated_at = now
    if row.attempts >= max_attempts:
        row.status = OutboxStatus.DEAD.value
        row.lease_until = None
    else:
        row.status = OutboxStatus.FAILED.value
        row.lease_until = now + timedelta(seconds=compute_backoff_seconds(row.attempts))
    session.flush()
    return row.status


def reap_expired_leases(session: Session, *, now: datetime) -> int:
    """Re-offer IN_PROGRESS messages whose lease expired; return how many.

    An expired lease means the claiming worker neither acked nor failed the
    message (crash, kill, partition). The row returns to PENDING with no
    lease. ``attempts`` is deliberately left unchanged: only an explicit
    ``fail_outbox`` counts an attempt, and workers must call it on handling
    errors so that poisoned messages still reach DEAD.
    """
    now = require_now(now)
    result = session.execute(
        update(OutboxMessage)
        .where(
            OutboxMessage.status == OutboxStatus.IN_PROGRESS.value,
            OutboxMessage.lease_until.is_not(None),
            OutboxMessage.lease_until <= now,
        )
        .values(status=OutboxStatus.PENDING.value, lease_until=None, updated_at=now)
    )
    return int(result.rowcount)
