"""Le corpus synthetique doit exercer la GRAMMAIRE d'un identifiant de fournisseur.

POURQUOI CE FICHIER EXISTE. `docs/08-runbooks/REPRENDRE_ICI.md` §4.4 nomme un
trou de couverture qui a coute cher : `apps/web/e2e/analysis.spec.ts` et
`today.spec.ts` sont passes AU VERT pendant que **72 reponses partaient en
500**. Cause : tout identifiant du corpus est frappe par Vertex
(`synthetic-dev:{seed}:{index:04d}`), donc AUCUNE identite de fournisseur n'a
jamais traverse le relais.

IBKR News encastre l'`article_id` du fournisseur dans l'`event_id`, et cet
article_id porte un `$` (forme reelle : `ibkr:news:DJ-RT:DJ-RT$1e0664c8`). Le
relais refusait ce caractere ; personne ne l'a vu, parce que rien dans les
tests n'avait cette forme.

CE QUE LE CORPUS N'IMITE PAS, ET C'EST DELIBERE. La passation suggerait de
semer `ibkr:news:<provider>:<provider>$<hex>`. Ce serait poser un marqueur de
source REELLE dans une fixture, ce que `.claude/rules/testing.md` interdit :
« une fixture porte explicitement le statut SYNTHETIC et ne peut franchir une
frontiere de production ».

Le corpus garde donc `source = synthetic-dev` et `rights = SYNTHETIC` — c'est
bien de la donnee generee, et rien ne doit laisser croire l'inverse. Ce qui est
reproduit, c'est la GRAMMAIRE de l'identifiant, la seule chose que le relais
lit : quatre segments, dont le dernier porte un `$` separant l'espace de noms
du fournisseur de son identifiant opaque. La forme est reelle, la provenance
reste synthetique.
"""

from __future__ import annotations

from datetime import UTC, datetime

from vertex_core.synthetic import SYNTHETIC_SOURCE
from vertex_core.synthetic.generator import (
    PROVIDER_ARTICLE_SEPARATOR,
    SYNTHETIC_NEWS_PROVIDER,
    generate_envelopes,
)

SEED = 20260901
COUNT = 48
BASE = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)


def _corpus() -> tuple[object, ...]:
    return generate_envelopes(seed=SEED, count=COUNT, base_time=BASE)


def _identifiants() -> list[str]:
    return [envelope.event_id for envelope in _corpus()]


def test_le_corpus_porte_au_moins_un_identifiant_de_fournisseur() -> None:
    """LE REPRODUCTEUR. Rouge tant que tout le corpus est frappe par Vertex.

    Sans un seul identifiant de cette forme, la campagne e2e ne peut pas voir
    un relais qui refuserait la grammaire des fournisseurs — et c'est
    exactement ce qui s'est produit : verte, pendant 72 reponses en 500.
    """
    porteurs = [
        identifiant
        for identifiant in _identifiants()
        if PROVIDER_ARTICLE_SEPARATOR in identifiant
    ]
    assert porteurs, (
        "aucun identifiant de forme fournisseur dans le corpus : la campagne "
        "e2e ne peut pas voir un relais qui refuserait cette grammaire"
    )
    # PLUSIEURS depeches distinctes, pas une : une seule pourrait etre ecartee
    # par un filtre de qualite ou de fraicheur et laisser le corpus muet.
    # Mesure sur ce corpus : deux identifiants distincts, chacun repete par les
    # doublons voulus du generateur.
    assert len(set(porteurs)) >= 2


def test_la_grammaire_est_celle_du_reel_segment_par_segment() -> None:
    """La forme doit etre la MEME que celle d'IBKR, sinon elle ne prouve rien.

    Reel :      ibkr:news:DJ-RT:DJ-RT$1e0664c8
    Synthetique : synthetic-dev:news:SYNWIRE:SYNWIRE$<hex>

    Quatre segments, le quatrieme portant `<espace de noms>$<identifiant>`.
    Une forme approchante laisserait passer le defaut qu'elle pretend epingler.
    """
    porteurs = [
        identifiant
        for identifiant in _identifiants()
        if PROVIDER_ARTICLE_SEPARATOR in identifiant
    ]
    for identifiant in porteurs:
        segments = identifiant.split(":")
        assert len(segments) == 4, identifiant
        assert segments[0] == SYNTHETIC_SOURCE  # jamais `ibkr` dans une fixture
        assert segments[1] == "news"
        assert segments[2] == SYNTHETIC_NEWS_PROVIDER
        espace, _, opaque = segments[3].partition(PROVIDER_ARTICLE_SEPARATOR)
        assert espace == SYNTHETIC_NEWS_PROVIDER
        assert opaque and all(caractere in "0123456789abcdef" for caractere in opaque)


def test_la_provenance_reste_synthetique_malgre_la_forme_reelle() -> None:
    """La grammaire est empruntee, la PROVENANCE ne l'est pas.

    Un corpus qui se declarerait `ibkr` franchirait la frontiere que
    `.claude/rules/testing.md` interdit de franchir. Ce test garde la
    distinction : la forme sert le test, l'aveu reste vrai.
    """
    porteuses = [
        envelope
        for envelope in _corpus()
        if PROVIDER_ARTICLE_SEPARATOR in envelope.event_id
    ]
    assert porteuses
    for envelope in porteuses:
        assert envelope.source == SYNTHETIC_SOURCE
        assert envelope.rights == "SYNTHETIC"
        assert "ibkr" not in envelope.event_id


def test_le_corpus_reste_deterministe() -> None:
    """Meme graine, memes identifiants — un semis non reproductible ne vaut rien."""
    assert _identifiants() == _identifiants()
