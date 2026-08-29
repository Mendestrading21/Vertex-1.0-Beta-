"""Wire DTOs of the Vertex One API.

``AdvicePreviewRequest`` IS the engine's ``AdviceInputs`` — same fields, same
validators, same canonical ``advice_id`` hash — with exactly one wire
refinement: ``calculation_statuses`` values are validated into
``CalculationStatus`` members, so the JSON strings a client sends become the
canonical enum values the gates expect. No decision logic lives here; the API
never redefines a contract, it only names its wire boundary.
"""

from typing import Annotated, Literal, Mapping, Optional

from pydantic import AfterValidator, Field, PlainSerializer

from vertex_core.contracts.enums import CalculationStatus, SourceCapabilityStatus
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
    freeze_str_mapping,
)
from vertex_core.decision import AdviceInputs, CalculationsInput

__all__ = [
    "AdvicePreviewRequest",
    "AttentionItem",
    "AttentionSnapshotResponse",
    "CalculationStatusesInput",
    "CapabilityStatusEntry",
    "DbHealth",
    "EngineInfoResponse",
    "HealthResponse",
    "SnapshotHealth",
    "SystemCapabilitiesResponse",
    "SystemHealth",
    "WorkerHealth",
]

FrozenCalculationStatusMapping = Annotated[
    Mapping[str, CalculationStatus],
    AfterValidator(freeze_str_mapping),
    PlainSerializer(dict, return_type=dict),
]
"""calculation id -> ``CalculationStatus``, frozen at validation time."""

FrozenGateVersionMapping = Annotated[
    Mapping[str, NonEmptyStr],
    AfterValidator(freeze_str_mapping),
    PlainSerializer(dict, return_type=dict),
]
"""gate id -> gate version, frozen at validation time."""


class CalculationStatusesInput(CalculationsInput):
    """Wire form of the gate 6 facts.

    Narrows the engine's ``Any``-valued mapping to ``CalculationStatus``
    members so JSON input (``{"iv_surface": "OK"}``) reaches the gate as
    canonical enum values. An absent mapping stays ``None`` (fail-closed at
    the gate), never an empty default.
    """

    calculation_statuses: Optional[FrozenCalculationStatusMapping] = None


class AdvicePreviewRequest(AdviceInputs):
    """Complete certified input set for one advice preview.

    Field-for-field the engine's own ``AdviceInputs`` (subclass — nothing is
    redefined), with the gate 6 mapping typed for the wire. A field left
    absent stays honestly absent and blocks its gate with ``UNEVALUABLE``.
    """

    calculations: CalculationStatusesInput = Field(default_factory=CalculationStatusesInput)


class HealthResponse(ContractModel):
    """Liveness payload: static status and engine version, nothing sensitive."""

    status: Literal["alive"]
    engine_version: NonEmptyStr


class EngineInfoResponse(ContractModel):
    """Engine and contract versions backing every verdict. Carries no secret.

    ``contracts_version`` equals the ``ENGINE_VERSION`` stamp because the
    canonical contracts are versioned by the same identifier that is recorded
    in every calculation and advice contract (``vertex_core.version``).
    """

    engine_version: NonEmptyStr
    contracts_version: NonEmptyStr
    gate_versions: FrozenGateVersionMapping


# ---------------------------------------------------------------------------
# GET /api/v1/today/attention — last published attention snapshot, verbatim
# ---------------------------------------------------------------------------


class AttentionItem(ContractModel):
    """One published attention item, relayed from the worker snapshot.

    ``synthetic`` and the ``population`` label of the response are shown
    exactly as published — synthetic data never blends into a real
    presentation. ``provenance`` is the cluster provenance block verbatim
    (cluster id, member event ids, sources, rights, timestamps,
    instrument_ref); the API adds nothing and recomputes nothing.
    """

    id: NonEmptyStr
    title: NonEmptyStr
    sources: tuple[NonEmptyStr, ...]
    rights: tuple[NonEmptyStr, ...]
    relevance_reasons: tuple[NonEmptyStr, ...] = Field(max_length=3)
    synthetic: bool
    provenance: FrozenStrMapping


class AttentionSnapshotResponse(ContractModel):
    """The last ``attention/global`` snapshot — or an honest empty state.

    ``state = "empty"`` means NO snapshot was ever published: every
    snapshot-derived field is ``None`` (never zero, never invented) and
    ``reason`` says why. ``state = "ok"`` carries the persisted snapshot
    version, ``as_of``, ``population`` (``SYNTHETIC`` shown as-is),
    the full coverage block and the published items.
    """

    state: Literal["ok", "empty"]
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    population: Optional[NonEmptyStr]
    coverage: Optional[FrozenStrMapping]
    items: tuple[AttentionItem, ...]
    rejected_count: Optional[Annotated[int, Field(ge=0)]]
    reason: Optional[NonEmptyStr]


# ---------------------------------------------------------------------------
# GET /api/v1/system/capabilities — manifest x latest probed snapshot + health
# ---------------------------------------------------------------------------


class CapabilityStatusEntry(ContractModel):
    """One declared capability crossed with the latest persisted probe.

    A capability never probed is ``tested_status = ERROR`` with
    ``reason = "NEVER_TESTED"`` and ``tested_at = None`` — absence of a probe
    is never presented as availability.
    """

    capability_id: NonEmptyStr
    family: NonEmptyStr
    declared_mode: NonEmptyStr
    description: Optional[NonEmptyStr]
    tested_status: SourceCapabilityStatus
    tested_at: Optional[UtcDatetime]
    reason: Optional[NonEmptyStr]


class DbHealth(ContractModel):
    """Result of the ``SELECT 1`` probe: ``ok`` or ``error``, nothing more."""

    status: Literal["ok", "error"]


class SnapshotHealth(ContractModel):
    """Presence and age of one published snapshot head (no content)."""

    present: bool
    version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    age_seconds: Optional[int]
    """May be negative under clock drift — reported honestly, never clamped."""


class WorkerHealth(ContractModel):
    """Honest worker liveness proxy: the age of the freshest snapshot.

    The worker exposes no direct heartbeat; the method label
    ``heartbeat_proxy`` names that limitation explicitly instead of
    pretending to observe the process.
    """

    method: Literal["heartbeat_proxy"]
    last_snapshot_as_of: Optional[UtcDatetime]
    age_seconds: Optional[int]
    """May be negative under clock drift — reported honestly, never clamped."""


class SystemHealth(ContractModel):
    """Health blocks: database, both snapshot heads, worker proxy."""

    db: DbHealth
    attention_snapshot: SnapshotHealth
    capabilities_snapshot: SnapshotHealth
    worker: WorkerHealth


class SystemCapabilitiesResponse(ContractModel):
    """Every declared capability with its really-tested status, plus health.

    ``total`` equals the exact number of manifest entries; ``as_of`` and
    ``snapshot_version`` describe the persisted capabilities snapshot
    (``None`` when never published). ``unknown_probed_capability_ids`` lists
    probed ids absent from the manifest — never silently dropped, never
    merged into the declared set. ``checked_at`` is the response instant.
    """

    checked_at: UtcDatetime
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    total: Annotated[int, Field(ge=0)]
    capabilities: tuple[CapabilityStatusEntry, ...]
    unknown_probed_capability_ids: tuple[NonEmptyStr, ...]
    health: SystemHealth
