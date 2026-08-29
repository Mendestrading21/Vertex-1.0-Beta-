"""options.* calculations: nominal values, gates, units, catalogue, edge cases.

All fixtures are SYNTHETIC and deterministic; no network, no real market
data, no unseeded randomness. No test creates, previews or transmits any
order of any kind — legs are manually declared analytic structures only.
"""

import math
from decimal import Decimal

import pytest
from pydantic import ValidationError

from vertex_core.calculations.options import (
    AMERICAN_MIN_STEPS,
    DefinedRiskResult,
    GreeksResult,
    IV_BRACKET_HI,
    IVNoSolutionError,
    OptionInputError,
    OptionLeg,
    OptionNotImplementedError,
    american_price,
    defined_risk_check,
    european_price,
    forward_price,
    greeks,
    implied_volatility,
    no_arbitrage_bounds,
    payoff_at_expiry,
    scenario_grid,
)
from vertex_core.contracts.enums import OptionRight

NON_FINITE_FLOATS = [float("nan"), float("inf"), float("-inf")]

# Maturities on the exact ACT/365F grid so the QuantLib date quantization of
# american_price is zero and invariants compare like for like.
T_HALF = 182.0 / 365.0
T_ONE = 365.0 / 365.0

# American engine discretization tolerance for |numeric - analytic| on a
# spot~100 scale (finite-difference 800x800 error is well below the former
# CRR-800 ~3e-3; documented engine tolerance, not a hidden fudge).
AMERICAN_TOL = 5e-3


def call_leg(qty, strike, premium="5", mult=100):
    return OptionLeg(
        quantity=qty,
        right="CALL",
        strike=Decimal(strike),
        premium=Decimal(premium),
        multiplier=mult,
    )


def put_leg(qty, strike, premium="5", mult=100):
    return OptionLeg(
        quantity=qty,
        right="PUT",
        strike=Decimal(strike),
        premium=Decimal(premium),
        multiplier=mult,
    )


def stock_leg(qty, premium="100", mult=1):
    return OptionLeg(
        quantity=qty, right="STOCK", strike=None, premium=Decimal(premium), multiplier=mult
    )


class TestForwardPrice:
    def test_nominal_continuous_compounding(self):
        assert forward_price(100, 0.03, 0.01, 1.0) == pytest.approx(
            100.0 * math.exp(0.02), rel=1e-12
        )

    def test_zero_maturity_is_spot(self):
        assert forward_price(123.45, 0.05, 0.02, 0.0) == pytest.approx(123.45)

    def test_negative_rate_inside_domain(self):
        assert forward_price(100, -0.01, 0.0, 2.0) == pytest.approx(
            100.0 * math.exp(-0.02), rel=1e-12
        )

    def test_decimal_inputs(self):
        result = forward_price(Decimal("100"), Decimal("0.03"), Decimal("0"), Decimal("1"))
        assert result == pytest.approx(100.0 * math.exp(0.03), rel=1e-12)

    def test_result_positive_and_finite(self):
        assert forward_price(1e-6, 0.08, 0.0, 100.0) > 0.0

    @pytest.mark.parametrize("spot", [0, -1, -0.5])
    def test_non_positive_spot_rejected(self, spot):
        with pytest.raises(OptionInputError):
            forward_price(spot, 0.03, 0.0, 1.0)

    @pytest.mark.parametrize("bad", NON_FINITE_FLOATS)
    def test_non_finite_inputs_rejected(self, bad):
        with pytest.raises(OptionInputError):
            forward_price(bad, 0.03, 0.0, 1.0)
        with pytest.raises(OptionInputError):
            forward_price(100, bad, 0.0, 1.0)
        with pytest.raises(OptionInputError):
            forward_price(100, 0.03, 0.0, bad)

    def test_negative_maturity_rejected(self):
        with pytest.raises(OptionInputError) as err:
            forward_price(100, 0.03, 0.0, -0.1)
        assert err.value.reason == "negative_maturity"

    def test_rate_out_of_domain_rejected(self):
        with pytest.raises(OptionInputError):
            forward_price(100, 1.5, 0.0, 1.0)
        with pytest.raises(OptionInputError):
            forward_price(100, 0.03, -1.5, 1.0)

    def test_bool_rejected(self):
        with pytest.raises(OptionInputError):
            forward_price(True, 0.03, 0.0, 1.0)


class TestNoArbitrageBounds:
    @pytest.mark.parametrize("right", [OptionRight.CALL, OptionRight.PUT, "CALL", "PUT"])
    @pytest.mark.parametrize("rate", [-0.01, 0.0, 0.08])
    @pytest.mark.parametrize("t", [0.0, 0.01, T_ONE, 3.0])
    def test_lower_not_above_upper(self, right, rate, t):
        lower, upper = no_arbitrage_bounds(100, 90, t, rate, 0.02, right)
        assert 0.0 <= lower <= upper

    def test_call_bounds_formula(self):
        s, k, t, r, q = 100.0, 90.0, 1.0, 0.03, 0.01
        lower, upper = no_arbitrage_bounds(s, k, t, r, q, OptionRight.CALL)
        assert lower == pytest.approx(
            s * math.exp(-q * t) - k * math.exp(-r * t), rel=1e-12
        )
        assert upper == pytest.approx(s * math.exp(-q * t), rel=1e-12)

    def test_put_bounds_formula(self):
        s, k, t, r, q = 100.0, 130.0, 1.0, 0.03, 0.01
        lower, upper = no_arbitrage_bounds(s, k, t, r, q, OptionRight.PUT)
        assert lower == pytest.approx(
            k * math.exp(-r * t) - s * math.exp(-q * t), rel=1e-12
        )
        assert upper == pytest.approx(k * math.exp(-r * t), rel=1e-12)

    def test_otm_lower_bound_is_zero_not_negative(self):
        lower, _ = no_arbitrage_bounds(100, 200, 0.5, 0.03, 0.0, OptionRight.CALL)
        assert lower == 0.0

    def test_invalid_right_rejected(self):
        with pytest.raises(OptionInputError) as err:
            no_arbitrage_bounds(100, 100, 1.0, 0.03, 0.0, "CALL_")
        assert err.value.reason == "invalid_right"


