"""Aucun relais ne sert plus une valeur sans dire son âge.

CE QUE CES TESTS FERMENT. Huit relais sur dix ne publiaient PAS l'âge de
l'instantané qu'ils servaient : un dossier de trois jours arrivait à l'écran
exactement comme un dossier d'une minute. `.claude/rules/financial-safety.md`
interdit cela sous le nom de « conserver SILENCIEUSEMENT un ancien verdict »,
et `test_chaos_degradation.py` a MESURÉ le défaut à +47 h puis +71 h.

Deux affirmations, pour chaque relais :

1. dans le budget, l'âge est publié quand même — c'est LE correctif, parce
   qu'un budget de 72 h laisse +71 h « frais » et qu'inventer un TTL plus
   court pour faire joli serait une valeur non justifiée ;
2. au-delà du budget, l'état bascule sur `stale` et la raison nomme la
   politique et sa version.

Les tests importent les contenus valides déjà écrits ailleurs : un contenu
recopié ici divergerait du vrai et prouverait autre chose.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from test_analysis import AS_OF as ANALYSIS_AS_OF
from test_analysis import analysis_content
from test_markets_overview import markets_content
from test_option_chain import chain_content
from test_snapshot_content_errors import (
    _valid_performance_content,
    _valid_review_queue_content,
)
from test_today_attention import attention_content

from vertex_api.follow_up import build_follow_up_queue_response
from vertex_api.performance import build_performance_response
from vertex_api.snapshot_views import (
    build_analysis_response,
    build_attention_response,
    build_markets_overview_response,
    build_option_chain_response,
)
from vertex_core.data.freshness import get_freshness_policy
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = ANALYSIS_AS_OF


def _snapshot(kind: str, content: dict[str, Any]) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind=kind,
        key="global",
        version=7,
        content=content,
        content_hash="sha256:relay-freshness",
        as_of=AS_OF,
    )


#: Chaque relais avec sa politique DÉCLARÉE et le constructeur qui le sert.
#: La politique n'est pas recopiée d'un souvenir : elle est relue du module,
#: donc un changement de politique fait bouger ce test avec le code.
RELAIS = (
    pytest.param(
        "attention",
        "news_attention",
        lambda now: build_attention_response(
            _snapshot("attention", attention_content()), now=now
        ),
        id="attention",
    ),
    pytest.param(
        "markets_overview",
        "daily_bar",
        lambda now: build_markets_overview_response(
            _snapshot("markets_overview", markets_content()), now=now
        ),
        id="markets_overview",
    ),
    pytest.param(
        "analysis",
        "daily_bar",
        lambda now: build_analysis_response(
            _snapshot("analysis", analysis_content()),
            instrument="SYN-TECH-01",
            now=now,
        ),
        id="analysis",
    ),
    pytest.param(
        "option_chain",
        "option_surface",
        lambda now: build_option_chain_response(
            _snapshot("option_chain", chain_content()),
            underlying="SYN-TECH-01",
            now=now,
        ),
        id="option_chain",
    ),
    pytest.param(
        "review_queue",
        "news_attention",
        lambda now: build_follow_up_queue_response(
            _snapshot("review_queue", _valid_review_queue_content()), now=now
        ),
        id="review_queue",
    ),
    pytest.param(
        "performance",
        "daily_bar",
        lambda now: build_performance_response(
            _snapshot("performance", _valid_performance_content()),
            portfolio_id=1,
            now=now,
        ),
        id="performance",
    ),
)


@pytest.mark.parametrize(("kind", "policy_name", "build"), RELAIS)
def test_l_age_est_publie_meme_dans_le_budget(
    kind: str, policy_name: str, build: Any
) -> None:
    """LE correctif : l'âge est servi, budget ou pas.

    C'est l'absence de cette valeur qui faisait passer trois jours pour une
    minute — pas la largeur du budget. Un instantané dans le budget reste
    `ok`, et porte désormais ses secondes.
    """
    # La moitié du budget PROPRE au relais : les politiques vont de 1 h
    # (news_attention, option_surface) à 72 h (daily_bar), donc un « +2 h »
    # écrit en dur testerait quelque chose de différent selon le relais.
    policy = get_freshness_policy(policy_name)
    dans_le_budget = timedelta(seconds=policy.ttl_closed_seconds // 2)
    response = build(AS_OF + dans_le_budget)
    assert response.state == "ok", f"{kind} ne devrait pas être périmé à mi-budget"
    assert response.age_seconds == int(dans_le_budget.total_seconds()), kind
    assert response.reason is None


@pytest.mark.parametrize(("kind", "policy_name", "build"), RELAIS)
def test_au_dela_du_budget_l_etat_bascule_et_nomme_sa_politique(
    kind: str, policy_name: str, build: Any
) -> None:
    policy = get_freshness_policy(policy_name)
    depassement = timedelta(seconds=policy.ttl_closed_seconds + 60)
    response = build(AS_OF + depassement)
    assert response.state == "stale", kind
    assert response.age_seconds == int(depassement.total_seconds())
    assert response.reason is not None
    assert policy.name in response.reason
    assert policy.version in response.reason
    assert str(policy.ttl_closed_seconds) in response.reason


@pytest.mark.parametrize(("kind", "policy_name", "build"), RELAIS)
def test_le_contenu_reste_servi_quand_il_est_perime(
    kind: str, policy_name: str, build: Any
) -> None:
    """`stale` DIT l'âge, il ne cache pas le contenu.

    Retirer le contenu ferait perdre à l'utilisateur la seule chose qu'il
    peut encore lire honnêtement. Ce qui était interdit, c'est de le servir
    SANS sa date.
    """
    policy = get_freshness_policy(policy_name)
    response = build(AS_OF + timedelta(seconds=policy.ttl_closed_seconds + 60))
    assert response.snapshot_version == 7, kind
    porteur = getattr(response, "content", None)
    if porteur is not None:
        assert porteur, f"{kind} a vidé son contenu au lieu de le dater"


@pytest.mark.parametrize(("kind", "policy_name", "build"), RELAIS)
def test_la_bascule_se_fait_a_la_seconde_pres(
    kind: str, policy_name: str, build: Any
) -> None:
    """Exactement au budget, l'instantané est encore `ok` : sinon le test
    ci-dessus passerait avec n'importe quelle borne."""
    policy = get_freshness_policy(policy_name)
    limite = timedelta(seconds=policy.ttl_closed_seconds)
    assert build(AS_OF + limite).state == "ok", kind
    assert build(AS_OF + limite + timedelta(seconds=1)).state == "stale", kind


