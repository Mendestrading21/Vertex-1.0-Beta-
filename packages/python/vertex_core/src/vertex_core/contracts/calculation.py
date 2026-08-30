"""Calculation lineage contract.

Every deterministic calculation is recorded with its method, engine version,
code SHA, input/result hashes, assumptions, parameters and explicit random
seed, so that identical inputs provably yield identical results and every
figure remains auditable. A capability without a real implementation is
recorded with status ``NOT_IMPLEMENTED`` — never presented as pending.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from pydantic import model_validator

from vertex_core.contracts.enums import CalculationStatus
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    Sha256Ref,
    UtcDatetime,
)
from vertex_core.version import ENGINE_VERSION

__all__ = ["CalculationRecord", "make_calculation_record"]


class CalculationRecord(ContractModel):
    """Immutable record of one deterministic calculation and its lineage.

    ``input_hash`` and ``result_hash`` are canonical JSON hashes; ``parameters``
    is frozen at validation time; ``random_seed`` is mandatory for any
    stochastic method (``None`` means the method uses no randomness).
    """

    calculation_id: NonEmptyStr
    calculation_type: NonEmptyStr
    engine_version: NonEmptyStr
    code_sha: NonEmptyStr
    input_hash: Sha256Ref
    source_event_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    method: NonEmptyStr
    parameters: FrozenStrMapping
    random_seed: int | None = None
    started_at: UtcDatetime
    completed_at: UtcDatetime
    status: CalculationStatus
    warnings: tuple[str, ...] = ()
    result_hash: Sha256Ref
    result: Any

    @model_validator(mode="after")
    def _check_temporal_consistency(self) -> CalculationRecord:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        return self


def make_calculation_record(
    *,
    calculation_id: str,
    calculation_type: str,
    code_sha: str,
    method: str,
    inputs: Any,
    result: Any,
    started_at: datetime,
    completed_at: datetime,
    status: CalculationStatus = CalculationStatus.OK,
    source_event_ids: Sequence[str] = (),
    assumptions: Sequence[str] = (),
    parameters: Mapping[str, Any] | None = None,
    random_seed: int | None = None,
    warnings: Sequence[str] = (),
    engine_version: str = ENGINE_VERSION,
) -> CalculationRecord:
    """Build a :class:`CalculationRecord`, deriving hashes from real data.

    ``input_hash`` and ``result_hash`` are computed with
    :func:`canonical_json_hash` from the actual ``inputs`` and ``result``
    objects, and ``engine_version`` defaults to :data:`ENGINE_VERSION`.
    Identical ``inputs`` therefore always produce an identical ``input_hash``.
    Raises the underlying typed errors (``CanonicalizationError``,
    ``ValidationError``) on invalid data — no silent fallback.
    """
    return CalculationRecord(
        calculation_id=calculation_id,
        calculation_type=calculation_type,
        engine_version=engine_version,
        code_sha=code_sha,
        input_hash=canonical_json_hash(inputs),
        source_event_ids=tuple(source_event_ids),
        assumptions=tuple(assumptions),
        method=method,
        parameters={} if parameters is None else parameters,
        random_seed=random_seed,
        started_at=started_at,
        completed_at=completed_at,
        status=status,
        warnings=tuple(warnings),
        result_hash=canonical_json_hash(result),
        result=result,
    )
