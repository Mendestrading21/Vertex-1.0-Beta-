"""Une depeche IBKR -> une observation de contenu : ce qui passe et ce qui non.

CE QUE CES TESTS EMPECHENT. Que la page Aujourd'hui redevienne vide sans que
personne ne le voie. Mesure du 2026-09-01 avant cette derivation : 500
observations considerees, 500 NON-CONTENU, zero cluster. Le cockpit etait vide
parce qu'une liste de depeches sous une observation n'est pas ce que le
fusionneur cherche — il cherche un `title` PAR observation.

Le test le plus important est `test_le_prefixe_IBKR_est_ANALYSE` : les scores
`K` et `C` sont des donnees, et un decoupage naif les aurait jetes.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_edge_ibkr.news import (
    NEWS_HEADLINE_SCHEMA_VERSION,
    NEWS_HEADLINE_TYPE,
    REASON_CON_ID_MISSING,
    news_headline_envelopes,
    news_headline_event_id,
)
from vertex_edge_ibkr.port import ContractSpec, NewsHeadline, NewsHeadlinesPayload

NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
CON_ID = 208813720
SPEC = ContractSpec(
    sec_type="STK", con_id=CON_ID, symbol="GOOG", exchange="SMART", currency="USD"
)


def source() -> DataEnvelope[NewsHeadlinesPayload]:
    return DataEnvelope(
        event_id="ibkr-news-source",
        schema_version="ibkr.news-headlines/1",
        source="ibkr",
        instrument_id=str(CON_ID),
        observed_at=NOW,
        received_at=NOW,
        as_of=NOW,
        stale_after=NOW,
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.UNKNOWN,
        connection_epoch=1,
        rights="IBKR_MARKET_DATA_DISPLAY_ONLY",
        payload_hash=canonical_json_hash({"con_id": CON_ID}),
        payload=NewsHeadlinesPayload(con_id=CON_ID, headlines=()),
    )


def charge(*depeches: NewsHeadline, con_id: int = CON_ID) -> NewsHeadlinesPayload:
    return NewsHeadlinesPayload(con_id=con_id, headlines=depeches)


def depeche(titre: str, *, article: str = "a1", fournisseur: str = "BRFG",
            quand: datetime | None = None) -> NewsHeadline:
    return NewsHeadline(
        provider_code=fournisseur, article_id=article, headline=titre, time=quand
    )


def test_une_depeche_devient_une_observation_de_CONTENU() -> None:
    """Le fusionneur reconnait une observation de contenu a son `title`."""
    enveloppes, resultat = news_headline_envelopes(
        source(), charge(depeche("Alphabet gagne du terrain")), SPEC
    )
    assert resultat.refused_reason is None
    assert len(enveloppes) == 1
    charge_utile = enveloppes[0].payload
    assert charge_utile["type"] == NEWS_HEADLINE_TYPE
    assert charge_utile["title"] == "Alphabet gagne du terrain"
    assert enveloppes[0].schema_version == NEWS_HEADLINE_SCHEMA_VERSION


def test_le_prefixe_IBKR_est_ANALYSE_pas_supprime() -> None:
    """`K` et `C` sont des SCORES, pas de la decoration.

    Mesure en direct : IBKR colle `{A:800015:L:en:K:0.97:C:0.97}` devant ses
    titres. Les jeter perdrait ce qu'il a pris la peine d'envoyer ; les laisser
    afficherait du bruit technique.
    """
    enveloppes, _ = news_headline_envelopes(
        source(),
        charge(depeche("{A:800015:L:en:K:0.97:C:0.97}Alphabet chute")),
        SPEC,
    )
    charge_utile = enveloppes[0].payload
    assert charge_utile["title"] == "Alphabet chute"
    assert charge_utile["article_ref"] == "800015"
    assert charge_utile["language"] == "en"
    assert charge_utile["keyword_score"] == "0.97"
    assert charge_utile["confidence_score"] == "0.97"


def test_un_champ_de_prefixe_INCONNU_est_conserve() -> None:
    """IBKR peut ajouter des champs ; les perdre en silence serait pire que
    de les nommer maladroitement."""
    enveloppes, _ = news_headline_envelopes(
        source(), charge(depeche("{Z:valeur:L:fr}Titre")), SPEC
    )
    assert enveloppes[0].payload["ibkr_z"] == "valeur"


def test_un_titre_sans_prefixe_reste_intact() -> None:
    enveloppes, _ = news_headline_envelopes(
        source(), charge(depeche("Titre nu, sans accolades")), SPEC
    )
    assert enveloppes[0].payload["title"] == "Titre nu, sans accolades"


def test_l_instrument_est_rattache_par_son_symbole() -> None:
    enveloppes, _ = news_headline_envelopes(source(), charge(depeche("T")), SPEC)
    assert enveloppes[0].payload["entities"] == ["GOOG"]
    assert enveloppes[0].instrument_id == str(CON_ID)


def test_une_depeche_SANS_DATE_ne_s_en_invente_pas() -> None:
    """Inventer une date de publication ordonnerait faussement la file."""
    enveloppes, _ = news_headline_envelopes(source(), charge(depeche("T")), SPEC)
    assert enveloppes[0].published_at is None


def test_une_depeche_datee_porte_sa_date() -> None:
    quand = datetime(2026, 8, 30, 9, 30, tzinfo=UTC)
    enveloppes, _ = news_headline_envelopes(
        source(), charge(depeche("T", quand=quand)), SPEC
    )
    assert enveloppes[0].published_at == quand


@pytest.mark.parametrize("titre", ["{A:1:L:en}", "{A:1:L:en}   "])
def test_un_titre_reduit_a_son_prefixe_est_ecarte_ET_compte(titre: str) -> None:
    """Une depeche sans texte n'est pas fusionnable, et son absence doit se voir.

    La chaine VIDE n'est pas testee ici : `NewsHeadline.headline` est un
    `NonEmptyStr` et pydantic la refuse a la construction — le contrat protege
    deja ce cas en amont. Reste le titre entierement consomme par son prefixe
    de metadonnees, qui lui est parfaitement constructible.
    """
    enveloppes, resultat = news_headline_envelopes(
        source(), charge(depeche(titre)), SPEC
    )
    assert enveloppes == ()
    assert resultat.skipped == 1


def test_sans_con_id_l_instrument_entier_est_refuse() -> None:
    enveloppes, resultat = news_headline_envelopes(
        source(), charge(depeche("T"), con_id=0), SPEC
    )
    assert enveloppes == ()
    assert resultat.refused_reason == REASON_CON_ID_MISSING


def test_l_identite_est_STABLE_donc_une_relance_ne_duplique_rien() -> None:
    """Un identifiant tire au hasard ferait dupliquer toute la presse a chaque
    relance du collecteur."""
    premier = news_headline_event_id("BRFG", "800015")
    assert premier == news_headline_event_id("BRFG", "800015")
    assert premier == "ibkr:news:BRFG:800015"
    assert premier != news_headline_event_id("DJ-RTG", "800015")


def test_la_provenance_est_HERITEE_de_la_reponse() -> None:
    """Une depeche derivee ne peut pas etre plus fiable que la reponse dont
    elle sort."""
    origine = source()
    enveloppes, _ = news_headline_envelopes(origine, charge(depeche("T")), SPEC)
    assert enveloppes[0].source == origine.source
    assert enveloppes[0].rights == origine.rights
    assert enveloppes[0].connection_epoch == origine.connection_epoch
    assert enveloppes[0].quality_status == origine.quality_status
