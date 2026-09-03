"""Le budget de fraîcheur est PUBLIÉ à côté de l'âge : la jauge se sert, elle ne se calcule pas.

CE QUE CES TESTS FERMENT. Depuis le lot « âge publié », chaque relais datable
sert ``age_seconds``. Mais le budget contre lequel cet âge est jugé — le TTL
de séance fermée de la politique du registre, que `vertex_api.freshness`
connaît et nomme dans sa raison ``stale`` — restait un secret du serveur.
L'interface recevait un âge sans échelle : « il y a 71 h » ne dit pas si
c'est la moitié ou le double de ce que la donnée tolère, et le seul moyen
de le savoir aurait été de recopier le registre côté client — un second
modèle concurrent, exactement ce que ce dépôt refuse.

Le correctif est de publier les COORDONNÉES de la jauge sur chaque réponse
datable : ``freshness_policy = {budget_seconds, kind, version}``. Le client
pose l'âge sur l'échelle qu'on lui donne ; il n'invente ni TTL ni ratio.

Trois affirmations, pour chaque route datable :

1. ``freshness_policy`` est servi par HTTP, et ses valeurs sont EXACTEMENT
   celles du registre (`vertex_core.data.freshness`), jamais un nombre local ;
2. ``budget_seconds`` est cohérent avec ``age_seconds`` et ``state`` : dans le
   budget ``ok``, au-delà ``stale`` — la bascule se lit sur les coordonnées
   publiées, sans arithmétique client ;
3. la matrice de capacités, SEULE famille sans budget au registre, publie une
   absence déclarée (``null``), jamais un zéro ni un TTL inventé.

L'agenda (`calendar`) entre dans la table par le correctif du LOT-S5 : ce
relais MESURAIT son âge — il basculait sur ``stale`` et nommait le budget dans
sa raison — sans le SERVIR. Il publie désormais ``age_seconds`` et sa jauge
dans chaque état daté, comme les autres.

Les contenus valides sont importés des tests qui les possèdent : une copie
divergerait du vrai et prouverait autre chose.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from portfolio_fakes import FakePortfolioGateway
from pydantic import ValidationError
from snapshot_fakes import FakeSnapshotReader, synthetic_session
from test_analysis import AS_OF as ANALYSIS_AS_OF
from test_analysis import analysis_content
from test_calendar_route import event as calendar_event
from test_calendar_route import snapshot as calendar_snapshot
from test_markets_overview import markets_content
from test_opportunities_route import opportunities_content
from test_option_chain import chain_content
from test_portfolio_routes import SYNTHETIC_VALUATION
from test_risk_route import contenu as risk_content
from test_sec_fundamentals_route import content as sec_content
from test_snapshot_content_errors import (
    _valid_performance_content,
    _valid_review_queue_content,
)
from test_system_capabilities import capabilities_snapshot
from test_today_attention import attention_content

from vertex_api import calendar as calendar_module
from vertex_api import opportunities as opportunities_module
from vertex_api.auth import require_session
from vertex_api.calendar import build_calendar_response
from vertex_api.capability_manifest import load_capability_manifest
from vertex_api.follow_up import build_follow_up_queue_response
from vertex_api.freshness import closed_session_budget, published_budget
from vertex_api.opportunities import build_opportunities_response
from vertex_api.performance import build_performance_response
from vertex_api.portfolio import build_portfolio_response
from vertex_api.risk import build_risk_response
from vertex_api.routes import get_portfolio_gateway
from vertex_api.schemas import FreshnessPolicyView
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import (
    CAPABILITIES_FRESHNESS_POLICY,
    build_analysis_response,
    build_attention_response,
    build_capabilities_response,
    build_markets_overview_response,
    build_option_chain_response,
    build_sec_fundamentals_response,
)
from vertex_core.data.freshness import FRESHNESS_POLICIES, get_freshness_policy
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = ANALYSIS_AS_OF
"""Instant de publication commun à tous les contenus importés (2026-08-25 12:00 UTC)."""

INSTRUMENT = "SYN-TECH-01"
SEC_INSTRUMENT = "AAPL"


def _snapshot(kind: str, key: str, content: dict[str, Any]) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind=kind,
        key=key,
        version=7,
        content=content,
        content_hash="sha256:freshness-budget",
        as_of=AS_OF,
    )


def _sec_snapshot() -> CurrentSnapshot:
    # Le contenu SEC importé est daté du 28 août : il est réaligné sur AS_OF
    # pour que toutes les routes soient mesurées contre la MÊME horloge.
    content = sec_content()
    content["as_of"] = AS_OF.isoformat()
    return _snapshot("sec_fundamentals", SEC_INSTRUMENT, content)


def _calendar_snapshot() -> CurrentSnapshot:
    """Un agenda dont l'événement reste dans son propre ``stale_after`` bien
    au-delà du budget de l'agenda : seule la bascule du BUDGET est mesurée."""
    entry = calendar_event("syn-ev-1")
    entry["stale_after"] = (AS_OF + timedelta(days=30)).isoformat()
    return calendar_snapshot([entry], version=7)


