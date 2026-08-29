"""Gate catalog: every PASS/DEGRADE/BLOCK branch of every gate, plus UNEVALUABLE.

All fixtures are SYNTHETIC and deterministic; no network, no clock, no
randomness. Fail-closed rule under test: any missing/invalid input makes the
gate BLOCK with reason_code='UNEVALUABLE'.
"""

from decimal import Decimal

import pytest

from vertex_core.contracts.decision import GateResult
from vertex_core.contracts.enums import (
    AssetClass,
    CalculationStatus,
    GateStatus,
    IdentityStatus,
    SnapshotQuality,
    SourceCapabilityStatus,
)
from vertex_core.decision.gates import (
    GATE_CATALOG,
    GATE_ORDER,
    GATE_VERSIONS,
    REASON_UNEVALUABLE,
    evaluate_calculations_valid,
    evaluate_critical_contradictions_resolved,
    evaluate_entitlements_sufficient,
    evaluate_instrument_resolved,
    evaluate_manual_portfolio_risk_available,
    evaluate_minimum_liquidity,
    evaluate_probability_calibrated_if_used,
    evaluate_session_and_event_known,
    evaluate_snapshot_fresh_and_coherent,
    evaluate_user_constraints_versioned,
)

EXPECTED_ORDER = (
    "instrument_resolved",
    "entitlements_sufficient",
    "snapshot_fresh_and_coherent",
    "session_and_event_known",
    "minimum_liquidity",
    "calculations_valid",
    "manual_portfolio_risk_available",
    "probability_calibrated_if_used",
    "critical_contradictions_resolved",
    "user_constraints_versioned",
)


def assert_unevaluable(result: GateResult) -> None:
    assert result.status is GateStatus.BLOCK
    assert result.reason_code == REASON_UNEVALUABLE


class TestCatalog:
    def test_ten_gates_in_documented_order(self):
        assert GATE_ORDER == EXPECTED_ORDER
        assert tuple(spec.gate_id for spec in GATE_CATALOG) == EXPECTED_ORDER
        assert len(GATE_CATALOG) == 10

    def test_every_gate_is_versioned(self):
        for spec in GATE_CATALOG:
            assert spec.version
            assert GATE_VERSIONS[spec.gate_id] == spec.version

    def test_every_evaluator_stamps_id_and_version(self):
        """Even the all-None (UNEVALUABLE) result of each gate carries its id and version."""
        import inspect

        for spec in GATE_CATALOG:
            params = inspect.signature(spec.evaluate).parameters
            result = spec.evaluate(**{name: None for name in params})
            assert result.gate_id == spec.gate_id
            assert result.version == spec.version
            assert_unevaluable(result)


class TestInstrumentResolved:
    def test_missing_status_unevaluable(self):
        assert_unevaluable(evaluate_instrument_resolved(
            identity_status=None, resolved_with_conid=True))

    def test_missing_conid_flag_unevaluable(self):
        assert_unevaluable(evaluate_instrument_resolved(
            identity_status=IdentityStatus.RESOLVED, resolved_with_conid=None))

    def test_unresolved_blocks(self):
        result = evaluate_instrument_resolved(
            identity_status=IdentityStatus.UNRESOLVED, resolved_with_conid=True)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "UNRESOLVED_IDENTITY"

    def test_ambiguous_blocks(self):
        result = evaluate_instrument_resolved(
            identity_status=IdentityStatus.AMBIGUOUS, resolved_with_conid=True)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "AMBIGUOUS_IDENTITY"

    def test_resolved_without_conid_degrades(self):
        result = evaluate_instrument_resolved(
            identity_status=IdentityStatus.RESOLVED, resolved_with_conid=False)
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "RESOLVED_WITHOUT_CONID"

    def test_resolved_passes(self):
        result = evaluate_instrument_resolved(
            identity_status=IdentityStatus.RESOLVED, resolved_with_conid=True)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "RESOLVED"


