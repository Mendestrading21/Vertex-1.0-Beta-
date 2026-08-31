"""Barre quotidienne IBKR → page Analyse. La chaîne entière, contre PostgreSQL.

CE TEST EXISTE À CAUSE D'UN DÉFAUT RÉEL. Le 2026-08-31, 251 barres IBKR
étaient en base et la page Analyse était vide : `DAILY_BARS_SCHEMA_PREFIXES`
ne déclarait que la famille synthétique. Rien n'échouait, rien n'était
journalisé — la donnée était simplement ignorée. Un test unitaire sur la
transformation n'aurait rien vu : le défaut vivait dans l'ACCORD entre deux
paquets, pas dans l'un des deux.

Le parcours mesuré, sans raccourci :

    barre IBKR → daily_bars_envelope → ingest_envelope → outbox
      → `analysis.ingested` → AnalysisHandler → snapshot publié

Et les deux sens : sous le profil réel le dossier est publié ; sous le profil
synthétique la MÊME donnée reste invisible. Sans le second, on n'aurait pas
prouvé que la porte existe encore.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_edge_ibkr.normalize import daily_bars_envelope
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.analysis import SNAPSHOT_KIND_ANALYSIS
from vertex_worker.handlers import build_registry
from vertex_worker.ingest import ingest_envelope
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


def enveloppe_barres() -> DataEnvelope[Any]:
    """Enveloppe telle que `historical_bars` de l'adaptateur la produit."""
    charge = BarsPayload(
        con_id=CON_ID,
        bar_size="1 day",
        what_to_show="TRADES",
        use_rth=True,
        bars=(
            _barre(NOW - timedelta(days=2), "211.27"),
            _barre(NOW - timedelta(days=1), "213.53"),
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
        payload=charge,
    )


def faire_tourner(session_factory: Any, profil: Any) -> Any:
    source = enveloppe_barres()
    derivee, resultat = daily_bars_envelope(source, source.payload, SPEC)
    assert resultat.refused_reason is None, resultat.refused_reason
    assert derivee is not None, "la dérivation n'a produit aucun enregistrement"

    with session_factory() as session:
        for enveloppe in (source, derivee):
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
        ),
        poll_interval_seconds=0.01,
        clock=horloge,
    )
    runner.run_once()
    with session_factory() as session:
        return get_current_snapshot(session, kind=SNAPSHOT_KIND_ANALYSIS, key=SYMBOLE)


@pytest.mark.usefixtures("clean_database")
def test_des_barres_IBKR_produisent_un_dossier_d_analyse(
    migrated_engine: Any, session_factory: Any
) -> None:
    """La page Analyse affiche enfin de vraies barres."""
    snapshot = faire_tourner(session_factory, real_ibkr_profile((GOOG,)))

    assert snapshot is not None, "aucun dossier d'analyse publié"
    contenu = snapshot.content
    barres = contenu["bars"]["bars"] if "bars" in contenu.get("bars", {}) else contenu["bars"]
    texte = str(contenu)
    assert SYMBOLE in texte, "le symbole n'apparaît pas dans le dossier publié"
    assert "213.53" in texte, "la clôture réelle n'est pas relayée verbatim"
    assert barres, "le dossier est publié mais ne contient aucune barre"


@pytest.mark.usefixtures("clean_database")
def test_sous_le_profil_SYNTHETIQUE_les_memes_barres_restent_invisibles(
    migrated_engine: Any, session_factory: Any
) -> None:
    """La porte deny-by-default vaut aussi pour la page Analyse.

    Le profil synthétique ne déclare ni la source `ibkr` ni ses droits :
    aucun dossier ne doit être publié pour un symbole qu'il n'a jamais
    déclaré. Une porte qui ne ferme jamais n'est pas une porte.
    """
    snapshot = faire_tourner(session_factory, synthetic_profile())
    assert snapshot is None, "une source non déclarée a atteint la page Analyse"
