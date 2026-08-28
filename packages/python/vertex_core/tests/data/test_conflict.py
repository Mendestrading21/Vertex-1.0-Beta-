"""Cross-source conflict detection: both sides kept, no vote, no average."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from vertex_core.data import (
    CONFLICT_CODE_UNIT_MISMATCH,
    CONFLICT_CODE_VALUE_DIVERGENCE,
    ConflictRecord,
    FieldObservation,
    detect_conflicts,
)

T0 = datetime(2026, 8, 28, 14, 0, tzinfo=timezone.utc)


def obs(source, value, field_name="last", as_of=T0, unit=None):
    return FieldObservation(
        source=source, field_name=field_name, value=Decimal(value), as_of=as_of, unit=unit
    )


class TestDetectConflicts:
    def test_divergent_sources_beyond_tolerance_conflict(self):
        records = detect_conflicts(
            [obs("ibkr", "100.0"), obs("tradingview", "101.5")], tolerance=Decimal("1")
        )
        assert len(records) == 1
        record = records[0]
        assert record.code == CONFLICT_CODE_VALUE_DIVERGENCE
        assert record.divergence == Decimal("1.5")
        assert record.tolerance == Decimal("1")

    def test_record_lists_both_values_verbatim(self):
        # BOTH observations are preserved exactly — never merged.
        (record,) = detect_conflicts(
            [obs("ibkr", "100.0"), obs("tradingview", "101.5")], tolerance=Decimal("0.5")
        )
        values = {(o.source, o.value) for o in record.observations}
        assert values == {("ibkr", Decimal("100.0")), ("tradingview", Decimal("101.5"))}

    def test_within_tolerance_no_conflict(self):
        records = detect_conflicts(
            [obs("ibkr", "100.0"), obs("tradingview", "100.9")], tolerance=Decimal("1")
        )
        assert records == ()

    def test_divergence_exactly_at_tolerance_is_not_a_conflict(self):
        records = detect_conflicts(
            [obs("ibkr", "100"), obs("tradingview", "101")], tolerance=Decimal("1")
        )
        assert records == ()

    def test_zero_tolerance_flags_any_difference(self):
        records = detect_conflicts(
            [obs("ibkr", "100.00"), obs("tradingview", "100.01")], tolerance=Decimal("0")
        )
        assert len(records) == 1

    def test_identical_values_never_conflict_even_at_zero_tolerance(self):
        records = detect_conflicts(
            [obs("ibkr", "100.0"), obs("tradingview", "100.0")], tolerance=Decimal("0")
        )
        assert records == ()

    def test_no_majority_vote_all_three_sources_listed(self):
        # Two sources agree, one diverges: NO majority vote — the record keeps
        # all three observations and elects no winner.
        records = detect_conflicts(
            [obs("ibkr", "100.0"), obs("tradingview", "100.0"), obs("sec", "110.0")],
            tolerance=Decimal("1"),
        )
        assert len(records) == 1
        record = records[0]
        assert len(record.observations) == 3
        assert {o.source for o in record.observations} == {"ibkr", "tradingview", "sec"}

    def test_no_average_no_resolved_value_anywhere(self):
        # The contract structurally forbids resolution: no field of the record
        # carries a merged, averaged, majority or resolved value.
        (record,) = detect_conflicts(
            [obs("ibkr", "100.0"), obs("tradingview", "104.0")], tolerance=Decimal("1")
        )
        forbidden = {"resolved_value", "consensus_value", "merged_value", "average", "winner"}
        assert forbidden.isdisjoint(ConflictRecord.model_fields)
        # The average (102.0) appears nowhere among the preserved values.
        assert Decimal("102.0") not in {o.value for o in record.observations}
        assert record.divergence == Decimal("4.0")

    def test_same_source_revisions_are_not_conflicts(self):
        # Two observations from ONE source are revisions, never a conflict.
        records = detect_conflicts(
            [obs("ibkr", "100.0"), obs("ibkr", "150.0", as_of=T0 + timedelta(seconds=5))],
            tolerance=Decimal("1"),
        )
        assert records == ()

    def test_cross_source_pairs_only_drive_divergence(self):
        # A same-source revision joins the record, but divergence is measured
        # across sources only.
        records = detect_conflicts(
            [
                obs("ibkr", "100.0"),
                obs("ibkr", "100.2", as_of=T0 + timedelta(seconds=1)),
                obs("tradingview", "103.0"),
            ],
            tolerance=Decimal("1"),
        )
        (record,) = records
        assert record.divergence == Decimal("3.0")
        assert len(record.observations) == 3

    def test_fields_are_grouped_independently(self):
        records = detect_conflicts(
            [
                obs("ibkr", "100.0", field_name="last"),
                obs("tradingview", "105.0", field_name="last"),
                obs("ibkr", "99.0", field_name="bid"),
                obs("tradingview", "99.1", field_name="bid"),
            ],
            tolerance=Decimal("1"),
        )
        assert [r.field_name for r in records] == ["last"]

    def test_unit_mismatch_is_a_conflict_not_a_conversion(self):
        records = detect_conflicts(
            [obs("ibkr", "100.0", unit="USD"), obs("sec", "100.0", unit="EUR")],
            tolerance=Decimal("1000"),
        )
        (record,) = records
        assert record.code == CONFLICT_CODE_UNIT_MISMATCH
        assert record.divergence is None
        assert len(record.observations) == 2

    def test_declared_versus_undeclared_unit_is_a_mismatch(self):
        records = detect_conflicts(
            [obs("ibkr", "100.0", unit="USD"), obs("tradingview", "100.0", unit=None)],
            tolerance=Decimal("1000"),
        )
        assert records[0].code == CONFLICT_CODE_UNIT_MISMATCH

    def test_single_observation_no_phantom_zero_counterpart(self):
        # An absent observation stays absent: one lone observation never
        # conflicts against an invented zero value.
        records = detect_conflicts([obs("ibkr", "100.0")], tolerance=Decimal("0"))
        assert records == ()

    def test_empty_input_no_conflicts(self):
        assert detect_conflicts([], tolerance=Decimal("1")) == ()

    def test_deterministic_under_input_permutation(self):
        base = [
            obs("tradingview", "103.0"),
            obs("ibkr", "100.0"),
            obs("sec", "108.0", field_name="bid"),
            obs("ibkr", "99.0", field_name="bid"),
        ]
        forward = detect_conflicts(base, tolerance=Decimal("1"))
        reordered = detect_conflicts(list(reversed(base)), tolerance=Decimal("1"))
        assert forward == reordered
        assert [r.field_name for r in forward] == ["bid", "last"]


class TestDetectConflictsValidation:
    def test_negative_tolerance_rejected(self):
        with pytest.raises(ValueError, match="tolerance"):
            detect_conflicts([obs("a", "1"), obs("b", "2")], tolerance=Decimal("-1"))

    def test_non_finite_tolerance_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            detect_conflicts([obs("a", "1"), obs("b", "2")], tolerance=Decimal("NaN"))

    def test_non_decimal_tolerance_rejected(self):
        with pytest.raises(TypeError):
            detect_conflicts([obs("a", "1"), obs("b", "2")], tolerance=1.0)

    def test_untyped_observation_rejected(self):
        with pytest.raises(TypeError):
            detect_conflicts([{"source": "a", "value": Decimal("1")}], tolerance=Decimal("1"))


class TestObservationModel:
    def test_nan_value_rejected(self):
        with pytest.raises(ValidationError):
            FieldObservation(source="a", field_name="last", value=Decimal("NaN"), as_of=T0)

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            FieldObservation(
                source="a", field_name="last", value=Decimal("1"), as_of=datetime(2026, 8, 28)
            )

    def test_frozen(self):
        observation = obs("ibkr", "1")
        with pytest.raises(ValidationError):
            observation.value = Decimal("2")


class TestConflictRecordModel:
    def test_requires_at_least_two_observations(self):
        with pytest.raises(ValidationError):
            ConflictRecord(
                field_name="last",
                code=CONFLICT_CODE_VALUE_DIVERGENCE,
                observations=(obs("ibkr", "1"),),
                tolerance=Decimal("1"),
                divergence=Decimal("2"),
                message="one-sided",
            )

    def test_requires_two_distinct_sources(self):
        with pytest.raises(ValidationError, match="distinct sources"):
            ConflictRecord(
                field_name="last",
                code=CONFLICT_CODE_VALUE_DIVERGENCE,
                observations=(obs("ibkr", "1"), obs("ibkr", "3")),
                tolerance=Decimal("1"),
                divergence=Decimal("2"),
                message="same source twice",
            )

    def test_rejects_foreign_field_observations(self):
        with pytest.raises(ValidationError, match="field_name"):
            ConflictRecord(
                field_name="last",
                code=CONFLICT_CODE_VALUE_DIVERGENCE,
                observations=(obs("ibkr", "1"), obs("sec", "3", field_name="bid")),
                tolerance=Decimal("1"),
                divergence=Decimal("2"),
                message="mixed fields",
            )
