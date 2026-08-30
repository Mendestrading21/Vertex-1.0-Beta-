"""Public API of the Vertex canonical contracts.

Strict, immutable, timezone-aware, fail-closed Pydantic v2 contracts: the
single source of truth for enums, identities, envelopes, calculation lineage
and the decision verdict. Analysis only — no transactional capability exists
in this package.
"""

from vertex_core.contracts.calculation import CalculationRecord, make_calculation_record
from vertex_core.contracts.decision import AdviceResult, GateResult
from vertex_core.contracts.enums import (
    AFFIRMATIVE_STATUSES,
    NON_AFFIRMATIVE_STATUSES,
    AdviceStatus,
    AssetClass,
    CalculationStatus,
    DelayStatus,
    Direction,
    DirectionHypothesis,
    EnvelopeQuality,
    ExerciseStyle,
    GateStatus,
    IdentityStatus,
    OptionRight,
    SettlementType,
    SnapshotQuality,
    SourceCapabilityStatus,
)
from vertex_core.contracts.envelope import DataEnvelope
from vertex_core.contracts.hashing import CanonicalizationError, canonical_json_hash
from vertex_core.contracts.identity import InstrumentId, OptionContractId
from vertex_core.contracts.types import (
    ContractModel,
    CurrencyCode,
    FiniteDecimal,
    FrozenStrMapping,
    Money,
    NonEmptyStr,
    NonNegativeDecimal,
    PositiveDecimal,
    PositiveInt,
    Sha256Ref,
    UtcDatetime,
    ensure_finite_decimal,
    ensure_utc,
    freeze_str_mapping,
)
from vertex_core.version import ENGINE_VERSION

__all__ = [
    # enums
    "AFFIRMATIVE_STATUSES",
    # version
    "ENGINE_VERSION",
    "NON_AFFIRMATIVE_STATUSES",
    # decision
    "AdviceResult",
    "AdviceStatus",
    "AssetClass",
    # calculation
    "CalculationRecord",
    "CalculationStatus",
    # hashing
    "CanonicalizationError",
    # types
    "ContractModel",
    "CurrencyCode",
    # envelope
    "DataEnvelope",
    "DelayStatus",
    "Direction",
    "DirectionHypothesis",
    "EnvelopeQuality",
    "ExerciseStyle",
    "FiniteDecimal",
    "FrozenStrMapping",
    "GateResult",
    "GateStatus",
    "IdentityStatus",
    # identity
    "InstrumentId",
    "Money",
    "NonEmptyStr",
    "NonNegativeDecimal",
    "OptionContractId",
    "OptionRight",
    "PositiveDecimal",
    "PositiveInt",
    "SettlementType",
    "Sha256Ref",
    "SnapshotQuality",
    "SourceCapabilityStatus",
    "UtcDatetime",
    "canonical_json_hash",
    "ensure_finite_decimal",
    "ensure_utc",
    "freeze_str_mapping",
    "make_calculation_record",
]