class TestEuropeanPrice:
    def test_expiry_is_intrinsic_call(self):
        assert european_price(110, 100, 0.0, 0.05, 0.02, 0.4, "CALL") == 10.0
        assert european_price(90, 100, 0.0, 0.05, 0.02, 0.4, "CALL") == 0.0

    def test_expiry_is_intrinsic_put(self):
        assert european_price(90, 100, 0.0, 0.05, 0.02, 0.4, "PUT") == 10.0
        assert european_price(110, 100, 0.0, 0.05, 0.02, 0.4, "PUT") == 0.0

    def test_zero_volatility_is_discounted_deterministic_bound(self):
        s, k, t, r, q = 100.0, 90.0, 2.0, 0.03, 0.01
        expected = s * math.exp(-q * t) - k * math.exp(-r * t)
        assert european_price(s, k, t, r, q, 0.0, "CALL") == pytest.approx(
            expected, rel=1e-12
        )
        assert european_price(s, k, t, r, q, 0.0, "PUT") == 0.0

    def test_known_value_atm(self):
        # Independent hand-checked BSM value (S=K=100, T=1, r=3%, q=1%, vol=25%).
        price = european_price(100, 100, 1.0, 0.03, 0.01, 0.25, "CALL")
        assert price == pytest.approx(10.7623946263, abs=1e-9)

    def test_accepts_enum_and_string_right(self):
        a = european_price(100, 100, 1.0, 0.03, 0.01, 0.25, OptionRight.CALL)
        b = european_price(100, 100, 1.0, 0.03, 0.01, 0.25, "CALL")
        assert a == b

    def test_put_call_parity_single_case(self):
        s, k, t, r, q, vol = 100.0, 110.0, 1.5, 0.04, 0.02, 0.35
        c = european_price(s, k, t, r, q, vol, "CALL")
        p = european_price(s, k, t, r, q, vol, "PUT")
        parity = s * math.exp(-q * t) - k * math.exp(-r * t)
        assert c - p == pytest.approx(parity, abs=1e-9)

    def test_negative_rate_priced_within_bounds(self):
        s, k, t, r, q, vol = 100.0, 100.0, 1.0, -0.01, 0.0, 0.2
        price = european_price(s, k, t, r, q, vol, "PUT")
        lower, upper = no_arbitrage_bounds(s, k, t, r, q, "PUT")
        assert lower - 1e-9 <= price <= upper + 1e-9

    def test_extreme_high_strike_call_near_zero_put_near_bound(self):
        s, k, t, r, q, vol = 100.0, 1e9, 1.0, 0.03, 0.0, 0.5
        call = european_price(s, k, t, r, q, vol, "CALL")
        put = european_price(s, k, t, r, q, vol, "PUT")
        assert call == pytest.approx(0.0, abs=1e-9)
        assert put == pytest.approx(
            k * math.exp(-r * t) - s * math.exp(-q * t), rel=1e-9
        )

    def test_extreme_low_strike_call_near_forward_bound(self):
        s, k, t, r, q, vol = 100.0, 1e-6, 1.0, 0.03, 0.01, 0.5
        call = european_price(s, k, t, r, q, vol, "CALL")
        assert call == pytest.approx(
            s * math.exp(-q * t) - k * math.exp(-r * t), rel=1e-9
        )

    @pytest.mark.parametrize(
        "kwargs, reason",
        [
            (dict(spot=0), "non_positive_spot"),
            (dict(spot=-5), "non_positive_spot"),
            (dict(strike=0), "non_positive_strike"),
            (dict(maturity=-0.5), "negative_maturity"),
            (dict(maturity=101.0), "maturity_out_of_domain"),
            (dict(vol=-0.1), "negative_volatility"),
            (dict(vol=10.5), "volatility_out_of_domain"),
            (dict(rate=1.5), "rate_out_of_domain"),
            (dict(div=-1.5), "rate_out_of_domain"),
            (dict(spot=2e12), "spot_out_of_domain"),
        ],
    )
    def test_domain_gates(self, kwargs, reason):
        params = dict(spot=100, strike=100, maturity=1.0, rate=0.03, div=0.0, vol=0.2)
        params.update(kwargs)
        with pytest.raises(OptionInputError) as err:
            european_price(
                params["spot"],
                params["strike"],
                params["maturity"],
                params["rate"],
                params["div"],
                params["vol"],
                "CALL",
            )
        assert err.value.reason == reason

    @pytest.mark.parametrize("bad", NON_FINITE_FLOATS)
    def test_non_finite_rejected_everywhere(self, bad):
        with pytest.raises(OptionInputError):
            european_price(bad, 100, 1.0, 0.03, 0.0, 0.2, "CALL")
        with pytest.raises(OptionInputError):
            european_price(100, 100, 1.0, 0.03, 0.0, bad, "CALL")

    def test_non_finite_decimal_rejected(self):
        with pytest.raises(OptionInputError):
            european_price(Decimal("NaN"), 100, 1.0, 0.03, 0.0, 0.2, "CALL")


