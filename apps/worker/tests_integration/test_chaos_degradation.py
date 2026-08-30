"""Campagne chaos LOT-23 : la chaîne réelle sous dégradation (PostgreSQL réel).

Les tests d'intégration existants prouvent le chemin nominal et quelques
chemins d'échec du worker. Ils ne prouvent pas ce que le programme promet de
plus important : **sous dégradation, rien ne devient QUALIFIED et rien de
périmé ne se fait passer pour frais**.

Chaque scénario ci-dessous introduit une dégradation réelle sur la base réelle,
puis vérifie l'invariant fail-closed correspondant. Aucun test n'affaiblit une
assertion pour passer : quand la dégradation ne peut pas être simulée
honnêtement (disque plein, perte de courant), le scénario est absent d'ici et
inscrit à `docs/99-status/DEBT.md` plutôt que mimé par un faux.

Toutes les données sont SYNTHETIC et déterministes (graine fixe, horloge
injectée). Aucune donnée IBKR ou TradingView réelle n'entre ici.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select

from vertex_core.synthetic import (
    generate_daily_bar_envelopes,
    generate_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import Observation, OutboxMessage, Snapshot
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.analysis import SNAPSHOT_KIND_ANALYSIS
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 909090

# Statuts qui affirment quelque chose de positif sur une opportunité. Aucune
# dégradation de cette campagne ne doit permettre de les atteindre.
STATUTS_AFFIRMATIFS = {"QUALIFIED", "REVIEW"}


class MutableClock:
    """Horloge injectée : les tests avancent le temps, jamais le système."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _runner(session_factory: Any, clock: MutableClock) -> WorkerRunner:
    return WorkerRunner(
        session_factory=session_factory,
        registry=build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG),
        poll_interval_seconds=0.05,
        clock=clock,
    )


def _ingest(session_factory: Any, envelopes: Any) -> int:
    with session_factory() as session:
        inserted = sum(1 for e in envelopes if ingest_envelope(session, e).inserted)
        session.commit()
    return inserted


def _current_as_of(session_factory: Any) -> dict[tuple[str, str], datetime]:
    """`as_of` de chaque snapshot COURANT, par (kind, key)."""
    instants: dict[tuple[str, str], datetime] = {}
    with session_factory() as session:
        couples = session.execute(select(Snapshot.kind, Snapshot.key).distinct()).all()
        for kind, key in couples:
            snapshot = get_current_snapshot(session, kind=kind, key=key)
            if snapshot is not None:
                instants[(kind, key)] = snapshot.as_of
    return instants


def _analysis_advices(session_factory: Any) -> list[dict[str, Any]]:
    """Tous les avis publiés dans les dossiers d'analyse courants."""
    advices: list[dict[str, Any]] = []
    with session_factory() as session:
        rows = session.execute(
            select(Snapshot.key).where(Snapshot.kind == SNAPSHOT_KIND_ANALYSIS).distinct()
        ).scalars()
        for key in rows:
            snapshot = get_current_snapshot(session, kind=SNAPSHOT_KIND_ANALYSIS, key=key)
            if snapshot is not None and "advice" in snapshot.content:
                advices.append(snapshot.content["advice"])
    return advices


# ── duplication ──────────────────────────────────────────────────────────────


def test_un_envelope_livre_deux_fois_ne_produit_qu_une_observation(
    session_factory: Any,
) -> None:
    """Une livraison en double est le cas normal d'un transport « au moins une
    fois ». Elle ne doit créer ni observation ni travail supplémentaires."""
    envelopes = generate_envelopes(seed=SEED, count=6, base_time=BASE_TIME)

    premier = _ingest(session_factory, envelopes)
    second = _ingest(session_factory, envelopes)

    assert premier > 0
    assert second == 0, "la seconde livraison a écrit des observations"

    with session_factory() as session:
        observations = session.execute(
            select(func.count()).select_from(Observation)
        ).scalar_one()
        jobs = session.execute(select(func.count()).select_from(OutboxMessage)).scalar_one()
    assert observations == premier
    # Le travail enfilé suit l'observation écrite, pas la livraison reçue.
    assert jobs > 0
    jobs_apres_replay = jobs

    _ingest(session_factory, envelopes)
    with session_factory() as session:
        assert (
            session.execute(select(func.count()).select_from(OutboxMessage)).scalar_one()
            == jobs_apres_replay
        )


def test_un_replay_complet_apres_traitement_ne_republie_pas_un_snapshot(
    session_factory: Any,
) -> None:
    """Rejouer toute l'ingestion après un drain complet ne doit pas créer une
    nouvelle révision : sinon un rejeu de transport réécrirait l'historique."""
    envelopes = (
        *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
    )
    _ingest(session_factory, envelopes)
    clock = MutableClock(NOW)
    _runner(session_factory, clock).drain(max_batches=30)

    with session_factory() as session:
        revisions_avant = session.execute(select(func.count()).select_from(Snapshot)).scalar_one()

    _ingest(session_factory, envelopes)
    _runner(session_factory, clock).drain(max_batches=30)

    with session_factory() as session:
        revisions_apres = session.execute(select(func.count()).select_from(Snapshot)).scalar_one()

    assert revisions_apres == revisions_avant


