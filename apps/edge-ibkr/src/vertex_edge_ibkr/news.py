"""Une depeche IBKR -> une observation de CONTENU, fusionnable.

POURQUOI CETTE DERIVATION EXISTE.
La page Aujourd'hui fusionne des observations de CONTENU : des choses qui
portent un titre. Mesure du 2026-09-01 : 500 observations considerees, 500
NON-CONTENU, zero cluster. Le cockpit etait vide parce que Vertex ne collectait
aucune actualite — alors que le compte a droit a huit fournisseurs (Dow Jones,
Briefing.com) et que l'adaptateur sait les lire depuis toujours.

LE MEME ECART, UNE TROISIEME FOIS. `NewsHeadlinesPayload` porte une LISTE de
depeches sous une seule observation ; le fusionneur cherche un `title` au
niveau de l'observation. Comme les cotations et les barres ce matin, il faut
deriver : une depeche, une observation.

CE QU'ELLE REFUSE
-----------------
- titre vide : une depeche sans titre n'est pas fusionnable et son absence
  serait invisible ; elle est ecartee et COMPTEE ;
- identifiant d'article absent : sans lui l'identite derivee ne serait pas
  stable, et chaque relance dupliquerait toute la presse ;
- `con_id` absent : l'observation n'appartiendrait a aucun instrument.

SUR LA DATE. `published_at` porte l'heure de la depeche quand IBKR la fournit,
et reste absent sinon — le fusionneur retombe alors sur `received_at`. Inventer
une date de publication ordonnerait faussement la file d'attention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from vertex_core.contracts import DataEnvelope
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_edge_ibkr.port import ContractSpec, NewsHeadlinesPayload

__all__ = [
    "NEWS_HEADLINE_SCHEMA_VERSION",
    "NEWS_HEADLINE_TYPE",
    "NewsNormalizationResult",
    "news_headline_envelopes",
    "news_headline_event_id",
]

#: Marqueur de nature de la charge derivee.
NEWS_HEADLINE_TYPE = "news_headline"

#: Schema des depeches derivees. Une observation par depeche, la ou
#: `ibkr.news-headlines/1` en porte une liste.
NEWS_HEADLINE_SCHEMA_VERSION = "ibkr.news-headline/1"

REASON_TITLE_MISSING = "TITLE_MISSING"
REASON_ARTICLE_ID_MISSING = "ARTICLE_ID_MISSING"
REASON_CON_ID_MISSING = "CON_ID_MISSING"


@dataclass(frozen=True)
class NewsNormalizationResult:
    """Ce que la derivation a produit — et ce qu'elle a ecarte."""

    payloads: tuple[dict[str, Any], ...] = ()
    skipped: int = 0
    refused_reason: str | None = None

    @property
    def produced(self) -> int:
        return len(self.payloads)


#: Prefixe de metadonnees qu'IBKR colle devant chaque titre, mesure le
#: 2026-09-01 : `{A:800015:L:en}` ou `{A:800015:L:en:K:0.97:C:0.97}`.
_PREFIXE_METADONNEES = re.compile(r"^\{([A-Za-z]:[^:}]*(?::[A-Za-z]:[^:}]*)*)\}(.*)$", re.S)

#: Noms lisibles des champs du prefixe. Un champ inconnu est conserve sous sa
#: lettre plutot que jete : IBKR peut en ajouter, et les perdre en silence
#: serait exactement ce que ce depot refuse.
_CHAMPS_PREFIXE = {
    "A": "article_ref",
    "L": "language",
    "K": "keyword_score",
    "C": "confidence_score",
}