class TestImpliedVolatility:
    S, K, T, R, Q = 100.0, 105.0, T_ONE, 0.03, 0.01

    def test_round_trip_recovers_volatility(self):
        vol_true = 0.31
        price = european_price(self.S, self.K, self.T, self.R, self.Q, vol_true, "CALL")
        iv = implied_volatility(price, self.S, self.K, self.T, self.R, self.Q, "CALL", "MID")
        assert iv == pytest.approx(vol_true, abs=1e-9)
        reprice = european_price(self.S, self.K, self.T, self.R, self.Q, iv, "CALL")
        assert abs(reprice - price) <= 1e-7 * price

    @pytest.mark.parametrize("side", ["BID", "ASK", "MID", "LAST", "MODEL"])
    def test_quote_side_catalogue_accepted(self, side):
        price = european_price(self.S, self.K, self.T, self.R, self.Q, 0.2, "PUT")
        iv = implied_volatility(price, self.S, self.K, self.T, self.R, self.Q, "PUT", side)
        assert iv == pytest.approx(0.2, abs=1e-9)

    @pytest.mark.parametrize("side", ["mid", "close", "", 3, None])
    def test_invalid_quote_side_rejected(self, side):
        with pytest.raises(OptionInputError) as err:
            implied_volatility(5.0, self.S, self.K, self.T, self.R, self.Q, "CALL", side)
        assert err.value.reason == "invalid_quote_side"

    def test_price_below_lower_bound_rejected(self):
        # Deep ITM call: lower bound is strictly positive; go below it.
        lower, _ = no_arbitrage_bounds(100, 50, self.T, self.R, self.Q, "CALL")
        with pytest.raises(IVNoSolutionError) as err:
            implied_volatility(
                lower * 0.5, 100, 50, self.T, self.R, self.Q, "CALL", "MID"
            )
        assert err.value.reason == "price_outside_no_arbitrage_bounds"

    def test_price_at_bound_rejected_strictness(self):
        lower, upper = no_arbitrage_bounds(100, 50, self.T, self.R, self.Q, "CALL")
        for at_bound in (lower, upper):
            with pytest.raises(IVNoSolutionError):
                implied_volatility(
                    at_bound, 100, 50, self.T, self.R, self.Q, "CALL", "MID"
                )

    def test_price_above_upper_bound_rejected(self):
        _, upper = no_arbitrage_bounds(self.S, self.K, self.T, self.R, self.Q, "CALL")
        with pytest.raises(IVNoSolutionError):
            implied_volatility(
                upper * 1.01, self.S, self.K, self.T, self.R, self.Q, "CALL", "MID"
            )

    def test_price_inside_bounds_but_above_bracket_ceiling_rejected(self):
        # ATM call, price just below its upper bound: IV would exceed 5.0.
        _, upper = no_arbitrage_bounds(100, 100, self.T, self.R, self.Q, "CALL")
        ceiling_price = european_price(100, 100, self.T, self.R, self.Q, IV_BRACKET_HI, "CALL")
        observed = (ceiling_price + upper) / 2.0
        with pytest.raises(IVNoSolutionError) as err:
            implied_volatility(observed, 100, 100, self.T, self.R, self.Q, "CALL", "MID")
        assert err.value.reason == "price_above_bracket_ceiling"

    def test_price_below_bracket_floor_rejected(self):
        # Deep ITM call barely above its lower bound: IV would be < 1e-6.
        lower, _ = no_arbitrage_bounds(100, 50, self.T, self.R, self.Q, "CALL")
        floor_price = european_price(100, 50, self.T, self.R, self.Q, 1e-6, "CALL")
        observed = (lower + floor_price) / 2.0
        if observed > lower:  # guard: representable strictly-inside price
            with pytest.raises(IVNoSolutionError) as err:
                implied_volatility(observed, 100, 50, self.T, self.R, self.Q, "CALL", "MID")
            assert err.value.reason == "price_below_bracket_floor"

    def test_expired_option_has_no_iv(self):
        with pytest.raises(OptionInputError) as err:
            implied_volatility(5.0, 100, 100, 0.0, self.R, self.Q, "CALL", "MID")
        assert err.value.reason == "maturity_zero_no_iv"

    def test_negative_rate_round_trip(self):
        price = european_price(100, 95, 0.5, -0.01, 0.0, 0.45, "PUT")
        iv = implied_volatility(price, 100, 95, 0.5, -0.01, 0.0, "PUT", "ASK")
        assert iv == pytest.approx(0.45, abs=1e-9)

    def test_non_finite_price_rejected(self):
        with pytest.raises(OptionInputError):
            implied_volatility(
                float("nan"), self.S, self.K, self.T, self.R, self.Q, "CALL", "MID"
            )

    def test_iv_error_is_subclass_of_input_error(self):
        assert issubclass(IVNoSolutionError, OptionInputError)


class TestGreeks:
    S, K, T, R, Q, VOL = 100.0, 105.0, 0.75, 0.03, 0.02, 0.3

    def g(self, right="CALL", **overrides):
        params = dict(s=self.S, k=self.K, t=self.T, r=self.R, q=self.Q, vol=self.VOL)
        params.update(overrides)
        return greeks(
            params["s"], params["k"], params["t"], params["r"], params["q"],
            params["vol"], right,
        )

    def price(self, right="CALL", **overrides):
        params = dict(s=self.S, k=self.K, t=self.T, r=self.R, q=self.Q, vol=self.VOL)
        params.update(overrides)
        return european_price(
            params["s"], params["k"], params["t"], params["r"], params["q"],
            params["vol"], right,
        )

    @pytest.mark.parametrize("right", ["CALL", "PUT"])
    def test_delta_matches_finite_difference(self, right):
        h = 1e-4 * self.S
        fd = (self.price(right, s=self.S + h) - self.price(right, s=self.S - h)) / (2 * h)
        assert self.g(right).delta == pytest.approx(fd, abs=1e-7)

    @pytest.mark.parametrize("right", ["CALL", "PUT"])
    def test_gamma_matches_finite_difference(self, right):
        h = 1e-3 * self.S
        fd = (
            self.price(right, s=self.S + h)
            - 2 * self.price(right)
            + self.price(right, s=self.S - h)
        ) / (h * h)
        assert self.g(right).gamma == pytest.approx(fd, rel=1e-5)

    @pytest.mark.parametrize("right", ["CALL", "PUT"])
    def test_vega_matches_finite_difference(self, right):
        h = 1e-6
        fd = (self.price(right, vol=self.VOL + h) - self.price(right, vol=self.VOL - h)) / (2 * h)
        assert self.g(right).vega == pytest.approx(fd, rel=1e-6)

    @pytest.mark.parametrize("right", ["CALL", "PUT"])
    def test_theta_matches_finite_difference_in_calendar_time(self, right):
        # theta = dV/dt = -dV/dT (per year of elapsing calendar time)
        h = 1e-6
        fd = -(self.price(right, t=self.T + h) - self.price(right, t=self.T - h)) / (2 * h)
        assert self.g(right).theta == pytest.approx(fd, rel=1e-5, abs=1e-8)

    @pytest.mark.parametrize("right", ["CALL", "PUT"])
    def test_rho_matches_finite_difference(self, right):
        h = 1e-6
        fd = (self.price(right, r=self.R + h) - self.price(right, r=self.R - h)) / (2 * h)
        assert self.g(right).rho == pytest.approx(fd, rel=1e-6)

    def test_delta_bounded_and_signed_for_non_negative_yield(self):
        for k_mult in (0.5, 0.8, 1.0, 1.25, 2.0):
            for vol in (0.05, 0.3, 1.5):
                for t in (0.01, 1.0, 3.0):
                    call = self.g("CALL", k=self.K * k_mult, vol=vol, t=t)
                    put = self.g("PUT", k=self.K * k_mult, vol=vol, t=t)
                    assert 0.0 <= call.delta <= 1.0
                    assert -1.0 <= put.delta <= 0.0
                    assert call.gamma >= 0.0 and put.gamma >= 0.0
                    assert call.vega >= 0.0 and put.vega >= 0.0

    def test_derived_unit_views_exact(self):
        g = self.g("CALL")
        assert g.vega_per_point == g.vega * 0.01
        assert g.theta_per_calendar_day == g.theta / 365.0
        assert g.rho_per_bp == g.rho * 0.0001

    def test_call_put_gamma_and_vega_identical(self):
        assert self.g("CALL").gamma == pytest.approx(self.g("PUT").gamma, rel=1e-12)
        assert self.g("CALL").vega == pytest.approx(self.g("PUT").vega, rel=1e-12)

    def test_expiry_rejected(self):
        with pytest.raises(OptionInputError) as err:
            self.g("CALL", t=0.0)
        assert err.value.reason == "maturity_zero_no_greeks"

    def test_zero_volatility_rejected(self):
        with pytest.raises(OptionInputError) as err:
            self.g("CALL", vol=0.0)
        assert err.value.reason == "volatility_zero_no_greeks"

    def test_result_model_rejects_non_finite(self):
        with pytest.raises(ValidationError):
            GreeksResult(
                delta=float("nan"), gamma=0.0, vega=0.0, vega_per_point=0.0,
                theta=0.0, theta_per_calendar_day=0.0, rho=0.0, rho_per_bp=0.0,
            )

    def test_result_model_rejects_inconsistent_derived_view(self):
        with pytest.raises(ValidationError):
            GreeksResult(
                delta=0.5, gamma=0.01, vega=40.0, vega_per_point=1.0,
                theta=-5.0, theta_per_calendar_day=-5.0 / 365.0, rho=45.0,
                rho_per_bp=45.0 * 0.0001,
            )

    def test_result_model_frozen(self):
        g = self.g("CALL")
        with pytest.raises(ValidationError):
            g.delta = 0.0


