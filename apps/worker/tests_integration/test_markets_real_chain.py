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

La dernière section (L1) mesure un troisième sens : la page reste servie
quand la base contient, plus récentes que les clôtures, des centaines de
lignes qui portent le schéma des cotations quotidiennes sans en être.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_core.contracts.market_quote import (
    UNCLASSIFIED_SECTOR_CODE,
    build_daily_quote_payload,
)
from vertex_edge_ibkr.normalize import (
    DAILY_QUOTE_SCHEMA_VERSION,
    IBKR_TRADES_ADJUSTMENT_BASIS,
    daily_quote_envelopes,
    daily_quote_event_id,
)
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import POPULATION_REAL, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.markets import SNAPSHOT_KIND_MARKETS, TOPIC_QUOTES_INGESTED
from vertex_worker.performance import load_all_daily_quote_records
from vertex_worker.profiles import RealInstrument, real_ibkr_profile, synthetic_profile
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
CON_ID = 208813720
SYMBOLE = "GOOG"
GOOG = RealInstrument(ref=str(CON_ID), symbol=SYMBOLE)
SPEC = ContractSpec(
    sec_type="STK", con_id=CON_ID, symbol=SYMBOLE, exchange="SMART", currency="USD"
)
DROITS_IBKR = "IBKR_MARKET_DATA_DISPLAY_ONLY"


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
        rights=DROITS_IBKR,
        payload_hash=canonical_json_hash({"con_id": CON_ID}),
        payload=bars,
    )


def construire_runner(session_factory: Any, profil: Any) -> WorkerRunner:
    return WorkerRunner(
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


def snapshot_marches(session_factory: Any) -> Any:
    with session_factory() as session:
        return get_current_snapshot(session, kind=SNAPSHOT_KIND_MARKETS, key="global")


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

    construire_runner(session_factory, profil).run_once()
    return snapshot_marches(session_factory)


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


# -- L1 : la fenêtre Marchés affamée par le temps réel (mesuré 2026-09-03) --
#
# Sur la base réelle, dans la fenêtre de 72 h : 3197 lignes `ibkr.daily-quote/1`
# SANS `ticker` ni `trading_day` — les cotations INSTANTANÉES des 8 indices,
# une par instrument et par cycle de 60 s, que l'adaptateur étiquetait du
# schéma des cotations quotidiennes — contre 323 vraies cotations quotidiennes.
# Parmi les 500 plus récentes par `as_of` : 495 instantanées, 5 quotidiennes.
# Résultat servi : coverage {expected 161, received 5, covered 0, discarded
# 161 missing_close}, population REAL, breadth non calculable — la page
# Marchés vide dès que le collecteur temps réel tourne.
#
# Ces lignes RESTENT en base (append-only) même une fois l'adaptateur corrigé.
# La fenêtre doit donc les ignorer AVANT sa borne, et non les charger puis
# les rejeter une à une jusqu'à ne plus avoir de place pour les clôtures.

NB_INSTRUMENTS = 161
NB_INSTANTANEES = 600
JOUR_VEILLE = date(2026, 8, 28)
JOUR_DERNIER = date(2026, 8, 29)
INDICES = ("SPX", "NDX", "DJI", "RUT", "VIX", "SX5E", "DAX", "SMI")


def univers_reel() -> tuple[RealInstrument, ...]:
    return tuple(
        RealInstrument(ref=str(700_000 + rang), symbol=f"T{rang:03d}")
        for rang in range(1, NB_INSTRUMENTS + 1)
    )


def cotation_quotidienne(
    instrument: RealInstrument, jour: date, close: str
) -> DataEnvelope[Any]:
    """Telle que `normalize.daily_quote_envelopes` la dérive d'une barre."""
    instant = datetime(jour.year, jour.month, jour.day, 20, 0, 0, tzinfo=UTC)
    charge = build_daily_quote_payload(
        ticker=instrument.symbol,
        sector=UNCLASSIFIED_SECTOR_CODE,
        trading_day=jour.isoformat(),
        close=Decimal(close),
        adjustment_basis=IBKR_TRADES_ADJUSTMENT_BASIS,
        currency="USD",
    )
    return DataEnvelope(
        event_id=daily_quote_event_id(int(instrument.ref), jour.isoformat()),
        schema_version=DAILY_QUOTE_SCHEMA_VERSION,
        source="ibkr",
        instrument_id=instrument.ref,
        observed_at=instant,
        received_at=instant,
        as_of=instant,
        stale_after=instant + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=1,
        rights=DROITS_IBKR,
        payload_hash=canonical_json_hash(charge),
        payload=charge,
    )


def cotation_instantanee(rang: int) -> DataEnvelope[Any]:
    """Telle qu'elle EXISTE en base : schéma quotidien, charge utile de carnet.

    Ni `ticker` ni `trading_day` : `symbol`, `bid`, `ask`, `last`, `volume`.
    Le schéma est le littéral mesuré, pas une constante — c'est l'état des
    lignes déjà écrites, que la correction de l'adaptateur n'efface pas.
    """
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
        event_id=f"ibkr-quote-{rang}",
        schema_version="ibkr.daily-quote/1",
        source="ibkr",
        instrument_id=str(charge["con_id"]),
        observed_at=instant,
        received_at=instant,
        as_of=instant,
        stale_after=instant + timedelta(seconds=60),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=1,
        rights=DROITS_IBKR,
        payload_hash=canonical_json_hash(charge),
        payload=charge,
    )


