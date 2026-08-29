"""Integration tests of the worker failure paths (real outbox rows).

Verifies fail-closed accounting on the real repository: a failing handler
records FAILED with a redacted, code-prefixed ``last_error`` and backoff; a
poisoned message reaches DEAD at ``max_attempts``; the mixed-population
boundary guard holds through the real chain.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE, generate_envelopes
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.errors import HandlerError
from vertex_worker.handlers import (
    FusionConfig,
    POPULATION_SYNTHETIC,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_ATTENTION,
    build_registry,
)
from vertex_worker.ingest import ingest_envelope
from vertex_worker.registry import HandlerRegistry
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def test_failing_handler_records_failed_with_code_and_backoff(session_factory) -> None:
    def failing_handler(session, message):
        raise HandlerError("synthetic failure for test", code="TEST_HANDLER_FAILURE")

    registry = HandlerRegistry()
    registry.register("test.failing", failing_handler)
    clock = MutableClock(NOW)
    runner = WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )
    with session_factory() as session:
        message_id = enqueue_outbox(session, "test.failing", {"k": "v"})
        session.commit()

    assert runner.drain(max_batches=2) == 1
    stats = runner.stats()
    assert (stats.failed, stats.dead, stats.acked) == (1, 0, 0)

    with session_factory() as session:
        row = session.execute(
            select(OutboxMessage).where(OutboxMessage.id == message_id)
        ).scalar_one()
        assert row.status == OutboxStatus.FAILED.value
        assert row.attempts == 1
        assert row.last_error.startswith("TEST_HANDLER_FAILURE:HandlerError")
        # Backoff: the retry-not-before instant is in the future.
        assert row.lease_until is not None
        assert row.lease_until > NOW


def test_poisoned_message_reaches_dead_at_max_attempts(session_factory) -> None:
    def failing_handler(session, message):
        raise HandlerError("always failing", code="ALWAYS_FAILS")

    registry = HandlerRegistry()
    registry.register("test.poison", failing_handler)
    clock = MutableClock(NOW)
    runner = WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        max_attempts=2,
        clock=clock,
    )
    with session_factory() as session:
        message_id = enqueue_outbox(session, "test.poison", {"k": "v"})
        session.commit()

    # First attempt -> FAILED with backoff.
    assert runner.drain(max_batches=2) == 1
    # Advance past the backoff so the retry is due, then second attempt -> DEAD.
    clock.now = NOW + timedelta(hours=2)
    assert runner.drain(max_batches=2) == 1
    stats = runner.stats()
    assert (stats.failed, stats.dead) == (2, 1)

    with session_factory() as session:
        row = session.execute(
            select(OutboxMessage).where(OutboxMessage.id == message_id)
        ).scalar_one()
        assert row.status == OutboxStatus.DEAD.value
        assert row.attempts == 2

    # A DEAD message is never claimed again.
    clock.now = NOW + timedelta(hours=10)
    assert runner.drain(max_batches=2) == 0


def test_mixed_population_is_labeled_through_the_real_chain(session_factory) -> None:
    """SYNTHETIC + non-SYNTHETIC observations => the published snapshot is
    labeled SYNTHETIC and every item declares its own nature (no silent mix)."""
    demo_source = "demo-feed"
    demo_rights = "DEMO"
    config = FusionConfig(
        allowed_sources=frozenset({SYNTHETIC_SOURCE, demo_source}),
        usable_rights=frozenset({SYNTHETIC_RIGHTS, demo_rights}),
        source_tiers={SYNTHETIC_SOURCE: "P4", demo_source: "P3"},
    )
    clock = MutableClock(NOW)
    registry = build_registry(clock=clock, fusion_config=config)
    runner = WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )

    envelopes = generate_envelopes(seed=42, count=3, base_time=BASE_TIME)
    with session_factory() as session:
        for envelope in envelopes:
            ingest_envelope(session, envelope)
        # Two DEMO-labeled (non-synthetic) fixture observations.
        for number in (1, 2):
            published = BASE_TIME + timedelta(minutes=number)
            insert_observation(
                session,
                event_id=f"demo:{number:04d}",
                schema_version="demo-news/1.0",
                source=demo_source,
                source_event_id=f"demo-native-{number:04d}",
                instrument_ref=f"DEMO{number}",
                published_at=published,
                received_at=published + timedelta(seconds=10),
                as_of=published + timedelta(seconds=10),
                stale_after=published + timedelta(hours=6),
                quality_status="VALID",
                delay_status="UNKNOWN",
                rights=demo_rights,
                payload={
                    "type": "news",
                    "title": f"Demo fixture headline number {number:04d}",
                    "canonical_url": f"https://demo.invalid/news/{number:04d}",
                    "entities": [f"DEMO{number}"],
                },
            )
        session.commit()

    assert runner.drain(max_batches=5) > 0

    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL
        )
    assert snapshot is not None
    content = snapshot.content
    assert content["population"] == POPULATION_SYNTHETIC
    natures = {item["item_id"]: item["synthetic"] for item in content["items"]}
    assert True in natures.values(), "synthetic items must declare themselves"
    assert False in natures.values(), "non-synthetic items must declare themselves"
    assert content["coverage"]["synthetic_observations"] >= 1
    assert content["coverage"]["non_synthetic_observations"] == 2