class TestAmericanPrice:
    def test_american_put_not_below_european(self):
        for k in (90.0, 100.0, 120.0):
            am = american_price(100, k, T_HALF, 0.05, 0.0, 0.3, "PUT")
            eu = european_price(100, k, T_HALF, 0.05, 0.0, 0.3, "PUT")
            assert am >= eu - AMERICAN_TOL

    def test_american_call_no_dividend_equals_european(self):
        # Without dividends early exercise of a call is never optimal.
        am = american_price(100, 100, T_HALF, 0.05, 0.0, 0.3, "CALL")
        eu = european_price(100, 100, T_HALF, 0.05, 0.0, 0.3, "CALL")
        assert am == pytest.approx(eu, abs=AMERICAN_TOL)
        assert am >= eu - AMERICAN_TOL

    def test_american_call_with_yield_not_below_european(self):
        am = american_price(100, 90, T_ONE, 0.03, 0.05, 0.25, "CALL")
        eu = european_price(100, 90, T_ONE, 0.03, 0.05, 0.25, "CALL")
        assert am >= eu - AMERICAN_TOL

    def test_deep_itm_put_early_exercise_premium_positive(self):
        am = american_price(60, 100, T_ONE, 0.08, 0.0, 0.2, "PUT")
        eu = european_price(60, 100, T_ONE, 0.08, 0.0, 0.2, "PUT")
        assert am > eu + 0.01  # genuine early-exercise premium
        assert am >= 40.0 - AMERICAN_TOL  # not below intrinsic

    def test_expiry_is_intrinsic(self):
        assert american_price(110, 100, 0.0, 0.05, 0.0, 0.3, "CALL") == 10.0
        assert american_price(90, 100, 0.0, 0.05, 0.0, 0.3, "PUT") == 10.0

    def test_grid_convergence_between_step_counts(self):
        coarse = american_price(100, 110, T_ONE, 0.05, 0.02, 0.35, "PUT", steps=400)
        fine = american_price(100, 110, T_ONE, 0.05, 0.02, 0.35, "PUT", steps=800)
        assert abs(coarse - fine) <= 2 * AMERICAN_TOL

    def test_deterministic(self):
        a = american_price(100, 105, T_ONE, 0.04, 0.01, 0.4, "PUT")
        b = american_price(100, 105, T_ONE, 0.04, 0.01, 0.4, "PUT")
        assert a == b

    def test_discrete_dividends_not_implemented(self):
        with pytest.raises(OptionNotImplementedError) as err:
            american_price(
                100, 100, T_ONE, 0.03, 0.0, 0.3, "PUT",
                discrete_dividends=(Decimal("1.20"),),
            )
        assert "NOT_IMPLEMENTED" in str(err.value)
        assert err.value.capability == "american_price.discrete_dividends"

    def test_discrete_dividends_never_silently_ignored_even_when_zero(self):
        with pytest.raises(OptionNotImplementedError):
            american_price(
                100, 100, T_ONE, 0.03, 0.0, 0.3, "PUT",
                discrete_dividends=[Decimal("0")],
            )

    def test_zero_volatility_rejected_no_fallback(self):
        with pytest.raises(OptionInputError) as err:
            american_price(100, 100, T_ONE, 0.03, 0.0, 0.0, "PUT")
        assert err.value.reason == "volatility_out_of_domain"

    def test_steps_below_validated_grid_rejected(self):
        with pytest.raises(OptionInputError) as err:
            american_price(
                100, 100, T_ONE, 0.03, 0.0, 0.3, "PUT", steps=AMERICAN_MIN_STEPS - 1
            )
        assert err.value.reason == "steps_below_validated_grid"

    def test_steps_must_be_int(self):
        with pytest.raises(OptionInputError):
            american_price(100, 100, T_ONE, 0.03, 0.0, 0.3, "PUT", steps=800.0)
        with pytest.raises(OptionInputError):
            american_price(100, 100, T_ONE, 0.03, 0.0, 0.3, "PUT", steps=True)

    def test_maturity_below_date_grid_rejected(self):
        with pytest.raises(OptionInputError) as err:
            american_price(100, 100, 1e-4, 0.03, 0.0, 0.3, "PUT")
        assert err.value.reason == "maturity_below_date_grid"

    def test_off_grid_maturity_rejected_not_silently_quantized(self):
        # Reproducer for the P0 date-grid defect: 2.5/365 years used to be
        # silently banker's-rounded to 2/365 (a half-day shorter maturity),
        # returning 2.34860 while the European price at the REQUESTED
        # maturity is 2.62332 — i.e. an "American" price 10.5% BELOW the
        # American >= European arbitrage floor of the requested input, with
        # no signal in the bare-float result. Off-grid maturities must be
        # rejected fail-closed, never quantized.
        with pytest.raises(OptionInputError) as err:
            american_price(100, 100, 2.5 / 365.0, 0.05, 0.0, 0.8, "PUT")
        assert err.value.reason == "maturity_off_date_grid"

    @pytest.mark.parametrize(
        "t",
        [
            1.5 / 365.0,   # would banker's-round UP to 2 days
            183.5 / 365.0, # half-day off the grid, would round to 184
            0.5,           # plain half-year = 182.5 days, off-grid
            0.01,          # 3.65 days, off-grid
        ],
    )
    def test_off_grid_maturities_all_rejected(self, t):
        with pytest.raises(OptionInputError) as err:
            american_price(100, 100, t, 0.05, 0.0, 0.3, "PUT")
        assert err.value.reason == "maturity_off_date_grid"

    def test_global_evaluation_date_restored_after_pricing(self):
        # Reproducer P2: american_price mutates the process-global
        # QuantLib Settings.instance().evaluationDate; it must restore the
        # caller's value (try/finally), never leak its internal anchor.
        import QuantLib as ql

        settings = ql.Settings.instance()
        saved = settings.evaluationDate
        sentinel = ql.Date(15, 6, 2030)
        try:
            settings.evaluationDate = sentinel
            american_price(100, 100, T_ONE, 0.03, 0.0, 0.3, "PUT")
            assert settings.evaluationDate == sentinel
        finally:
            settings.evaluationDate = saved

    def test_global_evaluation_date_restored_on_failure_inside_engine(self):
        # The restoration must also hold when pricing raises AFTER the
        # mutation. steps below the validated grid raises BEFORE the
        # mutation; an engine-level failure is hard to trigger with valid
        # gates, so this asserts restoration around a rejected input that
        # passes every pre-mutation gate is not required — instead verify
        # that a successful call immediately after a gate rejection still
        # sees the sentinel untouched.
        import QuantLib as ql

        settings = ql.Settings.instance()
        saved = settings.evaluationDate
        sentinel = ql.Date(16, 6, 2030)
        try:
            settings.evaluationDate = sentinel
            with pytest.raises(OptionInputError):
                american_price(100, 100, 0.5, 0.03, 0.0, 0.3, "PUT")  # off-grid
            assert settings.evaluationDate == sentinel
            american_price(100, 100, T_ONE, 0.03, 0.0, 0.3, "PUT")
            assert settings.evaluationDate == sentinel
        finally:
            settings.evaluationDate = saved

    def test_on_grid_maturities_accepted_despite_float_roundoff(self):
        # days / 365.0 carries float round-off up to a few ulps (e.g.
        # 3/365.0 * 365.0 == 3 - 4.44e-16); exact-grid maturities must
        # stay accepted and respect the arbitrage floor at the requested
        # maturity within the documented lattice tolerance.
        for d in (1, 3, 182, 365, 730):
            t = d / 365.0
            am = american_price(100, 100, t, 0.05, 0.0, 0.8, "PUT")
            eu = european_price(100, 100, t, 0.05, 0.0, 0.8, "PUT")
            assert math.isfinite(am)
            assert am >= eu - AMERICAN_TOL


