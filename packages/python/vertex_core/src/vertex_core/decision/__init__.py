"""Public API of the Vertex decision engine.

Deterministic, pure, analysis-only: the versioned gate catalog, the exact
``decision.risk_reward`` calculation and the single :class:`AdviceEngine`.
No data fetching, no AI, no network, no clock, no transactional capability.
"""

from vertex_core.decision.advice import (
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
from vertex_core.decision.gates import (
    GATE_CATALOG,
    GATE_ORDER,
    GATE_VERSIONS,
    REASON_UNEVALUABLE,
    GateSpec,
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
from vertex_core.decision.risk_reward import (
    RiskRewardInputError,
    RiskRewardResult,
    risk_reward,
)

__all__ = [
    # advice
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
    # gates
    "GATE_CATALOG",
    "GATE_ORDER",
    "GATE_VERSIONS",
    "REASON_UNEVALUABLE",
    "GateSpec",
    "evaluate_calculations_valid",
    "evaluate_critical_contradictions_resolved",
    "evaluate_entitlements_sufficient",
    "evaluate_instrument_resolved",
    "evaluate_manual_portfolio_risk_available",
    "evaluate_minimum_liquidity",
    "evaluate_probability_calibrated_if_used",
    "evaluate_session_and_event_known",
    "evaluate_snapshot_fresh_and_coherent",
    "evaluate_user_constraints_versioned",
    # risk_reward
    "RiskRewardInputError",
    "RiskRewardResult",
    "risk_reward",
]
