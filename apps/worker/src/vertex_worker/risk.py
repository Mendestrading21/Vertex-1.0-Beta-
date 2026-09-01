"""Page Risques : la matrice de correlation du perimetre declare.

CE QUE CETTE PAGE MONTRE. Une matrice bornee a [-1, 1] : deux actifs qui
montent et descendent ensemble portent le meme risque, meme sous deux noms.
Le calcul sous-jacent est ``risk.correlation``, lui-meme une renormalisation
de ``risk.covariance`` — approuve, teste, et dont l echelle depend des actifs.

LE PERIMETRE EST DECLARE, JAMAIS DEDUIT. ``RiskConfig.perimeter`` nomme les
instruments qui entrent dans la matrice. Le code ne le devine pas : choisir
QUI se compare a QUI est une decision de produit, au meme titre que l indice
de reference de la page Analyse. Un perimetre absent ne produit pas une
matrice vide mais un refus nomme.

L ALIGNEMENT SE PAIE, ET LE PRIX EST PUBLIE. ``risk.covariance`` exige une
matrice rectangulaire COMPLETE : une seance manquante est refusee, jamais
remplacee par zero. Des instruments de continents differents ne cotent pas les
memes jours, donc l intersection stricte est plus courte que chaque serie.
``coverage`` publie cette perte plutot que de la laisser deviner.

CE QUE LA MATRICE NE DIT PAS. Deux places qui ferment a des heures differentes
produisent des rendements « du meme jour » portant sur des instants disjoints.
Mesure le 2026-09-01 : SPX/N225 tombe a +0.168 non parce que Tokyo serait
decorrele du monde, mais parce que Tokyo ferme avant l ouverture de New York.
``synchronicity_warning`` porte cet avertissement dans le contenu publie —
l ecran ne doit pas laisser lire un artefact de fuseau comme un fait de marche.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from typing import Any

from sqlalchemy.orm import Session

from vertex_core.calculations.risk import (
    RiskCalculationError,
    correlation,
    covariance,
)
from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
)
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_worker.analysis import BarRecord, load_daily_bar_records
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "BAND_MODERATE_NEGATIVE",
    "BAND_MODERATE_POSITIVE",
    "BAND_SELF",
    "BAND_STRONG_NEGATIVE",
    "BAND_STRONG_POSITIVE",
    "BAND_WEAK",
    "DEFAULT_MODERATE_THRESHOLD",
    "DEFAULT_STRONG_THRESHOLD",
    "DEV_SYNTHETIC_RISK_CONFIG",
    "MINIMUM_COMMON_DAYS",
    "REASON_CALCULATION_REFUSED",
    "REASON_INSUFFICIENT_COMMON_DAYS",
    "REASON_NO_BARS",
    "REASON_PERIMETER_TOO_SMALL",
    "REASON_SOURCE_NOT_ALLOWED",
    "RISK_SCHEMA_VERSION",
    "SNAPSHOT_KIND_RISK",
    "TOPIC_RISK_MATRIX_REFRESH",
    "RiskConfig",
    "RiskMatrixHandler",
    "build_risk_matrix_content",
    "register_risk_handler",
]

log = logging.getLogger("vertex_worker.risk")

Clock = Callable[[], datetime]

TOPIC_RISK_MATRIX_REFRESH = "risk.matrix.refresh"
SNAPSHOT_KIND_RISK = "risk_matrix"
RISK_SCHEMA_VERSION = "vertex.risk-matrix/1.0"

MINIMUM_COMMON_DAYS = 30
"""Seances communes minimales sous lesquelles la matrice est REFUSEE.

``risk.covariance`` accepte deux observations (ddof = 1). Ce n est pas parce
qu un nombre SORT qu il veut dire quelque chose : une correlation sur trois
seances est du bruit presente comme une mesure. Le seuil est declare ici et
publie dans ``coverage`` — pas cache dans une condition."""

BAND_SELF = "self"
BAND_STRONG_POSITIVE = "strong_positive"
BAND_MODERATE_POSITIVE = "moderate_positive"
BAND_WEAK = "weak"
BAND_MODERATE_NEGATIVE = "moderate_negative"
BAND_STRONG_NEGATIVE = "strong_negative"

DEFAULT_MODERATE_THRESHOLD = 0.3
DEFAULT_STRONG_THRESHOLD = 0.7
"""Seuils PAR DEFAUT separant faible / modere / fort.

