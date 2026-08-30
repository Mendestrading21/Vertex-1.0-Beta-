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
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from vertex_core.synthetic import SYNTHETIC_FOCUS_TICKERS
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.analysis import SNAPSHOT_KIND_ANALYSIS
from vertex_worker.demo_seed import drain_published_snapshots, seed_demo_population
from vertex_worker.handlers import (
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_ATTENTION,
    SNAPSHOT_KIND_CAPABILITIES,
)
from vertex_worker.markets import SNAPSHOT_KIND_MARKETS
from vertex_worker.options import SNAPSHOT_KIND_OPTION_CHAIN

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _REPO_ROOT / "packages" / "python" / "vertex_persistence" / "alembic.ini"



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
        # 2. Population SYNTHETIC de démonstration, par le PROPRIÉTAIRE
        #    UNIQUE de ce semis (`vertex_worker.demo_seed`). Ce code vivait
        #    ici, dans l'échafaudage de test : le produit démarrait donc en
        #    CI et jamais pour son utilisateur. `tools/bootstrap_local.py`
        #    appelle exactement les mêmes fonctions.
        report = seed_demo_population(engine, now=now, reason="e2e-seed")
        inserted = report.envelopes
        quotes_inserted = report.quotes
        chains_inserted = report.chains
        bars_inserted = report.bars
        calendar_inserted = report.calendar
        portfolio_id = report.portfolio_id

        # 3. Drain borné du VRAI worker (horloge réelle).
        try:
            processed = drain_published_snapshots(engine)
        except RuntimeError as erreur:
            print(str(erreur), file=sys.stderr)
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
            f"inserted={inserted} quotes_inserted={quotes_inserted} "
            f"processed={processed} "
            f"attention_items={len(items)} attention_version={attention.version} "
            f"capabilities_version={capabilities.version} "
            f"markets_version={markets.version} "
            f"markets_covered={markets_coverage['covered']}/{markets_coverage['expected']} "
            f"chains_inserted={chains_inserted} bars_inserted={bars_inserted} "
            f"chain_versions={chain_versions} analysis_versions={analysis_versions} "
            f"portfolio_id={portfolio_id} valuation_version={valuation.version} "
            f"performance_version={performance.version} "
            f"review_queue_version={review_queue.version} due_ids={due_ids} "
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
