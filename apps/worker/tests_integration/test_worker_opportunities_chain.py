"""Opportunities chain integration test (real PostgreSQL, real migrations).

Synthetic daily bars + option chains -> ``ingest_envelope`` (which enqueues an
ADDITIONAL ``opportunities.refresh`` message per newly written bars/chain
observation) -> bounded worker run -> published ``opportunities/global``
snapshot read back through the repository.

Hard proofs, on real rows:

- NO candidate carrying a closed status (``BLOCKED`` / ``INSUFFICIENT_DATA``)
  sits in the qualified group, and no open status sits in the excluded group
  — both groups are traversed exhaustively, candidate by candidate;
- the distribution of exclusion reasons is published and COHERENT with the
  number of candidates (it accounts for every excluded candidate and for
  nothing else);
- ``profile_ref`` carries BOTH the manifest id and the manifest version;
- the ranking is stable across two executions: an identical drain
  republishes nothing (same version, same content hash) and a later clock
  moves only the time-derived fields, never the ordering.

Every fixture is SYNTHETIC and deterministic (fixed seed, fixed clock).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from sqlalchemy import func, select

from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_SCHEMA_DAILY_BARS,
    SYNTHETIC_SECTOR_TICKERS,
    SYNTHETIC_SOURCE,
    generate_daily_bar_envelopes,
    generate_option_chain_envelopes,
)
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.opportunities import (
    DEFAULT_PROFILE_ID,
    DEFAULT_PROFILES_PATH,
    EXCLUDED_STATUSES,
    QUALIFIED_ORDERING_KEYS,
    QUALIFIED_STATUSES,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_OPPORTUNITIES,
    TOPIC_OPPORTUNITIES_REFRESH,
    group_for_status,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 20260825

UNIVERSE = tuple(
    ticker for tickers in SYNTHETIC_SECTOR_TICKERS.values() for ticker in tickers
)


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_OPPORTUNITIES_REFRESH in registry.topics
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def _drain_clean(runner: WorkerRunner, session_factory) -> None:
    runner.drain(max_batches=60)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0
    with session_factory() as session:
        remaining = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert remaining == 0


def _refresh_message(event_id: str) -> dict[str, str]:
    return {
        "event_id": event_id,
        "source": SYNTHETIC_SOURCE,
        "schema_version": SYNTHETIC_SCHEMA_DAILY_BARS,
    }


def test_opportunities_chain_end_to_end(session_factory) -> None:
    chains = generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME)
    bars = generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    with session_factory() as session:
        inserted = sum(
            1 for envelope in (*chains, *bars) if ingest_envelope(session, envelope).inserted
        )
        session.commit()
    assert inserted == len(chains) + len(bars) == 16

    with session_factory() as session:
        refresh_jobs = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.topic == TOPIC_OPPORTUNITIES_REFRESH)
        ).scalar_one()
    # Bars AND chains both change a candidate's advice basis (12 + 4).
    assert refresh_jobs == inserted == 16

    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)
    _drain_clean(runner, session_factory)

    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_OPPORTUNITIES, key=SNAPSHOT_KEY_GLOBAL
        )
    assert snapshot is not None
    content = snapshot.content

    assert content["schema_version"] == "vertex.opportunities/1.0"
    assert content["population"] == "SYNTHETIC"
    assert content["as_of"] == NOW.isoformat()
    assert content["engine_version"] == ENGINE_VERSION

    # -- 1. profile_ref carries BOTH the manifest id and its version --------
    manifest = yaml.safe_load(
        Path(DEFAULT_PROFILES_PATH).read_text(encoding="utf-8")
    )
    entry = next(
        profile
        for profile in manifest["profiles"]
        if profile["id"] == DEFAULT_PROFILE_ID
    )
    profile_ref = content["profile_ref"]
    assert profile_ref["id"] == entry["id"] == DEFAULT_PROFILE_ID
    assert profile_ref["version"] == entry["version"]
    assert isinstance(profile_ref["version"], str) and profile_ref["version"]
    assert profile_ref["source"] == "manifests/strategy-profiles.yaml"
    # Every required evidence of the manifest is really checked per candidate.
    required = tuple(entry["required_evidence"])

    qualified = content["qualified"]
    excluded = content["excluded"]
    coverage = content["coverage"]

    # -- 2. exhaustive traversal of BOTH groups ----------------------------
    for candidate in qualified:
        status = candidate["advice"]["status"]
        assert status not in EXCLUDED_STATUSES, candidate["ticker"]
        assert status in QUALIFIED_STATUSES, candidate["ticker"]
        assert group_for_status(status) == "QUALIFIED_GROUP"
        assert candidate["primary_exclusion_reason"] is None
        assert candidate["rank"] >= 1
    for candidate in excluded:
        status = candidate["advice"]["status"]
        assert status in EXCLUDED_STATUSES, candidate["ticker"]
        assert status not in QUALIFIED_STATUSES, candidate["ticker"]
        assert group_for_status(status) == "EXCLUDED_GROUP"
        # A closed verdict names the FIRST closed gate of the canonical order.
        primary = candidate["primary_exclusion_reason"]
        assert primary is not None, candidate["ticker"]
        first_block = next(
            gate for gate in candidate["gates"] if gate["status"] == "BLOCK"
        )
        assert primary == {
            "gate_id": first_block["gate_id"],
            "reason_code": first_block["reason_code"],
        }
        # (JSONB does not preserve key order: the SET of checked evidence is
        # the contract, and every manifest entry must really be checked.)
        assert set(candidate["required_evidence"]) == set(required)

    # The two groups PARTITION the declared universe: no ticker in both,
    # none missing, none invented.
    qualified_tickers = [candidate["ticker"] for candidate in qualified]
    excluded_tickers = [candidate["ticker"] for candidate in excluded]
    assert set(qualified_tickers).isdisjoint(excluded_tickers)
    assert sorted(qualified_tickers + excluded_tickers) == sorted(UNIVERSE)
    assert coverage["universe_size"] == len(UNIVERSE) == 24
    assert coverage["qualified_count"] == len(qualified)
    assert coverage["excluded_count"] == len(excluded)
    assert (
        coverage["qualified_count"] + coverage["excluded_count"]
        == coverage["universe_size"]
    )
    assert sum(coverage["status_counts"].values()) == coverage["universe_size"]
    for status, count in coverage["status_counts"].items():
        assert group_for_status(status) in ("QUALIFIED_GROUP", "EXCLUDED_GROUP")
        assert count == sum(
            1
            for candidate in (*qualified, *excluded)
            if candidate["advice"]["status"] == status
        )

    # On the synthetic population the HONEST outcome is a fully closed
    # universe — the qualified group is empty, and nothing is forced open.
    assert coverage["status_counts"] == {"INSUFFICIENT_DATA": 24}
    assert qualified == []

    # -- 3. the exclusion-reason distribution is coherent -------------------
    reasons = content["exclusion_reasons"]
    assert reasons  # published, never silently empty while candidates are out
    assert sum(reasons.values()) == len(excluded) == coverage["excluded_count"]
    recomputed: dict[str, int] = {}
    for candidate in excluded:
        primary = candidate["primary_exclusion_reason"]
        key = f"{primary['gate_id']}:{primary['reason_code']}"
        recomputed[key] = recomputed.get(key, 0) + 1
    assert reasons == recomputed
    assert reasons == {"entitlements_sufficient:UNEVALUABLE": 24}

    # The four instruments really carrying bars keep an HONEST evidence map:
    # what the worker holds is present, what nobody holds stays absent.
    by_ticker = {candidate["ticker"]: candidate for candidate in excluded}
    for ticker in SYNTHETIC_FOCUS_TICKERS:
        evidence = by_ticker[ticker]["required_evidence"]
        assert evidence["price_volume"]["present"] is True
        assert evidence["sector"]["present"] is True
        assert evidence["regime"]["present"] is False
        assert evidence["fundamentals"]["present"] is False
        assert evidence["manual_portfolio_fit"]["present"] is False
        # No calendar snapshot was published: catalysts are honestly absent.
        assert evidence["catalysts"]["present"] is False
        assert by_ticker[ticker]["bars_status"] == "OK"
    # A ticker without bars is not repaired with a default series.
    assert by_ticker["SYN-UTIL-04"]["bars_status"] == "ABSENT"
    assert (
        by_ticker["SYN-UTIL-04"]["required_evidence"]["price_volume"]["present"]
        is False
    )

    # -- 4. documented ordering, stable and never an opaque score -----------
    assert content["ordering"]["method"] == "lexicographic"
    assert tuple(content["ordering"]["keys"]) == QUALIFIED_ORDERING_KEYS
    assert excluded_tickers == sorted(excluded_tickers)
    assert [candidate["rank"] for candidate in qualified] == list(
        range(1, len(qualified) + 1)
    )

    # Identical drain: publish-if-changed republishes NOTHING.
    first_version, first_hash = snapshot.version, snapshot.content_hash
    with session_factory() as session:
        enqueue_outbox(
            session, TOPIC_OPPORTUNITIES_REFRESH, _refresh_message("replay")
        )
        session.commit()
    replay_runner = make_runner(session_factory, clock)
    assert replay_runner.drain(max_batches=5) == 1
    with session_factory() as session:
        replayed = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_OPPORTUNITIES, key=SNAPSHOT_KEY_GLOBAL
        )
    assert replayed is not None
    assert replayed.version == first_version
    assert replayed.content_hash == first_hash
    assert replayed.content == content

    # Later clock: a new version whose ORDERING is identical.
    clock.now = NOW + timedelta(minutes=5)
    with session_factory() as session:
        enqueue_outbox(
            session, TOPIC_OPPORTUNITIES_REFRESH, _refresh_message("tick")
        )
        session.commit()
    later_runner = make_runner(session_factory, clock)
    assert later_runner.drain(max_batches=5) == 1
    with session_factory() as session:
        later = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_OPPORTUNITIES, key=SNAPSHOT_KEY_GLOBAL
        )
    assert later is not None
    assert later.version == first_version + 1
    assert later.content["as_of"] == clock.now.isoformat()
    assert [c["ticker"] for c in later.content["qualified"]] == qualified_tickers
    assert [c["ticker"] for c in later.content["excluded"]] == excluded_tickers
    assert later.content["exclusion_reasons"] == reasons
    assert later.content["coverage"]["status_counts"] == coverage["status_counts"]