def _expected_view(policy_name: str) -> dict[str, Any]:
    """La projection ATTENDUE, relue du registre — jamais recopiée d'un souvenir."""
    policy = get_freshness_policy(policy_name)
    return {
        "budget_seconds": policy.ttl_closed_seconds,
        "kind": policy.name,
        "version": policy.version,
    }


# ---------------------------------------------------------------------------
# Par constructeur : chaque relais datable, avec sa politique DÉCLARÉE
# ---------------------------------------------------------------------------

Build = Callable[[datetime], Any]

RELAIS: tuple[Any, ...] = (
    pytest.param(
        "news_attention",
        lambda now: build_attention_response(
            _snapshot("attention", "global", attention_content()), now=now
        ),
        id="attention",
    ),
    pytest.param(
        "daily_bar",
        lambda now: build_markets_overview_response(
            _snapshot("markets_overview", "global", markets_content()), now=now
        ),
        id="markets_overview",
    ),
    pytest.param(
        "daily_bar",
        lambda now: build_analysis_response(
            _snapshot("analysis", INSTRUMENT, analysis_content()),
            instrument=INSTRUMENT,
            now=now,
        ),
        id="analysis",
    ),
    pytest.param(
        "option_surface",
        lambda now: build_option_chain_response(
            _snapshot("option_chain", INSTRUMENT, chain_content()),
            underlying=INSTRUMENT,
            now=now,
        ),
        id="option_chain",
    ),
    pytest.param(
        "fundamental_filing",
        lambda now: build_sec_fundamentals_response(
            _sec_snapshot(), instrument=SEC_INSTRUMENT, now=now
        ),
        id="sec_fundamentals",
    ),
    pytest.param(
        "news_attention",
        lambda now: build_follow_up_queue_response(
            _snapshot("review_queue", "global", _valid_review_queue_content()), now=now
        ),
        id="review_queue",
    ),
    pytest.param(
        "daily_bar",
        lambda now: build_performance_response(
            _snapshot("performance", "1", _valid_performance_content()),
            portfolio_id=1,
            now=now,
        ),
        id="performance",
    ),
    pytest.param(
        "daily_bar",
        lambda now: build_risk_response(
            _snapshot("risk_matrix", "global", risk_content()), now=now
        ),
        id="risk_matrix",
    ),
    pytest.param(
        "daily_bar",
        lambda now: build_opportunities_response(
            _snapshot("opportunities", "global", opportunities_content([], [])), now=now
        ),
        id="opportunities",
    ),
    pytest.param(
        "corporate_event",
        lambda now: build_calendar_response(_calendar_snapshot(), window=None, now=now),
        id="calendar",
    ),
)


@pytest.mark.parametrize(("policy_name", "build"), RELAIS)
def test_le_budget_publie_est_celui_du_registre(policy_name: str, build: Build) -> None:
    """Le budget servi est le TTL de séance fermée de la politique DÉCLARÉE :
    la même valeur que `closed_session_budget`, jamais un nombre local."""
    policy = get_freshness_policy(policy_name)
    response = build(AS_OF + timedelta(minutes=1))
    assert response.freshness_policy is not None
    assert response.freshness_policy.budget_seconds == int(
        closed_session_budget(policy).total_seconds()
    )
    assert response.freshness_policy.kind == policy.name
    assert response.freshness_policy.version == policy.version
    assert response.freshness_policy.model_dump() == _expected_view(policy_name)


