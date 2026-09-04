"""Performance calculations: time-weighted return, XIRR (money-weighted), drawdown.

Implements the calculation registry entries ``performance.twr``,
``performance.xirr`` and ``performance.drawdown``.

Population rule
---------------
Each call measures exactly ONE population: one real declared portfolio OR one
hypothetical scenario, never a mix. The caller owns the population label;
mixing cannot be expressed through these signatures.

Numeric policy
--------------
``twr`` and ``drawdown`` stay in ``Decimal`` inside a pinned
``DECIMAL_PRECISION``-digit context (28, ``ROUND_HALF_EVEN``); ratios from
division are correct to 28 significant digits and the documented comparison
tolerance is ``1e-20`` relative. ``xirr`` uses the documented float64
numerical core: ``Decimal`` amounts are converted to float64 (relative
representation error <= 2**-52) and the NPV root is refined with
``scipy.optimize.brentq`` (``xtol=1e-12``); a root is accepted only if
``|NPV(root)| <= XIRR_NPV_TOLERANCE_SCALE * sum(|cashflow|)``.

Fail-closed rules
-----------------
Structurally invalid input raises a typed
:class:`PerformanceCalculationError` subclass. The one analytically
undecidable case — an NPV root that cannot be bracketed, or is not unique on
the documented search grid — returns an explicit ``CalculationStatus.INVALID``
result with a reason, never a fabricated number.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal, localcontext
from functools import reduce
from operator import mul
from typing import Annotated, Any

from pydantic import AfterValidator, Field, model_validator
from scipy.optimize import brentq

from vertex_core.contracts.enums import CalculationStatus
from vertex_core.contracts.types import (
    ContractModel,
    FiniteDecimal,
    NonEmptyStr,
    NonNegativeDecimal,
    UtcDatetime,
)

__all__ = [
    "DAYS_PER_YEAR",
    "DECIMAL_PRECISION",
    "XIRR_BRACKET_GRID",
    "XIRR_NPV_TOLERANCE_SCALE",
    "CashflowBoundaryError",
    "CashflowEvent",
    "DrawdownResult",
    "PerformanceCalculationError",
    "SignChangeError",
    "TwrResult",
    "Valuation",
    "XirrResult",
    "drawdown",
    "twr",
    "xirr",
]

DECIMAL_PRECISION = 28
"""Pinned significant digits for the Decimal computations (twr, drawdown)."""

DAYS_PER_YEAR = 365.0
"""ACT/365F: year fractions in xirr are elapsed seconds / (365 * 86400)."""

XIRR_NPV_TOLERANCE_SCALE = 1e-9
"""Accepted |NPV(root)| as a fraction of the summed absolute cashflows."""

XIRR_BRACKET_GRID: tuple[float, ...] = (
    -0.999999,
    -0.9999,
    -0.999,
    -0.99,
    -0.95,
    -0.9,
    -0.8,
    -0.6,
    -0.4,
    -0.2,
    -0.1,
    -0.05,
    0.0,
    0.05,
    0.1,
    0.2,
    0.4,
    0.7,
    1.0,
    2.0,
    5.0,
    10.0,
    25.0,
    100.0,
    1000.0,
)
"""Documented deterministic rate grid used to LOCATE the NPV root.

