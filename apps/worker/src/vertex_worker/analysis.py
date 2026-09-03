"""Analysis dossier snapshot chain: ``analysis.ingested`` handler.

Topic decision (documented, same pattern as ``quotes.ingested``): ingestion
enqueues an ADDITIONAL ``analysis.ingested`` message for every daily-bars
envelope AND for every option-chain envelope (a chain update changes the
scenario basis of the dossier). The registry stays one-handler-per-topic;
within one ingestion the chain job is enqueued before the analysis job, so a
drained outbox recomputes the chain snapshot before the dossier reads it.

The handler recomputes one ``analysis/{instrument}`` snapshot per declared
focus instrument present in the recent bars window:

- the admitted daily OHLCV bars relayed VERBATIM (decimal strings) after a
  fail-closed per-bar validation (an invalid bar is discarded WITH its
  reason, never repaired), plus the last close. This handler is the
  ADMISSION frontier of those source-controlled values: every payload field
  it relays into the published dossier (``currency``, ``adjustment_basis``,
  ``trading_day``, the four prices) must match its declared SHAPE — an
  ISO-4217 code, a technical code, a real ISO day, a plain decimal. A value
  out of shape is NEVER cleaned, escaped or truncated: it excludes its bar
  (``discarded``) or the whole observation (``coverage.rejected_records``)
  with a typed reason, and the rest of the dossier is still produced;
- une comparaison base 100 SERVIE contre l'indice de reference DECLARE
  (``market.rebased_series``) : les deux series sont ramenees a la meme base
  sur les SEULES seances communes, intersectees ICI. La page ne recoit rien a
  aligner et ne rebase rien — un rebasage dans le navigateur serait un calcul
  financier en TypeScript, interdit par ``.claude/rules/frontend.md``. L'indice
  passe la MEME porte d'admission que l'instrument ; un refus est NOMME
  (``BENCHMARK_NOT_OBSERVED``, ``INSUFFICIENT_SAMPLE``, devise ou base
  d'ajustement divergente), jamais une serie tronquee en silence;

- a short evidence rail: the ticker's content clusters from the single
  deterministic fusion engine (``vertex_core.fusion.fuse``) — dedup only,
  no invented relevance;
- simple scenarios through ``vertex_core.calculations.options.scenario_grid``
  ONLY when the published option chain of the instrument carries a healthy
  contract (sane quote AND resolved Vertex IV); otherwise the block is
  honestly ``ABSENT`` with its reason. Scenario values are labeled
  ``value_nature = "THEORETICAL"`` and keep their ``CalculationRecord``
  lineage;
- the canonical ``AdviceResult`` produced by THE single ``AdviceEngine`` on
  ``AdviceInputs`` built HONESTLY from the retained population:
  facts the worker genuinely holds are filled (identity in the declared
  universe without an IBKR con_id, snapshot quality/freshness from the bars,
  the statuses of the calculations actually run, the portfolio-risk
  requirement DECLARED by the caller's ``AnalysisConfig``, no probability
  used); facts nobody holds (entitlements, session/event calendar, liquidity
  thresholds, contradiction review, user constraints, and the manual
  portfolio declarations when the caller requires them) stay ``None`` and
  their gates BLOCK ``UNEVALUABLE`` —
  fail-closed. The resulting status (typically ``INSUFFICIENT_DATA``) is
  published AS IS: the worker NEVER forces a status, and ``direction`` stays
  ``UNKNOWN`` because no upstream analytical reading exists. Population
  wording in the explanation and risk summary is derived from the same
  retained inputs as the top-level ``population`` field; real observations
  are never described as synthetic fixtures.

Publication follows the same publish-if-changed semantics as the other
handlers.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from vertex_core.calculations.options import (
    OptionInputError,
    OptionLeg,
    scenario_grid,
)
from vertex_core.contracts import CalculationRecord, make_calculation_record
from vertex_core.contracts.enums import (
    CalculationStatus,
    Direction,
    EnvelopeQuality,
    IdentityStatus,
    SnapshotQuality,
)
from vertex_core.decision import AdviceEngine, AdviceInputs
from vertex_core.decision.advice import (
    CalculationsInput,
    InstrumentResolutionInput,
    PortfolioRiskInput,
    ProbabilityInput,
    SnapshotInput,
)
from vertex_core.fusion import fuse
from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
)
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.models import Observation
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.registry import HandlerRegistry

if TYPE_CHECKING:  # import-time cycle avoidance (handlers -> ingest -> here)
    from vertex_worker.handlers import ObservationRecord

__all__ = [
    "ANALYSIS_SCHEMA_VERSION",
    "DAILY_BARS_SCHEMA_PREFIXES",
    "DEV_SYNTHETIC_ANALYSIS_CONFIG",
    "REASON_INVALID_ADJUSTMENT_BASIS",
    "REASON_INVALID_BAR",
    "REASON_INVALID_CURRENCY",
    "REASON_INVALID_PAYLOAD",
    "REASON_INVALID_TRADING_DAY",
    "REASON_NO_HEALTHY_CONTRACT",
    "REASON_NO_OPTION_CHAIN",
    "REASON_RIGHTS_NOT_USABLE",
    "REASON_SOURCE_NOT_ALLOWED",
    "SNAPSHOT_KIND_ANALYSIS",
    "TOPIC_ANALYSIS_INGESTED",
    "AnalysisConfig",
    "AnalysisHandler",
    "BarRecord",
    "build_analysis_content",
    "is_daily_bars_schema",
    "load_daily_bar_records",
    "register_analysis_handler",
]

log = logging.getLogger("vertex_worker.analysis")

Clock = Callable[[], datetime]

TOPIC_ANALYSIS_INGESTED = "analysis.ingested"
"""Outbox topic enqueued (in addition to ``observation.ingested``) for every
newly written daily-bars or option-chain observation."""

SNAPSHOT_KIND_ANALYSIS = "analysis"
ANALYSIS_SCHEMA_VERSION = "vertex.analysis/1.0"

DAILY_BARS_SCHEMA_PREFIXES: tuple[str, ...] = (
    "synthetic-daily-bars/",
    "ibkr.daily-bars/",
)
"""Familles de barres quotidiennes ADMISES par la page Analyse.

