"""Chaîne Risques, de bout en bout contre PostgreSQL réel.

Barres quotidiennes synthétiques → ``ingest_envelope`` → passe bornée du VRAI
worker → instantané ``risk_matrix/global`` relu par le dépôt.

CE QUE CE TEST PROTÈGE, ET QUE LES TESTS UNITAIRES NE PEUVENT PAS VOIR.

Un constructeur de contenu peut être parfait sans qu'aucun message ne
l'atteigne jamais. C'est le défaut le plus courant de ce dépôt — quelque chose
déclaré à un endroit et jamais branché à un autre — et il s'est produit deux
fois aujourd'hui sur ce même chantier :

- ``matrix_bands`` validé côté API et absent du chemin nominal du worker ;
- le registre de développement visant des tickers SANS barres, donc une page
  refusée sur une base pourtant semée.

Ici, rien n'est appelé directement : le message passe par la file d'attente,
le worker le réclame, et le handler doit avoir été enregistré pour que
l'instantané existe. Un câblage manquant fait rougir ce test, pas la
production.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from vertex_core.synthetic import SYNTHETIC_FOCUS_TICKERS, generate_daily_bar_envelopes
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.risk import (
    DEV_SYNTHETIC_RISK_CONFIG,
    RISK_SCHEMA_VERSION,
    SNAPSHOT_KIND_RISK,
    TOPIC_RISK_MATRIX_REFRESH,
)
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
    registry = build_registry(
        clock=clock,
        fusion_config=DEV_SYNTHETIC_CONFIG,
        risk_config=DEV_SYNTHETIC_RISK_CONFIG,
    )
    # Le câblage, vérifié AVANT de drainer : sans ce sujet enregistré, le
    # message mourrait sans réclamant et le test échouerait plus loin sur un
    # symptôme au lieu de sa cause.
    assert TOPIC_RISK_MATRIX_REFRESH in registry.topics
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def seed_bars(session_factory) -> int:
    envelopes = generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    with session_factory() as session:
        inserted = sum(1 for e in envelopes if ingest_envelope(session, e).inserted)
        session.commit()
    return inserted


def test_risk_chain_end_to_end(session_factory) -> None:
    inserted = seed_bars(session_factory)
    assert inserted == len(SYNTHETIC_FOCUS_TICKERS)

    with session_factory() as session:
        enqueue_outbox(session, TOPIC_RISK_MATRIX_REFRESH, {"reason": "test"})
        session.commit()

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
            session, kind=SNAPSHOT_KIND_RISK, key="global"
        )
    assert snapshot is not None
    content = snapshot.content

    assert content["schema_version"] == RISK_SCHEMA_VERSION
    assert content["engine_version"] == ENGINE_VERSION
    # Les barres semées portent les droits synthétiques : l'aveu doit le dire.
    assert content["population"] == "SYNTHETIC"

    tickers = [entry["ticker"] for entry in content["instruments"]]
    assert tickers == list(SYNTHETIC_FOCUS_TICKERS)

    # La matrice EST carrée et sa diagonale est exacte.
    taille = len(SYNTHETIC_FOCUS_TICKERS)
    assert len(content["matrix"]) == taille
    for index, ligne in enumerate(content["matrix"]):
        assert len(ligne) == taille
        assert ligne[index] == "1.000"

    # Les bandes suivent la matrice, et la diagonale se NOMME.
    assert len(content["matrix_bands"]) == taille
    for index, ligne in enumerate(content["matrix_bands"]):
        assert len(ligne) == taille
        assert ligne[index] == "self"


def test_le_perimetre_de_dev_vise_des_tickers_qui_ONT_des_barres(
    session_factory,
) -> None:
    """Le défaut exact trouvé le 2026-09-01, épinglé.

    ``DEV_SYNTHETIC_RISK_CONFIG`` visait d'abord six tickers pris au début du
    premier secteur. Or seuls les quatre ``SYNTHETIC_FOCUS_TICKERS`` portent
    des barres quotidiennes. Le registre pointait donc vers des instruments
    sans données : la page aurait refusé « aucune barre » sur une base
    pourtant complète, et rien n'aurait dit pourquoi.
    """
    seed_bars(session_factory)
    with session_factory() as session:
        enqueue_outbox(session, TOPIC_RISK_MATRIX_REFRESH, {"reason": "test"})
        session.commit()

    runner = make_runner(session_factory, MutableClock(NOW))
    runner.drain(max_batches=20)

    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_RISK, key="global"
        )
    assert snapshot is not None
    couverture = snapshot.content["coverage"]
    # AUCUN écart, AUCUN refus : chaque instrument déclaré a ses barres.
    assert couverture["discarded"] == []
    assert couverture["refusal_reason"] is None
    assert couverture["retained_count"] == couverture["perimeter_size"]


def test_republication_sans_barre_nouvelle_ne_change_rien(session_factory) -> None:
    """Publish-if-changed : deux passes identiques, une seule version.

    La matrice dépend des CLÔTURES. Rejouer le même message sans nouvelle
    barre ne doit pas produire une version de plus — sinon chaque
    rafraîchissement gonflerait l'historique sans rien apprendre.
    """
    seed_bars(session_factory)
    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)

    with session_factory() as session:
        enqueue_outbox(session, TOPIC_RISK_MATRIX_REFRESH, {"reason": "un"})
        session.commit()
    runner.drain(max_batches=20)
    with session_factory() as session:
        premiere = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_RISK, key="global"
        )
    assert premiere is not None

    # MÊME horloge : `as_of` ne bouge pas, donc le contenu est identique au
    # bit près et la publication doit être un non-événement.
    with session_factory() as session:
        enqueue_outbox(session, TOPIC_RISK_MATRIX_REFRESH, {"reason": "deux"})
        session.commit()
    runner.drain(max_batches=20)
    with session_factory() as session:
        seconde = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_RISK, key="global"
        )
    assert seconde is not None
    assert seconde.version == premiere.version


def test_sans_aucune_barre_le_refus_est_nomme(session_factory) -> None:
    """Une base vide produit un refus MOTIVÉ, pas un instantané absent.

    L'écran doit pouvoir dire « moins de deux instruments ont des barres »
    plutôt que rester blanc comme après une panne.
    """
    with session_factory() as session:
        enqueue_outbox(session, TOPIC_RISK_MATRIX_REFRESH, {"reason": "vide"})
        session.commit()

    runner = make_runner(session_factory, MutableClock(NOW))
    runner.drain(max_batches=20)

    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_RISK, key="global"
        )
    assert snapshot is not None  # publié QUAND MÊME : le refus est une réponse
    content = snapshot.content
    assert content["population"] == "EMPTY"
    assert content["coverage"]["refusal_reason"] == "perimeter_too_small"
    assert content["matrix"] == []
    assert content["conclusion"]
