"""The single AdviceEngine: gates in, one canonical AdviceResult out.

This module hosts the ONLY ``AdviceEngine`` in the repository. It aggregates
already-certified facts supplied by the caller: it fetches no data, calls no
AI model, touches no network, reads no clock and uses no randomness. The human
remains the sole decision maker, acting outside Vertex.

Status derivation (deterministic, documented, fail-closed)
----------------------------------------------------------

The ten gates run in the canonical order of
:data:`~vertex_core.decision.gates.GATE_CATALOG`. Then:

1. If any gate is ``BLOCK`` (a BLOCK is never compensated by other gates,
   evidence or any score):

   - every blocking reason code signals absent data (``UNEVALUABLE`` or a
     code starting with ``MISSING``) -> ``INSUFFICIENT_DATA``;
   - at least one blocking reason code is a real rule violation ->
     ``BLOCKED`` (violation dominates missing data).

2. Otherwise a base level is computed from the evidence actually present:

   - ``QUALIFIED``: at least one evidence id, at least one explanation fact,
     at least one scenario id and no upstream limitation;
   - ``REVIEW``: at least one evidence id and one explanation fact, but
     scenarios are missing or upstream limitations exist;
   - ``OBSERVE``: evidence ids or explanation facts are missing (valid data,
     not enough for study).

3. Any ``DEGRADE`` gate caps the status at ``REVIEW`` (a base ``QUALIFIED``
   becomes ``REVIEW``; ``OBSERVE`` stays ``OBSERVE``) and appends one visible
   limitation per degraded gate.

``direction`` is the upstream analytical reading carried through unchanged:
it is strictly independent of the status. ``probability_evidence`` is
propagated only when a probability is used AND the probability gate passed
with reason ``PROBABILITY_CALIBRATED``; otherwise it stays ``None`` and a
limitation records the withholding — an uncalibrated probability is never
displayed.

``advice_id`` is the canonical JSON hash of the full inputs plus the engine
version and every gate version: replaying identical inputs yields the same
``advice_id`` and byte-identical result content.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from vertex_core.contracts.decision import AdviceResult, GateResult
from vertex_core.contracts.enums import (
    AdviceStatus,
    AssetClass,
    Direction,
    GateStatus,
    IdentityStatus,
    SnapshotQuality,
    SourceCapabilityStatus,
)
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_core.contracts.types import (
    ContractModel,
    FiniteDecimal,
    FrozenStrMapping,
    NonEmptyStr,
    UtcDatetime,
)
from vertex_core.decision.gates import (
    GATE_CATALOG,
    GATE_VERSIONS,
    PROBABILITY_CALIBRATED_GATE_ID,
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
from vertex_core.version import ENGINE_VERSION

__all__ = [
    "AdviceEngine",
    "AdviceInputs",
    "CalculationsInput",
    "ConstraintsInput",
    "ContradictionsInput",
    "EntitlementsInput",
    "InstrumentResolutionInput",
    "LiquidityInput",
    "PortfolioRiskInput",
    "ProbabilityInput",
    "SessionEventInput",
    "SnapshotInput",
]

_ADVICE_ID_SCHEMA = "vertex.advice_inputs@1"
_PROPAGATE_PROBABILITY_REASON = "PROBABILITY_CALIBRATED"


def _reason_signals_missing_data(reason_code: str) -> bool:
    """True when a blocking reason means 'required data absent', not 'rule violated'."""
    return reason_code == REASON_UNEVALUABLE or reason_code.startswith("MISSING")


# ---------------------------------------------------------------------------
# Per-gate typed inputs. A field left to its ``None`` default is honestly
# absent and makes its gate BLOCK with reason ``UNEVALUABLE`` (fail-closed);
# absence is never replaced by zero or any other fabricated value.
# ---------------------------------------------------------------------------


class InstrumentResolutionInput(ContractModel):
    """Facts for gate 1 (``instrument_resolved``)."""

    identity_status: IdentityStatus | None = None
    resolved_with_conid: bool | None = None


class EntitlementsInput(ContractModel):
    """Facts for gate 2 (``entitlements_sufficient``)."""

    capability_status: SourceCapabilityStatus | None = None


class SnapshotInput(ContractModel):
    """Facts for gate 3 (``snapshot_fresh_and_coherent``)."""

    quality: SnapshotQuality | None = None
    fresh: bool | None = None


class SessionEventInput(ContractModel):
    """Facts for gate 4 (``session_and_event_known``)."""

    session_known: bool | None = None
    event_calendar_known: bool | None = None


class LiquidityInput(ContractModel):
    """Facts for gate 5 (``minimum_liquidity``); the threshold is per asset class."""

    asset_class: AssetClass | None = None
    observed_liquidity: FiniteDecimal | None = None
    required_minimum: FiniteDecimal | None = None
    observation_delayed: bool | None = None


class CalculationsInput(ContractModel):
    """Facts for gate 6 (``calculations_valid``): calculation id -> CalculationStatus."""

    calculation_statuses: FrozenStrMapping | None = None


class PortfolioRiskInput(ContractModel):
    """Facts for gate 7 (``manual_portfolio_risk_available``); declarations are user-made only."""

    risk_required: bool | None = None
    portfolio_risk_available: bool | None = None
    declarations_current: bool | None = None


class ProbabilityInput(ContractModel):
    """Facts for gate 8 (``probability_calibrated_if_used``)."""

    probability_used: bool | None = None
    calibration_valid: bool | None = None
    out_of_sample_validated: bool | None = None
    calibration_current: bool | None = None


class ContradictionsInput(ContractModel):
    """Facts for gate 9 (``critical_contradictions_resolved``)."""

    unresolved_critical_count: int | None = None
    explicit_contradiction_count: int | None = None


class ConstraintsInput(ContractModel):
    """Facts for gate 10 (``user_constraints_versioned``)."""

    constraints_version: str | None = None
    constraints_current: bool | None = None


class AdviceInputs(ContractModel):
    """Complete, certified input set for one advice evaluation.

    Everything the engine may use is here — the engine adds no data of its
    own. ``direction`` is the upstream analytical reading (independent of the
    final status); ``probability_evidence`` is candidate evidence that is
    propagated only when proven calibrated by gate 8.
    """

    instrument_id: NonEmptyStr
    as_of: UtcDatetime
    valid_until: UtcDatetime
    input_snapshot_id: NonEmptyStr
    horizon: NonEmptyStr
    direction: Direction
    risk_summary: NonEmptyStr
    evidence_ids: tuple[str, ...] = ()
    scenario_ids: tuple[str, ...] = ()
    explanation_facts: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    probability_evidence: FrozenStrMapping | None = None
    supersedes: NonEmptyStr | None = None
    instrument: InstrumentResolutionInput = Field(default_factory=InstrumentResolutionInput)
    entitlements: EntitlementsInput = Field(default_factory=EntitlementsInput)
    snapshot: SnapshotInput = Field(default_factory=SnapshotInput)
    session_event: SessionEventInput = Field(default_factory=SessionEventInput)
    liquidity: LiquidityInput = Field(default_factory=LiquidityInput)
    calculations: CalculationsInput = Field(default_factory=CalculationsInput)
    portfolio_risk: PortfolioRiskInput = Field(default_factory=PortfolioRiskInput)
    probability: ProbabilityInput = Field(default_factory=ProbabilityInput)
    contradictions: ContradictionsInput = Field(default_factory=ContradictionsInput)
    constraints: ConstraintsInput = Field(default_factory=ConstraintsInput)

    @model_validator(mode="after")
    def _check_temporal_consistency(self) -> AdviceInputs:
        if self.valid_until < self.as_of:
            raise ValueError("valid_until must not precede as_of")
        return self


class AdviceEngine:
    """The single decision-status authority: certified inputs -> one AdviceResult.

    Pure and deterministic — identical :class:`AdviceInputs` always produce
    the same ``advice_id`` and the same result content. The engine owns the
    status/gate aggregation only; it never fabricates a figure, never
    softens a BLOCK, and never turns absence into zero.
    """

    def evaluate(self, inputs: AdviceInputs) -> AdviceResult:
        """Run the ten gates in canonical order and derive the verdict.

        See the module docstring for the full documented status rules.
        Raises ``pydantic.ValidationError`` on inconsistent construction and
        never returns a partially evaluated result.
        """
        if not isinstance(inputs, AdviceInputs):
            raise TypeError(f"inputs must be AdviceInputs, got {type(inputs).__name__}")

        gates = self._run_gates(inputs)
        status = self._derive_status(inputs, gates)

        limitations: list[str] = list(inputs.limitations)
        for gate in gates:
            if gate.status is GateStatus.DEGRADE:
                limitations.append(f"gate {gate.gate_id} degraded: {gate.reason_code}")

        probability_evidence = self._propagated_probability_evidence(inputs, gates, limitations)

        advice_id = canonical_json_hash(
            {
                "schema": _ADVICE_ID_SCHEMA,
                "engine_version": ENGINE_VERSION,
                "gate_versions": dict(GATE_VERSIONS),
                "inputs": inputs,
            }
        )

        return AdviceResult(
            advice_id=advice_id,
            instrument_id=inputs.instrument_id,
            as_of=inputs.as_of,
            valid_until=inputs.valid_until,
            input_snapshot_id=inputs.input_snapshot_id,
            engine_version=ENGINE_VERSION,
            status=status,
            direction=inputs.direction,
            horizon=inputs.horizon,
            gates=gates,
            evidence_ids=inputs.evidence_ids,
            risk_summary=inputs.risk_summary,
            scenario_ids=inputs.scenario_ids,
            probability_evidence=probability_evidence,
            limitations=tuple(limitations),
            explanation_facts=inputs.explanation_facts,
            supersedes=inputs.supersedes,
        )

    @staticmethod
    def _run_gates(inputs: AdviceInputs) -> tuple[GateResult, ...]:
        """Evaluate the ten gates in the canonical GATE_CATALOG order."""
        gates = (
            evaluate_instrument_resolved(
                identity_status=inputs.instrument.identity_status,
                resolved_with_conid=inputs.instrument.resolved_with_conid,
            ),
            evaluate_entitlements_sufficient(
                capability_status=inputs.entitlements.capability_status,
            ),
            evaluate_snapshot_fresh_and_coherent(
                quality=inputs.snapshot.quality,
                fresh=inputs.snapshot.fresh,
            ),
            evaluate_session_and_event_known(
                session_known=inputs.session_event.session_known,
                event_calendar_known=inputs.session_event.event_calendar_known,
            ),
            evaluate_minimum_liquidity(
                asset_class=inputs.liquidity.asset_class,
                observed_liquidity=inputs.liquidity.observed_liquidity,
                required_minimum=inputs.liquidity.required_minimum,
                observation_delayed=inputs.liquidity.observation_delayed,
            ),
            evaluate_calculations_valid(
                calculation_statuses=inputs.calculations.calculation_statuses,
            ),
            evaluate_manual_portfolio_risk_available(
                risk_required=inputs.portfolio_risk.risk_required,
                portfolio_risk_available=inputs.portfolio_risk.portfolio_risk_available,
                declarations_current=inputs.portfolio_risk.declarations_current,
            ),
            evaluate_probability_calibrated_if_used(
                probability_used=inputs.probability.probability_used,
                calibration_valid=inputs.probability.calibration_valid,
                out_of_sample_validated=inputs.probability.out_of_sample_validated,
                calibration_current=inputs.probability.calibration_current,
            ),
            evaluate_critical_contradictions_resolved(
                unresolved_critical_count=inputs.contradictions.unresolved_critical_count,
                explicit_contradiction_count=inputs.contradictions.explicit_contradiction_count,
            ),
            evaluate_user_constraints_versioned(
                constraints_version=inputs.constraints.constraints_version,
                constraints_current=inputs.constraints.constraints_current,
            ),
        )
        # Structural self-check against the catalog: order and versions match.
        assert tuple(g.gate_id for g in gates) == tuple(s.gate_id for s in GATE_CATALOG)  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
        return gates

    @staticmethod
    def _derive_status(inputs: AdviceInputs, gates: tuple[GateResult, ...]) -> AdviceStatus:
        """Apply the documented status rules (module docstring)."""
        blocking = tuple(g for g in gates if g.status is GateStatus.BLOCK)
        if blocking:
            if all(_reason_signals_missing_data(g.reason_code) for g in blocking):
                return AdviceStatus.INSUFFICIENT_DATA
            return AdviceStatus.BLOCKED

        has_core_evidence = bool(inputs.evidence_ids) and bool(inputs.explanation_facts)
        full_evidence = has_core_evidence and bool(inputs.scenario_ids) and not inputs.limitations
        if full_evidence:
            base = AdviceStatus.QUALIFIED
        elif has_core_evidence:
            base = AdviceStatus.REVIEW
        else:
            base = AdviceStatus.OBSERVE

        if any(g.status is GateStatus.DEGRADE for g in gates) and base is AdviceStatus.QUALIFIED:
            return AdviceStatus.REVIEW
        return base

    @staticmethod
    def _propagated_probability_evidence(
        inputs: AdviceInputs,
        gates: tuple[GateResult, ...],
        limitations: list[str],
    ) -> FrozenStrMapping | None:
        """Propagate probability evidence only when gate 8 proved calibration.

        Any other outcome keeps ``probability_evidence = None`` and, when
        candidate evidence was supplied, appends a visible limitation. This
        also covers the DEGRADE case (``CALIBRATION_AGING``): aging
        calibration withholds the figure, fail-closed.
        """
        if inputs.probability_evidence is None:
            return None
        probability_gate = next(
            g for g in gates if g.gate_id == PROBABILITY_CALIBRATED_GATE_ID
        )
        if (
            probability_gate.status is GateStatus.PASS
            and probability_gate.reason_code == _PROPAGATE_PROBABILITY_REASON
        ):
            return inputs.probability_evidence
        limitations.append(
            "probability_evidence withheld: calibration not proven "
            f"(gate {PROBABILITY_CALIBRATED_GATE_ID}: {probability_gate.reason_code})"
        )
        return None
