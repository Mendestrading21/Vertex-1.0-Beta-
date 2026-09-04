"""Une DÉCLARATION DE CAPACITÉ DE LECTURE n'est pas une PROVENANCE (S0).

DÉFAUT MESURÉ sur la pile vivante (base ``vertex_live``, 2026-09-04 11:43 UTC) :

    GET /api/v1/today/attention  -> 500 {"code":"SNAPSHOT_CONTENT_INVALID"}
    GET /api/v1/follow-up/queue  -> 500 idem

``checked_relayed_content`` refusait le contenu réellement publié avec

    population: the content claims an observation while carrying a synthetic
    provenance marker at coverage.content_schema_prefixes[0]
    populations.information_context: ... at coverage.content_schema_prefixes[0]

Le lot S0 fait publier au worker, DANS LA COUVERTURE, la liste des familles de
schéma que le consommateur SAIT LIRE (``vertex_worker.handlers.build_attention_content``
et ``vertex_worker.follow_up.build_review_queue_content``) :

    "content_schema_prefixes": ["synthetic-news/", "ibkr.news-headline/"]

Le balayage de provenance y voyait le préfixe ``synthetic-`` et concluait que
la donnée servie était générée, alors que la population déclarée était ``REAL``.
C'est un FAUX POSITIF : cette clé décrit ce que le consommateur accepte de LIRE,
pas d'où viennent les observations RETENUES. En CI la population est
``SYNTHETIC``, la contradiction n'existait pas, et le défaut n'a été vu que sur
données réelles.

CE MODULE TIENT LES DEUX BOUTS, par le VRAI chemin HTTP :

1. un contenu ``REAL`` portant la déclaration est SERVI (200) ;
2. un contenu ``REAL`` portant un VRAI marqueur de provenance synthétique dans
   les éléments servis (source, droits, identifiant d'événement, titre généré,
   nature imbriquée) est TOUJOURS REFUSÉ (500 typé). Le garde n'est pas désarmé :
   si quelqu'un l'affaiblit, ces témoins virent au rouge.

Tout est SYNTHÉTIQUE ici : le lecteur d'instantanés est injecté par
``dependency_overrides``, aucun chemin de production ne l'atteint.
"""

from __future__ import annotations