``ibkr.daily-bars/`` est la forme derivee par
``vertex_edge_ibkr.normalize.daily_bars_envelope`` : la barre BRUTE
d'IBKR (``ibkr.bars/``) n'est deliberement PAS admise ici, car ce
schema couvre toutes les tailles de barre. Y laisser entrer une barre
horaire ferait passer une bougie de 60 minutes pour une seance."""
"""Schema families recognized as daily OHLCV bars (deny by default)."""

VALUE_NATURE_THEORETICAL = "THEORETICAL"

REASON_INVALID_BAR = "invalid_bar"
REASON_INVALID_PAYLOAD = "invalid_payload"
REASON_INVALID_CURRENCY = "invalid_currency"
REASON_INVALID_ADJUSTMENT_BASIS = "invalid_adjustment_basis"
REASON_INVALID_TRADING_DAY = "invalid_trading_day"
REASON_SOURCE_NOT_ALLOWED = "source_not_allowed"
REASON_RIGHTS_NOT_USABLE = "rights_not_usable"
REASON_NO_OPTION_CHAIN = "no_option_chain_snapshot"
REASON_NO_HEALTHY_CONTRACT = "no_healthy_option_contract"

# --------------------------------------------------------------------------
# Admission allowlists: SHAPE of every source-controlled payload field this
# module relays into the published dossier.
#
# The dossier is read downstream by the explanation layer, which concatenates
# some of these values into FACT sentences. The frontier that ADMITS a value
# is this worker, so a value whose SHAPE is not the declared one is never
# repaired, escaped or truncated here: it EXCLUDES its element (the bar, or
# the whole observation) with a typed reason published in the dossier —
# fail-closed, and without cancelling the rest of the dossier.
# --------------------------------------------------------------------------

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
"""ISO-4217 alphabetic code: exactly three ASCII capitals."""

_TRADING_DAY_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
"""Strict ISO calendar day (the value must ALSO be a real date)."""

_BASIS_CODE_RE = re.compile(r"^[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*$")
"""Technical code (``synthetic-unadjusted``, ``split_adjusted``, ...)."""

_PRICE_RE = re.compile(r"^(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?$")
"""Plain positive decimal string. ASCII digits only: no sign, no exponent,
no underscore, no surrounding whitespace, no Unicode digit — all of which
``Decimal`` would otherwise accept and this module would relay VERBATIM."""

_MAX_CODE_LENGTH = 32


def _currency_or_none(value: Any) -> str | None:
    """The ISO-4217 code itself, or ``None`` when the shape is not admitted."""
    if not isinstance(value, str) or not _CURRENCY_RE.fullmatch(value):
        return None
    return value


def _trading_day_or_none(value: Any) -> str | None:
    """The ISO day itself, or ``None`` (shape rejected, or not a real date)."""
    if not isinstance(value, str) or not _TRADING_DAY_RE.fullmatch(value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _basis_code_or_none(value: Any) -> str | None:
    """The adjustment-basis code itself, or ``None`` when out of shape."""
    if not isinstance(value, str) or len(value) > _MAX_CODE_LENGTH:
        return None
    if not _BASIS_CODE_RE.fullmatch(value):
        return None
    return value


def _price_or_none(value: Any) -> tuple[str, Decimal] | None:
    """The verbatim price string AND its Decimal, or ``None`` when out of
    shape. Guarantees that what is relayed verbatim is a plain decimal."""
    if not isinstance(value, str) or not _PRICE_RE.fullmatch(value):
        return None
    parsed = Decimal(value)
    return (value, parsed) if parsed.is_finite() else None


_CODE_SHA = f"module:vertex_core.calculations.options@{ENGINE_VERSION}"
_SPOT_SHOCKS = (Decimal("0.90"), Decimal("0.95"), Decimal("1.00"), Decimal("1.05"), Decimal("1.10"))
_CENTS = Decimal("0.01")

#: Fenetres des indicateurs. Declarees ici, jamais deduites de la taille des
#: donnees disponibles : calculer une volatilite « sur ce qu'on a » produirait
#: un nombre dont personne ne connaitrait la periode.
VOLATILITY_WINDOW = 20
ATR_LOOKBACK = 14

#: Seances par an, pour l'annualisation. 252 est la convention des barres
#: quotidiennes de marches actions.
TRADING_PERIODS_PER_YEAR = 252

#: Statut publie quand la fenetre demandee depasse l'historique disponible.
REASON_INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"

#: Horizon de la force relative, en seances communes aux deux series.
RELATIVE_STRENGTH_HORIZON = 60

#: Raisons d'absence de la force relative, chacune nommee.
REASON_NO_BENCHMARK = "NO_BENCHMARK_DECLARED"
REASON_BENCHMARK_ABSENT = "BENCHMARK_NOT_OBSERVED"
REASON_IS_BENCHMARK = "INSTRUMENT_IS_BENCHMARK"

#: Base commune de la comparaison servie (`market.rebased_series`). DECLAREE
#: ici et PUBLIEE dans le bloc : une page qui choisirait sa propre base
#: afficherait deux courbes que rien ne rend comparables.
REBASE_BASE_VALUE = Decimal("100")

#: Minimum de seances communes pour publier une comparaison. DEUX : avec une
#: seule seance commune les deux series valent EXACTEMENT la base et la
#: comparaison ne compare rien. Exiger davantage inventerait un seuil que
#: personne n'a declare.
REBASED_COMPARISON_MIN_SESSIONS = 2

#: Refus NOMMES de la comparaison base 100. Rebaser deux series qui ne
#: partagent ni la devise ni la base d'ajustement affiche un ecart FAUX --
#: derive de change ou detachement de dividende lu comme une performance --
#: que rien a l'ecran ne signalerait.
REASON_BENCHMARK_CURRENCY_MISMATCH = "BENCHMARK_CURRENCY_MISMATCH"
REASON_BENCHMARK_BASIS_MISMATCH = "BENCHMARK_ADJUSTMENT_BASIS_MISMATCH"


def is_daily_bars_schema(schema_version: str) -> bool:
    """``True`` when ``schema_version`` belongs to a declared bars family."""
    return isinstance(schema_version, str) and schema_version.startswith(DAILY_BARS_SCHEMA_PREFIXES)


@dataclass(frozen=True)
class BarRecord:
    """ORM-free view of one persisted daily-bars observation."""

    event_id: str
    source: str
    instrument_ref: str | None
    as_of: datetime
    quality_status: str
    rights: str
    schema_version: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class SerieAdmise:
    """Serie quotidienne d'un ticker ADMISE par la porte du dossier.

    Elle transporte ses UNITES (devise, base d'ajustement) avec ses barres :
    comparer deux series exige de savoir dans quoi chacune est libellee, et
    aller rechercher cette information ailleurs reviendrait a la deviner.
    """

    ticker: str
    bars: tuple[Mapping[str, Any], ...]
    currency: str
    adjustment_basis: str
    event_id: str


def _is_synthetic_bar(record: BarRecord) -> bool:
    return record.rights == SYNTHETIC_RIGHTS or record.source == SYNTHETIC_SOURCE


@dataclass(frozen=True)
class AnalysisConfig:
    """Declared inputs of the analysis dossier builder (owned upstream)."""

    instruments: tuple[str, ...]
    allowed_sources: frozenset[str]
    usable_rights: frozenset[str]
    lookback: timedelta = timedelta(hours=72)
    max_observations: int = 500
    bars_freshness: timedelta = timedelta(hours=48)
    advice_validity: timedelta = timedelta(hours=1)
    max_evidence: int = 5
    horizon: str = "1d"
    #: Symbole de l'indice de reference pour `market.relative_strength`.
    #: `None` = aucun indice declare : l'indicateur est ABSENT avec sa raison,
    #: jamais calcule contre un indice choisi par le code.
    benchmark: str | None = None
    portfolio_risk_required: bool = False
    """Whether gate 7 must be OBSERVED for this population.

    ``False`` states the honest fact of the analysis page: no strategy
    profile requires a manual portfolio-fit here, so the gate PASSES
    ``NOT_REQUIRED``. A caller whose profile DOES require a portfolio fit
    (opportunities under ``equity_etf_swing_3_12m``) must set it to ``True``:
    the gate is then evaluated on the real user declarations and BLOCKS
    fail-closed while none exists — a required gate is never satisfied by
    declaration."""

    def __post_init__(self) -> None:
        if not self.instruments:
            raise ValueError("instruments: at least one instrument required")
        if self.lookback <= timedelta(0):
            raise ValueError("lookback: must be a positive duration")
        if self.bars_freshness <= timedelta(0):
            raise ValueError("bars_freshness: must be a positive duration")
        if self.advice_validity <= timedelta(0):
            raise ValueError("advice_validity: must be a positive duration")
        if not isinstance(self.max_observations, int) or self.max_observations < 1:
            raise ValueError("max_observations: must be an int >= 1")
        if not isinstance(self.max_evidence, int) or self.max_evidence < 1:
            raise ValueError("max_evidence: must be an int >= 1")
        if not self.horizon:
            raise ValueError("horizon: non-empty string required")
        if not isinstance(self.portfolio_risk_required, bool):
            raise ValueError("portfolio_risk_required: bool required")


DEV_SYNTHETIC_ANALYSIS_CONFIG = AnalysisConfig(
    instruments=SYNTHETIC_FOCUS_TICKERS,
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)
"""Development-only registry: ONLY the synthetic source/rights and the 4
declared focus instruments. Every snapshot it produces is population
``SYNTHETIC``."""


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def load_daily_bar_records(
    session: Session, *, now: datetime, lookback: timedelta, limit: int
) -> list[BarRecord]:
    """Load the bounded recent daily-bars window, deterministically ordered."""
    filters = [
        Observation.schema_version.like(f"{prefix}%") for prefix in DAILY_BARS_SCHEMA_PREFIXES
    ]
    schema_filter: ColumnElement[bool] = filters[0]
    for extra in filters[1:]:
        schema_filter = schema_filter | extra
    rows = (
        session.execute(
            select(Observation)
            .where(
                Observation.as_of <= now,
                Observation.as_of >= now - lookback,
                schema_filter,
            )
            .order_by(Observation.as_of.desc(), Observation.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        BarRecord(
            event_id=row.event_id,
            source=row.source,
            instrument_ref=row.instrument_ref,
            as_of=row.as_of,
            quality_status=row.quality_status,
            rights=row.rights,
            schema_version=row.schema_version,
            payload=row.payload,
        )
        for row in rows
    ]


# --------------------------------------------------------------------------
# Pure content helpers (no session, fully deterministic)
# --------------------------------------------------------------------------


def _num_string(value: float) -> str:
    return format(Decimal(repr(value)), "f")


def _calculation_meta(record: CalculationRecord) -> dict[str, Any]:
    return {
        "calculation_id": record.calculation_id,
        "engine_version": record.engine_version,
        "method": record.method,
        "input_hash": record.input_hash,
        "result_hash": record.result_hash,
        "status": record.status.value,
    }


def _decimal_or_none(value: Any) -> Decimal | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _validate_bar(raw: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Validate one OHLCV bar fail-closed.

    Returns ``(bar, None)`` for an admitted bar — relayed VERBATIM — or
    ``(None, reason)`` for a discarded one. A field whose SHAPE is not the
    declared one is never repaired: it discards the bar with its reason.
    """
    if not isinstance(raw, Mapping):
        return None, REASON_INVALID_BAR
    trading_day = _trading_day_or_none(raw.get("trading_day"))
    if trading_day is None:
        return None, REASON_INVALID_TRADING_DAY
    prices: dict[str, tuple[str, Decimal]] = {}
    for name in ("open", "high", "low", "close"):
        price = _price_or_none(raw.get(name))
        if price is None:
            return None, REASON_INVALID_BAR
        prices[name] = price
    volume = raw.get("volume")
    if isinstance(volume, bool) or not isinstance(volume, int) or volume < 0:
        return None, REASON_INVALID_BAR
    open_, high, low, close = (prices[name][1] for name in ("open", "high", "low", "close"))
    if min(open_, high, low, close) <= 0:
        return None, REASON_INVALID_BAR
    if high < max(open_, close) or low > min(open_, close):
        return None, REASON_INVALID_BAR
    return {
        "trading_day": trading_day,
        "open": prices["open"][0],
        "high": prices["high"][0],
        "low": prices["low"][0],
        "close": prices["close"][0],
        "volume": volume,
    }, None


def _instrument_ref_de(
    bar_records: Sequence[Any], instrument: str
) -> str | None:
    """`instrument_ref` de l'instrument, releve sur ses propres barres.

    Les observations portent le `con_id` en `instrument_ref` tandis que les
    pages parlent en TICKER : la correspondance n'est nulle part ailleurs, et
    l'inventer serait deviner. Sans barre pour cet instrument, on rend `None`
    et la fenetre reste globale — le comportement d'avant, jamais pire.
    """
    for record in bar_records:
        charge = record.payload if isinstance(record.payload, Mapping) else {}
        if charge.get("ticker") == instrument and record.instrument_ref:
            return str(record.instrument_ref)
    return None


def _build_indicators(
    valid_bars: Sequence[Mapping[str, Any]],
    *,
    now: datetime,
    source_event_id: str | None,
) -> dict[str, Any]:
    """Indicateurs techniques, calcules par le moteur approuve.

    Chaque entree porte sa valeur ET sa tracabilite. Aucune interpretation
    n'est publiee : un ATR est une amplitude, pas un jugement ; le qualifier
    d'« eleve » exigerait un seuil declare, et il n'y en a pas.

    Une fenetre plus longue que l'historique disponible ne produit PAS une
    valeur approchee : elle produit `INSUFFICIENT_SAMPLE` avec le compte reel.
    """
    from vertex_core.calculations.market import (
        CalculationInputError,
        OhlcBar,
        atr,
        realized_volatility,
    )

    indicateurs: dict[str, Any] = {}
    evenements = (source_event_id,) if source_event_id else ()

    # -- volatilite realisee annualisee -------------------------------------
    cloture_series = [Decimal(bar["close"]) for bar in valid_bars]
    if len(cloture_series) < VOLATILITY_WINDOW + 1:
        indicateurs["realized_volatility"] = {
            "status": REASON_INSUFFICIENT_SAMPLE,
            "window": VOLATILITY_WINDOW,
            "available_bars": len(cloture_series),
            "detail": (
                f"{VOLATILITY_WINDOW + 1} clotures requises pour "
                f"{VOLATILITY_WINDOW} rendements ; {len(cloture_series)} disponibles"
            ),
        }
    else:
        fenetre = cloture_series[-(VOLATILITY_WINDOW + 1) :]
        rendements = [float(fenetre[i] / fenetre[i - 1] - 1) for i in range(1, len(fenetre))]
        debut = now
        try:
            valeur = realized_volatility(rendements, TRADING_PERIODS_PER_YEAR)
        except CalculationInputError as erreur:
            indicateurs["realized_volatility"] = {
                "status": "REFUSED",
                "window": VOLATILITY_WINDOW,
                "reason": erreur.reason,
                "detail": erreur.detail,
            }
        else:
            enregistrement = make_calculation_record(
                calculation_id="market.realized_volatility",
                calculation_type="market_statistic",
                code_sha=f"module:vertex_core.calculations.market@{ENGINE_VERSION}",
                method="unbiased sample stdev of daily simple returns, annualized",
                inputs={
                    "returns": [_num_string(r) for r in rendements],
                    "periods_per_year": TRADING_PERIODS_PER_YEAR,
                },
                result={"value": _num_string(valeur)},
                started_at=debut,
                completed_at=now,
                source_event_ids=evenements,
            )
            # Forme en pourcentage produite ICI : multiplier par 100 dans le
            # navigateur serait un calcul financier en TypeScript, ce que
            # `.claude/rules/frontend.md` interdit. La page Marches suit deja
            # cette regle avec `return_1d_pct`.
            en_pourcent = (Decimal(_num_string(valeur)) * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
            indicateurs["realized_volatility"] = {
                "status": "OK",
                "window": VOLATILITY_WINDOW,
                "unit": "annualized_ratio",
                "value": _num_string(valeur),
                "value_pct": format(en_pourcent, "f"),
                "calculation": _calculation_meta(enregistrement),
            }

    # -- ATR ----------------------------------------------------------------
    if len(valid_bars) < ATR_LOOKBACK + 1:
        indicateurs["atr"] = {
            "status": REASON_INSUFFICIENT_SAMPLE,
            "lookback": ATR_LOOKBACK,
            "available_bars": len(valid_bars),
            "detail": (f"{ATR_LOOKBACK + 1} barres requises ; {len(valid_bars)} disponibles"),
        }
    else:
        recentes = list(valid_bars)[-(ATR_LOOKBACK + 1) :]
        debut = now
        try:
            barres = tuple(
                OhlcBar(
                    timestamp=datetime.fromisoformat(bar["trading_day"]).replace(tzinfo=UTC),
                    open=Decimal(bar["open"]),
                    high=Decimal(bar["high"]),
                    low=Decimal(bar["low"]),
                    close=Decimal(bar["close"]),
                )
                for bar in recentes
            )
            valeur = atr(barres, ATR_LOOKBACK)
        except (CalculationInputError, ValueError) as erreur:
            indicateurs["atr"] = {
                "status": "REFUSED",
                "lookback": ATR_LOOKBACK,
                "reason": getattr(erreur, "reason", "invalid_bar"),
                "detail": str(erreur),
            }
        else:
            enregistrement = make_calculation_record(
                calculation_id="market.atr",
                calculation_type="market_statistic",
                code_sha=f"module:vertex_core.calculations.market@{ENGINE_VERSION}",
                method="Wilder true range, arithmetic mean over the lookback",
                inputs={
                    "bars": [bar["trading_day"] for bar in recentes],
                    "lookback": ATR_LOOKBACK,
                },
                result={"value": _num_string(valeur)},
                started_at=debut,
                completed_at=now,
                source_event_ids=evenements,
            )
            indicateurs["atr"] = {
                "status": "OK",
                "lookback": ATR_LOOKBACK,
                "unit": "price",
                "value": _num_string(valeur),
                "calculation": _calculation_meta(enregistrement),
            }

    return indicateurs


def _barres_de(
    bar_records: Sequence[Any], ticker: str, *, config: AnalysisConfig
) -> tuple[SerieAdmise | None, tuple[dict[str, str], ...]]:
    """Serie d'un ticker, ADMISE par la MEME porte que l'instrument.

    Le constructeur possede deja toutes les barres de la fenetre : selectionner
    celles de l'indice de reference ne coute aucune requete supplementaire.

    ECART B2 (matrice R2), corrige ici : cette fonction relevait les barres
    SANS aucun controle, alors que l'instrument, lui, passe cinq portes. Un
    indice provenant d'une source non autorisee, porte par un droit
    inutilisable, ou dont la devise / la base d'ajustement n'a pas la FORME
    declaree entrait donc dans une comparaison servie. Le filtre applique ici
    est LITTERALEMENT celui de `build_analysis_content`, dans le meme ordre :
    ce qui est refuse a l'instrument est refuse a l'indice.

    L'enregistrement retenu est le DERNIER admis (ordre croissant), exactement
    comme pour l'instrument. Un enregistrement admis dont aucune barre ne
    survit a `_validate_bar` ne fournit pas de serie : il est rendu avec son
    motif plutot que remplace en silence par un enregistrement plus ancien.

    Rend `(serie, rejets)`. Les rejets nomment CHAQUE enregistrement ecarte :
    « pas encore collecte » et « collecte mais refuse » sont deux faits
    differents, et le dossier doit dire lequel.
    """
    rejets: list[dict[str, str]] = []
    retenu: tuple[Any, str, str] | None = None
    for record in sorted(bar_records, key=lambda r: (r.as_of, r.event_id)):
        charge = record.payload if isinstance(record.payload, Mapping) else {}
        if charge.get("ticker") != ticker:
            continue
        if record.source not in config.allowed_sources:
            rejets.append({"event_id": record.event_id, "reason": REASON_SOURCE_NOT_ALLOWED})
            continue
        if record.rights not in config.usable_rights:
            rejets.append({"event_id": record.event_id, "reason": REASON_RIGHTS_NOT_USABLE})
            continue
        if not isinstance(charge.get("bars"), list):
            rejets.append({"event_id": record.event_id, "reason": REASON_INVALID_PAYLOAD})
            continue
        devise = _currency_or_none(charge.get("currency"))
        if devise is None:
            rejets.append({"event_id": record.event_id, "reason": REASON_INVALID_CURRENCY})
            continue
        base = _basis_code_or_none(charge.get("adjustment_basis"))
        if base is None:
            rejets.append(
                {"event_id": record.event_id, "reason": REASON_INVALID_ADJUSTMENT_BASIS}
            )
            continue
        retenu = (record, devise, base)  # ordre croissant : le dernier admis gagne

    if retenu is None:
        return None, tuple(rejets)

    record, devise, base = retenu
    retenues: list[Mapping[str, Any]] = []
    for brute in record.payload["bars"]:
        barre, _ = _validate_bar(brute)
        if barre is not None:
            retenues.append(barre)
    if not retenues:
        rejets.append({"event_id": record.event_id, "reason": REASON_INVALID_BAR})
        return None, tuple(rejets)
    retenues.sort(key=lambda b: b["trading_day"])
    return (
        SerieAdmise(
            ticker=ticker,
            bars=tuple(retenues),
            currency=devise,
            adjustment_basis=base,
            event_id=record.event_id,
        ),
        tuple(rejets),
    )


def _relative_strength_block(
    valid_bars: Sequence[Mapping[str, Any]],
    benchmark_bars: Sequence[Mapping[str, Any]] | None,
    *,
    instrument: str,
    benchmark: str | None,
    now: datetime,
) -> dict[str, Any]:
    """Force relative contre un indice DECLARE, sur calendriers alignes.

    L'alignement est explicite : `market.relative_strength` refuse deux series
    de longueurs differentes et ne tronque jamais. Deux places n'ont pas les
    memes jours feries, on intersecte donc les jours de bourse AVANT d'appeler,
    et on publie le nombre de seances communes retenues.
    """
    from vertex_core.calculations.market import (
        CalculationInputError,
        relative_strength,
    )

    if benchmark is None:
        return {"status": REASON_NO_BENCHMARK, "detail": "aucun indice de référence déclaré"}
    if benchmark == instrument:
        return {
            "status": REASON_IS_BENCHMARK,
            "benchmark": benchmark,
            "detail": "un instrument ne se compare pas à lui-même",
        }
    if not benchmark_bars:
        return {
            "status": REASON_BENCHMARK_ABSENT,
            "benchmark": benchmark,
            "detail": f"aucune barre observée pour {benchmark}",
        }

    # Intersection des jours de bourse : alignement, jamais troncature.
    par_jour_actif = {bar["trading_day"]: Decimal(bar["close"]) for bar in valid_bars}
    par_jour_indice = {
        bar["trading_day"]: Decimal(bar["close"]) for bar in benchmark_bars
    }
    jours = sorted(set(par_jour_actif) & set(par_jour_indice))
    if len(jours) < RELATIVE_STRENGTH_HORIZON + 1:
        return {
            "status": REASON_INSUFFICIENT_SAMPLE,
            "benchmark": benchmark,
            "horizon": RELATIVE_STRENGTH_HORIZON,
            "common_sessions": len(jours),
            "detail": (
                f"{RELATIVE_STRENGTH_HORIZON + 1} séances communes requises ; "
                f"{len(jours)} partagées avec {benchmark}"
            ),
        }

    fenetre = jours[-(RELATIVE_STRENGTH_HORIZON + 1) :]
    rendements_actif = [
        float(par_jour_actif[fenetre[i]] / par_jour_actif[fenetre[i - 1]] - 1)
        for i in range(1, len(fenetre))
    ]
    rendements_indice = [
        float(par_jour_indice[fenetre[i]] / par_jour_indice[fenetre[i - 1]] - 1)
        for i in range(1, len(fenetre))
    ]

    debut = now
    try:
        valeur = relative_strength(
            rendements_actif, rendements_indice, RELATIVE_STRENGTH_HORIZON
        )
    except CalculationInputError as erreur:
        return {
            "status": "REFUSED",
            "benchmark": benchmark,
            "horizon": RELATIVE_STRENGTH_HORIZON,
            "reason": erreur.reason,
            "detail": erreur.detail,
        }

    enregistrement = make_calculation_record(
        calculation_id="market.relative_strength",
        calculation_type="market_statistic",
        code_sha=f"module:vertex_core.calculations.market@{ENGINE_VERSION}",
        method="compounded asset return divided by compounded benchmark return",
        inputs={
            "sessions": fenetre,
            "benchmark": benchmark,
            "horizon": RELATIVE_STRENGTH_HORIZON,
        },
        result={"value": _num_string(valeur)},
        started_at=debut,
        completed_at=now,
    )
    return {
        "status": "OK",
        "benchmark": benchmark,
        "horizon": RELATIVE_STRENGTH_HORIZON,
        "common_sessions": len(jours),
        "unit": "ratio",
        "value": _num_string(valeur),
        "calculation": _calculation_meta(enregistrement),
    }


def _rebased_comparison_block(
    valid_bars: Sequence[Mapping[str, Any]],
    benchmark_series: SerieAdmise | None,
    *,
    instrument: str,
    benchmark: str | None,
    currency: str | None,
    adjustment_basis: str | None,
    now: datetime,
    benchmark_rejected: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    """Comparaison base 100 SERVIE contre l'indice DECLARE.

    `market.rebased_series` etait APPROUVE au registre et n'avait aucun
    appelant : la page Graphiques ne pouvait comparer deux series qu'en les
    rebasant dans le navigateur, c'est-a-dire en calculant une performance en
    TypeScript — ce que `.claude/rules/frontend.md` interdit. Le rebasage ET
    l'alignement des calendriers se font donc ICI.

    Alignement, jamais troncature : deux places n'ont pas les memes feries, on
    intersecte les jours de bourse et on publie leur compte. Chaque point rendu
    porte SON jour et les DEUX valeurs de ce jour — la page ne peut donc pas
    apparier deux listes de longueurs differentes, la structure l'interdit.

    Refus NOMMES, jamais une serie tronquee en silence : aucun indice declare,
    instrument egal a l'indice, indice non observe (avec le motif de rejet
    quand il a ete collecte puis refuse), seances communes insuffisantes,
    devise ou base d'ajustement divergente.
    """
    from vertex_core.calculations.market import CalculationInputError, rebase_series

    if benchmark is None:
        return {"status": REASON_NO_BENCHMARK, "detail": "aucun indice de référence déclaré"}
    if benchmark == instrument:
        return {
            "status": REASON_IS_BENCHMARK,
            "benchmark": benchmark,
            "detail": "un instrument ne se compare pas à lui-même",
        }
    if benchmark_series is None:
        bloc_absent: dict[str, Any] = {
            "status": REASON_BENCHMARK_ABSENT,
            "benchmark": benchmark,
            "detail": f"aucune série exploitable admise pour {benchmark}",
        }
        if benchmark_rejected:
            bloc_absent["rejected_records"] = [dict(rejet) for rejet in benchmark_rejected]
        return bloc_absent

    if currency is None or adjustment_basis is None:
        # Aucun enregistrement de barres n'a ete ADMIS pour l'instrument : il
        # n'a ni devise ni base d'ajustement publiees, donc aucune seance a
        # partager. Emprunter celles de l'indice fabriquerait exactement
        # l'etiquette que la porte ci-dessous protege.
        return {
            "status": REASON_INSUFFICIENT_SAMPLE,
            "benchmark": benchmark,
            "minimum_sessions": REBASED_COMPARISON_MIN_SESSIONS,
            "common_sessions": 0,
            "detail": (
                f"aucune série admise pour {instrument} : 0 séance partagée "
                f"avec {benchmark}"
            ),
        }

    # Unites : deux series ne se superposent que si elles sont libellees dans
    # la meme monnaie et sur la meme base d'ajustement. Sinon la base 100
    # afficherait une derive de change ou un detachement de dividende comme
    # une surperformance, et rien a l'ecran ne le dirait.
    if currency != benchmark_series.currency:
        return {
            "status": REASON_BENCHMARK_CURRENCY_MISMATCH,
            "benchmark": benchmark,
            "currency": currency,
            "benchmark_currency": benchmark_series.currency,
            "detail": (
                f"{instrument} est libellé en {currency} et {benchmark} en "
                f"{benchmark_series.currency} : une base 100 muette sur la devise "
                "afficherait la dérive de change comme une performance"
            ),
        }
    if adjustment_basis != benchmark_series.adjustment_basis:
        return {
            "status": REASON_BENCHMARK_BASIS_MISMATCH,
            "benchmark": benchmark,
            "adjustment_basis": adjustment_basis,
            "benchmark_adjustment_basis": benchmark_series.adjustment_basis,
            "detail": (
                f"{instrument} est sur la base {adjustment_basis} et {benchmark} sur "
                f"{benchmark_series.adjustment_basis} : l'écart affiché serait FAUX"
            ),
        }

    par_jour_actif = {bar["trading_day"]: bar["close"] for bar in valid_bars}
    par_jour_indice = {bar["trading_day"]: bar["close"] for bar in benchmark_series.bars}
    jours = sorted(set(par_jour_actif) & set(par_jour_indice))
    if len(jours) < REBASED_COMPARISON_MIN_SESSIONS:
        return {
            "status": REASON_INSUFFICIENT_SAMPLE,
            "benchmark": benchmark,
            "minimum_sessions": REBASED_COMPARISON_MIN_SESSIONS,
            "common_sessions": len(jours),
            "detail": (
                f"{REBASED_COMPARISON_MIN_SESSIONS} séances communes requises ; "
                f"{len(jours)} partagée(s) avec {benchmark}"
            ),
        }

    prix_actif = [par_jour_actif[jour] for jour in jours]
    prix_indice = [par_jour_indice[jour] for jour in jours]
    bases_actif = [adjustment_basis] * len(jours)
    bases_indice = [benchmark_series.adjustment_basis] * len(jours)

    debut = now
    try:
        rebase_actif = rebase_series(
            [Decimal(prix) for prix in prix_actif],
            adjustment_bases=bases_actif,
            base_value=REBASE_BASE_VALUE,
        )
        rebase_indice = rebase_series(
            [Decimal(prix) for prix in prix_indice],
            adjustment_bases=bases_indice,
            base_value=REBASE_BASE_VALUE,
        )
    except CalculationInputError as erreur:
        return {
            "status": "REFUSED",
            "benchmark": benchmark,
            "common_sessions": len(jours),
            "reason": erreur.reason,
            "detail": erreur.detail,
        }

    base_publiee = format(REBASE_BASE_VALUE, "f")
    methode = "base_value * p_i / p_0 sur les seules séances communes aux deux séries"
    code_sha = f"module:vertex_core.calculations.market@{ENGINE_VERSION}"
    valeurs_actif = [_num_string(valeur) for valeur in rebase_actif]
    valeurs_indice = [_num_string(valeur) for valeur in rebase_indice]

    enregistrement_actif = make_calculation_record(
        calculation_id="market.rebased_series",
        calculation_type="market_statistic",
        code_sha=code_sha,
        method=methode,
        inputs={
            "sessions": jours,
            "prices": prix_actif,
            "adjustment_bases": bases_actif,
            "base_value": base_publiee,
        },
        result={"series": valeurs_actif},
        started_at=debut,
        completed_at=now,
    )
    enregistrement_indice = make_calculation_record(
        calculation_id="market.rebased_series",
        calculation_type="market_statistic",
        code_sha=code_sha,
        method=methode,
        inputs={
            "sessions": jours,
            "prices": prix_indice,
            "adjustment_bases": bases_indice,
            "base_value": base_publiee,
        },
        result={"series": valeurs_indice},
        started_at=debut,
        completed_at=now,
    )

    return {
        "status": "OK",
        "benchmark": benchmark,
        "unit": "index",
        "base_value": base_publiee,
        "currency": currency,
        "adjustment_basis": adjustment_basis,
        "common_sessions": len(jours),
        "first_trading_day": jours[0],
        "last_trading_day": jours[-1],
        # Un point = un jour ET ses deux valeurs. Publier deux listes
        # paralleles laisserait la page les apparier, donc les desaligner.
        "series": [
            {
                "trading_day": jour,
                "instrument": valeurs_actif[index],
                "benchmark": valeurs_indice[index],
            }
            for index, jour in enumerate(jours)
        ],
        "calculation": _calculation_meta(enregistrement_actif),
        "benchmark_calculation": _calculation_meta(enregistrement_indice),
    }


def _build_evidence(
    evidence_records: Sequence[ObservationRecord],
    *,
    instrument: str,
    config: AnalysisConfig,
) -> dict[str, Any]:
    """Short evidence rail from the deterministic fusion of the ticker's
    content observations (title-carrying observations mentioning the
    instrument). Dedup only — no relevance invention here."""
    from vertex_core.fusion import ContentObservation
    from vertex_worker.handlers import (  # local import: cycle avoidance
        DEFAULT_SOURCE_TIER,
        is_synthetic_record,
    )

    observations = []
    record_by_id: dict[str, Any] = {}
    for record in evidence_records:
        payload = record.payload if isinstance(record.payload, Mapping) else {}
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        raw_entities = payload.get("entities")
        entities = (
            tuple(e for e in raw_entities if isinstance(e, str) and e.strip())
            if isinstance(raw_entities, (list, tuple))
            else ()
        )
        if instrument not in entities and record.instrument_ref != instrument:
            continue
        url = payload.get("canonical_url")
        observations.append(
            ContentObservation(
                content_id=record.event_id,
                source=record.source,
                source_tier=DEFAULT_SOURCE_TIER,
                native_id=record.source_event_id,
                canonical_url=url if isinstance(url, str) and url else None,
                title=title,
                entities=entities or (instrument,),
                published_at=record.published_at,
                received_at=record.received_at,
                rights=record.rights,
                quality=EnvelopeQuality(record.quality_status),
                is_deleted=False,
            )
        )
        record_by_id[record.event_id] = record

    fusion = fuse(observations)
    observation_by_id = {obs.content_id: obs for obs in fusion.observations}
    clusters = sorted(
        fusion.clusters,
        key=lambda cluster: (cluster.last_received_at, cluster.cluster_id),
        reverse=True,
    )
    entries: list[dict[str, Any]] = []
    for cluster in clusters[: config.max_evidence]:
        representative = observation_by_id[min(cluster.member_ids)]
        entries.append(
            {
                "cluster_id": cluster.cluster_id,
                "title": representative.title,
                "sources": list(cluster.sources),
                "rights": list(cluster.rights),
                "member_count": len(cluster.member_ids),
                "member_event_ids": list(cluster.member_ids),
                "last_received_at": cluster.last_received_at.isoformat(),
                "synthetic": any(
                    is_synthetic_record(record_by_id[member]) for member in cluster.member_ids
                ),
            }
        )
    return {
        "source": "fusion",
        "ruleset_version": fusion.ruleset_version,
        "considered": len(observations),
        "clusters_total": len(fusion.clusters),
        "clusters": entries,
    }


def _pick_healthy_contract(
    chain_content: Mapping[str, Any],
) -> dict[str, Any] | None:
    """First contract with a sane quote AND a resolved Vertex IV, plus its
    group context. CALL contracts are preferred (simple long-call scenario);
    a healthy PUT is used only when no CALL qualifies."""
    fallback: dict[str, Any] | None = None
    expirations = chain_content.get("expirations")
    if not isinstance(expirations, list):
        return None
    spot = chain_content.get("spot")
    assumptions = chain_content.get("assumptions")
    if not isinstance(spot, Mapping) or not isinstance(assumptions, Mapping):
        return None
    for group in expirations:
        if not isinstance(group, Mapping):
            continue
        contracts = group.get("contracts")
        if not isinstance(contracts, list):
            continue
        for entry in contracts:
            if not isinstance(entry, Mapping):
                continue
            quote = entry.get("quote")
            iv = entry.get("iv")
            if not isinstance(quote, Mapping) or not isinstance(iv, Mapping):
                continue
            if quote.get("status") != "OK" or iv.get("status") != "OK":
                continue
            ask = _decimal_or_none(quote.get("ask"))
            strike = _decimal_or_none(entry.get("strike"))
            iv_value = _decimal_or_none(iv.get("value"))
            spot_value = _decimal_or_none(spot.get("value"))
            rate = _decimal_or_none(assumptions.get("rate"))
            dividend_yield = _decimal_or_none(assumptions.get("dividend_yield"))
            maturity = _decimal_or_none(group.get("maturity_years"))
            multiplier = entry.get("multiplier")
            if None in (ask, strike, iv_value, spot_value, rate, dividend_yield, maturity):
                continue
            if not isinstance(multiplier, int) or multiplier <= 0:
                continue
            # `None in (...)` ci-dessus refuse déjà l'absence, mais ne
            # restreint aucun des noms testés.
            assert ask is not None and maturity is not None  # noqa: S101
            if ask <= 0 or maturity <= 0:
                continue
            candidate = {
                "entry": entry,
                "group": group,
                "ask": ask,
                "strike": strike,
                "iv": iv_value,
                "spot": spot_value,
                "rate": rate,
                "dividend_yield": dividend_yield,
                "maturity_years": maturity,
                "multiplier": multiplier,
            }
            if entry.get("right") == "CALL":
                return candidate
            if fallback is None and entry.get("right") == "PUT":
                fallback = candidate
    return fallback


def _build_scenarios(
    chain_content: Mapping[str, Any] | None,
    *,
    chain_version: int | None,
    now: datetime,
) -> dict[str, Any]:
    """Scenario block: ``scenario_grid`` on ONE healthy long option leg, or
    an honest ABSENT block with the typed reason."""
    if chain_content is None:
        return {"status": "ABSENT", "reason": REASON_NO_OPTION_CHAIN}
    picked = _pick_healthy_contract(chain_content)
    if picked is None:
        return {"status": "ABSENT", "reason": REASON_NO_HEALTHY_CONTRACT}

    entry = picked["entry"]
    leg = OptionLeg(
        quantity=1,
        right=entry["right"],
        strike=picked["strike"],
        premium=picked["ask"],  # hypothetical buy of one leg: the observed ask
        multiplier=picked["multiplier"],
    )
    spot_points = [(picked["spot"] * shock).quantize(_CENTS) for shock in _SPOT_SHOCKS]
    maturity = float(picked["maturity_years"])
    time_points = (maturity, maturity / 2.0, 0.0)
    iv_value = float(picked["iv"])
    try:
        grid = scenario_grid(
            (leg,),
            tuple(spot_points),
            time_points,
            ((iv_value,),),
            picked["rate"],
            picked["dividend_yield"],
        )
    except OptionInputError as exc:
        return {"status": "ABSENT", "reason": exc.reason}

    record = make_calculation_record(
        calculation_id="options.scenario_grid",
        calculation_type="options",
        code_sha=_CODE_SHA,
        method="BSM repricing grid, single long leg, IV unchanged scenario",
        inputs={
            "leg": leg.model_dump(),
            "spot_grid": spot_points,
            "time_grid_years": [repr(t) for t in time_points],
            "iv_scenarios": [[repr(iv_value)]],
            "rate": picked["rate"],
            "dividend_yield": picked["dividend_yield"],
        },
        result=grid,
        started_at=now,
        completed_at=now,
        assumptions=(
            "premium side ASK (hypothetical buy of one long leg)",
            "single scenario: implied volatility unchanged",
            "P&L before declared costs (scenario_grid contract)",
        ),
    )
    return {
        "status": "OK",
        "value_nature": VALUE_NATURE_THEORETICAL,
        "basis": {
            "con_id": entry.get("con_id"),
            "right": entry.get("right"),
            "strike": entry.get("strike"),
            "expiration": entry.get("expiration"),
            "trading_class": entry.get("trading_class"),
            "multiplier": picked["multiplier"],
            "currency": entry.get("currency"),
            "premium": format(picked["ask"], "f"),
            "premium_side": "ASK",
            "iv": format(picked["iv"], "f"),
            "chain_snapshot_version": chain_version,
        },
        "spot_grid": [format(point, "f") for point in spot_points],
        "time_grid_years": [_num_string(point) for point in time_points],
        "iv_scenarios": [[_num_string(iv_value)]],
        "grid": [[[_num_string(cell) for cell in row] for row in scenario] for scenario in grid],
        "calculation": _calculation_meta(record),
    }


def build_analysis_content(
    bar_records: Sequence[BarRecord],
    *,
    instrument: str,
    evidence_records: Sequence[ObservationRecord],
    option_chain_content: Mapping[str, Any] | None,
    option_chain_version: int | None,
    now: datetime,
    config: AnalysisConfig,
    engine: AdviceEngine | None = None,
) -> dict[str, Any]:
    """Build the ``analysis/{instrument}`` snapshot content (pure).

    Identical inputs produce an identical dict. Every considered bar record
    is used or rejected with a reason, every invalid bar is discarded with a
    reason, and the verdict is whatever THE ``AdviceEngine`` returns on the
    honestly assembled inputs — never forced, never softened.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    if instrument not in config.instruments:
        raise ValueError(f"instrument {instrument!r} is not declared")
    engine = engine if engine is not None else AdviceEngine()

    # -- pick the latest usable bars record for this instrument --------------
    rejected_records: list[dict[str, str]] = []
    chosen: BarRecord | None = None
    considered = 0
    for record in sorted(bar_records, key=lambda r: (r.as_of, r.event_id)):
        payload = record.payload if isinstance(record.payload, Mapping) else {}
        if payload.get("ticker") != instrument:
            continue
        considered += 1
        if record.source not in config.allowed_sources:
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_SOURCE_NOT_ALLOWED}
            )
            continue
        if record.rights not in config.usable_rights:
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_RIGHTS_NOT_USABLE}
            )
            continue
        if not isinstance(payload.get("bars"), list):
            rejected_records.append({"event_id": record.event_id, "reason": REASON_INVALID_PAYLOAD})
            continue
        # Record-level source-controlled fields relayed into the dossier:
        # admitted ONLY on their declared shape, never repaired.
        if _currency_or_none(payload.get("currency")) is None:
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_INVALID_CURRENCY}
            )
            continue
        if _basis_code_or_none(payload.get("adjustment_basis")) is None:
            rejected_records.append(
                {
                    "event_id": record.event_id,
                    "reason": REASON_INVALID_ADJUSTMENT_BASIS,
                }
            )
            continue
        chosen = record  # ascending order: the latest usable record wins

    # -- bars block (verbatim, fail-closed per bar) ---------------------------
    valid_bars: list[dict[str, Any]] = []
    discarded_bars: list[dict[str, Any]] = []
    synthetic = False
    bars_fresh = False
    bars_age_seconds: int | None = None
    if chosen is not None:
        synthetic = _is_synthetic_bar(chosen)
        bars_age = now - chosen.as_of
        bars_age_seconds = int(bars_age.total_seconds())
        # Une observation datée dans le futur n'est jamais « fraîche » :
        # elle signale une incohérence d'horloge et ferme la gate comme stale.
        bars_fresh = timedelta(0) <= bars_age <= config.bars_freshness
        for index, raw in enumerate(chosen.payload["bars"]):
            bar, reason = _validate_bar(raw)
            if bar is None:
                discarded_bars.append({"index": index, "reason": reason})
            else:
                valid_bars.append(bar)
        valid_bars.sort(key=lambda bar: bar["trading_day"])
    last_close = valid_bars[-1]["close"] if valid_bars else None
    payload = chosen.payload if chosen is not None else {}
    bars_block: dict[str, Any] = {
        "status": "OK" if valid_bars else "ABSENT",
        "count": len(valid_bars),
        # Both were admitted on their shape above: relayed as admitted.
        "currency": (_currency_or_none(payload.get("currency")) if chosen is not None else None),
        "adjustment_basis": (
            _basis_code_or_none(payload.get("adjustment_basis")) if chosen is not None else None
        ),
        "first_trading_day": valid_bars[0]["trading_day"] if valid_bars else None,
        "last_trading_day": valid_bars[-1]["trading_day"] if valid_bars else None,
        "last_close": last_close,
        "quality": chosen.quality_status if chosen is not None else None,
        "fresh": bars_fresh if chosen is not None else None,
        "age_seconds": bars_age_seconds,
        "source_event_id": chosen.event_id if chosen is not None else None,
        "observed_as_of": chosen.as_of.isoformat() if chosen is not None else None,
        "discarded": discarded_bars,
        "bars": valid_bars,
    }

    # -- indicateurs techniques ----------------------------------------------
    # Calculs DEJA approuves au registre et jamais appeles jusqu'ici. Ils ne
    # publient qu'une valeur et sa tracabilite : aucune interpretation, aucun
    # seuil, aucun regime.
    indicators = _build_indicators(
        valid_bars,
        now=now,
        source_event_id=chosen.event_id if chosen is not None else None,
    )
    # Force relative et comparaison base 100 contre l'indice DECLARE par la
    # configuration. Ses barres sortent du meme chargement, et passent la MEME
    # porte d'admission que l'instrument : aucune requete supplementaire,
    # aucune serie que l'instrument n'aurait pas eu le droit d'utiliser.
    serie_indice, indice_rejets = (
        _barres_de(bar_records, config.benchmark, config=config)
        if config.benchmark
        else (None, ())
    )
    indicators["relative_strength"] = _relative_strength_block(
        valid_bars,
        None if serie_indice is None else list(serie_indice.bars),
        instrument=instrument,
        benchmark=config.benchmark,
        now=now,
    )
    indicators["rebased_comparison"] = _rebased_comparison_block(
        valid_bars,
        serie_indice,
        instrument=instrument,
        benchmark=config.benchmark,
        currency=bars_block["currency"],
        adjustment_basis=bars_block["adjustment_basis"],
        benchmark_rejected=indice_rejets,
        now=now,
    )

    # -- evidence and scenarios ----------------------------------------------
    evidence = _build_evidence(evidence_records, instrument=instrument, config=config)
    scenarios = _build_scenarios(option_chain_content, chain_version=option_chain_version, now=now)
    if any(entry["synthetic"] for entry in evidence["clusters"]):
        synthetic = True

    # -- honest AdviceInputs -> the single AdviceEngine -----------------------
    if chosen is None or not valid_bars:
        snapshot_quality = SnapshotQuality.MISSING
    elif discarded_bars or chosen.quality_status != "VALID":
        snapshot_quality = SnapshotQuality.PARTIAL
    else:
        snapshot_quality = SnapshotQuality.GOOD

    calculation_statuses: dict[str, CalculationStatus] = {}
    if scenarios["status"] == "OK":
        calculation_statuses["options.scenario_grid"] = CalculationStatus.OK

    # Population is derived BEFORE the AdviceInputs so every sentence inside
    # AdviceResult uses the same truth as the top-level dossier field.  A
    # rejected record retains nothing and therefore cannot turn EMPTY into
    # REAL; one retained synthetic component conservatively labels the whole
    # population SYNTHETIC.
    retained = bool(valid_bars) or bool(evidence["clusters"])
    if not retained:
        population = "EMPTY"
    elif synthetic:
        population = "SYNTHETIC"
    else:
        population = "REAL"

    explanation_facts: list[str] = []
    if valid_bars:
        # The bars keep their own nature even when a synthetic evidence
        # cluster makes the aggregate population SYNTHETIC.
        assert chosen is not None  # noqa: S101 (valid_bars implies a chosen record)
        bars_population = "SYNTHETIC" if _is_synthetic_bar(chosen) else "REAL"
        explanation_facts.append(
            f"{len(valid_bars)} {bars_population} daily bars from "
            f"{bars_block['first_trading_day']} to {bars_block['last_trading_day']}"
        )
        explanation_facts.append(
            f"last {bars_population} close {last_close} {bars_block['currency']}"
        )
    if evidence["clusters"]:
        explanation_facts.append(f"{len(evidence['clusters'])} evidence cluster(s) from fusion")

    if population == "SYNTHETIC":
        risk_summary = (
            "SYNTHETIC development population retained; no authoritative "
            "market risk assessment exists for this instrument"
        )
    elif population == "REAL":
        risk_summary = (
            "REAL observation population retained; no authoritative market "
            "risk assessment exists for this instrument"
        )
    else:
        risk_summary = (
            "EMPTY population; no observation was retained and no authoritative "
            "market risk assessment exists for this instrument"
        )

    inputs = AdviceInputs(
        instrument_id=instrument,
        as_of=now,
        valid_until=now + config.advice_validity,
        input_snapshot_id=(
            chosen.event_id if chosen is not None else f"analysis:{instrument}:none"
        ),
        horizon=config.horizon,
        # No upstream analytical reading exists for this dossier population:
        # the direction is honestly UNKNOWN, never inferred here.
        direction=Direction.UNKNOWN,
        risk_summary=risk_summary,
        evidence_ids=tuple(entry["cluster_id"] for entry in evidence["clusters"]),
        scenario_ids=(
            (scenarios["calculation"]["input_hash"],) if scenarios["status"] == "OK" else ()
        ),
        explanation_facts=tuple(explanation_facts),
        limitations=("SYNTHETIC development population",) if synthetic else (),
        instrument=InstrumentResolutionInput(
            identity_status=IdentityStatus.RESOLVED,
            # Synthetic instruments have no IBKR con_id confirmation: the
            # honest fact makes gate 1 DEGRADE (RESOLVED_WITHOUT_CONID).
            resolved_with_conid=False,
        ),
        # entitlements / session_event / liquidity / contradictions /
        # constraints: nobody holds these facts for this dossier population,
        # so they stay absent and their gates BLOCK UNEVALUABLE (fail-closed;
        # the resulting INSUFFICIENT_DATA is the WANTED honest verdict).
        snapshot=SnapshotInput(quality=snapshot_quality, fresh=bars_fresh),
        calculations=CalculationsInput(calculation_statuses=calculation_statuses or None),
        # Declared by the caller's configuration, never by this builder: when
        # the required flag is set and no user declaration exists, gate 7
        # BLOCKS (fail-closed) instead of passing NOT_REQUIRED.
        portfolio_risk=PortfolioRiskInput(risk_required=config.portfolio_risk_required),
        probability=ProbabilityInput(probability_used=False),
    )
    advice = engine.evaluate(inputs)

    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "instrument": instrument,
        "engine_version": ENGINE_VERSION,
        "bars": bars_block,
        "indicators": indicators,
        "evidence": evidence,
        "scenarios": scenarios,
        "advice": advice.model_dump(mode="json"),
        "coverage": {
            "observations_considered": considered,
            "rejected_records": rejected_records,
            "lookback_seconds": int(config.lookback.total_seconds()),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class AnalysisHandler:
    """Handler of ``analysis.ingested``: recompute per-instrument dossiers."""

    def __init__(self, *, config: AnalysisConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock
        self._engine = AdviceEngine()

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local imports avoid a module cycle (handlers imports ingest,
        # ingest imports this module).
        from vertex_worker.handlers import (
            load_recent_observation_records,
            publish_if_changed,
        )
        from vertex_worker.options import SNAPSHOT_KIND_OPTION_CHAIN

        now = self._clock()
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("clock returned a naive datetime; aware UTC required")
        bar_records = load_daily_bar_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )
        seen = {
            record.payload.get("ticker")
            for record in bar_records
            if isinstance(record.payload, Mapping)
        }
        for instrument in self._config.instruments:
            if instrument not in seen:
                # Absence stays absent: no invented dossier, the API answers
                # its honest empty state until bars actually exist.
                continue
            chain = get_current_snapshot(session, kind=SNAPSHOT_KIND_OPTION_CHAIN, key=instrument)
            # Preuves cadrées sur l'instrument : demander la fenêtre globale
            # puis filtrer affamait chaque dossier dès que d'autres
            # instruments étaient collectés après lui. Mesuré le 2026-09-01 :
            # 0 dépêche GOOG dans les 500 plus récentes, alors que 140
            # existaient en base.
            evidence_records = load_recent_observation_records(
                session,
                now=now,
                lookback=self._config.lookback,
                limit=self._config.max_observations,
                instrument_ref=_instrument_ref_de(bar_records, instrument),
            )
            content = build_analysis_content(
                bar_records,
                instrument=instrument,
                evidence_records=evidence_records,
                option_chain_content=None if chain is None else chain.content,
                option_chain_version=None if chain is None else chain.version,
                now=now,
                config=self._config,
                engine=self._engine,
            )
            published = publish_if_changed(
                session,
                kind=SNAPSHOT_KIND_ANALYSIS,
                key=instrument,
                content=content,
                as_of=now,
            )
            if published is None:
                log.info("analysis %s unchanged (message_id=%s)", instrument, message.id)
            else:
                log.info(
                    "analysis %s published version=%s (message_id=%s)",
                    instrument,
                    published.version,
                    message.id,
                )


def register_analysis_handler(
    registry: HandlerRegistry, *, clock: Clock, config: AnalysisConfig
) -> None:
    """Register the analysis handler on ``analysis.ingested``."""
    registry.register(TOPIC_ANALYSIS_INGESTED, AnalysisHandler(config=config, clock=clock))
