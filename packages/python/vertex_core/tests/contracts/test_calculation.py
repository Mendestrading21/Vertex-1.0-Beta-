"""CalculationRecord and its factory: lineage hashes, temporal and immutability rules."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from vertex_core.contracts import (
    ENGINE_VERSION,
    CalculationRecord,
    CalculationStatus,
    canonical_json_hash,
    make_calculation_record,
)

STARTED_AT = datetime(2026, 3, 3, 9, 0, tzinfo=UTC)
COMPLETED_AT = STARTED_AT + timedelta(milliseconds=250)
INPUTS = {"spot": Decimal("100.5"), "rate": Decimal("0.031")}
RESULT = {"fair_value": Decimal("12.34")}


def make_record(**overrides):
    kwargs = {
        "calculation_id": "calc-0001",
        "calculation_type": "option_fair_value",
        "code_sha": "a" * 40,
        "method": "black_scholes_merton",
        "inputs": INPUTS,
        "result": RESULT,
        "started_at": STARTED_AT,
        "completed_at": COMPLETED_AT,
        "source_event_ids": ("evt-0001",),
        "assumptions": ("flat_rate_curve",),
        "parameters": {"day_count": "ACT/365F"},
    }
    kwargs.update(overrides)
    return make_calculation_record(**kwargs)


class TestFactory:
    def test_hashes_derived_from_real_data(self):
        record = make_record()
        assert record.input_hash == canonical_json_hash(INPUTS)
        assert record.result_hash == canonical_json_hash(RESULT)

    def test_same_inputs_same_input_hash(self):
        assert make_record().input_hash == make_record().input_hash

    def test_key_permutation_of_inputs_same_input_hash(self):
        permuted = {"rate": Decimal("0.031"), "spot": Decimal("100.5")}
        assert make_record(inputs=permuted).input_hash == make_record().input_hash

    def test_different_inputs_different_input_hash(self):
        other = make_record(inputs={"spot": Decimal("101.5"), "rate": Decimal("0.031")})
        assert other.input_hash != make_record().input_hash

    def test_engine_version_defaults_to_package_version(self):
        record = make_record()
        assert record.engine_version == ENGINE_VERSION == "vertex_core@0.1.0"

    def test_sequences_converted_to_tuples(self):
        record = make_record(source_event_ids=["evt-1", "evt-2"], warnings=["w1"])
        assert record.source_event_ids == ("evt-1", "evt-2")
        assert record.warnings == ("w1",)

    def test_status_not_implemented_is_expressible(self):
        record = make_record(status=CalculationStatus.NOT_IMPLEMENTED)
        assert record.status is CalculationStatus.NOT_IMPLEMENTED

    def test_random_seed_recorded(self):
        assert make_record(random_seed=1234).random_seed == 1234
        assert make_record().random_seed is None


class TestModelInvariants:
    def test_completed_before_started_rejected(self):
        with pytest.raises(ValidationError, match="completed_at"):
            make_record(completed_at=STARTED_AT - timedelta(seconds=1))

    def test_completed_equal_to_started_accepted(self):
        record = make_record(completed_at=STARTED_AT)
        assert record.completed_at == record.started_at

    def test_naive_started_at_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_record(started_at=datetime(2026, 3, 3, 9, 0))  # noqa: DTZ001 (naïf délibéré : rejet vérifié)

    def test_frozen(self):
        record = make_record()
        with pytest.raises(ValidationError):
            record.status = CalculationStatus.INVALID

    def test_parameters_mapping_is_frozen(self):
        record = make_record()
        with pytest.raises(TypeError):
            record.parameters["day_count"] = "30/360"

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            CalculationRecord(
                calculation_id="calc-0002",
                calculation_type="x",
                engine_version=ENGINE_VERSION,
                code_sha="b" * 40,
                input_hash=canonical_json_hash(INPUTS),
                method="m",
                parameters={},
                started_at=STARTED_AT,
                completed_at=COMPLETED_AT,
                status=CalculationStatus.OK,
                result_hash=canonical_json_hash(RESULT),
                result=RESULT,
                extra_field="nope",
            )

    def test_malformed_hash_rejected(self):
        with pytest.raises(ValidationError):
            CalculationRecord(
                calculation_id="calc-0003",
                calculation_type="x",
                engine_version=ENGINE_VERSION,
                code_sha="b" * 40,
                input_hash="not-a-hash",
                method="m",
                parameters={},
                started_at=STARTED_AT,
                completed_at=COMPLETED_AT,
                status=CalculationStatus.OK,
                result_hash=canonical_json_hash(RESULT),
                result=RESULT,
            )