def _decouper_prefixe(brut: str) -> tuple[str, dict[str, str]]:
    """Separe le titre lisible des metadonnees collees devant lui.

    Un prefixe non reconnu n'est PAS retire : le titre reste tel quel. Mieux
    vaut un titre bruyant qu'un titre ampute par une regle trop large.
    """
    correspondance = _PREFIXE_METADONNEES.match(brut)
    if correspondance is None:
        return brut.strip(), {}

    metadonnees: dict[str, str] = {}
    champs = correspondance.group(1).split(":")
    for index in range(0, len(champs) - 1, 2):
        lettre = champs[index]
        valeur = champs[index + 1]
        nom = _CHAMPS_PREFIXE.get(lettre, f"ibkr_{lettre.lower()}")
        metadonnees[nom] = valeur
    return correspondance.group(2).strip(), metadonnees


def news_headline_event_id(provider_code: str, article_id: str) -> str:
    """Identite STABLE d'une depeche : fournisseur + article.

    `ingest_envelope` est idempotent dessus. Un identifiant tire au hasard
    ferait dupliquer toute la presse a chaque relance du collecteur.
    """
    return f"ibkr:news:{provider_code}:{article_id}"


def news_headline_envelopes(
    source_envelope: DataEnvelope[Any],
    headlines: NewsHeadlinesPayload,
    spec: ContractSpec,
) -> tuple[tuple[DataEnvelope[Any], ...], NewsNormalizationResult]:
    """Derive une observation de contenu par depeche.

    Les metadonnees de provenance — source, droits, epoch, qualite, retard —
    sont HERITEES : une depeche derivee ne peut pas etre plus fiable que la
    reponse dont elle sort.
    """
    if headlines.con_id is None or headlines.con_id <= 0:
        return (), NewsNormalizationResult(refused_reason=REASON_CON_ID_MISSING)

    enveloppes: list[DataEnvelope[Any]] = []
    charges: list[dict[str, Any]] = []
    ecartees = 0

    for depeche in headlines.headlines:
        titre, metadonnees = _decouper_prefixe(depeche.headline or "")
        if not titre:
            ecartees += 1
            continue
        if not depeche.article_id or not depeche.provider_code:
            ecartees += 1
            continue

        charge: dict[str, Any] = {
            "type": NEWS_HEADLINE_TYPE,
            # `title` est LA cle que le fusionneur cherche pour reconnaitre
            # une observation de contenu.
            "title": titre,
            "provider_code": depeche.provider_code,
            "article_id": depeche.article_id,
        }
        # Metadonnees du prefixe, publiees sous leur nom plutot que jetees.
        charge.update(metadonnees)
        # Horodatage du fournisseur SANS fuseau : conserve tel quel, sous un
        # nom qui dit son defaut. `published_at` reste absent — l'instant est
        # inconnu — mais l'ecran peut afficher la date en la qualifiant.
        if depeche.time_unzoned is not None:
            charge["provider_time_unzoned"] = depeche.time_unzoned
        # `entities` rattache la depeche a l'instrument : sans elle le
        # fusionneur retombe sur `instrument_ref`, ce qui marche aussi, mais
        # le symbole est plus lisible dans une preuve affichee.
        if spec.symbol:
            charge["entities"] = [spec.symbol]

        charges.append(charge)
        enveloppes.append(
            DataEnvelope(
                event_id=news_headline_event_id(
                    depeche.provider_code, depeche.article_id
                ),
                schema_version=NEWS_HEADLINE_SCHEMA_VERSION,
                source=source_envelope.source,
                instrument_id=str(headlines.con_id),
                observed_at=depeche.time or source_envelope.observed_at,
                # Absent quand IBKR ne date pas la depeche : inventer une date
                # de publication ordonnerait faussement la file d'attention.
                published_at=depeche.time,
                received_at=source_envelope.received_at,
                as_of=depeche.time or source_envelope.as_of,
                stale_after=source_envelope.stale_after,
                quality_status=source_envelope.quality_status,
                delay_status=source_envelope.delay_status,
                connection_epoch=source_envelope.connection_epoch,
                rights=source_envelope.rights,
                payload_hash=canonical_json_hash(charge),
                payload=charge,
            )
        )

    return tuple(enveloppes), NewsNormalizationResult(
        payloads=tuple(charges), skipped=ecartees
    )
