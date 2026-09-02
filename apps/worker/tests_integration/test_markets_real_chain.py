"""Barre quotidienne IBKR → page Marchés. La chaîne entière, mesurée.

C'EST LE TEST QUI RÉPOND À LA QUESTION DE L'UTILISATEUR : « est-ce que ça
s'affiche ? ». Tout le reste — profil de fusion, préfixes de schéma,
transformation — n'était qu'un moyen. Ce test mesure la fin.

Le parcours complet, sans raccourci :

    barre IBKR → normalize → enveloppes → ingest_envelope → outbox
      → `quotes.ingested` → MarketsOverviewHandler → snapshot publié

Et il vérifie les deux sens : sous le profil réel la donnée arrive et
l'étiquette dit `REAL` ; sous le profil synthétique **la même donnée est
refusée**. Sans le second, on n'aurait pas prouvé que la porte existe encore.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_core.contracts.market_quote import UNCLASSIFIED_SECTOR_CODE
from vertex_edge_ibkr.normalize import daily_quote_envelopes
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import POPULATION_REAL, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.markets import SNAPSHOT_KIND_MARKETS
from vertex_worker.profiles import RealInstrument, real_ibkr_profile, synthetic_profile
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
CON_ID = 208813720
SYMBOLE = "GOOG"
GOOG = RealInstrument(ref=str(CON_ID), symbol=SYMBOLE)
SPEC = ContractSpec(
    sec_type="STK", con_id=CON_ID, symbol=SYMBOLE, exchange="SMART", currency="USD"
)


def horloge() -> datetime:
    return NOW


def enveloppe_barres() -> DataEnvelope[Any]:
    """Enveloppe telle que `historical_bars` de l'adaptateur la produit."""
    bars = BarsPayload(
        con_id=CON_ID,
        bar_size="1 day",
        what_to_show="TRADES",
        use_rth=True,
        bars=(
            BarObservation(
                time=NOW - timedelta(days=1), close=Decimal("201.25"), volume=Decimal("1000")
            ),
        ),
    )
    return DataEnvelope(
        event_id=f"ibkr-bars-{CON_ID}",
        schema_version="ibkr.bars/1",
        source="ibkr",
        instrument_id=str(CON_ID),
        observed_at=NOW - timedelta(minutes=5),
        received_at=NOW - timedelta(minutes=5),
        as_of=NOW - timedelta(minutes=5),
        stale_after=NOW + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=1,
        rights="IBKR_MARKET_DATA_DISPLAY_ONLY",
        payload_hash=canonical_json_hash({"con_id": CON_ID}),
        payload=bars,
    )


def faire_tourner(session_factory: Any, profil: Any) -> Any:
    """Le parcours complet : normalisation, ingestion, worker, snapshot."""
    source = enveloppe_barres()
    derivees, resultat = daily_quote_envelopes(
        source, source.payload, SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    )
    assert resultat.refused_reason is None
    assert derivees, "la transformation n'a produit aucune cotation"

    with session_factory() as session:
        for enveloppe in (source, *derivees):
            ingest_envelope(session, enveloppe)
        session.commit()

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
    runner.run_once()
    with session_factory() as session:
        return get_current_snapshot(session, kind=SNAPSHOT_KIND_MARKETS, key="global")


@pytest.mark.usefixtures("clean_database")
def test_une_barre_ibkr_arrive_sur_la_page_MARCHES_en_REAL(
    migrated_engine: Any, session_factory: Any
) -> None:
    """La question de l'utilisateur, mesurée jusqu'à l'écran."""
    snapshot = faire_tourner(session_factory, real_ibkr_profile((GOOG,)))

    assert snapshot is not None, "aucun snapshot Marchés publié"
    contenu = snapshot.content
    assert contenu["population"] == POPULATION_REAL, (
        f"population attendue REAL, obtenue {contenu['population']!r}"
    )
    # Le symbole est bien celui qu'on affiche, pas un identifiant technique.
    texte = str(contenu)
    assert SYMBOLE in texte, "le symbole n'apparaît pas dans le snapshot publié"
    assert str(CON_ID) not in texte.replace(f"ibkr-bars-{CON_ID}", ""), (
        "un identifiant de contrat a fuité jusqu'à l'affichage"
    )


@pytest.mark.usefixtures("clean_database")
def test_sous_le_profil_SYNTHETIQUE_la_meme_barre_n_affiche_rien(
    migrated_engine: Any, session_factory: Any
) -> None:
    """La porte deny-by-default vaut aussi pour la page Marchés.

    La population est dérivée des observations admises, jamais de la seule
    présence d'une entrée : puisque cette barre IBKR est refusée, elle reste
    `EMPTY`. La couverture prouve en plus qu'aucune cotation n'est reçue et
    que le refus est compté.
    """
    snapshot = faire_tourner(session_factory, synthetic_profile())

    assert snapshot is not None
    assert snapshot.content["population"] == "EMPTY"
    couverture = snapshot.content["coverage"]
    assert couverture["received"] == 0, "une source non déclarée a été reçue"
    assert couverture["covered"] == 0
    assert couverture["rejected_records"], "le refus doit être compté, pas silencieux"
    assert SYMBOLE not in str(snapshot.content["sectors"]), (
        "une source non déclarée a atteint la page Marchés"
    )