from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import (
    CAPABILITY_DECLARATION_PATHS,
    checked_relayed_content,
    is_synthetic_marker,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot
from vertex_worker.follow_up import build_review_queue_content
from vertex_worker.handlers import (
    CONTENT_SCHEMA_PREFIXES,
    DEV_SYNTHETIC_CONFIG,
    build_attention_content,
)

AS_OF = datetime(2026, 9, 4, 11, 43, 0, tzinfo=UTC)
#: Horloge FIXE du relais : sans elle l'instantané deviendrait périmé au fil
#: des jours et ces tests échoueraient sans qu'aucun comportement ait changé.
_NOW = AS_OF + timedelta(minutes=5)

#: La déclaration EXACTE que le worker publie depuis le lot S0
#: (``vertex_worker.handlers.CONTENT_SCHEMA_PREFIXES``). Elle est recopiée ici
#: plutôt qu'importée : l'API ne dépend pas du worker, et le témoin de dérive
#: qui apparie les deux vit côté worker.
DECLARED_PREFIXES = ["synthetic-news/", "ibkr.news-headline/"]


def real_attention_content() -> dict[str, Any]:
    """Copie de la forme publiée par le worker, population ``REAL``.

    Aucune valeur ne porte de marqueur de provenance synthétique : la source,
    les droits, les identifiants et le titre sont ceux d'une dépêche observée.
    La SEULE occurrence du mot « synthetic » est la DÉCLARATION de capacité.
    """
    return {
        "schema_version": "vertex.attention-queue/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "REAL",
        "policy_version": "relevance-policy/1.0",
        "fusion_ruleset_version": "fusion/1.0",
        "items": [
            {
                "item_id": "ibkr:news:0001",
                "title": "Apple releases quarterly results",
                "synthetic": False,
                "priority_class": "P2",
                "relevance_reasons": ["reason-one", "reason-two"],
                "age_seconds": 120,
                "source_tier": "P1",
                "quality": "VALID",
                "provenance": {
                    "cluster_id": "cluster-0001",
                    "member_event_ids": ["ibkr:news:0001"],
                    "sources": ["ibkr"],
                    "rights": ["IBKR_MARKET_DATA_DISPLAY_ONLY"],
                    "first_published_at": AS_OF.isoformat(),
                    "last_received_at": AS_OF.isoformat(),
                    "instrument_ref": "AAPL:NASDAQ:STK:USD",
                },
            }
        ],
        "conflicts": [],
        "rejected": [],
        "coverage": {
            "lookback_seconds": 259200,
            "content_schema_prefixes": list(DECLARED_PREFIXES),
            "max_items": 15,
            "observations_considered": 4,
            "content_observations": 2,
            "non_content_observations": 2,
            "synthetic_observations": 0,
            "non_synthetic_observations": 4,
            "clusters": 1,
            "polarity_conflicts": 0,
            "ranked": 1,
            "rejected": 0,
            "published_items": 1,
            "truncated_ranked": 0,
        },
    }


def real_queue_content() -> dict[str, Any]:
    """Copie de la forme publiée par ``build_review_queue_content``.

    ``populations.information_context`` vaut ``REAL`` : c'est la seconde
    étiquette que le défaut mesuré nommait dans son refus.
    """
    return {
        "schema_version": "vertex.review-queue/1.0",
        "as_of": AS_OF.isoformat(),
        "populations": {"theses": "USER_DECLARED", "information_context": "REAL"},
        "ordering": {
            "method": "lexicographic",
            "keys": ["effective_review_due_at asc", "thesis_id asc"],
            "note": "new information raises urgency but never rewrites the thesis",
        },
        "theses": [
            {
                "thesis": {
                    "id": 1,
                    "portfolio_id": None,
                    "instrument": {"ticker": "AAPL"},
                    "title": "Apple keeps its margin",
                    "hypotheses": "the services mix keeps the gross margin above 45%",
                    "invalidation": "gross margin below 40% for two quarters",
                    "horizon": "3m",
                    "review_due_at": AS_OF.isoformat(),
                    "created_at": AS_OF.isoformat(),
                },
                "state": {
                    "status": "ACTIVE",
                    "review_due_at": AS_OF.isoformat(),
                    "is_due": True,
                    "snooze_until": None,
                    "last_reviewed_at": None,
                    "last_action": "CREATED",
                    "last_recorded_at": AS_OF.isoformat(),
                    "revision_count": 1,
                },
                "instrument_ticker": "AAPL",
                "information_context": {"population": "REAL", "clusters": []},
                "has_new_information": False,
                "urgency_reasons": [],
            }
        ],
        "due": [
            {
                "rank": 1,
                "thesis_id": 1,
                "title": "Apple keeps its margin",
                "review_due_at": AS_OF.isoformat(),
                "overdue_seconds": 0,
                "last_recorded_at": AS_OF.isoformat(),
                "has_new_information": False,
                "urgency_reasons": [],
            }
        ],
        "coverage": {
            "theses_total": 1,
            "due_count": 1,
            "theses_with_instrument": 1,
            "theses_with_new_information": 0,
            "observations_considered": 4,
            "content_observations": 2,
            "clusters": 1,
            "lookback_seconds": 259200,
            "content_schema_prefixes": list(DECLARED_PREFIXES),
        },
    }


def _snapshot(kind: str, content: dict[str, Any]) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind=kind,
        key="global",
        version=7,
        content=content,
        content_hash="sha256:" + "0" * 64,
        as_of=AS_OF,
    )


def _client(app: FastAPI, reader: FakeSnapshotReader) -> Iterator[TestClient]:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    app.dependency_overrides[get_clock] = lambda: (lambda: _NOW)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def attention_client(app: FastAPI) -> Iterator[TestClient]:
    reader = FakeSnapshotReader(
        {("attention", "global"): _snapshot("attention", real_attention_content())}
    )
    yield from _client(app, reader)


@pytest.fixture()
def queue_client(app: FastAPI) -> Iterator[TestClient]:
    reader = FakeSnapshotReader(
        {("review_queue", "global"): _snapshot("review_queue", real_queue_content())}
    )
    yield from _client(app, reader)


# -- 1. la déclaration de capacité ne refuse plus rien ----------------------


def test_real_attention_carrying_the_capability_declaration_is_served(
    attention_client: TestClient,
) -> None:
    """Le défaut du 2026-09-04 : cette route répondait 500 sur données réelles."""
    response = attention_client.get("/api/v1/today/attention")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["state"] == "ok"
    assert body["population"] == "REAL"
    # La déclaration est SERVIE telle quelle : elle explique au lecteur quelles
    # familles ont été lues, elle ne disparaît pas du rapport de couverture.
    assert body["coverage"]["content_schema_prefixes"] == DECLARED_PREFIXES
    assert len(body["items"]) == 1


def test_real_review_queue_carrying_the_capability_declaration_is_served(
    queue_client: TestClient,
) -> None:
    """Même défaut, seconde route : ``populations.information_context``."""
    response = queue_client.get("/api/v1/follow-up/queue")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["state"] == "ok"
    # La file de revue relaie son contenu VERBATIM sous ``content``.
    assert body["content"]["populations"]["information_context"] == "REAL"
    assert (
        body["content"]["coverage"]["content_schema_prefixes"] == DECLARED_PREFIXES
    )


