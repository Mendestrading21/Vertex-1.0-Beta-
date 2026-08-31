"""Barre quotidienne IBKR → cotation quotidienne. La dernière marche.

POURQUOI CETTE TRANSFORMATION EXISTE, ET POURQUOI ELLE EST ÉTROITE.
La page Marchés lit une COTATION QUOTIDIENNE : un ticker, un jour de bourse,
une clôture, une base d'ajustement. L'ingestion temps réel d'IBKR produit tout
autre chose — un carnet haut instantané (`bid`, `ask`, `last`). Faire passer
l'un pour l'autre serait une falsification sémantique : un meilleur prix
acheteur à 11 h 27 n'est pas le cours de clôture du jour.

La barre quotidienne, elle, EST une clôture datée. C'est la seule entrée IBKR
qui puisse honnêtement alimenter cette page, et ce module ne convertit rien
d'autre.

POURQUOI ICI ET NON DANS LE WORKER. `symbol` et `currency` vivent dans le
`ContractSpec`, jamais dans `BarsPayload`. Le worker ne les a pas et ne peut
pas les inventer : seule l'edge possède le contexte de la requête.

CE QU'IL REFUSE, ET POURQUOI CHAQUE REFUS EXISTE
------------------------------------------------
- barre non quotidienne : une barre horaire n'a pas de clôture de séance ;
- `what_to_show` autre que `TRADES` : `MIDPOINT` et `BID_ASK` sont des prix
  synthétiques du carnet, pas des cours de transaction ;
- clôture absente, non finie ou négative : sautée et COMPTÉE, jamais changée
  en zéro ;
- symbole absent : l'instrument entier est refusé, en nommant son `con_id`.
  Sans symbole, la cotation n'appartiendrait à aucun univers déclaré et serait
  rejetée plus loin, sans que personne sache pourquoi.

SUR LA BASE D'AJUSTEMENT. Une barre `TRADES` d'IBKR n'est PAS ajustée des
dividendes ni des splits. La constante le dit littéralement. Écrire `adjusted`
serait faux ; réutiliser le marqueur synthétique serait pire.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vertex_core.contracts import DataEnvelope
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_core.contracts.market_quote import (
    DailyBarError,
    DailyBarsError,
    DailyQuoteError,
    build_daily_bar,
    build_daily_bars_payload,
    build_daily_quote_payload,
)
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec

__all__ = [
    "DAILY_BARS_SCHEMA_VERSION",
    "DAILY_BAR_SIZE",
    "DAILY_QUOTE_SCHEMA_VERSION",
    "IBKR_TRADES_ADJUSTMENT_BASIS",
    "TRADES_WHAT_TO_SHOW",
    "BarsNormalizationResult",
    "NormalizationResult",
    "daily_bars_envelope",
    "daily_bars_event_id",
    "daily_bars_payload_from_bars",
    "daily_quote_envelopes",
    "daily_quotes_from_bars",
]

#: Une barre `TRADES` d'IBKR n'est pas ajustée des dividendes et des splits.
IBKR_TRADES_ADJUSTMENT_BASIS = "ibkr-trades-unadjusted"

#: Les seules valeurs qu'une cotation quotidienne peut honnêtement porter.
DAILY_BAR_SIZE = "1 day"
TRADES_WHAT_TO_SHOW = "TRADES"

REASON_BAR_SIZE_NOT_DAILY = "BAR_SIZE_NOT_DAILY"
REASON_WHAT_TO_SHOW_NOT_TRADES = "WHAT_TO_SHOW_NOT_TRADES"
REASON_SYMBOL_MISSING = "SYMBOL_MISSING"


@dataclass(frozen=True)
class NormalizationResult:
    """Ce que la transformation a produit — et ce qu'elle a écarté.

    ``refused_reason`` est ``None`` quand la transformation a eu lieu.
    ``skipped_bars`` compte les barres écartées pour clôture inutilisable :
    elles ne disparaissent jamais en silence.
    """

    payloads: tuple[dict[str, Any], ...] = ()
    skipped_bars: int = 0
    refused_reason: str | None = None

    @property
    def produced(self) -> int:
        return len(self.payloads)


def daily_quotes_from_bars(
    bars: BarsPayload,
    spec: ContractSpec,
    *,
    sector: str,
) -> NormalizationResult:
    """Convertit des barres QUOTIDIENNES en cotations, ou refuse en le disant.

    Ne lève jamais sur une barre isolée : dans un remplissage de mille titres,
    une clôture manquante ne doit pas interrompre les 999 autres. Elle est
    comptée dans ``skipped_bars``.
    """
    if bars.bar_size != DAILY_BAR_SIZE:
        return NormalizationResult(refused_reason=REASON_BAR_SIZE_NOT_DAILY)
    if bars.what_to_show != TRADES_WHAT_TO_SHOW:
        return NormalizationResult(refused_reason=REASON_WHAT_TO_SHOW_NOT_TRADES)
    if not spec.symbol:
        return NormalizationResult(refused_reason=REASON_SYMBOL_MISSING)

    payloads: list[dict[str, Any]] = []
    ecartees = 0
    for barre in bars.bars:
        if barre.close is None:
            ecartees += 1
            continue
        try:
            payloads.append(
                build_daily_quote_payload(
                    ticker=spec.symbol,
                    sector=sector,
                    trading_day=barre.time.date().isoformat(),
                    close=barre.close,
                    adjustment_basis=IBKR_TRADES_ADJUSTMENT_BASIS,
                    currency=spec.currency,
                )
            )
        except DailyQuoteError:
            # Clôture non finie, nulle ou négative : la barre est écartée et
            # comptée. Jamais transformée en zéro, jamais publiée à moitié.
            ecartees += 1
    return NormalizationResult(payloads=tuple(payloads), skipped_bars=ecartees)


#: Schema des cotations derivees. Le prefixe `ibkr.daily-quote/` est DEJA
#: declare dans `vertex_worker.markets.DAILY_QUOTE_SCHEMA_PREFIXES` : c'est lui
#: qui fait mettre `quotes.ingested` en file, donc qui reveille la page Marches.
DAILY_QUOTE_SCHEMA_VERSION = "ibkr.daily-quote/1"


def daily_quote_event_id(con_id: int | None, trading_day: str) -> str:
    """Identite STABLE d'une cotation derivee : contrat + jour de bourse.

    `ingest_envelope` est idempotent sur `event_id`. Un identifiant tire au
    hasard ferait dupliquer TOUT l'historique a chaque relance du remplissage ;
    un identifiant metier rend la relance gratuite et sure.
    """
    return f"ibkr:daily-quote:{con_id}:{trading_day}"


def daily_quote_envelopes(
    source_envelope: DataEnvelope[Any],
    bars: BarsPayload,
    spec: ContractSpec,
    *,
    sector: str,
) -> tuple[tuple[DataEnvelope[Any], ...], NormalizationResult]:
    """Enveloppes de cotation derivees d'une enveloppe de barres.

    Les metadonnees de provenance — source, droits, epoch de connexion,
    qualite, statut de retard — sont HERITEES telles quelles : une cotation
    derivee ne peut pas etre plus fiable que la barre dont elle sort.

    ``observed_at`` et ``as_of`` deviennent l'instant de la barre, pas celui de
    la requete : c'est la seule datation qui rende la fraicheur honnete.
    """
    resultat = daily_quotes_from_bars(bars, spec, sector=sector)
    if resultat.refused_reason is not None or not resultat.payloads:
        return (), resultat

    enveloppes: list[DataEnvelope[Any]] = []
    for charge_utile, barre in zip(resultat.payloads, _bars_with_close(bars), strict=True):
        enveloppes.append(
            DataEnvelope(
                event_id=daily_quote_event_id(spec.con_id, charge_utile["trading_day"]),
                schema_version=DAILY_QUOTE_SCHEMA_VERSION,
                source=source_envelope.source,
                instrument_id=str(spec.con_id) if spec.con_id is not None else None,
                observed_at=barre.time,
                received_at=source_envelope.received_at,
                as_of=barre.time,
                stale_after=source_envelope.stale_after,
                quality_status=source_envelope.quality_status,
                delay_status=source_envelope.delay_status,
                connection_epoch=source_envelope.connection_epoch,
                rights=source_envelope.rights,
                payload_hash=canonical_json_hash(charge_utile),
                payload=charge_utile,
            )
        )
    return tuple(enveloppes), resultat


def _bars_with_close(bars: BarsPayload) -> list[BarObservation]:
    """Les barres RETENUES, dans le meme ordre que les charges utiles produites.

    `daily_quotes_from_bars` ecarte les clotures inutilisables ; apparier
    naivement sur l'index d'origine decalerait les dates d'un cran apres le
    premier ecart, et chaque cotation porterait le jour d'une autre.
    """
    retenues: list[BarObservation] = []
    for barre in bars.bars:
        if barre.close is None:
            continue
        try:
            build_daily_quote_payload(
                ticker="x",
                sector="x",
                trading_day=barre.time.date().isoformat(),
                close=barre.close,
                adjustment_basis="x",
            )
        except DailyQuoteError:
            continue
        retenues.append(barre)
    return retenues


# ---------------------------------------------------------------------------
# Barre quotidienne IBKR → enregistrement de barres (page Analyse)
# ---------------------------------------------------------------------------
#
# POURQUOI UNE SECONDE DÉRIVATION. La page Marchés se contente d'une clôture ;
# la page Analyse calcule des tendances et exige l'OHLC complet plus le volume.
# La même barre IBKR alimente donc deux formes distinctes. Ne produire que la
# cotation laissait la page Analyse vide alors que la donnée était DÉJÀ en
# base — mesuré le 2026-08-31 : 251 barres réelles ingérées, zéro lue.
#
# POURQUOI UN SEUL ENREGISTREMENT POUR TOUT L'HISTORIQUE. Le consommateur
# choisit « le dernier enregistrement utilisable » et lit son tableau `bars`
# entier. Émettre une observation par barre ferait gagner la plus récente
# SEULE, et la page n'afficherait qu'un seul jour.

#: Schema des barres derivees. Le prefixe `ibkr.daily-bars/` doit etre declare
#: dans `vertex_worker.analysis.DAILY_BARS_SCHEMA_PREFIXES`, sinon rien ne
#: reveille la page Analyse et l'absence est silencieuse.
DAILY_BARS_SCHEMA_VERSION = "ibkr.daily-bars/1"

REASON_CURRENCY_MISSING = "CURRENCY_MISSING"
REASON_NO_USABLE_BAR = "NO_USABLE_BAR"


@dataclass(frozen=True)
class BarsNormalizationResult:
    """Ce que la dérivation des barres a produit — et ce qu'elle a écarté."""

    payload: dict[str, Any] | None = None
    skipped_bars: int = 0
    refused_reason: str | None = None

    @property
    def produced(self) -> int:
        return 0 if self.payload is None else len(self.payload["bars"])