Ce sont des CONVENTIONS, pas des verites : 0.7 ne devient pas « fort » par
une propriete des marches. Elles sont declarees dans `RiskConfig`, publiees
avec la matrice, et l ecran les affiche — un seuil qu on ne peut pas lire ne
peut pas etre discute."""

REASON_NO_BARS = "no_bars"
REASON_PERIMETER_TOO_SMALL = "perimeter_too_small"
REASON_INSUFFICIENT_COMMON_DAYS = "insufficient_common_days"
REASON_CALCULATION_REFUSED = "calculation_refused"
REASON_SOURCE_NOT_ALLOWED = "source_not_allowed"
REASON_RIGHTS_NOT_USABLE = "rights_not_usable"


@dataclass(frozen=True)
class RiskConfig:
    """Entrees DECLAREES de la matrice de risque.

    ``perimeter`` nomme les instruments compares, dans l ordre d affichage.
    ``labels`` porte leur libelle lisible. ``allowed_sources`` et
    ``usable_rights`` sont des registres deny-by-default, comme partout.
    """

    perimeter: tuple[str, ...]
    labels: Mapping[str, str]
    allowed_sources: frozenset[str]
    usable_rights: frozenset[str]
    minimum_common_days: int = MINIMUM_COMMON_DAYS
    moderate_threshold: float = DEFAULT_MODERATE_THRESHOLD
    strong_threshold: float = DEFAULT_STRONG_THRESHOLD
    lookback: timedelta = timedelta(days=14)
    max_observations: int = 500

    def __post_init__(self) -> None:
        if len(self.perimeter) < 2:
            raise ValueError(
                "perimeter: at least two instruments are required — "
                "a correlation matrix compares, it does not describe"
            )
        if len(set(self.perimeter)) != len(self.perimeter):
            raise ValueError("perimeter: duplicate instrument")
        if not isinstance(self.minimum_common_days, int) or self.minimum_common_days < 2:
            raise ValueError("minimum_common_days: must be an int >= 2 (ddof = 1)")
        if self.lookback <= timedelta(0):
            raise ValueError("lookback: must be a positive duration")
        if not isinstance(self.max_observations, int) or self.max_observations < 1:
            raise ValueError("max_observations: must be an int >= 1")
        if not 0.0 < self.moderate_threshold < self.strong_threshold < 1.0:
            raise ValueError(
                "thresholds: 0 < moderate < strong < 1 required — des seuils "
                "croises rendraient les bandes incoherentes"
            )


def _est_synthetique(record: BarRecord) -> bool:
    """Meme predicat que `markets.py` : une seule verite sur ce qui est faux."""
    return record.rights == SYNTHETIC_RIGHTS or record.source == SYNTHETIC_SOURCE


def _population(records: Sequence[BarRecord]) -> str:
    """Ce que la fenetre d entree contient REELLEMENT.

    Un aveu, pas une etiquette : une seule barre synthetique suffit a rendre
    toute la matrice synthetique, parce qu elle en a contamine les rendements.
    """
    if not records:
        return "EMPTY"
    if any(_est_synthetique(record) for record in records):
        return "SYNTHETIC"
    return "REAL"


def _closes_by_day(
    records: Sequence[BarRecord], config: RiskConfig
) -> tuple[dict[str, dict[str, Decimal]], list[dict[str, str]]]:
    """Clotures par ticker et par seance, plus les rejets NOMMES.

    Le ticker vient de la CHARGE (``payload["ticker"]``) et non de la colonne
    ``instrument_ref``, qui porte le ``con_id`` : deux identifiants pour deux
    usages, chacun compare au champ qui lui correspond.
    """
    perimetre = set(config.perimeter)
    par_ticker: dict[str, dict[str, Decimal]] = {}
    rejets: list[dict[str, str]] = []

    # Ordre deterministe : la derniere observation d une seance l emporte.
    for record in sorted(records, key=lambda r: (r.as_of, r.event_id)):
        if record.source not in config.allowed_sources:
            rejets.append({"event_id": record.event_id, "reason": REASON_SOURCE_NOT_ALLOWED})
            continue
        if record.rights not in config.usable_rights:
            rejets.append({"event_id": record.event_id, "reason": REASON_RIGHTS_NOT_USABLE})
            continue
        payload = record.payload
        if not isinstance(payload, Mapping):
            continue
        ticker = payload.get("ticker")
        if not isinstance(ticker, str) or ticker not in perimetre:
            continue  # hors perimetre : ni une erreur, ni une donnee
        barres = payload.get("bars")
        if not isinstance(barres, Sequence):
            continue
        jours = par_ticker.setdefault(ticker, {})
        for barre in barres:
            if not isinstance(barre, Mapping):
                continue
            jour = barre.get("trading_day")
            cloture = barre.get("close")
            if not isinstance(jour, str) or cloture is None:
                continue
            try:
                valeur = Decimal(str(cloture))
            except (InvalidOperation, ValueError):
                continue
            if not valeur.is_finite() or valeur <= 0:
                continue
            jours[jour] = valeur
    return par_ticker, rejets


def _bande(valeur: float, config: RiskConfig) -> str:
    """La bande d un coefficient, d apres les seuils DECLARES du registre.

    Le signe compte autant que l intensite : deux actifs a -0.85 sont aussi
    fortement lies que deux a +0.85, mais en sens contraire. Les confondre
    dans une seule bande « fort » effacerait la seule information qui rend une
    matrice utile — ce qui protege de ce qui accompagne.
    """
    intensite = abs(valeur)
    if intensite >= config.strong_threshold:
        return BAND_STRONG_POSITIVE if valeur > 0 else BAND_STRONG_NEGATIVE
    if intensite >= config.moderate_threshold:
        return BAND_MODERATE_POSITIVE if valeur > 0 else BAND_MODERATE_NEGATIVE
    return BAND_WEAK


def build_risk_matrix_content(
    records: Sequence[BarRecord], *, now: datetime, config: RiskConfig
) -> dict[str, Any]:
    """Contenu de l instantane Risques. Pure et deterministe.

    Chaque instrument du perimetre est SOIT dans la matrice, SOIT ecarte avec
    un motif nomme. Rien n est interpole, aucune seance manquante n est
    remplacee.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")

    par_ticker, rejets = _closes_by_day(records, config)

    ecartes: list[dict[str, str]] = []
    retenus: list[str] = []
    for ticker in config.perimeter:
        if len(par_ticker.get(ticker, {})) < 2:
            ecartes.append({"instrument": ticker, "reason": REASON_NO_BARS})
        else:
            retenus.append(ticker)

    seances_par_instrument = {t: len(par_ticker[t]) for t in retenus}

    def refus(motif: str, communs: int, message: str) -> dict[str, Any]:
        return {
            "schema_version": RISK_SCHEMA_VERSION,
            "as_of": now.isoformat(),
            "population": _population(records),
            "data_state": "insufficient",
            "unit": "correlation_coefficient",
            "engine_version": ENGINE_VERSION,
            "conclusion": message,
            "instruments": [],
            "matrix": [],
            "matrix_bands": [],
            "extremes": None,
            "synchronicity_warning": None,
            "coverage": {
                "perimeter": list(config.perimeter),
                "perimeter_size": len(config.perimeter),
                "retained": retenus,
                "retained_count": len(retenus),
                "discarded": ecartes,
                "rejected_records": rejets,
                "common_trading_days": communs,
                "minimum_common_days": config.minimum_common_days,
                "moderate_threshold": f"{config.moderate_threshold:.2f}",
                "strong_threshold": f"{config.strong_threshold:.2f}",
                "trading_days_per_instrument": seances_par_instrument,
                "observations_considered": len(records),
                "lookback_seconds": int(config.lookback.total_seconds()),
                "refusal_reason": motif,
            },
        }

    if len(retenus) < 2:
        return refus(
            REASON_PERIMETER_TOO_SMALL,
            0,
            "Moins de deux instruments du périmètre ont des barres : une "
            "matrice de corrélation compare, elle ne décrit pas.",
        )

    # Intersection STRICTE : les seances ou TOUS les instruments retenus cotent.
    communs = sorted(set.intersection(*(set(par_ticker[t]) for t in retenus)))
    if len(communs) - 1 < config.minimum_common_days:
        return refus(
            REASON_INSUFFICIENT_COMMON_DAYS,
            len(communs),
            f"Seulement {len(communs)} séances communes aux "
            f"{len(retenus)} instruments retenus, sous le seuil déclaré de "
            f"{config.minimum_common_days}. Une corrélation sur si peu de "
            "séances serait du bruit présenté comme une mesure.",
        )

    # Rendements simples, une ligne par seance, une colonne par instrument.
    lignes: list[list[float]] = []
    for precedent, courant in pairwise(communs):
        lignes.append(
            [float(par_ticker[t][courant] / par_ticker[t][precedent] - 1) for t in retenus]
        )

    try:
        resultat = correlation(covariance(lignes))
    except RiskCalculationError as erreur:
        return refus(REASON_CALCULATION_REFUSED, len(communs), str(erreur))

    # -- extremes : la paire la plus liee et la plus opposee, hors diagonale
    plus_haute: tuple[str, str, float] | None = None
    plus_basse: tuple[str, str, float] | None = None
    for i, gauche in enumerate(retenus):
        for j, droite in enumerate(retenus):
            if j <= i:
                continue
            valeur = resultat.matrix[i][j]
            if plus_haute is None or valeur > plus_haute[2]:
                plus_haute = (gauche, droite, valeur)
            if plus_basse is None or valeur < plus_basse[2]:
                plus_basse = (gauche, droite, valeur)

    def paire(p: tuple[str, str, float] | None) -> dict[str, Any] | None:
        if p is None:
            return None
        return {"a": p[0], "b": p[1], "value": f"{p[2]:.3f}"}

    perdues = {t: seances_par_instrument[t] - len(communs) for t in retenus}
    return {
        "schema_version": RISK_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": _population(records),
        "data_state": "ok" if not ecartes and not rejets else "partial",
        "unit": "correlation_coefficient",
        "engine_version": ENGINE_VERSION,
        "conclusion": (
            f"Matrice de corrélation sur {len(retenus)} instruments et "
            f"{resultat.n_observations} rendements, du {communs[0]} au "
            f"{communs[-1]}."
        ),
        "instruments": [{"ticker": t, "label": config.labels.get(t, t)} for t in retenus],
        # Chaines rendues cote serveur : le navigateur ne calcule rien.
        "matrix": [[f"{valeur:.3f}" for valeur in ligne] for ligne in resultat.matrix],
        # La BANDE de chaque case, decidee ICI : classer un coefficient
        # (« fortement lie », « faible ») est un jugement de domaine, pas une
        # mise en page. L ecran choisit une couleur a partir d un NOM et ne
        # relit jamais le nombre — `.claude/rules/frontend.md`.
        "matrix_bands": [
            [BAND_SELF if i == j else _bande(valeur, config) for j, valeur in enumerate(ligne)]
            for i, ligne in enumerate(resultat.matrix)
        ],
        "extremes": {"most_correlated": paire(plus_haute), "most_opposed": paire(plus_basse)},
        "synchronicity_warning": (
            "Les places ne ferment pas à la même heure. Deux rendements « du "
            "même jour » peuvent porter sur des instants disjoints, ce qui "
            "abaisse artificiellement la corrélation entre continents."
        ),
        "coverage": {
            "perimeter": list(config.perimeter),
            "perimeter_size": len(config.perimeter),
            "retained": retenus,
            "retained_count": len(retenus),
            "discarded": ecartes,
            "rejected_records": rejets,
            "common_trading_days": len(communs),
            "minimum_common_days": config.minimum_common_days,
            # Publies pour etre LUS a l ecran : un seuil invisible ne se
            # discute pas.
            "moderate_threshold": f"{config.moderate_threshold:.2f}",
            "strong_threshold": f"{config.strong_threshold:.2f}",
            "trading_days_per_instrument": seances_par_instrument,
            # Le prix de l alignement, publie plutot que laisse deviner.
            "trading_days_lost_to_alignment": perdues,
            "window_start": communs[0],
            "window_end": communs[-1],
            "observations_considered": len(records),
            "lookback_seconds": int(config.lookback.total_seconds()),
            "refusal_reason": None,
        },
    }


