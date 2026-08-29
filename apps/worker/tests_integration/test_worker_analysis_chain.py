"""Analysis dossier integration test (real PostgreSQL, real migrations).

Synthetic bars + option chains + news -> ``ingest_envelope`` -> bounded
worker run -> one published ``analysis/{instrument}`` snapshot per focus
instrument: verbatim OHLCV bars, fusion evidence, THEORETICAL scenarios from
the published chain, and the single AdviceEngine's HONEST verdict
(INSUFFICIENT_DATA on the synthetic population — never forced), plus
publish-if-changed replay semantics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    generate_daily_bar_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.analysis import (
    SNAPSHOT_KIND_ANALYSIS,
    TOPIC_ANALYSIS_INGESTED,
)
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 454545


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_ANALYSIS_INGESTED in registry.topics
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def test_analysis_dossiers_end_to_end(session_factory) -> None:
    chains = generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME)
    bars = generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    with session_factory() as session:
        inserted = sum(
            1 for e in (*chains, *bars) if ingest_envelope(session, e).inserted
        )
        session.commit()
    assert inserted == len(chains) + len(bars) == 16

    with session_factory() as session:
        analysis_jobs = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.topic == TOPIC_ANALYSIS_INGESTED)
        ).scalar_one()
    # Chains AND bars both feed the analysis topic (12 + 4 messages).
    assert analysis_jobs == 16

    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)
    runner.drain(max_batches=30)
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
    for instrument in SYNTHETIC_FOCUS_TICKERS:
        with session_factory() as session:
            snapshot = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_ANALYSIS, key=instrument
            )
        assert snapshot is not None, instrument
        content = snapshot.content
        versions[instrument] = snapshot.version
        hashes[instrument] = snapshot.content_hash

        assert content["schema_version"] == "vertex.analysis/1.0"
        assert content["population"] == "SYNTHETIC"
        assert content["instrument"] == instrument
        assert content["as_of"] == NOW.isoformat()

        bars_block = content["bars"]
        assert bars_block["status"] == "OK"
        assert bars_block["count"] == 60
        assert bars_block["discarded"] == []
        assert bars_block["last_close"] == bars_block["bars"][-1]["close"]
        assert bars_block["fresh"] is True

        # Scenarios exist because the published chain holds healthy
        # contracts, and they are labeled THEORETICAL with full lineage.
        scenarios = content["scenarios"]
        assert scenarios["status"] == "OK"
        assert scenarios["value_nature"] == "THEORETICAL"
        assert scenarios["basis"]["premium_side"] == "ASK"
        assert scenarios["basis"]["chain_snapshot_version"] is not None
        assert (
            scenarios["calculation"]["calculation_id"] == "options.scenario_grid"
        )
        assert len(scenarios["grid"]) == 1
        assert len(scenarios["grid"][0]) == 3
        assert all(len(row) == 5 for row in scenarios["grid"][0])

        # The single AdviceEngine's HONEST verdict: the synthetic population
        # cannot prove entitlements/session/liquidity/contradictions/
        # constraints, so INSUFFICIENT_DATA with UNEVALUABLE blocks.
        advice = content["advice"]
        assert advice["status"] == "INSUFFICIENT_DATA"
        assert advice["direction"] == "UNKNOWN"
        gates = {g["gate_id"]: g for g in advice["gates"]}
        assert len(gates) == 10
        blocked = [g for g in advice["gates"] if g["status"] == "BLOCK"]
        assert blocked and all(g["reason_code"] == "UNEVALUABLE" for g in blocked)
        assert gates["instrument_resolved"]["reason_code"] == "RESOLVED_WITHOUT_CONID"
        assert gates["calculations_valid"]["reason_code"] == "ALL_CALCULATIONS_VALID"
        assert advice["scenario_ids"] == [scenarios["calculation"]["input_hash"]]
        assert "SYNTHETIC development population" in advice["limitations"]

    # -- replay with identical clock: publish-if-changed keeps every head ----
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_ANALYSIS_INGESTED,
            {
                "event_id": "replay",
                "source": "synthetic-dev",
                "schema_version": "synthetic-daily-bars/1.0",
            },
        )
        session.commit()
    replay_runner = make_runner(session_factory, clock)
    assert replay_runner.drain(max_batches=5) == 1
    for instrument in SYNTHETIC_FOCUS_TICKERS:
        with session_factory() as session:
            replayed = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_ANALYSIS, key=instrument
            )
        assert replayed is not None
        assert replayed.version == versions[instrument]
        assert replayed.content_hash == hashes[instrument]


def test_bars_without_chain_publish_scenarioless_dossier(session_factory) -> None:
    bars = generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    with session_factory() as session:
        for envelope in bars:
            ingest_envelope(session, envelope)
        session.commit()

    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)
    runner.drain(max_batches=20)
    assert runner.stats().failed == 0

    instrument = SYNTHETIC_FOCUS_TICKERS[0]
    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ANALYSIS, key=instrument
        )
    assert snapshot is not None
    scenarios = snapshot.content["scenarios"]
    assert scenarios == {
        "status": "ABSENT",
        "reason": "no_option_chain_snapshot",
    }
    gates = {g["gate_id"]: g for g in snapshot.content["advice"]["gates"]}
    assert gates["calculations_valid"]["reason_code"] == "UNEVALUABLE"
