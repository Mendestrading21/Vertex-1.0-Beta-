"""AdviceEngine: status rules, block dominance, replay determinism, uniqueness.

All fixtures are SYNTHETIC and deterministic; no network, no clock, no
randomness.
"""

import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

import pytest

from vertex_core.contracts.enums import (
    AdviceStatus,
    AssetClass,
    CalculationStatus,
    Direction,
    GateStatus,
    IdentityStatus,
    SnapshotQuality,
    SourceCapabilityStatus,
)
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_core.decision import (
    GATE_ORDER,
    AdviceEngine,
    AdviceInputs,
    CalculationsInput,
    ConstraintsInput,
    ContradictionsInput,
    EntitlementsInput,
    InstrumentResolutionInput,
    LiquidityInput,
    PortfolioRiskInput,
    ProbabilityInput,
    SessionEventInput,
    SnapshotInput,
)
from vertex_core.version import ENGINE_VERSION

AS_OF = datetime(2026, 8, 28, 13, 30, tzinfo=UTC)
VALID_UNTIL = datetime(2026, 8, 28, 21, 0, tzinfo=UTC)

QUALIFIED_FAMILY = {AdviceStatus.OBSERVE, AdviceStatus.REVIEW, AdviceStatus.QUALIFIED}


def all_pass_inputs(**overrides) -> AdviceInputs:
    """Synthetic inputs whose ten gates all PASS and whose evidence is complete."""
    kwargs = {
        "instrument_id": "instr-SYN-001",
        "as_of": AS_OF,
        "valid_until": VALID_UNTIL,
        "input_snapshot_id": "snap-SYN-001",
        "horizon": "10D",
        "direction": Direction.BULLISH,
        "risk_summary": "synthetic risk summary: defined stop distance, bounded loss scenario",
        "evidence_ids": ("ev-1", "ev-2"),
        "scenario_ids": ("sc-1",),
        "explanation_facts": (
            "fact: synthetic momentum evidence",
            "fact: synthetic volume evidence",
        ),
        "limitations": (),
        "instrument": InstrumentResolutionInput(
            identity_status=IdentityStatus.RESOLVED, resolved_with_conid=True
        ),
        "entitlements": EntitlementsInput(capability_status=SourceCapabilityStatus.AVAILABLE),
        "snapshot": SnapshotInput(quality=SnapshotQuality.GOOD, fresh=True),
        "session_event": SessionEventInput(session_known=True, event_calendar_known=True),
        "liquidity": LiquidityInput(
            asset_class=AssetClass.STOCK,
            observed_liquidity=Decimal("500000"),
            required_minimum=Decimal("100000"),
            observation_delayed=False,
        ),
        "calculations": CalculationsInput(
            calculation_statuses={"decision.risk_reward": CalculationStatus.OK}
        ),
        "portfolio_risk": PortfolioRiskInput(
            risk_required=True, portfolio_risk_available=True, declarations_current=True
        ),
        "probability": ProbabilityInput(probability_used=False),
        "contradictions": ContradictionsInput(
            unresolved_critical_count=0, explicit_contradiction_count=0
        ),
        "constraints": ConstraintsInput(constraints_version="v3", constraints_current=True),
    }
    kwargs.update(overrides)
    return AdviceInputs(**kwargs)


# One violation override per gate: exactly that gate turns BLOCK, others PASS.
BLOCK_OVERRIDES_PER_GATE = {
    "instrument_resolved": {"instrument": InstrumentResolutionInput(
        identity_status=IdentityStatus.UNRESOLVED, resolved_with_conid=True)},
    "entitlements_sufficient": {"entitlements": EntitlementsInput(
        capability_status=SourceCapabilityStatus.NOT_ENTITLED)},
    "snapshot_fresh_and_coherent": {"snapshot": SnapshotInput(
        quality=SnapshotQuality.CONTRADICTORY, fresh=True)},
    "session_and_event_known": {"session_event": SessionEventInput(
        session_known=False, event_calendar_known=True)},
    "minimum_liquidity": {"liquidity": LiquidityInput(
        asset_class=AssetClass.STOCK,
        observed_liquidity=Decimal("1"),
        required_minimum=Decimal("100000"),
        observation_delayed=False)},
    "calculations_valid": {"calculations": CalculationsInput(
        calculation_statuses={"decision.risk_reward": CalculationStatus.INVALID})},
    "manual_portfolio_risk_available": {"portfolio_risk": PortfolioRiskInput(
        risk_required=True, portfolio_risk_available=False, declarations_current=True)},
    "probability_calibrated_if_used": {"probability": ProbabilityInput(
        probability_used=True, calibration_valid=False,
        out_of_sample_validated=True, calibration_current=True)},
    "critical_contradictions_resolved": {"contradictions": ContradictionsInput(
        unresolved_critical_count=1, explicit_contradiction_count=0)},
    "user_constraints_versioned": {"constraints": ConstraintsInput(
        constraints_version="", constraints_current=True)},
}