class RiskMatrixHandler:
    """Handler de ``risk.matrix.refresh`` : recalcule la matrice."""

    def __init__(self, *, config: RiskConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        from vertex_worker.handlers import publish_if_changed

        now = self._clock()
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("clock returned a naive datetime; aware UTC required")
        records = load_daily_bar_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )
        content = build_risk_matrix_content(records, now=now, config=self._config)
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_RISK,
            key="global",
            content=content,
            as_of=now,
        )
        if published is None:
            log.info("risk matrix unchanged (message_id=%s)", message.id)
        else:
            log.info(
                "risk matrix published version=%s retained=%s (message_id=%s)",
                published.version,
                content["coverage"]["retained_count"],
                message.id,
            )


def register_risk_handler(registry: HandlerRegistry, *, clock: Clock, config: RiskConfig) -> None:
    """Enregistre la matrice de risque sur ``risk.matrix.refresh``."""
    registry.register(TOPIC_RISK_MATRIX_REFRESH, RiskMatrixHandler(config=config, clock=clock))


_SYNTHETIC_PERIMETER = SYNTHETIC_FOCUS_TICKERS
"""Les QUATRE tickers de mise au point, et pas six pris au hasard.

Ce sont les SEULS du jeu synthetique a porter des barres quotidiennes
(`generate_daily_bar_envelopes`, 60 barres chacun). Un perimetre visant
d autres tickers ferait refuser la page « aucune barre » sur une base pourtant
semee — un ecran vide dont la cause serait introuvable."""

DEV_SYNTHETIC_RISK_CONFIG = RiskConfig(
    perimeter=_SYNTHETIC_PERIMETER,
    labels={t: t for t in _SYNTHETIC_PERIMETER},
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)
"""Registre de developpement UNIQUEMENT : la source et les droits
synthetiques, sur six tickers du jeu de demonstration. Toute matrice qu il
produit est honnetement etiquetee ``population = "SYNTHETIC"``."""
