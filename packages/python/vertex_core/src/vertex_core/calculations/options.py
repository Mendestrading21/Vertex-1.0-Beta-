"""Options pricing, sensitivities, payoff and scenario calculations.

Pure, deterministic functions implementing the ``options.*`` entries of
``docs/03-domain/calculations/CALCULATION_REGISTRY.yaml``:

- ``options.forward_price``      -> :func:`forward_price`
- ``options.no_arbitrage_bounds``-> :func:`no_arbitrage_bounds`
- ``options.european_price``     -> :func:`european_price`
- ``options.implied_volatility`` -> :func:`implied_volatility`
- ``options.greeks``             -> :func:`greeks`
- ``options.american_price``     -> :func:`american_price`
- ``options.payoff``             -> :func:`payoff_at_expiry`
- ``options.scenario_grid``      -> :func:`scenario_grid`
- defined-risk certification     -> :func:`defined_risk_check`

Numeric policy (UNITS_TIME_AND_PRECISION):

- Boundary inputs may be ``int``, ``float`` or ``Decimal``; ``Decimal`` values
  are converted explicitly to float64 before analytic computation. ``bool`` is
  rejected (it is not a number at this boundary).
- The analytic core (Black-Scholes-Merton, bounds, Greeks, scenario grids) is
  float64 with documented tolerances ``FLOAT64_REL_TOL`` / ``FLOAT64_ABS_TOL``.
- :func:`payoff_at_expiry` is contractual money arithmetic and therefore runs
  in exact ``Decimal`` arithmetic (no float rounding at breakpoints).
- ``NaN``, infinities and sentinel values are rejected fail-closed with
  :class:`OptionInputError`; negative zero is normalized.
- Absent data stays absent: no default price, curve, volatility or fee is ever
  substituted. Out-of-domain input raises a typed exception, never a silent
  fallback (in particular: never a silent BSM fallback for the American
  engine).
- No randomness is used anywhere in this module.

Model domain (registry gate ``inside_model_domain``, fail-closed):

- ``0 < spot <= 1e12`` and ``0 < strike <= 1e12`` (price units);
- ``0 <= maturity_years <= 100`` (ACT/365-style year fraction);
- ``0 <= volatility <= 10`` (annualized decimal, ``0.25`` = 25%/yr);
- ``-1 <= rate <= 1`` and ``-1 <= dividend_yield <= 1`` (continuously
  compounded annualized decimals; negative rates are inside the domain).

QuantLib (``american_price``) is a hard dependency of the ``quant`` extra and
is imported at module top; SciPy's ``brentq`` is used only for implied
volatility root finding. The closed-form European pricer uses ``math.erf``
only (no SciPy in that path).
"""

from __future__ import annotations

import math
from decimal import Decimal, localcontext
from typing import Literal, Optional, Sequence, Tuple, Union

import QuantLib as _ql
from pydantic import field_validator, model_validator
from scipy.optimize import brentq as _brentq

from vertex_core.contracts.enums import OptionRight
from vertex_core.contracts.types import (
    ContractModel,
    NonNegativeDecimal,
    PositiveDecimal,
    PositiveInt,
)

__all__ = [
    "AMERICAN_MIN_STEPS",
    "DefinedRiskResult",
    "FLOAT64_ABS_TOL",
    "FLOAT64_REL_TOL",
    "GreeksResult",
    "IVNoSolutionError",
    "IV_BRACKET_HI",
    "IV_BRACKET_LO",
    "MATURITY_MAX_YEARS",
    "NumberLike",
    "OptionInputError",
    "OptionLeg",
    "OptionNotImplementedError",
    "RATE_ABS_MAX",
    "SPOT_STRIKE_MAX",
    "VOLATILITY_MAX",
    "QUOTE_SIDES",
    "american_price",
    "defined_risk_check",
    "european_price",
    "forward_price",
    "greeks",
    "implied_volatility",
    "no_arbitrage_bounds",
    "payoff_at_expiry",
    "scenario_grid",
]

FLOAT64_REL_TOL = 1e-9
"""Documented relative tolerance for float64 analytic identities."""

FLOAT64_ABS_TOL = 1e-12
"""Documented absolute tolerance for float64 comparisons near zero."""

SPOT_STRIKE_MAX = 1e12
"""Upper bound of the validated model domain for spot and strike."""

MATURITY_MAX_YEARS = 100.0
"""Upper bound of the validated model domain for maturities (years)."""

VOLATILITY_MAX = 10.0
"""Upper bound of the validated model domain for annualized volatility."""

RATE_ABS_MAX = 1.0
"""Absolute bound for continuously compounded rates and dividend yields."""

IV_BRACKET_LO = 1e-6
"""Lower edge of the explicit implied-volatility root bracket."""

IV_BRACKET_HI = 5.0
"""Upper edge of the explicit implied-volatility root bracket."""

AMERICAN_MIN_STEPS = 50
"""Minimum validated binomial grid size for the American engine."""

QUOTE_SIDES = frozenset({"BID", "ASK", "MID", "LAST", "MODEL"})
"""Closed catalogue of quote-side labels accepted by implied volatility."""

DAYS_PER_YEAR = 365.0
"""Calendar-day convention (ACT/365F) used for theta-per-day and the
American engine's date grid."""

NumberLike = Union[int, float, Decimal]
"""Accepted numeric boundary types; converted explicitly to float64 inside."""

_SQRT2 = math.sqrt(2.0)
_SQRT_2PI = math.sqrt(2.0 * math.pi)

# Fixed, arbitrary anchor date for the QuantLib date grid. Pricing depends
# only on the year fraction between anchor and expiry (flat curves, constant
# vol), so the anchor choice does not influence results; fixing it makes the
# American engine deterministic across processes and wall-clock time.
_QL_ANCHOR_SERIAL = _ql.Date(2, 1, 2026).serialNumber()


class OptionInputError(ValueError):
    """Typed, fail-closed gate violation for an ``options.*`` calculation.

    ``reason`` is a stable machine-readable code naming the violated gate
    (e.g. ``"non_positive_spot"``, ``"volatility_out_of_domain"``);
    ``detail`` is the human-readable explanation. No calculation in this
    module substitutes a default for an invalid input — it raises instead.
    """

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class IVNoSolutionError(OptionInputError):
    """No implied volatility exists inside the verified bracket.

    Raised when the observed price is outside the strict no-arbitrage
    bounds, outside the explicit bracket ``[IV_BRACKET_LO, IV_BRACKET_HI]``,
    or when the root finder fails to converge. Never resolved by clamping.
    """


