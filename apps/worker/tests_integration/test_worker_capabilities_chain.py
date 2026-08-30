"""Integration tests of the ``capabilities.refresh`` topic (real PostgreSQL).

The capabilities snapshot lists ONLY what was really probed and persisted;
with nothing persisted it is an honest empty snapshot (the API layer renders
per-capability ``NEVER_TESTED`` states — never this worker).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import (
    CAPABILITIES_SCHEMA_VERSION,
    DEV_SYNTHETIC_CONFIG,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_CAPABILITIES,
    TOPIC_CAPABILITIES_REFRESH,
    build_registry,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


def make_runner(session_factory, now: datetime = NOW) -> WorkerRunner:
    registry = build_registry(
        clock=lambda: now, fusion_config=DEV_SYNTHETIC_CONFIG
    )
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=lambda: now,
    )


def enqueue_refresh(session_factory) -> None:
    with session_factory() as session:
        enqueue_outbox(session, TOPIC_CAPABILITIES_REFRESH, {"reason": "test"})
        session.commit()


def read_snapshot(session_factory):
    with session_factory() as session:
        return get_current_snapshot(
            session, kind=SNAPSHOT_KIND_CAPABILITIES, key=SNAPSHOT_KEY_GLOBAL
        )


def test_empty_capabilities_snapshot_is_honest(session_factory) -> None:
    enqueue_refresh(session_factory)
    runner = make_runner(session_factory)
    assert runner.drain(max_batches=5) == 1
    assert runner.stats().acked == 1

    snapshot = read_snapshot(session_factory)
    assert snapshot is not None
    assert snapshot.version == 1
    assert snapshot.content == {
        "schema_version": CAPABILITIES_SCHEMA_VERSION,
        "as_of": NOW.isoformat(),
        "probed_sources": [],
    }


def test_persisted_probe_appears_in_snapshot(session_factory) -> None:
    # First refresh: honest empty snapshot.
    enqueue_refresh(session_factory)
    make_runner(session_factory).drain(max_batches=5)

    # Persist one real probe observation (SYNTHETIC/DEMO fixture payload).
    probe_time = NOW - timedelta(hours=1)
    with session_factory() as session:
        inserted = insert_observation(
            session,
            event_id="edge-demo:capability:0001",
            schema_version="source-capability/1.0",
            source="edge-demo",
            received_at=probe_time,
            as_of=probe_time,
            stale_after=probe_time + timedelta(hours=6),
            quality_status="VALID",
            delay_status="UNKNOWN",
            rights="DEMO",
            payload={
                "probe_id": "probe-demo-0001",
                "connection_epoch": 1,
                "tested_at": probe_time.isoformat(),
                "expires_at": (probe_time + timedelta(hours=6)).isoformat(),
                "fields": [
                    {
                        "capability_id": "quotes",
                        "field": "bid",
                        "status": "DELAYED",
                        "reason_code": None,
                    }
                ],
            },
        )
        session.commit()
    assert inserted is True

    enqueue_refresh(session_factory)
    runner = make_runner(session_factory)
    assert runner.drain(max_batches=5) == 1

    snapshot = read_snapshot(session_factory)
    assert snapshot is not None
    assert snapshot.version == 2  # content changed => new version
    sources = snapshot.content["probed_sources"]
    assert len(sources) == 1
    entry = sources[0]
    assert entry["source"] == "edge-demo"
    assert entry["snapshot"]["probe_id"] == "probe-demo-0001"
    assert entry["snapshot"]["fields"][0]["status"] == "DELAYED"

    # Refresh again with identical persisted state and identical clock:
    # publish-if-changed keeps the same version and hash.
    previous_hash = snapshot.content_hash
    enqueue_refresh(session_factory)
    make_runner(session_factory).drain(max_batches=5)
    replayed = read_snapshot(session_factory)
    assert replayed is not None
    assert replayed.version == 2
    assert replayed.content_hash == previous_hash