# ── désordre et régression temporelle ────────────────────────────────────────


def test_une_observation_plus_ancienne_arrivant_apres_ne_fait_pas_regresser_le_snapshot(
    session_factory: Any,
) -> None:
    """Le désordre réseau ne doit pas remonter le temps de l'interface."""
    recentes = generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    anciennes = generate_daily_bar_envelopes(
        seed=SEED + 1, base_time=BASE_TIME - timedelta(days=30)
    )

    _ingest(session_factory, recentes)
    clock = MutableClock(NOW)
    _runner(session_factory, clock).drain(max_batches=30)

    instants_avant = _current_as_of(session_factory)
    assert instants_avant, "le scénario n'a de sens que si des snapshots existaient"

    _ingest(session_factory, anciennes)
    _runner(session_factory, clock).drain(max_batches=30)

    apres = _current_as_of(session_factory)

    for cle, instant_avant in instants_avant.items():
        assert cle in apres, f"{cle} a disparu après l'arrivée d'une donnée plus ancienne"
        assert apres[cle] >= instant_avant, (
            f"{cle} a régressé de {instant_avant} à {apres[cle]} "
            "après l'arrivée d'une observation plus ancienne"
        )


# ── fraîcheur et dérive d'horloge ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("libelle", "avance"),
    [
        ("une_seconde_dans_le_futur", timedelta(seconds=1)),
        ("une_heure_dans_le_futur", timedelta(hours=1)),
        ("un_jour_dans_le_futur", timedelta(days=1)),
    ],
)
def test_une_horloge_qui_derive_ne_produit_jamais_un_avis_affirmatif(
    session_factory: Any, libelle: str, avance: timedelta
) -> None:
    """Si l'horloge du système recule par rapport aux données (ou, ce qui
    revient au même, si les données arrivent du futur), aucun avis affirmatif
    ne doit sortir. Un `observed_at` postérieur à l'instant de calcul n'est pas
    une donnée fraîche : c'est une incohérence."""
    envelopes = (
        *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
    )
    _ingest(session_factory, envelopes)

    # L'horloge du worker est placée AVANT les observations : de son point de
    # vue, elles viennent du futur.
    clock = MutableClock(BASE_TIME - avance)
    _runner(session_factory, clock).drain(max_batches=30)

    for advice in _analysis_advices(session_factory):
        assert advice["status"] not in STATUTS_AFFIRMATIFS, (
            f"{libelle} : un avis {advice['status']} a été produit "
            "alors que les observations sont postérieures à l'instant de calcul"
        )


@pytest.mark.parametrize("age", [timedelta(days=2), timedelta(days=30), timedelta(days=400)])
def test_une_population_perimee_ne_produit_jamais_un_avis_affirmatif(
    session_factory: Any, age: timedelta
) -> None:
    """Une donnée vieille reste une donnée : elle n'est jamais promue en
    verdict positif par le simple passage du temps.

    Deux issues sont légitimes et vérifiées ici :

    * un dossier est publié, et son avis n'est pas affirmatif ;
    * aucun dossier n'est publié, parce que la fenêtre bornée de barres
      (`AnalysisConfig.lookback`, 72 h) ne contient plus rien. C'est le cas
      au-delà de quelques jours. Le silence n'est acceptable que s'il est
      PROPRE : aucun message empoisonné, aucune tentative bloquée.

    L'issue interdite est la troisième : un dossier publié malgré une
    population hors fenêtre.
    """
    envelopes = (
        *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
    )
    _ingest(session_factory, envelopes)

    clock = MutableClock(NOW + age)
    runner = _runner(session_factory, clock)
    runner.drain(max_batches=30)

    for advice in _analysis_advices(session_factory):
        assert advice["status"] not in STATUTS_AFFIRMATIFS
        assert advice["direction"] in {"UNKNOWN", "NEUTRAL", "MIXED", "BULLISH", "BEARISH"}

    # Le silence doit être propre : rien d'empoisonné, rien de bloqué.
    stats = runner.stats()
    assert (stats.failed, stats.dead) == (0, 0), (
        "une population périmée ne doit pas empoisonner la file : "
        f"{stats.failed} échec(s), {stats.dead} mort(s)"
    )
    with session_factory() as session:
        bloques = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert bloques == 0


