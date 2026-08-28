"""Public API of the Vertex canonical contracts.

Strict, immutable, timezone-aware, fail-closed Pydantic v2 contracts: the
single source of truth for enums, identities, envelopes, calculation lineage
and the decision verdict. Analysis only — no transactional capability exists
in this package.
"""

from vertex_core.contracts.calculation import CalculationRecord, make_calculation_record
from vertex_core.contracts.decision import AdviceResult, GateResult
from vertex_core.contracts.envelope import DataEnvelope
from vertex_core.contracts.enums import (
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
    # version
    "ENGINE_VERSION",
    # enums
    "AdviceStatus",
    "AssetClass",
    "CalculationStatus",
    "DelayStatus",
    "Direction",
    "DirectionHypothesis",
    "EnvelopeQuality",
    "ExerciseStyle",
    "GateStatus",
    "IdentityStatus",
    "OptionRight",
    "SettlementType",
    "SnapshotQuality",
    "SourceCapabilityStatus",
    # types
    "ContractModel",
    "CurrencyCode",
    "FiniteDecimal",
    "FrozenStrMapping",
    "Money",
    "NonEmptyStr",
    "NonNegativeDecimal",
    "PositiveDecimal",
    "PositiveInt",
    "Sha256Ref",
    "UtcDatetime",
    "ensure_finite_decimal",
    "ensure_utc",
    "freeze_str_mapping",
    # hashing
    "CanonicalizationError",
    "canonical_json_hash",
    # identity
    "InstrumentId",
    "OptionContractId",
    # envelope
    "DataEnvelope",
    # calculation
    "CalculationRecord",
    "make_calculation_record",
    # decision
    "AdviceResult",
    "GateResult",
]
