"""Public API of the Vertex data-quality engine (data_quality owner).

Session-aware freshness policies, layered envelope-quality evaluation,
coverage reporting and cross-source conflict detection — all pure,
deterministic and fail-closed. Market-data observations only; no account,
order or transactional concept exists in this package.
"""

from vertex_core.data.conflict import (
    CONFLICT_CODE_UNIT_MISMATCH,
    CONFLICT_CODE_VALUE_DIVERGENCE,
    ConflictRecord,
    FieldObservation,
    detect_conflicts,
)
from vertex_core.data.freshness import (
    FRESHNESS_POLICIES,
    FRESHNESS_REGISTRY_VERSION,
    FreshnessPolicy,
    FreshnessStatus,
    SessionState,
    UnknownFreshnessPolicyError,
    evaluate_freshness,
    get_freshness_policy,
)
from vertex_core.data.quality import (
    CoverageReport,
    QualityChecks,
    QualityLayer,
    QualityViolation,
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

__all__ = [
    # conflict
    "CONFLICT_CODE_UNIT_MISMATCH",
    "CONFLICT_CODE_VALUE_DIVERGENCE",
    # freshness
    "FRESHNESS_POLICIES",
    "FRESHNESS_REGISTRY_VERSION",
    "ConflictRecord",
    # quality
    "CoverageReport",
    "FieldObservation",
    "FreshnessPolicy",
    "FreshnessStatus",
    "QualityChecks",
    "QualityLayer",
    "QualityViolation",
    "SessionState",
    "UnknownFreshnessPolicyError",
    "ViolationSeverity",
    "aggregate_violations",
    "check_bounds",
    "check_conflicts",
    "check_coverage",
    "check_entitlement",
    "check_freshness",
    "check_identity",
    "check_price_coherence",
    "check_schema",
    "check_time_order",
    "check_units",
    "collect_violations",
    "coverage_ratio",
    "detect_conflicts",
    "evaluate_envelope_quality",
    "evaluate_freshness",
    "get_freshness_policy",
]