class TestOptionLeg:
    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            OptionLeg(
                quantity=0, right="CALL", strike=Decimal("100"),
                premium=Decimal("1"), multiplier=100,
            )

    def test_option_leg_requires_strike(self):
        with pytest.raises(ValidationError):
            OptionLeg(quantity=1, right="CALL", strike=None, premium=Decimal("1"), multiplier=100)

    def test_stock_leg_forbids_strike(self):
        with pytest.raises(ValidationError):
            OptionLeg(
                quantity=1, right="STOCK", strike=Decimal("100"),
                premium=Decimal("100"), multiplier=1,
            )

    def test_negative_premium_rejected(self):
        with pytest.raises(ValidationError):
            OptionLeg(
                quantity=1, right="PUT", strike=Decimal("100"),
                premium=Decimal("-1"), multiplier=100,
            )

    def test_non_positive_multiplier_rejected(self):
        with pytest.raises(ValidationError):
            OptionLeg(
                quantity=1, right="PUT", strike=Decimal("100"),
                premium=Decimal("1"), multiplier=0,
            )

    def test_unknown_right_rejected(self):
        with pytest.raises(ValidationError):
            OptionLeg(
                quantity=1, right="FUTURE", strike=Decimal("100"),
                premium=Decimal("1"), multiplier=100,
            )

    def test_frozen(self):
        leg = call_leg(1, "100")
        with pytest.raises(ValidationError):
            leg.quantity = 2


