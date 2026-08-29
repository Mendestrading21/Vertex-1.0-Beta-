"""Full-chain integration test (real PostgreSQL, real migrations).

40 synthetic envelopes (multi-level duplicates included) -> ``ingest_envelope``
-> bounded worker run -> published ``attention`` snapshot -> read back through
the repository: <=15 items, deduplicated, ranked, SYNTHETIC-labeled, and
replayable.

Re-publication semantics under test (the documented contract of
``vertex_worker.handlers``): publish-if-changed. A second run over identical
inputs with an identical injected clock is a no-op — the head keeps the SAME
version and the SAME ``content_hash``. A run with a later clock publishes a
new version (``as_of`` and ages are part of the content and are never
silently frozen).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from vertex_core.synthetic import generate_envelopes
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import Observation, OutboxMessage
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import (
    DEV_SYNTHETIC_CONFIG,
    MAX_ATTENTION_ITEMS,
    POPULATION_SYNTHETIC,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_ATTENTION,
    build_registry,
)
from vertex_worker.ingest import TOPIC_OBSERVATION_INGESTED, ingest_envelope
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 1234
COUNT = 40


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def ingest_all(session_factory, envelopes) -> list:
    results = []
    with session_factory() as session:
        for envelope in envelopes:
            results.append(ingest_envelope(session, envelope))
        session.commit()
    return results


def test_full_ingestion_chain(session_factory) -> None:
    envelopes = generate_envelopes(seed=SEED, count=COUNT, base_time=BASE_TIME)
    unique_event_ids = {e.event_id for e in envelopes}
    assert len(unique_event_ids) < COUNT, "fixture must contain ingest-level duplicates"

    # --- Ingestion: idempotent insert + outbox in the same transaction -----
    results = ingest_all(session_factory, envelopes)
    inserted = [r for r in results if r.inserted]
    duplicates = [r for r in results if not r.inserted]
    assert len(inserted) == len(unique_event_ids)
    assert len(duplicates) == COUNT - len(unique_event_ids)
    assert all(r.outbox_message_id is not None for r in inserted)
    assert all(r.outbox_message_id is None for r in duplicates)

    with session_factory() as session:
        observation_count = session.execute(
            select(func.count()).select_from(Observation)
        ).scalar_one()
        pending = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status == OutboxStatus.PENDING.value)
        ).scalar_one()
    assert observation_count == len(unique_event_ids)
    assert pending == len(inserted)

    # --- Bounded worker run (no infinite loop in tests) --------------------
    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)
    processed = runner.drain(max_batches=10)
    assert processed == len(inserted)
    stats = runner.stats()
    assert stats.acked == len(inserted)
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0

    with session_factory() as session:
        remaining = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert remaining == 0

    # --- Published attention snapshot, read back via the repository --------
    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL
        )
    assert snapshot is not None
    content = snapshot.content
    items = content["items"]

    assert 1 <= len(items) <= MAX_ATTENTION_ITEMS
    # Deduplicated: no repeated item, no repeated cluster, and fewer clusters
    # than content observations (the multi-level duplicates were absorbed).
    assert len({i["item_id"] for i in items}) == len(items)
    assert len({i["provenance"]["cluster_id"] for i in items}) == len(items)
    assert content["coverage"]["clusters"] < content["coverage"]["content_observations"]
    # Ranked and explained.
    for item in items:
        assert 1 <= len(item["relevance_reasons"]) <= 3
        assert item["provenance"]["member_event_ids"]
        assert item["title"].startswith("[SYNTHETIC] ")
    # SYNTHETIC labeling: population and per-item nature.
    assert content["population"] == POPULATION_SYNTHETIC
    assert all(item["synthetic"] is True for item in items)
    assert content["as_of"] == NOW.isoformat()

    first_version = snapshot.version
    first_hash = snapshot.content_hash

    # --- Replay with identical clock: same version, same content -----------
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_OBSERVATION_INGESTED,
            {"event_id": "replay", "source": "synthetic-dev", "schema_version": "x/1"},
        )
        session.commit()
    replay_runner = make_runner(session_factory, clock)
    assert replay_runner.drain(max_batches=5) == 1
    assert replay_runner.stats().acked == 1

    with session_factory() as session:
        replayed = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL
        )
    assert replayed is not None
    assert replayed.version == first_version
    assert replayed.content_hash == first_hash
    assert replayed.content == content

    # --- Later clock: a NEW version is published (ages move honestly) ------
    clock.now = NOW + timedelta(minutes=5)
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_OBSERVATION_INGESTED,
            {"event_id": "tick", "source": "synthetic-dev", "schema_version": "x/1"},
        )
        session.commit()
    later_runner = make_runner(session_factory, clock)
    assert later_runner.drain(max_batches=5) == 1

    with session_factory() as session:
        later = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL
        )
    assert later is not None
    assert later.version == first_version + 1
    assert later.content_hash != first_hash
    assert later.content["as_of"] == clock.now.isoformat()
    # Same ranked identities: only time-derived fields moved.
    assert [i["item_id"] for i in later.content["items"]] == [
        i["item_id"] for i in items
    ]


def test_reingesting_same_envelopes_enqueues_nothing(session_factory) -> None:
    envelopes = generate_envelopes(seed=SEED, count=10, base_time=BASE_TIME)
    ingest_all(session_factory, envelopes)
    with session_factory() as session:
        before = session.execute(
            select(func.count()).select_from(OutboxMessage)
        ).scalar_one()
    # Full idempotent replay of the same batch.
    results = ingest_all(session_factory, envelopes)
    assert all(r.inserted is False for r in results)
    with session_factory() as session:
        after = session.execute(
            select(func.count()).select_from(OutboxMessage)
        ).scalar_one()
        observations = session.execute(
            select(func.count()).select_from(Observation)
        ).scalar_one()
    assert after == before
    assert observations == len({e.event_id for e in envelopes})
