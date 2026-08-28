"""Versioned catalog of the ten decision gates (DECISION_ENGINE.md order).

Every evaluator is a pure function: simple typed inputs in, one
:class:`~vertex_core.contracts.decision.GateResult` out. No network, no
clock, no randomness, no data fetching — the caller supplies every fact.

Fail-closed rule (ADR-014): a gate that cannot be evaluated — any required
input is ``None`` or carries an invalid value — is ``BLOCK`` with
``reason_code = "UNEVALUABLE"``. There is no ``UNKNOWN`` gate state, and a
missing observation is never replaced by zero or a default.

Reason-code vocabulary (consumed by the advice engine's status mapping):

- ``UNEVALUABLE`` and any code starting with ``MISSING`` signal absent
  required data (mapped to ``INSUFFICIENT_DATA`` when blocking);
- every other blocking code signals a real rule violation (mapped to
  ``BLOCKED``).

Each gate carries its own version; bump a gate's version whenever its rule,
inputs or reason codes change.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping, Optional

from vertex_core.contracts.decision import GateResult
from vertex_core.contracts.enums import (
    AssetClass,
    CalculationStatus,
    GateStatus,
    IdentityStatus,
    SnapshotQuality,
    SourceCapabilityStatus,
)

__all__ = [
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
]

REASON_UNEVALUABLE = "UNEVALUABLE"
"""Canonical reason code of a gate that cannot be evaluated (fail-closed BLOCK)."""


def _unevaluable(gate_id: str, version: str, message: str) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.BLOCK,
        reason_code=REASON_UNEVALUABLE,
        message=message,
    )


# ---------------------------------------------------------------------------
# Gate 1 — instrument_resolved
# ---------------------------------------------------------------------------

INSTRUMENT_RESOLVED_GATE_ID = "instrument_resolved"
INSTRUMENT_RESOLVED_VERSION = "1.0.0"


def evaluate_instrument_resolved(
    *,
    identity_status: Optional[IdentityStatus],
    resolved_with_conid: Optional[bool],
) -> GateResult:
    """Gate 1: the instrument identity is unambiguously resolved.

    - ``identity_status`` missing -> BLOCK ``UNEVALUABLE``;
    - ``UNRESOLVED`` -> BLOCK ``UNRESOLVED_IDENTITY``;
    - ``AMBIGUOUS`` -> BLOCK ``AMBIGUOUS_IDENTITY`` (analysis on the wrong
      instrument is never acceptable);
    - ``RESOLVED`` with ``resolved_with_conid`` missing -> BLOCK ``UNEVALUABLE``;
    - ``RESOLVED`` without a confirming IBKR con_id -> DEGRADE
      ``RESOLVED_WITHOUT_CONID`` (visible limitation);
    - ``RESOLVED`` with con_id confirmation -> PASS ``RESOLVED``.
    """
    gate_id, version = INSTRUMENT_RESOLVED_GATE_ID, INSTRUMENT_RESOLVED_VERSION
    if identity_status is None or not isinstance(identity_status, IdentityStatus):
        return _unevaluable(gate_id, version, "identity_status is missing or invalid")
    if identity_status is IdentityStatus.UNRESOLVED:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="UNRESOLVED_IDENTITY",
            message="instrument identity is unresolved",
            observed_values={"identity_status": identity_status.value},
        )
    if identity_status is IdentityStatus.AMBIGUOUS:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="AMBIGUOUS_IDENTITY",
            message="instrument identity is ambiguous",
            observed_values={"identity_status": identity_status.value},
        )
    if resolved_with_conid is None or not isinstance(resolved_with_conid, bool):
        return _unevaluable(gate_id, version, "resolved_with_conid is missing or invalid")
    if not resolved_with_conid:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="RESOLVED_WITHOUT_CONID",
            message="identity resolved without an IBKR con_id confirmation",
            observed_values={"identity_status": identity_status.value, "resolved_with_conid": False},
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="RESOLVED",
        message="instrument identity resolved and confirmed",
        observed_values={"identity_status": identity_status.value, "resolved_with_conid": True},
    )


# ---------------------------------------------------------------------------
# Gate 2 — entitlements_sufficient
# ---------------------------------------------------------------------------

ENTITLEMENTS_SUFFICIENT_GATE_ID = "entitlements_sufficient"
ENTITLEMENTS_SUFFICIENT_VERSION = "1.0.0"


def evaluate_entitlements_sufficient(
    *,
    capability_status: Optional[SourceCapabilityStatus],
) -> GateResult:
    """Gate 2: the market-data entitlements actually cover the required capability.

    - missing -> BLOCK ``UNEVALUABLE``;
    - ``AVAILABLE`` -> PASS ``ENTITLED``;
    - ``DELAYED`` -> DEGRADE ``DELAYED_DATA_ENTITLEMENT``;
    - ``MANUAL_EXPORT`` -> DEGRADE ``MANUAL_EXPORT_SOURCE``;
    - ``NOT_ENTITLED`` -> BLOCK ``NOT_ENTITLED``;
    - ``UNSUPPORTED`` -> BLOCK ``UNSUPPORTED_CAPABILITY``;
    - ``ERROR`` -> BLOCK ``SOURCE_ERROR``.
    """
    gate_id, version = ENTITLEMENTS_SUFFICIENT_GATE_ID, ENTITLEMENTS_SUFFICIENT_VERSION
    if capability_status is None or not isinstance(capability_status, SourceCapabilityStatus):
        return _unevaluable(gate_id, version, "capability_status is missing or invalid")
    observed = {"capability_status": capability_status.value}
    if capability_status is SourceCapabilityStatus.AVAILABLE:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.PASS,
            reason_code="ENTITLED",
            message="required market-data capability is available",
            observed_values=observed,
        )
    if capability_status is SourceCapabilityStatus.DELAYED:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="DELAYED_DATA_ENTITLEMENT",
            message="only delayed market data is entitled",
            observed_values=observed,
        )
    if capability_status is SourceCapabilityStatus.MANUAL_EXPORT:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="MANUAL_EXPORT_SOURCE",
            message="capability served through a manual export, not a live feed",
            observed_values=observed,
        )
    reason = {
        SourceCapabilityStatus.NOT_ENTITLED: "NOT_ENTITLED",
        SourceCapabilityStatus.UNSUPPORTED: "UNSUPPORTED_CAPABILITY",
        SourceCapabilityStatus.ERROR: "SOURCE_ERROR",
    }[capability_status]
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.BLOCK,
        reason_code=reason,
        message=f"capability status {capability_status.value} cannot support the analysis",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Gate 3 — snapshot_fresh_and_coherent
# ---------------------------------------------------------------------------

SNAPSHOT_FRESH_AND_COHERENT_GATE_ID = "snapshot_fresh_and_coherent"
SNAPSHOT_FRESH_AND_COHERENT_VERSION = "1.0.0"


def evaluate_snapshot_fresh_and_coherent(
    *,
    quality: Optional[SnapshotQuality],
    fresh: Optional[bool],
) -> GateResult:
    """Gate 3: the evidence snapshot is coherent and inside its freshness window.

    Order: quality first, then freshness.

    - any input missing -> BLOCK ``UNEVALUABLE``;
    - ``CONTRADICTORY`` -> BLOCK ``CONTRADICTORY_SNAPSHOT``;
    - ``MISSING`` -> BLOCK ``MISSING_SNAPSHOT`` (absent data, not a violation);
    - not fresh -> BLOCK ``STALE_SNAPSHOT``;
    - ``GOOD`` and fresh -> PASS ``FRESH_AND_COHERENT``;
    - ``PARTIAL`` and fresh -> DEGRADE ``PARTIAL_SNAPSHOT``;
    - ``DEGRADED`` and fresh -> DEGRADE ``DEGRADED_SNAPSHOT``.
    """
    gate_id, version = SNAPSHOT_FRESH_AND_COHERENT_GATE_ID, SNAPSHOT_FRESH_AND_COHERENT_VERSION
    if quality is None or not isinstance(quality, SnapshotQuality):
        return _unevaluable(gate_id, version, "snapshot quality is missing or invalid")
    if fresh is None or not isinstance(fresh, bool):
        return _unevaluable(gate_id, version, "snapshot freshness flag is missing or invalid")
    observed: dict[str, Any] = {"quality": quality.value, "fresh": fresh}
    if quality is SnapshotQuality.CONTRADICTORY:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="CONTRADICTORY_SNAPSHOT",
            message="snapshot carries contradictory evidence",
            observed_values=observed,
        )
    if quality is SnapshotQuality.MISSING:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="MISSING_SNAPSHOT",
            message="required snapshot evidence is missing",
            observed_values=observed,
        )
    if not fresh:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="STALE_SNAPSHOT",
            message="snapshot is outside its freshness window",
            observed_values=observed,
        )
    if quality is SnapshotQuality.GOOD:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.PASS,
            reason_code="FRESH_AND_COHERENT",
            message="snapshot is fresh and coherent",
            observed_values=observed,
        )
    reason = "PARTIAL_SNAPSHOT" if quality is SnapshotQuality.PARTIAL else "DEGRADED_SNAPSHOT"
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.DEGRADE,
        reason_code=reason,
        message=f"snapshot quality is {quality.value}",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Gate 4 — session_and_event_known
# ---------------------------------------------------------------------------

SESSION_AND_EVENT_KNOWN_GATE_ID = "session_and_event_known"
SESSION_AND_EVENT_KNOWN_VERSION = "1.0.0"


def evaluate_session_and_event_known(
    *,
    session_known: Optional[bool],
    event_calendar_known: Optional[bool],
) -> GateResult:
    """Gate 4: market session state and the event calendar are known.

    - any input missing -> BLOCK ``UNEVALUABLE``;
    - session state unknown -> BLOCK ``SESSION_UNKNOWN``;
    - event calendar incomplete -> DEGRADE ``EVENT_CALENDAR_INCOMPLETE``;
    - both known -> PASS ``SESSION_AND_EVENT_KNOWN``.
    """
    gate_id, version = SESSION_AND_EVENT_KNOWN_GATE_ID, SESSION_AND_EVENT_KNOWN_VERSION
    if session_known is None or not isinstance(session_known, bool):
        return _unevaluable(gate_id, version, "session_known is missing or invalid")
    if event_calendar_known is None or not isinstance(event_calendar_known, bool):
        return _unevaluable(gate_id, version, "event_calendar_known is missing or invalid")
    observed = {"session_known": session_known, "event_calendar_known": event_calendar_known}
    if not session_known:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="SESSION_UNKNOWN",
            message="market session state is unknown",
            observed_values=observed,
        )
    if not event_calendar_known:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="EVENT_CALENDAR_INCOMPLETE",
            message="event calendar coverage is incomplete",
            observed_values=observed,
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="SESSION_AND_EVENT_KNOWN",
        message="session state and event calendar are known",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Gate 5 — minimum_liquidity
# ---------------------------------------------------------------------------

MINIMUM_LIQUIDITY_GATE_ID = "minimum_liquidity"
MINIMUM_LIQUIDITY_VERSION = "1.0.0"


def evaluate_minimum_liquidity(
    *,
    asset_class: Optional[AssetClass],
    observed_liquidity: Optional[Decimal],
    required_minimum: Optional[Decimal],
    observation_delayed: Optional[bool],
) -> GateResult:
    """Gate 5: observed liquidity meets the per-asset-class minimum.

    The caller supplies both the observation and the asset-class threshold
    (thresholds are configuration owned upstream; this gate never invents
    one and never substitutes zero for a missing observation).

    - any input missing, non-finite, negative observation or non-positive
      threshold -> BLOCK ``UNEVALUABLE``;
    - observed < required -> BLOCK ``LIQUIDITY_BELOW_MINIMUM``;
    - observed >= required but the observation is delayed -> DEGRADE
      ``DELAYED_LIQUIDITY_OBSERVATION``;
    - observed >= required, timely -> PASS ``LIQUIDITY_SUFFICIENT``.
    """
    gate_id, version = MINIMUM_LIQUIDITY_GATE_ID, MINIMUM_LIQUIDITY_VERSION
    if asset_class is None or not isinstance(asset_class, AssetClass):
        return _unevaluable(gate_id, version, "asset_class is missing or invalid")
    if observed_liquidity is None or not isinstance(observed_liquidity, Decimal):
        return _unevaluable(gate_id, version, "observed_liquidity is missing or invalid")
    if required_minimum is None or not isinstance(required_minimum, Decimal):
        return _unevaluable(gate_id, version, "required_minimum is missing or invalid")
    if observation_delayed is None or not isinstance(observation_delayed, bool):
        return _unevaluable(gate_id, version, "observation_delayed is missing or invalid")
    if not observed_liquidity.is_finite() or observed_liquidity < 0:
        return _unevaluable(gate_id, version, "observed_liquidity must be a finite Decimal >= 0")
    if not required_minimum.is_finite() or required_minimum <= 0:
        return _unevaluable(gate_id, version, "required_minimum must be a finite Decimal > 0")
    observed = {
        "asset_class": asset_class.value,
        "observed_liquidity": observed_liquidity,
        "observation_delayed": observation_delayed,
    }
    thresholds = {"required_minimum": required_minimum}
    if observed_liquidity < required_minimum:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="LIQUIDITY_BELOW_MINIMUM",
            message="observed liquidity is below the asset-class minimum",
            observed_values=observed,
            thresholds=thresholds,
        )
    if observation_delayed:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="DELAYED_LIQUIDITY_OBSERVATION",
            message="liquidity meets the minimum but the observation is delayed",
            observed_values=observed,
            thresholds=thresholds,
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="LIQUIDITY_SUFFICIENT",
        message="observed liquidity meets the asset-class minimum",
        observed_values=observed,
        thresholds=thresholds,
    )


# ---------------------------------------------------------------------------
# Gate 6 — calculations_valid
# ---------------------------------------------------------------------------

CALCULATIONS_VALID_GATE_ID = "calculations_valid"
CALCULATIONS_VALID_VERSION = "1.0.0"


def evaluate_calculations_valid(
    *,
    calculation_statuses: Optional[Mapping[str, CalculationStatus]],
) -> GateResult:
    """Gate 6: every numeric calculation backing the advice is valid.

    - mapping missing or containing a non-``CalculationStatus`` value ->
      BLOCK ``UNEVALUABLE``;
    - empty mapping -> BLOCK ``MISSING_CALCULATIONS`` (no calculation
      evidence exists — absent data, not a violation);
    - any ``INVALID`` -> BLOCK ``INVALID_CALCULATION`` (violation);
    - any ``NOT_IMPLEMENTED`` (and none ``INVALID``) -> DEGRADE
      ``NOT_IMPLEMENTED_CALCULATION`` (the absent capability is named,
      never presented as pending);
    - all ``OK`` -> PASS ``ALL_CALCULATIONS_VALID``.
    """
    gate_id, version = CALCULATIONS_VALID_GATE_ID, CALCULATIONS_VALID_VERSION
    if calculation_statuses is None or not isinstance(calculation_statuses, Mapping):
        return _unevaluable(gate_id, version, "calculation_statuses is missing or invalid")
    for key, status in calculation_statuses.items():
        if not isinstance(key, str) or not key or not isinstance(status, CalculationStatus):
            return _unevaluable(
                gate_id, version, "calculation_statuses must map non-empty ids to CalculationStatus"
            )
    if len(calculation_statuses) == 0:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="MISSING_CALCULATIONS",
            message="no calculation evidence is available",
        )
    observed = {key: status.value for key, status in sorted(calculation_statuses.items())}
    invalid_ids = tuple(
        sorted(k for k, s in calculation_statuses.items() if s is CalculationStatus.INVALID)
    )
    if invalid_ids:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="INVALID_CALCULATION",
            message=f"invalid calculations: {', '.join(invalid_ids)}",
            observed_values=observed,
        )
    not_implemented_ids = tuple(
        sorted(k for k, s in calculation_statuses.items() if s is CalculationStatus.NOT_IMPLEMENTED)
    )
    if not_implemented_ids:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="NOT_IMPLEMENTED_CALCULATION",
            message=f"calculations without a real implementation: {', '.join(not_implemented_ids)}",
            observed_values=observed,
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="ALL_CALCULATIONS_VALID",
        message="all backing calculations are valid",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Gate 7 — manual_portfolio_risk_available
# ---------------------------------------------------------------------------

MANUAL_PORTFOLIO_RISK_GATE_ID = "manual_portfolio_risk_available"
MANUAL_PORTFOLIO_RISK_VERSION = "1.0.0"


def evaluate_manual_portfolio_risk_available(
    *,
    risk_required: Optional[bool],
    portfolio_risk_available: Optional[bool],
    declarations_current: Optional[bool],
) -> GateResult:
    """Gate 7: manually declared portfolio risk is available when required.

    Portfolio state comes exclusively from the user's voluntary declarations
    (never from a broker account read).

    - ``risk_required`` missing -> BLOCK ``UNEVALUABLE``;
    - not required -> PASS ``NOT_REQUIRED`` (remaining inputs are irrelevant);
    - required but availability missing -> BLOCK ``UNEVALUABLE``;
    - required and unavailable -> BLOCK ``MISSING_PORTFOLIO_RISK`` (absent
      user declaration — insufficient data, not a violation);
    - required, available, currency of the declarations unknown -> BLOCK
      ``UNEVALUABLE``;
    - available but declarations not current -> DEGRADE
      ``STALE_PORTFOLIO_DECLARATIONS``;
    - available and current -> PASS ``PORTFOLIO_RISK_AVAILABLE``.
    """
    gate_id, version = MANUAL_PORTFOLIO_RISK_GATE_ID, MANUAL_PORTFOLIO_RISK_VERSION
    if risk_required is None or not isinstance(risk_required, bool):
        return _unevaluable(gate_id, version, "risk_required is missing or invalid")
    if not risk_required:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.PASS,
            reason_code="NOT_REQUIRED",
            message="portfolio risk is not required for this advice",
            observed_values={"risk_required": False},
        )
    if portfolio_risk_available is None or not isinstance(portfolio_risk_available, bool):
        return _unevaluable(gate_id, version, "portfolio_risk_available is missing or invalid")
    if not portfolio_risk_available:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="MISSING_PORTFOLIO_RISK",
            message="required manual portfolio risk is not available",
            observed_values={"risk_required": True, "portfolio_risk_available": False},
        )
    if declarations_current is None or not isinstance(declarations_current, bool):
        return _unevaluable(gate_id, version, "declarations_current is missing or invalid")
    observed = {
        "risk_required": True,
        "portfolio_risk_available": True,
        "declarations_current": declarations_current,
    }
    if not declarations_current:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="STALE_PORTFOLIO_DECLARATIONS",
            message="manual portfolio declarations are not current",
            observed_values=observed,
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="PORTFOLIO_RISK_AVAILABLE",
        message="manual portfolio risk is available and current",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Gate 8 — probability_calibrated_if_used
# ---------------------------------------------------------------------------

PROBABILITY_CALIBRATED_GATE_ID = "probability_calibrated_if_used"
PROBABILITY_CALIBRATED_VERSION = "1.0.0"


def evaluate_probability_calibrated_if_used(
    *,
    probability_used: Optional[bool],
    calibration_valid: Optional[bool],
    out_of_sample_validated: Optional[bool],
    calibration_current: Optional[bool],
) -> GateResult:
    """Gate 8: any predictive probability in play is calibrated and validated.

    - ``probability_used`` missing -> BLOCK ``UNEVALUABLE``;
    - probability not used -> PASS ``PROBABILITY_NOT_USED``;
    - used but calibration facts missing -> BLOCK ``UNEVALUABLE``;
    - calibration invalid -> BLOCK ``UNCALIBRATED_PROBABILITY``;
    - no out-of-sample validation -> BLOCK ``NO_OUT_OF_SAMPLE_VALIDATION``;
    - calibrated and validated but the calibration is aging -> DEGRADE
      ``CALIBRATION_AGING``;
    - fully calibrated, validated and current -> PASS ``PROBABILITY_CALIBRATED``.
    """
    gate_id, version = PROBABILITY_CALIBRATED_GATE_ID, PROBABILITY_CALIBRATED_VERSION
    if probability_used is None or not isinstance(probability_used, bool):
        return _unevaluable(gate_id, version, "probability_used is missing or invalid")
    if not probability_used:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.PASS,
            reason_code="PROBABILITY_NOT_USED",
            message="no predictive probability is used by this advice",
            observed_values={"probability_used": False},
        )
    if calibration_valid is None or not isinstance(calibration_valid, bool):
        return _unevaluable(gate_id, version, "calibration_valid is missing or invalid")
    if out_of_sample_validated is None or not isinstance(out_of_sample_validated, bool):
        return _unevaluable(gate_id, version, "out_of_sample_validated is missing or invalid")
    if not calibration_valid:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="UNCALIBRATED_PROBABILITY",
            message="a predictive probability is used without valid calibration",
            observed_values={"probability_used": True, "calibration_valid": False},
        )
    if not out_of_sample_validated:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="NO_OUT_OF_SAMPLE_VALIDATION",
            message="a predictive probability is used without out-of-sample validation",
            observed_values={"probability_used": True, "out_of_sample_validated": False},
        )
    if calibration_current is None or not isinstance(calibration_current, bool):
        return _unevaluable(gate_id, version, "calibration_current is missing or invalid")
    observed = {
        "probability_used": True,
        "calibration_valid": True,
        "out_of_sample_validated": True,
        "calibration_current": calibration_current,
    }
    if not calibration_current:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="CALIBRATION_AGING",
            message="probability calibration is valid but aging",
            observed_values=observed,
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="PROBABILITY_CALIBRATED",
        message="probability calibration is valid, validated and current",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Gate 9 — critical_contradictions_resolved
# ---------------------------------------------------------------------------

CRITICAL_CONTRADICTIONS_GATE_ID = "critical_contradictions_resolved"
CRITICAL_CONTRADICTIONS_VERSION = "1.0.0"


def evaluate_critical_contradictions_resolved(
    *,
    unresolved_critical_count: Optional[int],
    explicit_contradiction_count: Optional[int],
) -> GateResult:
    """Gate 9: critical contradictions are resolved or at least made explicit.

    - any count missing, boolean or negative -> BLOCK ``UNEVALUABLE``;
    - unresolved critical contradictions -> BLOCK
      ``UNRESOLVED_CRITICAL_CONTRADICTION``;
    - only explicit (documented) contradictions -> DEGRADE
      ``EXPLICIT_CONTRADICTIONS_PRESENT``;
    - none -> PASS ``NO_CRITICAL_CONTRADICTION``.
    """
    gate_id, version = CRITICAL_CONTRADICTIONS_GATE_ID, CRITICAL_CONTRADICTIONS_VERSION
    for name, count in (
        ("unresolved_critical_count", unresolved_critical_count),
        ("explicit_contradiction_count", explicit_contradiction_count),
    ):
        if count is None or isinstance(count, bool) or not isinstance(count, int) or count < 0:
            return _unevaluable(gate_id, version, f"{name} is missing or invalid")
    observed = {
        "unresolved_critical_count": unresolved_critical_count,
        "explicit_contradiction_count": explicit_contradiction_count,
    }
    if unresolved_critical_count > 0:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="UNRESOLVED_CRITICAL_CONTRADICTION",
            message=f"{unresolved_critical_count} critical contradiction(s) unresolved",
            observed_values=observed,
        )
    if explicit_contradiction_count > 0:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="EXPLICIT_CONTRADICTIONS_PRESENT",
            message=f"{explicit_contradiction_count} contradiction(s) explicit but present",
            observed_values=observed,
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="NO_CRITICAL_CONTRADICTION",
        message="no critical contradiction remains",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Gate 10 — user_constraints_versioned
# ---------------------------------------------------------------------------

USER_CONSTRAINTS_GATE_ID = "user_constraints_versioned"
USER_CONSTRAINTS_VERSION = "1.0.0"


def evaluate_user_constraints_versioned(
    *,
    constraints_version: Optional[str],
    constraints_current: Optional[bool],
) -> GateResult:
    """Gate 10: the user constraints applied to this advice carry a version.

    - ``constraints_version`` missing -> BLOCK ``UNEVALUABLE``;
    - empty/blank version string -> BLOCK ``UNVERSIONED_CONSTRAINTS``
      (constraints exist but were never versioned — a violation);
    - ``constraints_current`` missing -> BLOCK ``UNEVALUABLE``;
    - versioned but acknowledgement outdated -> DEGRADE
      ``OUTDATED_CONSTRAINTS_ACKNOWLEDGEMENT``;
    - versioned and current -> PASS ``CONSTRAINTS_VERSIONED``.
    """
    gate_id, version = USER_CONSTRAINTS_GATE_ID, USER_CONSTRAINTS_VERSION
    if constraints_version is None or not isinstance(constraints_version, str):
        return _unevaluable(gate_id, version, "constraints_version is missing or invalid")
    if not constraints_version.strip():
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.BLOCK,
            reason_code="UNVERSIONED_CONSTRAINTS",
            message="user constraints exist but carry no version",
        )
    if constraints_current is None or not isinstance(constraints_current, bool):
        return _unevaluable(gate_id, version, "constraints_current is missing or invalid")
    observed = {
        "constraints_version": constraints_version,
        "constraints_current": constraints_current,
    }
    if not constraints_current:
        return GateResult(
            gate_id=gate_id,
            version=version,
            status=GateStatus.DEGRADE,
            reason_code="OUTDATED_CONSTRAINTS_ACKNOWLEDGEMENT",
            message="user constraints are versioned but the acknowledgement is outdated",
            observed_values=observed,
        )
    return GateResult(
        gate_id=gate_id,
        version=version,
        status=GateStatus.PASS,
        reason_code="CONSTRAINTS_VERSIONED",
        message="user constraints are versioned and current",
        observed_values=observed,
    )


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateSpec:
    """One catalog entry: canonical id, version and pure evaluator."""

    gate_id: str
    version: str
    evaluate: Callable[..., GateResult]


GATE_CATALOG: tuple[GateSpec, ...] = (
    GateSpec(INSTRUMENT_RESOLVED_GATE_ID, INSTRUMENT_RESOLVED_VERSION, evaluate_instrument_resolved),
    GateSpec(
        ENTITLEMENTS_SUFFICIENT_GATE_ID,
        ENTITLEMENTS_SUFFICIENT_VERSION,
        evaluate_entitlements_sufficient,
    ),
    GateSpec(
        SNAPSHOT_FRESH_AND_COHERENT_GATE_ID,
        SNAPSHOT_FRESH_AND_COHERENT_VERSION,
        evaluate_snapshot_fresh_and_coherent,
    ),
    GateSpec(
        SESSION_AND_EVENT_KNOWN_GATE_ID,
        SESSION_AND_EVENT_KNOWN_VERSION,
        evaluate_session_and_event_known,
    ),
    GateSpec(MINIMUM_LIQUIDITY_GATE_ID, MINIMUM_LIQUIDITY_VERSION, evaluate_minimum_liquidity),
    GateSpec(CALCULATIONS_VALID_GATE_ID, CALCULATIONS_VALID_VERSION, evaluate_calculations_valid),
    GateSpec(
        MANUAL_PORTFOLIO_RISK_GATE_ID,
        MANUAL_PORTFOLIO_RISK_VERSION,
        evaluate_manual_portfolio_risk_available,
    ),
    GateSpec(
        PROBABILITY_CALIBRATED_GATE_ID,
        PROBABILITY_CALIBRATED_VERSION,
        evaluate_probability_calibrated_if_used,
    ),
    GateSpec(
        CRITICAL_CONTRADICTIONS_GATE_ID,
        CRITICAL_CONTRADICTIONS_VERSION,
        evaluate_critical_contradictions_resolved,
    ),
    GateSpec(USER_CONSTRAINTS_GATE_ID, USER_CONSTRAINTS_VERSION, evaluate_user_constraints_versioned),
)
"""The ten decision gates, in the canonical DECISION_ENGINE.md order."""

GATE_ORDER: tuple[str, ...] = tuple(spec.gate_id for spec in GATE_CATALOG)
"""Canonical gate execution order (ids only)."""

GATE_VERSIONS: Mapping[str, str] = {spec.gate_id: spec.version for spec in GATE_CATALOG}
"""gate_id -> version, as embedded in every advice_id hash."""