class TestEntitlementsSufficient:
    def test_missing_unevaluable(self):
        assert_unevaluable(evaluate_entitlements_sufficient(capability_status=None))

    def test_available_passes(self):
        result = evaluate_entitlements_sufficient(
            capability_status=SourceCapabilityStatus.AVAILABLE)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "ENTITLED"

    @pytest.mark.parametrize("status, reason", [
        (SourceCapabilityStatus.DELAYED, "DELAYED_DATA_ENTITLEMENT"),
        (SourceCapabilityStatus.MANUAL_EXPORT, "MANUAL_EXPORT_SOURCE"),
    ])
    def test_degrade_branches(self, status, reason):
        result = evaluate_entitlements_sufficient(capability_status=status)
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == reason

    @pytest.mark.parametrize("status, reason", [
        (SourceCapabilityStatus.NOT_ENTITLED, "NOT_ENTITLED"),
        (SourceCapabilityStatus.UNSUPPORTED, "UNSUPPORTED_CAPABILITY"),
        (SourceCapabilityStatus.ERROR, "SOURCE_ERROR"),
    ])
    def test_block_branches(self, status, reason):
        result = evaluate_entitlements_sufficient(capability_status=status)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == reason


class TestSnapshotFreshAndCoherent:
    @pytest.mark.parametrize("kwargs", [
        {"quality": None, "fresh": True},
        {"quality": SnapshotQuality.GOOD, "fresh": None},
    ])
    def test_missing_inputs_unevaluable(self, kwargs):
        assert_unevaluable(evaluate_snapshot_fresh_and_coherent(**kwargs))

    def test_contradictory_blocks(self):
        result = evaluate_snapshot_fresh_and_coherent(
            quality=SnapshotQuality.CONTRADICTORY, fresh=True)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "CONTRADICTORY_SNAPSHOT"

    def test_missing_snapshot_blocks_as_missing_data(self):
        result = evaluate_snapshot_fresh_and_coherent(
            quality=SnapshotQuality.MISSING, fresh=True)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "MISSING_SNAPSHOT"

    def test_stale_blocks(self):
        result = evaluate_snapshot_fresh_and_coherent(
            quality=SnapshotQuality.GOOD, fresh=False)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "STALE_SNAPSHOT"

    def test_good_and_fresh_passes(self):
        result = evaluate_snapshot_fresh_and_coherent(
            quality=SnapshotQuality.GOOD, fresh=True)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "FRESH_AND_COHERENT"

    @pytest.mark.parametrize("quality, reason", [
        (SnapshotQuality.PARTIAL, "PARTIAL_SNAPSHOT"),
        (SnapshotQuality.DEGRADED, "DEGRADED_SNAPSHOT"),
    ])
    def test_partial_or_degraded_degrades(self, quality, reason):
        result = evaluate_snapshot_fresh_and_coherent(quality=quality, fresh=True)
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == reason


class TestSessionAndEventKnown:
    @pytest.mark.parametrize("kwargs", [
        {"session_known": None, "event_calendar_known": True},
        {"session_known": True, "event_calendar_known": None},
    ])
    def test_missing_inputs_unevaluable(self, kwargs):
        assert_unevaluable(evaluate_session_and_event_known(**kwargs))

    def test_session_unknown_blocks(self):
        result = evaluate_session_and_event_known(
            session_known=False, event_calendar_known=True)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "SESSION_UNKNOWN"

    def test_event_calendar_incomplete_degrades(self):
        result = evaluate_session_and_event_known(
            session_known=True, event_calendar_known=False)
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "EVENT_CALENDAR_INCOMPLETE"

    def test_both_known_passes(self):
        result = evaluate_session_and_event_known(
            session_known=True, event_calendar_known=True)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "SESSION_AND_EVENT_KNOWN"


def liquidity_kwargs(**overrides) -> dict:
    kwargs = dict(
        asset_class=AssetClass.STOCK,
        observed_liquidity=Decimal("500000"),
        required_minimum=Decimal("100000"),
        observation_delayed=False,
    )
    kwargs.update(overrides)
    return kwargs


