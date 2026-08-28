"""performance calculations: twr, xirr and drawdown."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from vertex_core.calculations.performance import (
    XIRR_NPV_TOLERANCE_SCALE,
    CashflowBoundaryError,
    CashflowEvent,
    DrawdownResult,
    PerformanceCalculationError,
    SignChangeError,
    Valuation,
    XirrResult,
    drawdown,
    twr,
    xirr,
)
from vertex_core.contracts.enums import CalculationStatus

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def val(days, value):
    return Valuation(at=T0 + timedelta(days=days), value=Decimal(value))


def flow(days, amount):
    return CashflowEvent(at=T0 + timedelta(days=days), amount=Decimal(amount))


def curve(values):
    return [val(i, v) for i, v in enumerate(values)]


class TestInputModels:
    def test_naive_valuation_rejected(self):
        with pytest.raises(ValidationError, match="naive"):
            Valuation(at=datetime(2026, 1, 1), value=Decimal("1"))

    def test_negative_valuation_rejected(self):
        with pytest.raises(ValidationError):
            Valuation(at=T0, value=Decimal("-1"))

    def test_nan_cashflow_rejected(self):
        with pytest.raises(ValidationError):
            CashflowEvent(at=T0, amount=Decimal("NaN"))

    def test_xirr_result_invalid_must_not_carry_numbers(self):
        with pytest.raises(ValidationError):
            XirrResult(status=CalculationStatus.INVALID, rate=0.1, reason="broken")

    def test_xirr_result_ok_requires_numbers(self):
        with pytest.raises(ValidationError):
            XirrResult(status=CalculationStatus.OK)

    def test_drawdown_result_rejects_positive_drawdown(self):
        with pytest.raises(ValidationError):
            DrawdownResult(max_drawdown=Decimal("0.1"), drawdowns=(Decimal("0.1"),))


class TestTwr:
    @pytest.mark.golden
    def test_golden_two_period_hand_computed(self):
        # Provenance — hand computation (documented 2026-08-28):
        #   t0 = 2026-01-01: V0 = 100, no flow.
        #   t1 = 2026-02-01: V1 = 110 -> period 1 growth = 110/100 = 1.10.
        #     External contribution +50 arrives just after the t1 valuation
        #     (documented convention), so period 2 starts from 110+50 = 160.
        #   t2 = 2026-03-01: V2 = 176 -> period 2 growth = 176/160 = 1.10.
        #   TWR = 1.10 * 1.10 - 1 = 0.21 ; period returns (0.10, 0.10).
        result = twr(
            [val(0, "100"), val(31, "110"), val(59, "176")],
            [flow(31, "50")],
        )
        assert result.total_return == Decimal("0.21")
        assert result.period_returns == (Decimal("0.10"), Decimal("0.10"))

    def test_no_flow_same_growth_same_twr(self):
        # Same per-period growth without any flow gives the same TWR.
        result = twr([val(0, "100"), val(31, "110"), val(59, "121")])
        assert result.total_return == Decimal("0.21")

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(
        contribution=st.decimals(
            min_value=Decimal("0"), max_value=Decimal("1e6"), places=2, allow_nan=False, allow_infinity=False
        )
    )
    def test_cashflow_timing_neutrality(self, contribution):
        # Invariant cashflow_timing_neutrality: whatever external capital
        # arrives at the boundary, the chained return of identical
        # per-period growth (10% then 10%) stays exactly 0.21.
        base = Decimal("110") + contribution
        final = base * Decimal("1.1")  # exact: both periods grow 10%
        result = twr(
            [val(0, "100"), val(31, "110"), val(59, str(final))],
            [flow(31, str(contribution))],
        )
        assert result.total_return == Decimal("0.21")

    def test_withdrawal_at_boundary(self):
        # V1=110, withdrawal -10 just after t1 -> period 2 starts at 100.
        result = twr([val(0, "100"), val(31, "110"), val(59, "105")], [flow(31, "-10")])
        assert result.period_returns == (Decimal("0.10"), Decimal("0.05"))

    def test_flows_netted_at_same_boundary(self):
        result = twr(
            [val(0, "100"), val(31, "110"), val(59, "160")],
            [flow(31, "80"), flow(31, "-30")],  # net +50 -> base 160
        )
        assert result.period_returns[1] == Decimal("0")

    def test_flow_at_final_valuation_cannot_affect_result(self):
        with_flow = twr([val(0, "100"), val(31, "110")], [flow(31, "1000")])
        without = twr([val(0, "100"), val(31, "110")])
        assert with_flow == without

    def test_flow_off_boundary_rejected(self):
        with pytest.raises(CashflowBoundaryError, match="complete cashflow boundaries"):
            twr([val(0, "100"), val(31, "110")], [flow(15, "50")])

    def test_flow_before_first_valuation_rejected(self):
        with pytest.raises(CashflowBoundaryError):
            twr([val(0, "100"), val(31, "110")], [flow(-5, "50")])

    def test_fewer_than_two_valuations_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="at least two"):
            twr([val(0, "100")])

    def test_unordered_valuations_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="strictly increasing"):
            twr([val(5, "100"), val(1, "110")])

    def test_duplicate_valuation_timestamps_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="strictly increasing"):
            twr([val(0, "100"), val(0, "110")])

    def test_non_positive_capital_base_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="capital base"):
            twr([val(0, "100"), val(31, "110")], [flow(0, "-100")])

    def test_wrong_element_type_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="Valuation"):
            twr([("2026-01-01", 100), ("2026-01-02", 101)])


class TestXirr:
    @pytest.mark.golden
    def test_golden_one_year_ten_percent(self):
        # Provenance — hand computation (documented 2026-08-28):
        #   -1000 on 2019-01-01, +1100 on 2020-01-01 = exactly 365 days
        #   = 1.0 year under ACT/365F.
        #   NPV(r) = -1000 + 1100/(1+r) = 0  <=>  r = 0.10 exactly.
        d0 = datetime(2019, 1, 1, tzinfo=timezone.utc)
        result = xirr(
            [
                CashflowEvent(at=d0, amount=Decimal("-1000")),
                CashflowEvent(at=d0 + timedelta(days=365), amount=Decimal("1100")),
            ]
        )
        assert result.status is CalculationStatus.OK
        assert result.rate == pytest.approx(0.10, abs=1e-9)
        assert abs(result.npv_at_rate) <= XIRR_NPV_TOLERANCE_SCALE * 2100.0

    @pytest.mark.oracle
    def test_oracle_polynomial_root_via_numpy(self):
        # Oracle — independent computation (numpy.roots, not brentq):
        # flows at exact 365-day spacing make NPV a polynomial in
        # x = 1/(1+r):  p(x) = 500 x^3 + 400 x^2 + 300 x - 1000.
        # Its unique positive real root x* gives the oracle rate 1/x* - 1.
        roots = np.roots([500.0, 400.0, 300.0, -1000.0])
        real_positive = [r.real for r in roots if abs(r.imag) < 1e-12 and r.real > 0.0]
        assert len(real_positive) == 1
        oracle_rate = 1.0 / real_positive[0] - 1.0

        d0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        amounts = ["-1000", "300", "400", "500"]
        flows = [
            CashflowEvent(at=d0 + timedelta(days=365 * k), amount=Decimal(a))
            for k, a in enumerate(amounts)
        ]
        result = xirr(flows)
        assert result.status is CalculationStatus.OK
        assert result.rate == pytest.approx(oracle_rate, abs=1e-9)
        assert abs(result.npv_at_rate) <= XIRR_NPV_TOLERANCE_SCALE * 2200.0

    def test_deterministic(self):
        d0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        flows = [
            CashflowEvent(at=d0, amount=Decimal("-500")),
            CashflowEvent(at=d0 + timedelta(days=200), amount=Decimal("120")),
            CashflowEvent(at=d0 + timedelta(days=400), amount=Decimal("450")),
        ]
        assert xirr(flows) == xirr(flows)

    def test_unsorted_input_same_result(self):
        d0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        a = CashflowEvent(at=d0, amount=Decimal("-1000"))
        b = CashflowEvent(at=d0 + timedelta(days=365), amount=Decimal("1100"))
        assert xirr([a, b]) == xirr([b, a])

    def test_no_sign_change_rejected(self):
        with pytest.raises(SignChangeError, match="strictly positive"):
            xirr([flow(0, "100"), flow(365, "100")])

    def test_zero_amounts_do_not_count_as_sign_change(self):
        with pytest.raises(SignChangeError):
            xirr([flow(0, "0"), flow(365, "100")])

    def test_single_instant_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="one instant"):
            xirr([flow(0, "-100"), flow(0, "100")])

    def test_fewer_than_two_flows_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="at least two"):
            xirr([flow(0, "-100")])

    def test_no_bracket_returns_invalid_not_a_number(self):
        # NPV(x) = -100 + 235 x - 139 x^2 (x = 1/(1+r)) has negative
        # discriminant (235^2 - 4*139*100 = -375): no real root exists.
        result = xirr([flow(0, "-100"), flow(365, "235"), flow(730, "-139")])
        assert result.status is CalculationStatus.INVALID
        assert result.rate is None
        assert result.npv_at_rate is None
        assert "bracket" in result.reason

    def test_multiple_roots_return_invalid(self):
        # NPV(x) = -100 + 235 x - 137 x^2 has two real roots
        # (r ~ 7.2% and r ~ 27.8%): the root is not unique -> INVALID.
        result = xirr([flow(0, "-100"), flow(365, "235"), flow(730, "-137")])
        assert result.status is CalculationStatus.INVALID
        assert result.rate is None
        assert "not unique" in result.reason

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(
        outflow=st.decimals(min_value=Decimal("100"), max_value=Decimal("1e6"), places=2, allow_nan=False, allow_infinity=False),
        growth_bp=st.integers(min_value=-5000, max_value=20000),
        days=st.integers(min_value=365, max_value=3650),
    )
    def test_npv_at_root_within_documented_tolerance(self, outflow, growth_bp, days):
        # For -X then +X*(1+g) with horizon >= 1 year the annualized root
        # stays inside the documented grid and satisfies |NPV| <= tol.
        inflow = outflow * (Decimal("1") + Decimal(growth_bp) / Decimal("10000"))
        result = xirr([flow(0, str(-outflow)), flow(days, str(inflow))])
        assert result.status is CalculationStatus.OK
        assert abs(result.npv_at_rate) <= XIRR_NPV_TOLERANCE_SCALE * float(outflow + inflow)


class TestDrawdown:
    @pytest.mark.golden
    def test_golden_hand_vector(self):
        # Provenance — hand computation (documented 2026-08-28):
        #   values      100  120   90    96  130   65
        #   running max 100  120  120   120  130  130
        #   drawdown      0    0  -0.25 -0.2   0  -0.5
        #   (90/120 - 1 = -0.25 ; 96/120 - 1 = -0.2 ; 65/130 - 1 = -0.5)
        #   max drawdown -0.5, trough at t5, peak set at t4 (130).
        result = drawdown(curve(["100", "120", "90", "96", "130", "65"]))
        assert result.drawdowns == (
            Decimal("0"),
            Decimal("0"),
            Decimal("-0.25"),
            Decimal("-0.2"),
            Decimal("0"),
            Decimal("-0.5"),
        )
        assert result.max_drawdown == Decimal("-0.5")
        assert result.trough_at == T0 + timedelta(days=5)
        assert result.peak_at == T0 + timedelta(days=4)

    def test_monotone_curve_has_zero_drawdown(self):
        result = drawdown(curve(["100", "101", "150"]))
        assert result.max_drawdown == Decimal("0")
        assert all(dd == 0 for dd in result.drawdowns)
        assert result.peak_at is None and result.trough_at is None

    def test_single_point_curve(self):
        result = drawdown([val(0, "100")])
        assert result.max_drawdown == Decimal("0")
        assert result.drawdowns == (Decimal("0"),)

    def test_first_trough_reported(self):
        # Two equal troughs at -0.5: the first one (t1) is reported.
        result = drawdown(curve(["100", "50", "100", "50"]))
        assert result.max_drawdown == Decimal("-0.5")
        assert result.trough_at == T0 + timedelta(days=1)
        assert result.peak_at == T0

    def test_empty_curve_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="at least one"):
            drawdown([])

    def test_unordered_curve_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="strictly increasing"):
            drawdown([val(3, "100"), val(1, "90")])

    def test_zero_value_rejected(self):
        with pytest.raises(PerformanceCalculationError, match="strictly positive"):
            drawdown([val(0, "100"), val(1, "0")])

    @pytest.mark.property
    @settings(max_examples=200, deadline=None)
    @given(
        values=st.lists(
            st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1e6"), places=4, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=20,
        )
    )
    def test_drawdown_always_non_positive(self, values):
        result = drawdown(curve([str(v) for v in values]))
        assert result.max_drawdown <= 0
        assert all(dd <= 0 for dd in result.drawdowns)
        assert result.max_drawdown == min(result.drawdowns)
