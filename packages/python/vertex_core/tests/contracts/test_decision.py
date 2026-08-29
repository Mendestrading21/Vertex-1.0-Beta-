"""Decision contracts: gate/advice invariants, fail-closed BLOCK rule, no transactional field."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from vertex_core.contracts import (
    AdviceResult,
    AdviceStatus,
    Direction,
    ENGINE_VERSION,
    GateResult,
    GateStatus,
)

AS_OF = datetime(2026, 3, 4, 16, 0, tzinfo=timezone.utc)


def make_gate(**overrides):
    kwargs = dict(
        gate_id="gate.freshness",
        version="1.0.0",
        status=GateStatus.PASS,
        reason_code="FRESH",
        message="all required observations within freshness budget",
        evidence_ids=("evt-0001",),
        observed_values={"age_seconds": Decimal("2.5")},
        thresholds={"max_age_seconds": Decimal("30")},
    )
    kwargs.update(overrides)
    return GateResult(**kwargs)


def make_advice(**overrides):
    kwargs = dict(
        advice_id="adv-0001",
        instrument_id="ins-aapl-2026",
        as_of=AS_OF,
        valid_until=AS_OF + timedelta(hours=4),
        input_snapshot_id="snap-0001",
        engine_version=ENGINE_VERSION,
        status=AdviceStatus.REVIEW,
        direction=Direction.NEUTRAL,
        horizon="P1W",
        gates=(make_gate(),),
        risk_summary="synthetic demo scenario for tests only",
        limitations=("SYNTHETIC fixture",),
    )
    kwargs.update(overrides)
    return AdviceResult(**kwargs)


class TestGateResult:
    def test_valid_construction(self):
        gate = make_gate()
        assert gate.status is GateStatus.PASS
        assert gate.observed_values["age_seconds"] == Decimal("2.5")

    def test_observed_values_mapping_is_frozen(self):
        gate = make_gate()
        with pytest.raises(TypeError):
            gate.observed_values["age_seconds"] = Decimal("0")

    def test_thresholds_mapping_is_frozen(self):
        gate = make_gate()
        with pytest.raises(TypeError):
            del gate.thresholds["max_age_seconds"]

    def test_frozen(self):
        gate = make_gate()
        with pytest.raises(ValidationError):
            gate.status = GateStatus.BLOCK

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            make_gate(score=1.0)


class TestAdviceResult:
    def test_valid_construction(self):
        advice = make_advice()
        assert advice.status is AdviceStatus.REVIEW
        assert advice.probability_evidence is None
        assert advice.supersedes is None

    def test_at_least_one_gate_required(self):
        with pytest.raises(ValidationError):
            make_advice(gates=())

    def test_block_gate_forces_blocked_or_insufficient_data(self):
        block_gate = make_gate(status=GateStatus.BLOCK, reason_code="UNEVALUABLE")
        for status in (AdviceStatus.OBSERVE, AdviceStatus.REVIEW, AdviceStatus.QUALIFIED):
            with pytest.raises(ValidationError, match="BLOCK"):
                make_advice(status=status, gates=(block_gate,))

    def test_block_gate_with_blocked_status_accepted(self):
        block_gate = make_gate(status=GateStatus.BLOCK, reason_code="STALE_DATA")
        advice = make_advice(status=AdviceStatus.BLOCKED, gates=(make_gate(), block_gate))
        assert advice.status is AdviceStatus.BLOCKED

    def test_block_gate_with_insufficient_data_status_accepted(self):
        block_gate = make_gate(status=GateStatus.BLOCK, reason_code="MISSING_INPUT")
        advice = make_advice(status=AdviceStatus.INSUFFICIENT_DATA, gates=(block_gate,))
        assert advice.status is AdviceStatus.INSUFFICIENT_DATA

    def test_degrade_gates_do_not_force_blocked(self):
        degraded = make_gate(status=GateStatus.DEGRADE, reason_code="DELAYED_FEED")
        advice = make_advice(status=AdviceStatus.OBSERVE, gates=(degraded,))
        assert advice.status is AdviceStatus.OBSERVE

    def test_valid_until_before_as_of_rejected(self):
        with pytest.raises(ValidationError, match="valid_until"):
            make_advice(valid_until=AS_OF - timedelta(seconds=1))

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_advice(as_of=datetime(2026, 3, 4, 16, 0))

    def test_frozen(self):
        advice = make_advice()
        with pytest.raises(ValidationError):
            advice.status = AdviceStatus.QUALIFIED

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            make_advice(target_quantity=100)

    def test_probability_evidence_mapping_is_frozen_when_present(self):
        advice = make_advice(
            probability_evidence={"calibration_id": "cal-1", "population": "sp500-2y"}
        )
        with pytest.raises(TypeError):
            advice.probability_evidence["population"] = "other"

    def test_no_transactional_field_exists(self):
        # The verdict is analytical only: no field name may suggest a
        # transaction, a broker ticket or an account action.
        field_names = {name.lower() for name in AdviceResult.model_fields}
        field_names |= {name.lower() for name in GateResult.model_fields}
        forbidden_fragments = ("side", "quantity", "account", "ticket", "fill", "trade")
        for fragment in forbidden_fragments:
            assert not any(fragment in name for name in field_names), fragment

    def test_exact_advice_field_set(self):
        assert set(AdviceResult.model_fields) == {
            "advice_id",
            "instrument_id",
            "as_of",
            "valid_until",
            "input_snapshot_id",
            "engine_version",
            "status",
            "direction",
            "horizon",
            "gates",
            "evidence_ids",
            "risk_summary",
            "scenario_ids",
            "probability_evidence",
            "limitations",
            "explanation_facts",
            "supersedes",
        }
