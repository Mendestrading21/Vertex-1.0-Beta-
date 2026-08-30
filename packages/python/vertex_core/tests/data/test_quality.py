"""Layered envelope-quality evaluation: matrix, precedence, absent-is-not-zero."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from vertex_core.contracts import DelayStatus, EnvelopeQuality, IdentityStatus
from vertex_core.data import (
    ConflictRecord,
    FieldObservation,
    FreshnessStatus,
    QualityChecks,
    QualityLayer,
    ViolationSeverity,
    aggregate_violations,
    check_bounds,
    check_conflicts,
    check_coverage,
    check_entitlement,
    check_freshness,
    check_identity,
    check_price_coherence,
    check_schema,
    check_time_order,
    check_units,
    collect_violations,
    coverage_ratio,
    evaluate_envelope_quality,
)

T0 = datetime(2026, 8, 28, 14, 0, tzinfo=UTC)


def make_checks(**overrides):
    """All-clear checks; override single facts to trigger specific layers."""
    kwargs = {
        "schema_valid": True,
        "identity_status": IdentityStatus.RESOLVED,
        "unit_consistent": True,
        "rights_known": True,
        "delay_status": DelayStatus.LIVE,
        "freshness": FreshnessStatus.FRESH,
    }
    kwargs.update(overrides)
    return QualityChecks(**kwargs)


def make_conflict_record():
    observations = (
        FieldObservation(source="ibkr", field_name="last", value=Decimal("100.0"), as_of=T0),
        FieldObservation(source="tradingview", field_name="last", value=Decimal("103.0"), as_of=T0),
    )
    return ConflictRecord(
        field_name="last",
        code="VALUE_DIVERGENCE",
        observations=observations,
        tolerance=Decimal("0.5"),
        divergence=Decimal("3.0"),
        message="synthetic conflict fixture (SYNTHETIC)",
    )


def partial_coverage():
    return coverage_ratio(expected=10, received=7, valid=6, delayed=1, stale=0, missing=3)


def full_coverage():
    return coverage_ratio(expected=10, received=10, valid=10, delayed=0, stale=0, missing=0)


CHECKS_BY_TARGET_QUALITY = {
    EnvelopeQuality.VALID: {},
    EnvelopeQuality.PARTIAL: {"coverage": partial_coverage()},
    EnvelopeQuality.STALE: {"freshness": FreshnessStatus.STALE},
    EnvelopeQuality.INVALID: {"schema_valid": False},
    EnvelopeQuality.CONFLICT: {"conflicts": (make_conflict_record(),)},
}


class TestQualityDelayMatrix:
    """Full EnvelopeQuality x DelayStatus matrix (key transitions).

    Quality and delay are orthogonal dimensions: for every DelayStatus member
    (including the explicit UNKNOWN) each reachable quality outcome must be
    produced unchanged. Only an UNASSESSED delay dimension (None) fails closed.
    """

    @pytest.mark.parametrize("delay_status", list(DelayStatus))
    @pytest.mark.parametrize("target", list(CHECKS_BY_TARGET_QUALITY))
    def test_matrix(self, target, delay_status):
        overrides = dict(CHECKS_BY_TARGET_QUALITY[target])
        overrides["delay_status"] = delay_status
        assert evaluate_envelope_quality(make_checks(**overrides)) is target

    @pytest.mark.parametrize("target", list(CHECKS_BY_TARGET_QUALITY))
    def test_unassessed_delay_dimension_fails_closed(self, target):
        overrides = dict(CHECKS_BY_TARGET_QUALITY[target])
        overrides["delay_status"] = None
        assert evaluate_envelope_quality(make_checks(**overrides)) is EnvelopeQuality.INVALID

    def test_insufficient_data_never_produced_by_aggregation(self):
        # INSUFFICIENT_DATA is assigned upstream by the collector; the layered
        # evaluator only yields the other five states.
        for target, overrides in CHECKS_BY_TARGET_QUALITY.items():
            result = evaluate_envelope_quality(make_checks(**overrides))
            assert result is not EnvelopeQuality.INSUFFICIENT_DATA
            assert result is target


class TestAggregationPrecedence:
    def test_all_clear_is_valid(self):
        assert evaluate_envelope_quality(make_checks()) is EnvelopeQuality.VALID

    def test_blocking_beats_conflict_stale_and_partial(self):
        checks = make_checks(
            schema_valid=False,
            freshness=FreshnessStatus.STALE,
            coverage=partial_coverage(),
            conflicts=(make_conflict_record(),),
        )
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.INVALID

    def test_conflict_beats_stale_and_partial(self):
        checks = make_checks(
            freshness=FreshnessStatus.STALE,
            coverage=partial_coverage(),
            conflicts=(make_conflict_record(),),
        )
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.CONFLICT

    def test_stale_beats_partial(self):
        checks = make_checks(freshness=FreshnessStatus.STALE, coverage=partial_coverage())
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.STALE

    def test_partial_when_only_coverage_gap(self):
        checks = make_checks(coverage=partial_coverage())
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.PARTIAL

    def test_full_coverage_stays_valid(self):
        checks = make_checks(coverage=full_coverage())
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.VALID

    def test_aggregate_empty_violations_is_valid(self):
        assert aggregate_violations(()) is EnvelopeQuality.VALID

    def test_aggregate_rejects_untyped_items(self):
        with pytest.raises(TypeError):
            aggregate_violations([{"severity": "BLOCKING"}])

    def test_evaluate_rejects_untyped_checks(self):
        with pytest.raises(TypeError):
            evaluate_envelope_quality({"schema_valid": True})


class TestFailClosedUnassessedFacts:
    """Every required assessment fact passed as None is a BLOCKING violation."""

    @pytest.mark.parametrize(
        "field",
        ["schema_valid", "identity_status", "unit_consistent", "rights_known", "freshness"],
    )
    def test_none_fact_fails_closed(self, field):
        checks = make_checks(**{field: None})
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.INVALID

    def test_facts_cannot_be_omitted(self):
        with pytest.raises(ValidationError):
            QualityChecks(schema_valid=True)


class TestSchemaLayer:
    def test_valid_schema_no_violation(self):
        assert check_schema(schema_valid=True) == ()

    def test_invalid_schema_blocking(self):
        (violation,) = check_schema(schema_valid=False)
        assert violation.layer is QualityLayer.SCHEMA
        assert violation.severity is ViolationSeverity.BLOCKING
        assert violation.code == "SCHEMA_INVALID"

    def test_unverified_schema_blocking(self):
        (violation,) = check_schema(schema_valid=None)
        assert violation.code == "SCHEMA_UNVERIFIED"
        assert violation.severity is ViolationSeverity.BLOCKING


class TestIdentityLayer:
    def test_resolved_no_violation(self):
        assert check_identity(identity_status=IdentityStatus.RESOLVED) == ()

    @pytest.mark.parametrize(
        "status", [IdentityStatus.UNRESOLVED, IdentityStatus.AMBIGUOUS]
    )
    def test_unresolved_or_ambiguous_blocking(self, status):
        (violation,) = check_identity(identity_status=status)
        assert violation.severity is ViolationSeverity.BLOCKING
        assert status.value in violation.code


class TestUnitLayer:
    def test_consistent_no_violation(self):
        assert check_units(unit_consistent=True) == ()

    def test_inconsistent_blocking(self):
        (violation,) = check_units(unit_consistent=False)
        assert violation.code == "UNIT_INCONSISTENT"
        assert violation.severity is ViolationSeverity.BLOCKING


class TestTimeLayer:
    def test_observed_after_received_blocking(self):
        (violation,) = check_time_order(
            observed_at=T0 + timedelta(seconds=1), received_at=T0
        )
        assert violation.code == "OBSERVED_AFTER_RECEIVED"
        assert violation.severity is ViolationSeverity.BLOCKING

    def test_observed_before_received_ok(self):
        assert check_time_order(observed_at=T0 - timedelta(seconds=1), received_at=T0) == ()

    def test_absent_timestamps_not_a_violation(self):
        # Absent metadata stays None; only a checkable incoherence violates.
        assert check_time_order(observed_at=None, received_at=None) == ()
        assert check_time_order(observed_at=T0, received_at=None) == ()

    def test_observed_after_received_makes_envelope_invalid(self):
        checks = make_checks(observed_at=T0 + timedelta(seconds=2), received_at=T0)
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.INVALID

    def test_naive_datetime_rejected_at_dto_boundary(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_checks(observed_at=datetime(2026, 8, 28, 14, 0))  # noqa: DTZ001 (naïf délibéré : rejet vérifié)


class TestEntitlementLayer:
    def test_rights_known_and_delay_declared_ok(self):
        assert check_entitlement(rights_known=True, delay_status=DelayStatus.DELAYED) == ()

    def test_rights_unknown_blocking(self):
        violations = check_entitlement(rights_known=False, delay_status=DelayStatus.LIVE)
        assert [v.code for v in violations] == ["RIGHTS_UNKNOWN"]
        assert violations[0].severity is ViolationSeverity.BLOCKING

    def test_delay_dimension_unassessed_blocking(self):
        violations = check_entitlement(rights_known=True, delay_status=None)
        assert [v.code for v in violations] == ["DELAY_STATUS_MISSING"]

    def test_explicit_unknown_delay_is_not_a_quality_violation(self):
        # DelayStatus.UNKNOWN is a declared honest state, distinct from an
        # unassessed dimension (None).
        assert check_entitlement(rights_known=True, delay_status=DelayStatus.UNKNOWN) == ()


class TestBoundsLayer:
    def test_negative_price_blocking(self):
        (violation,) = check_bounds(bid=Decimal("-0.01"))
        assert violation.code == "NEGATIVE_PRICE"
        assert violation.severity is ViolationSeverity.BLOCKING

    def test_negative_volume_blocking(self):
        (violation,) = check_bounds(volume=Decimal("-1"))
        assert violation.code == "NEGATIVE_VOLUME"

    def test_zero_price_is_within_bounds(self):
        # A worthless option can legitimately quote at zero.
        assert check_bounds(bid=Decimal("0")) == ()

    def test_absent_values_never_treated_as_zero(self):
        # None is absence, not zero: no bounds violation may fire on absence.
        assert check_bounds() == ()
        assert (
            check_bounds(
                bid=None,
                ask=None,
                last=None,
                open_price=None,
                high_price=None,
                low_price=None,
                close_price=None,
                volume=None,
            )
            == ()
        )

    def test_absent_quote_fields_keep_envelope_valid(self):
        # Explicit absent-is-not-zero: a checks object with every numeric
        # field absent aggregates to VALID, and no violation observes a 0.
        checks = make_checks()
        assert checks.bid is None and checks.volume is None
        violations = collect_violations(checks)
        assert violations == ()
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.VALID


class TestCoherenceLayer:
    def test_bid_above_ask_unexplained_is_violation(self):
        (violation,) = check_price_coherence(bid=Decimal("10.1"), ask=Decimal("10.0"))
        assert violation.code == "BID_ABOVE_ASK_UNEXPLAINED"
        assert violation.severity is ViolationSeverity.BLOCKING

    def test_bid_above_ask_with_none_explanation_still_violation(self):
        (violation,) = check_price_coherence(
            bid=Decimal("10.1"), ask=Decimal("10.0"), crossed_market_explained=None
        )
        assert violation.code == "BID_ABOVE_ASK_UNEXPLAINED"

    def test_bid_above_ask_explained_crossed_market_accepted(self):
        assert (
            check_price_coherence(
                bid=Decimal("10.1"), ask=Decimal("10.0"), crossed_market_explained=True
            )
            == ()
        )

    def test_locked_market_bid_equal_ask_is_coherent(self):
        assert check_price_coherence(bid=Decimal("10"), ask=Decimal("10")) == ()

    def test_bid_below_ask_is_coherent(self):
        assert check_price_coherence(bid=Decimal("9.9"), ask=Decimal("10")) == ()

    def test_missing_bid_or_ask_not_a_violation(self):
        assert check_price_coherence(bid=Decimal("10"), ask=None) == ()
        assert check_price_coherence(bid=None, ask=Decimal("10")) == ()

    def test_high_below_low_violation(self):
        violations = check_price_coherence(high_price=Decimal("9"), low_price=Decimal("10"))
        assert "OHLC_HIGH_BELOW_LOW" in [v.code for v in violations]

    def test_open_outside_range_violation(self):
        (violation,) = check_price_coherence(
            open_price=Decimal("11"), high_price=Decimal("10.5"), low_price=Decimal("9")
        )
        assert violation.code == "OHLC_VALUE_OUTSIDE_RANGE"

    def test_close_below_low_violation(self):
        (violation,) = check_price_coherence(
            close_price=Decimal("8"), high_price=Decimal("10.5"), low_price=Decimal("9")
        )
        assert violation.code == "OHLC_VALUE_OUTSIDE_RANGE"

    def test_coherent_ohlc_no_violation(self):
        assert (
            check_price_coherence(
                open_price=Decimal("9.5"),
                high_price=Decimal("10.5"),
                low_price=Decimal("9"),
                close_price=Decimal("10"),
            )
            == ()
        )

    def test_unexplained_crossed_quote_makes_envelope_invalid(self):
        checks = make_checks(bid=Decimal("10.1"), ask=Decimal("10.0"))
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.INVALID


class TestCoverageLayer:
    def test_no_coverage_report_no_violation(self):
        assert check_coverage(coverage=None) == ()

    def test_partial_coverage_partial_violation(self):
        (violation,) = check_coverage(coverage=partial_coverage())
        assert violation.severity is ViolationSeverity.PARTIAL
        assert violation.code == "COVERAGE_PARTIAL"
        assert violation.observed["missing"] == 3

    def test_full_coverage_no_violation(self):
        assert check_coverage(coverage=full_coverage()) == ()


class TestFreshnessLayer:
    def test_fresh_no_violation(self):
        assert check_freshness(freshness=FreshnessStatus.FRESH) == ()

    def test_stale_severity_stale(self):
        (violation,) = check_freshness(freshness=FreshnessStatus.STALE)
        assert violation.severity is ViolationSeverity.STALE

    def test_future_observation_blocking(self):
        (violation,) = check_freshness(freshness=FreshnessStatus.INVALID)
        assert violation.code == "FUTURE_OBSERVATION"
        assert violation.severity is ViolationSeverity.BLOCKING

    def test_future_observation_makes_envelope_invalid_not_stale(self):
        checks = make_checks(freshness=FreshnessStatus.INVALID)
        assert evaluate_envelope_quality(checks) is EnvelopeQuality.INVALID

    def test_unevaluated_freshness_blocking(self):
        (violation,) = check_freshness(freshness=None)
        assert violation.code == "FRESHNESS_UNVERIFIED"


class TestConflictLayer:
    def test_no_conflicts_no_violation(self):
        assert check_conflicts(conflicts=()) == ()

    def test_each_conflict_record_yields_a_conflict_violation(self):
        record = make_conflict_record()
        violations = check_conflicts(conflicts=(record, record))
        assert len(violations) == 2
        assert all(v.severity is ViolationSeverity.CONFLICT for v in violations)
        assert all(v.layer is QualityLayer.CONFLICT for v in violations)


class TestViolationModel:
    def test_violations_are_frozen(self):
        (violation,) = check_schema(schema_valid=False)
        with pytest.raises(ValidationError):
            violation.severity = ViolationSeverity.PARTIAL

    def test_observed_mapping_is_read_only(self):
        (violation,) = check_bounds(bid=Decimal("-1"))
        with pytest.raises(TypeError):
            violation.observed["bid"] = "0"

    def test_collect_violations_reports_layers_in_canonical_order(self):
        checks = make_checks(
            schema_valid=False,
            freshness=FreshnessStatus.STALE,
            conflicts=(make_conflict_record(),),
        )
        layers = [v.layer for v in collect_violations(checks)]
        assert layers == [QualityLayer.SCHEMA, QualityLayer.FRESHNESS, QualityLayer.CONFLICT]

    def test_checks_model_is_frozen_and_strict(self):
        checks = make_checks()
        with pytest.raises(ValidationError):
            checks.schema_valid = False
        with pytest.raises(ValidationError):
            make_checks(unexpected_field=1)
