"""decision.risk_reward: golden vector, every INVALID branch, property invariants.

All fixtures are SYNTHETIC and deterministic; no network, no real market data,
no unseeded randomness (Hypothesis manages its own reproducible search).
"""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vertex_core.contracts.enums import CalculationStatus
from vertex_core.decision.risk_reward import (
    RiskRewardInputError,
    RiskRewardResult,
    risk_reward,
)


def valid_kwargs(**overrides) -> dict:
    """Baseline valid long scenario; override single fields per test."""
    kwargs = {
        "entry": Decimal("100"),
        "stop": Decimal("95"),
        "target": Decimal("115"),
        "multiplier": 1,
        "costs": Decimal("1"),
        "currency_match": True,
        "horizon_defined": True,
    }
    kwargs.update(overrides)
    return kwargs


class TestGolden:
    @pytest.mark.golden
    def test_hand_checked_vector(self):
        """Provenance: DECISION_ENGINE.md formula, hand-checked 2026-08-28.

        E=100, S=95, T=115, M=1, C=1:
        risk = (100-95)*1 + 1 = 6 ; reward = (115-100)*1 - 1 = 14 ;
        ratio = 14/6 = 2.333...
        """
        result = risk_reward(**valid_kwargs())
        assert result.status is CalculationStatus.OK
        assert result.risk == Decimal("6")
        assert result.reward == Decimal("14")
        assert result.ratio == Decimal("14") / Decimal("6")
        assert result.reason is None

    @pytest.mark.golden
    def test_multiplier_and_costs_vector(self):
        """E=50, S=48, T=56, M=100, C=30: risk=2*100+30=230; reward=6*100-30=570."""
        result = risk_reward(
            entry=Decimal("50"),
            stop=Decimal("48"),
            target=Decimal("56"),
            multiplier=100,
            costs=Decimal("30"),
            currency_match=True,
            horizon_defined=True,
        )
        assert result.status is CalculationStatus.OK
        assert result.risk == Decimal("230")
        assert result.reward == Decimal("570")
        assert result.ratio == Decimal("570") / Decimal("230")


class TestInvalidBranches:
    @pytest.mark.parametrize("field", [
        "entry", "stop", "target", "multiplier", "costs", "currency_match", "horizon_defined",
    ])
    def test_missing_input(self, field):
        result = risk_reward(**valid_kwargs(**{field: None}))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "MISSING_INPUT"
        assert result.ratio is None and result.risk is None and result.reward is None

    @pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
    @pytest.mark.parametrize("field", ["entry", "stop", "target", "costs"])
    def test_non_finite_input(self, field, value):
        result = risk_reward(**valid_kwargs(**{field: value}))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "NON_FINITE_INPUT"

    @pytest.mark.parametrize("multiplier", [0, -1, -100])
    def test_invalid_multiplier(self, multiplier):
        result = risk_reward(**valid_kwargs(multiplier=multiplier))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "INVALID_MULTIPLIER"

    def test_negative_costs(self):
        result = risk_reward(**valid_kwargs(costs=Decimal("-0.01")))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "NEGATIVE_COSTS"

    @pytest.mark.parametrize("overrides", [
        {"entry": Decimal("0")},
        {"entry": Decimal("-1"), "stop": Decimal("-2")},
        {"stop": Decimal("0"), "entry": Decimal("1"), "target": Decimal("2")},
        {"target": Decimal("-5")},
    ])
    def test_non_positive_price(self, overrides):
        result = risk_reward(**valid_kwargs(**overrides))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "NON_POSITIVE_PRICE"

    def test_currency_mismatch(self):
        result = risk_reward(**valid_kwargs(currency_match=False))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "CURRENCY_MISMATCH"

    def test_horizon_undefined(self):
        result = risk_reward(**valid_kwargs(horizon_defined=False))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "HORIZON_UNDEFINED"

    @pytest.mark.parametrize("stop", [Decimal("100"), Decimal("101")])
    def test_stop_not_below_entry(self, stop):
        result = risk_reward(**valid_kwargs(stop=stop))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "STOP_NOT_BELOW_ENTRY"
        assert result.ratio is None

    @pytest.mark.parametrize("target", [Decimal("100"), Decimal("99.99")])
    def test_target_not_above_entry(self, target):
        result = risk_reward(**valid_kwargs(target=target))
        assert result.status is CalculationStatus.INVALID
        assert result.reason == "TARGET_NOT_ABOVE_ENTRY"
        assert result.ratio is None

    def test_invalid_result_exposes_no_partial_figure(self):
        result = risk_reward(**valid_kwargs(currency_match=False))
        assert (result.ratio, result.risk, result.reward) == (None, None, None)


class TestTypedErrors:
    @pytest.mark.parametrize("field, value", [
        ("entry", 100.0),
        ("stop", 95),
        ("target", "115"),
        ("costs", 1.0),
        ("multiplier", 1.0),
        ("multiplier", True),
        ("currency_match", 1),
        ("horizon_defined", "yes"),
    ])
    def test_wrong_type_raises(self, field, value):
        with pytest.raises(RiskRewardInputError):
            risk_reward(**valid_kwargs(**{field: value}))


