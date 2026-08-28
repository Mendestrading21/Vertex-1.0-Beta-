"""CoverageReport: count invariants, absent-is-not-zero, Hypothesis properties."""

from decimal import Decimal

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from vertex_core.data import CoverageReport, coverage_ratio


class TestCoverageRatioValidation:
    def test_received_above_expected_rejected(self):
        with pytest.raises(ValidationError, match="received must not exceed expected"):
            coverage_ratio(expected=5, received=6, valid=5, delayed=0, stale=0, missing=0)

    def test_classified_counts_above_received_rejected(self):
        with pytest.raises(ValidationError, match="valid \\+ delayed \\+ stale"):
            coverage_ratio(expected=10, received=5, valid=4, delayed=1, stale=1, missing=5)

    def test_inconsistent_missing_rejected(self):
        with pytest.raises(ValidationError, match="missing must equal expected - received"):
            coverage_ratio(expected=10, received=8, valid=8, delayed=0, stale=0, missing=1)

    def test_negative_count_rejected(self):
        with pytest.raises(ValidationError):
            coverage_ratio(expected=10, received=8, valid=-1, delayed=0, stale=0, missing=2)

    def test_bool_count_rejected(self):
        # Strict typing: True is not a count of 1.
        with pytest.raises(TypeError):
            coverage_ratio(expected=10, received=8, valid=True, delayed=0, stale=0, missing=2)

    def test_negative_max_age_rejected(self):
        with pytest.raises(ValidationError):
            coverage_ratio(
                expected=1,
                received=1,
                valid=1,
                delayed=0,
                stale=0,
                missing=0,
                max_age_seconds=Decimal("-1"),
            )

    def test_report_is_frozen(self):
        report = coverage_ratio(expected=2, received=2, valid=2, delayed=0, stale=0, missing=0)
        with pytest.raises(ValidationError):
            report.valid = 0


class TestCoverageRatioSemantics:
    def test_exact_ratio_and_counts_preserved(self):
        report = coverage_ratio(expected=10, received=8, valid=6, delayed=1, stale=1, missing=2)
        assert report.coverage_ratio == Decimal("0.6")
        assert (report.expected, report.received, report.valid) == (10, 8, 6)
        assert (report.delayed, report.stale, report.missing) == (1, 1, 2)

    def test_absent_max_age_stays_none_never_zero(self):
        # Absence of age information is None, never converted to 0 seconds.
        report = coverage_ratio(expected=3, received=0, valid=0, delayed=0, stale=0, missing=3)
        assert report.max_age_seconds is None
        assert report.max_age_seconds != Decimal(0)

    def test_present_max_age_preserved(self):
        report = coverage_ratio(
            expected=1,
            received=1,
            valid=1,
            delayed=0,
            stale=0,
            missing=0,
            max_age_seconds=Decimal("12.5"),
        )
        assert report.max_age_seconds == Decimal("12.5")

    def test_zero_expected_is_vacuously_complete(self):
        report = coverage_ratio(expected=0, received=0, valid=0, delayed=0, stale=0, missing=0)
        assert report.coverage_ratio == Decimal(1)

    def test_nothing_valid_is_zero_ratio(self):
        report = coverage_ratio(expected=4, received=0, valid=0, delayed=0, stale=0, missing=4)
        assert report.coverage_ratio == Decimal(0)

    def test_stale_and_delayed_items_reduce_usable_coverage(self):
        report = coverage_ratio(expected=4, received=4, valid=2, delayed=1, stale=1, missing=0)
        assert report.coverage_ratio == Decimal("0.5")


@st.composite
def consistent_counts(draw):
    expected = draw(st.integers(min_value=0, max_value=500))
    received = draw(st.integers(min_value=0, max_value=expected))
    valid = draw(st.integers(min_value=0, max_value=received))
    delayed = draw(st.integers(min_value=0, max_value=received - valid))
    stale = draw(st.integers(min_value=0, max_value=received - valid - delayed))
    return dict(
        expected=expected,
        received=received,
        valid=valid,
        delayed=delayed,
        stale=stale,
        missing=expected - received,
    )


@pytest.mark.property
class TestCoverageProperties:
    @given(counts=consistent_counts())
    def test_ratio_always_in_unit_interval(self, counts):
        report = coverage_ratio(**counts)
        assert Decimal(0) <= report.coverage_ratio <= Decimal(1)

    @given(
        expected=st.integers(min_value=1, max_value=500),
        data=st.data(),
    )
    def test_ratio_monotone_in_valid_count(self, expected, data):
        # More valid items (everything else equal) never lowers the ratio.
        valid_low = data.draw(st.integers(min_value=0, max_value=expected - 1))
        valid_high = data.draw(st.integers(min_value=valid_low + 1, max_value=expected))
        low = coverage_ratio(
            expected=expected, received=expected, valid=valid_low, delayed=0, stale=0, missing=0
        )
        high = coverage_ratio(
            expected=expected, received=expected, valid=valid_high, delayed=0, stale=0, missing=0
        )
        assert high.coverage_ratio > low.coverage_ratio

    @given(
        valid=st.integers(min_value=1, max_value=200),
        data=st.data(),
    )
    def test_ratio_antitone_in_expected_count(self, valid, data):
        # A larger expected universe (same valid count) never raises the ratio.
        expected_small = data.draw(st.integers(min_value=valid, max_value=400))
        expected_large = data.draw(st.integers(min_value=expected_small + 1, max_value=800))
        small = coverage_ratio(
            expected=expected_small,
            received=valid,
            valid=valid,
            delayed=0,
            stale=0,
            missing=expected_small - valid,
        )
        large = coverage_ratio(
            expected=expected_large,
            received=valid,
            valid=valid,
            delayed=0,
            stale=0,
            missing=expected_large - valid,
        )
        assert large.coverage_ratio < small.coverage_ratio

    @given(counts=consistent_counts())
    def test_full_ratio_iff_all_expected_valid(self, counts):
        report = coverage_ratio(**counts)
        if counts["expected"] == 0 or counts["valid"] == counts["expected"]:
            assert report.coverage_ratio == Decimal(1)
        else:
            assert report.coverage_ratio < Decimal(1)

    @given(counts=consistent_counts())
    def test_determinism(self, counts):
        assert coverage_ratio(**counts) == coverage_ratio(**counts)


class TestCoverageReportModelDirect:
    def test_ratio_outside_unit_interval_rejected(self):
        with pytest.raises(ValidationError, match="coverage_ratio"):
            CoverageReport(
                expected=1,
                received=1,
                valid=1,
                delayed=0,
                stale=0,
                missing=0,
                coverage_ratio=Decimal("1.5"),
            )

    def test_non_finite_ratio_rejected(self):
        with pytest.raises(ValidationError):
            CoverageReport(
                expected=1,
                received=1,
                valid=1,
                delayed=0,
                stale=0,
                missing=0,
                coverage_ratio=Decimal("NaN"),
            )