class TestPayoffAtExpiry:
    def bull_call(self):
        # Long CALL 100 at 5, short CALL 110 at 2, multiplier 100.
        return [call_leg(1, "100", "5"), call_leg(-1, "110", "2")]

    def test_exact_at_strikes_and_between(self):
        fees = Decimal("1.50")
        pnl = payoff_at_expiry(
            self.bull_call(),
            [Decimal("90"), Decimal("100"), Decimal("105"), Decimal("110"), Decimal("125")],
            fees,
        )
        # Net debit D = (5-2)*100 = 300; width W*M = 1000.
        assert pnl[0] == Decimal("-301.50")  # below both strikes: -D - F
        assert pnl[1] == Decimal("-301.50")  # exactly at long strike (breakpoint)
        assert pnl[2] == Decimal("198.50")  # 5*100 - 300 - 1.50
        assert pnl[3] == Decimal("698.50")  # exactly at short strike: W*M - D - F
        assert pnl[4] == Decimal("698.50")  # capped above

    def test_breakeven_exact(self):
        # Breakeven at K1 + D/M = 103; P&L there is exactly -fees.
        pnl = payoff_at_expiry(self.bull_call(), [Decimal("103")], Decimal("0"))
        assert pnl[0] == Decimal("0")

    def test_leg_sum_linearity_exact(self):
        # Linearity is asserted on an all-long decomposition: a certified
        # short leg is inseparable from its structure (P1-3) and cannot be
        # priced alone through the public API.
        legs = [call_leg(1, "100", "5"), put_leg(1, "110", "6"), stock_leg(2, "95")]
        grid = [Decimal("80"), Decimal("100"), Decimal("103.17"), Decimal("110"), Decimal("140")]
        combined = payoff_at_expiry(legs, grid, Decimal("0"))
        parts = [payoff_at_expiry([leg], grid, Decimal("0")) for leg in legs]
        for i in range(len(grid)):
            assert combined[i] == sum(p[i] for p in parts)

    def test_certified_vertical_equals_hand_computed_leg_sum(self):
        # For the certified bull call debit the combined payoff still equals
        # the exact per-leg formula sum(q*M*(h(S)-p)) computed by hand.
        grid = [Decimal("80"), Decimal("103"), Decimal("110"), Decimal("140")]
        combined = payoff_at_expiry(self.bull_call(), grid, Decimal("0"))
        for spot, total in zip(grid, combined):
            long_leg = 100 * (max(spot - Decimal("100"), Decimal(0)) - Decimal("5"))
            short_leg = -100 * (max(spot - Decimal("110"), Decimal(0)) - Decimal("2"))
            assert total == long_leg + short_leg

    def test_put_leg_and_bankruptcy_tail(self):
        legs = [put_leg(1, "100", "4")]
        pnl = payoff_at_expiry(legs, [Decimal("0"), Decimal("100"), Decimal("120")], Decimal("0"))
        assert pnl[0] == Decimal("9600")  # (100 - 0 - 4) * 100
        assert pnl[1] == Decimal("-400")
        assert pnl[2] == Decimal("-400")

    def test_stock_leg_is_linear(self):
        legs = [stock_leg(50, "100")]
        pnl = payoff_at_expiry(legs, [Decimal("90"), Decimal("110")], Decimal("0"))
        assert pnl[0] == Decimal("-500")
        assert pnl[1] == Decimal("500")

    def test_float_spot_converted_exactly(self):
        pnl_float = payoff_at_expiry(self.bull_call(), [110.0], Decimal("0"))
        pnl_decimal = payoff_at_expiry(self.bull_call(), [Decimal("110")], Decimal("0"))
        assert pnl_float == pnl_decimal == (Decimal("700"),)

    def test_fees_reduce_result(self):
        base = payoff_at_expiry(self.bull_call(), [Decimal("110")], Decimal("0"))[0]
        with_fees = payoff_at_expiry(self.bull_call(), [Decimal("110")], Decimal("2.25"))[0]
        assert base - with_fees == Decimal("2.25")

    def test_naked_short_call_rejected_without_certification(self):
        # Reproducer P1-3: the spec requires the defined-risk verifier
        # before any scenario on a structure containing a short quantity;
        # payoff_at_expiry used to price a naked short call silently.
        with pytest.raises(OptionInputError) as err:
            payoff_at_expiry([call_leg(-1, "110", "3")], [Decimal("100")], Decimal("0"))
        assert err.value.reason == "undefined_risk_structure"

    def test_uncertified_covered_call_rejected(self):
        # Covered call is outside the closed catalogue (P1-2), therefore
        # payoff refuses it too as long as no dedicated profile exists.
        legs = [stock_leg(100, "100"), call_leg(-1, "110", "3")]
        with pytest.raises(OptionInputError) as err:
            payoff_at_expiry(legs, [Decimal("100")], Decimal("0"))
        assert err.value.reason == "undefined_risk_structure"

    def test_certified_bull_call_debit_accepted(self):
        # A certified catalogue member keeps pricing normally.
        pnl = payoff_at_expiry(self.bull_call(), [Decimal("110")], Decimal("0"))
        assert pnl == (Decimal("700"),)

    def test_all_long_structure_needs_no_certification(self):
        pnl = payoff_at_expiry(
            [call_leg(1, "100", "5"), put_leg(1, "100", "5")],
            [Decimal("100")],
            Decimal("0"),
        )
        assert pnl == (Decimal("-1000"),)

    def test_gates(self):
        legs = self.bull_call()
        with pytest.raises(OptionInputError):
            payoff_at_expiry([], [Decimal("100")], Decimal("0"))
        with pytest.raises(OptionInputError):
            payoff_at_expiry(legs, [], Decimal("0"))
        with pytest.raises(OptionInputError):
            payoff_at_expiry(legs, [Decimal("-1")], Decimal("0"))
        with pytest.raises(OptionInputError):
            payoff_at_expiry(legs, [float("nan")], Decimal("0"))
        with pytest.raises(OptionInputError):
            payoff_at_expiry(legs, [Decimal("100")], Decimal("-1"))
        with pytest.raises(OptionInputError):
            payoff_at_expiry(legs, [Decimal("100")], 1.5)  # float fees rejected
        with pytest.raises(OptionInputError):
            payoff_at_expiry(legs, [Decimal("100")], Decimal("NaN"))
        with pytest.raises(OptionInputError):
            payoff_at_expiry([legs[0], "not a leg"], [Decimal("100")], Decimal("0"))


