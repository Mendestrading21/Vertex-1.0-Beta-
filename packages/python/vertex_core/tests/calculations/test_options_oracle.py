"""Differential oracle tests for options.european_price, options.greeks
and options.american_price.

European price — three INDEPENDENT implementations must agree on a grid:

1. ``vertex_core.calculations.options.european_price`` (math.erf closed form);
2. QuantLib ``AnalyticEuropeanEngine`` on identical flat curves (ACT/365F);
3. a scipy.stats.norm reference implementation written IN THIS TEST.

Tolerance: ``1e-9`` absolute or ``1e-7`` relative, whichever is larger.

American price — the runtime finite-difference engine (registry reference
``QuantLib_finite_difference``) is checked against (a) an INDEPENDENT
second numerical method (QuantLib binomial CRR at 800 steps, built in this
test), (b) the ``american >= european`` invariant, (c) golden vectors for
the American put with documented derivation, (d) the exercise boundary
(very ITM short-dated put ~ intrinsic value).

All fixtures are SYNTHETIC; no network, no real market data, no orders.
"""

import math

import pytest
import QuantLib as ql
from scipy.stats import norm

from vertex_core.calculations.options import american_price, european_price, greeks

pytestmark = pytest.mark.oracle

ANCHOR = ql.Date(2, 1, 2026)

# Maturities expressed in exact ACT/365F days so the date-based QuantLib
# leg of the oracle prices the exact same year fraction as the analytic
# implementations (T = days / 365).
MATURITY_DAYS = [4, 30, 91, 182, 365, 1095]  # 0.011 .. 3.0 years
MONEYNESS = [0.5, 0.8, 1.0, 1.2, 2.0]
VOLS = [0.05, 0.2, 0.5, 1.5]
RATES = [-0.01, 0.0, 0.03, 0.08]
YIELDS = [0.0, 0.02, 0.05]
SPOT = 100.0


def scipy_reference_price(s, k, t, r, q, vol, right):
    """Independent BSM reference using scipy.stats.norm (test-only oracle)."""
    if t == 0.0:
        intrinsic = s - k if right == "CALL" else k - s
        return max(intrinsic, 0.0)
    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    if vol == 0.0:
        det = s * df_q - k * df_r if right == "CALL" else k * df_r - s * df_q
        return max(det, 0.0)
    sqrt_t = math.sqrt(t)
    d1 = (math.log(s / k) + (r - q + 0.5 * vol * vol) * t) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t
    if right == "CALL":
        return s * df_q * float(norm.cdf(d1)) - k * df_r * float(norm.cdf(d2))
    return k * df_r * float(norm.cdf(-d2)) - s * df_q * float(norm.cdf(-d1))


def quantlib_european(s, k, days, r, q, vol, right):
    """QuantLib AnalyticEuropeanEngine on flat ACT/365F curves (test oracle)."""
    ql.Settings.instance().evaluationDate = ANCHOR
    day_count = ql.Actual365Fixed()
    calendar = ql.NullCalendar()
    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(s)),
        ql.YieldTermStructureHandle(ql.FlatForward(ANCHOR, q, day_count)),
        ql.YieldTermStructureHandle(ql.FlatForward(ANCHOR, r, day_count)),
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(ANCHOR, calendar, vol, day_count)),
    )
    ql_right = ql.Option.Call if right == "CALL" else ql.Option.Put
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(ql_right, k),
        ql.EuropeanExercise(ANCHOR + days),
    )
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
    return option


def within_oracle_tolerance(a, b):
    return abs(a - b) <= max(1e-9, 1e-7 * max(abs(a), abs(b)))


class TestEuropeanPriceThreeWayOracle:
    @pytest.mark.parametrize("right", ["CALL", "PUT"])
    def test_full_grid_three_implementations_agree(self, right):
        checked = 0
        for days in MATURITY_DAYS:
            t = days / 365.0
            for m in MONEYNESS:
                k = SPOT * m
                for vol in VOLS:
                    for r in RATES:
                        for q in YIELDS:
                            vertex = european_price(SPOT, k, t, r, q, vol, right)
                            reference = scipy_reference_price(SPOT, k, t, r, q, vol, right)
                            ql_price = quantlib_european(SPOT, k, days, r, q, vol, right).NPV()
                            assert within_oracle_tolerance(vertex, reference), (
                                f"vertex vs scipy diverge: right={right} T={t} "
                                f"K={k} vol={vol} r={r} q={q}: "
                                f"{vertex!r} vs {reference!r}"
                            )
                            assert within_oracle_tolerance(vertex, ql_price), (
                                f"vertex vs QuantLib diverge: right={right} "
                                f"T={t} K={k} vol={vol} r={r} q={q}: "
                                f"{vertex!r} vs {ql_price!r}"
                            )
                            checked += 1
        # Guard against a silently empty grid.
        assert checked == len(MATURITY_DAYS) * len(MONEYNESS) * len(VOLS) * len(RATES) * len(YIELDS)


