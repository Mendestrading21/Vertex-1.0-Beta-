"""Dépêche IBKR → file d'attention, quand le temps réel remplit la base.

CE TEST EXISTE À CAUSE D'UN DÉFAUT MESURÉ. Le 2026-09-03 à 08:40 UTC,
`today/attention` servait 0 item sur données réelles alors que des dépêches
valides existaient en base. Le collecteur temps réel émet une cotation
instantanée par instrument et par cycle de 60 s (schéma `ibkr.quote/1` depuis
le lot L1, `ibkr.daily-quote/1` pour les 3 197 lignes déjà écrites) : sans
titre, elles ne sont jamais du contenu, mais `load_recent_observation_records`
bornait la fenêtre à 500 lignes par `as_of` décroissant SANS distinguer les
familles de schéma. Les 500 plus récentes étaient toutes des instantanées ;
les dépêches, plus anciennes de quelques minutes, n'entraient plus dans la
fenêtre. Rien n'échouait, rien n'était journalisé : la file était vide.

Le parcours mesuré, sans raccourci :

    base héritée (dépêches + instantanées) → `observation.ingested`
      → AttentionFusionHandler → snapshot `attention/global`
    et la même fenêtre pour `review_queue.refresh` → ReviewQueueHandler.

La base est peuplée TELLE QU'ELLE EXISTE (`insert_observation`, sans message
par ligne) : c'est l'état hérité que ce test reproduit, pas le chemin
d'ingestion. Un seul message réveille ensuite chaque file, comme le ferait la
prochaine cotation ingérée.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_edge_ibkr.news import NEWS_HEADLINE_SCHEMA_VERSION, news_headline_event_id
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.follow_up import (
    SNAPSHOT_KIND_REVIEW_QUEUE,
    TOPIC_REVIEW_QUEUE_REFRESH,
)
from vertex_worker.handlers import (
    CONTENT_SCHEMA_PREFIXES,
    MAX_ATTENTION_ITEMS,
    POPULATION_REAL,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_ATTENTION,
    build_registry,
)
from vertex_worker.ingest import TOPIC_OBSERVATION_INGESTED
from vertex_worker.profiles import (
    IBKR_RIGHTS,
    IBKR_SOURCE,
    RealInstrument,
    real_ibkr_profile,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 9, 3, 8, 40, 0, tzinfo=UTC)

#: Quatre instruments réels, cinq dépêches chacun : vingt dépêches valides.
UNIVERS = (
    RealInstrument(ref="208813720", symbol="GOOG"),
    RealInstrument(ref="272093", symbol="MSFT"),
    RealInstrument(ref="265598", symbol="AAPL"),
    RealInstrument(ref="4391", symbol="IBM"),
)
THEMES = (
    "résultats trimestriels publiés",
    "changement de direction générale annoncé",
    "programme de rachat d'actions relevé",
    "avertissement sur les résultats de l'exercice",
    "nouveau contrat pluriannuel signé",
)
NB_DEPECHES = len(UNIVERS) * len(THEMES)

#: Instantanées PLUS RÉCENTES que les dépêches, à parts égales sous les deux
#: schémas qui coexistent en base : les lignes déjà écrites (`ibkr.daily-quote/1`)
#: et celles que le collecteur émet depuis L1 (`ibkr.quote/1`). Les deux sont
#: des littéraux : c'est l'ÉTAT de la base, pas une constante du code.
NB_INSTANTANEES = 600
SCHEMAS_INSTANTANEES = ("ibkr.quote/1", "ibkr.daily-quote/1")
INDICES = ("SPX", "NDX", "DJI", "RUT", "VIX", "SX5E", "DAX", "SMI")


def horloge() -> datetime:
    return NOW


def depeche(instrument: RealInstrument, rang: int) -> DataEnvelope[Any]:
    """Telle que `news.news_headline_envelopes` la dérive d'une réponse IBKR."""
    instant = NOW - timedelta(minutes=30, seconds=10 * rang)
    charge = {
        "type": "news_headline",
        "title": f"{instrument.symbol} : {THEMES[rang % len(THEMES)]}",
        "provider_code": "BRFG",
        "article_id": f"{instrument.symbol}-{rang}",
        "entities": [instrument.symbol],
    }
    return DataEnvelope(
        event_id=news_headline_event_id("BRFG", f"{instrument.symbol}-{rang}"),
        schema_version=NEWS_HEADLINE_SCHEMA_VERSION,
        source=IBKR_SOURCE,
        instrument_id=instrument.ref,
        observed_at=instant,
        published_at=instant,
        received_at=instant,
        as_of=instant,
        stale_after=instant + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=1,
        rights=IBKR_RIGHTS,
        payload_hash=canonical_json_hash(charge),
        payload=charge,
    )


def cotation_instantanee(rang: int) -> DataEnvelope[Any]:
    """Telle qu'elle EXISTE en base : charge utile de carnet, ni titre ni ticker."""
    instant = NOW - timedelta(minutes=5, seconds=rang)
    charge = {
        "con_id": 416_904 + rang % len(INDICES),
        "symbol": INDICES[rang % len(INDICES)],
        "bid": "6500.25",
        "bid_size": "3",
        "ask": "6500.75",
        "ask_size": "5",
        "last": "6500.50",
        "last_size": "1",
        "volume": "12345",
        "close": "6490.00",
        "halted": False,
        "market_data_type": 1,
    }
    return DataEnvelope(
        event_id=f"ibkr-instantanee-{rang}",
        schema_version=SCHEMAS_INSTANTANEES[rang % len(SCHEMAS_INSTANTANEES)],
        source=IBKR_SOURCE,
        instrument_id=str(charge["con_id"]),
        observed_at=instant,
        received_at=instant,
        as_of=instant,
        stale_after=instant + timedelta(seconds=60),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=1,
        rights=IBKR_RIGHTS,
        payload_hash=canonical_json_hash(charge),
        payload=charge,
    )


