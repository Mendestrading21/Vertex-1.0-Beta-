"""HTTP routes of the Vertex One API (LOT-12 base: three endpoints).

- ``GET /api/v1/health`` — public liveness, no sensitive data;
- ``POST /api/v1/advice/preview`` — protected; a pure pass-through to the
  single ``AdviceEngine`` of ``vertex_core.decision`` (the API computes no
  score, no gate and no verdict of its own);
- ``GET /api/v1/system/engine`` — protected; engine/contract versions only.

Protected routes depend on :func:`vertex_api.auth.require_session` (LOT-09):
a valid WebAuthn session cookie — plus the CSRF double-submit header on every
mutation — or a generic 401 with code ``AUTH_REQUIRED``, fail-closed.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from vertex_api.auth import require_session
from vertex_api.schemas import AdvicePreviewRequest, EngineInfoResponse, HealthResponse
from vertex_core.contracts.decision import AdviceResult
from vertex_core.decision import GATE_VERSIONS, AdviceEngine
from vertex_core.version import ENGINE_VERSION

__all__ = [
    "get_advice_engine",
    "parse_advice_preview_request",
    "protected_router",
    "public_router",
]

public_router = APIRouter(prefix="/api/v1")

protected_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_session)],
    responses={
        401: {
            "description": (
                "Authentication required: no valid WebAuthn session cookie (or "
                "missing/invalid CSRF header on a mutation). Always the same "
                "generic body with detail code AUTH_REQUIRED."
            )
        }
    },
)


def get_advice_engine() -> AdviceEngine:
    """Provide the single, stateless ``AdviceEngine`` (pure, deterministic)."""
    return AdviceEngine()


async def parse_advice_preview_request(request: Request) -> AdvicePreviewRequest:
    """Validate the raw JSON body in pydantic JSON mode (fail-closed 422).

    The canonical contracts are strict models: python-mode validation (what
    FastAPI applies to an already-parsed body) would reject the legitimate
    wire forms (ISO datetime strings, decimal strings, enum values). Parsing
    the raw bytes with ``model_validate_json`` keeps the contracts strict
    while accepting exactly the canonical JSON wire encoding — any deviation
    (naive datetime, non-finite decimal, unknown field) is rejected as 422.
    """
    raw_body = await request.body()
    try:
        return AdvicePreviewRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


@public_router.get(
    "/health",
    operation_id="get_health",
    response_model=HealthResponse,
    summary="Liveness probe",
)
def get_health() -> HealthResponse:
    """Report process liveness and the engine version. No sensitive data."""
    return HealthResponse(status="alive", engine_version=ENGINE_VERSION)


@protected_router.post(
    "/advice/preview",
    operation_id="post_advice_preview",
    response_model=AdviceResult,
    summary="Evaluate gate inputs through the single AdviceEngine",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AdvicePreviewRequest"}
                }
            },
        }
    },
)
def post_advice_preview(
    inputs: Annotated[AdvicePreviewRequest, Depends(parse_advice_preview_request)],
    engine: Annotated[AdviceEngine, Depends(get_advice_engine)],
) -> AdviceResult:
    """Return the canonical ``AdviceResult`` for certified gate inputs.

    Pass-through only: the route validates the wire payload and hands it to
    the single ``AdviceEngine``. Decimals serialize as strings and datetimes
    as ISO-8601 UTC. The result is analytical — the human decides outside
    Vertex.
    """
    return engine.evaluate(inputs)


@protected_router.get(
    "/system/engine",
    operation_id="get_system_engine",
    response_model=EngineInfoResponse,
    summary="Engine and contract versions",
)
def get_system_engine() -> EngineInfoResponse:
    """Report the engine, contract and per-gate versions. Never a secret."""
    return EngineInfoResponse(
        engine_version=ENGINE_VERSION,
        contracts_version=ENGINE_VERSION,
        gate_versions=dict(GATE_VERSIONS),
    )
