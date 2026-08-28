"""market.* calculations: nominal values, gate violations, property invariants.

All fixtures are SYNTHETIC and deterministic; no network, no real market data,
no unseeded randomness (Hypothesis manages its own reproducible search).
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st

from vertex_core.calculations.market import (
    FLOAT64_ABS_TOL,
    FLOAT64_REL_TOL,
    CalculationInputError,
    OhlcBar,
    atr,
    breadth,
    log_return,
    realized_volatility,
    relative_strength,
    simple_return,
)

BASE_TS = datetime(2026, 3, 2, 14, 30, tzinfo=timezone.utc)
BASIS = "split_adjusted"

NON_FINITE_FLOATS = [float("nan"), float("inf"), float("-inf")]
NON_FINITE_DECIMALS = [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")]


def make_bar(minute: int, open_: str, high: str, low: str, close: str) -> OhlcBar:
    return OhlcBar(
        timestamp=BASE_TS + timedelta(minutes=minute),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def coherent_bars() -> list[OhlcBar]:
    """Three coherent, strictly ordered bars with hand-checked true ranges."""
    return [
        make_bar(0, "10", "11", "9", "10"),
        # prev close 10: TR = max(12-10, |12-10|, |10-10|) = 2
        make_bar(1, "10", "12", "10", "11"),
        # prev close 11: TR = max(1, 0.5, 0.5) = 1
        make_bar(2, "11", "11.5", "10.5", "11"),
    ]


class TestSimpleReturn:
    def test_nominal_gain(self):
        result = simple_return(
            100.0, 110.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        assert result == pytest.approx(0.10, rel=FLOAT64_REL_TOL)

    def test_nominal_loss(self):
        result = simple_return(
            200, 150, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        assert result == pytest.approx(-0.25, rel=FLOAT64_REL_TOL)

    def test_decimal_inputs_converted_explicitly(self):
        result = simple_return(
            Decimal("100.00"),
            Decimal("101.50"),
            adjustment_basis_t0=BASIS,
            adjustment_basis_t1=BASIS,
        )
        assert result == pytest.approx(0.015, rel=FLOAT64_REL_TOL)

    def test_flat_price_returns_positive_zero(self):
        result = simple_return(
            50.0, 50.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        assert result == 0.0
        assert math.copysign(1.0, result) == 1.0  # never -0.0

    @pytest.mark.parametrize("bad", [0, 0.0, -1, Decimal("-5"), Decimal("0")])
    def test_non_positive_price_rejected(self, bad):
        with pytest.raises(CalculationInputError) as exc:
            simple_return(bad, 10.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        assert exc.value.reason == "non_positive_price"
        with pytest.raises(CalculationInputError):
            simple_return(10.0, bad, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)

    def test_adjustment_basis_mismatch_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            simple_return(
                100.0,
                110.0,
                adjustment_basis_t0="split_adjusted",
                adjustment_basis_t1="unadjusted",
            )
        assert exc.value.reason == "adjustment_basis_mismatch"

    @pytest.mark.parametrize("bad_basis", ["", None, 3])
    def test_invalid_adjustment_basis_rejected(self, bad_basis):
        with pytest.raises(CalculationInputError) as exc:
            simple_return(
                100.0, 110.0, adjustment_basis_t0=bad_basis, adjustment_basis_t1=BASIS
            )
        assert exc.value.reason == "invalid_adjustment_basis"

    @pytest.mark.parametrize("bad", NON_FINITE_FLOATS + NON_FINITE_DECIMALS)
    def test_non_finite_price_rejected(self, bad):
        with pytest.raises(CalculationInputError) as exc:
            simple_return(bad, 10.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        assert exc.value.reason == "non_finite_input"

    @pytest.mark.parametrize("bad", [True, "100", None, [100.0]])
    def test_non_numeric_price_rejected(self, bad):
        with pytest.raises(CalculationInputError) as exc:
            simple_return(bad, 10.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        assert exc.value.reason == "invalid_type"


class TestLogReturn:
    def test_nominal(self):
        result = log_return(
            100.0, 110.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        assert result == pytest.approx(math.log(1.1), rel=FLOAT64_REL_TOL)

    def test_flat_price_is_zero(self):
        assert (
            log_return(42.0, 42.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
            == 0.0
        )

    def test_extreme_ratio_stays_finite(self):
        # log(p1) - log(p0) never overflows where p1/p0 would.
        result = log_return(
            1e-300, 1e300, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        assert math.isfinite(result)
        assert result == pytest.approx(600 * math.log(10.0), rel=FLOAT64_REL_TOL)

    def test_non_positive_price_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            log_return(0.0, 10.0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        assert exc.value.reason == "non_positive_price"

    def test_adjustment_basis_mismatch_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            log_return(
                100.0,
                110.0,
                adjustment_basis_t0="total_return",
                adjustment_basis_t1="unadjusted",
            )
        assert exc.value.reason == "adjustment_basis_mismatch"

    @pytest.mark.parametrize("bad", NON_FINITE_FLOATS + NON_FINITE_DECIMALS)
    def test_non_finite_price_rejected(self, bad):
        with pytest.raises(CalculationInputError) as exc:
            log_return(10.0, bad, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        assert exc.value.reason == "non_finite_input"


class TestRealizedVolatility:
    def test_nominal_two_returns(self):
        # mean 0, sample variance (1e-4 + 1e-4) / 1 = 2e-4, annualized by 252.
        result = realized_volatility([0.01, -0.01], 252)
        assert result == pytest.approx(math.sqrt(2e-4 * 252), rel=FLOAT64_REL_TOL)

    def test_nominal_four_returns(self):
        returns = [0.01, -0.01, 0.02, 0.0]
        mean = sum(returns) / 4
        variance = sum((r - mean) ** 2 for r in returns) / 3
        result = realized_volatility(returns, 252)
        assert result == pytest.approx(math.sqrt(variance * 252), rel=FLOAT64_REL_TOL)

    def test_constant_returns_give_zero(self):
        assert realized_volatility([0.005, 0.005, 0.005], 12) == 0.0

    def test_decimal_returns_accepted(self):
        result = realized_volatility([Decimal("0.01"), Decimal("-0.01")], Decimal("252"))
        assert result == pytest.approx(math.sqrt(2e-4 * 252), rel=FLOAT64_REL_TOL)

    @pytest.mark.parametrize("too_small", [[], [0.01]])
    def test_minimum_sample_gate(self, too_small):
        with pytest.raises(CalculationInputError) as exc:
            realized_volatility(too_small, 252)
        assert exc.value.reason == "minimum_sample"

    @pytest.mark.parametrize("bad_ppy", [0, -252, 0.0])
    def test_non_positive_periods_per_year_rejected(self, bad_ppy):
        with pytest.raises(CalculationInputError) as exc:
            realized_volatility([0.01, -0.01], bad_ppy)
        assert exc.value.reason == "invalid_annualization"

    @pytest.mark.parametrize("bad", NON_FINITE_FLOATS + NON_FINITE_DECIMALS)
    def test_non_finite_return_rejected(self, bad):
        with pytest.raises(CalculationInputError) as exc:
            realized_volatility([0.01, bad], 252)
        assert exc.value.reason == "non_finite_input"

    @pytest.mark.parametrize("bad_seq", ["0.01", 5, None, {"a": 1}])
    def test_non_sequence_rejected(self, bad_seq):
        with pytest.raises(CalculationInputError) as exc:
            realized_volatility(bad_seq, 252)
        assert exc.value.reason == "invalid_type"

    def test_overflowing_series_fails_closed(self):
        # Squared deviations overflow float64: INVALID, never inf.
        with pytest.raises(CalculationInputError) as exc:
            realized_volatility([1e308, -1e308], 252)
        assert exc.value.reason == "non_finite_result"


class TestAtr:
    def test_nominal_hand_checked(self):
        assert atr(coherent_bars(), 2) == pytest.approx(1.5, rel=FLOAT64_REL_TOL)

    def test_lookback_uses_only_last_true_ranges(self):
        assert atr(coherent_bars(), 1) == pytest.approx(1.0, rel=FLOAT64_REL_TOL)

    def test_gap_uses_previous_close(self):
        bars = [
            make_bar(0, "10", "11", "9", "10"),
            # Gap up: TR = max(16-14.5, |16-10|, |14.5-10|) = 6
            make_bar(1, "15", "16", "14.5", "15"),
        ]
        assert atr(bars, 1) == pytest.approx(6.0, rel=FLOAT64_REL_TOL)

    def test_result_non_negative(self):
        assert atr(coherent_bars(), 2) >= 0.0

    def test_minimum_sample_gate(self):
        with pytest.raises(CalculationInputError) as exc:
            atr(coherent_bars(), 3)  # needs 4 bars for lookback 3
        assert exc.value.reason == "minimum_sample"

    @pytest.mark.parametrize("bad_lookback", [0, -1])
    def test_invalid_lookback_rejected(self, bad_lookback):
        with pytest.raises(CalculationInputError) as exc:
            atr(coherent_bars(), bad_lookback)
        assert exc.value.reason == "invalid_lookback"

    def test_lookback_bool_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            atr(coherent_bars(), True)
        assert exc.value.reason == "invalid_type"

    def test_unordered_bars_rejected(self):
        bars = coherent_bars()
        with pytest.raises(CalculationInputError) as exc:
            atr([bars[1], bars[0], bars[2]], 2)
        assert exc.value.reason == "unordered_bars"

    def test_duplicate_timestamp_rejected(self):
        bars = coherent_bars()
        with pytest.raises(CalculationInputError) as exc:
            atr([bars[0], bars[0], bars[2]], 2)
        assert exc.value.reason == "unordered_bars"

    def test_high_below_low_rejected(self):
        bars = coherent_bars()
        bars[1] = make_bar(1, "10.2", "10.1", "10.3", "10.2")
        with pytest.raises(CalculationInputError) as exc:
            atr(bars, 2)
        assert exc.value.reason == "incomplete_bar"

    def test_high_below_close_rejected(self):
        bars = coherent_bars()
        bars[2] = make_bar(2, "11", "11.5", "10.5", "12")
        with pytest.raises(CalculationInputError) as exc:
            atr(bars, 2)
        assert exc.value.reason == "incomplete_bar"

    def test_low_above_open_rejected(self):
        bars = coherent_bars()
        bars[2] = make_bar(2, "10", "11.5", "10.5", "11")
        with pytest.raises(CalculationInputError) as exc:
            atr(bars, 2)
        assert exc.value.reason == "incomplete_bar"

    def test_incomplete_bar_outside_lookback_still_rejected(self):
        # The gate covers the whole series, not only the averaged window.
        bars = coherent_bars()
        bars[0] = make_bar(0, "10", "9.5", "9", "10")  # high < open
        with pytest.raises(CalculationInputError) as exc:
            atr(bars, 1)
        assert exc.value.reason == "incomplete_bar"

    def test_non_bar_element_rejected(self):
        bars = coherent_bars()
        with pytest.raises(CalculationInputError) as exc:
            atr([bars[0], {"open": 1}, bars[2]], 2)
        assert exc.value.reason == "invalid_type"

    def test_ohlc_bar_rejects_naive_timestamp(self):
        with pytest.raises(Exception):
            OhlcBar(
                timestamp=datetime(2026, 3, 2, 14, 30),  # naive: rejected
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10"),
            )

    def test_ohlc_bar_rejects_non_positive_price(self):
        with pytest.raises(Exception):
            make_bar(0, "10", "11", "0", "10")


class TestRelativeStrength:
    def test_nominal_outperformance(self):
        result = relative_strength((0.10, 0.10), (0.0, 0.0), 2)
        assert result == pytest.approx(1.21, rel=FLOAT64_REL_TOL)

    def test_horizon_selects_trailing_window(self):
        # Only the last period counts with horizon=1.
        result = relative_strength((9.0, 0.10), (0.0, 0.0), 1)
        assert result == pytest.approx(1.1, rel=FLOAT64_REL_TOL)

    def test_equal_series_give_one(self):
        series = (0.01, -0.02, 0.03)
        assert relative_strength(series, series, 3) == pytest.approx(
            1.0, rel=FLOAT64_REL_TOL
        )

    def test_decimal_returns_accepted(self):
        result = relative_strength(
            [Decimal("0.10")], [Decimal("0.05")], 1
        )
        assert result == pytest.approx(1.1 / 1.05, rel=FLOAT64_REL_TOL)

    def test_misaligned_calendars_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            relative_strength((0.01, 0.02), (0.01,), 1)
        assert exc.value.reason == "misaligned_calendars"

    @pytest.mark.parametrize("bad_horizon", [0, -3])
    def test_invalid_horizon_rejected(self, bad_horizon):
        with pytest.raises(CalculationInputError) as exc:
            relative_strength((0.01,), (0.02,), bad_horizon)
        assert exc.value.reason == "invalid_horizon"

    def test_horizon_beyond_history_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            relative_strength((0.01, 0.02), (0.0, 0.0), 3)
        assert exc.value.reason == "minimum_sample"

    @pytest.mark.parametrize("bad_return", [-1.0, -1.5, Decimal("-2")])
    def test_return_at_or_below_minus_one_rejected(self, bad_return):
        with pytest.raises(CalculationInputError) as exc:
            relative_strength((bad_return,), (0.0,), 1)
        assert exc.value.reason == "invalid_return"

    @pytest.mark.parametrize("bad", NON_FINITE_FLOATS + NON_FINITE_DECIMALS)
    def test_non_finite_return_rejected(self, bad):
        with pytest.raises(CalculationInputError) as exc:
            relative_strength((0.01, bad), (0.0, 0.0), 2)
        assert exc.value.reason == "non_finite_input"

    def test_benchmark_underflow_fails_closed(self):
        # Compounding tiny benchmark factors underflows to 0.0: INVALID.
        bench = tuple([-0.9999999999] * 40)
        asset = tuple([0.0] * 40)
        with pytest.raises(CalculationInputError) as exc:
            relative_strength(asset, bench, 40)
        assert exc.value.reason == "non_finite_result"


class TestBreadth:
    def test_nominal(self):
        result = breadth(60, 100, covered_count=90, coverage_threshold=0.8)
        assert result == pytest.approx(60 / 90, rel=FLOAT64_REL_TOL)

    def test_full_participation(self):
        assert breadth(90, 100, covered_count=90, coverage_threshold=0.5) == 1.0

    def test_zero_participation(self):
        assert breadth(0, 100, covered_count=100, coverage_threshold=1.0) == 0.0

    def test_threshold_accepts_decimal(self):
        result = breadth(30, 100, covered_count=80, coverage_threshold=Decimal("0.75"))
        assert result == pytest.approx(0.375, rel=FLOAT64_REL_TOL)

    def test_coverage_below_threshold_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            breadth(30, 100, covered_count=70, coverage_threshold=0.8)
        assert exc.value.reason == "coverage_below_threshold"

    def test_zero_coverage_always_rejected(self):
        # threshold > 0 makes covered_count = 0 unreachable: no 0/0 breadth.
        with pytest.raises(CalculationInputError) as exc:
            breadth(0, 100, covered_count=0, coverage_threshold=0.01)
        assert exc.value.reason == "coverage_below_threshold"

    def test_above_count_beyond_coverage_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            breadth(95, 100, covered_count=90, coverage_threshold=0.5)
        assert exc.value.reason == "invalid_count"

    def test_negative_above_count_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            breadth(-1, 100, covered_count=90, coverage_threshold=0.5)
        assert exc.value.reason == "invalid_count"

    def test_coverage_beyond_universe_rejected(self):
        with pytest.raises(CalculationInputError) as exc:
            breadth(10, 100, covered_count=101, coverage_threshold=0.5)
        assert exc.value.reason == "invalid_coverage"

    @pytest.mark.parametrize("bad_universe", [0, -10])
    def test_invalid_universe_rejected(self, bad_universe):
        with pytest.raises(CalculationInputError) as exc:
            breadth(0, bad_universe, covered_count=0, coverage_threshold=0.5)
        assert exc.value.reason == "invalid_universe"

    @pytest.mark.parametrize("bad_threshold", [0.0, -0.5, 1.5])
    def test_invalid_threshold_rejected(self, bad_threshold):
        with pytest.raises(CalculationInputError) as exc:
            breadth(10, 100, covered_count=100, coverage_threshold=bad_threshold)
        assert exc.value.reason == "invalid_threshold"

    @pytest.mark.parametrize("bad_count", [True, 10.0, "10", None])
    def test_non_int_counts_rejected(self, bad_count):
        with pytest.raises(CalculationInputError) as exc:
            breadth(bad_count, 100, covered_count=100, coverage_threshold=0.5)
        assert exc.value.reason == "invalid_type"


# --- Property-based invariants (Hypothesis) --------------------------------

prices = st.floats(
    min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False
)
# Composition identities pass through r = ratio - 1 then 1 + r, whose float64
# round trip loses relative precision proportional to 1/ratio. The documented
# tolerance (FLOAT64_REL_TOL) therefore applies to bounded ratios: with prices
# in [1e-2, 1e3] the ratio stays within [1e-5, 1e5] and the round-trip error
# is <= ~2.2e-16 / 1e-5 ~ 2.2e-11 relative, comfortably inside 1e-9.
composition_prices = st.floats(
    min_value=1e-2, max_value=1e3, allow_nan=False, allow_infinity=False
)
period_returns = st.floats(
    min_value=-0.9, max_value=10.0, allow_nan=False, allow_infinity=False
)
non_finite = st.sampled_from(NON_FINITE_FLOATS + NON_FINITE_DECIMALS)


@st.composite
def coherent_bar_series(draw):
    """Ordered coherent OHLC bars plus a valid lookback."""
    count = draw(st.integers(min_value=2, max_value=12))
    bars = []
    for i in range(count):
        open_ = draw(st.floats(min_value=1.0, max_value=1000.0))
        close = draw(st.floats(min_value=1.0, max_value=1000.0))
        span_up = draw(st.floats(min_value=0.0, max_value=0.1))
        span_down = draw(st.floats(min_value=0.0, max_value=0.1))
        high = max(open_, close) * (1.0 + span_up)
        low = min(open_, close) * (1.0 - span_down)
        bars.append(
            OhlcBar(
                timestamp=BASE_TS + timedelta(minutes=i),
                open=Decimal(str(open_)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
            )
        )
    lookback = draw(st.integers(min_value=1, max_value=count - 1))
    return bars, lookback


@pytest.mark.property
class TestReturnCompositionProperties:
    @given(p0=prices, p1=prices, p2=prices)
    def test_log_returns_compose_additively(self, p0, p1, p2):
        direct = log_return(
            p0, p2, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        composed = log_return(
            p0, p1, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        ) + log_return(p1, p2, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        assert math.isclose(direct, composed, rel_tol=FLOAT64_REL_TOL, abs_tol=1e-9)

    @given(p0=composition_prices, p1=composition_prices, p2=composition_prices)
    def test_simple_returns_compose_multiplicatively(self, p0, p1, p2):
        direct = 1.0 + simple_return(
            p0, p2, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        composed = (
            1.0
            + simple_return(p0, p1, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        ) * (
            1.0
            + simple_return(p1, p2, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        )
        assert math.isclose(
            direct, composed, rel_tol=FLOAT64_REL_TOL, abs_tol=FLOAT64_ABS_TOL
        )

    @given(p0=composition_prices, p1=composition_prices)
    def test_log_return_matches_log1p_of_simple_return(self, p0, p1):
        via_log = log_return(
            p0, p1, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        via_simple = math.log1p(
            simple_return(p0, p1, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS)
        )
        assert math.isclose(via_log, via_simple, rel_tol=FLOAT64_REL_TOL, abs_tol=1e-12)

    @given(p0=prices, p1=prices)
    def test_simple_return_bounded_below_and_finite(self, p0, p1):
        result = simple_return(
            p0, p1, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        assert math.isfinite(result)
        assert result > -1.0

    @given(p0=prices, p1=prices)
    def test_return_antisymmetry(self, p0, p1):
        forward = log_return(
            p0, p1, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        backward = log_return(
            p1, p0, adjustment_basis_t0=BASIS, adjustment_basis_t1=BASIS
        )
        assert math.isclose(forward, -backward, rel_tol=FLOAT64_REL_TOL, abs_tol=1e-12)


@pytest.mark.property
class TestVolatilityProperties:
    @given(
        returns=st.lists(period_returns, min_size=2, max_size=50),
        ppy=st.sampled_from([12, 52, 252, 78840]),
    )
    def test_non_negative_and_finite(self, returns, ppy):
        result = realized_volatility(returns, ppy)
        assert result >= 0.0
        assert math.isfinite(result)

    @given(
        value=period_returns,
        n=st.integers(min_value=2, max_value=20),
        ppy=st.sampled_from([12, 252]),
    )
    def test_constant_series_has_zero_volatility(self, value, n, ppy):
        # The float64 mean of n identical values is exact only up to 1 ulp,
        # so the volatility of a constant series is zero within
        # ~eps * |value| * sqrt(ppy) (documented float64 tolerance).
        bound = 1e-12 * max(1.0, abs(value)) * math.sqrt(ppy)
        assert 0.0 <= realized_volatility([value] * n, ppy) <= bound

    @given(
        returns=st.lists(period_returns, min_size=2, max_size=20),
        bad=non_finite,
        ppy=st.sampled_from([252]),
    )
    def test_any_non_finite_return_rejected(self, returns, bad, ppy):
        with pytest.raises(CalculationInputError) as exc:
            realized_volatility(returns + [bad], ppy)
        assert exc.value.reason == "non_finite_input"


@pytest.mark.property
class TestAtrProperties:
    @given(data=coherent_bar_series())
    def test_non_negative_and_finite(self, data):
        bars, lookback = data
        result = atr(bars, lookback)
        assert result >= 0.0
        assert math.isfinite(result)


@pytest.mark.property
class TestRelativeStrengthProperties:
    @given(
        asset=st.lists(period_returns, min_size=1, max_size=20),
        bench=st.lists(period_returns, min_size=1, max_size=20),
        data=st.data(),
    )
    def test_finite_and_positive_on_aligned_series(self, asset, bench, data):
        size = min(len(asset), len(bench))
        asset, bench = asset[:size], bench[:size]
        horizon = data.draw(st.integers(min_value=1, max_value=size))
        result = relative_strength(asset, bench, horizon)
        assert math.isfinite(result)
        assert result > 0.0

    @given(series=st.lists(period_returns, min_size=1, max_size=20))
    def test_identical_series_give_one(self, series):
        result = relative_strength(series, series, len(series))
        assert math.isclose(result, 1.0, rel_tol=FLOAT64_REL_TOL)


@pytest.mark.property
class TestBreadthProperties:
    @given(universe=st.integers(min_value=1, max_value=500), data=st.data())
    def test_ratio_within_zero_one(self, universe, data):
        covered = data.draw(st.integers(min_value=1, max_value=universe))
        above = data.draw(st.integers(min_value=0, max_value=covered))
        coverage = covered / universe
        threshold = data.draw(
            st.floats(
                min_value=1e-9,
                max_value=coverage,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        result = breadth(
            above, universe, covered_count=covered, coverage_threshold=threshold
        )
        assert 0.0 <= result <= 1.0
        # Registry invariant between_minus_one_and_one is a superset of [0, 1].
        assert -1.0 <= result <= 1.0
