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

from vertex_core.contracts.enums import CalculationStatus
from vertex_core.contracts.types import ContractModel, NonEmptyStr, freeze_str_mapping
from vertex_core.decision import AdviceInputs, CalculationsInput

__all__ = [
    "AdvicePreviewRequest",
    "CalculationStatusesInput",
    "EngineInfoResponse",
    "HealthResponse",
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