def daily_bars_event_id(con_id: int | None, premier_jour: str, dernier_jour: str) -> str:
    """Identite STABLE : contrat + fenetre couverte.

    Relancer le meme remplissage produit le meme identifiant, donc aucune
    duplication ; une fenetre differente produit un enregistrement distinct,
    et le consommateur gardera le plus recent.
    """
    return f"ibkr:daily-bars:{con_id}:{premier_jour}:{dernier_jour}"


def daily_bars_payload_from_bars(bars: BarsPayload, spec: ContractSpec) -> BarsNormalizationResult:
    """Convertit des barres QUOTIDIENNES en enregistrement, ou refuse.

    Les refus de structure sont les mêmes que pour les cotations : une barre
    horaire n'a pas de séance, `MIDPOINT` n'est pas un cours de transaction,
    et sans symbole l'enregistrement n'appartiendrait à aucun univers déclaré.
    S'y ajoute la devise, que le consommateur exige au niveau de
    l'enregistrement entier — l'omettre viderait la page sans cause visible.
    """
    if bars.bar_size != DAILY_BAR_SIZE:
        return BarsNormalizationResult(refused_reason=REASON_BAR_SIZE_NOT_DAILY)
    if bars.what_to_show != TRADES_WHAT_TO_SHOW:
        return BarsNormalizationResult(refused_reason=REASON_WHAT_TO_SHOW_NOT_TRADES)
    if not spec.symbol:
        return BarsNormalizationResult(refused_reason=REASON_SYMBOL_MISSING)
    if not spec.currency:
        return BarsNormalizationResult(refused_reason=REASON_CURRENCY_MISSING)

    retenues: list[dict[str, Any]] = []
    ecartees = 0
    for barre in bars.bars:
        if (
            barre.open is None
            or barre.high is None
            or barre.low is None
            or barre.close is None
            or barre.volume is None
        ):
            # Une barre partielle n'est pas réparable : l'OHLC est un tout.
            ecartees += 1
            continue
        try:
            retenues.append(
                build_daily_bar(
                    trading_day=barre.time.date().isoformat(),
                    open_=barre.open,
                    high=barre.high,
                    low=barre.low,
                    close=barre.close,
                    volume=barre.volume,
                )
            )
        except DailyBarError:
            # Volume fractionnaire, prix hors forme, barre incohérente : elle
            # est écartée et COMPTÉE. Jamais arrondie, jamais réparée.
            ecartees += 1

    if not retenues:
        return BarsNormalizationResult(skipped_bars=ecartees, refused_reason=REASON_NO_USABLE_BAR)

    try:
        charge = build_daily_bars_payload(
            ticker=spec.symbol,
            currency=spec.currency,
            adjustment_basis=IBKR_TRADES_ADJUSTMENT_BASIS,
            bars=retenues,
        )
    except DailyBarsError:
        return BarsNormalizationResult(skipped_bars=ecartees, refused_reason=REASON_NO_USABLE_BAR)
    return BarsNormalizationResult(payload=charge, skipped_bars=ecartees)


