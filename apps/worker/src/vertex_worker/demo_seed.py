"""Population de DÉMONSTRATION : propriétaire unique du semis SYNTHETIC.

Ce module existe parce que la séquence qu'il contient était le seul chemin
prouvé qui amène Vertex à un état affichable — et elle vivait dans
l'échafaudage de test (`apps/web/e2e/seed_synthetic.py`), branchée sur
``VERTEX_TEST_DATABASE_URL`` et précédée d'un ``DROP SCHEMA``. Autrement dit :
le produit démarrait 402 fois par jour en CI et **pas une seule fois pour son
utilisateur**.

Deux appelants, une seule vérité :

* ``tools/bootstrap_local.py`` — premier démarrage local, sur
  ``VERTEX_DATABASE_URL``, **sans jamais détruire le schéma** ;
* ``apps/web/e2e/seed_synthetic.py`` — campagne E2E, qui garde ce qui lui
  appartient : la base jetable, le schéma recréé et ses assertions.

CE QUE CE MODULE N'EST PAS. Ce n'est pas une source de données. Tout ce qu'il
écrit vient de ``vertex_core.synthetic`` et porte ``population = "SYNTHETIC"``
jusqu'à l'écran ; les écritures de journal et les thèses portent un préfixe
``[SYNTHETIC]`` lisible. Rien ici ne peut être présenté comme réel, et rien
ici ne contacte IBKR, TradingView ou quelque source que ce soit.

Rien n'est réimplémenté : les enveloppes passent par
``vertex_worker.ingest.ingest_envelope`` (idempotent + outbox), le journal et
les thèses par les repositories de production, et la publication par le vrai
``WorkerRunner``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, NamedTuple

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from vertex_core.synthetic import (
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
    generate_daily_quote_envelopes,
    generate_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.repository.ledger import create_portfolio, record_ledger_event
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.theses import create_thesis
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, TOPIC_CAPABILITIES_REFRESH, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

__all__ = [
    "ENVELOPE_COUNT",
    "PROBED_CAPABILITIES",
    "SEED",
    "DemoSeedReport",
    "drain_published_snapshots",
    "seed_demo_population",
]

#: Graine du générateur déterministe. Deux semis de la même graine produisent
#: exactement la même population : c'est ce qui rend la démonstration
#: reproductible et les captures comparables.
SEED = 1234

#: 60 enveloppes brutes (doublons compris) sont nécessaires pour que le
#: générateur déterministe publie 8 à 15 items d'attention.
ENVELOPE_COUNT = 60

#: Capacités RÉELLES du manifeste, sondées avec des statuts variés pour que la
#: matrice `/system` montre toute la gamme de badges. Le reste reste
#: honnêtement `NEVER_TESTED` — une capacité non sondée n'est pas une capacité
#: disponible.
PROBED_CAPABILITIES = [
    ("option_chain_definition", "AVAILABLE", None),
    ("underlying_top_of_book", "DELAYED", "DELAYED_ENTITLEMENT_ONLY"),
    ("option_computations_live", "NOT_ENTITLED", "NO_LIVE_OPTION_SUBSCRIPTION"),
    ("live_option_tick_by_tick", "UNSUPPORTED", "NOT_PROVIDED_BY_TWS_API"),
    ("underlying_historical_volatility_30d", "MANUAL_EXPORT", "EXPORT_ONLY"),
]


class DemoSeedReport(NamedTuple):
    """Ce que le semis a RÉELLEMENT inséré, pour être reporté, pas supposé."""

    envelopes: int
    quotes: int
    chains: int
    bars: int
    calendar: int
    portfolio_id: int


def seed_demo_population(
    engine: Engine, *, now: datetime, reason: str = "demo-seed"
) -> DemoSeedReport:
    """Écrit la population SYNTHETIC de démonstration et met en file ses jobs.

    Ne touche NI au schéma NI aux migrations : l'appelant en est responsable.
    L'ingestion étant idempotente par identifiant d'enveloppe, un second appel
    avec le même ``now`` n'insère rien de plus.
    """
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
    # into READABLE ``previous_values`` — le chemin de révision est donc
    # RÉELLEMENT exercé, au lieu d'afficher une liste toujours vide.
    # A distinct seed only avoids an envelope-id collision with the
    # current generation (ingestion is idempotent by envelope id); the
    # earnings stable ids do NOT depend on the seed.
    superseded_envelopes = tuple(
        envelope
        for envelope in generate_calendar_event_envelopes(
            seed=SEED + 1, base_time=now - timedelta(minutes=5, days=1)
        )
        # `source_event_id` est optionnel au contrat : une enveloppe sans
        # identifiant stable ne peut PAS être une révision de celle-ci.
        if (envelope.source_event_id or "").startswith("syn-ev-earnings-")
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

        def record(offset: timedelta, **kwargs: Any) -> int:
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
            note="[SYNTHETIC] depot initial declare (demonstration)",
        )
        record(
            timedelta(minutes=-60),
            kind="BUY_RECORDED",
            amount=Decimal("-1750"),
            fees=Decimal("1"),
            instrument={"ticker": "SYN-TECH-01"},
            quantity=Decimal("10"),
            price=Decimal("175.00"),
            note="[SYNTHETIC] achat enregistre apres coup (demonstration)",
        )
        record(
            timedelta(minutes=-45),
            kind="BUY_RECORDED",
            amount=Decimal("-550"),
            fees=Decimal("0"),
            instrument={"ticker": "SYN-FINL-01"},
            quantity=Decimal("5"),
            price=Decimal("110.00"),
            note="[SYNTHETIC] achat enregistre apres coup (demonstration)",
        )
        # Jour 2 (clôtures synthétiques D2) — dépôt puis vente partielle.
        day2 = latest_published - older_published
        record(
            day2 + timedelta(minutes=-60),
            kind="DEPOSIT",
            amount=Decimal("1000"),
            fees=Decimal("0"),
            note="[SYNTHETIC] second depot declare (demonstration)",
        )
        record(
            day2 + timedelta(minutes=-30),
            kind="SELL_RECORDED",
            amount=Decimal("686"),
            fees=Decimal("0"),
            instrument={"ticker": "SYN-TECH-01"},
            quantity=Decimal("4"),
            price=Decimal("171.50"),
            note="[SYNTHETIC] vente enregistree apres coup (demonstration)",
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
            idempotency_key=f"{reason}-thesis-due",
            now=now - timedelta(hours=6),
            instrument={"ticker": "SYN7"},
            horizon="3 mois",
            review_due_at=now - timedelta(days=2),
            note="[SYNTHETIC] population de demonstration",
        )
        create_thesis(
            session,
            title="[SYNTHETIC] These sans echeance",
            hypotheses="[SYNTHETIC] Autre hypothese de demonstration.",
            invalidation="[SYNTHETIC] Invalidee si X survient.",
            idempotency_key=f"{reason}-thesis-quiet",
            now=now - timedelta(hours=6),
        )

        # Refresh jobs — mêmes topics/payloads que l'API en production.
        enqueue_outbox(session, "portfolio.valuation.refresh", {"portfolio_id": portfolio_id})
        enqueue_outbox(session, "performance.refresh", {"portfolio_id": portfolio_id})
        enqueue_outbox(session, "review_queue.refresh", {"reason": reason})
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
        enqueue_outbox(session, TOPIC_CAPABILITIES_REFRESH, {"reason": reason})
        session.commit()


    return DemoSeedReport(
        envelopes=inserted,
        quotes=quotes_inserted,
        chains=chains_inserted,
        bars=bars_inserted,
        calendar=calendar_inserted,
        portfolio_id=portfolio_id,
    )


def drain_published_snapshots(engine: Engine, *, max_batches: int = 50) -> int:
    """Draine le VRAI worker jusqu'à publication, sur l'horloge réelle.

    Rend le nombre de messages traités. Lève ``RuntimeError`` si le drain a
    échoué, tué un message ou perdu un bail : un semis à moitié publié laisse
    des pages vides sans le dire, ce qui est exactement le contraire de ce que
    ce module sert.
    """

    def clock() -> datetime:
        return datetime.now(UTC)

    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    runner = WorkerRunner(
        session_factory=lambda: Session(engine),
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )
    processed = runner.drain(max_batches=max_batches)
    stats = runner.stats()
    if stats.failed or stats.dead or stats.lease_lost:
        raise RuntimeError(f"le drain du worker a signalé des échecs : {stats}")
    return processed
