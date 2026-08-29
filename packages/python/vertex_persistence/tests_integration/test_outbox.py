"""Outbox: transactional atomicity, SKIP LOCKED claims, leases, DEAD letters.

Clocks are injected synthetic instants — no sleeping, no real time.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from vertex_persistence.backoff import DEFAULT_MAX_ATTEMPTS, compute_backoff_seconds
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.errors import OutboxLeaseError, OutboxStateError
from vertex_persistence.models import Observation, OutboxMessage
from vertex_persistence.repository import (
    ack_outbox,
    claim_outbox_batch,
    enqueue_outbox,
    fail_outbox,
    insert_observation,
    reap_expired_leases,
)

UTC = timezone.utc
T0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)
TOPIC = "synthetic.test.topic"


def _enqueue(session: Session, n: int = 1) -> list[int]:
    return [enqueue_outbox(session, TOPIC, {"seq": i}) for i in range(n)]


def test_enqueue_shares_business_transaction_rollback_drops_both(db_session: Session) -> None:
    inserted = insert_observation(
        db_session,
        event_id="evt-atomic",
        schema_version="1.0.0",
        source="SYNTHETIC_TEST",
        received_at=T0,
        as_of=T0,
        stale_after=T0 + timedelta(minutes=5),
        quality_status="VALID",
        delay_status="LIVE",
        rights="DELAYED_ENTITLED",
        payload={"symbol": "SYN"},
    )
    assert inserted is True
    enqueue_outbox(db_session, TOPIC, {"event_id": "evt-atomic"})
    db_session.rollback()  # business failure: neither the row nor the message survives
    assert db_session.execute(select(func.count()).select_from(Observation)).scalar_one() == 0
    assert db_session.execute(select(func.count()).select_from(OutboxMessage)).scalar_one() == 0


def test_enqueue_commit_persists_both(db_session: Session) -> None:
    _enqueue(db_session, 1)
    db_session.commit()
    row = db_session.execute(select(OutboxMessage)).scalar_one()
    assert row.status == OutboxStatus.PENDING.value
    assert row.attempts == 0
    assert row.payload == {"seq": 0}
    assert row.lease_until is None


def test_concurrent_claims_are_disjoint_skip_locked(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as setup:
        _enqueue(setup, 4)
        setup.commit()
    with Session(migrated_engine) as worker_a, Session(migrated_engine) as worker_b:
        claimed_a = claim_outbox_batch(worker_a, [TOPIC], limit=2, lease_seconds=60, now=T0)
        # worker_a has NOT committed: its rows stay locked, SKIP LOCKED must skip them.
        claimed_b = claim_outbox_batch(worker_b, [TOPIC], limit=4, lease_seconds=60, now=T0)
        ids_a = {message.id for message in claimed_a}
        ids_b = {message.id for message in claimed_b}
        assert len(ids_a) == 2
        assert len(ids_b) == 2  # only the two unlocked rows, no blocking, no overlap
        assert ids_a.isdisjoint(ids_b)
        worker_a.commit()
        worker_b.commit()
    with Session(migrated_engine) as check:
        statuses = check.execute(select(OutboxMessage.status)).scalars().all()
        assert statuses == [OutboxStatus.IN_PROGRESS.value] * 4


def test_claim_filters_topics_and_respects_limit(db_session: Session) -> None:
    enqueue_outbox(db_session, "other.topic", {"seq": 99})
    _enqueue(db_session, 2)
    db_session.commit()
    claimed = claim_outbox_batch(db_session, [TOPIC], limit=1, lease_seconds=60, now=T0)
    assert len(claimed) == 1
    assert claimed[0].topic == TOPIC
    assert claimed[0].lease_until == T0 + timedelta(seconds=60)
    db_session.commit()


def test_expired_lease_is_reaped_then_reclaimable(db_session: Session) -> None:
    _enqueue(db_session, 1)
    db_session.commit()
    (claimed,) = claim_outbox_batch(db_session, [TOPIC], limit=1, lease_seconds=60, now=T0)
    db_session.commit()

    # Lease still running: nothing to reap, nothing claimable.
    assert reap_expired_leases(db_session, now=T0 + timedelta(seconds=30)) == 0
    assert claim_outbox_batch(db_session, [TOPIC], 1, 60, now=T0 + timedelta(seconds=30)) == []

    # Worker vanished, lease expired: the reaper counts the lost attempt and
    # re-offers the message after its backoff (never a silent PENDING).
    reap_now = T0 + timedelta(seconds=61)
    assert reap_expired_leases(db_session, now=reap_now) == 1
    db_session.commit()
    row = db_session.get(OutboxMessage, claimed.id)
    assert row is not None
    assert row.status == OutboxStatus.FAILED.value
    assert row.attempts == 1
    assert row.lease_token is None
    retry_at = reap_now + timedelta(seconds=compute_backoff_seconds(1))
    assert row.lease_until == retry_at
    # Not claimable before the retry-not-before instant, claimable after.
    assert claim_outbox_batch(db_session, [TOPIC], 1, 60, now=reap_now) == []
    reclaimed = claim_outbox_batch(db_session, [TOPIC], 1, 60, now=retry_at)
    assert [message.id for message in reclaimed] == [claimed.id]
    assert reclaimed[0].lease_token != claimed.lease_token  # a fresh lease grant
    db_session.commit()


def test_fail_applies_exponential_backoff(db_session: Session) -> None:
    (message_id,) = _enqueue(db_session, 1)
    db_session.commit()
    (claimed,) = claim_outbox_batch(db_session, [TOPIC], 1, 60, now=T0)
    status = fail_outbox(
        db_session,
        message_id,
        "synthetic handler error",
        lease_token=claimed.lease_token,
        now=T0,
    )
    db_session.commit()
    row = db_session.get(OutboxMessage, message_id)
    assert status == OutboxStatus.FAILED.value
    assert row is not None
    assert row.attempts == 1
    assert row.lease_until == T0 + timedelta(seconds=5)  # first backoff step
    assert row.last_error == "synthetic handler error"
    # Not claimable before its retry-not-before instant, claimable after.
    assert claim_outbox_batch(db_session, [TOPIC], 1, 60, now=T0 + timedelta(seconds=4)) == []
    assert len(claim_outbox_batch(db_session, [TOPIC], 1, 60, now=T0 + timedelta(seconds=6))) == 1
    db_session.commit()


def test_max_attempts_reaches_dead_and_stops_delivery(db_session: Session) -> None:
    (message_id,) = _enqueue(db_session, 1)
    db_session.commit()
    now = T0
    for attempt in range(1, DEFAULT_MAX_ATTEMPTS + 1):
        claimed = claim_outbox_batch(db_session, [TOPIC], 1, lease_seconds=10, now=now)
        assert [message.id for message in claimed] == [message_id]
        status = fail_outbox(
            db_session,
            message_id,
            f"synthetic failure {attempt}",
            lease_token=claimed[0].lease_token,
            now=now,
        )
        db_session.commit()
        now = now + timedelta(hours=2)  # move past any backoff before the next claim
    assert status == OutboxStatus.DEAD.value
    row = db_session.get(OutboxMessage, message_id)
    assert row is not None
    assert row.attempts == DEFAULT_MAX_ATTEMPTS
    assert row.lease_until is None
    assert claim_outbox_batch(db_session, [TOPIC], 1, 10, now=now) == []  # DEAD is never re-offered


def test_ack_marks_done_and_message_stays_done(db_session: Session) -> None:
    (message_id,) = _enqueue(db_session, 1)
    db_session.commit()
    (claimed,) = claim_outbox_batch(db_session, [TOPIC], 1, 60, now=T0)
    ack_outbox(
        db_session, message_id, lease_token=claimed.lease_token, now=T0 + timedelta(seconds=1)
    )
    db_session.commit()
    row = db_session.get(OutboxMessage, message_id)
    assert row is not None
    assert row.status == OutboxStatus.DONE.value
    assert row.lease_until is None
    assert row.lease_token is None
    assert claim_outbox_batch(db_session, [TOPIC], 1, 60, now=T0 + timedelta(hours=1)) == []


def test_ack_and_fail_require_an_owned_lease(db_session: Session) -> None:
    (message_id,) = _enqueue(db_session, 1)
    db_session.commit()
    # Never claimed: no lease is held, whatever token the caller presents.
    with pytest.raises(OutboxLeaseError, match="not held under this lease token"):
        ack_outbox(db_session, message_id, lease_token="synthetic-unissued-token", now=T0)
    db_session.rollback()
    with pytest.raises(OutboxLeaseError, match="not held under this lease token"):
        fail_outbox(
            db_session, message_id, "synthetic", lease_token="synthetic-unissued-token", now=T0
        )
    db_session.rollback()
    with pytest.raises(OutboxStateError, match="does not exist"):
        ack_outbox(db_session, 999999, lease_token="synthetic-unissued-token", now=T0)
    db_session.rollback()
    # A finished message no longer carries a lease either: the old token is dead.
    (claimed,) = claim_outbox_batch(db_session, [TOPIC], 1, 60, now=T0)
    ack_outbox(db_session, message_id, lease_token=claimed.lease_token, now=T0)
    db_session.commit()
    with pytest.raises(OutboxLeaseError, match="not held under this lease token"):
        ack_outbox(db_session, message_id, lease_token=claimed.lease_token, now=T0)
    db_session.rollback()