def ecrire_sans_outbox(session: Any, enveloppe: DataEnvelope[Any]) -> None:
    """Écrit l'observation telle quelle, sans message : l'ÉTAT de la base."""
    inseree = insert_observation(
        session,
        event_id=enveloppe.event_id,
        schema_version=enveloppe.schema_version,
        source=enveloppe.source,
        source_event_id=enveloppe.source_event_id,
        instrument_ref=enveloppe.instrument_id,
        observed_at=enveloppe.observed_at,
        published_at=enveloppe.published_at,
        received_at=enveloppe.received_at,
        as_of=enveloppe.as_of,
        stale_after=enveloppe.stale_after,
        quality_status=enveloppe.quality_status.value,
        delay_status=enveloppe.delay_status.value,
        connection_epoch=enveloppe.connection_epoch,
        rights=enveloppe.rights,
        payload=enveloppe.payload,
    )
    assert inseree, f"observation dupliquée : {enveloppe.event_id}"


def peupler_base_affamee(session_factory: Any) -> set[str]:
    """20 dépêches valides, puis 600 instantanées PLUS RÉCENTES. Rend les titres."""
    titres: set[str] = set()
    with session_factory() as session:
        for instrument in UNIVERS:
            for rang in range(len(THEMES)):
                enveloppe = depeche(instrument, rang)
                titres.add(str(enveloppe.payload["title"]))
                ecrire_sans_outbox(session, enveloppe)
        for rang in range(NB_INSTANTANEES):
            ecrire_sans_outbox(session, cotation_instantanee(rang))
        reveil = {"event_id": "reveil", "source": IBKR_SOURCE, "schema_version": "ibkr.quote/1"}
        enqueue_outbox(session, TOPIC_OBSERVATION_INGESTED, reveil)
        enqueue_outbox(session, TOPIC_REVIEW_QUEUE_REFRESH, reveil)
        session.commit()
    assert len(titres) == NB_DEPECHES
    return titres


def faire_tourner(session_factory: Any) -> None:
    profil = real_ibkr_profile(UNIVERS)
    runner = WorkerRunner(
        session_factory=session_factory,
        registry=build_registry(
            clock=horloge,
            fusion_config=profil.fusion,
            markets_config=profil.markets,
            options_config=profil.options,
            analysis_config=profil.analysis,
            calendar_config=profil.calendar,
            opportunities_config=profil.opportunities,
            risk_config=profil.risk,
        ),
        poll_interval_seconds=0.01,
        clock=horloge,
    )
    runner.drain(max_batches=10)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0, stats


def snapshot(session_factory: Any, kind: str) -> Any:
    with session_factory() as session:
        return get_current_snapshot(session, kind=kind, key=SNAPSHOT_KEY_GLOBAL)


@pytest.mark.usefixtures("clean_database")
def test_la_file_d_ATTENTION_n_est_pas_affamee_par_les_cotations_instantanees(
    migrated_engine: Any, session_factory: Any
) -> None:
    """REPRODUCTEUR S0 : 600 instantanées plus récentes que 20 dépêches valides.

    Avant le correctif : 0 item, `content_observations` 0 — la fenêtre de 500
    ne contenait que des instantanées. Attendu : les 20 dépêches sont TOUTES
    dans la fenêtre (elles sont le seul contenu), la file publie des items
    réels, et aucune instantanée ne compte comme contenu.
    """
    titres = peupler_base_affamee(session_factory)
    faire_tourner(session_factory)

    attention = snapshot(session_factory, SNAPSHOT_KIND_ATTENTION)
    assert attention is not None, "aucun snapshot d'attention publié"
    contenu = attention.content
    couverture = contenu["coverage"]
    assert couverture["content_observations"] == NB_DEPECHES, (
        f"dépêches dans la fenêtre : {couverture['content_observations']} "
        f"sur {NB_DEPECHES} ; couverture = {couverture}"
    )
    # La fenêtre ne regarde QUE les familles déclarées, et le dit.
    assert couverture["observations_considered"] == NB_DEPECHES, couverture
    assert couverture["content_schema_prefixes"] == list(CONTENT_SCHEMA_PREFIXES)
    items = contenu["items"]
    assert items, f"file vide ; refus = {contenu['rejected']} ; couverture = {couverture}"
    assert len(items) <= MAX_ATTENTION_ITEMS
    assert contenu["population"] == POPULATION_REAL
    for item in items:
        assert item["synthetic"] is False
        assert item["title"] in titres, f"item inattendu : {item['title']!r}"


@pytest.mark.usefixtures("clean_database")
def test_la_file_de_REVUE_lit_la_meme_fenetre_de_contenu(
    migrated_engine: Any, session_factory: Any
) -> None:
    """La file de revue partage le chargeur : même famine, même correctif.

    Sans thèse déclarée elle ne publie aucune entrée, mais son contexte
    d'information doit voir les 20 dépêches — c'est lui qui signale
    « nouvelle information » sur une thèse. Avant : 0 observation de contenu.
    """
    peupler_base_affamee(session_factory)
    faire_tourner(session_factory)

    revue = snapshot(session_factory, SNAPSHOT_KIND_REVIEW_QUEUE)
    assert revue is not None, "aucun snapshot de file de revue publié"
    couverture = revue.content["coverage"]
    assert couverture["content_observations"] == NB_DEPECHES, couverture
    assert couverture["observations_considered"] == NB_DEPECHES, couverture
    assert couverture["content_schema_prefixes"] == list(CONTENT_SCHEMA_PREFIXES)
    assert revue.content["populations"]["information_context"] == POPULATION_REAL