class TestMinimumLiquidity:
    @pytest.mark.parametrize("field", [
        "asset_class", "observed_liquidity", "required_minimum", "observation_delayed",
    ])
    def test_missing_inputs_unevaluable(self, field):
        assert_unevaluable(evaluate_minimum_liquidity(**liquidity_kwargs(**{field: None})))

    @pytest.mark.parametrize("overrides", [
        {"observed_liquidity": Decimal("NaN")},
        {"observed_liquidity": Decimal("-1")},
        {"required_minimum": Decimal("0")},
        {"required_minimum": Decimal("Infinity")},
    ])
    def test_invalid_values_unevaluable(self, overrides):
        """A nonsensical observation or threshold is unevaluable, never coerced to zero."""
        assert_unevaluable(evaluate_minimum_liquidity(**liquidity_kwargs(**overrides)))

    def test_below_minimum_blocks(self):
        result = evaluate_minimum_liquidity(
            **liquidity_kwargs(observed_liquidity=Decimal("99999.99")))
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "LIQUIDITY_BELOW_MINIMUM"
        assert result.thresholds["required_minimum"] == Decimal("100000")

    def test_delayed_observation_degrades(self):
        result = evaluate_minimum_liquidity(**liquidity_kwargs(observation_delayed=True))
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "DELAYED_LIQUIDITY_OBSERVATION"

    def test_sufficient_passes(self):
        result = evaluate_minimum_liquidity(**liquidity_kwargs())
        assert result.status is GateStatus.PASS
        assert result.reason_code == "LIQUIDITY_SUFFICIENT"
        assert result.observed_values["observed_liquidity"] == Decimal("500000")

    def test_exactly_at_minimum_passes(self):
        result = evaluate_minimum_liquidity(
            **liquidity_kwargs(observed_liquidity=Decimal("100000")))
        assert result.status is GateStatus.PASS


class TestCalculationsValid:
    def test_missing_mapping_unevaluable(self):
        assert_unevaluable(evaluate_calculations_valid(calculation_statuses=None))

    def test_non_status_value_unevaluable(self):
        assert_unevaluable(evaluate_calculations_valid(
            calculation_statuses={"decision.risk_reward": "OK"}))

    def test_empty_key_unevaluable(self):
        assert_unevaluable(evaluate_calculations_valid(
            calculation_statuses={"": CalculationStatus.OK}))

    def test_empty_mapping_blocks_as_missing(self):
        result = evaluate_calculations_valid(calculation_statuses={})
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "MISSING_CALCULATIONS"

    def test_any_invalid_blocks(self):
        result = evaluate_calculations_valid(calculation_statuses={
            "decision.risk_reward": CalculationStatus.OK,
            "risk.covariance": CalculationStatus.INVALID,
        })
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "INVALID_CALCULATION"

    def test_invalid_dominates_not_implemented(self):
        result = evaluate_calculations_valid(calculation_statuses={
            "a": CalculationStatus.NOT_IMPLEMENTED,
            "b": CalculationStatus.INVALID,
        })
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "INVALID_CALCULATION"

    def test_not_implemented_degrades(self):
        result = evaluate_calculations_valid(calculation_statuses={
            "decision.risk_reward": CalculationStatus.OK,
            "options.exotic_payoff": CalculationStatus.NOT_IMPLEMENTED,
        })
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "NOT_IMPLEMENTED_CALCULATION"
        assert "options.exotic_payoff" in result.message

    def test_all_ok_passes(self):
        result = evaluate_calculations_valid(calculation_statuses={
            "decision.risk_reward": CalculationStatus.OK,
            "risk.covariance": CalculationStatus.OK,
        })
        assert result.status is GateStatus.PASS
        assert result.reason_code == "ALL_CALCULATIONS_VALID"


class TestManualPortfolioRiskAvailable:
    def test_missing_required_flag_unevaluable(self):
        assert_unevaluable(evaluate_manual_portfolio_risk_available(
            risk_required=None, portfolio_risk_available=True, declarations_current=True))

    def test_not_required_passes_ignoring_other_inputs(self):
        result = evaluate_manual_portfolio_risk_available(
            risk_required=False, portfolio_risk_available=None, declarations_current=None)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "NOT_REQUIRED"

    def test_required_but_availability_missing_unevaluable(self):
        assert_unevaluable(evaluate_manual_portfolio_risk_available(
            risk_required=True, portfolio_risk_available=None, declarations_current=True))

    def test_required_and_unavailable_blocks_as_missing(self):
        result = evaluate_manual_portfolio_risk_available(
            risk_required=True, portfolio_risk_available=False, declarations_current=True)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "MISSING_PORTFOLIO_RISK"

    def test_currency_of_declarations_unknown_unevaluable(self):
        assert_unevaluable(evaluate_manual_portfolio_risk_available(
            risk_required=True, portfolio_risk_available=True, declarations_current=None))

    def test_stale_declarations_degrade(self):
        result = evaluate_manual_portfolio_risk_available(
            risk_required=True, portfolio_risk_available=True, declarations_current=False)
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "STALE_PORTFOLIO_DECLARATIONS"

    def test_available_and_current_passes(self):
        result = evaluate_manual_portfolio_risk_available(
            risk_required=True, portfolio_risk_available=True, declarations_current=True)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "PORTFOLIO_RISK_AVAILABLE"