def _american_process(s, r, q, vol):
    ql.Settings.instance().evaluationDate = ANCHOR
    day_count = ql.Actual365Fixed()
    calendar = ql.NullCalendar()
    return ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(s)),
        ql.YieldTermStructureHandle(ql.FlatForward(ANCHOR, q, day_count)),
        ql.YieldTermStructureHandle(ql.FlatForward(ANCHOR, r, day_count)),
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(ANCHOR, calendar, vol, day_count)),
    )


def _american_option(k, days, right):
    ql_right = ql.Option.Call if right == "CALL" else ql.Option.Put
    return ql.VanillaOption(
        ql.PlainVanillaPayoff(ql_right, k),
        ql.AmericanExercise(ANCHOR, ANCHOR + days),
    )


def quantlib_american_fd(s, k, days, r, q, vol, right, grid=800):
    """Independent construction of the registry engine (finite difference)."""
    option = _american_option(k, days, right)
    option.setPricingEngine(
        ql.FdBlackScholesVanillaEngine(_american_process(s, r, q, vol), grid, grid, 0)
    )
    return option.NPV()


def quantlib_american_crr(s, k, days, r, q, vol, right, steps=800):
    """SECOND independent numerical method: binomial CRR tree (test oracle)."""
    option = _american_option(k, days, right)
    option.setPricingEngine(ql.BinomialVanillaEngine(_american_process(s, r, q, vol), "crr", steps))
    return option.NPV()


# Cross-method tolerance |FD_800x800 - CRR_800| observed <= ~2.5e-3 on the
# domain below (spot scale ~100 and ~40); 5e-3 is the documented envelope.
CROSS_METHOD_TOL = 5e-3

AMERICAN_GRID = [
    # (spot, strike, days, rate, dividend_yield, volatility, right)
    (100.0, 100.0, 365, 0.05, 0.00, 0.2, "PUT"),
    (100.0, 120.0, 182, 0.03, 0.00, 0.4, "PUT"),
    (100.0, 80.0, 365, 0.08, 0.00, 0.3, "PUT"),
    (100.0, 100.0, 30, -0.01, 0.02, 0.25, "PUT"),
    (100.0, 90.0, 365, 0.03, 0.05, 0.25, "CALL"),
    (100.0, 110.0, 730, 0.05, 0.02, 0.35, "CALL"),
    (40.0, 40.0, 365, 0.06, 0.00, 0.2, "PUT"),
    (36.0, 40.0, 730, 0.06, 0.00, 0.4, "PUT"),
]

# Golden vectors for the American PUT (registry method QuantLib finite
# difference). DERIVATION (independent recomputation, cited per the
# validation spec): each expected value is the stable 4-decimal rounding of
# TWO independent QuantLib engines run at high resolution on the EXACT
# runtime date grid (flat ACT/365F curves, anchor + days, constant vol):
# FdBlackScholesVanillaEngine tGrid=xGrid=4000 and BinomialVanillaEngine
# "crr" 8001 steps, which agree within 8e-4 on every vector. Literature
# cross-checks: the S=36 K=40 r=0.06 q=0 vol=0.2 T=1 American put is the
# classic Longstaff & Schwartz (2001, Table 1) case whose accurate
# finite-difference benchmark value is 4.48637; the S=K=100 r=0.05 q=0
# vol=0.2 T=1 American put is the textbook example commonly quoted ~6.090.
# Assertion tolerance 2e-3 absolute covers the documented discretization
# error of both 800-resolution engines against these converged values.
GOLDEN_TOL = 2e-3
AMERICAN_PUT_GOLDEN = [
    # (spot, strike, days, rate, volatility, expected)
    (100.0, 100.0, 365, 0.05, 0.2, 6.0901),
    (36.0, 40.0, 365, 0.06, 0.2, 4.4866),
    (36.0, 40.0, 730, 0.06, 0.2, 4.8482),
    (36.0, 40.0, 365, 0.06, 0.4, 7.1089),
    (40.0, 40.0, 365, 0.06, 0.2, 2.3195),
]