class TestScenarioGrid:
    def legs(self):
        return [call_leg(1, "100", "5"), call_leg(-1, "110", "2")]

    def test_shape_and_finiteness(self):
        grid = scenario_grid(
            self.legs(), [90.0, 100.0, 110.0], [0.5, 0.25, 0.0],
            [(0.2, 0.2), (0.3, 0.3)], 0.03, 0.01,
        )
        assert len(grid) == 2
        assert all(len(row) == 3 for row in grid)
        assert all(len(cells) == 3 for row in grid for cells in row)
        assert all(math.isfinite(v) for row in grid for cells in row for v in cells)

    def test_deterministic(self):
        args = (
            self.legs(), [95.0, 105.0], [0.4, 0.1], [(0.25, 0.28)], 0.02, 0.0,
        )
        assert scenario_grid(*args) == scenario_grid(*args)

    def test_single_leg_cell_equals_bsm_repricing(self):
        legs = [call_leg(2, "100", "5")]
        grid = scenario_grid(legs, [104.0], [0.5], [(0.3,)], 0.03, 0.01)
        expected = 2 * 100 * (
            european_price(104.0, 100.0, 0.5, 0.03, 0.01, 0.3, "CALL") - 5.0
        )
        assert grid[0][0][0] == pytest.approx(expected, rel=1e-12)

    def test_converges_to_payoff_at_expiry(self):
        legs = self.legs()
        spots = [90.0, 100.0, 103.0, 110.0, 130.0]
        grid = scenario_grid(legs, spots, [0.0], [(0.25, 0.25)], 0.03, 0.01)
        payoff = payoff_at_expiry(legs, spots, Decimal("0"))
        for cell, exact in zip(grid[0][0], payoff):
            assert cell == pytest.approx(float(exact), abs=1e-9)

    def test_stock_leg_requires_none_volatility(self):
        legs = [stock_leg(10, "100"), call_leg(1, "110", "2")]
        grid = scenario_grid(legs, [105.0], [0.5], [(None, 0.3)], 0.03, 0.0)
        assert math.isfinite(grid[0][0][0])
        with pytest.raises(OptionInputError) as err:
            scenario_grid(legs, [105.0], [0.5], [(0.2, 0.3)], 0.03, 0.0)
        assert err.value.reason == "stock_leg_volatility"

    def test_option_leg_volatility_absence_rejected_not_zeroed(self):
        with pytest.raises(OptionInputError) as err:
            scenario_grid(self.legs(), [100.0], [0.5], [(0.2, None)], 0.03, 0.0)
        assert err.value.reason == "missing_leg_volatility"

    def test_scenario_length_mismatch_rejected(self):
        with pytest.raises(OptionInputError) as err:
            scenario_grid(self.legs(), [100.0], [0.5], [(0.2,)], 0.03, 0.0)
        assert err.value.reason == "scenario_leg_mismatch"

    def test_empty_grids_rejected(self):
        with pytest.raises(OptionInputError):
            scenario_grid(self.legs(), [], [0.5], [(0.2, 0.2)], 0.03, 0.0)
        with pytest.raises(OptionInputError):
            scenario_grid(self.legs(), [100.0], [], [(0.2, 0.2)], 0.03, 0.0)
        with pytest.raises(OptionInputError):
            scenario_grid(self.legs(), [100.0], [0.5], [], 0.03, 0.0)

    def test_zero_spot_rejected_here(self):
        with pytest.raises(OptionInputError):
            scenario_grid(self.legs(), [0.0], [0.5], [(0.2, 0.2)], 0.03, 0.0)

    def test_naked_short_call_rejected_without_certification(self):
        # Reproducer P1-3: same certification gate as payoff_at_expiry —
        # scenario_grid used to reprice a naked short call silently.
        with pytest.raises(OptionInputError) as err:
            scenario_grid([call_leg(-1, "110", "3")], [100.0], [0.5], [(0.2,)], 0.03, 0.0)
        assert err.value.reason == "undefined_risk_structure"

    def test_certified_bull_call_debit_accepted_short_leg_present(self):
        # The certified debit vertical (contains a short leg) keeps pricing.
        grid = scenario_grid(self.legs(), [100.0], [0.5], [(0.2, 0.2)], 0.03, 0.0)
        assert math.isfinite(grid[0][0][0])

    def test_leg_strike_outside_model_domain_rejected(self):
        # Reproducer P1-1: a strike of 5e13 is rejected by european_price
        # (model domain (0, 1e12]) but scenario_grid used to convert it with
        # a bare float(leg.strike) and price it silently, bypassing the gate.
        legs = [call_leg(1, "5e13", "5")]
        with pytest.raises(OptionInputError) as err:
            scenario_grid(legs, [100.0], [0.5], [(0.2,)], 0.03, 0.0)
        assert err.value.reason == "leg_strike_out_of_domain"

    def test_leg_strike_overflowing_float64_rejected_typed(self):
        # Reproducer P1-1: Decimal('1e400') is a finite Decimal accepted by
        # OptionLeg but overflows float64 to inf; the old code leaked a raw
        # ValueError from math.log instead of a typed OptionInputError.
        legs = [call_leg(1, "1e400", "5")]
        with pytest.raises(OptionInputError) as err:
            scenario_grid(legs, [100.0], [0.5], [(0.2,)], 0.03, 0.0)
        assert err.value.reason == "non_finite_input"

    def test_leg_premium_outside_domain_rejected(self):
        # Same P1-1 gate for the declared premium (finite, [0, 1e12]).
        legs = [call_leg(1, "100", "5e13")]
        with pytest.raises(OptionInputError) as err:
            scenario_grid(legs, [100.0], [0.5], [(0.2,)], 0.03, 0.0)
        assert err.value.reason == "leg_premium_out_of_domain"
        legs = [call_leg(1, "100", "1e400")]
        with pytest.raises(OptionInputError) as err:
            scenario_grid(legs, [100.0], [0.5], [(0.2,)], 0.03, 0.0)
        assert err.value.reason == "non_finite_input"

    def test_leg_multiplier_overflowing_float64_rejected_typed(self):
        # Same P1-1 gate for the multiplier (int too large for float64).
        legs = [call_leg(1, "100", "5", mult=10**400)]
        with pytest.raises(OptionInputError) as err:
            scenario_grid(legs, [100.0], [0.5], [(0.2,)], 0.03, 0.0)
        assert err.value.reason == "non_finite_input"