class TestFinancialSemantics:
    def test_costs_reduce_reward(self):
        """Registry invariant costs_reduce_reward: higher costs => lower reward and ratio."""
        cheap = risk_reward(**valid_kwargs(costs=Decimal("0.50")))
        expensive = risk_reward(**valid_kwargs(costs=Decimal("2.50")))
        assert cheap.status is CalculationStatus.OK
        assert expensive.status is CalculationStatus.OK
        assert expensive.reward < cheap.reward
        assert expensive.risk > cheap.risk
        assert expensive.ratio < cheap.ratio

    def test_zero_costs_allowed(self):
        result = risk_reward(**valid_kwargs(costs=Decimal("0")))
        assert result.status is CalculationStatus.OK
        assert result.risk == Decimal("5")
        assert result.reward == Decimal("15")
        assert result.ratio == Decimal("3")

    def test_costs_may_turn_reward_negative_without_invalidating(self):
        """Costs above the gross reward yield an honest ratio <= 0, not a fake figure."""
        result = risk_reward(**valid_kwargs(target=Decimal("100.50"), costs=Decimal("1")))
        assert result.status is CalculationStatus.OK
        assert result.reward == Decimal("-0.50")
        assert result.ratio < 0

    def test_ratio_is_a_ratio_not_a_score(self):
        """Large favorable geometry gives a ratio far above any 0-100-style bound's shape."""
        result = risk_reward(
            entry=Decimal("100"),
            stop=Decimal("99.99"),
            target=Decimal("200"),
            multiplier=1,
            costs=Decimal("0"),
            currency_match=True,
            horizon_defined=True,
        )
        assert result.status is CalculationStatus.OK
        # reward = 100, risk = 0.01 -> ratio 10000: far outside any 0-100 score shape.
        assert result.ratio == Decimal("100") / Decimal("0.01")

    def test_result_model_rejects_ok_without_figures(self):
        with pytest.raises(Exception):  # noqa: B017 (contrat du test inchangé (resserrement = dette, cf. DEBT.md))
            RiskRewardResult(status=CalculationStatus.OK)

    def test_result_model_rejects_not_implemented_status(self):
        with pytest.raises(Exception):  # noqa: B017 (contrat du test inchangé (resserrement = dette, cf. DEBT.md))
            RiskRewardResult(status=CalculationStatus.NOT_IMPLEMENTED, reason="X")


PRICES = st.decimals(
    min_value=Decimal("0.01"), max_value=Decimal("100000"),
    places=4, allow_nan=False, allow_infinity=False,
)
COSTS = st.decimals(
    min_value=Decimal("0"), max_value=Decimal("1000"),
    places=4, allow_nan=False, allow_infinity=False,
)
MULTIPLIERS = st.integers(min_value=1, max_value=10000)


@pytest.mark.property
class TestProperties:
    @given(
        entry=PRICES, stop=PRICES, target=PRICES,
        multiplier=MULTIPLIERS, costs=COSTS,
        currency_match=st.booleans(), horizon_defined=st.booleans(),
    )
    def test_never_a_ratio_when_risk_not_positive_finite_otherwise(
        self, entry, stop, target, multiplier, costs, currency_match, horizon_defined
    ):
        """Never a ratio unless every gate holds and risk > 0; then it is finite and exact."""
        result = risk_reward(
            entry, stop, target, multiplier, costs, currency_match, horizon_defined
        )
        gates_hold = currency_match and horizon_defined and stop < entry < target
        if result.status is CalculationStatus.OK:
            assert gates_hold
            expected_risk = (entry - stop) * multiplier + costs
            expected_reward = (target - entry) * multiplier - costs
            assert result.risk == expected_risk
            assert result.risk > 0
            assert result.reward == expected_reward
            assert result.ratio is not None and result.ratio.is_finite()
            assert result.ratio == expected_reward / expected_risk
            assert result.reason is None
        else:
            # No ratio ever leaves an invalid evaluation (risk <= 0 included).
            assert result.status is CalculationStatus.INVALID
            assert result.ratio is None and result.risk is None and result.reward is None
            assert result.reason

    @given(
        entry=st.decimals(min_value=Decimal("10"), max_value=Decimal("1000"), places=2,
                          allow_nan=False, allow_infinity=False),
        stop_gap=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("5"), places=2,
                             allow_nan=False, allow_infinity=False),
        target_gap=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("50"), places=2,
                               allow_nan=False, allow_infinity=False),
        multiplier=st.integers(min_value=1, max_value=100),
        costs=st.decimals(min_value=Decimal("0"), max_value=Decimal("10"), places=2,
                          allow_nan=False, allow_infinity=False),
        extra_costs=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10"), places=2,
                                allow_nan=False, allow_infinity=False),
    )
    def test_costs_reduce_reward_property(
        self, entry, stop_gap, target_gap, multiplier, costs, extra_costs
    ):
        """Registry invariant: strictly higher costs strictly reduce reward and ratio."""
        stop = entry - stop_gap
        target = entry + target_gap
        base = risk_reward(entry, stop, target, multiplier, costs, True, True)
        pricier = risk_reward(entry, stop, target, multiplier, costs + extra_costs, True, True)
        assert base.status is CalculationStatus.OK
        assert pricier.status is CalculationStatus.OK
        assert pricier.reward < base.reward
        assert pricier.risk > base.risk
        assert pricier.ratio < base.ratio