# -- 2. témoins : le garde reste armé --------------------------------------
#
# Chaque variante plante un VRAI marqueur de provenance dans les éléments
# SERVIS d'un contenu qui se déclare ``REAL``. Le refus attendu est le 500
# typé du relais. Supprimer l'exclusion de déclaration ne les rend pas verts ;
# élargir l'exclusion (par clé feuille, par motif, par sous-arbre) les rend
# ROUGES — c'est exactement ce qu'ils sont là pour empêcher.


def _attention_with(mutate: Any) -> dict[str, Any]:
    content = real_attention_content()
    mutate(content)
    return content


ATTENTION_FORGERIES = {
    # La source réellement retenue est celle du générateur.
    "source": lambda c: c["items"][0]["provenance"].update(sources=["synthetic-dev"]),
    # Les droits portés par les observations fusionnées.
    "rights": lambda c: c["items"][0]["provenance"].update(rights=["SYNTHETIC"]),
    # L'identifiant d'événement minté par le générateur.
    "event_id": lambda c: c["items"][0]["provenance"].update(
        member_event_ids=["synthetic-dev:evt:0001"]
    ),
    # Le titre que le générateur préfixe.
    "title": lambda c: c["items"][0].update(title="[SYNTHETIC] generated headline"),
    # L'auto-déclaration explicite du producteur.
    "self_declaration": lambda c: c["items"][0].update(synthetic=True),
    # Un identifiant d'instrument que seul le générateur mint.
    "minted_ticker": lambda c: c["items"][0]["provenance"].update(
        sources=["synthetic-dev"], ticker="SYN-TECH-01"
    ),
}


@pytest.mark.parametrize("forgery", sorted(ATTENTION_FORGERIES))
def test_a_real_claim_over_a_synthetic_marker_is_still_refused(
    app: FastAPI, forgery: str
) -> None:
    content = _attention_with(ATTENTION_FORGERIES[forgery])
    reader = FakeSnapshotReader(
        {("attention", "global"): _snapshot("attention", content)}
    )
    for test_client in _client(app, reader):
        response = test_client.get("/api/v1/today/attention")
        assert response.status_code == 500
        assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"


QUEUE_FORGERIES = {
    "nested_nature": lambda c: c["theses"][0]["information_context"].update(
        population="SYNTHETIC"
    ),
    "cluster_source": lambda c: c["theses"][0]["information_context"].update(
        clusters=[{"cluster_id": "c-1", "sources": ["synthetic-dev"]}]
    ),
    "generated_title": lambda c: c["due"][0].update(
        title="[SYNTHETIC] generated thesis title"
    ),
}


@pytest.mark.parametrize("forgery", sorted(QUEUE_FORGERIES))
def test_a_real_information_context_over_a_marker_is_still_refused(
    app: FastAPI, forgery: str
) -> None:
    content = real_queue_content()
    QUEUE_FORGERIES[forgery](content)
    reader = FakeSnapshotReader(
        {("review_queue", "global"): _snapshot("review_queue", content)}
    )
    for test_client in _client(app, reader):
        response = test_client.get("/api/v1/follow-up/queue")
        assert response.status_code == 500
        assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"


# -- 3. l'exclusion est ANCRÉE : elle ne s'applique qu'à ce chemin ----------


def test_the_same_string_elsewhere_in_the_content_is_still_a_marker(
    app: FastAPI,
) -> None:
    """``synthetic-news/1.0`` ailleurs reste une PROVENANCE, pas une capacité.

    C'est la différence que le correctif doit tenir : la même chaîne, un autre
    chemin. Ici elle est publiée comme la version de schéma d'un élément servi.
    """
    content = real_attention_content()
    content["items"][0]["provenance"]["schema_version"] = "synthetic-news/1.0"
    reader = FakeSnapshotReader(
        {("attention", "global"): _snapshot("attention", content)}
    )
    for test_client in _client(app, reader):
        response = test_client.get("/api/v1/today/attention")
        assert response.status_code == 500
        assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"


def test_a_declaration_published_outside_the_coverage_block_is_not_excluded(
    app: FastAPI,
) -> None:
    """Aucun producteur ne publie cette clé hors de ``coverage`` aujourd'hui.

    Si l'un le faisait demain, le garde continuerait de la lire comme une
    provenance : l'exclusion nomme un CHEMIN, pas une clé feuille. Le remède
    serait d'ajouter ce chemin à la liste — une décision explicite, pas un
    élargissement silencieux du motif de détection.
    """
    content = real_attention_content()
    content["content_schema_prefixes"] = list(DECLARED_PREFIXES)
    reader = FakeSnapshotReader(
        {("attention", "global"): _snapshot("attention", content)}
    )
    for test_client in _client(app, reader):
        response = test_client.get("/api/v1/today/attention")
        assert response.status_code == 500
        assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"