class OptionNotImplementedError(NotImplementedError):
    """A requested capability is explicitly NOT_IMPLEMENTED.

    Raised (never silently worked around) when a caller requests a
    capability this engine does not support, e.g. discrete dividends for the
    American pricer. There is no BSM or continuous-yield fallback.
    """

    def __init__(self, capability: str, detail: str) -> None:
        super().__init__(f"NOT_IMPLEMENTED {capability}: {detail}")
        self.capability = capability
        self.detail = detail


# ---------------------------------------------------------------------------
# Boundary validation helpers (fail-closed, no defaults)
# ---------------------------------------------------------------------------


def _to_float(value: NumberLike, name: str) -> float:
    """Convert a boundary number to finite float64; reject everything else."""
    if isinstance(value, bool):
        raise OptionInputError(
            "invalid_type", f"{name} must be int, float or Decimal, got bool"
        )
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise OptionInputError(
                "non_finite_input", f"{name} is a non-finite Decimal ({value})"
            )
        result = float(value)
    elif isinstance(value, int):
        try:
            result = float(value)
        except OverflowError:
            raise OptionInputError(
                "non_finite_input", f"{name} is too large for float64"
            ) from None
    elif isinstance(value, float):
        result = value
    else:
        raise OptionInputError(
            "invalid_type",
            f"{name} must be int, float or Decimal, got {type(value).__name__}",
        )
    if not math.isfinite(result):
        raise OptionInputError(
            "non_finite_input", f"{name} is not finite in float64 ({result!r})"
        )
    return 0.0 if result == 0.0 else result


def _require_price_positive(value: NumberLike, name: str) -> float:
    price = _to_float(value, name)
    if price <= 0.0:
        raise OptionInputError(
            f"non_positive_{name}", f"{name} must be strictly positive, got {price!r}"
        )
    if price > SPOT_STRIKE_MAX:
        raise OptionInputError(
            f"{name}_out_of_domain",
            f"{name} {price!r} exceeds the validated model domain "
            f"(0, {SPOT_STRIKE_MAX:g}]",
        )
    return price


def _require_maturity(value: NumberLike, name: str = "maturity_years") -> float:
    t = _to_float(value, name)
    if t < 0.0:
        raise OptionInputError(
            "negative_maturity", f"{name} must be >= 0 years, got {t!r}"
        )
    if t > MATURITY_MAX_YEARS:
        raise OptionInputError(
            "maturity_out_of_domain",
            f"{name} {t!r} exceeds the validated model domain "
            f"[0, {MATURITY_MAX_YEARS:g}] years",
        )
    return t


def _require_volatility(value: NumberLike, name: str = "volatility") -> float:
    vol = _to_float(value, name)
    if vol < 0.0:
        raise OptionInputError(
            "negative_volatility", f"{name} must be >= 0, got {vol!r}"
        )
    if vol > VOLATILITY_MAX:
        raise OptionInputError(
            "volatility_out_of_domain",
            f"{name} {vol!r} exceeds the validated model domain "
            f"[0, {VOLATILITY_MAX:g}]",
        )
    return vol


def _require_rate(value: NumberLike, name: str) -> float:
    rate = _to_float(value, name)
    if rate < -RATE_ABS_MAX or rate > RATE_ABS_MAX:
        raise OptionInputError(
            "rate_out_of_domain",
            f"{name} {rate!r} is outside the validated model domain "
            f"[-{RATE_ABS_MAX:g}, {RATE_ABS_MAX:g}]",
        )
    return rate


def _require_right(right: object) -> str:
    """Normalize ``right`` to the internal 'CALL'/'PUT' string, fail-closed.

    Accepts an :class:`~vertex_core.contracts.enums.OptionRight` member or
    the exact strings ``"CALL"`` / ``"PUT"``. Anything else is rejected.
    """
    if isinstance(right, OptionRight):
        return right.value
    if isinstance(right, str) and right in ("CALL", "PUT"):
        return right
    raise OptionInputError(
        "invalid_right",
        f"right must be OptionRight.CALL/PUT or the string 'CALL'/'PUT', "
        f"got {right!r}",
    )


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OptionInputError(
            "invalid_type", f"{name} must be int, got {type(value).__name__}"
        )
    return value


def _require_sequence(value: object, name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, (list, tuple)
    ):
        raise OptionInputError(
            "invalid_type",
            f"{name} must be a list or tuple, got {type(value).__name__}",
        )
    return value


