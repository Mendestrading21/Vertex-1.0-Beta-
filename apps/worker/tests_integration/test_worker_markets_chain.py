"""Markets chain integration test (real PostgreSQL, real migrations).

Synthetic daily-quote envelopes -> ``ingest_envelope`` (which enqueues BOTH
``observation.ingested`` and ``quotes.ingested``) -> bounded worker run ->
published ``markets_overview/global`` snapshot read back via the repository:
sectors/tickers with exact decimal closes, ``market.simple_return`` lineage,
fail-closed discards for tickers missing a close, breadth with its coverage
gate, SYNTHETIC population and publish-if-changed replay semantics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from vertex_core.synthetic import (
    SYNTHETIC_SECTOR_TICKERS,
    SYNTHETIC_SECTORS,
    generate_daily_quote_envelopes,
)
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.markets import (
    REASON_MISSING_CLOSE,
    SNAPSHOT_KIND_MARKETS,
    TOPIC_QUOTES_INGESTED,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 424242


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_QUOTES_INGESTED in registry.topics
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def test_markets_chain_end_to_end(session_factory) -> None:
    envelopes = generate_daily_quote_envelopes(
        seed=SEED, base_time=BASE_TIME, missing_close_count=2
    )
    with session_factory() as session:
        inserted = sum(1 for e in envelopes if ingest_envelope(session, e).inserted)
        session.commit()
    assert inserted == len(envelopes) == 46  # 22 tickers x 2 days + 2 x 1 day

    with session_factory() as session:
        quote_jobs = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.topic == TOPIC_QUOTES_INGESTED)
        ).scalar_one()
    assert quote_jobs == inserted  # one markets job per inserted daily quote

    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)
    runner.drain(max_batches=20)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0

    with session_factory() as session:
        remaining = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert remaining == 0

    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_MARKETS, key="global"
        )
    assert snapshot is not None
    content = snapshot.content

    assert content["schema_version"] == "vertex.markets-overview/1.0"
    assert content["population"] == "SYNTHETIC"
    assert content["as_of"] == NOW.isoformat()
    assert content["engine_version"] == ENGINE_VERSION

    coverage = content["coverage"]
    assert coverage["expected"] == 24
    assert coverage["received"] == 24
    assert coverage["covered"] == 22
    assert coverage["discarded"] == 2
    assert all(
        entry["reason"] == REASON_MISSING_CLOSE
        for entry in coverage["discarded_tickers"]
    )
    assert coverage["rejected_records"] == []

    # All 6 declared sectors are present; published tickers belong to them.
    sectors = content["sectors"]
    assert [s["sector"] for s in sectors] == sorted(SYNTHETIC_SECTORS)
    published = [t for s in sectors for t in s["tickers"]]
    assert len(published) == 22
    for sector in sectors:
        declared = set(SYNTHETIC_SECTOR_TICKERS[sector["sector"]])
        for ticker in sector["tickers"]:
            assert ticker["ticker"] in declared
            # Exact decimal strings and preserved calculation lineage.
            assert Decimal(ticker["last_close"]) > 0
            assert ticker["synthetic"] is True
            calc = ticker["calculation"]
            assert calc["calculation_id"] == "market.simple_return"
            assert calc["engine_version"] == ENGINE_VERSION
            assert calc["input_hash"].startswith("sha256:")

    # Per-sector weights of covered tickers sum to ~1 (quantized shares).
    for sector in sectors:
        if not sector["tickers"]:
            continue
        total = sum(Decimal(t["weight_in_sector"]) for t in sector["tickers"])
        assert abs(total - 1) <= Decimal("0.00001")

    # Breadth: coverage 22/24 >= 0.8 threshold; counts agree with returns.
    breadth = content["breadth"]
    assert breadth["status"] == "OK"
    assert breadth["universe_size"] == 24
    assert breadth["covered_count"] == 22
    up = sum(1 for t in published if Decimal(t["return_1d"]) > 0)
    assert breadth["above_count"] == up
    assert breadth["calculation"]["calculation_id"] == "market.breadth"

    # The generator degrades 2 PARTIAL + 2 STALE latest closes -> partial.
    assert content["data_state"] == "partial"
    qualities = [t["quality"] for t in published]
    assert qualities.count("PARTIAL") == 2
    assert qualities.count("STALE") == 2

    assert isinstance(content["conclusion"], str)
    assert "22 sont couverts" in content["conclusion"]

    # -- replay with identical clock: publish-if-changed keeps the head ------
    first_version, first_hash = snapshot.version, snapshot.content_hash
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_QUOTES_INGESTED,
            {"event_id": "replay", "source": "synthetic-dev", "schema_version": "synthetic-daily-quote/1.0"},
        )
        session.commit()
    replay_runner = make_runner(session_factory, clock)
    assert replay_runner.drain(max_batches=5) == 1

    with session_factory() as session:
        replayed = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_MARKETS, key="global"
        )
    assert replayed is not None
    assert replayed.version == first_version
    assert replayed.content_hash == first_hash

    # -- later clock: new version (as_of moves honestly) ---------------------
    clock.now = NOW + timedelta(minutes=5)
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_QUOTES_INGESTED,
            {"event_id": "tick", "source": "synthetic-dev", "schema_version": "synthetic-daily-quote/1.0"},
        )
        session.commit()
    later_runner = make_runner(session_factory, clock)
    assert later_runner.drain(max_batches=5) == 1
    with session_factory() as session:
        later = get_current_snapshot(session, kind=SNAPSHOT_KIND_MARKETS, key="global")
    assert later is not None
    assert later.version == first_version + 1
    assert later.content["as_of"] == clock.now.isoformat()
    # Identical universe values: only time-derived fields moved.
    assert [t["ticker"] for s in later.content["sectors"] for t in s["tickers"]] == [
        t["ticker"] for t in published
    ]


def test_non_quote_envelopes_enqueue_no_markets_job(session_factory) -> None:
    from vertex_core.synthetic import generate_envelopes

    envelopes = generate_envelopes(seed=SEED, count=10, base_time=BASE_TIME)
    with session_factory() as session:
        for envelope in envelopes:
            ingest_envelope(session, envelope)
        session.commit()
    with session_factory() as session:
        quote_jobs = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.topic == TOPIC_QUOTES_INGESTED)
        ).scalar_one()
    assert quote_jobs == 0
