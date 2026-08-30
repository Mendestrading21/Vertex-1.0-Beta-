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
from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
    generate_daily_quote_envelopes,
    generate_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.repository.ledger import create_portfolio, record_ledger_event
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_persistence.repository.theses import create_thesis
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

        # 2 quinquies. Calendar events SYNTHETIC (page 02) through the SAME
        # ingestion path: it enqueues ``calendar.ingested`` and, after it,
        # ``opportunities.refresh`` — so a drained outbox publishes the
        # calendar snapshot BEFORE the opportunities handler reads it as
        # catalyst provenance. Nothing is reimplemented here; the generator
        # already emits ESTIMATED and CONFIRMED-through-a-dated-revision
        # events, dividends, option expirations and global macro events.
        calendar_envelopes = generate_calendar_event_envelopes(
            seed=SEED, base_time=now - timedelta(minutes=5)
        )
        # An OLDER generation of the SAME earnings events (same stable ids
        # ``syn-ev-earnings-<ticker>``, one day earlier, hence an earlier
        # instant and an earlier ``as_of``). The calendar builder keeps the
        # most recent business knowledge and turns the ones it supersedes
        # into READABLE ``previous_values`` — the E2E therefore exercises the
        # real revision path instead of asserting an always-empty list.
        # A distinct seed only avoids an envelope-id collision with the
        # current generation (ingestion is idempotent by envelope id); the
        # earnings stable ids do NOT depend on the seed.
        superseded_envelopes = tuple(
            envelope
            for envelope in generate_calendar_event_envelopes(
                seed=SEED + 1, base_time=now - timedelta(minutes=5, days=1)
            )
            if envelope.source_event_id.startswith("syn-ev-earnings-")
        )
        with Session(engine) as session:
            calendar_inserted = sum(
                1
                for e in superseded_envelopes + calendar_envelopes
                if ingest_envelope(session, e).inserted
            )
            session.commit()

        # 2 quater. Portefeuille DÉMO (vague 4) : journal manuel SYNTHETIC —
        # 2 dépôts + 2 achats + 1 vente — et 2 thèses (dont 1 due, liée au
        # ticker SYN7 du flux d'attention pour que le contexte d'information
        # s'y attache). Tout passe par les repositories de production ; les
        # topics de refresh sont mis en file comme le ferait l'API.
        latest_published = (now - timedelta(minutes=5)) - timedelta(hours=2)
        older_published = latest_published - timedelta(hours=24)
        with Session(engine) as session:
            # Même identité que le get-or-create de l'API (« main », USD).
            portfolio_id = create_portfolio(session, name="main", base_currency="USD")

            def record(offset: timedelta, **kwargs) -> int:
                return record_ledger_event(
                    session,
                    portfolio_id=portfolio_id,
                    currency="SYN",
                    effective_at=older_published + offset,
                    recorded_at=now,
                    **kwargs,
                )

            # Jour 1 (clôtures synthétiques D1) — dépôt puis 2 achats.
            record(
                timedelta(minutes=-90),
                kind="DEPOSIT",
                amount=Decimal("10000"),
                fees=Decimal("0"),
                note="[SYNTHETIC] depot initial declare (demo E2E)",
            )
            record(
                timedelta(minutes=-60),
                kind="BUY_RECORDED",
                amount=Decimal("-1750"),
                fees=Decimal("1"),
                instrument={"ticker": "SYN-TECH-01"},
                quantity=Decimal("10"),
                price=Decimal("175.00"),
                note="[SYNTHETIC] achat enregistre apres coup (demo E2E)",
            )
            record(
                timedelta(minutes=-45),
                kind="BUY_RECORDED",
                amount=Decimal("-550"),
                fees=Decimal("0"),
                instrument={"ticker": "SYN-FINL-01"},
                quantity=Decimal("5"),
                price=Decimal("110.00"),
                note="[SYNTHETIC] achat enregistre apres coup (demo E2E)",
            )
            # Jour 2 (clôtures synthétiques D2) — dépôt puis vente partielle.
            day2 = latest_published - older_published
            record(
                day2 + timedelta(minutes=-60),
                kind="DEPOSIT",
                amount=Decimal("1000"),
                fees=Decimal("0"),
                note="[SYNTHETIC] second depot declare (demo E2E)",
            )
            record(
                day2 + timedelta(minutes=-30),
                kind="SELL_RECORDED",
                amount=Decimal("686"),
                fees=Decimal("0"),
                instrument={"ticker": "SYN-TECH-01"},
                quantity=Decimal("4"),
                price=Decimal("171.50"),
                note="[SYNTHETIC] vente enregistree apres coup (demo E2E)",
            )

            # 2 thèses DÉMO. La première suit un ticker du flux d'attention
            # synthétique (SYN7), est créée AVANT l'arrivée des observations
            # (now-6h) et son échéance est passée : elle est DUE et porte
            # « nouvelle information » (clusters reçus après la création).
            # La seconde n'a pas d'échéance : jamais due.
            create_thesis(
                session,
                title="[SYNTHETIC] These due - surveiller SYN7",
                hypotheses="[SYNTHETIC] Hypothese de demonstration E2E.",
                invalidation="[SYNTHETIC] Invalidee si la cloture synthetique retombe sous 90.",
                idempotency_key="e2e-seed-thesis-due",
                now=now - timedelta(hours=6),
                instrument={"ticker": "SYN7"},
                horizon="3 mois",
                review_due_at=now - timedelta(days=2),
                note="[SYNTHETIC] semee par e2e/seed_synthetic.py",
            )
            create_thesis(
                session,
                title="[SYNTHETIC] These sans echeance",
                hypotheses="[SYNTHETIC] Autre hypothese de demonstration.",
                invalidation="[SYNTHETIC] Invalidee si X survient.",
                idempotency_key="e2e-seed-thesis-quiet",
                now=now - timedelta(hours=6),
            )

            # Refresh jobs — mêmes topics/payloads que l'API en production.
            enqueue_outbox(session, "portfolio.valuation.refresh", {"portfolio_id": portfolio_id})
            enqueue_outbox(session, "performance.refresh", {"portfolio_id": portfolio_id})
            enqueue_outbox(session, "review_queue.refresh", {"reason": "e2e-seed"})
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

        # 5 ter. Vague 4 : valorisation, performance et file de revues
        # réellement publiées, populations honnêtes, métriques OK.
        with Session(engine) as session:
            valuation = get_current_snapshot(
                session, kind="portfolio_valuation", key=str(portfolio_id)
            )
            performance = get_current_snapshot(
                session, kind="performance", key=str(portfolio_id)
            )
            review_queue = get_current_snapshot(session, kind="review_queue", key="global")
        if valuation is None or performance is None or review_queue is None:
            print(
                "expected portfolio_valuation, performance and review_queue "
                "snapshots to be published",
                file=sys.stderr,
            )
            return 1
        vcontent = valuation.content
        vcoverage = vcontent["coverage"]
        if (
            vcontent["mark_population"] != "SYNTHETIC"
            or vcoverage["lots_open"] != 2
            or vcoverage["lots_valued"] != 2
            or vcoverage["lots_excluded"] != 0
        ):
            print(f"unexpected portfolio valuation: coverage={vcoverage}", file=sys.stderr)
            return 1
        pcontent = performance.content
        metric_status = {
            key: pcontent["metrics"][key]["status"] for key in pcontent["metrics"]
        }
        if (
            pcontent["population"] != "SYNTHETIC_MARKS_REAL_LEDGER"
            or pcontent["series"]["status"] != "OK"
            or len(pcontent["series"]["points"]) != 2
            or metric_status["twr_gross"] != "OK"
            or metric_status["xirr_gross"] != "OK"
            or metric_status["drawdown_gross"] != "OK"
        ):
            print(
                f"unexpected performance snapshot: series={pcontent['series']['status']} "
                f"points={len(pcontent['series']['points'])} metrics={metric_status}",
                file=sys.stderr,
            )
            return 1
        qcontent = review_queue.content
        due_ids = [entry["thesis_id"] for entry in qcontent["due"]]
        due_new_info = {
            entry["thesis_id"]: entry["has_new_information"] for entry in qcontent["due"]
        }
        if (
            qcontent["populations"]["theses"] != "USER_DECLARED"
            or qcontent["coverage"]["theses_total"] != 2
            or len(due_ids) != 1
            or due_new_info[due_ids[0]] is not True
        ):
            print(
                f"unexpected review queue: populations={qcontent['populations']} "
                f"coverage={qcontent['coverage']} due={qcontent['due']}",
                file=sys.stderr,
            )
            return 1

        # 5 quater. Vague finale : calendrier et opportunités RÉELLEMENT
        # publiés, états honnêtes, révisions conservées et provenance croisée.
        with Session(engine) as session:
            calendar = get_current_snapshot(session, kind="calendar", key="global")
            opportunities = get_current_snapshot(
                session, kind="opportunities", key="global"
            )
        if calendar is None or opportunities is None:
            print(
                "expected calendar and opportunities snapshots to be published",
                file=sys.stderr,
            )
            return 1
        ccontent = calendar.content
        agenda = ccontent["agenda"]
        revised_events = [event for event in agenda if event["revised"]]
        with_previous = [event for event in agenda if event["previous_values"]]
        statuses = ccontent["statuses"]
        if (
            ccontent["agenda_state"] != "OK"
            or ccontent["population"] != "SYNTHETIC"
            or ccontent["importance_rule"]["version"] != "importance_rule/1.1"
            or statuses.get("ESTIMATED", 0) < 1
            or statuses.get("CONFIRMED", 0) < 1
            or len(revised_events) < 1
            or len(with_previous) < 1
            or ccontent["coverage"]["events_superseded"] < 1
        ):
            print(
                f"unexpected calendar snapshot: state={ccontent['agenda_state']} "
                f"statuses={statuses} revised={len(revised_events)} "
                f"previous={len(with_previous)} "
                f"coverage={ccontent['coverage']}",
                file=sys.stderr,
            )
            return 1
        ocontent = opportunities.content
        ocoverage = ocontent["coverage"]
        if (
            ocontent["population"] != "SYNTHETIC"
            or ocontent["calendar_ref"]["status"] != "USED"
            or ocoverage["qualified_count"] != 0
            or ocoverage["excluded_count"] != ocoverage["universe_size"]
            or not ocontent["profile_ref"]["not_applied"]
        ):
            print(
                f"unexpected opportunities snapshot: coverage={ocoverage} "
                f"calendar_ref={ocontent['calendar_ref']}",
                file=sys.stderr,
            )
            return 1

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
            f"chain_versions={chain_versions} analysis_versions={analysis_versions} "
            f"portfolio_id={portfolio_id} valuation_version={valuation.version} "
            f"performance_version={performance.version} "
            f"review_queue_version={review_queue.version} due_ids={due_ids} "
            f"calendar_envelopes={len(calendar_envelopes)} "
            f"superseded_envelopes={len(superseded_envelopes)} "
            f"calendar_inserted={calendar_inserted} "
            f"calendar_version={calendar.version} "
            f"calendar_events={len(agenda)} calendar_statuses={statuses} "
            f"calendar_revised={len(revised_events)} "
            f"calendar_with_previous={len(with_previous)} "
            f"opportunities_version={opportunities.version} "
            f"opportunities_qualified={ocoverage['qualified_count']} "
            f"opportunities_excluded={ocoverage['excluded_count']} "
            f"opportunities_reasons={ocontent['exclusion_reasons']}"
        )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
