"""E2E seeding: real migrations + SYNTHETIC envelopes through the real worker.

Reads the throwaway test DSN from ``VERTEX_TEST_DATABASE_URL`` (environment
only — the DSN is NEVER stored in a file). Steps, all through the existing
production modules (nothing is reimplemented here):

1. drop/recreate the ``public`` schema and run ``alembic upgrade head``;
2. ingest 60 deterministic SYNTHETIC envelopes (``vertex_core.synthetic``)
   via ``vertex_worker.ingest.ingest_envelope`` (idempotent + outbox);
   60 rather than "~40" because the deterministic generator needs ~60 raw
   envelopes (duplicates included) to publish 8..15 attention items;
2 ter. ingest the 12 SYNTHETIC option-chain-slice envelopes (4 underlyings x
   3 slices, one near expiration under TWO trading classes) and the 4
   SYNTHETIC daily-bars envelopes (60 OHLCV bars per focus ticker) — the
   ingestion path itself enqueues ``option_chains.ingested`` and
   ``analysis.ingested``;
3. insert a handful of DEMO capability-probe observations (labeled rights
   ``DEMO``) and enqueue ``capabilities.refresh``;
4. drain the real ``WorkerRunner`` (bounded) so every snapshot is published;
5. verify the REALLY published snapshots: attention (8..15 SYNTHETIC items),
   markets, one ``option_chain/{u}`` per declared underlying (never-merged
   groups, SYNTHETIC population) and one ``analysis/{i}`` per focus ticker
   (60 bars, advice present) — anything else fails the setup loudly.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    generate_daily_bar_envelopes,
    generate_daily_quote_envelopes,
    generate_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import (
    DEV_SYNTHETIC_CONFIG,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_ATTENTION,
    SNAPSHOT_KIND_CAPABILITIES,
    TOPIC_CAPABILITIES_REFRESH,
    build_registry,
)
from vertex_worker.analysis import SNAPSHOT_KIND_ANALYSIS
from vertex_worker.ingest import ingest_envelope
from vertex_worker.markets import SNAPSHOT_KIND_MARKETS
from vertex_worker.options import SNAPSHOT_KIND_OPTION_CHAIN
from vertex_worker.runner import WorkerRunner

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _REPO_ROOT / "packages" / "python" / "vertex_persistence" / "alembic.ini"

SEED = 1234
ENVELOPE_COUNT = 60

# Real manifest capability ids probed with varied statuses so the /system
# matrix shows the full badge range; the rest honestly stays NEVER_TESTED.
PROBED_CAPABILITIES = [
    ("option_chain_definition", "AVAILABLE", None),
    ("underlying_top_of_book", "DELAYED", "DELAYED_ENTITLEMENT_ONLY"),
    ("option_computations_live", "NOT_ENTITLED", "NO_LIVE_OPTION_SUBSCRIPTION"),
    ("live_option_tick_by_tick", "UNSUPPORTED", "NOT_PROVIDED_BY_TWS_API"),
    ("underlying_historical_volatility_30d", "MANUAL_EXPORT", "EXPORT_ONLY"),
]


def main() -> int:
    url = os.environ.get("VERTEX_TEST_DATABASE_URL")
    if not url:
        print(
            "VERTEX_TEST_DATABASE_URL is not set (throwaway test database DSN, "
            "environment only — never stored in a file). Aborting.",
            file=sys.stderr,
        )
        return 2

    now = datetime.now(timezone.utc)

    # 1. Fresh schema + real migrations (owned by vertex_persistence).
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        admin.dispose()
    alembic_config = Config(str(_ALEMBIC_INI))
    alembic_config.attributes["sqlalchemy_url"] = url
    command.upgrade(alembic_config, "head")

    engine = create_engine(url)
    try:
        # 2. SYNTHETIC envelopes through the real ingestion path.
        envelopes = generate_envelopes(
            seed=SEED, count=ENVELOPE_COUNT, base_time=now - timedelta(minutes=5)
        )
        with Session(engine) as session:
            inserted = sum(
                1 for e in envelopes if ingest_envelope(session, e).inserted
            )
            session.commit()

        # 2 bis. Quotes journalières SYNTHETIC pour la page Marchés (LOT-13) :
        # 24 tickers / 6 secteurs, 2 clôtures, 2 tickers volontairement privés
        # de leur clôture ancienne (chemin « écarté, jamais interpolé »).
        quote_envelopes = generate_daily_quote_envelopes(
            seed=SEED, base_time=now - timedelta(minutes=5)
        )
        with Session(engine) as session:
            quotes_inserted = sum(
                1 for e in quote_envelopes if ingest_envelope(session, e).inserted
            )
            session.commit()

        # 2 ter. Chaînes d'options + barres journalières SYNTHETIC (LOT V3) :
        # 12 tranches de chaîne (4 sous-jacents x 3, dont UNE expiration sous
        # DEUX trading_class distinctes) et 4 séries de 60 barres OHLCV.
        # L'ingestion enqueue elle-même ``option_chains.ingested`` et
        # ``analysis.ingested`` — rien n'est réimplémenté ici.
        chain_envelopes = generate_option_chain_envelopes(
            seed=SEED, base_time=now - timedelta(minutes=5)
        )
        bar_envelopes = generate_daily_bar_envelopes(
            seed=SEED, base_time=now - timedelta(minutes=5)
        )
        with Session(engine) as session:
            chains_inserted = sum(
                1 for e in chain_envelopes if ingest_envelope(session, e).inserted
            )
            bars_inserted = sum(
                1 for e in bar_envelopes if ingest_envelope(session, e).inserted
            )
            session.commit()

        # 3. DEMO capability probe + refresh job. UNE seule observation par
        # source : le snapshot capacités ne retient que la DERNIÈRE sonde de
        # chaque source, donc toutes les capacités sondées vivent dans le même
        # payload ``fields``.
        probe_time = now - timedelta(minutes=10)
        with Session(engine) as session:
            insert_observation(
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
                            "capability_id": capability_id,
                            "field": "status",
                            "status": status,
                            "reason_code": reason_code,
                        }
                        for capability_id, status, reason_code in PROBED_CAPABILITIES
                    ],
                },
            )
            enqueue_outbox(session, TOPIC_CAPABILITIES_REFRESH, {"reason": "e2e-setup"})
            session.commit()

        # 4. Bounded drain of the REAL worker (real clock).
        def clock() -> datetime:
            return datetime.now(timezone.utc)

        registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
        runner = WorkerRunner(
            session_factory=lambda: Session(engine),
            registry=registry,
            poll_interval_seconds=0.05,
            clock=clock,
        )
        processed = runner.drain(max_batches=50)
        stats = runner.stats()
        if stats.failed or stats.dead or stats.lease_lost:
            print(f"worker drain reported failures: {stats}", file=sys.stderr)
            return 1

        # 5. Verify what was REALLY published.
        with Session(engine) as session:
            attention = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL
            )
            capabilities = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_CAPABILITIES, key=SNAPSHOT_KEY_GLOBAL
            )
            markets = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_MARKETS, key=SNAPSHOT_KEY_GLOBAL
            )
        if attention is None or capabilities is None or markets is None:
            print("expected all three snapshots to be published", file=sys.stderr)
            return 1
        markets_coverage = markets.content["coverage"]
        if (
            markets.content["population"] != "SYNTHETIC"
            or markets_coverage["expected"] != 24
            or markets_coverage["covered"] != 22
            or markets_coverage["discarded"] != 2
            or markets.content["breadth"]["status"] != "OK"
        ):
            print(
                f"unexpected markets snapshot: coverage={markets_coverage} "
                f"population={markets.content['population']}",
                file=sys.stderr,
            )
            return 1
        items = attention.content["items"]
        if not 8 <= len(items) <= 15:
            print(
                f"published attention items = {len(items)}, expected 8..15",
                file=sys.stderr,
            )
            return 1
        if attention.content["population"] != "SYNTHETIC":
            print("population must be SYNTHETIC in the E2E pipeline", file=sys.stderr)
            return 1

        # 5 bis. Option chains: one snapshot per declared focus underlying,
        # SYNTHETIC population, 3 never-merged (expiration, trading_class)
        # groups of which TWO share the same near expiration date.
        chain_versions: dict[str, int] = {}
        analysis_versions: dict[str, int] = {}
        with Session(engine) as session:
            for underlying in SYNTHETIC_FOCUS_TICKERS:
                chain = get_current_snapshot(
                    session, kind=SNAPSHOT_KIND_OPTION_CHAIN, key=underlying
                )
                if chain is None:
                    print(f"option_chain/{underlying} not published", file=sys.stderr)
                    return 1
                content = chain.content
                groups = content["expirations"]
                group_keys = [
                    (group["expiration"], group["trading_class"]) for group in groups
                ]
                expirations_seen = [key[0] for key in group_keys]
                if (
                    content["population"] != "SYNTHETIC"
                    or len(groups) != 3
                    or len(set(group_keys)) != 3
                    or len(set(expirations_seen)) != 2
                ):
                    print(
                        f"unexpected option_chain/{underlying}: "
                        f"population={content['population']} groups={group_keys}",
                        file=sys.stderr,
                    )
                    return 1
                chain_versions[underlying] = chain.version
                analysis = get_current_snapshot(
                    session, kind=SNAPSHOT_KIND_ANALYSIS, key=underlying
                )
                if analysis is None:
                    print(f"analysis/{underlying} not published", file=sys.stderr)
                    return 1
                dossier = analysis.content
                if (
                    dossier["population"] != "SYNTHETIC"
                    or dossier["bars"]["count"] != 60
                    or not isinstance(dossier.get("advice"), dict)
                    or "status" not in dossier["advice"]
                ):
                    print(
                        f"unexpected analysis/{underlying}: "
                        f"population={dossier['population']} "
                        f"bars={dossier['bars']['count']}",
                        file=sys.stderr,
                    )
                    return 1
                analysis_versions[underlying] = analysis.version

        print(
            "seed ok: "
            f"envelopes={len(envelopes)} inserted={inserted} "
            f"quotes={len(quote_envelopes)} quotes_inserted={quotes_inserted} "
            f"processed={processed} "
            f"attention_items={len(items)} attention_version={attention.version} "
            f"capabilities_version={capabilities.version} "
            f"markets_version={markets.version} "
            f"markets_covered={markets_coverage['covered']}/{markets_coverage['expected']} "
            f"chains={len(chain_envelopes)} chains_inserted={chains_inserted} "
            f"bars_envelopes={len(bar_envelopes)} bars_inserted={bars_inserted} "
            f"chain_versions={chain_versions} analysis_versions={analysis_versions}"
        )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