def _finite_result(value: float, calculation_id: str) -> float:
    if not math.isfinite(value):
        raise OptionInputError(
            "non_finite_result",
            f"{calculation_id} produced a non-finite float64 result ({value!r})",
        )
    return 0.0 if value == 0.0 else value


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via ``math.erf`` (no SciPy in the pricing path)."""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


# ---------------------------------------------------------------------------
# options.forward_price
# ---------------------------------------------------------------------------


def forward_price(
    spot: NumberLike,
    rate: NumberLike,
    dividend_yield: NumberLike,
    maturity_years: NumberLike,
) -> float:
    """``options.forward_price`` — continuous-compounding forward.

    ``F = S * exp((r - q) * T)`` with a flat continuously compounded rate
    ``r`` and dividend yield ``q`` over the ACT/365-style year fraction ``T``.

    Gates (violations raise :class:`OptionInputError`): ``positive_spot``
    (spot strictly positive, inside domain) and ``valid_curves`` (rate and
    dividend yield finite, within ``[-1, 1]``; maturity in ``[0, 100]``).

    Invariants: result is finite and strictly positive (float64 overflow is
    rejected fail-closed, never returned as ``inf``). Unit: price units of
    ``spot``; currency ownership stays with the caller's instrument identity.
    """
    s = _require_price_positive(spot, "spot")
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    t = _require_maturity(maturity_years)
    result = _finite_result(s * math.exp((r - q) * t), "options.forward_price")
    if result <= 0.0:
        raise OptionInputError(
            "non_finite_result",
            "options.forward_price underflowed float64 to a non-positive value",
        )
    return result


# ---------------------------------------------------------------------------
# options.no_arbitrage_bounds
# ---------------------------------------------------------------------------


def _bounds_core(
    s: float, k: float, t: float, r: float, q: float, right: str
) -> Tuple[float, float]:
    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    fwd_spot = s * df_q
    fwd_strike = k * df_r
    if right == "CALL":
        lower = max(fwd_spot - fwd_strike, 0.0)
        upper = fwd_spot
    else:
        lower = max(fwd_strike - fwd_spot, 0.0)
        upper = fwd_strike
    return lower, upper


def no_arbitrage_bounds(
    spot: NumberLike,
    strike: NumberLike,
    maturity_years: NumberLike,
    rate: NumberLike,
    dividend_yield: NumberLike,
    right: object,
) -> Tuple[float, float]:
    """``options.no_arbitrage_bounds`` — European price interval.

    With ``df_r = e^{-rT}``, ``df_q = e^{-qT}``:

    - CALL: ``lower = max(S*df_q - K*df_r, 0)``, ``upper = S*df_q``;
    - PUT:  ``lower = max(K*df_r - S*df_q, 0)``, ``upper = K*df_r``.

    Gate ``valid_contract``: spot/strike strictly positive within domain,
    maturity in ``[0, 100]``, curves within ``[-1, 1]``, right valid.

    Invariant ``lower_not_above_upper``: ``0 <= lower <= upper`` holds by
    construction and is re-checked fail-closed. Returns ``(lower, upper)``
    as finite float64 price units.
    """
    s = _require_price_positive(spot, "spot")
    k = _require_price_positive(strike, "strike")
    t = _require_maturity(maturity_years)
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    right_s = _require_right(right)
    lower, upper = _bounds_core(s, k, t, r, q, right_s)
    lower = _finite_result(lower, "options.no_arbitrage_bounds")
    upper = _finite_result(upper, "options.no_arbitrage_bounds")
    if lower > upper:
        raise OptionInputError(
            "non_finite_result",
            "options.no_arbitrage_bounds produced lower > upper "
            f"({lower!r} > {upper!r})",
        )
    return lower, upper


# ---------------------------------------------------------------------------
# options.european_price
# ---------------------------------------------------------------------------


def _bsm_price_core(
    s: float, k: float, t: float, r: float, q: float, vol: float, right: str
) -> float:
    """Closed-form BSM on pre-validated float64 inputs.

    ``T == 0`` returns intrinsic value; ``vol == 0`` returns the
    deterministic discounted-forward bound ``max(±(S e^{-qT} - K e^{-rT}), 0)``
    (the vol->0 limit of the closed form). Tiny negative float rounding is
    normalized to ``0.0`` (the analytic price is provably non-negative).
    """
    if t == 0.0:
        intrinsic = s - k if right == "CALL" else k - s
        return max(intrinsic, 0.0)
    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    fwd_spot = s * df_q
    fwd_strike = k * df_r
    if vol == 0.0:
        deterministic = fwd_spot - fwd_strike if right == "CALL" else fwd_strike - fwd_spot
        return max(deterministic, 0.0)
    sqrt_t = math.sqrt(t)
    sigma_sqrt_t = vol * sqrt_t
    if sigma_sqrt_t == 0.0:
        # vol > 0 and t > 0, but vol * sqrt(t) underflowed float64 (subnormal
        # inputs). At sigma*sqrt(T) below the smallest positive float64 the
        # analytic price is indistinguishable from its deterministic vol->0
        # limit at float64 precision — return that exact limit (documented
        # numerical boundary, not a fallback).
        deterministic = fwd_spot - fwd_strike if right == "CALL" else fwd_strike - fwd_spot
        return max(deterministic, 0.0)
    d1 = (math.log(s / k) + (r - q + 0.5 * vol * vol) * t) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    if right == "CALL":
        price = fwd_spot * _norm_cdf(d1) - fwd_strike * _norm_cdf(d2)
    else:
        price = fwd_strike * _norm_cdf(-d2) - fwd_spot * _norm_cdf(-d1)
    # Analytic price is >= 0; only float64 rounding can produce a tiny
    # negative value here. Normalize within documented tolerance.
    return max(price, 0.0)


def european_price(
    spot: NumberLike,
    strike: NumberLike,
    maturity_years: NumberLike,
    rate: NumberLike,
    dividend_yield: NumberLike,
    volatility: NumberLike,
    right: object,
) -> float:
    """``options.european_price`` — closed-form Black-Scholes-Merton.

    Method: analytic BSM with continuous rate ``r`` and dividend yield ``q``,
    standard normal CDF via ``math.erf`` (deliberately no SciPy in this
    runtime path). ``d1 = [ln(S/K) + (r - q + vol^2/2) T] / (vol sqrt(T))``.

    Domain (gate ``inside_model_domain``, violations raise
    :class:`OptionInputError`): spot/strike in ``(0, 1e12]``, maturity in
    ``[0, 100]`` years, volatility in ``[0, 10]``, rate and dividend yield in
    ``[-1, 1]``, right valid.

    Documented boundary cases (deterministic, not fallbacks):

    - ``maturity_years == 0``: intrinsic value ``max(±(S - K), 0)``;
    - ``volatility == 0``: discounted deterministic bound
      ``max(±(S e^{-qT} - K e^{-rT}), 0)`` (the vol->0 limit).

    Invariants (verified by tests): price inside :func:`no_arbitrage_bounds`,
    put-call parity, monotonicity in spot, convexity in strike — all within
    ``FLOAT64_REL_TOL`` / ``FLOAT64_ABS_TOL``. Result is a finite float64
    price in the units of ``spot``.
    """
    s = _require_price_positive(spot, "spot")
    k = _require_price_positive(strike, "strike")
    t = _require_maturity(maturity_years)
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    vol = _require_volatility(volatility)
    right_s = _require_right(right)
    return _finite_result(
        _bsm_price_core(s, k, t, r, q, vol, right_s), "options.european_price"
    )


# ---------------------------------------------------------------------------
# options.implied_volatility
# ---------------------------------------------------------------------------


def implied_volatility(
    observed_price: NumberLike,
    spot: NumberLike,
    strike: NumberLike,
    maturity_years: NumberLike,
    rate: NumberLike,
    dividend_yield: NumberLike,
    right: object,
    quote_side: str,
) -> float:
    """``options.implied_volatility`` — bracketed Brent root of the BSM price.

    ``quote_side`` documents which side of the quote the observed price came
    from and must belong to the closed catalogue :data:`QUOTE_SIDES`
    (``BID``/``ASK``/``MID``/``LAST``/``MODEL``); it does not change the
    mathematics but is required so the caller's provenance is explicit.

    Gates (fail-closed):

    - all pricing-domain gates of :func:`european_price`; additionally
      ``maturity_years > 0`` (an expired option has no implied volatility);
    - ``price_inside_bounds``: the observed price must lie STRICTLY inside
      :func:`no_arbitrage_bounds`; at or outside the bounds raises
      :class:`IVNoSolutionError`;
    - ``bracket_exists``: the explicit bracket
      ``[IV_BRACKET_LO, IV_BRACKET_HI]`` = ``[1e-6, 5.0]`` is verified by
      evaluating the pricer at both edges; a price below the floor price or
      above the ceiling price raises :class:`IVNoSolutionError` (never a
      clamped or extrapolated volatility).

    Root finding: SciPy ``brentq`` on the verified bracket with
    ``xtol=1e-12``; non-convergence raises :class:`IVNoSolutionError`.

    Invariants (verified by tests): round trip price -> IV -> price within
    ``1e-7`` relative; result is a finite annualized decimal (``0.25`` =
    25%/yr) inside the bracket.
    """
    if not isinstance(quote_side, str) or quote_side not in QUOTE_SIDES:
        raise OptionInputError(
            "invalid_quote_side",
            f"quote_side must be one of {sorted(QUOTE_SIDES)}, got {quote_side!r}",
        )
    p = _to_float(observed_price, "observed_price")
    s = _require_price_positive(spot, "spot")
    k = _require_price_positive(strike, "strike")
    t = _require_maturity(maturity_years)
    if t == 0.0:
        raise OptionInputError(
            "maturity_zero_no_iv",
            "implied volatility is undefined at expiry (maturity_years == 0)",
        )
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    right_s = _require_right(right)
    lower, upper = _bounds_core(s, k, t, r, q, right_s)
    if not (lower < p < upper):
        raise IVNoSolutionError(
            "price_outside_no_arbitrage_bounds",
            f"observed_price {p!r} ({quote_side}) is not strictly inside the "
            f"no-arbitrage interval ({lower!r}, {upper!r})",
        )

    def objective(vol: float) -> float:
        return _bsm_price_core(s, k, t, r, q, vol, right_s) - p

    f_lo = objective(IV_BRACKET_LO)
    f_hi = objective(IV_BRACKET_HI)
    if f_lo >= 0.0:
        raise IVNoSolutionError(
            "price_below_bracket_floor",
            f"observed_price {p!r} is at or below the model price at the "
            f"bracket floor vol={IV_BRACKET_LO!r}; no IV inside "
            f"[{IV_BRACKET_LO!r}, {IV_BRACKET_HI!r}]",
        )
    if f_hi <= 0.0:
        raise IVNoSolutionError(
            "price_above_bracket_ceiling",
            f"observed_price {p!r} is at or above the model price at the "
            f"bracket ceiling vol={IV_BRACKET_HI!r}; no IV inside "
            f"[{IV_BRACKET_LO!r}, {IV_BRACKET_HI!r}]",
        )
    root, info = _brentq(
        objective,
        IV_BRACKET_LO,
        IV_BRACKET_HI,
        xtol=1e-12,
        maxiter=200,
        full_output=True,
        disp=False,
    )
    if not info.converged:
        raise IVNoSolutionError(
            "root_not_converged",
            "brentq did not converge inside the verified bracket "
            f"[{IV_BRACKET_LO!r}, {IV_BRACKET_HI!r}]",
        )
    iv = float(root)
    if not math.isfinite(iv) or iv < IV_BRACKET_LO or iv > IV_BRACKET_HI:
        raise IVNoSolutionError(
            "root_outside_bracket",
            f"brentq returned {iv!r}, outside the verified bracket",
        )
    return iv


# ---------------------------------------------------------------------------
# options.greeks
# ---------------------------------------------------------------------------


class GreeksResult(ContractModel):
    """BSM sensitivities with the unit of every field encoded explicitly.

    Fields and units (all finite float64; NaN/inf rejected at validation):

    - ``delta``: option price change per +1 unit of underlying price
      (dimensionless, in ``[-1, 1]`` for non-negative dividend yields;
      CALL >= 0, PUT <= 0);
    - ``gamma``: delta change per +1 unit of underlying price
      (1 / price unit, >= 0 for vanilla options);
    - ``vega``: RAW price change per +1.0 change of annualized volatility
      (i.e. per 100 vol points; price units, >= 0 for vanilla options);
    - ``vega_per_point``: derived view per +0.01 volatility change
      (one vol point); always ``vega * 0.01``;
    - ``theta``: RAW price change per +1 YEAR of calendar time elapsing
      (``dV/dt = -dV/dT``, model-time ACT/365-style year; price units,
      typically negative for long vanilla options);
    - ``theta_per_calendar_day``: derived view per one CALENDAR day under
      the ACT/365F convention; always ``theta / 365``;
    - ``rho``: RAW price change per +1.0 change of the continuously
      compounded rate (i.e. per 100 percentage points; price units);
    - ``rho_per_bp``: derived view per +1 basis point (0.0001) rate change;
      always ``rho * 0.0001``.

    Monetary exposures (multiplier x quantity x FX) are deliberately NOT
    computed here: they require the manual position declaration and a dated
    FX rate, which belong to the caller.
    """

    delta: float
    gamma: float
    vega: float
    vega_per_point: float
    theta: float
    theta_per_calendar_day: float
    rho: float
    rho_per_bp: float

    @field_validator("*")
    @classmethod
    def _finite_float(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError(f"greek values must be finite, got {value!r}")
        return 0.0 if value == 0.0 else value

    @model_validator(mode="after")
    def _derived_views_consistent(self) -> "GreeksResult":
        checks = (
            ("vega_per_point", self.vega_per_point, self.vega * 0.01),
            (
                "theta_per_calendar_day",
                self.theta_per_calendar_day,
                self.theta / DAYS_PER_YEAR,
            ),
            ("rho_per_bp", self.rho_per_bp, self.rho * 0.0001),
        )
        for name, actual, expected in checks:
            if abs(actual - expected) > 1e-12 * max(1.0, abs(expected)):
                raise ValueError(
                    f"{name} ({actual!r}) is inconsistent with its raw field "
                    f"(expected {expected!r})"
                )
        return self


def greeks(
    spot: NumberLike,
    strike: NumberLike,
    maturity_years: NumberLike,
    rate: NumberLike,
    dividend_yield: NumberLike,
    volatility: NumberLike,
    right: object,
) -> GreeksResult:
    """``options.greeks`` — closed-form BSM sensitivities.

    Units are documented per field on :class:`GreeksResult` (raw vega per
    +1.0 vol, raw theta per year of elapsing calendar time, raw rho per +1.0
    rate, plus the derived per-point / per-calendar-day / per-basis-point
    views).

    Domain: the :func:`european_price` gates, and additionally
    ``maturity_years > 0`` and ``volatility > 0`` — at expiry or at zero
    volatility the distributional sensitivities are not defined and the
    input is rejected fail-closed (no step-function fallback).

    Invariants (verified by tests): all values finite; ``delta`` in
    ``[-1, 1]`` for ``dividend_yield >= 0``; ``gamma >= 0``; ``vega >= 0``.
    """
    s = _require_price_positive(spot, "spot")
    k = _require_price_positive(strike, "strike")
    t = _require_maturity(maturity_years)
    if t == 0.0:
        raise OptionInputError(
            "maturity_zero_no_greeks",
            "BSM greeks are undefined at expiry (maturity_years == 0)",
        )
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    vol = _require_volatility(volatility)
    if vol == 0.0:
        raise OptionInputError(
            "volatility_zero_no_greeks",
            "BSM greeks are undefined at zero volatility (degenerate "
            "distribution); provide a strictly positive volatility",
        )
    right_s = _require_right(right)
    sqrt_t = math.sqrt(t)
    sigma_sqrt_t = vol * sqrt_t
    d1 = (math.log(s / k) + (r - q + 0.5 * vol * vol) * t) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    pdf_d1 = _norm_pdf(d1)
    if right_s == "CALL":
        delta = df_q * _norm_cdf(d1)
        theta = (
            -(s * vol * df_q * pdf_d1) / (2.0 * sqrt_t)
            - r * k * df_r * _norm_cdf(d2)
            + q * s * df_q * _norm_cdf(d1)
        )
        rho = k * t * df_r * _norm_cdf(d2)
    else:
        delta = -df_q * _norm_cdf(-d1)
        theta = (
            -(s * vol * df_q * pdf_d1) / (2.0 * sqrt_t)
            + r * k * df_r * _norm_cdf(-d2)
            - q * s * df_q * _norm_cdf(-d1)
        )
        rho = -k * t * df_r * _norm_cdf(-d2)
    gamma = df_q * pdf_d1 / (s * sigma_sqrt_t)
    vega = s * df_q * pdf_d1 * sqrt_t
    calc = "options.greeks"
    delta = _finite_result(delta, calc)
    gamma = _finite_result(gamma, calc)
    vega = _finite_result(vega, calc)
    theta = _finite_result(theta, calc)
    rho = _finite_result(rho, calc)
    return GreeksResult(
        delta=delta,
        gamma=gamma,
        vega=vega,
        vega_per_point=vega * 0.01,
        theta=theta,
        theta_per_calendar_day=theta / DAYS_PER_YEAR,
        rho=rho,
        rho_per_bp=rho * 0.0001,
    )


# ---------------------------------------------------------------------------
# options.american_price
# ---------------------------------------------------------------------------


def american_price(
    spot: NumberLike,
    strike: NumberLike,
    maturity_years: NumberLike,
    rate: NumberLike,
    dividend_yield: NumberLike,
    volatility: NumberLike,
    right: object,
    *,
    steps: int = 800,
    discrete_dividends: Sequence[object] = (),
) -> float:
    """``options.american_price`` — QuantLib binomial CRR tree.

    Method: ``QuantLib.BinomialVanillaEngine(process, "crr", steps)`` on a
    ``BlackScholesMertonProcess`` with flat continuously compounded rate and
    dividend-yield curves (Actual/365 Fixed day count, null calendar) and
    constant volatility. QuantLib is a hard dependency of the ``quant``
    extra and is imported at module top — there is no analytic fallback.

    Date grid (strict, fail-closed): QuantLib prices between dates, so the
    maturity is realized as an integral number of calendar days on an
    ACT/365F grid. ``maturity_years`` must therefore be a multiple of
    ``1/365`` (e.g. ``days / 365.0``; float round-off up to
    ``FLOAT64_REL_TOL`` relative is tolerated). An off-grid maturity is
    rejected with reason ``maturity_off_date_grid`` — it is NEVER silently
    rounded to the nearest day: that quantization (up to half a day) can
    return a price below the no-arbitrage floor of the requested maturity
    for short maturities. A positive maturity that rounds to zero days is
    rejected with ``maturity_below_date_grid`` (never silently priced at
    expiry).

    Explicit non-capabilities (fail-closed):

    - ``discrete_dividends`` non-empty raises
      :class:`OptionNotImplementedError` — discrete cash dividends are
      NOT_IMPLEMENTED; they are never approximated by the continuous yield
      and never silently priced with BSM;
    - ``volatility == 0`` is rejected (:class:`OptionInputError`) — the CRR
      lattice degenerates; there is no deterministic-bound fallback here.

    Other gates: the :func:`european_price` domain gates;
    ``steps`` an int ``>= AMERICAN_MIN_STEPS`` (validated numerical grid,
    default 800). ``maturity_years == 0`` returns intrinsic value.

    Invariants (verified by tests): finite non-negative price; American
    >= European minus a documented lattice tolerance; convergence between
    grid sizes.
    """
    s = _require_price_positive(spot, "spot")
    k = _require_price_positive(strike, "strike")
    t = _require_maturity(maturity_years)
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    vol = _require_volatility(volatility)
    right_s = _require_right(right)
    n_steps = _require_int(steps, "steps")
    if n_steps < AMERICAN_MIN_STEPS:
        raise OptionInputError(
            "steps_below_validated_grid",
            f"steps must be >= {AMERICAN_MIN_STEPS} (validated numerical "
            f"grid), got {n_steps}",
        )
    dividends_seq = _require_sequence(discrete_dividends, "discrete_dividends")
    if len(dividends_seq) > 0:
        raise OptionNotImplementedError(
            "american_price.discrete_dividends",
            "discrete cash dividends are not implemented for the American "
            "engine; refusing to approximate them with a continuous yield "
            "or a silent BSM fallback",
        )
    if t == 0.0:
        intrinsic = s - k if right_s == "CALL" else k - s
        return max(intrinsic, 0.0)
    if vol == 0.0:
        raise OptionInputError(
            "volatility_out_of_domain",
            "the American CRR engine requires volatility > 0 (the lattice "
            "degenerates at zero volatility); no deterministic fallback",
        )
    days = int(round(t * DAYS_PER_YEAR))
    if days < 1:
        raise OptionInputError(
            "maturity_below_date_grid",
            f"maturity_years {t!r} rounds to 0 days on the ACT/365F date "
            "grid; the American engine cannot represent it (minimum "
            "1/365 year)",
        )
    # Fail-closed date-grid gate: the engine can only price an integral
    # number of calendar days. Rejecting off-grid maturities (instead of
    # silently rounding, up to half a day) prevents returning a price below
    # the no-arbitrage floor of the REQUESTED maturity for short maturities.
    # The tolerance admits float round-off of exact-grid inputs such as
    # ``days / 365.0`` (a few ulps), nothing more.
    grid_error_days = abs(t * DAYS_PER_YEAR - float(days))
    if grid_error_days > FLOAT64_REL_TOL * max(1.0, t * DAYS_PER_YEAR):
        raise OptionInputError(
            "maturity_off_date_grid",
            f"maturity_years {t!r} is not an integral number of calendar "
            f"days on the ACT/365F date grid (nearest is {days}/365, off by "
            f"{grid_error_days!r} days); the American engine prices between "
            "dates and will not silently quantize the maturity — pass a "
            "multiple of 1/365 (e.g. days / 365.0)",
        )
    anchor = _ql.Date(_QL_ANCHOR_SERIAL)
    _ql.Settings.instance().evaluationDate = anchor
    expiry = anchor + days
    day_count = _ql.Actual365Fixed()
    calendar = _ql.NullCalendar()
    process = _ql.BlackScholesMertonProcess(
        _ql.QuoteHandle(_ql.SimpleQuote(s)),
        _ql.YieldTermStructureHandle(_ql.FlatForward(anchor, q, day_count)),
        _ql.YieldTermStructureHandle(_ql.FlatForward(anchor, r, day_count)),
        _ql.BlackVolTermStructureHandle(
            _ql.BlackConstantVol(anchor, calendar, vol, day_count)
        ),
    )
    ql_right = _ql.Option.Call if right_s == "CALL" else _ql.Option.Put
    option = _ql.VanillaOption(
        _ql.PlainVanillaPayoff(ql_right, k),
        _ql.AmericanExercise(anchor, expiry),
    )
    option.setPricingEngine(_ql.BinomialVanillaEngine(process, "crr", n_steps))
    npv = float(option.NPV())
    npv = _finite_result(npv, "options.american_price")
    if npv < -FLOAT64_ABS_TOL * max(1.0, s):
        raise OptionInputError(
            "non_finite_result",
            f"options.american_price produced a negative price ({npv!r})",
        )
    return max(npv, 0.0)


# ---------------------------------------------------------------------------
# options.payoff — legs and exact expiry P&L
# ---------------------------------------------------------------------------


class OptionLeg(ContractModel):
    """One declared leg of a manually stated structure (strict, frozen).

    Fields:

    - ``quantity``: signed integer number of contracts/shares; positive =
      long, negative = short; zero is rejected (a leg must exist);
    - ``right``: ``"CALL"``, ``"PUT"`` or ``"STOCK"`` (the linear underlying
      leg, intrinsic ``h(S) = S``);
    - ``strike``: strictly positive ``Decimal``; REQUIRED for CALL/PUT and
      FORBIDDEN for STOCK (fail-closed both ways);
    - ``premium``: non-negative ``Decimal`` unit premium actually declared
      for the leg (for STOCK, the declared unit reference price);
    - ``multiplier``: strictly positive int contract multiplier.

    Legs describe a manually declared analytic structure only: same
    underlying, currency and expiry by construction of the caller. No field
    of this model is, or ever becomes, a transmissible ticket of any kind.
    """

    quantity: int
    right: Literal["CALL", "PUT", "STOCK"]
    strike: Optional[PositiveDecimal] = None
    premium: NonNegativeDecimal
    multiplier: PositiveInt

    @field_validator("quantity")
    @classmethod
    def _non_zero_quantity(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity must be a non-zero signed integer")
        return value

    @model_validator(mode="after")
    def _strike_presence(self) -> "OptionLeg":
        if self.right == "STOCK":
            if self.strike is not None:
                raise ValueError("a STOCK leg must not carry a strike")
        elif self.strike is None:
            raise ValueError(f"a {self.right} leg requires a strike")
        return self


def _require_legs(legs: object) -> Tuple[OptionLeg, ...]:
    seq = _require_sequence(legs, "legs")
    if len(seq) == 0:
        raise OptionInputError("empty_legs", "at least one leg is required")
    typed: list = []
    for i, leg in enumerate(seq):
        if not isinstance(leg, OptionLeg):
            raise OptionInputError(
                "invalid_type",
                f"legs[{i}] must be OptionLeg, got {type(leg).__name__}",
            )
        typed.append(leg)
    return tuple(typed)


def _spot_to_exact_decimal(value: object, name: str) -> Decimal:
    """Convert a terminal spot to an EXACT Decimal (no rounding).

    ``Decimal(float)`` is the exact binary-to-decimal expansion, ``int`` is
    exact by construction, ``Decimal`` passes through. ``bool``, non-finite
    and negative values are rejected (a terminal spot may be exactly zero —
    the bankruptcy tail — but never negative).
    """
    if isinstance(value, bool):
        raise OptionInputError(
            "invalid_type", f"{name} must be int, float or Decimal, got bool"
        )
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise OptionInputError(
                "non_finite_input", f"{name} is a non-finite Decimal ({value})"
            )
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise OptionInputError(
                "non_finite_input", f"{name} is not finite ({value!r})"
            )
        result = Decimal(value)  # exact binary expansion, no rounding
    else:
        raise OptionInputError(
            "invalid_type",
            f"{name} must be int, float or Decimal, got {type(value).__name__}",
        )
    if result < 0:
        raise OptionInputError(
            "negative_terminal_spot", f"{name} must be >= 0, got {result}"
        )
    return result


def payoff_at_expiry(
    legs: Sequence[OptionLeg],
    terminal_spot_grid: Sequence[NumberLike],
    fees: Decimal,
) -> Tuple[Decimal, ...]:
    """``options.payoff`` — exact expiry P&L per terminal spot.

    ``P&L_T(S) = sum_i q_i * M_i * [h_i(S) - p_i] - F`` with intrinsic
    ``h_CALL(S) = max(S - K, 0)``, ``h_PUT(S) = max(K - S, 0)``,
    ``h_STOCK(S) = S``; ``F = fees`` groups the positive declared costs.

    Money arithmetic: computed ENTIRELY in ``Decimal`` under a local
    60-significant-digit context, so payoffs are EXACT at every strike
    breakpoint and leg-sum linearity is exact (documented bound: inputs with
    more than ~50 significant digits would round; declared premiums, fees
    and realistic spot grids are far below that). Terminal spots given as
    ``float`` are converted by their exact binary expansion.

    Gates: legs non-empty and typed; every terminal spot finite and >= 0
    (zero = bankruptcy tail); ``fees`` a finite non-negative ``Decimal``
    instance (costs are declared, never defaulted).

    This formula describes expiry only; before expiry legs are repriced by
    :func:`scenario_grid`. Returns one exact ``Decimal`` P&L (money units of
    the declared premiums) per grid point, in grid order.
    """
    typed_legs = _require_legs(legs)
    if not isinstance(fees, Decimal) or isinstance(fees, bool):
        raise OptionInputError(
            "invalid_type",
            f"fees must be Decimal, got {type(fees).__name__}",
        )
    if not fees.is_finite():
        raise OptionInputError(
            "non_finite_input", f"fees is a non-finite Decimal ({fees})"
        )
    if fees < 0:
        raise OptionInputError(
            "negative_fees", f"fees must be >= 0 (positive declared costs), got {fees}"
        )
    grid_seq = _require_sequence(terminal_spot_grid, "terminal_spot_grid")
    if len(grid_seq) == 0:
        raise OptionInputError(
            "empty_grid", "terminal_spot_grid must contain at least one spot"
        )
    spots = [
        _spot_to_exact_decimal(v, f"terminal_spot_grid[{i}]")
        for i, v in enumerate(grid_seq)
    ]
    zero = Decimal(0)
    results: list = []
    with localcontext() as ctx:
        ctx.prec = 60
        for spot_t in spots:
            total = zero
            for leg in typed_legs:
                if leg.right == "CALL":
                    intrinsic = spot_t - leg.strike
                    if intrinsic < 0:
                        intrinsic = zero
                elif leg.right == "PUT":
                    intrinsic = leg.strike - spot_t
                    if intrinsic < 0:
                        intrinsic = zero
                else:  # STOCK
                    intrinsic = spot_t
                total += (
                    Decimal(leg.quantity)
                    * Decimal(leg.multiplier)
                    * (intrinsic - leg.premium)
                )
            total -= fees
            if total.is_zero() and total.is_signed():
                total = total.copy_negate()  # normalize -0
            results.append(total)
    return tuple(results)


# ---------------------------------------------------------------------------
# options.scenario_grid
# ---------------------------------------------------------------------------


def scenario_grid(
    legs: Sequence[OptionLeg],
    spot_grid: Sequence[NumberLike],
    time_grid_years: Sequence[NumberLike],
    iv_scenarios: Sequence[Sequence[Optional[NumberLike]]],
    rate: NumberLike,
    dividend_yield: NumberLike,
) -> Tuple[Tuple[Tuple[float, ...], ...], ...]:
    """``options.scenario_grid`` — BSM repricing of all legs per cell.

    Every cell ``[scenario][time][spot]`` reprices EVERY leg on the SAME
    assumption snapshot (this call's arguments — one rate, one dividend
    yield, one per-leg volatility vector per scenario, one remaining
    maturity per time point) and sums
    ``q_i * M_i * (model_value_i(S, T, vol_i) - p_i)``. STOCK legs
    contribute ``q * M * (S - p)``. Fees are NOT subtracted here (they
    belong to :func:`payoff_at_expiry` and to the caller's cost model);
    the grid is P&L before declared costs.

    Structure of ``iv_scenarios``: a sequence of scenarios; each scenario is
    a sequence aligned index-by-index with ``legs`` — ``None`` for STOCK
    legs (no volatility applies, required to be ``None`` fail-closed) and an
    annualized decimal volatility in ``[0, 10]`` for option legs. All legs
    share the single expiry described by ``time_grid_years`` (remaining
    maturity in years, ``>= 0``); calendar/diagonal structures are out of
    scope for this grid.

    Gates: leg/domain gates as elsewhere; every spot strictly positive
    within domain (a zero terminal spot belongs to
    :func:`payoff_at_expiry`); non-empty grids; scenario vectors sized
    exactly like ``legs``.

    Invariants (verified by tests): deterministic (identical inputs give
    identical grids), every cell finite, and at ``T == 0`` the cells
    converge to ``payoff_at_expiry(legs, spot_grid, fees=0)`` within
    float64 tolerance (premiums are converted to float64 here — documented
    conversion, exact money stays in :func:`payoff_at_expiry`).

    Returns nested tuples indexed ``[scenario][time][spot]`` of finite
    float64 P&L values in the money units of the declared premiums.
    """
    typed_legs = _require_legs(legs)
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    spot_seq = _require_sequence(spot_grid, "spot_grid")
    if len(spot_seq) == 0:
        raise OptionInputError("empty_grid", "spot_grid must not be empty")
    spots = [
        _require_price_positive(v, f"spot_grid[{i}]") for i, v in enumerate(spot_seq)
    ]
    time_seq = _require_sequence(time_grid_years, "time_grid_years")
    if len(time_seq) == 0:
        raise OptionInputError("empty_grid", "time_grid_years must not be empty")
    times = [
        _require_maturity(v, f"time_grid_years[{i}]") for i, v in enumerate(time_seq)
    ]
    scen_seq = _require_sequence(iv_scenarios, "iv_scenarios")
    if len(scen_seq) == 0:
        raise OptionInputError("empty_grid", "iv_scenarios must not be empty")
    scenarios: list = []
    for si, scenario in enumerate(scen_seq):
        vol_seq = _require_sequence(scenario, f"iv_scenarios[{si}]")
        if len(vol_seq) != len(typed_legs):
            raise OptionInputError(
                "scenario_leg_mismatch",
                f"iv_scenarios[{si}] has {len(vol_seq)} entries for "
                f"{len(typed_legs)} legs; one volatility (or None for STOCK) "
                "per leg is required",
            )
        vols: list = []
        for li, (leg, vol_entry) in enumerate(zip(typed_legs, vol_seq)):
            if leg.right == "STOCK":
                if vol_entry is not None:
                    raise OptionInputError(
                        "stock_leg_volatility",
                        f"iv_scenarios[{si}][{li}] must be None for a STOCK "
                        f"leg, got {vol_entry!r}",
                    )
                vols.append(None)
            else:
                if vol_entry is None:
                    raise OptionInputError(
                        "missing_leg_volatility",
                        f"iv_scenarios[{si}][{li}] is None for a "
                        f"{leg.right} leg; an annualized volatility is "
                        "required (absence is never converted to zero)",
                    )
                vols.append(
                    _require_volatility(vol_entry, f"iv_scenarios[{si}][{li}]")
                )
        scenarios.append(vols)

    leg_static = [
        (
            float(leg.quantity) * float(leg.multiplier),
            leg.right,
            None if leg.strike is None else float(leg.strike),
            float(leg.premium),
        )
        for leg in typed_legs
    ]
    grid: list = []
    for vols in scenarios:
        time_rows: list = []
        for t in times:
            spot_row: list = []
            for s in spots:
                total = 0.0
                for (qty_mult, leg_right, leg_strike, leg_premium), vol in zip(
                    leg_static, vols
                ):
                    if leg_right == "STOCK":
                        value = s
                    else:
                        value = _bsm_price_core(
                            s, leg_strike, t, r, q, vol, leg_right
                        )
                    total += qty_mult * (value - leg_premium)
                spot_row.append(_finite_result(total, "options.scenario_grid"))
            time_rows.append(tuple(spot_row))
        grid.append(tuple(time_rows))
    return tuple(grid)


# ---------------------------------------------------------------------------
# Defined-risk certification (tail analysis)
# ---------------------------------------------------------------------------


class DefinedRiskResult(ContractModel):
    """Outcome of the defined-risk tail certification (strict, frozen).

    ``is_defined_risk`` is the verdict; ``reason_code`` is the stable
    machine-readable code (``DEFINED_RISK``,
    ``UNCOVERED_SHORT_UPSIDE_TAIL``, ``UNCOVERED_SHORT_DOWNSIDE_TAIL``);
    ``detail`` is the human-readable justification with the tail exposures.
    """

    is_defined_risk: bool
    reason_code: str
    detail: str

    @field_validator("reason_code", "detail")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("must be a non-empty string")
        return value


def defined_risk_check(legs: Sequence[OptionLeg]) -> DefinedRiskResult:
    """Certify that a declared structure has no uncovered short tail.

    Tail analysis (piecewise-linear expiry payoff, both tails):

    - upside tail ``S -> inf``: CALL and STOCK legs dominate; the
      multiplier-weighted net quantity
      ``sum(q*M over CALL legs) + sum(q*M over STOCK legs)`` must be >= 0,
      otherwise the residual short quantity is uncovered and the loss is
      unbounded — REJECTED (``UNCOVERED_SHORT_UPSIDE_TAIL``);
    - downside tail ``S -> 0``: PUT legs dominate; the multiplier-weighted
      net put quantity ``sum(q*M over PUT legs)`` must be >= 0, otherwise a
      residual short put quantity is uncovered on the bankruptcy tail —
      REJECTED (``UNCOVERED_SHORT_DOWNSIDE_TAIL``). (A short STOCK leg
      never covers this check's puts: a structure net short stock is
      already rejected on the upside tail unless calls cover it.)

    Consequences on the closed catalogue (verified by tests): bull call
    debit, bear put debit, long straddle and long strangle are ACCEPTED;
    naked short calls/puts and ratio spreads (net short one tail) are
    REJECTED. A short leg therefore only exists as an inseparable component
    of an accepted structure.

    Premise (caller's responsibility, as for :func:`payoff_at_expiry`):
    all legs share the same underlying, currency and expiry; unknown
    combinations across expiries (calendars, diagonals) cannot be expressed
    with :class:`OptionLeg` and are out of scope by construction.

    This is an analytic certification of a manually declared structure;
    it neither creates nor implies any transaction.
    """
    typed_legs = _require_legs(legs)
    upside = 0
    downside_puts = 0
    for leg in typed_legs:
        weight = leg.quantity * leg.multiplier
        if leg.right in ("CALL", "STOCK"):
            upside += weight
        else:
            downside_puts += weight
    if upside < 0:
        return DefinedRiskResult(
            is_defined_risk=False,
            reason_code="UNCOVERED_SHORT_UPSIDE_TAIL",
            detail=(
                "net multiplier-weighted CALL+STOCK quantity on the S->inf "
                f"tail is {upside} < 0: unbounded loss, structure rejected"
            ),
        )
    if downside_puts < 0:
        return DefinedRiskResult(
            is_defined_risk=False,
            reason_code="UNCOVERED_SHORT_DOWNSIDE_TAIL",
            detail=(
                "net multiplier-weighted PUT quantity on the S->0 tail is "
                f"{downside_puts} < 0: uncovered short puts, structure "
                "rejected"
            ),
        )
    return DefinedRiskResult(
        is_defined_risk=True,
        reason_code="DEFINED_RISK",
        detail=(
            "both tails covered: net CALL+STOCK quantity on S->inf is "
            f"{upside} >= 0 and net PUT quantity on S->0 is "
            f"{downside_puts} >= 0; maximum loss is finite"
        ),
    )