def test_the_declaration_does_not_disarm_the_form_check(app: FastAPI) -> None:
    """Le chemin exclu du BALAYAGE reste soumis au contrôle de FORME.

    Une déclaration vide n'est pas un préfixe : elle est refusée comme
    n'importe quelle chaîne relayée. L'exclusion retire une INTERPRÉTATION,
    elle ne retire pas une vérification.
    """
    content = deepcopy(real_attention_content())
    content["coverage"]["content_schema_prefixes"] = [""]
    reader = FakeSnapshotReader(
        {("attention", "global"): _snapshot("attention", content)}
    )
    for test_client in _client(app, reader):
        response = test_client.get("/api/v1/today/attention")
        assert response.status_code == 500
        assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"


# -- 4. dérive : ce que les worker publient VRAIMENT ------------------------
#
# Les fixtures ci-dessus sont des COPIES de la forme publiée. Une copie peut
# vieillir sans bruit : cette section appelle les VRAIS constructeurs et refait
# passer leur sortie par le garde. Si un lot ajoute demain une seconde
# déclaration de capacité dans une couverture — un ``*_prefixes``, un
# ``*_families``, une famille de schéma quelconque — ces tests virent au rouge
# ici, en CI, au lieu d'attendre une base réelle pour rendre un 500.


def _published_contents() -> dict[str, dict[str, Any]]:
    """Les deux contenus S0, construits par leurs vrais constructeurs.

    Aucune observation n'est fournie : le contenu est celui d'une fenêtre
    vide, donc sans élément servi — ne restent que les blocs de tête et la
    couverture, c'est-à-dire exactement ce que cette section examine.
    """
    return {
        "attention": build_attention_content(
            [], now=AS_OF, config=DEV_SYNTHETIC_CONFIG
        ),
        "review_queue": build_review_queue_content(
            [], [], [], now=AS_OF, config=DEV_SYNTHETIC_CONFIG
        ),
    }


def _flagged_paths(content: Any, path: str = "") -> set[str]:
    """Chemins des chaînes que le balayage lirait comme un marqueur."""
    if isinstance(content, dict):
        found: set[str] = set()
        for key, value in content.items():
            found |= _flagged_paths(value, f"{path}.{key}" if path else key)
        return found
    if isinstance(content, list):
        found = set()
        for index, value in enumerate(content):
            found |= _flagged_paths(value, f"{path}[{index}]")
        return found
    if isinstance(content, str) and is_synthetic_marker(content, path):
        return {path}
    return set()


def test_the_workers_declarations_are_the_only_flagged_strings_they_publish() -> None:
    """Aucune AUTRE famille ne tombe dans le même piège aujourd'hui.

    Chaque chaîne que le balayage lirait comme un marqueur, dans ce que les
    deux constructeurs publient, doit être un chemin DÉCLARÉ. Une nouvelle
    déclaration publiée ailleurs ferait échouer ce test avant d'atteindre la
    production.
    """
    for name, content in _published_contents().items():
        flagged = _flagged_paths(content)
        declared = {
            path
            for path in flagged
            if path.split("[")[0] in CAPABILITY_DECLARATION_PATHS
        }
        assert flagged == declared, (name, sorted(flagged - declared))


def test_the_declared_path_is_where_the_worker_really_publishes_it() -> None:
    """Le chemin exclu est celui que le worker écrit, pas un chemin supposé."""
    contents = _published_contents()
    assert contents["attention"]["coverage"]["content_schema_prefixes"] == list(
        CONTENT_SCHEMA_PREFIXES
    )
    assert contents["review_queue"]["coverage"]["content_schema_prefixes"] == list(
        CONTENT_SCHEMA_PREFIXES
    )
    assert "coverage.content_schema_prefixes" in CAPABILITY_DECLARATION_PATHS


def test_what_the_workers_publish_is_accepted_under_a_real_head() -> None:
    """Le cas mesuré sur la pile vivante, rejoué sur la sortie réelle.

    La tête est portée à ``REAL`` — c'est l'état de production quand aucune
    observation retenue n'est synthétique — et le garde doit servir.
    """
    contents = _published_contents()
    attention = contents["attention"]
    attention["population"] = "REAL"
    checked_relayed_content(attention)

    queue = contents["review_queue"]
    queue["populations"]["information_context"] = "REAL"
    checked_relayed_content(queue)
