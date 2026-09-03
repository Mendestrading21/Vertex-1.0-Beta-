"""Preuves par instrument sur la page Opportunités, contre PostgreSQL.

CE QUE CE TEST ÉTABLIT. Le rail de preuves de la page Analyse est cadré par
instrument depuis le 2026-09-01 (`analysis.py`, `instrument_ref` passé au
chargeur AVANT la borne) : mesuré ce jour-là, la fenêtre globale de 500 ne
contenait plus AUCUNE dépêche de GOOG alors que 140 existaient en base. La
page Opportunités construit POURTANT le même dossier pour chaque candidat à
partir d'UNE fenêtre globale (`opportunities.py`, sans `instrument_ref`) :
le même instrument y perd ses preuves dès qu'un autre instrument est collecté
après lui. Deux pages, un seul moteur, deux réponses — c'est ce que ce test
refuse.

Le parcours mesuré :

    barres IBKR (A et B) → ingest_envelope → outbox → `opportunities.refresh`
      → OpportunitiesHandler → snapshot `opportunities/global`
    avec, en base, 3 dépêches de A PLUS ANCIENNES que 520 dépêches de B.

La page Analyse sert de témoin : elle voit les preuves de A. La page
Opportunités doit les voir aussi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_edge_ibkr.news import NEWS_HEADLINE_SCHEMA_VERSION, news_headline_event_id
from vertex_edge_ibkr.normalize import daily_bars_envelope
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.analysis import SNAPSHOT_KIND_ANALYSIS
from vertex_worker.handlers import build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.opportunities import (
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_OPPORTUNITIES,
)
from vertex_worker.profiles import (
    IBKR_RIGHTS,
    IBKR_SOURCE,
    RealInstrument,
    real_ibkr_profile,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 9, 3, 8, 40, 0, tzinfo=UTC)
A = RealInstrument(ref="208813720", symbol="GOOG")
B = RealInstrument(ref="272093", symbol="MSFT")

#: Plus de dépêches de B que la borne de la fenêtre globale (500), toutes plus
#: récentes que les 3 dépêches de A : la fenêtre globale ne contient plus A.
NB_DEPECHES_A = 3
NB_DEPECHES_B = 520


def horloge() -> datetime:
    return NOW


def spec(instrument: RealInstrument) -> ContractSpec:
    return ContractSpec(
        sec_type="STK",
        con_id=int(instrument.ref),
        symbol=instrument.symbol,
        exchange="SMART",
        currency="USD",
    )


def _barre(jour: datetime, cloture: str) -> BarObservation:
    base = Decimal(cloture)
    return BarObservation(
        time=jour,
        open=base - Decimal("1.00"),
        high=base + Decimal("2.00"),
        low=base - Decimal("2.00"),
        close=base,
        volume=Decimal("11006698.0"),
    )


def enveloppe_barres(instrument: RealInstrument) -> DataEnvelope[Any]:
    """Enveloppe telle que `historical_bars` de l'adaptateur la produit."""
    charge = BarsPayload(
        con_id=int(instrument.ref),
        bar_size="1 day",
        what_to_show="TRADES",
        use_rth=True,
        bars=(
            _barre(NOW - timedelta(days=2), "211.27"),
            _barre(NOW - timedelta(days=1), "213.53"),
        ),
    )
    return DataEnvelope(
        event_id=f"ibkr-bars-{instrument.ref}",
        schema_version="ibkr.bars/1",
        source=IBKR_SOURCE,
        instrument_id=instrument.ref,
        observed_at=NOW - timedelta(minutes=5),
        received_at=NOW - timedelta(minutes=5),
        as_of=NOW - timedelta(minutes=5),
        stale_after=NOW + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=1,
        rights=IBKR_RIGHTS,
        payload_hash=canonical_json_hash({"con_id": int(instrument.ref)}),
        payload=charge,
    )


def depeche(instrument: RealInstrument, rang: int, instant: datetime) -> DataEnvelope[Any]:
    """Telle que `news.news_headline_envelopes` la dérive d'une réponse IBKR."""
    charge = {
        "type": "news_headline",
        "title": f"{instrument.symbol} : dépêche n°{rang} sur un fait distinct {rang * 7919}",
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


def peupler(session_factory: Any) -> None:
    """Barres de A et B par le chemin d'ingestion ; dépêches à l'état hérité."""
    with session_factory() as session:
        for instrument in (A, B):
            source = enveloppe_barres(instrument)
            derivee, resultat = daily_bars_envelope(source, source.payload, spec(instrument))
            assert resultat.refused_reason is None, resultat.refused_reason
            assert derivee is not None, "la dérivation n'a produit aucun enregistrement"
            for enveloppe in (source, derivee):
                assert ingest_envelope(session, enveloppe).inserted
        for rang in range(NB_DEPECHES_A):
            ecrire_sans_outbox(
                session, depeche(A, rang, NOW - timedelta(hours=3, seconds=10 * rang))
            )
        for rang in range(NB_DEPECHES_B):
            ecrire_sans_outbox(
                session, depeche(B, rang, NOW - timedelta(hours=1, seconds=rang))
            )
        session.commit()


def faire_tourner(session_factory: Any) -> None:
    profil = real_ibkr_profile((A, B))
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
    runner.drain(max_batches=60)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0, stats


def candidat(contenu: dict[str, Any], symbole: str) -> dict[str, Any]:
    for groupe in ("qualified", "excluded"):
        for entree in contenu[groupe]:
            if entree["ticker"] == symbole:
                return dict(entree)
    raise AssertionError(f"{symbole} absent des deux groupes : {contenu['coverage']}")


@pytest.mark.usefixtures("clean_database")
def test_les_preuves_d_un_candidat_ne_sont_pas_chassees_par_un_autre_instrument(
    migrated_engine: Any, session_factory: Any
) -> None:
    """REPRODUCTEUR S0-3 : 520 dépêches de B plus récentes que 3 dépêches de A.

    Témoin : la page Analyse (fenêtre cadrée par instrument) voit les preuves
    de A. Attendu : le candidat A de la page Opportunités les voit aussi.
    Avant le correctif : `evidence_cluster_ids` vide pour A.
    """
    peupler(session_factory)
    faire_tourner(session_factory)

    with session_factory() as session:
        analyse = get_current_snapshot(session, kind=SNAPSHOT_KIND_ANALYSIS, key=A.symbol)
        opportunites = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_OPPORTUNITIES, key=SNAPSHOT_KEY_GLOBAL
        )
    assert analyse is not None, "aucun dossier d'analyse publié pour A"
    temoin = analyse.content["evidence"]
    assert temoin["clusters_total"] >= 1, f"le témoin Analyse ne voit pas A : {temoin}"

    assert opportunites is not None, "aucun snapshot d'opportunités publié"
    contenu = opportunites.content
    assert contenu["population"] == "REAL"
    preuves_a = candidat(contenu, A.symbol)["evidence_cluster_ids"]
    assert preuves_a, (
        f"la page Opportunités ne voit aucune preuve de {A.symbol} alors que "
        f"la page Analyse en voit {temoin['clusters_total']} : "
        f"fenêtre globale chassée par {NB_DEPECHES_B} dépêches de {B.symbol}"
    )
    assert set(preuves_a) == {c["cluster_id"] for c in temoin["clusters"]}, (
        "les deux pages ne publient pas les mêmes grappes de preuves pour A"
    )
    preuves_b = candidat(contenu, B.symbol)["evidence_cluster_ids"]
    assert preuves_b, f"les preuves de {B.symbol} ont disparu"
