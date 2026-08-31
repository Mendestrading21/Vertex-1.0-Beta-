"""Contrat de la cotation quotidienne — déclaré UNE fois, pour tous.

POURQUOI CE FICHIER EXISTE. La forme d'une cotation quotidienne était
implicite, éclatée entre deux endroits qui ne se connaissent pas :
`vertex_core.synthetic.market._quote_payload` la produisait, et
`vertex_worker.markets._parse_quote` la relisait. Tant qu'une seule source
existait, l'accord tenait par coïncidence. Dès qu'une deuxième source réelle
produit des cotations, l'accord doit être **déclaré**, sinon il dérive en
silence — et une dérive ici se voit à l'écran sous forme de page vide, sans
message d'erreur.

Ce module vit dans `vertex_core` parce que c'est la SEULE dépendance commune
à `apps/edge-ibkr` (qui produit) et `apps/worker` (qui relit). L'y placer
évite qu'un des deux dépende de l'autre.

SUR LE SECTEUR NON CLASSÉ. Vertex n'a aujourd'hui aucune source de
classification sectorielle pour des instruments réels. Le code déclaré ici
n'est donc pas un secteur : c'est l'aveu explicite qu'il n'y en a pas. Le
libellé le dit à l'écran plutôt que de laisser croire à un classement.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

__all__ = [
    "DAILY_BARS_REQUIRED_FIELDS",
    "DAILY_BARS_TYPE",
    "DAILY_BAR_REQUIRED_FIELDS",
    "DAILY_QUOTE_REQUIRED_FIELDS",
    "DAILY_QUOTE_TYPE",
    "UNCLASSIFIED_SECTOR_CODE",
    "UNCLASSIFIED_SECTOR_LABEL",
    "DailyBarError",
    "DailyBarsError",
    "DailyQuoteError",
    "build_daily_bar",
    "build_daily_bars_payload",
    "build_daily_quote_payload",
    "format_price",
]

#: Marqueur de nature, lu par les consommateurs de cotations.
DAILY_QUOTE_TYPE = "daily_quote"

#: Champs SANS lesquels `vertex_worker.markets._parse_quote` refuse la
#: cotation. Les nommer ici rend le contrat vérifiable des deux côtés.
DAILY_QUOTE_REQUIRED_FIELDS: tuple[str, ...] = (
    "type",
    "ticker",
    "sector",
    "trading_day",
    "close",
    "adjustment_basis",
)

#: Absence DÉCLARÉE de classification sectorielle — pas un secteur.
UNCLASSIFIED_SECTOR_CODE = "NON_CLASSE"
UNCLASSIFIED_SECTOR_LABEL = "Secteur non déclaré"


class DailyQuoteError(ValueError):
    """Cotation quotidienne incomplète, vide ou numériquement impossible."""


def _require_text(nom: str, valeur: str | None) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise DailyQuoteError(f"{nom} : chaîne non vide requise, reçu {valeur!r}.")
    return valeur


def build_daily_quote_payload(
    *,
    ticker: str,
    sector: str,
    trading_day: str,
    close: Decimal,
    adjustment_basis: str,
    currency: str | None = None,
) -> dict[str, Any]:
    """Construit une cotation quotidienne VALIDE, ou refuse.

    Le refus est délibérément en amont : une charge utile invalide serait
    acceptée par la base (c'est du JSON) puis rejetée silencieusement à
    l'affichage, où l'utilisateur ne verrait qu'une page vide sans cause.

    ``close`` est un ``Decimal`` et le reste : il est sérialisé par ``str``,
    jamais par ``float``, pour que le centime survive au trajet.
    """
    ticker = _require_text("ticker", ticker)
    sector = _require_text("sector", sector)
    trading_day = _require_text("trading_day", trading_day)
    adjustment_basis = _require_text("adjustment_basis", adjustment_basis)

    try:
        date.fromisoformat(trading_day)
    except ValueError as erreur:
        raise DailyQuoteError(
            f"trading_day : date ISO (AAAA-MM-JJ) requise, reçu {trading_day!r}."
        ) from erreur

    if not isinstance(close, Decimal):
        raise DailyQuoteError(
            f"close : Decimal requis, reçu {type(close).__name__}. Un float "
            "perdrait l'exactitude du cours."
        )
    if not close.is_finite() or close <= 0:
        raise DailyQuoteError(f"close : valeur finie strictement positive requise, reçu {close}.")

    payload: dict[str, Any] = {
        "type": DAILY_QUOTE_TYPE,
        "ticker": ticker,
        "sector": sector,
        "trading_day": trading_day,
        "close": str(close),
        "adjustment_basis": adjustment_basis,
    }
    if currency is not None:
        payload["currency"] = _require_text("currency", currency)
    return payload


# ---------------------------------------------------------------------------
# Barres quotidiennes — le contrat de la page Analyse
# ---------------------------------------------------------------------------
#
# POURQUOI UN SECOND CONTRAT ICI. La page Marchés lit une COTATION (un jour,
# une clôture). La page Analyse lit des BARRES (un jour, OHLC + volume) : elle
# calcule des tendances, ce qu'une clôture seule ne permet pas. Ce sont deux
# formes distinctes, et les confondre viderait l'une des deux sans message.
#
# SUR LA DOUBLE VALIDATION. `vertex_worker.analysis._validate_bar` revalide
# tout ce qui est construit ici. Ce n'est PAS une redondance à supprimer : le
# producteur affirme, le consommateur vérifie, et le consommateur ne doit
# jamais faire confiance à un producteur — c'est ce qui rend l'ajout d'une
# source réelle sûr. Les formes admises sont déclarées ici pour que la dérive
# entre les deux côtés soit visible, pas pour qu'un côté cesse de vérifier.

#: Marqueur de nature des enregistrements de barres quotidiennes.
DAILY_BARS_TYPE = "daily_bars"

#: Champs SANS lesquels `vertex_worker.analysis` rejette l'enregistrement
#: entier (et non la seule barre fautive).
DAILY_BARS_REQUIRED_FIELDS: tuple[str, ...] = (
    "type",
    "ticker",
    "currency",
    "adjustment_basis",
    "bars",
)

#: Champs exigés de CHAQUE barre.
DAILY_BAR_REQUIRED_FIELDS: tuple[str, ...] = (
    "trading_day",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

#: Formes admises, recopiées du consommateur pour rendre l'accord vérifiable.
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_BASIS_CODE_RE = re.compile(r"^[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*$")
_PRICE_RE = re.compile(r"^(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?$")
_MAX_CODE_LENGTH = 32


class DailyBarsError(ValueError):
    """Enregistrement de barres quotidiennes hors contrat."""


class DailyBarError(DailyBarsError):
    """Barre isolée inutilisable — écartée et comptée, jamais réparée."""


def format_price(valeur: Decimal) -> str:
    """Prix en décimal simple, dans la forme que le consommateur admet.

    ``str(Decimal)`` peut produire une notation exponentielle (``2E+2``) que
    le consommateur rejette. ``format(..., "f")`` ne le fait jamais.
    """
    if not isinstance(valeur, Decimal):
        raise DailyBarError(
            f"prix : Decimal requis, reçu {type(valeur).__name__}. Un float "
            "perdrait l'exactitude du cours."
        )
    if not valeur.is_finite() or valeur <= 0:
        raise DailyBarError(f"prix : valeur finie strictement positive requise, reçu {valeur}.")
    texte = format(valeur, "f")
    if not _PRICE_RE.fullmatch(texte):
        # Plus de 8 décimales, ou plus de 16 chiffres entiers : la barre est
        # écartée. Arrondir ici falsifierait un cours pour le faire entrer
        # dans une forme — le refus est la seule réponse honnête.
        raise DailyBarError(f"prix : forme décimale non admise, reçu {texte!r}.")
    return texte


def build_daily_bar(
    *,
    trading_day: str,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
) -> dict[str, Any]:
    """Construit UNE barre quotidienne valide, ou refuse en le disant.

    ``volume`` arrive en ``Decimal`` (IBKR le renvoie ainsi) et doit être un
    entier exact : un volume fractionnaire n'a pas de sens et serait arrondi
    en silence par un ``int()`` nu.
    """
    trading_day = _require_text("trading_day", trading_day)
    try:
        date.fromisoformat(trading_day)
    except ValueError as erreur:
        raise DailyBarError(
            f"trading_day : date ISO (AAAA-MM-JJ) requise, reçu {trading_day!r}."
        ) from erreur

    prix = {
        "open": format_price(open_),
        "high": format_price(high),
        "low": format_price(low),
        "close": format_price(close),
    }
    if high < max(open_, close) or low > min(open_, close):
        raise DailyBarError(
            f"barre incohérente : haut {high} / bas {low} n'encadrent pas "
            f"ouverture {open_} et clôture {close}."
        )

    if not isinstance(volume, Decimal):
        raise DailyBarError(f"volume : Decimal requis, reçu {type(volume).__name__}.")
    if not volume.is_finite() or volume < 0:
        raise DailyBarError(f"volume : entier fini positif ou nul requis, reçu {volume}.")
    if volume != volume.to_integral_value():
        raise DailyBarError(f"volume : entier exact requis, reçu {volume} (fractionnaire).")

    return {"trading_day": trading_day, **prix, "volume": int(volume)}


def build_daily_bars_payload(
    *,
    ticker: str,
    currency: str,
    adjustment_basis: str,
    bars: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Assemble l'enregistrement de barres, ou refuse.

    ``currency`` est OBLIGATOIRE ici alors qu'il est facultatif pour une
    cotation : `vertex_worker.analysis` rejette l'enregistrement entier sans
    lui. Le rendre facultatif produirait une page vide sans cause visible.
    """
    ticker = _require_text("ticker", ticker)
    currency = _require_text("currency", currency)
    adjustment_basis = _require_text("adjustment_basis", adjustment_basis)

    if not _CURRENCY_RE.fullmatch(currency):
        raise DailyBarsError(f"currency : code ISO-4217 requis, reçu {currency!r}.")
    if len(adjustment_basis) > _MAX_CODE_LENGTH or not _BASIS_CODE_RE.fullmatch(adjustment_basis):
        raise DailyBarsError(f"adjustment_basis : code admis requis, reçu {adjustment_basis!r}.")
    if not bars:
        raise DailyBarsError("bars : au moins une barre requise, aucune fournie.")

    return {
        "type": DAILY_BARS_TYPE,
        "ticker": ticker,
        "currency": currency,
        "adjustment_basis": adjustment_basis,
        "bars": [dict(barre) for barre in bars],
    }