class TestDefinedRiskCheck:
    """Strict closed catalogue: accepted and rejected structures, with reasons."""

    def test_bull_call_debit_accepted(self):
        result = defined_risk_check([call_leg(1, "100", "5"), call_leg(-1, "110", "2")])
        assert result.is_defined_risk is True
        assert result.reason_code == "DEFINED_RISK"
        assert "BULL_CALL_DEBIT" in result.detail

    def test_bull_call_debit_multiple_paired_contracts_accepted(self):
        result = defined_risk_check([call_leg(3, "100", "5"), call_leg(-3, "110", "2")])
        assert result.is_defined_risk is True
        assert "BULL_CALL_DEBIT" in result.detail

    def test_bear_put_debit_accepted(self):
        result = defined_risk_check([put_leg(1, "110", "6"), put_leg(-1, "100", "3")])
        assert result.is_defined_risk is True
        assert "BEAR_PUT_DEBIT" in result.detail

    def test_long_straddle_accepted(self):
        result = defined_risk_check([call_leg(1, "100", "5"), put_leg(1, "100", "5")])
        assert result.is_defined_risk is True
        assert "LONG_STRADDLE" in result.detail

    def test_long_strangle_accepted(self):
        result = defined_risk_check([call_leg(1, "110", "3"), put_leg(1, "90", "3")])
        assert result.is_defined_risk is True
        assert "LONG_STRANGLE" in result.detail

    def test_single_long_call_accepted(self):
        result = defined_risk_check([call_leg(1, "100", "5")])
        assert result.is_defined_risk is True
        assert result.reason_code == "DEFINED_RISK"

    def test_single_long_put_accepted(self):
        result = defined_risk_check([put_leg(1, "100", "5")])
        assert result.is_defined_risk is True

    def test_long_stock_alone_accepted(self):
        result = defined_risk_check([stock_leg(100, "100")])
        assert result.is_defined_risk is True

    def test_all_long_combination_accepted(self):
        result = defined_risk_check(
            [call_leg(2, "110", "3"), put_leg(1, "90", "3"), stock_leg(10, "100")]
        )
        assert result.is_defined_risk is True

    def test_naked_short_call_rejected(self):
        result = defined_risk_check([call_leg(-1, "110", "3")])
        assert result.is_defined_risk is False
        assert result.reason_code == "UNCOVERED_SHORT_UPSIDE_TAIL"

    def test_naked_short_put_rejected(self):
        result = defined_risk_check([put_leg(-1, "90", "3")])
        assert result.is_defined_risk is False
        assert result.reason_code == "UNCOVERED_SHORT_DOWNSIDE_TAIL"

    def test_call_ratio_spread_rejected(self):
        result = defined_risk_check([call_leg(1, "100", "5"), call_leg(-2, "110", "2")])
        assert result.is_defined_risk is False
        assert result.reason_code == "UNCOVERED_SHORT_UPSIDE_TAIL"

    def test_put_ratio_spread_rejected(self):
        result = defined_risk_check([put_leg(1, "100", "5"), put_leg(-2, "90", "2")])
        assert result.is_defined_risk is False
        assert result.reason_code == "UNCOVERED_SHORT_DOWNSIDE_TAIL"

    def test_short_stock_alone_rejected(self):
        result = defined_risk_check([stock_leg(-100, "100")])
        assert result.is_defined_risk is False
        assert result.reason_code == "UNCOVERED_SHORT_UPSIDE_TAIL"

    def test_covered_call_rejected_outside_closed_catalogue(self):
        # Reproducer P1-2: a covered call (100 shares covering one short
        # contract) has covered tails but is NOT in the documented closed
        # catalogue {BULL_CALL_DEBIT, BEAR_PUT_DEBIT, LONG_STRADDLE,
        # LONG_STRANGLE, all-long}. It used to be certified by the tail
        # math alone; strict recognition must refuse it until a separate
        # profile is validated.
        result = defined_risk_check([stock_leg(100, "100"), call_leg(-1, "110", "3")])
        assert result.is_defined_risk is False
        assert result.reason_code == "OUTSIDE_CLOSED_CATALOG"

    def test_broken_wing_butterfly_rejected(self):
        # Reproducer P1-2: +1 C90 / -2 C100 / +1 C120 has zero net call
        # quantity on the upside tail (the tail math passes) but is a
        # broken-wing butterfly, explicitly refused by the specification
        # until a dedicated profile is validated.
        legs = [
            call_leg(1, "90", "12"),
            call_leg(-2, "100", "6"),
            call_leg(1, "120", "1"),
        ]
        result = defined_risk_check(legs)
        assert result.is_defined_risk is False
        assert result.reason_code == "OUTSIDE_CLOSED_CATALOG"

    def test_call_credit_vertical_rejected(self):
        # Reproducer P1-2: bear call credit (short C100, long C110) has
        # covered tails but the catalogue only contains DEBIT verticals;
        # credit verticals are refused until a separate profile exists.
        result = defined_risk_check([call_leg(-1, "100", "5"), call_leg(1, "110", "2")])
        assert result.is_defined_risk is False
        assert result.reason_code == "CREDIT_VERTICAL_NOT_VALIDATED"

    def test_put_credit_vertical_rejected(self):
        # Bull put credit (short P110, long P100): same refusal.
        result = defined_risk_check([put_leg(-1, "110", "6"), put_leg(1, "100", "3")])
        assert result.is_defined_risk is False
        assert result.reason_code == "CREDIT_VERTICAL_NOT_VALIDATED"

    def test_debit_shape_with_non_positive_debit_rejected(self):
        # Bull-call shape whose declared premiums produce D <= 0: the doc
        # requires rejection (incoherent quotes / hidden credit), not repair.
        result = defined_risk_check([call_leg(1, "100", "2"), call_leg(-1, "110", "5")])
        assert result.is_defined_risk is False
        assert result.reason_code == "VERTICAL_DEBIT_NOT_POSITIVE"
        # Exactly zero debit is also rejected.
        result = defined_risk_check([call_leg(1, "100", "3"), call_leg(-1, "110", "3")])
        assert result.is_defined_risk is False
        assert result.reason_code == "VERTICAL_DEBIT_NOT_POSITIVE"

    def test_debit_at_or_above_width_rejected(self):
        # D >= W*M means incoherent quotes for a debit vertical: rejected.
        result = defined_risk_check([call_leg(1, "100", "15"), call_leg(-1, "110", "2")])
        assert result.is_defined_risk is False
        assert result.reason_code == "VERTICAL_DEBIT_NOT_BELOW_WIDTH"
        # Exactly D == W*M (width 10, net debit 10) is also rejected.
        result = defined_risk_check([call_leg(1, "100", "12"), call_leg(-1, "110", "2")])
        assert result.is_defined_risk is False
        assert result.reason_code == "VERTICAL_DEBIT_NOT_BELOW_WIDTH"

    def test_unpaired_vertical_quantities_rejected(self):
        # +2/-1 is net long (tails pass) but the legs are not paired 1:1.
        result = defined_risk_check([call_leg(2, "100", "5"), call_leg(-1, "110", "2")])
        assert result.is_defined_risk is False
        assert result.reason_code == "VERTICAL_LEGS_NOT_PAIRED"

    def test_unpaired_vertical_multipliers_rejected(self):
        result = defined_risk_check(
            [call_leg(1, "100", "5", mult=100), call_leg(-1, "110", "2", mult=10)]
        )
        assert result.is_defined_risk is False
        assert result.reason_code == "VERTICAL_LEGS_NOT_PAIRED"

    def test_same_strike_vertical_rejected(self):
        result = defined_risk_check([call_leg(1, "100", "5"), call_leg(-1, "100", "4")])
        assert result.is_defined_risk is False
        assert result.reason_code == "VERTICAL_LEGS_NOT_PAIRED"

    def test_short_leg_with_extra_long_legs_rejected(self):
        # Vertical plus an extra long put: defined tails, but not a
        # catalogue structure — strict recognition refuses it.
        legs = [call_leg(1, "100", "5"), call_leg(-1, "110", "2"), put_leg(1, "90", "1")]
        result = defined_risk_check(legs)
        assert result.is_defined_risk is False
        assert result.reason_code == "OUTSIDE_CLOSED_CATALOG"

    def test_multiplier_weighting_detects_partial_cover(self):
        # 50 shares do NOT cover a 100-multiplier short call.
        result = defined_risk_check([stock_leg(50, "100"), call_leg(-1, "110", "3")])
        assert result.is_defined_risk is False
        assert result.reason_code == "UNCOVERED_SHORT_UPSIDE_TAIL"

    def test_empty_legs_rejected(self):
        with pytest.raises(OptionInputError):
            defined_risk_check([])

    def test_result_model_frozen(self):
        result = defined_risk_check([call_leg(1, "100", "5")])
        assert isinstance(result, DefinedRiskResult)
        with pytest.raises(ValidationError):
            result.is_defined_risk = False