class TestGateExecution:
    def test_gates_run_in_canonical_order(self):
        result = AdviceEngine().evaluate(all_pass_inputs())
        assert tuple(g.gate_id for g in result.gates) == GATE_ORDER
        assert len(result.gates) == 10

    def test_all_pass_qualified(self):
        result = AdviceEngine().evaluate(all_pass_inputs())
        assert all(g.status is GateStatus.PASS for g in result.gates)
        assert result.status is AdviceStatus.QUALIFIED
        assert result.engine_version == ENGINE_VERSION

    def test_wrong_input_type_rejected(self):
        with pytest.raises(TypeError):
            AdviceEngine().evaluate({"instrument_id": "x"})


class TestBlockDominance:
    @pytest.mark.parametrize("gate_id", list(BLOCK_OVERRIDES_PER_GATE))
    def test_nine_pass_one_block_never_qualified(self, gate_id):
        """A single BLOCK among 9 PASS is never compensated: no OBSERVE/REVIEW/QUALIFIED."""
        inputs = all_pass_inputs(**BLOCK_OVERRIDES_PER_GATE[gate_id])
        result = AdviceEngine().evaluate(inputs)
        statuses = [g.status for g in result.gates]
        assert statuses.count(GateStatus.BLOCK) == 1
        assert statuses.count(GateStatus.PASS) == 9
        blocked_gate = next(g for g in result.gates if g.status is GateStatus.BLOCK)
        assert blocked_gate.gate_id == gate_id
        assert result.status in {AdviceStatus.BLOCKED, AdviceStatus.INSUFFICIENT_DATA}
        assert result.status not in QUALIFIED_FAMILY

    def test_violation_block_maps_to_blocked(self):
        result = AdviceEngine().evaluate(
            all_pass_inputs(**BLOCK_OVERRIDES_PER_GATE["entitlements_sufficient"]))
        assert result.status is AdviceStatus.BLOCKED

    def test_unevaluable_block_maps_to_insufficient_data(self):
        """Documented rule: UNEVALUABLE (missing input) blocks map to INSUFFICIENT_DATA."""
        result = AdviceEngine().evaluate(
            all_pass_inputs(instrument=InstrumentResolutionInput()))
        blocked = [g for g in result.gates if g.status is GateStatus.BLOCK]
        assert [g.reason_code for g in blocked] == ["UNEVALUABLE"]
        assert result.status is AdviceStatus.INSUFFICIENT_DATA

    def test_missing_reason_maps_to_insufficient_data(self):
        """MISSING_* reasons (e.g. MISSING_CALCULATIONS) also mean insufficient data."""
        result = AdviceEngine().evaluate(
            all_pass_inputs(calculations=CalculationsInput(calculation_statuses={})))
        blocked = [g for g in result.gates if g.status is GateStatus.BLOCK]
        assert [g.reason_code for g in blocked] == ["MISSING_CALCULATIONS"]
        assert result.status is AdviceStatus.INSUFFICIENT_DATA

    def test_violation_dominates_missing_data(self):
        """One violation BLOCK + one UNEVALUABLE BLOCK => BLOCKED, not INSUFFICIENT_DATA."""
        result = AdviceEngine().evaluate(all_pass_inputs(
            instrument=InstrumentResolutionInput(),  # UNEVALUABLE
            **BLOCK_OVERRIDES_PER_GATE["entitlements_sufficient"],  # violation
        ))
        assert result.status is AdviceStatus.BLOCKED

    def test_empty_inputs_fail_closed_to_insufficient_data(self):
        """All gate inputs absent: every gate is UNEVALUABLE, nothing is fabricated."""
        inputs = AdviceInputs(
            instrument_id="instr-SYN-001",
            as_of=AS_OF,
            valid_until=VALID_UNTIL,
            input_snapshot_id="snap-SYN-001",
            horizon="10D",
            direction=Direction.UNKNOWN,
            risk_summary="no evaluable data",
        )
        result = AdviceEngine().evaluate(inputs)
        assert all(g.status is GateStatus.BLOCK for g in result.gates)
        assert all(g.reason_code == "UNEVALUABLE" for g in result.gates)
        assert result.status is AdviceStatus.INSUFFICIENT_DATA