class TestAmericanPriceOracle:
    def test_runtime_engine_is_registry_finite_difference(self):
        # Registry conformance (P1-4 reproducer): CALCULATION_REGISTRY.yaml
        # declares reference QuantLib_finite_difference for
        # options.american_price; the runtime price must match an
        # INDEPENDENTLY constructed FdBlackScholesVanillaEngine on the same
        # date grid to numerical identity (the old binomial-CRR runtime
        # diverged from this by ~1e-4..1e-3).
        for s, k, days, r, q, vol, right in AMERICAN_GRID:
            t = days / 365.0
            runtime = american_price(s, k, t, r, q, vol, right, steps=800)
            fd = quantlib_american_fd(s, k, days, r, q, vol, right, grid=800)
            assert runtime == pytest.approx(fd, abs=1e-10), (
                f"runtime is not the registry finite-difference method: "
                f"S={s} K={k} d={days} r={r} q={q} vol={vol} {right}: "
                f"{runtime!r} vs {fd!r}"
            )

    def test_crr_second_numerical_method_agrees(self):
        # (a) Independent SECOND numerical method: binomial CRR at 800
        # steps, built in this test, must agree within the documented
        # cross-method envelope on the whole grid.
        for s, k, days, r, q, vol, right in AMERICAN_GRID:
            t = days / 365.0
            runtime = american_price(s, k, t, r, q, vol, right, steps=800)
            crr = quantlib_american_crr(s, k, days, r, q, vol, right, steps=800)
            assert abs(runtime - crr) <= CROSS_METHOD_TOL, (
                f"FD runtime vs CRR oracle diverge: S={s} K={k} d={days} "
                f"r={r} q={q} vol={vol} {right}: {runtime!r} vs {crr!r}"
            )

    def test_american_not_below_european_invariant(self):
        # (b) Registry invariant american_not_below_european, and never
        # below intrinsic (early exercise), on the whole grid.
        for s, k, days, r, q, vol, right in AMERICAN_GRID:
            t = days / 365.0
            am = american_price(s, k, t, r, q, vol, right, steps=800)
            eu = european_price(s, k, t, r, q, vol, right)
            intrinsic = max(s - k, 0.0) if right == "CALL" else max(k - s, 0.0)
            assert am >= eu - 1e-3 * s
            assert am >= intrinsic - 1e-3 * s

    def test_golden_vectors_literature_american_put(self):
        # (c) Golden vectors with documented derivation (see comment above
        # AMERICAN_PUT_GOLDEN). Both the runtime finite-difference engine
        # AND the in-test CRR second method must reproduce every golden
        # value within the documented tolerance.
        for s, k, days, r, vol, expected in AMERICAN_PUT_GOLDEN:
            t = days / 365.0
            runtime = american_price(s, k, t, r, 0.0, vol, "PUT", steps=800)
            crr = quantlib_american_crr(s, k, days, r, 0.0, vol, "PUT", steps=800)
            assert runtime == pytest.approx(expected, abs=GOLDEN_TOL), (
                f"golden vector failed (runtime FD): S={s} K={k} d={days} "
                f"r={r} vol={vol}: got {runtime!r}, expected {expected!r}"
            )
            assert crr == pytest.approx(expected, abs=GOLDEN_TOL), (
                f"golden vector failed (CRR oracle): S={s} K={k} d={days} "
                f"r={r} vol={vol}: got {crr!r}, expected {expected!r}"
            )

    def test_near_exercise_boundary_very_itm_put_is_intrinsic(self):
        # (d) Near the exercise boundary: a very ITM short-dated American
        # put sits in the immediate-exercise region, so its value is the
        # intrinsic value (K - S) exactly at engine resolution, and never
        # below it. The European equivalent is strictly smaller (discount).
        for s, k, days, vol in [(50.0, 100.0, 1, 0.3), (80.0, 100.0, 5, 0.3)]:
            t = days / 365.0
            intrinsic = k - s
            am = american_price(s, k, t, 0.05, 0.0, vol, "PUT", steps=800)
            eu = european_price(s, k, t, 0.05, 0.0, vol, "PUT")
            assert am == pytest.approx(intrinsic, abs=1e-9)
            assert am >= intrinsic - 1e-9
            assert eu < intrinsic


class TestGreeksQuantLibOracle:
    @pytest.mark.parametrize("right", ["CALL", "PUT"])
    @pytest.mark.parametrize("days", [30, 182, 365])
    @pytest.mark.parametrize("moneyness", [0.8, 1.0, 1.25])
    @pytest.mark.parametrize("vol", [0.15, 0.45])
    def test_greeks_match_quantlib_analytic(self, right, days, moneyness, vol):
        t = days / 365.0
        k = SPOT * moneyness
        r, q = 0.03, 0.01
        ours = greeks(SPOT, k, t, r, q, vol, right)
        option = quantlib_european(SPOT, k, days, r, q, vol, right)
        assert ours.delta == pytest.approx(option.delta(), abs=1e-9)
        assert ours.gamma == pytest.approx(option.gamma(), abs=1e-9)
        # QuantLib vega/rho are raw per +1.0 change, theta raw per year of
        # elapsing calendar time — the same conventions as GreeksResult.
        assert ours.vega == pytest.approx(option.vega(), rel=1e-9, abs=1e-9)
        assert ours.theta == pytest.approx(option.theta(), rel=1e-9, abs=1e-9)
        assert ours.rho == pytest.approx(option.rho(), rel=1e-9, abs=1e-9)