@pytest.mark.parametrize(("policy_name", "build"), RELAIS)
def test_les_coordonnees_publiees_suffisent_a_lire_la_bascule(
    policy_name: str, build: Build
) -> None:
    """Dans le budget : ``age_seconds <= budget_seconds`` et ``ok`` ; au-delà :
    ``age_seconds > budget_seconds`` et ``stale``. Le client compare deux
    entiers servis, il ne recalcule rien."""
    budget = get_freshness_policy(policy_name).ttl_closed_seconds

    dans_le_budget = build(AS_OF + timedelta(seconds=budget))
    assert dans_le_budget.state == "ok"
    assert dans_le_budget.age_seconds == budget
    assert dans_le_budget.age_seconds <= dans_le_budget.freshness_policy.budget_seconds

    perime = build(AS_OF + timedelta(seconds=budget + 1))
    assert perime.state == "stale"
    assert perime.age_seconds == budget + 1
    assert perime.age_seconds > perime.freshness_policy.budget_seconds
    # Le budget publié est CELUI que la raison nomme : une seule source.
    assert str(perime.freshness_policy.budget_seconds) in perime.reason
    assert perime.freshness_policy.kind in perime.reason
    assert perime.freshness_policy.version in perime.reason


@pytest.mark.parametrize(("policy_name", "build"), RELAIS)
def test_le_budget_ne_change_pas_avec_l_age(policy_name: str, build: Build) -> None:
    """Le budget est une propriété de la ROUTE, pas de l'instantané : il est
    identique à une minute et à trois jours. Seul l'âge bouge."""
    tot = build(AS_OF + timedelta(minutes=1)).freshness_policy
    tard = build(AS_OF + timedelta(days=3)).freshness_policy
    assert tot == tard


# ---------------------------------------------------------------------------
# Par route HTTP : ce que le client reçoit vraiment
# ---------------------------------------------------------------------------

NOW = AS_OF + timedelta(minutes=30)


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader(
        {
            ("attention", "global"): _snapshot("attention", "global", attention_content()),
            ("markets_overview", "global"): _snapshot(
                "markets_overview", "global", markets_content()
            ),
            ("analysis", INSTRUMENT): _snapshot("analysis", INSTRUMENT, analysis_content()),
            ("option_chain", INSTRUMENT): _snapshot("option_chain", INSTRUMENT, chain_content()),
            ("sec_fundamentals", SEC_INSTRUMENT): _sec_snapshot(),
            ("review_queue", "global"): _snapshot(
                "review_queue", "global", _valid_review_queue_content()
            ),
            ("performance", "1"): _snapshot("performance", "1", _valid_performance_content()),
            ("risk_matrix", "global"): _snapshot("risk_matrix", "global", risk_content()),
            ("opportunities", "global"): _snapshot(
                "opportunities", "global", opportunities_content([], [])
            ),
            ("capabilities", "global"): capabilities_snapshot([]),
            ("calendar", "global"): _calendar_snapshot(),
        }
    )


