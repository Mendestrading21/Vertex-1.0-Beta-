"""Differential oracle tests for options.european_price and options.greeks.

Three INDEPENDENT implementations must agree on a synthetic grid:

1. ``vertex_core.calculations.options.european_price`` (math.erf closed form);
2. QuantLib ``AnalyticEuropeanEngine`` on identical flat curves (ACT/365F);
3. a scipy.stats.norm reference implementation written IN THIS TEST.

Tolerance: ``1e-9`` absolute or ``1e-7`` relative, whichever is larger.
All fixtures are SYNTHETIC; no network, no real market data, no orders.
"""

import math

import pytest
import QuantLib as ql
from scipy.stats import norm

from vertex_core.calculations.options import european_price, greeks

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
        ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(ANCHOR, calendar, vol, day_count)
        ),
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
                            reference = scipy_reference_price(
                                SPOT, k, t, r, q, vol, right
                            )
                            ql_price = quantlib_european(
                                SPOT, k, days, r, q, vol, right
                            ).NPV()
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
        assert checked == len(MATURITY_DAYS) * len(MONEYNESS) * len(VOLS) * len(
            RATES
        ) * len(YIELDS)


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
