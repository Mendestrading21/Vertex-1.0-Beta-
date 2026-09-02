"""La revalorisation repart d'un MOUVEMENT des cotes, pas d'une republication.

CE QUE CE TEST EMPECHE, ET CE QU'IL NE TOUCHE PAS.

`_enqueue_portfolio_revaluations` documente sa garde : « an unchanged snapshot
changes no mark and enqueues nothing […] a quote that does not move a
published close cannot move any valuation ». Cette garde ne s'est JAMAIS
fermee : `publish_if_changed` ne renvoie jamais `None`, puisque le contenu
porte `as_of` et que l'horodatage bouge a chaque recalcul.

MESURE SUR LA BASE LIVE (2026-09-01), portefeuille SANS aucune transaction :

  portfolio.valuation.refresh   16 946 messages
  performance.refresh           16 946 messages
  portfolio_valuation            3 075 versions
  performance                    3 075 versions

Ce test ne remet PAS en cause le versionnage de `markets_overview` : le test
voisin `test_markets_chain_end_to_end` affirme deliberement qu'un recalcul
ulterieur publie une nouvelle version — « as_of moves honestly ». On continue
donc de publier. Seule la cascade redevient conditionnelle, comme elle se
decrit elle-meme.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from vertex_core.synthetic import generate_daily_quote_envelopes
from vertex_persistence.models import OutboxMessage, Portfolio
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.markets import SNAPSHOT_KIND_MARKETS, TOPIC_QUOTES_INGESTED
from vertex_worker.performance import TOPIC_PERFORMANCE_REFRESH
from vertex_worker.portfolio import TOPIC_PORTFOLIO_VALUATION_REFRESH
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 424242


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    return WorkerRunner(
        session_factory=session_factory,
        registry=build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG),
        poll_interval_seconds=0.05,
        clock=clock,
    )


def _compter(session, topic: str) -> int:
    return int(
        session.execute(
            select(func.count()).select_from(OutboxMessage).where(OutboxMessage.topic == topic)
        ).scalar_one()
    )


def test_une_republication_sans_mouvement_n_enfile_aucune_revalorisation(
    session_factory,
) -> None:
    """Le défaut mesuré : 17 000 revalorisations d'un portefeuille vide."""
    with session_factory() as session:
        session.add(Portfolio(name="test", base_currency="USD"))
        for enveloppe in generate_daily_quote_envelopes(
            seed=SEED, base_time=BASE_TIME, missing_close_count=0
        ):
            ingest_envelope(session, enveloppe)
        session.commit()

    horloge = MutableClock(NOW)
    make_runner(session_factory, horloge).drain(max_batches=20)

    with session_factory() as session:
        premier_snapshot = get_current_snapshot(session, kind=SNAPSHOT_KIND_MARKETS, key="global")
        revalorisations = _compter(session, TOPIC_PORTFOLIO_VALUATION_REFRESH)
        performances = _compter(session, TOPIC_PERFORMANCE_REFRESH)
    assert premier_snapshot is not None
    assert revalorisations >= 1, "la première publication doit revaloriser"

    # -- même information, horloge avancée : rien n'a bougé côté cotes -------
    horloge.now = NOW + timedelta(minutes=5)
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_QUOTES_INGESTED,
            {
                "event_id": "tick",
                "source": "synthetic-dev",
                "schema_version": "synthetic-daily-quote/1.0",
            },
        )
        session.commit()
    make_runner(session_factory, horloge).drain(max_batches=5)

    with session_factory() as session:
        second_snapshot = get_current_snapshot(session, kind=SNAPSHOT_KIND_MARKETS, key="global")
        revalorisations_apres = _compter(session, TOPIC_PORTFOLIO_VALUATION_REFRESH)
        performances_apres = _compter(session, TOPIC_PERFORMANCE_REFRESH)

    assert second_snapshot is not None
    # Le versionnage reste INTACT : « as_of moves honestly ».
    assert second_snapshot.version == premier_snapshot.version + 1, (
        "la republication horodatée doit continuer de créer une version"
    )
    # Mais aucune cote n'a bougé : aucune revalorisation ne doit être enfilée.
    assert revalorisations_apres == revalorisations, (
        "une republication sans mouvement des cotes ne doit revaloriser aucun "
        "portefeuille — c'est ce que la garde documentée promet"
    )
    assert performances_apres == performances


def test_un_vrai_mouvement_de_cote_revalorise_toujours(session_factory) -> None:
    """La garde ne doit pas devenir un blocage : une cote qui bouge cascade."""
    with session_factory() as session:
        session.add(Portfolio(name="test", base_currency="USD"))
        enveloppes = generate_daily_quote_envelopes(
            seed=SEED, base_time=BASE_TIME, missing_close_count=0
        )
        for enveloppe in enveloppes[:-1]:
            ingest_envelope(session, enveloppe)
        session.commit()

    horloge = MutableClock(NOW)
    make_runner(session_factory, horloge).drain(max_batches=20)
    with session_factory() as session:
        avant = _compter(session, TOPIC_PORTFOLIO_VALUATION_REFRESH)

    # Une cotation de plus : le contenu publié change réellement.
    horloge.now = NOW + timedelta(minutes=5)
    with session_factory() as session:
        ingest_envelope(session, enveloppes[-1])
        session.commit()
    make_runner(session_factory, horloge).drain(max_batches=20)

    with session_factory() as session:
        apres = _compter(session, TOPIC_PORTFOLIO_VALUATION_REFRESH)
    assert apres > avant, "un mouvement réel des cotes doit revaloriser"