def daily_bars_envelope(
    source_envelope: DataEnvelope[Any], bars: BarsPayload, spec: ContractSpec
) -> tuple[DataEnvelope[Any] | None, BarsNormalizationResult]:
    """Enveloppe de barres dérivée d'une enveloppe de barres brutes.

    ``as_of`` prend l'instant de la barre la PLUS RÉCENTE, jamais celui de la
    requête. Dater l'enregistrement de maintenant le ferait paraître frais un
    lundi matin alors que sa dernière séance est celle de vendredi : la porte
    de fraîcheur de la page Analyse mentirait au lieu d'avouer.
    """
    resultat = daily_bars_payload_from_bars(bars, spec)
    if resultat.payload is None:
        return None, resultat

    jours = [barre["trading_day"] for barre in resultat.payload["bars"]]
    plus_recente = max(
        barre.time for barre in bars.bars if barre.time.date().isoformat() in set(jours)
    )
    return (
        DataEnvelope(
            event_id=daily_bars_event_id(spec.con_id, min(jours), max(jours)),
            schema_version=DAILY_BARS_SCHEMA_VERSION,
            source=source_envelope.source,
            instrument_id=str(spec.con_id) if spec.con_id is not None else None,
            observed_at=plus_recente,
            received_at=source_envelope.received_at,
            as_of=plus_recente,
            stale_after=source_envelope.stale_after,
            quality_status=source_envelope.quality_status,
            delay_status=source_envelope.delay_status,
            connection_epoch=source_envelope.connection_epoch,
            rights=source_envelope.rights,
            payload_hash=canonical_json_hash(resultat.payload),
            payload=resultat.payload,
        ),
        resultat,
    )
