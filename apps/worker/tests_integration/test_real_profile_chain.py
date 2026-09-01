"""La porte de fusion : une source réelle atteint-elle l'écran, et elle seule ?

CE QUE CE TEST ÉTABLIT. Les tests unitaires prouvent que le profil réel
DÉCLARE la source IBKR. Ils ne prouvent pas que la donnée traverse la chaîne
complète : ingestion → outbox → worker → snapshot publié. C'est pourtant la
seule question qui compte — « est-ce que ça s'affiche ? ».

POURQUOI UNE ACTUALITÉ ET NON UNE COTATION. La file d'attention ne retient que
les observations porteuses d'un `title` (`_content_title`) : une cotation brute
n'en a pas et reste « non-contenu », quelle que soit sa source. Une actualité
IBKR en a un. Tester la porte avec une cotation aurait mesuré la classification
du contenu, pas la porte — et aurait donné une fausse assurance.

Deux mesures contre une vraie base migrée, et la seconde compte autant que la
première : un test qui ne montrerait que le succès ne prouverait pas que la
protection existe encore.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import (
    POPULATION_REAL,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_ATTENTION,
    build_registry,
)
from vertex_worker.ingest import ingest_envelope
from vertex_worker.profiles import (
    IBKR_RIGHTS,
    IBKR_SOURCE,
    RealInstrument,
    real_ibkr_profile,
    synthetic_profile,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
CON_ID = "208813720"
INSTRUMENT = RealInstrument(ref=CON_ID, symbol="GOOG")


def horloge() -> datetime:
    return NOW


def enveloppe_actualite_ibkr(event_id: str) -> DataEnvelope[Any]:
    """Actualité IBKR : porteuse d'un titre, donc du contenu pour l'attention."""
    payload = {
        "title": "Résultats trimestriels publiés",
        "provider_code": "BRFG",
        "con_id": int(CON_ID),
    }
    return DataEnvelope(
        event_id=event_id,
        schema_version="ibkr.news-headlines/1",
        source=IBKR_SOURCE,
        instrument_id=CON_ID,
        observed_at=NOW - timedelta(minutes=1),
        received_at=NOW - timedelta(minutes=1),
        as_of=NOW - timedelta(minutes=1),
        stale_after=NOW + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=1,
        rights=IBKR_RIGHTS,
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


def faire_tourner(session_factory: Any, profil: Any, event_id: str) -> Any:
    """Ingère une observation IBKR, fait tourner le worker, rend le snapshot."""
    with session_factory() as session:
        ingest_envelope(session, enveloppe_actualite_ibkr(event_id))
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
        return get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL
        )


@pytest.mark.usefixtures("clean_database")
def test_sous_le_profil_REEL_la_donnee_ibkr_atteint_l_ecran(
    migrated_engine: Any, session_factory: Any
) -> None:
    """La question de l'utilisateur : « est-ce que ça s'affiche ? »."""
    snapshot = faire_tourner(session_factory, real_ibkr_profile((INSTRUMENT,)), "ibkr-reel-1")

    assert snapshot is not None, "aucun snapshot publié : la donnée n'a pas traversé"
    contenu = snapshot.content
    assert contenu["items"], f"rien affiché ; refus = {contenu['rejected']}"
    assert contenu["population"] == POPULATION_REAL
    # L'item affiché est bien réel, jamais étiqueté synthétique.
    assert all(item["synthetic"] is False for item in contenu["items"])


@pytest.mark.usefixtures("clean_database")
def test_sous_le_profil_SYNTHETIQUE_la_meme_donnee_est_refusee(
    migrated_engine: Any, session_factory: Any
) -> None:
    """La porte deny-by-default doit toujours exister.

    C'est LA garantie de sécurité : une source non déclarée n'atteint pas
    l'écran, même si elle est déjà en base. Le refus doit en outre être
    EXPLICITE — jamais un abandon silencieux.
    """
    snapshot = faire_tourner(session_factory, synthetic_profile(), "ibkr-refus-1")

    assert snapshot is not None
    contenu = snapshot.content
    assert contenu["items"] == [], "une source non déclarée a atteint l'écran"
    assert contenu["coverage"]["ranked"] == 0
    assert contenu["rejected"], "le refus doit être visible, pas implicite"
    motifs = {rejet["filtered_reason"] for rejet in contenu["rejected"]}
    assert motifs <= {"SOURCE_OK_FAILED", "RIGHTS_OK_FAILED"}, motifs
