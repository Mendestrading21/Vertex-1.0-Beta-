"""Familles déclarées : un préfixe est un LITTÉRAL, jamais un motif ``LIKE``.

CE TEST EXISTE À CAUSE D'UNE RÉSERVE DE REVUE (S0, réserve 4).
`load_recent_observation_records` applique les familles déclarées par
``LIKE '<préfixe>%'`` sans échapper ``%`` ni ``_``, et `_require_schema_prefixes`
ne les refuse pas. Un souligné dans une famille déclarée vaut alors « n'importe
quel caractère » et un pourcent « n'importe quelle suite » : une famille que le
consommateur n'a PAS déclarée entre dans sa fenêtre. Sans effet sur les
familles actuelles (aucune ne porte ``%`` ni ``_``) — le contrat « deny by
default » ne tient qu'à ce hasard, et c'est ce que ce test refuse.

Le parcours mesuré, contre PostgreSQL : observations écrites telles qu'elles
existeraient en base (`insert_observation`, sans message), puis le chargeur
appelé avec la déclaration du consommateur. Attendu : SEULES les lignes dont
le ``schema_version`` COMMENCE PAR le préfixe, caractère pour caractère.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from vertex_persistence.repository.observations import insert_observation
from vertex_worker.handlers import load_recent_observation_records

NOW = datetime(2026, 9, 3, 10, 0, 0, tzinfo=UTC)
LOOKBACK = timedelta(hours=72)
SOURCE = "demo-source"
RIGHTS = "DEMO"


def ecrire(session: Any, *, event_id: str, schema_version: str, rang: int) -> None:
    """Une dépêche minimale (titre + entités) sous le schéma demandé."""
    instant = NOW - timedelta(minutes=10 + rang)
    inseree = insert_observation(
        session,
        event_id=event_id,
        schema_version=schema_version,
        source=SOURCE,
        source_event_id=event_id,
        instrument_ref="1",
        observed_at=instant,
        published_at=instant,
        received_at=instant,
        as_of=instant,
        stale_after=instant + timedelta(hours=24),
        quality_status="VALID",
        delay_status="LIVE",
        connection_epoch=1,
        rights=RIGHTS,
        payload={"title": f"dépêche {event_id}", "entities": ["1"]},
    )
    assert inseree, f"observation dupliquée : {event_id}"


def familles_chargees(session: Any, prefixes: tuple[str, ...]) -> list[str]:
    fenetre = load_recent_observation_records(
        session, now=NOW, lookback=LOOKBACK, limit=100, schema_prefixes=prefixes
    )
    return sorted(record.schema_version for record in fenetre)


@pytest.mark.usefixtures("migrated_engine")
def test_un_souligne_dans_une_famille_declaree_n_est_pas_un_joker(db_session: Any) -> None:
    """``demo_news/`` déclaré : ``demoXnews/1.0`` et ``demo-news/1.0`` restent dehors.

    Avant le correctif : ``LIKE 'demo_news/%'`` accepte les trois lignes.
    """
    ecrire(db_session, event_id="souligne", schema_version="demo_news/1.0", rang=0)
    ecrire(db_session, event_id="lettre", schema_version="demoXnews/1.0", rang=1)
    ecrire(db_session, event_id="tiret", schema_version="demo-news/1.0", rang=2)
    db_session.commit()

    assert familles_chargees(db_session, ("demo_news/",)) == ["demo_news/1.0"], (
        "un souligné dans une famille déclarée a été lu comme un joker LIKE"
    )


@pytest.mark.usefixtures("migrated_engine")
def test_un_pourcent_dans_une_famille_declaree_n_est_pas_un_joker(db_session: Any) -> None:
    """``demo%`` déclaré : seule une famille commençant LITTÉRALEMENT par
    ``demo%`` entre ; ``demo-news/1.0`` reste dehors.

    Avant le correctif : ``LIKE 'demo%%'`` accepte tout ce qui commence par
    ``demo``.
    """
    ecrire(db_session, event_id="pourcent", schema_version="demo%-news/1.0", rang=0)
    ecrire(db_session, event_id="tiret", schema_version="demo-news/1.0", rang=1)
    db_session.commit()

    assert familles_chargees(db_session, ("demo%",)) == ["demo%-news/1.0"], (
        "un pourcent dans une famille déclarée a été lu comme un joker LIKE"
    )


@pytest.mark.usefixtures("migrated_engine")
def test_le_separateur_de_famille_est_lu_tel_quel(db_session: Any) -> None:
    """Toutes les familles réelles finissent par ``/`` : il doit rester un
    caractère ordinaire, quel que soit le caractère d'échappement retenu."""
    ecrire(db_session, event_id="dedans", schema_version="demo-news/1.0", rang=0)
    ecrire(db_session, event_id="dehors", schema_version="demo-newsletter/1.0", rang=1)
    db_session.commit()

    assert familles_chargees(db_session, ("demo-news/",)) == ["demo-news/1.0"]