@pytest.fixture()
def api(
    app: FastAPI, reader: FakeSnapshotReader, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    app.dependency_overrides[get_portfolio_gateway] = lambda: FakePortfolioGateway(
        valuation=SYNTHETIC_VALUATION
    )
    # Horloge FIXE, sur les deux coutures : la dépendance FastAPI et la
    # couture propre du relais des opportunités.
    app.dependency_overrides[get_clock] = lambda: lambda: NOW
    monkeypatch.setattr(opportunities_module, "_utc_now", lambda: NOW)
    monkeypatch.setattr(calendar_module, "_utc_now", lambda: NOW)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


ROUTES: tuple[Any, ...] = (
    pytest.param("/api/v1/today/attention", "news_attention", id="today_attention"),
    pytest.param("/api/v1/markets/overview", "daily_bar", id="markets_overview"),
    pytest.param(f"/api/v1/analysis/{INSTRUMENT}", "daily_bar", id="analysis"),
    pytest.param(
        f"/api/v1/sources/sec/{SEC_INSTRUMENT}/fundamentals",
        "fundamental_filing",
        id="sec_fundamentals",
    ),
    pytest.param(f"/api/v1/options/{INSTRUMENT}/chain", "option_surface", id="option_chain"),
    pytest.param("/api/v1/follow-up/queue", "news_attention", id="follow_up_queue"),
    pytest.param("/api/v1/performance/1", "daily_bar", id="performance"),
    pytest.param("/api/v1/risk/matrix", "daily_bar", id="risk_matrix"),
    pytest.param("/api/v1/opportunities", "daily_bar", id="opportunities"),
    pytest.param("/api/v1/calendar", "corporate_event", id="calendar"),
)


@pytest.mark.parametrize(("path", "policy_name"), ROUTES)
def test_chaque_route_datable_sert_son_budget(api: TestClient, path: str, policy_name: str) -> None:
    response = api.get(path)
    assert response.status_code == 200, path
    body = response.json()
    assert body["state"] == "ok", path
    assert body["freshness_policy"] == _expected_view(policy_name), path
    assert body["age_seconds"] is not None
    assert body["age_seconds"] <= body["freshness_policy"]["budget_seconds"]


@pytest.mark.parametrize(("path", "policy_name"), ROUTES)
def test_l_etat_vide_declare_encore_le_budget_de_la_route(
    app: FastAPI, path: str, policy_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sans instantané, l'âge est ``null`` — il n'existe pas — mais le budget
    est une propriété de la ROUTE et reste servi : le client sait quelle
    échelle attendre, et « absent » n'est pas converti en zéro."""
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: FakeSnapshotReader()
    app.dependency_overrides[get_clock] = lambda: lambda: NOW
    monkeypatch.setattr(opportunities_module, "_utc_now", lambda: NOW)
    monkeypatch.setattr(calendar_module, "_utc_now", lambda: NOW)
    with TestClient(app) as client:
        body = client.get(path).json()
    app.dependency_overrides.clear()
    assert body["state"] == "empty", path
    assert body["age_seconds"] is None
    assert body["freshness_policy"] == _expected_view(policy_name), path


def test_la_valorisation_du_portefeuille_sert_son_budget(api: TestClient) -> None:
    """Le portefeuille porte sa valorisation dans un bloc imbriqué : la jauge
    est servie là où l'âge l'est, avec la politique ``portfolio_mark``."""
    body = api.get("/api/v1/portfolio").json()
    valuation = body["valuation"]
    assert valuation["state"] == "ok"
    assert valuation["freshness_policy"] == _expected_view("portfolio_mark")
    assert valuation["age_seconds"] <= valuation["freshness_policy"]["budget_seconds"]

    vide = build_portfolio_response(
        FakePortfolioGateway(valuation=None).overview(), now=NOW
    ).valuation
    assert vide.state == "empty"
    assert vide.age_seconds is None
    assert vide.freshness_policy is not None
    assert vide.freshness_policy.model_dump() == _expected_view("portfolio_mark")


def test_la_matrice_de_capacites_declare_une_absence_de_budget(api: TestClient) -> None:
    """Aucune politique du registre ne couvre cette famille — c'est DÉCLARÉ
    (`CAPABILITIES_FRESHNESS_POLICY is None`). La réponse dit ``null``, pas
    ``{budget_seconds: 0}`` : une absence n'est jamais convertie en zéro, et
    un TTL fabriqué ici serait la valeur non justifiée que ce dépôt refuse."""
    assert CAPABILITIES_FRESHNESS_POLICY is None
    body = api.get("/api/v1/system/capabilities").json()
    assert "freshness_policy" in body
    assert body["freshness_policy"] is None
    assert body["age_seconds"] is not None  # l'âge, lui, reste publié

    response = build_capabilities_response(
        load_capability_manifest(),
        snapshot=capabilities_snapshot([]),
        attention=None,
        db_ok=True,
        now=NOW,
    )
    assert response.freshness_policy is None


# ---------------------------------------------------------------------------
# L'agenda : l'âge et la jauge sont publiés dans CHAQUE état daté
# ---------------------------------------------------------------------------

VINGT_MINUTES = timedelta(minutes=20)

ETATS_PUBLIES_PAR_LE_WORKER: tuple[Any, ...] = (
    pytest.param("OK", None, "ok", id="ok"),
    pytest.param("EMPTY", "nothing observed", "empty", id="empty_publie"),
    pytest.param("NOT_ENTITLED", "rights not usable (2/2)", "not_entitled", id="not_entitled"),
    pytest.param("REJECTED", "every record invalid (2/2)", "rejected", id="rejected"),
    pytest.param("STALE", "every displayed event is stale (1/1)", "stale", id="stale_publie"),
)


@pytest.mark.parametrize(
    ("agenda_state", "agenda_reason", "served"), ETATS_PUBLIES_PAR_LE_WORKER
)
def test_l_agenda_publie_son_age_et_sa_jauge_dans_chaque_verdict_du_worker(
    agenda_state: str, agenda_reason: str | None, served: str
) -> None:
    """Le relais de l'agenda MESURAIT son âge — il nommait le budget dans sa
    raison ``stale`` — sans le SERVIR : un agenda de vingt heures arrivait
    comme un agenda d'une minute. Chaque verdict daté du worker est servi
    avec ``age_seconds`` et les coordonnées de sa jauge (``corporate_event``)."""
    events = [calendar_event("syn-ev-1")] if agenda_state in ("OK", "STALE") else []
    published = calendar_snapshot(
        events, version=7, agenda_state=agenda_state, agenda_state_reason=agenda_reason
    )
    response = build_calendar_response(published, window=None, now=AS_OF + VINGT_MINUTES)
    assert response.state == served
    assert response.age_seconds == int(VINGT_MINUTES.total_seconds())
    assert response.freshness_policy is not None
    assert response.freshness_policy.model_dump() == _expected_view("corporate_event")


def test_l_agenda_degrade_ou_hors_fenetre_reste_date() -> None:
    """Les deux états que le relais DÉRIVE lui-même (contrat antérieur, fenêtre
    qui ne sélectionne rien) sont datés comme les autres : l'âge ne dépend pas
    du verdict, il dépend de l'instantané."""
    now = AS_OF + VINGT_MINUTES

    legacy = calendar_snapshot([calendar_event("syn-ev-1")], version=7)
    legacy.content.pop("agenda_state")
    legacy.content.pop("agenda_state_reason")
    degrade = build_calendar_response(legacy, window=None, now=now)
    assert degrade.state == "degraded"
    assert degrade.age_seconds == int(VINGT_MINUTES.total_seconds())
    assert degrade.freshness_policy is not None
    assert degrade.freshness_policy.model_dump() == _expected_view("corporate_event")

    # L'événement de test est daté du 1er septembre : une fenêtre d'octobre
    # ne sélectionne rien.
    fenetre = (AS_OF + timedelta(days=60), AS_OF + timedelta(days=61))
    hors_fenetre = build_calendar_response(
        calendar_snapshot([calendar_event("syn-ev-1")], version=7), window=fenetre, now=now
    )
    assert hors_fenetre.state == "empty_window"
    assert hors_fenetre.age_seconds == int(VINGT_MINUTES.total_seconds())
    assert hors_fenetre.freshness_policy is not None
    assert hors_fenetre.freshness_policy.model_dump() == _expected_view("corporate_event")


def test_sans_agenda_publie_l_age_est_absent_mais_l_echelle_est_connue() -> None:
    """Jamais publié : l'âge n'existe pas (``null``, jamais zéro) ; le budget
    est une propriété de la route et reste servi."""
    response = build_calendar_response(None, window=None)
    assert response.state == "empty"
    assert response.age_seconds is None
    assert response.freshness_policy is not None
    assert response.freshness_policy.model_dump() == _expected_view("corporate_event")


# ---------------------------------------------------------------------------
# Le propriétaire : `vertex_api.freshness.published_budget`
# ---------------------------------------------------------------------------


def test_published_budget_projette_chaque_politique_du_registre() -> None:
    """Toute politique du registre se projette sans perte : budget = TTL de
    séance fermée, kind = nom, version = version. Rien d'autre n'est inventé."""
    for name, policy in FRESHNESS_POLICIES.items():
        view = published_budget(policy)
        assert view is not None
        assert view == FreshnessPolicyView(
            budget_seconds=policy.ttl_closed_seconds,
            kind=name,
            version=policy.version,
        )
        assert view.budget_seconds == int(closed_session_budget(policy).total_seconds())


def test_published_budget_d_une_absence_est_une_absence() -> None:
    assert published_budget(None) is None


def test_un_budget_nul_est_refuse_a_la_frontiere() -> None:
    """``budget_seconds = 0`` ne peut pas être servi : c'est la forme qu'une
    absence prendrait si elle était convertie en zéro."""
    with pytest.raises(ValidationError):
        FreshnessPolicyView(budget_seconds=0, kind="daily_bar", version="1.0.0")
    with pytest.raises(ValidationError):
        FreshnessPolicyView(budget_seconds=3600, kind="", version="1.0.0")


def test_l_instant_de_reference_reste_ancre() -> None:
    """Garde contre une dérive de fixture : AS_OF doit rester le même partout."""
    assert AS_OF == datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