def probability_kwargs(**overrides) -> dict:
    kwargs = dict(
        probability_used=True,
        calibration_valid=True,
        out_of_sample_validated=True,
        calibration_current=True,
    )
    kwargs.update(overrides)
    return kwargs


class TestProbabilityCalibratedIfUsed:
    def test_missing_used_flag_unevaluable(self):
        assert_unevaluable(evaluate_probability_calibrated_if_used(
            **probability_kwargs(probability_used=None)))

    def test_not_used_passes(self):
        result = evaluate_probability_calibrated_if_used(
            probability_used=False, calibration_valid=None,
            out_of_sample_validated=None, calibration_current=None)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "PROBABILITY_NOT_USED"

    @pytest.mark.parametrize("field", [
        "calibration_valid", "out_of_sample_validated", "calibration_current",
    ])
    def test_missing_calibration_facts_unevaluable(self, field):
        assert_unevaluable(evaluate_probability_calibrated_if_used(
            **probability_kwargs(**{field: None})))

    def test_uncalibrated_blocks(self):
        result = evaluate_probability_calibrated_if_used(
            **probability_kwargs(calibration_valid=False))
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "UNCALIBRATED_PROBABILITY"

    def test_no_out_of_sample_validation_blocks(self):
        result = evaluate_probability_calibrated_if_used(
            **probability_kwargs(out_of_sample_validated=False))
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "NO_OUT_OF_SAMPLE_VALIDATION"

    def test_aging_calibration_degrades(self):
        result = evaluate_probability_calibrated_if_used(
            **probability_kwargs(calibration_current=False))
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "CALIBRATION_AGING"

    def test_fully_calibrated_passes(self):
        result = evaluate_probability_calibrated_if_used(**probability_kwargs())
        assert result.status is GateStatus.PASS
        assert result.reason_code == "PROBABILITY_CALIBRATED"


class TestCriticalContradictionsResolved:
    @pytest.mark.parametrize("kwargs", [
        {"unresolved_critical_count": None, "explicit_contradiction_count": 0},
        {"unresolved_critical_count": 0, "explicit_contradiction_count": None},
        {"unresolved_critical_count": -1, "explicit_contradiction_count": 0},
        {"unresolved_critical_count": 0, "explicit_contradiction_count": -2},
        {"unresolved_critical_count": True, "explicit_contradiction_count": 0},
    ])
    def test_missing_or_invalid_counts_unevaluable(self, kwargs):
        assert_unevaluable(evaluate_critical_contradictions_resolved(**kwargs))

    def test_unresolved_blocks(self):
        result = evaluate_critical_contradictions_resolved(
            unresolved_critical_count=2, explicit_contradiction_count=0)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "UNRESOLVED_CRITICAL_CONTRADICTION"

    def test_explicit_only_degrades(self):
        result = evaluate_critical_contradictions_resolved(
            unresolved_critical_count=0, explicit_contradiction_count=1)
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "EXPLICIT_CONTRADICTIONS_PRESENT"

    def test_none_passes(self):
        result = evaluate_critical_contradictions_resolved(
            unresolved_critical_count=0, explicit_contradiction_count=0)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "NO_CRITICAL_CONTRADICTION"


class TestUserConstraintsVersioned:
    def test_missing_version_unevaluable(self):
        assert_unevaluable(evaluate_user_constraints_versioned(
            constraints_version=None, constraints_current=True))

    def test_missing_current_flag_unevaluable(self):
        assert_unevaluable(evaluate_user_constraints_versioned(
            constraints_version="v3", constraints_current=None))

    @pytest.mark.parametrize("version", ["", "   "])
    def test_blank_version_blocks(self, version):
        result = evaluate_user_constraints_versioned(
            constraints_version=version, constraints_current=True)
        assert result.status is GateStatus.BLOCK
        assert result.reason_code == "UNVERSIONED_CONSTRAINTS"

    def test_outdated_acknowledgement_degrades(self):
        result = evaluate_user_constraints_versioned(
            constraints_version="v3", constraints_current=False)
        assert result.status is GateStatus.DEGRADE
        assert result.reason_code == "OUTDATED_CONSTRAINTS_ACKNOWLEDGEMENT"

    def test_versioned_and_current_passes(self):
        result = evaluate_user_constraints_versioned(
            constraints_version="v3", constraints_current=True)
        assert result.status is GateStatus.PASS
        assert result.reason_code == "CONSTRAINTS_VERSIONED"
