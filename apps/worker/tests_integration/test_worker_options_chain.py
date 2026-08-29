"""Option-chain integration test (real PostgreSQL, real migrations).

Synthetic option-chain envelopes -> ``ingest_envelope`` (which enqueues BOTH
``observation.ingested`` and ``option_chains.ingested``) -> bounded worker
run -> one published ``option_chain/{underlying}`` snapshot per underlying:
trading-class separation at a shared expiration, Vertex IV/Greeks with
lineage for sane quotes only, typed refusals for crossed/stale/missing
quotes, honest coverage and publish-if-changed replay semantics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from vertex_core.synthetic import (
    SYNTHETIC_OPTION_UNDERLYINGS,
    generate_option_chain_envelopes,
)
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.options import (
    REASON_QUOTE_CROSSED,
    REASON_QUOTE_MISSING,
    REASON_QUOTE_STALE,
    SNAPSHOT_KIND_OPTION_CHAIN,
    TOPIC_OPTION_CHAINS_INGESTED,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 434343


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_OPTION_CHAINS_INGESTED in registry.topics
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def test_option_chains_end_to_end(session_factory) -> None:
    envelopes = generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME)
    with session_factory() as session:
        inserted = sum(1 for e in envelopes if ingest_envelope(session, e).inserted)
        session.commit()
    assert inserted == len(envelopes) == 12  # 4 underlyings x 3 slices

    with session_factory() as session:
        chain_jobs = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.topic == TOPIC_OPTION_CHAINS_INGESTED)
        ).scalar_one()
    assert chain_jobs == inserted

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

    versions: dict[str, int] = {}
    hashes: dict[str, str] = {}
    for underlying in SYNTHETIC_OPTION_UNDERLYINGS:
        with session_factory() as session:
            snapshot = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_OPTION_CHAIN, key=underlying
            )
        assert snapshot is not None, underlying
        content = snapshot.content
        versions[underlying] = snapshot.version
        hashes[underlying] = snapshot.content_hash

        assert content["schema_version"] == "vertex.option-chain/1.0"
        assert content["population"] == "SYNTHETIC"
        assert content["underlying"] == underlying
        assert content["value_nature"] == "THEORETICAL"
        assert content["as_of"] == NOW.isoformat()

        # Three (expiration, trading_class) groups; the near expiration is
        # shared by two DISTINCT trading classes and never merged.
        groups = [
            (g["expiration"], g["trading_class"]) for g in content["expirations"]
        ]
        assert len(groups) == len(set(groups)) == 3
        expirations = [expiration for expiration, _ in groups]
        shared = [x for x in set(expirations) if expirations.count(x) == 2]
        assert len(shared) == 1
        assert {tc for exp, tc in groups if exp == shared[0]} == {
            underlying,
            f"{underlying}W",
        }

        # Every group: 24 contracts with full identity; sane quotes resolve
        # a THEORETICAL Vertex IV with CalculationRecord lineage.
        discard_reasons: list[str] = []
        resolved = 0
        for group in content["expirations"]:
            assert len(group["contracts"]) == 24
            coverage = group["coverage"]
            assert coverage["expected"] == 24
            assert coverage["iv_resolved"] == 24 - len(coverage["discarded"])
            discard_reasons.extend(
                entry["reason"] for entry in coverage["discarded"]
            )
            resolved += coverage["iv_resolved"]
            for entry in group["contracts"]:
                assert entry["trading_class"] == group["trading_class"]
                assert entry["multiplier"] == 100
                assert entry["settlement"] == "CASH"
                if entry["iv"]["status"] == "OK":
                    assert entry["iv"]["value_nature"] == "THEORETICAL"
                    calc = entry["iv"]["calculation"]
                    assert calc["calculation_id"] == "options.implied_volatility"
                    assert calc["input_hash"].startswith("sha256:")
                    assert entry["greeks"]["status"] == "OK"
                    assert (
                        entry["greeks"]["calculation"]["calculation_id"]
                        == "options.greeks"
                    )
                else:
                    assert entry["iv"]["reason"]
                    assert entry["greeks"]["status"] == "ABSENT"

        # The three deliberately degraded quotes are refused with their
        # typed reasons; the sane majority resolves.
        assert discard_reasons.count(REASON_QUOTE_CROSSED) == 1
        assert discard_reasons.count(REASON_QUOTE_STALE) == 1
        assert discard_reasons.count(REASON_QUOTE_MISSING) == 1
        assert resolved >= 40  # most of the 72 rows resolve an IV

        budget = content["row_budget"]
        assert budget["total_rows"] == 72
        assert budget["published_rows"] == 72
        assert budget["truncated_rows"] == 0

    # -- replay with identical clock: publish-if-changed keeps every head ----
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_OPTION_CHAINS_INGESTED,
            {
                "event_id": "replay",
                "source": "synthetic-dev",
                "schema_version": "synthetic-option-chain/1.0",
            },
        )
        session.commit()
    replay_runner = make_runner(session_factory, clock)
    assert replay_runner.drain(max_batches=5) == 1
    for underlying in SYNTHETIC_OPTION_UNDERLYINGS:
        with session_factory() as session:
            replayed = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_OPTION_CHAIN, key=underlying
            )
        assert replayed is not None
        assert replayed.version == versions[underlying]
        assert replayed.content_hash == hashes[underlying]
