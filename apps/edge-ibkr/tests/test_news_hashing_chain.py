"""R2-C' — la chaîne de presse de bout en bout : collecte → hachage → dérivation.

CE QUE CE FICHIER REPRODUIT, PAR LE VRAI CHEMIN. Sur ``main@ecc50c1``,
``NewsHeadline.time_unzoned`` est un ``datetime | None`` et
``IbAsyncInformationAdapter.news_headlines`` y place l'horodatage IBKR **naïf**
tel quel. L'enveloppe est ensuite hachée dans ``_envelope`` —
``payload_hash = canonical_json_hash(payload)`` — et le canonicaliseur refuse
tout datetime naïf, à juste titre. Mesuré le 2026-09-02 sur le poste de
l'utilisateur : ``CanonicalizationError`` à la première dépêche, **zéro**
dépêche collectée depuis l'introduction du champ.

Aucun test ne faisait passer une dépêche à horodatage naïf par l'adaptateur :
la suite était verte pendant que la collecte réelle plantait. Ces tests
suivent le trajet réel — la ligne IBKR telle que ``ib_async`` la rend, la
construction par l'adaptateur, le hachage de ``_envelope``, puis la dérivation
en observation de contenu, elle aussi hachée.

Ils sont ROUGES sur ``main@ecc50c1`` (``CanonicalizationError``) et verts
après reprise de ``732f7e5`` (chaîne ISO).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from fakes import T1, FakeIB
from test_adapter import make_adapter

from vertex_core.contracts.hashing import canonical_json_hash
from vertex_edge_ibkr.news import news_headline_envelopes
from vertex_edge_ibkr.port import ContractSpec

CON_ID = 208813720
SPEC = ContractSpec(sec_type="STK", con_id=CON_ID, symbol="GOOG", exchange="SMART", currency="USD")

# Un horodatage SANS fuseau, exactement comme IBKR les émet (mesuré :
# tzinfo=None). Dérivé d'un instant daté plutôt que construit : DTZ001
# interdit datetime() nu, et désactiver la règle pour un test qui porte
# précisément sur les fuseaux serait absurde.
NAIF = datetime(2026, 6, 2, 14, 50, 49, tzinfo=UTC).replace(tzinfo=None)


def _ligne_ibkr_naive() -> SimpleNamespace:
    """La ligne que ``reqHistoricalNewsAsync`` rend : mêmes noms qu'``ib_async``."""
    return SimpleNamespace(
        providerCode="DJ-RT",
        articleId="DJ-RT$1e0664c8",
        headline="{A:800015:L:en:K:0.97:C:0.97}Alphabet recule",
        time=NAIF,
    )


def test_l_adaptateur_hache_une_reponse_de_presse_a_horodatage_naif() -> None:
    """LE REPRODUCTEUR. Sur main : ``CanonicalizationError`` dans ``_envelope``.

    C'est le hachage appliqué à CHAQUE réponse fournisseur. S'il lève, aucune
    dépêche n'est jamais ingérée — et le collecteur tombe à la première ligne.
    """
    adapter = make_adapter(FakeIB(headlines=(_ligne_ibkr_naive(),)))
    enveloppe = asyncio.run(adapter.news_headlines(CON_ID, ("DJ-RT",)))

    assert enveloppe.payload_hash == canonical_json_hash(enveloppe.payload)
    (depeche,) = enveloppe.payload.headlines
    # L'ambiguïté est portée par le NOM du champ ; son TYPE traverse le hachage.
    assert depeche.time is None
    assert depeche.time_unzoned == "2026-06-02T14:50:49"


def test_un_horodatage_deja_date_ne_va_pas_dans_le_champ_ambigu() -> None:
    """Un instant AVEC fuseau va dans ``time`` ; ``time_unzoned`` reste vide."""
    ligne = _ligne_ibkr_naive()
    ligne.time = T1  # aware UTC
    adapter = make_adapter(FakeIB(headlines=(ligne,)))
    enveloppe = asyncio.run(adapter.news_headlines(CON_ID, ("DJ-RT",)))
    (depeche,) = enveloppe.payload.headlines
    assert depeche.time == T1
    assert depeche.time_unzoned is None


def test_la_chaine_complete_jusqu_a_l_observation_de_contenu() -> None:
    """Réponse hachée → dérivation en observation de contenu, ELLE AUSSI hachée.

    L'horodatage ambigu arrive conservé sous son nom, ``published_at`` reste
    absent — l'instant demeure inconnu — et l'identité de fournisseur traverse
    INCHANGÉE : c'est la clé d'idempotence de l'ingestion.
    """
    adapter = make_adapter(FakeIB(headlines=(_ligne_ibkr_naive(),)))
    source = asyncio.run(adapter.news_headlines(CON_ID, ("DJ-RT",)))

    enveloppes, resultat = news_headline_envelopes(source, source.payload, SPEC)
    assert resultat.refused_reason is None
    assert len(enveloppes) == 1
    derivee = enveloppes[0]
    assert derivee.payload["provider_time_unzoned"] == "2026-06-02T14:50:49"
    assert derivee.published_at is None
    assert derivee.payload_hash == canonical_json_hash(derivee.payload)
    assert derivee.event_id == "ibkr:news:DJ-RT:DJ-RT$1e0664c8"