class TestDegradeRules:
    def test_degrade_caps_qualified_at_review_and_adds_limitation(self):
        inputs = all_pass_inputs(entitlements=EntitlementsInput(
            capability_status=SourceCapabilityStatus.DELAYED))
        result = AdviceEngine().evaluate(inputs)
        assert result.status is AdviceStatus.REVIEW
        assert (
            "gate entitlements_sufficient degraded: DELAYED_DATA_ENTITLEMENT" in result.limitations
        )

    def test_degrade_with_thin_evidence_stays_observe(self):
        inputs = all_pass_inputs(
            evidence_ids=(),
            entitlements=EntitlementsInput(capability_status=SourceCapabilityStatus.DELAYED),
        )
        result = AdviceEngine().evaluate(inputs)
        assert result.status is AdviceStatus.OBSERVE

    def test_every_degraded_gate_adds_one_visible_limitation(self):
        inputs = all_pass_inputs(
            entitlements=EntitlementsInput(capability_status=SourceCapabilityStatus.DELAYED),
            snapshot=SnapshotInput(quality=SnapshotQuality.PARTIAL, fresh=True),
        )
        result = AdviceEngine().evaluate(inputs)
        degraded = [g for g in result.gates if g.status is GateStatus.DEGRADE]
        assert len(degraded) == 2
        for gate in degraded:
            assert f"gate {gate.gate_id} degraded: {gate.reason_code}" in result.limitations


class TestEvidenceLadder:
    def test_no_evidence_ids_observe(self):
        result = AdviceEngine().evaluate(all_pass_inputs(evidence_ids=()))
        assert result.status is AdviceStatus.OBSERVE

    def test_no_explanation_facts_observe(self):
        result = AdviceEngine().evaluate(all_pass_inputs(explanation_facts=()))
        assert result.status is AdviceStatus.OBSERVE

    def test_no_scenarios_review(self):
        result = AdviceEngine().evaluate(all_pass_inputs(scenario_ids=()))
        assert result.status is AdviceStatus.REVIEW

    def test_upstream_limitation_caps_at_review(self):
        result = AdviceEngine().evaluate(
            all_pass_inputs(limitations=("synthetic upstream limitation",)))
        assert result.status is AdviceStatus.REVIEW
        assert "synthetic upstream limitation" in result.limitations


class TestDirectionIndependence:
    @pytest.mark.parametrize("direction", list(Direction))
    def test_direction_carried_unchanged_when_blocked(self, direction):
        inputs = all_pass_inputs(
            direction=direction,
            **BLOCK_OVERRIDES_PER_GATE["critical_contradictions_resolved"],
        )
        result = AdviceEngine().evaluate(inputs)
        assert result.status in {AdviceStatus.BLOCKED, AdviceStatus.INSUFFICIENT_DATA}
        assert result.direction is direction

    @pytest.mark.parametrize("direction", list(Direction))
    def test_direction_carried_unchanged_when_qualified(self, direction):
        result = AdviceEngine().evaluate(all_pass_inputs(direction=direction))
        assert result.status is AdviceStatus.QUALIFIED
        assert result.direction is direction

    def test_same_direction_different_statuses(self):
        """The same BULLISH reading coexists with QUALIFIED and BLOCKED verdicts."""
        qualified = AdviceEngine().evaluate(all_pass_inputs(direction=Direction.BULLISH))
        blocked = AdviceEngine().evaluate(all_pass_inputs(
            direction=Direction.BULLISH,
            **BLOCK_OVERRIDES_PER_GATE["entitlements_sufficient"]))
        assert qualified.direction is blocked.direction is Direction.BULLISH
        assert qualified.status is not blocked.status


