"""Le rail de preuves lit les familles À TITRE de SON instrument.

CE TEST EXISTE À CAUSE D'UNE RÉGRESSION MESURÉE (CI GitHub, exécution
33750177958, tâche « e2e — Chromium, 3 viewports desktop, axe » : trois
échecs identiques sur les trois viewports) ::

    ✘ e2e/ai-inspector.spec.ts:89 › Explication IA — extraits externes
    > 122 |     expect(answer.external_excerpts.length).toBeGreaterThanOrEqual(1);
    Expected: >= 1
    Received:    0

Le lot S0 a rendu OBLIGATOIRE, avant la borne, la déclaration des familles
de schéma que chaque consommateur sait lire, et a déclaré
`CONTENT_SCHEMA_PREFIXES` — les dépêches — pour le rail de preuves d'Analyse
(`apps/worker/src/vertex_worker/analysis.py`) comme pour celui
d'Opportunités (`apps/worker/src/vertex_worker/opportunities.py`). Or les
SEULES observations porteuses d'un `title` rattachées à un ticker de la
population de démonstration sont les ÉVÉNEMENTS DE CALENDRIER
(`synthetic-calendar-event/`, `vertex_core.synthetic.events`) : les dépêches
synthétiques parlent des tickers `SYN1`..`SYN9`
(`vertex_core.synthetic.generator`), jamais de `SYN-TECH-01`. Le rail est
donc passé de plusieurs grappes à zéro ; l'explication IA, dont les extraits
externes n'ont qu'une source (`evidence.clusters[].title`, lu par
`apps/api/src/vertex_api/ai_explain.py:1658`), n'en a plus produit aucun.
Rien n'a échoué côté serveur : la page a servi un bloc vide.

Le parcours mesuré, sans raccourci ::

    enveloppes SYNTHETIC (barres + événements de calendrier)
      → `ingest_envelope` (VRAI chemin d'ingestion)
      → `analysis.ingested` / `opportunities.refresh` (VRAI worker drainé)
      → snapshots `analysis/SYN-TECH-01` et `opportunities/global`
      → `evidence.clusters` / `candidat.evidence_cluster_ids`

Le partage reste DÉCLARÉ dans les deux sens : la file d'attention, elle, ne
lit toujours pas ces événements — le témoin en est réaffirmé ici sur la
chaîne réelle, pas seulement en unitaire.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vertex_core.synthetic import (
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
)
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.analysis import SNAPSHOT_KIND_ANALYSIS
from vertex_worker.handlers import (
    DEV_SYNTHETIC_CONFIG,
    POPULATION_EMPTY,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_ATTENTION,
    build_registry,
)
from vertex_worker.ingest import ingest_envelope
from vertex_worker.opportunities import (
    SNAPSHOT_KEY_GLOBAL as OPPORTUNITIES_KEY,
)
from vertex_worker.opportunities import (
    SNAPSHOT_KIND_OPPORTUNITIES,
)
from vertex_worker.runner import WorkerRunner

#: Le ticker que l'inspecteur IA explique dans le parcours e2e
#: (`apps/web/e2e/ai-inspector.spec.ts`).
INSTRUMENT = "SYN-TECH-01"

SEED = 20260903
NOW = datetime.now(UTC).replace(microsecond=0)
BASE_TIME = NOW - timedelta(minutes=30)

SessionFactory = Callable[[], Session]


def _drain(session_factory: SessionFactory) -> None:
    """Ingère la population puis draine le VRAI worker jusqu'au silence."""

    def clock() -> datetime:
        return datetime.now(UTC)

    with session_factory() as session:
        for envelope in (
            *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
            *generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME),
        ):
            ingest_envelope(session, envelope)
        session.commit()

    runner = WorkerRunner(
        session_factory=session_factory,
        registry=build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG),
        poll_interval_seconds=0.05,
        clock=clock,
    )
    runner.drain(max_batches=120)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0, stats


def _analysis_content(session_factory: SessionFactory) -> Mapping[str, Any]:
    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ANALYSIS, key=INSTRUMENT
        )
    assert snapshot is not None, f"aucun dossier publié pour {INSTRUMENT}"
    return snapshot.content


@pytest.mark.usefixtures("migrated_engine")
def test_le_rail_d_analyse_publie_les_evenements_de_calendrier_de_l_instrument(
    session_factory: SessionFactory,
) -> None:
    """`analysis/SYN-TECH-01` porte au moins une grappe de preuve TITRÉE.

    Sur le code d'avant le correctif, `evidence.clusters` est VIDE : la
    déclaration du rail ne nomme que les dépêches, et aucune dépêche
    synthétique ne parle de ce ticker.
    """
    _drain(session_factory)
    content = _analysis_content(session_factory)

    clusters = content["evidence"]["clusters"]
    assert clusters, (
        "rail de preuves vide : la famille des événements de calendrier "
        "n'est pas déclarée par le consommateur du rail "
        f"(evidence={content['evidence']})"
    )
    for cluster in clusters:
        titre = cluster["title"]
        assert isinstance(titre, str) and titre.strip(), cluster
    assert any(INSTRUMENT in cluster["title"] for cluster in clusters), clusters


@pytest.mark.usefixtures("migrated_engine")
def test_le_rail_d_opportunites_porte_les_memes_grappes(
    session_factory: SessionFactory,
) -> None:
    """Second consommateur du rail : le candidat cite les mêmes grappes.

    Opportunités recalcule chaque dossier par `build_analysis_content` : une
    famille non déclarée l'affame exactement de la même façon.
    """
    _drain(session_factory)
    attendu = [
        cluster["cluster_id"]
        for cluster in _analysis_content(session_factory)["evidence"]["clusters"]
    ]
    assert attendu, "rail d'Analyse vide : la comparaison ne prouverait rien"

    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_OPPORTUNITIES, key=OPPORTUNITIES_KEY
        )
    assert snapshot is not None, "aucun instantané d'Opportunités publié"
    candidats = [
        candidate
        for candidate in (*snapshot.content["qualified"], *snapshot.content["excluded"])
        if candidate["ticker"] == INSTRUMENT
    ]
    assert len(candidats) == 1, candidats
    assert candidats[0]["evidence_cluster_ids"] == attendu


@pytest.mark.usefixtures("migrated_engine")
def test_la_file_d_attention_ne_lit_toujours_pas_les_evenements_de_calendrier(
    session_factory: SessionFactory,
) -> None:
    """TÉMOIN du partage : la même base, sans dépêche, laisse la file VIDE.

    Élargir le rail de preuves ne réouvre pas la file d'attention aux
    événements de calendrier : ce sont deux déclarations distinctes, et
    celle de la file n'a pas bougé.
    """
    _drain(session_factory)
    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL
        )
    assert snapshot is not None, "aucun instantané d'attention publié"
    assert snapshot.content["items"] == []
    assert snapshot.content["population"] == POPULATION_EMPTY
    assert "synthetic-calendar-event/" not in (
        snapshot.content["coverage"]["content_schema_prefixes"]
    )
