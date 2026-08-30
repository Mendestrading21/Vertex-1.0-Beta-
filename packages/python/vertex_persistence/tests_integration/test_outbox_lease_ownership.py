"""Outbox lease ownership: reaped attempts are counted, stale leases are inert.

Reproducers for two confirmed P1 defects:

1. A handler that overran its lease and then failed never got its attempt
   counted: ``reap_expired_leases`` silently returned the row to PENDING and
   the late ``fail_outbox`` raised, so a poisoned message looped
   claim -> reap -> PENDING forever and never reached DEAD, contradicting
   ADR-006 ("record attempt, lease and result").
2. After a reap and a re-claim by worker B, stale worker A could still ack or
   fail the row B was processing, corrupting status/attempts/last_error and
   discarding B's legitimate result.

Contract under test: every claim carries a per-claim ``lease_token``; ack and
fail require the matching token; the reaper itself records the lost attempt
(FAILED with backoff, DEAD at max attempts), so no attempt is ever lost and
no stale worker can touch a row it no longer owns.

Clocks are injected synthetic instants — no sleeping, no real time.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from vertex_persistence.backoff import DEFAULT_MAX_ATTEMPTS, compute_backoff_seconds
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.errors import OutboxLeaseError
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository import (
    ack_outbox,
    claim_outbox_batch,
    enqueue_outbox,
    fail_outbox,
    reap_expired_leases,
)

UTC = UTC
T0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)
TOPIC = "synthetic.test.topic"


def test_reap_records_the_lost_attempt(db_session: Session) -> None:
    """A reaped lease is a recorded failed attempt, never a silent PENDING."""
    message_id = enqueue_outbox(db_session, TOPIC, {"seq": 0})
    db_session.commit()
    (claimed,) = claim_outbox_batch(db_session, [TOPIC], limit=1, lease_seconds=10, now=T0)
    db_session.commit()

    reap_now = T0 + timedelta(seconds=11)
    assert reap_expired_leases(db_session, now=reap_now) == 1
    db_session.commit()

    row = db_session.get(OutboxMessage, message_id)
    assert row is not None
    assert row.status == OutboxStatus.FAILED.value
    assert row.attempts == 1  # the overrun IS the attempt — counted by the reaper
    assert row.lease_until == reap_now + timedelta(seconds=compute_backoff_seconds(1))
    assert row.lease_token is None
    assert row.last_error is not None and "lease expired" in row.last_error
    assert claimed.id == message_id


def test_poisoned_message_reaches_dead_through_reaps_alone(db_session: Session) -> None:
    """A handler that always overruns and never acks/fails still ends DEAD."""
    message_id = enqueue_outbox(db_session, TOPIC, {"seq": 0})
    db_session.commit()
    now = T0
    for attempt in range(1, DEFAULT_MAX_ATTEMPTS + 1):
        claimed = claim_outbox_batch(db_session, [TOPIC], limit=1, lease_seconds=10, now=now)
        assert [message.id for message in claimed] == [message_id], f"attempt {attempt}"
        db_session.commit()
        now = now + timedelta(seconds=11)  # lease overrun, worker never reports
        assert reap_expired_leases(db_session, now=now) == 1
        db_session.commit()
        now = now + timedelta(hours=2)  # move past any backoff before the next claim
    row = db_session.get(OutboxMessage, message_id)
    assert row is not None
    assert row.status == OutboxStatus.DEAD.value
    assert row.attempts == DEFAULT_MAX_ATTEMPTS
    assert row.lease_until is None
    assert row.lease_token is None
    # DEAD is final: the claim -> reap -> claim loop is provably finite.
    assert claim_outbox_batch(db_session, [TOPIC], 1, 10, now=now) == []


def test_late_fail_after_reap_is_rejected_without_double_count(db_session: Session) -> None:
    """The overrunning worker's late fail is refused; its attempt was already counted."""
    message_id = enqueue_outbox(db_session, TOPIC, {"seq": 0})
    db_session.commit()
    (claimed,) = claim_outbox_batch(db_session, [TOPIC], limit=1, lease_seconds=60, now=T0)
    db_session.commit()

    assert reap_expired_leases(db_session, now=T0 + timedelta(seconds=61)) == 1
    db_session.commit()

    with pytest.raises(OutboxLeaseError):
        fail_outbox(
            db_session,
            message_id,
            RuntimeError("synthetic late handler failure"),
            code="HANDLER_ERROR",
            lease_token=claimed.lease_token,
            now=T0 + timedelta(seconds=62),
        )
    db_session.rollback()

    row = db_session.get(OutboxMessage, message_id)
    assert row is not None
    assert row.attempts == 1  # counted once by the reaper, not twice
    assert row.status == OutboxStatus.FAILED.value


def test_stale_worker_cannot_touch_a_reclaimed_message(migrated_engine: Engine) -> None:
    """After reap + re-claim by worker B, worker A's stale ack/fail are inert."""
    with Session(migrated_engine) as setup:
        message_id = enqueue_outbox(setup, TOPIC, {"seq": 0})
        setup.commit()

    with Session(migrated_engine) as worker_a, Session(migrated_engine) as worker_b:
        (claim_a,) = claim_outbox_batch(worker_a, [TOPIC], limit=1, lease_seconds=60, now=T0)
        worker_a.commit()

        # Worker A stalls; its lease expires and the reaper counts the attempt.
        reap_now = T0 + timedelta(seconds=61)
        assert reap_expired_leases(worker_b, now=reap_now) == 1
        worker_b.commit()

        # Worker B re-claims once the retry-not-before instant has passed.
        b_now = reap_now + timedelta(seconds=compute_backoff_seconds(1) + 1)
        (claim_b,) = claim_outbox_batch(worker_b, [TOPIC], limit=1, lease_seconds=60, now=b_now)
        worker_b.commit()
        assert claim_b.id == message_id
        assert claim_b.lease_token != claim_a.lease_token  # a lease is a distinct grant

        # Stale worker A wakes up: neither its ack nor its fail may land on B's row.
        with pytest.raises(OutboxLeaseError):
            ack_outbox(worker_a, message_id, lease_token=claim_a.lease_token, now=b_now)
        worker_a.rollback()
        with pytest.raises(OutboxLeaseError):
            fail_outbox(
                worker_a,
                message_id,
                RuntimeError("synthetic stale failure"),
                code="HANDLER_ERROR",
                lease_token=claim_a.lease_token,
                now=b_now,
            )
        worker_a.rollback()

        # Worker B's legitimate result is preserved, not thrown away.
        ack_outbox(worker_b, message_id, lease_token=claim_b.lease_token, now=b_now)
        worker_b.commit()

    with Session(migrated_engine) as check:
        row = check.get(OutboxMessage, message_id)
        assert row is not None
        assert row.status == OutboxStatus.DONE.value
        assert row.attempts == 1  # the reaped attempt only; B's success added none
        assert row.lease_until is None
        assert row.lease_token is None
