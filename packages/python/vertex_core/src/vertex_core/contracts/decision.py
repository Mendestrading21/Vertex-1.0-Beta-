"""Decision contracts: gate results and the single authoritative advice.

One ``AdviceResult`` is the only canonical verdict. It is analytical only:
no field instructs, prepares or transmits any transaction, and the human
remains the sole decision maker, acting outside Vertex.

Fail-closed invariant enforced at the model: if any gate is ``BLOCK``, the
advice status must be ``BLOCKED`` or ``INSUFFICIENT_DATA`` — a closed gate can
never coexist with ``OBSERVE``, ``REVIEW`` or ``QUALIFIED``.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Annotated, Any

from pydantic import Field, model_validator

from vertex_core.contracts.enums import AdviceStatus, Direction, GateStatus
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    UtcDatetime,
)

__all__ = ["AdviceResult", "GateResult"]

_BLOCK_COMPATIBLE_STATUSES = frozenset({AdviceStatus.BLOCKED, AdviceStatus.INSUFFICIENT_DATA})


def _empty_frozen_mapping() -> MappingProxyType[str, Any]:
    return MappingProxyType({})


class GateResult(ContractModel):
    """Outcome of one versioned decision gate.

    ``observed_values`` and ``thresholds`` carry the real evidence the gate
    saw; both are frozen at validation time. A gate that cannot be evaluated
    is ``BLOCK`` with ``reason_code = "UNEVALUABLE"`` (fail-closed).
    """

    gate_id: NonEmptyStr
    version: NonEmptyStr
    status: GateStatus
    reason_code: NonEmptyStr
    message: str
    evidence_ids: tuple[str, ...] = ()
    observed_values: FrozenStrMapping = Field(default_factory=_empty_frozen_mapping)
    thresholds: FrozenStrMapping = Field(default_factory=_empty_frozen_mapping)


class AdviceResult(ContractModel):
    """The single authoritative analytical verdict for one instrument.

    Carries status, direction, gates, evidence, limitations and explanation
    facts. ``probability_evidence`` stays ``None`` unless calibrated evidence
    genuinely exists — absence is never converted into a fabricated figure.
    Contains no transactional field of any kind.
    """

    advice_id: NonEmptyStr
    instrument_id: NonEmptyStr
    as_of: UtcDatetime
    valid_until: UtcDatetime
    input_snapshot_id: NonEmptyStr
    engine_version: NonEmptyStr
    status: AdviceStatus
    direction: Direction
    horizon: NonEmptyStr
    gates: Annotated[tuple[GateResult, ...], Field(min_length=1)]
    evidence_ids: tuple[str, ...] = ()
    risk_summary: NonEmptyStr
    scenario_ids: tuple[str, ...] = ()
    probability_evidence: FrozenStrMapping | None = None
    limitations: tuple[str, ...] = ()
    explanation_facts: tuple[str, ...] = ()
    supersedes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _check_invariants(self) -> AdviceResult:
        if self.valid_until < self.as_of:
            raise ValueError("valid_until must not precede as_of")
        if any(gate.status is GateStatus.BLOCK for gate in self.gates):
            if self.status not in _BLOCK_COMPATIBLE_STATUSES:
                raise ValueError(
                    "a BLOCK gate requires advice status BLOCKED or INSUFFICIENT_DATA (fail-closed)"
                )
        return self