class TestProbabilityEvidence:
    CANDIDATE: ClassVar[dict[str, str]] = {
        "model": "synthetic-calib-v1",
        "p_up_10d": "0.62",
        "population": "SYN",
    }

    def test_none_when_probability_not_used(self):
        result = AdviceEngine().evaluate(all_pass_inputs(
            probability_evidence=self.CANDIDATE,
            probability=ProbabilityInput(probability_used=False),
        ))
        assert result.probability_evidence is None
        assert any("probability_evidence withheld" in item for item in result.limitations)

    def test_none_when_calibration_aging(self):
        result = AdviceEngine().evaluate(all_pass_inputs(
            probability_evidence=self.CANDIDATE,
            probability=ProbabilityInput(
                probability_used=True, calibration_valid=True,
                out_of_sample_validated=True, calibration_current=False),
        ))
        assert result.probability_evidence is None
        assert any("probability_evidence withheld" in item for item in result.limitations)

    def test_none_when_uncalibrated_and_blocked(self):
        result = AdviceEngine().evaluate(all_pass_inputs(
            probability_evidence=self.CANDIDATE,
            **BLOCK_OVERRIDES_PER_GATE["probability_calibrated_if_used"],
        ))
        assert result.status is AdviceStatus.BLOCKED
        assert result.probability_evidence is None

    def test_propagated_only_when_fully_calibrated(self):
        result = AdviceEngine().evaluate(all_pass_inputs(
            probability_evidence=self.CANDIDATE,
            probability=ProbabilityInput(
                probability_used=True, calibration_valid=True,
                out_of_sample_validated=True, calibration_current=True),
        ))
        assert result.probability_evidence is not None
        assert dict(result.probability_evidence) == self.CANDIDATE

    def test_absent_candidate_stays_none_without_limitation(self):
        result = AdviceEngine().evaluate(all_pass_inputs())
        assert result.probability_evidence is None
        assert not any("probability_evidence" in item for item in result.limitations)


class TestReplayDeterminism:
    def test_replay_100_iterations_identical_hash(self):
        """100 rebuilds of identical inputs => one advice_id, one canonical result hash."""
        advice_ids = set()
        result_hashes = set()
        for _ in range(100):
            result = AdviceEngine().evaluate(all_pass_inputs())
            advice_ids.add(result.advice_id)
            result_hashes.add(canonical_json_hash(result))
        assert len(advice_ids) == 1
        assert len(result_hashes) == 1

    def test_replay_blocked_scenario_identical_hash(self):
        hashes = {
            canonical_json_hash(AdviceEngine().evaluate(
                all_pass_inputs(**BLOCK_OVERRIDES_PER_GATE["minimum_liquidity"])))
            for _ in range(100)
        }
        assert len(hashes) == 1

    def test_advice_id_is_canonical_hash_form(self):
        result = AdviceEngine().evaluate(all_pass_inputs())
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", result.advice_id)

    def test_different_inputs_different_advice_id(self):
        a = AdviceEngine().evaluate(all_pass_inputs())
        b = AdviceEngine().evaluate(all_pass_inputs(horizon="20D"))
        assert a.advice_id != b.advice_id


class TestSingleAuthority:
    def test_single_advice_engine_class_under_src(self):
        """Static proof: exactly one 'class AdviceEngine' definition under src/."""
        src_root = Path(__file__).resolve().parents[2] / "src"
        assert src_root.is_dir()
        pattern = re.compile(r"^class AdviceEngine\b", re.MULTILINE)
        occurrences = []
        for path in sorted(src_root.rglob("*.py")):
            matches = pattern.findall(path.read_text(encoding="utf-8"))
            if matches:
                occurrences.append((path, len(matches)))
        assert occurrences == [
            (src_root / "vertex_core" / "decision" / "advice.py", 1)
        ], f"expected exactly one AdviceEngine definition, found: {occurrences}"