def ecrire_sans_outbox(session: Any, enveloppe: DataEnvelope[Any]) -> None:
    """Écrit l'observation telle quelle, sans message : l'ÉTAT de la base.

    C'est la base héritée que ce test reproduit, pas le chemin d'ingestion ;
    un seul `quotes.ingested` réveille ensuite la page, comme le ferait la
    prochaine cotation ingérée.
    """
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


def peupler_base_affamee(session_factory: Any) -> None:
    """161 × 2 clôtures valides, puis 600 instantanées PLUS RÉCENTES."""
    with session_factory() as session:
        for instrument in univers_reel():
            ecrire_sans_outbox(session, cotation_quotidienne(instrument, JOUR_VEILLE, "100.00"))
            ecrire_sans_outbox(session, cotation_quotidienne(instrument, JOUR_DERNIER, "101.00"))
        for rang in range(NB_INSTANTANEES):
            ecrire_sans_outbox(session, cotation_instantanee(rang))
        enqueue_outbox(
            session,
            TOPIC_QUOTES_INGESTED,
            {"event_id": "reveil", "source": "ibkr", "schema_version": DAILY_QUOTE_SCHEMA_VERSION},
        )
        session.commit()


@pytest.mark.usefixtures("clean_database")
def test_la_fenetre_MARCHES_n_est_pas_affamee_par_les_cotations_temps_reel(
    migrated_engine: Any, session_factory: Any
) -> None:
    """REPRODUCTEUR L1 : 600 instantanées plus récentes que 161 × 2 clôtures.

    Attendu : les 161 tickers couverts, aucun écarté, rien converti. Avant le
    correctif, la borne de 500 ne contenait que des instantanées et la page
    servait `covered 0, discarded 161 missing_close`.
    """
    profil = real_ibkr_profile(univers_reel())
    # Le reproducteur exige la forme mesurée : plus d'instantanées que la borne.
    assert NB_INSTANTANEES > profil.markets.max_observations
    peupler_base_affamee(session_factory)

    construire_runner(session_factory, profil).run_once()
    snapshot = snapshot_marches(session_factory)

    assert snapshot is not None, "aucun snapshot Marchés publié"
    contenu = snapshot.content
    couverture = contenu["coverage"]
    assert couverture["expected"] == NB_INSTRUMENTS
    assert couverture["covered"] == NB_INSTRUMENTS, (
        f"couverts {couverture['covered']} sur {NB_INSTRUMENTS} : "
        f"écartés {couverture['discarded_tickers'][:3]}…"
    )
    assert couverture["discarded"] == 0
    assert couverture["received"] == NB_INSTRUMENTS
    # Les instantanées ne sont pas entrées dans la fenêtre : ni comptées, ni
    # rejetées une à une.
    assert couverture["observations_considered"] == 2 * NB_INSTRUMENTS
    assert couverture["rejected_records"] == []
    assert contenu["population"] == POPULATION_REAL
    assert contenu["breadth"]["status"] == "OK"
    # 100.00 -> 101.00 partout : rien n'a été interpolé ni mis à zéro.
    assert contenu["breadth"]["above_count"] == NB_INSTRUMENTS


@pytest.mark.usefixtures("clean_database")
def test_l_historique_PERFORMANCE_ignore_aussi_les_cotations_temps_reel(
    migrated_engine: Any, session_factory: Any
) -> None:
    """Même famille de schéma, même défaut : l'historique de performance.

    `load_all_daily_quote_records` charge TOUT l'historique (sans fenêtre
    temporelle) sous une borne de 10 000 au-delà de laquelle la série entière
    est déclarée insuffisante. Des instantanées comptées dedans consomment
    cette borne pour rien.
    """
    peupler_base_affamee(session_factory)

    with session_factory() as session:
        cotations, tronque = load_all_daily_quote_records(session, now=NOW)

    assert not tronque
    assert len(cotations) == 2 * NB_INSTRUMENTS, (
        f"{len(cotations)} lignes chargées : des instantanées sont entrées"
    )
    assert all("ticker" in c.payload and "trading_day" in c.payload for c in cotations)