Elle ne prouve rien : deux racines logées entre deux points consécutifs n'y
changent aucun signe. L'unicité est établie AVANT, par la règle des signes de
Descartes sur les montants ordonnés dans le temps (LOT 2 bis). Cette grille
n'est employée que lorsque l'unicité est déjà démontrée ; zéro ou plusieurs
encadrements donnent alors un résultat INVALID.
"""

_ZERO = Decimal("0")
_ONE = Decimal("1")


class PerformanceCalculationError(ValueError):
    """Base typed error for every invalid performance-calculation input (fail-closed)."""


class CashflowBoundaryError(PerformanceCalculationError):
    """An external cashflow has no valuation at its exact timestamp (incomplete boundaries)."""


class SignChangeError(PerformanceCalculationError):
    """XIRR requires at least one strictly positive and one strictly negative cashflow."""


def _ensure_finite_float(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(
            "non-finite float rejected: NaN and infinities are not valid contract values"
        )
    return value


FiniteFloat = Annotated[float, AfterValidator(_ensure_finite_float)]
"""Float64 result value with NaN/infinity rejected at the DTO boundary."""


class Valuation(ContractModel):
    """Portfolio value of the single population at one instant, in its currency.

    ``value`` is a non-negative ``Decimal``; the currency and the population
    label are fixed per call by the caller (one population, one currency).
    """

    at: UtcDatetime
    value: NonNegativeDecimal


class CashflowEvent(ContractModel):
    """One dated external cashflow of the population.

    Sign convention: positive = contribution INTO the portfolio, negative =
    withdrawal. Zero-amount events are legal and change nothing.
    """

    at: UtcDatetime
    amount: FiniteDecimal


class TwrResult(ContractModel):
    """Chain-linked time-weighted return with its per-period sub-returns."""

    total_return: FiniteDecimal
    period_returns: tuple[FiniteDecimal, ...] = Field(min_length=1)


class XirrResult(ContractModel):
    """XIRR outcome: an OK root with its residual NPV, or an explicit INVALID.

    ``rate`` is the annualized internal rate (ACT/365F, float64 core).
    ``status`` is restricted to ``OK`` and ``INVALID``; an INVALID result
    carries a reason and no number — never a fabricated rate.
    """

    status: CalculationStatus
    rate: FiniteFloat | None = None
    npv_at_rate: FiniteFloat | None = None
    reason: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _check_status_shape(self) -> XirrResult:
        if self.status is CalculationStatus.OK:
            if self.rate is None or self.npv_at_rate is None:
                raise ValueError("an OK xirr result requires rate and npv_at_rate")
            if self.reason is not None:
                raise ValueError("an OK xirr result must not carry a failure reason")
        elif self.status is CalculationStatus.INVALID:
            if self.rate is not None or self.npv_at_rate is not None:
                raise ValueError("an INVALID xirr result must not carry numbers")
            if self.reason is None:
                raise ValueError("an INVALID xirr result requires an explicit reason")
        else:
            raise ValueError("xirr status must be OK or INVALID")
        return self


class DrawdownResult(ContractModel):
    """Per-point drawdowns (all <= 0) and the maximum drawdown of the curve.

    ``peak_at``/``trough_at`` locate the maximum drawdown; both are ``None``
    when the curve never draws down (``max_drawdown == 0``).
    """

    max_drawdown: FiniteDecimal
    drawdowns: tuple[FiniteDecimal, ...] = Field(min_length=1)
    peak_at: UtcDatetime | None = None
    trough_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _check_non_positive(self) -> DrawdownResult:
        if self.max_drawdown > _ZERO:
            raise ValueError("max_drawdown must be <= 0")
        if any(dd > _ZERO for dd in self.drawdowns):
            raise ValueError("every drawdown must be <= 0")
        if min(self.drawdowns) != self.max_drawdown:
            raise ValueError("max_drawdown must equal the minimum per-point drawdown")
        if (self.peak_at is None) != (self.trough_at is None):
            raise ValueError("peak_at and trough_at must be present together")
        return self


def _as_tuple_of(values: Sequence[object], expected_type: type, name: str) -> tuple[Any, ...]:
    if isinstance(values, (str, bytes)):
        raise PerformanceCalculationError(
            f"{name} must be a sequence of {expected_type.__name__} instances"
        )
    items = tuple(values)
    for item in items:
        if not isinstance(item, expected_type):
            raise PerformanceCalculationError(
                f"{name} must contain only {expected_type.__name__} instances, "
                f"got {type(item).__name__}"
            )
    return items


def _require_strictly_increasing(points: tuple[Any, ...], name: str) -> None:
    for prev, curr in itertools.pairwise(points):
        if curr.at <= prev.at:
            raise PerformanceCalculationError(
                f"{name} must be strictly increasing in time "
                f"({prev.at.isoformat()} then {curr.at.isoformat()})"
            )


def twr(
    valuations: Sequence[Valuation],
    external_cashflows: Sequence[CashflowEvent] = (),
) -> TwrResult:
    """Time-weighted return over dated valuations with external cashflows.

    Registry: ``performance.twr``. Gate ``complete_cashflow_boundaries``:
    every external cashflow must land exactly on a valuation timestamp,
    otherwise :class:`CashflowBoundaryError` — TWR is undefined without the
    portfolio value at each flow boundary. Cashflows are netted per
    timestamp; the absence of a flow at a boundary is a true zero flow (an
    event ledger), not missing data.

    Cashflow timing convention (documented, tested): a flow stamped at ``t``
    arrives immediately AFTER the valuation observed at ``t`` and therefore
    adjusts the capital base of the period STARTING at ``t``. A flow stamped
    at the final valuation starts no period and cannot affect the result.
    Sub-period return: ``r_i = V_i / (V_{i-1} + F_{i-1}) - 1``; the total is
    the chain-linked product minus one.

    Invariant ``cashflow_timing_neutrality`` (tested): external flows change
    capital bases, never the chained return produced by the same per-period
    growth.
    """
    vals = _as_tuple_of(valuations, Valuation, "valuations")
    flows = _as_tuple_of(external_cashflows, CashflowEvent, "external_cashflows")
    if len(vals) < 2:
        raise PerformanceCalculationError("twr requires at least two dated valuations")
    _require_strictly_increasing(vals, "valuations")
    valuation_times = {v.at for v in vals}

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        net_flow: dict[datetime, Decimal] = {}
        for flow in flows:
            if flow.at not in valuation_times:
                raise CashflowBoundaryError(
                    f"external cashflow at {flow.at.isoformat()} has no valuation at that exact "
                    "instant: complete cashflow boundaries are required"
                )
            net_flow[flow.at] = net_flow.get(flow.at, _ZERO) + flow.amount

        growth_factors = []
        for prev, curr in itertools.pairwise(vals):
            start_capital = prev.value + net_flow.get(prev.at, _ZERO)
            if start_capital <= _ZERO:
                raise PerformanceCalculationError(
                    f"non-positive capital base {start_capital} at {prev.at.isoformat()}: "
                    "the sub-period return is undefined"
                )
            growth_factors.append(curr.value / start_capital)

        total_return = reduce(mul, growth_factors) - _ONE
        period_returns = tuple(growth - _ONE for growth in growth_factors)

    return TwrResult(total_return=total_return, period_returns=period_returns)


def xirr(dated_cashflows: Sequence[CashflowEvent]) -> XirrResult:
    """Annualized money-weighted return (XIRR) of one population's cashflows.

    Registry: ``performance.xirr``. Gates:

    - ``sign_change``: at least one strictly positive and one strictly
      negative amount, otherwise :class:`SignChangeError`;
    - all flows at one single instant are rejected (no time dimension);
    - ``unique_valid_root``: uniqueness is PROVEN, not searched. Descartes'
      rule of signs — in its form for real exponents — bounds the number of
      strictly positive roots of ``sum(cf * x**t)`` by the number of sign
      changes of the time-ordered amounts. More than one sign change proves
      nothing, and returns ``INVALID``: several rates may satisfy NPV = 0 and
      the money-weighted return is not uniquely defined. Exactly one sign
      change bounds the roots to one; ``XIRR_BRACKET_GRID`` then only has to
      LOCATE it. No bracket, or several brackets, also returns ``INVALID``
      — never a number.

    Method: ACT/365F year fractions from the earliest flow (fractional days
    kept via seconds); float64 NPV ``sum(cf * (1+r)**-t)``;
    ``scipy.optimize.brentq`` on the single bracket; the root is accepted
    only if ``|NPV(root)| <= XIRR_NPV_TOLERANCE_SCALE * sum(|cf|)``
    (tested). Deterministic: no randomness, fixed grid, fixed tolerances.
    """
    flows = _as_tuple_of(dated_cashflows, CashflowEvent, "dated_cashflows")
    if len(flows) < 2:
        raise PerformanceCalculationError("xirr requires at least two dated cashflows")
    has_positive = any(flow.amount > _ZERO for flow in flows)
    has_negative = any(flow.amount < _ZERO for flow in flows)
    if not (has_positive and has_negative):
        raise SignChangeError(
            "xirr requires at least one strictly positive and one strictly negative cashflow"
        )

    ordered = sorted(flows, key=lambda flow: flow.at)
    t0 = ordered[0].at
    times = [(flow.at - t0).total_seconds() / (86400.0 * DAYS_PER_YEAR) for flow in ordered]
    if times[-1] == 0.0:
        raise PerformanceCalculationError(
            "xirr is undefined when every cashflow shares one instant"
        )
    amounts = [float(flow.amount) for flow in ordered]
    npv_tolerance = XIRR_NPV_TOLERANCE_SCALE * sum(abs(amount) for amount in amounts)

    def npv_or_none(rate: float) -> float | None:
        base = 1.0 + rate
        if base <= 0.0:
            return None
        total = 0.0
        for amount, t in zip(amounts, times, strict=True):
            try:
                total += amount * base ** (-t)
            except OverflowError:
                return None
        if not math.isfinite(total):
            return None
        return total

    def npv_strict(rate: float) -> float:
        value = npv_or_none(rate)
        if value is None:
            raise PerformanceCalculationError(
                f"NPV overflowed during root refinement at rate {rate!r}"
            )
        return value

    # ------------------------------------------------------------------
    # LOT 2 bis — L'UNICITÉ EST PROUVÉE, PLUS SEULEMENT CHERCHÉE.
    #
    # La grille ne peut PAS prouver l'unicité, et le croire était un défaut
    # mesuré : elle teste le signe de la NPV en vingt-cinq points seulement,
    # et deux racines logées dans un même intervalle n'y changent aucun signe.
    # Un flux dont les racines sont 15 %, 45 % et 55 % — les deux dernières
    # dans (0,4 ; 0,7) — présentait UN seul encadrement, et la fonction
    # renvoyait 15,00 % comme LE rendement. Un chiffre faux affiché comme
    # valide.
    #
    # La borne employée ici est la règle des signes de Descartes, dans sa forme
    # généralisée aux exposants réels : le nombre de racines strictement
    # positives de `sum(a_i * x**t_i)`, avec `t_0 < t_1 < ...`, est au plus le
    # nombre de changements de signe de la suite `(a_i)`. La NPV vue en
    # `x = 1/(1+r)` est exactement de cette forme, et `r > -1` équivaut à
    # `x > 0` : la borne s'applique telle quelle, y compris pour des dates
    # fractionnaires, ce qu'une décomposition polynomiale n'aurait pas permis.
    #
    # UN changement de signe borne donc le nombre de racines à une seule :
    # l'unicité est alors DÉMONTRÉE, et un encadrement trouvé la localise.
    # Au-delà, la borne ne prouve plus rien — le nombre de racines vaut le
    # nombre de changements de signe MOINS un multiple de deux, donc trois
    # racines et une seule sont indiscernables sans preuve supplémentaire.
    # Dans ce cas la fonction refuse, au lieu d'affirmer.
    #
    # CE QUE CE REFUS COÛTE, DIT SANS ATTÉNUATION : un portefeuille dont les
    # apports et les retraits alternent produit un flux non conventionnel, et
    # son XIRR devient INVALID au lieu d'un nombre. Ce n'est pas une perte de
    # capacité : c'est la fin d'une capacité qui n'existait pas. Pour un tel
    # flux le rendement pondéré par l'argent n'est pas défini de façon unique,
    # et en afficher une racine parmi plusieurs était l'erreur.
    # ------------------------------------------------------------------
    changements_de_signe = 0
    signe_precedent = 0
    for amount in amounts:
        signe = 1 if amount > 0.0 else -1 if amount < 0.0 else 0
        if signe == 0:
            continue
        if signe_precedent != 0 and signe != signe_precedent:
            changements_de_signe += 1
        signe_precedent = signe
    if changements_de_signe > 1:
        return XirrResult(
            status=CalculationStatus.INVALID,
            reason=(
                "uniqueness of the XIRR root is not proven: the time-ordered cashflow signs "
                f"change {changements_de_signe} times, so Descartes' rule bounds the number of "
                "roots above one and several rates may satisfy NPV = 0"
            ),
        )

    grid_values = [npv_or_none(rate) for rate in XIRR_BRACKET_GRID]
    roots_at_grid = [
        rate
        for rate, value in zip(XIRR_BRACKET_GRID, grid_values, strict=True)
        if value is not None and value == 0.0
    ]
    brackets = []
    for (rate_a, value_a), (rate_b, value_b) in zip(
        zip(XIRR_BRACKET_GRID, grid_values, strict=True),
        zip(XIRR_BRACKET_GRID[1:], grid_values[1:], strict=True),
        strict=False,
    ):
        if value_a is None or value_b is None:
            continue
        if value_a * value_b < 0.0:
            brackets.append((rate_a, rate_b))

    candidate_count = len(roots_at_grid) + len(brackets)
    if candidate_count == 0:
        return XirrResult(
            status=CalculationStatus.INVALID,
            reason="no NPV sign change on the documented search grid: the root cannot be bracketed",
        )
    if candidate_count > 1:
        return XirrResult(
            status=CalculationStatus.INVALID,
            reason=(
                "multiple NPV sign changes on the documented search grid: the root is not unique"
            ),
        )

    if roots_at_grid:
        root = roots_at_grid[0]
    else:
        low, high = brackets[0]
        root = float(brentq(npv_strict, low, high, xtol=1e-12, maxiter=200))
    residual = npv_strict(root)
    if abs(residual) > npv_tolerance:
        return XirrResult(
            status=CalculationStatus.INVALID,
            reason="the refined root does not satisfy the documented |NPV| tolerance",
        )
    return XirrResult(status=CalculationStatus.OK, rate=root, npv_at_rate=residual)


def drawdown(equity_curve: Sequence[Valuation]) -> DrawdownResult:
    """Per-point and maximum drawdown of one ordered, strictly positive curve.

    Registry: ``performance.drawdown``. Gate ``ordered_values``: timestamps
    must be strictly increasing. Every value must be strictly positive (a
    running-maximum ratio is undefined otherwise); this is a fail-closed
    rejection, never a silent skip.

    Per point: ``dd_i = V_i / running_max_i - 1 <= 0`` (Decimal, pinned
    28-digit context). ``max_drawdown = min(dd)`` and is located by
    ``peak_at`` (where the running maximum was set) and ``trough_at`` (first
    instant reaching the maximum drawdown); both are ``None`` for a curve
    that never declines.
    """
    points = _as_tuple_of(equity_curve, Valuation, "equity_curve")
    if not points:
        raise PerformanceCalculationError("drawdown requires at least one valuation")
    _require_strictly_increasing(points, "equity_curve")
    for point in points:
        if point.value <= _ZERO:
            raise PerformanceCalculationError(
                f"equity value {point.value} at {point.at.isoformat()} is not strictly positive: "
                "drawdown is undefined"
            )

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        running_max = points[0].value
        running_max_at = points[0].at
        drawdowns = []
        max_dd: Decimal | None = None
        peak_at = None
        trough_at = None
        for point in points:
            if point.value > running_max:
                running_max = point.value
                running_max_at = point.at
            dd = point.value / running_max - _ONE
            drawdowns.append(dd)
            if max_dd is None or dd < max_dd:
                max_dd = dd
                peak_at = running_max_at
                trough_at = point.at

    # narrowing mypy, garde réelle au-dessus
    assert max_dd is not None  # points is non-empty  # noqa: S101
    if max_dd == _ZERO:
        peak_at = None
        trough_at = None
    return DrawdownResult(
        max_drawdown=max_dd,
        drawdowns=tuple(drawdowns),
        peak_at=peak_at,
        trough_at=trough_at,
    )
