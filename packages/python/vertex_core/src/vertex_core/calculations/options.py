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
from collections.abc import Sequence
from decimal import Decimal, localcontext
from typing import Literal

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
    "FLOAT64_ABS_TOL",
    "FLOAT64_REL_TOL",
    "IV_BRACKET_HI",
    "IV_BRACKET_LO",
    "MATURITY_MAX_YEARS",
    "QUOTE_SIDES",
    "RATE_ABS_MAX",
    "SPOT_STRIKE_MAX",
    "VOLATILITY_MAX",
    "DefinedRiskResult",
    "GreeksResult",
    "IVNoSolutionError",
    "NumberLike",
    "OptionInputError",
    "OptionLeg",
    "OptionNotImplementedError",
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
"""Minimum validated grid resolution (time and space steps) for the
American finite-difference engine."""

QUOTE_SIDES = frozenset({"BID", "ASK", "MID", "LAST", "MODEL"})
"""Closed catalogue of quote-side labels accepted by implied volatility."""

DAYS_PER_YEAR = 365.0
"""Calendar-day convention (ACT/365F) used for theta-per-day and the
American engine's date grid."""

NumberLike = int | float | Decimal
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


def _to_float(value: object, name: str) -> float:
    """Convert a boundary number to finite float64; reject everything else."""
    if isinstance(value, bool):
        raise OptionInputError("invalid_type", f"{name} must be int, float or Decimal, got bool")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise OptionInputError("non_finite_input", f"{name} is a non-finite Decimal ({value})")
        result = float(value)
    elif isinstance(value, int):
        try:
            result = float(value)
        except OverflowError:
            raise OptionInputError("non_finite_input", f"{name} is too large for float64") from None
    elif isinstance(value, float):
        result = value
    else:
        raise OptionInputError(
            "invalid_type",
            f"{name} must be int, float or Decimal, got {type(value).__name__}",
        )
    if not math.isfinite(result):
        raise OptionInputError("non_finite_input", f"{name} is not finite in float64 ({result!r})")
    return 0.0 if result == 0.0 else result


def _require_price_positive(value: object, name: str) -> float:
    price = _to_float(value, name)
    if price <= 0.0:
        raise OptionInputError(
            f"non_positive_{name}", f"{name} must be strictly positive, got {price!r}"
        )
    if price > SPOT_STRIKE_MAX:
        raise OptionInputError(
            f"{name}_out_of_domain",
            f"{name} {price!r} exceeds the validated model domain (0, {SPOT_STRIKE_MAX:g}]",
        )
    return price


def _require_maturity(value: object, name: str = "maturity_years") -> float:
    t = _to_float(value, name)
    if t < 0.0:
        raise OptionInputError("negative_maturity", f"{name} must be >= 0 years, got {t!r}")
    if t > MATURITY_MAX_YEARS:
        raise OptionInputError(
            "maturity_out_of_domain",
            f"{name} {t!r} exceeds the validated model domain [0, {MATURITY_MAX_YEARS:g}] years",
        )
    return t


def _require_volatility(value: object, name: str = "volatility") -> float:
    vol = _to_float(value, name)
    if vol < 0.0:
        raise OptionInputError("negative_volatility", f"{name} must be >= 0, got {vol!r}")
    if vol > VOLATILITY_MAX:
        raise OptionInputError(
            "volatility_out_of_domain",
            f"{name} {vol!r} exceeds the validated model domain [0, {VOLATILITY_MAX:g}]",
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
        f"right must be OptionRight.CALL/PUT or the string 'CALL'/'PUT', got {right!r}",
    )


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OptionInputError("invalid_type", f"{name} must be int, got {type(value).__name__}")
    return value