def test_le_vieillissement_d_un_dossier_n_est_pas_blanchi_par_une_activite_ulterieure(
    session_factory: Any,
) -> None:
    """L'invariant le plus dangereux de l'architecture par snapshots.

    Un dossier publié quand la donnée était fraîche reste le dossier COURANT
    quand la donnée vieillit. Ce qui serait inacceptable, c'est qu'une activité
    ultérieure sans rapport (d'autres observations, d'autres topics) rafraîchisse
    son `as_of` ou en publie une nouvelle version : l'ancienneté serait blanchie
    et un lecteur croirait le dossier récent.

    Ce test fige donc : un mois plus tard, après une ingestion réelle et un
    drain complet, chaque dossier d'analyse garde SA version et SON `as_of`.
    C'est ce qui permet à l'interface de juger la fraîcheur à la lecture.
    """
    _ingest(
        session_factory,
        (
            *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
            *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
        ),
    )
    _runner(session_factory, MutableClock(NOW)).drain(max_batches=30)

    with session_factory() as session:
        cles = list(
            session.execute(
                select(Snapshot.key).where(Snapshot.kind == SNAPSHOT_KIND_ANALYSIS).distinct()
            ).scalars()
        )
        avant = {}
        for cle in cles:
            snapshot = get_current_snapshot(session, kind=SNAPSHOT_KIND_ANALYSIS, key=cle)
            assert snapshot is not None
            avant[cle] = (snapshot.version, snapshot.as_of)
    assert avant, "le scénario exige des dossiers publiés sur données fraîches"

    plus_tard = NOW + timedelta(days=30)
    _ingest(
        session_factory,
        generate_envelopes(seed=SEED + 3, count=6, base_time=plus_tard - timedelta(minutes=5)),
    )
    _runner(session_factory, MutableClock(plus_tard)).drain(max_batches=40)

    with session_factory() as session:
        for cle, (version, as_of) in avant.items():
            snapshot = get_current_snapshot(session, kind=SNAPSHOT_KIND_ANALYSIS, key=cle)
            assert snapshot is not None, f"{cle} a disparu"
            assert snapshot.as_of == as_of, (
                f"{cle} : `as_of` est passé de {as_of} à {snapshot.as_of} sans "
                "nouvelle observation d'analyse — l'ancienneté a été blanchie"
            )
            assert snapshot.version == version
            assert snapshot.content["advice"]["status"] not in STATUTS_AFFIRMATIFS


def test_aucune_degradation_de_cette_campagne_ne_produit_un_avis_affirmatif(
    session_factory: Any,
) -> None:
    """Filet de sécurité transversal.

    Les scénarios ci-dessus vérifient chacun leur invariant. Celui-ci vérifie
    le seul qui compte pour l'utilisateur : sur une population SYNTHETIC
    dégradée, la machine ne dit jamais « qualifié ». Il échouerait si un futur
    changement rendait un des chemins de dégradation silencieusement permissif.
    """
    envelopes = (
        *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_envelopes(seed=SEED, count=8, base_time=BASE_TIME),
    )
    _ingest(session_factory, envelopes)
    clock = MutableClock(NOW)
    _runner(session_factory, clock).drain(max_batches=40)

    advices = _analysis_advices(session_factory)
    assert advices
    for advice in advices:
        assert advice["status"] not in STATUTS_AFFIRMATIFS
        assert advice["limitations"], "un avis dégradé sans limitation écrite est muet"


# ── interruption du traitement ───────────────────────────────────────────────


def test_une_interruption_en_plein_drain_ne_perd_ni_ne_duplique_le_travail(
    session_factory: Any,
) -> None:
    """Un worker tué au milieu du traitement reprend sans perte ni doublon.

    L'interruption est réelle : le premier `drain` est borné à un lot, puis
    abandonné. Aucun message ne doit rester bloqué ni être traité deux fois.
    """
    envelopes = (
        *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
    )
    _ingest(session_factory, envelopes)
    clock = MutableClock(NOW)

    # Premier worker : un seul lot, puis on l'abandonne (processus tué).
    _runner(session_factory, clock).drain(max_batches=1)

    with session_factory() as session:
        restants = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert restants > 0, "le scénario exige qu'il reste du travail après l'interruption"

    # Second worker : reprend le reste.
    _runner(session_factory, clock).drain(max_batches=40)

    with session_factory() as session:
        bloques = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert bloques == 0, "des messages sont restés bloqués après la reprise"
    # Plusieurs versions d'un même snapshot sont légitimes (publish-if-changed).
    # Ce qui ne le serait pas, c'est une version issue d'un double traitement du
    # MÊME message : le rejeu complet ci-dessus
    # (`test_un_replay_complet_apres_traitement_ne_republie_pas_un_snapshot`)
    # prouve qu'un retraitement ne publie rien de neuf. Ici, l'invariant est
    # qu'aucun message n'est ni perdu ni bloqué.