def test_la_matrice_de_capacites_publie_son_age_sans_inventer_de_ttl() -> None:
    """Aucune politique du registre ne couvre cette famille, et c'est DÉCLARÉ.

    La péremption d'une capacité est portée champ par champ par le
    ``expires_at`` de la sonde. Fabriquer ici un budget de relais donnerait
    un TTL que personne n'a décidé.
    """
    from vertex_api.snapshot_views import CAPABILITIES_FRESHNESS_POLICY

    assert CAPABILITIES_FRESHNESS_POLICY is None


def test_un_instantane_date_en_avance_ne_devient_pas_un_age_negatif() -> None:
    """Deux processus horodatent chacun leur lecture : l'âge est borné à zéro,
    jamais publié négatif — un âge négatif serait un non-sens à l'écran."""
    response = build_attention_response(
        _snapshot("attention", attention_content()), now=AS_OF - timedelta(seconds=0)
    )
    assert response.age_seconds == 0


def test_l_horloge_du_relais_est_toujours_injectee() -> None:
    """Aucun de ces constructeurs ne lit l'horloge système par défaut.

    Un défaut implicite rendrait la fraîcheur intestable et ferait rougir ces
    tests tout seuls avec le temps.
    """
    with pytest.raises(TypeError, match="now"):
        build_attention_response(_snapshot("attention", attention_content()))  # type: ignore[call-arg]


def test_l_instant_de_reference_reste_ancre() -> None:
    """Garde contre une dérive de fixture : AS_OF doit rester le même partout."""
    assert AS_OF == datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


def test_le_portefeuille_date_sa_valorisation_et_la_declare_perimee() -> None:
    """Le portefeuille ne prend pas un instantané mais un `PortfolioOverview` :
    il ne peut pas entrer dans la table ci-dessus, il est donc prouvé à part.

    Sa politique est ``portfolio_mark``, la SEULE du registre qui nomme
    exactement cet usage — la marque d'un portefeuille déclaré à la main.
    """
    from portfolio_fakes import FakePortfolioGateway
    from test_portfolio_routes import SYNTHETIC_VALUATION

    from vertex_api.portfolio import PORTFOLIO_FRESHNESS_POLICY, build_portfolio_response

    policy = get_freshness_policy(PORTFOLIO_FRESHNESS_POLICY)
    assert PORTFOLIO_FRESHNESS_POLICY == "portfolio_mark"
    publie = SYNTHETIC_VALUATION.as_of

    dans_le_budget = build_portfolio_response(
        FakePortfolioGateway(valuation=SYNTHETIC_VALUATION).overview(),
        now=publie + timedelta(seconds=policy.ttl_closed_seconds // 2),
    )
    assert dans_le_budget.valuation.state == "ok"
    assert dans_le_budget.valuation.age_seconds == policy.ttl_closed_seconds // 2

    perime = build_portfolio_response(
        FakePortfolioGateway(valuation=SYNTHETIC_VALUATION).overview(),
        now=publie + timedelta(seconds=policy.ttl_closed_seconds + 60),
    )
    assert perime.valuation.state == "stale"
    assert perime.valuation.reason is not None
    assert policy.name in perime.valuation.reason
    # Le contenu reste servi : `stale` DIT l'âge, il ne cache pas la valeur.
    assert perime.valuation.content