def _require_sequence(value: object, name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
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
) -> tuple[float, float]:
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
) -> tuple[float, float]:
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
            f"options.no_arbitrage_bounds produced lower > upper ({lower!r} > {upper!r})",
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
    return _finite_result(_bsm_price_core(s, k, t, r, q, vol, right_s), "options.european_price")


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
    def _derived_views_consistent(self) -> GreeksResult:
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
    """``options.american_price`` — QuantLib finite differences.

    Method (registry reference ``QuantLib_finite_difference``):
    ``QuantLib.FdBlackScholesVanillaEngine(process, tGrid=steps,
    xGrid=steps, dampingSteps=0)`` (Douglas scheme) on a
    ``BlackScholesMertonProcess`` with flat continuously compounded rate and
    dividend-yield curves (Actual/365 Fixed day count, null calendar) and
    constant volatility. QuantLib is a hard dependency of the ``quant``
    extra and is imported at module top — there is no analytic fallback.
    The differential oracle for this engine is an independent binomial CRR
    tree plus golden vectors (see ``test_options_oracle.py``).

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
    expiry). The engine prices on an internal fixed anchor date; the
    process-global ``QuantLib.Settings.instance().evaluationDate`` is
    saved and restored around the computation (``try``/``finally``), so
    callers never observe a leaked mutation.

    Explicit non-capabilities (fail-closed):

    - ``discrete_dividends`` non-empty raises
      :class:`OptionNotImplementedError` — discrete cash dividends are
      NOT_IMPLEMENTED; they are never approximated by the continuous yield
      and never silently priced with BSM;
    - ``volatility == 0`` is rejected (:class:`OptionInputError`) — the
      numerical grid degenerates; there is no deterministic-bound fallback
      here.

    Other gates: the :func:`european_price` domain gates;
    ``steps`` an int ``>= AMERICAN_MIN_STEPS`` (validated numerical grid:
    both the time grid and the space grid of the finite-difference solver,
    default 800). ``maturity_years == 0`` returns intrinsic value.

    Invariants (verified by tests): finite non-negative price; American
    >= European minus a documented discretization tolerance; convergence
    between grid sizes; agreement with the independent CRR second method
    and the golden vectors of the oracle suite.
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
            f"steps must be >= {AMERICAN_MIN_STEPS} (validated numerical grid), got {n_steps}",
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
            "the American finite-difference engine requires volatility > 0 "
            "(the numerical grid degenerates at zero volatility); no "
            "deterministic fallback",
        )
    days = round(t * DAYS_PER_YEAR)
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
    # QuantLib's evaluation date is PROCESS-GLOBAL state. Save it and
    # restore it unconditionally (try/finally) so pricing never leaks the
    # internal anchor to other QuantLib users in the process, success or
    # failure alike (P2 audit fix).
    settings = _ql.Settings.instance()
    saved_evaluation_date = settings.evaluationDate
    try:
        settings.evaluationDate = anchor
        expiry = anchor + days
        day_count = _ql.Actual365Fixed()
        calendar = _ql.NullCalendar()
        process = _ql.BlackScholesMertonProcess(
            _ql.QuoteHandle(_ql.SimpleQuote(s)),
            _ql.YieldTermStructureHandle(_ql.FlatForward(anchor, q, day_count)),
            _ql.YieldTermStructureHandle(_ql.FlatForward(anchor, r, day_count)),
            _ql.BlackVolTermStructureHandle(_ql.BlackConstantVol(anchor, calendar, vol, day_count)),
        )
        ql_right = _ql.Option.Call if right_s == "CALL" else _ql.Option.Put
        option = _ql.VanillaOption(
            _ql.PlainVanillaPayoff(ql_right, k),
            _ql.AmericanExercise(anchor, expiry),
        )
        option.setPricingEngine(_ql.FdBlackScholesVanillaEngine(process, n_steps, n_steps, 0))
        npv = float(option.NPV())
    finally:
        settings.evaluationDate = saved_evaluation_date
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
    strike: PositiveDecimal | None = None
    premium: NonNegativeDecimal
    multiplier: PositiveInt

    @field_validator("quantity")
    @classmethod
    def _non_zero_quantity(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity must be a non-zero signed integer")
        return value

    @model_validator(mode="after")
    def _strike_presence(self) -> OptionLeg:
        if self.right == "STOCK":
            if self.strike is not None:
                raise ValueError("a STOCK leg must not carry a strike")
        elif self.strike is None:
            raise ValueError(f"a {self.right} leg requires a strike")
        return self


def _require_legs(legs: object) -> tuple[OptionLeg, ...]:
    seq = _require_sequence(legs, "legs")
    if len(seq) == 0:
        raise OptionInputError("empty_legs", "at least one leg is required")
    typed: list[OptionLeg] = []
    for i, leg in enumerate(seq):
        if not isinstance(leg, OptionLeg):
            raise OptionInputError(
                "invalid_type",
                f"legs[{i}] must be OptionLeg, got {type(leg).__name__}",
            )
        typed.append(leg)
    return tuple(typed)


def _require_defined_risk_for_shorts(
    typed_legs: tuple[OptionLeg, ...], calculation_id: str
) -> None:
    """Registry gate: a short quantity requires DEFINED_RISK certification.

    The specification requires the defined-risk verifier BEFORE any
    multi-leg scenario: as soon as a declared structure contains at least
    one short quantity it must be recognized by :func:`defined_risk_check`
    (strict closed catalogue). An uncertified structure is rejected
    fail-closed with reason ``undefined_risk_structure`` — a short leg only
    exists as an inseparable component of a certified structure. Strictly
    all-long structures pass without certification (their maximum loss is
    the premium paid, by construction).
    """
    if all(leg.quantity > 0 for leg in typed_legs):
        return
    verdict = defined_risk_check(typed_legs)
    if not verdict.is_defined_risk:
        raise OptionInputError(
            "undefined_risk_structure",
            f"{calculation_id} refuses an uncertified structure containing "
            f"short quantities — {verdict.reason_code}: {verdict.detail}",
        )


def _leg_strike(leg: OptionLeg) -> Decimal:
    """Strike d'une jambe CALL/PUT.

    ``OptionLeg`` garantit par validateur de modèle l'équivalence
    STOCK <=> ``strike is None``. Cette fonction rend cet invariant
    inter-champs visible au vérificateur de types, sans l'affaiblir : une
    jambe STOCK qui arriverait ici est un défaut de programmation, pas une
    entrée utilisateur, et échoue fermé.
    """
    strike = leg.strike
    if strike is None:
        raise OptionInputError("missing_leg_strike", f"a {leg.right} leg requires a strike")
    return strike


def _leg_pricing_floats(
    typed_legs: tuple[OptionLeg, ...],
) -> tuple[tuple[float, str, float | None, float], ...]:
    """Validate every leg against the pricing model domain, as float64.

    :func:`scenario_grid` reprices option legs through the same BSM core as
    :func:`european_price`, so every leg passes the SAME domain gate before
    any pricing (fail-closed; P1 audit fix — a bare ``float(leg.strike)``
    used to bypass the ``inside_model_domain`` gate entirely):

    - CALL/PUT strike: finite in float64, strictly positive and
      ``<= SPOT_STRIKE_MAX`` — reason ``leg_strike_out_of_domain``;
    - premium: finite in float64, inside ``[0, SPOT_STRIKE_MAX]`` (price
      units, zero allowed) — reason ``leg_premium_out_of_domain``;
    - quantity and multiplier: representable as finite float64 (an
      overflowing value raises ``non_finite_input``, never a raw
      ``OverflowError``).

    A ``Decimal`` such as ``1e400`` is finite as a Decimal but overflows
    float64 to ``inf``; :func:`_to_float` rejects it with the typed reason
    ``non_finite_input`` instead of leaking a raw ``ValueError`` from the
    pricing core. Returns one ``(quantity*multiplier, right, strike,
    premium)`` float64 tuple per leg, in leg order.
    """
    static: list[tuple[float, str, float | None, float]] = []
    for i, leg in enumerate(typed_legs):
        prefix = f"legs[{i}]"
        if leg.right == "STOCK":
            strike_f: float | None = None
        else:
            strike_f = _to_float(_leg_strike(leg), f"{prefix}.strike")
            if strike_f <= 0.0 or strike_f > SPOT_STRIKE_MAX:
                raise OptionInputError(
                    "leg_strike_out_of_domain",
                    f"{prefix}.strike {strike_f!r} is outside the validated "
                    f"model domain (0, {SPOT_STRIKE_MAX:g}] shared with "
                    "options.european_price",
                )
        premium_f = _to_float(leg.premium, f"{prefix}.premium")
        if premium_f < 0.0 or premium_f > SPOT_STRIKE_MAX:
            raise OptionInputError(
                "leg_premium_out_of_domain",
                f"{prefix}.premium {premium_f!r} is outside the validated "
                f"domain [0, {SPOT_STRIKE_MAX:g}]",
            )
        qty_f = _to_float(leg.quantity, f"{prefix}.quantity")
        mult_f = _to_float(leg.multiplier, f"{prefix}.multiplier")
        static.append((qty_f * mult_f, leg.right, strike_f, premium_f))
    return tuple(static)


def _spot_to_exact_decimal(value: object, name: str) -> Decimal:
    """Convert a terminal spot to an EXACT Decimal (no rounding).

    ``Decimal(float)`` is the exact binary-to-decimal expansion, ``int`` is
    exact by construction, ``Decimal`` passes through. ``bool``, non-finite
    and negative values are rejected (a terminal spot may be exactly zero —
    the bankruptcy tail — but never negative).
    """
    if isinstance(value, bool):
        raise OptionInputError("invalid_type", f"{name} must be int, float or Decimal, got bool")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise OptionInputError("non_finite_input", f"{name} is a non-finite Decimal ({value})")
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise OptionInputError("non_finite_input", f"{name} is not finite ({value!r})")
        result = Decimal(value)  # exact binary expansion, no rounding
    else:
        raise OptionInputError(
            "invalid_type",
            f"{name} must be int, float or Decimal, got {type(value).__name__}",
        )
    if result < 0:
        raise OptionInputError("negative_terminal_spot", f"{name} must be >= 0, got {result}")
    return result


def payoff_at_expiry(
    legs: Sequence[OptionLeg],
    terminal_spot_grid: Sequence[NumberLike],
    fees: Decimal,
) -> tuple[Decimal, ...]:
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

    Gates: legs non-empty and typed; any structure containing a short
    quantity must be certified by :func:`defined_risk_check` (strict closed
    catalogue) — an uncertified structure raises
    ``undefined_risk_structure`` and is never priced, while strictly
    all-long structures pass without certification; every terminal spot
    finite and >= 0 (zero = bankruptcy tail); ``fees`` a finite
    non-negative ``Decimal`` instance (costs are declared, never
    defaulted).

    This formula describes expiry only; before expiry legs are repriced by
    :func:`scenario_grid`. Returns one exact ``Decimal`` P&L (money units of
    the declared premiums) per grid point, in grid order.
    """
    typed_legs = _require_legs(legs)
    _require_defined_risk_for_shorts(typed_legs, "options.payoff")
    if not isinstance(fees, Decimal) or isinstance(fees, bool):
        raise OptionInputError(
            "invalid_type",
            f"fees must be Decimal, got {type(fees).__name__}",
        )
    if not fees.is_finite():
        raise OptionInputError("non_finite_input", f"fees is a non-finite Decimal ({fees})")
    if fees < 0:
        raise OptionInputError(
            "negative_fees", f"fees must be >= 0 (positive declared costs), got {fees}"
        )
    grid_seq = _require_sequence(terminal_spot_grid, "terminal_spot_grid")
    if len(grid_seq) == 0:
        raise OptionInputError("empty_grid", "terminal_spot_grid must contain at least one spot")
    spots = [_spot_to_exact_decimal(v, f"terminal_spot_grid[{i}]") for i, v in enumerate(grid_seq)]
    zero = Decimal(0)
    results: list[Decimal] = []
    with localcontext() as ctx:
        ctx.prec = 60
        for spot_t in spots:
            total = zero
            for leg in typed_legs:
                if leg.right == "CALL":
                    intrinsic = spot_t - _leg_strike(leg)
                    if intrinsic < 0:
                        intrinsic = zero
                elif leg.right == "PUT":
                    intrinsic = _leg_strike(leg) - spot_t
                    if intrinsic < 0:
                        intrinsic = zero
                else:  # STOCK
                    intrinsic = spot_t
                total += Decimal(leg.quantity) * Decimal(leg.multiplier) * (intrinsic - leg.premium)
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
    iv_scenarios: Sequence[Sequence[NumberLike | None]],
    rate: NumberLike,
    dividend_yield: NumberLike,
) -> tuple[tuple[tuple[float, ...], ...], ...]:
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

    Gates: leg/domain gates as elsewhere; any structure containing a short
    quantity must be certified by :func:`defined_risk_check` (strict closed
    catalogue) — an uncertified structure raises
    ``undefined_risk_structure`` before any pricing, all-long structures
    pass without certification; every leg strike and premium is
    validated against the SAME model domain as :func:`european_price`
    before any pricing (``leg_strike_out_of_domain`` /
    ``leg_premium_out_of_domain`` / ``non_finite_input``, fail-closed —
    never a silent out-of-domain repricing); every spot strictly positive
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
    _require_defined_risk_for_shorts(typed_legs, "options.scenario_grid")
    r = _require_rate(rate, "rate")
    q = _require_rate(dividend_yield, "dividend_yield")
    spot_seq = _require_sequence(spot_grid, "spot_grid")
    if len(spot_seq) == 0:
        raise OptionInputError("empty_grid", "spot_grid must not be empty")
    spots = [_require_price_positive(v, f"spot_grid[{i}]") for i, v in enumerate(spot_seq)]
    time_seq = _require_sequence(time_grid_years, "time_grid_years")
    if len(time_seq) == 0:
        raise OptionInputError("empty_grid", "time_grid_years must not be empty")
    times = [_require_maturity(v, f"time_grid_years[{i}]") for i, v in enumerate(time_seq)]
    scen_seq = _require_sequence(iv_scenarios, "iv_scenarios")
    if len(scen_seq) == 0:
        raise OptionInputError("empty_grid", "iv_scenarios must not be empty")
    scenarios: list[list[float | None]] = []
    for si, scenario in enumerate(scen_seq):
        vol_seq = _require_sequence(scenario, f"iv_scenarios[{si}]")
        if len(vol_seq) != len(typed_legs):
            raise OptionInputError(
                "scenario_leg_mismatch",
                f"iv_scenarios[{si}] has {len(vol_seq)} entries for "
                f"{len(typed_legs)} legs; one volatility (or None for STOCK) "
                "per leg is required",
            )
        vols: list[float | None] = []
        for li, (leg, vol_entry) in enumerate(zip(typed_legs, vol_seq, strict=True)):
            if leg.right == "STOCK":
                if vol_entry is not None:
                    raise OptionInputError(
                        "stock_leg_volatility",
                        f"iv_scenarios[{si}][{li}] must be None for a STOCK leg, got {vol_entry!r}",
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
                vols.append(_require_volatility(vol_entry, f"iv_scenarios[{si}][{li}]"))
        scenarios.append(vols)

    leg_static = _leg_pricing_floats(typed_legs)
    grid: list[tuple[tuple[float, ...], ...]] = []
    for vols in scenarios:
        time_rows: list[tuple[float, ...]] = []
        for t in times:
            spot_row: list[float] = []
            for s in spots:
                total = 0.0
                for (qty_mult, leg_right, leg_strike, leg_premium), vol in zip(
                    leg_static, vols, strict=True
                ):
                    if leg_right == "STOCK":
                        value = s
                    else:
                        # STOCK <=> strike et volatilité absents (garanti
                        # par `_leg_pricing_floats` et par la validation de
                        # `iv_scenarios` plus haut) : cette branche a
                        # toujours les deux.
                        assert leg_strike is not None  # noqa: S101
                        assert vol is not None  # noqa: S101
                        value = _bsm_price_core(s, leg_strike, t, r, q, vol, leg_right)
                    total += qty_mult * (value - leg_premium)
                spot_row.append(_finite_result(total, "options.scenario_grid"))
            time_rows.append(tuple(spot_row))
        grid.append(tuple(time_rows))
    return tuple(grid)


# ---------------------------------------------------------------------------
# Defined-risk certification (tail analysis)
# ---------------------------------------------------------------------------


class DefinedRiskResult(ContractModel):
    """Outcome of the defined-risk certification (strict, frozen).

    ``is_defined_risk`` is the verdict; ``reason_code`` is the stable
    machine-readable code; ``detail`` is the human-readable justification
    (for an accepted structure it names the recognized catalogue member).

    Codes:

    - ``DEFINED_RISK`` — accepted; the structure is an exact member of the
      closed catalogue AND both tails are covered;
    - ``UNCOVERED_SHORT_UPSIDE_TAIL`` / ``UNCOVERED_SHORT_DOWNSIDE_TAIL``
      — rejected by the tail guard (unbounded or uncovered loss);
    - ``CREDIT_VERTICAL_NOT_VALIDATED`` — a credit-shaped vertical, refused
      until a separate credit profile is formally validated;
    - ``VERTICAL_DEBIT_NOT_POSITIVE`` — debit-shaped vertical with
      ``D <= 0`` (hidden credit / incoherent quotes);
    - ``VERTICAL_DEBIT_NOT_BELOW_WIDTH`` — debit vertical with
      ``D >= W*M`` (incoherent quotes);
    - ``VERTICAL_LEGS_NOT_PAIRED`` — two same-right legs whose quantities,
      multipliers or strikes do not form one exact K1<K2 pairing;
    - ``OUTSIDE_CLOSED_CATALOG`` — any other structure containing a short
      quantity (covered call, broken wing, ratio/combination not reducible
      to a catalogue member), refused until a dedicated profile exists.
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


_CLOSED_CATALOG = (
    "BULL_CALL_DEBIT",
    "BEAR_PUT_DEBIT",
    "LONG_STRADDLE",
    "LONG_STRANGLE",
    "ALL_LONG",
)
"""The documented closed catalogue of certifiable structures (spec:
OPTIONS_PRICING_AND_SCENARIOS.md, « Stratégies multi-jambes à risque
défini »). ``ALL_LONG`` covers every structure whose legs are strictly
long — single long CALL/PUT, long STOCK, and any all-long combination
(straddle and strangle are named members of that family)."""


def _classify_all_long(typed_legs: tuple[OptionLeg, ...]) -> str:
    """Name an all-long structure: LONG_STRADDLE, LONG_STRANGLE or ALL_LONG.

    A straddle is one long CALL plus one long PUT at the SAME strike, same
    quantity and multiplier; a strangle is the same pairing with the PUT
    strike strictly below the CALL strike. Every other all-long structure
    (single legs, long stock, other combinations) is the generic ALL_LONG
    member. The label only refines ``detail``; acceptance is identical.
    """
    if len(typed_legs) == 2:
        calls = [leg for leg in typed_legs if leg.right == "CALL"]
        puts = [leg for leg in typed_legs if leg.right == "PUT"]
        if len(calls) == 1 and len(puts) == 1:
            call, put = calls[0], puts[0]
            if call.quantity == put.quantity and call.multiplier == put.multiplier:
                call_k, put_k = _leg_strike(call), _leg_strike(put)
                if call_k == put_k:
                    return "LONG_STRADDLE"
                if put_k < call_k:
                    return "LONG_STRANGLE"
    return "ALL_LONG"


def _reject(reason_code: str, detail: str) -> DefinedRiskResult:
    return DefinedRiskResult(is_defined_risk=False, reason_code=reason_code, detail=detail)


def defined_risk_check(legs: Sequence[OptionLeg]) -> DefinedRiskResult:
    """Certify a declared structure by STRICT closed-catalogue recognition.

    Acceptance criterion (spec: « Stratégies multi-jambes à risque défini »):
    the structure must be recognized as an EXACT member of the closed
    catalogue :data:`_CLOSED_CATALOG` — nothing else is certified, even
    when its expiry tails happen to be covered:

    - ``BULL_CALL_DEBIT``: long CALL at ``K1`` paired 1:1 (same absolute
      quantity, same multiplier) with a short CALL at ``K2``, ``K1 < K2``,
      per-unit net debit ``d = p_long - p_short`` with ``0 < d < W`` where
      ``W = K2 - K1`` (equivalently ``0 < D < W*M`` per paired contract);
    - ``BEAR_PUT_DEBIT``: long PUT at ``K2`` paired 1:1 with a short PUT at
      ``K1``, ``K1 < K2``, same debit conditions;
    - ``LONG_STRADDLE`` / ``LONG_STRANGLE`` and every other strictly
      all-long structure (``ALL_LONG``): every leg quantity > 0 — STOCK
      legs are only ever accepted long; maximum loss is the premium paid.

    Everything else is REJECTED with an explicit reason: any residual short
    quantity (naked shorts, ratios — also caught by the tail guard), credit
    verticals (``CREDIT_VERTICAL_NOT_VALIDATED``), incoherent debit quotes
    (``VERTICAL_DEBIT_NOT_POSITIVE`` for ``D <= 0``,
    ``VERTICAL_DEBIT_NOT_BELOW_WIDTH`` for ``D >= W*M``), unpaired legs
    (``VERTICAL_LEGS_NOT_PAIRED``) and every other short-containing
    combination — covered call, broken-wing butterfly, ratio or unknown
    combination — as ``OUTSIDE_CLOSED_CATALOG``, until a dedicated profile
    is formally validated. Calendars and diagonals cannot even be expressed
    with :class:`OptionLeg` (single shared expiry by construction).

    The expiry tail analysis (net multiplier-weighted CALL+STOCK quantity
    on ``S -> inf`` >= 0, net PUT quantity on ``S -> 0`` >= 0) remains a
    SECONDARY safeguard evaluated first: it rejects unbounded structures
    with the historical ``UNCOVERED_SHORT_*_TAIL`` codes, but passing it
    never certifies anything — catalogue recognition does.

    Premise (caller's responsibility, as for :func:`payoff_at_expiry`):
    all legs share the same underlying, currency and expiry. This is an
    analytic certification of a manually declared structure; it neither
    creates nor implies any transaction.
    """
    typed_legs = _require_legs(legs)

    # --- Secondary tail guard (never the acceptance criterion) ------------
    upside = 0
    downside_puts = 0
    for leg in typed_legs:
        weight = leg.quantity * leg.multiplier
        if leg.right in ("CALL", "STOCK"):
            upside += weight
        else:
            downside_puts += weight
    if upside < 0:
        return _reject(
            "UNCOVERED_SHORT_UPSIDE_TAIL",
            "net multiplier-weighted CALL+STOCK quantity on the S->inf "
            f"tail is {upside} < 0: unbounded loss, structure rejected",
        )
    if downside_puts < 0:
        return _reject(
            "UNCOVERED_SHORT_DOWNSIDE_TAIL",
            "net multiplier-weighted PUT quantity on the S->0 tail is "
            f"{downside_puts} < 0: uncovered short puts, structure rejected",
        )

    # --- Strict closed-catalogue recognition (the acceptance criterion) ---
    short_legs = [leg for leg in typed_legs if leg.quantity < 0]
    if not short_legs:
        structure = _classify_all_long(typed_legs)
        return DefinedRiskResult(
            is_defined_risk=True,
            reason_code="DEFINED_RISK",
            detail=(
                f"{structure}: all {len(typed_legs)} leg(s) strictly long; "
                "maximum loss is the declared premium paid (tail guard: net "
                f"CALL+STOCK {upside} >= 0, net PUT {downside_puts} >= 0)"
            ),
        )

    # A short quantity is only certifiable inside one of the two debit
    # verticals: exactly two same-right option legs paired 1:1.
    catalogue_msg = (
        "the closed catalogue only certifies BULL_CALL_DEBIT, "
        "BEAR_PUT_DEBIT, LONG_STRADDLE/LONG_STRANGLE and all-long "
        "structures; every other short-containing structure (covered "
        "call, broken wing, ratio, credit or unknown combination) is "
        "refused until a dedicated profile is validated"
    )
    if len(typed_legs) != 2:
        return _reject(
            "OUTSIDE_CLOSED_CATALOG",
            f"{len(typed_legs)} legs with {len(short_legs)} short leg(s) do "
            f"not form a recognized debit vertical; {catalogue_msg}",
        )
    if any(leg.right == "STOCK" for leg in typed_legs):
        return _reject(
            "OUTSIDE_CLOSED_CATALOG",
            "a STOCK leg combined with a short option leg (e.g. a covered "
            f"call) is not a catalogue member; {catalogue_msg}",
        )
    first, second = typed_legs
    if first.right != second.right:
        return _reject(
            "OUTSIDE_CLOSED_CATALOG",
            "two option legs of different rights with a short quantity do "
            f"not form a debit vertical; {catalogue_msg}",
        )
    long_leg = first if first.quantity > 0 else second
    short_leg = second if first.quantity > 0 else first
    if long_leg.quantity <= 0 or short_leg.quantity >= 0:
        # Both legs short: already rejected by the tail guard above; kept
        # fail-closed against any future reordering.
        return _reject(
            "OUTSIDE_CLOSED_CATALOG",
            f"no long leg available to pair the short leg; {catalogue_msg}",
        )
    if long_leg.quantity != -short_leg.quantity:
        return _reject(
            "VERTICAL_LEGS_NOT_PAIRED",
            f"quantities are not paired 1:1 (long {long_leg.quantity}, "
            f"short {short_leg.quantity}); a debit vertical requires the "
            "same absolute quantity on both legs",
        )
    if long_leg.multiplier != short_leg.multiplier:
        return _reject(
            "VERTICAL_LEGS_NOT_PAIRED",
            f"multipliers differ (long {long_leg.multiplier}, short "
            f"{short_leg.multiplier}); a debit vertical requires one shared "
            "multiplier",
        )
    if long_leg.strike == short_leg.strike:
        return _reject(
            "VERTICAL_LEGS_NOT_PAIRED",
            f"both legs share strike {long_leg.strike}; a debit vertical "
            "requires two distinct strikes K1 < K2",
        )
    right = long_leg.right
    long_k, short_k = _leg_strike(long_leg), _leg_strike(short_leg)
    debit_shape = long_k < short_k if right == "CALL" else long_k > short_k
    if not debit_shape:
        return _reject(
            "CREDIT_VERTICAL_NOT_VALIDATED",
            f"the long {right} sits at the credit side of the spread (long "
            f"K={long_leg.strike}, short K={short_leg.strike}): this is a "
            "credit vertical, refused until the formal proof and separate "
            "credit profile required by the specification are validated",
        )
    width = abs(short_k - long_k)  # W, price units
    net_debit = long_leg.premium - short_leg.premium  # D/M per unit
    if net_debit <= 0:
        return _reject(
            "VERTICAL_DEBIT_NOT_POSITIVE",
            f"per-unit net debit {net_debit} <= 0 for a debit-shaped "
            "vertical: hidden credit or incoherent declared quotes; the "
            "structure is rejected, never repaired",
        )
    if net_debit >= width:
        return _reject(
            "VERTICAL_DEBIT_NOT_BELOW_WIDTH",
            f"per-unit net debit {net_debit} >= width {width} (D >= W*M): "
            "incoherent declared quotes for a debit vertical; rejected",
        )
    structure = "BULL_CALL_DEBIT" if right == "CALL" else "BEAR_PUT_DEBIT"
    pairs = long_leg.quantity
    mult = long_leg.multiplier
    return DefinedRiskResult(
        is_defined_risk=True,
        reason_code="DEFINED_RISK",
        detail=(
            f"{structure}: {pairs} pair(s) long K={long_leg.strike} / short "
            f"K={short_leg.strike}, multiplier {mult}; per-unit debit "
            f"{net_debit} in (0, {width}); max loss D="
            f"{net_debit * mult * pairs}, max gain "
            f"{(width - net_debit) * mult * pairs} before declared costs "
            f"(tail guard: net CALL+STOCK {upside} >= 0, net PUT "
            f"{downside_puts} >= 0)"
        ),
    )
