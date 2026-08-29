"""HTTP routes of the Vertex One API.

- ``GET /api/v1/health`` — public liveness, no sensitive data;
- ``POST /api/v1/advice/preview`` — protected; a pure pass-through to the
  single ``AdviceEngine`` of ``vertex_core.decision`` (the API computes no
  score, no gate and no verdict of its own);
- ``GET /api/v1/system/engine`` — protected; engine/contract versions only;
- ``GET /api/v1/today/attention`` — protected; the LAST published
  ``attention/global`` snapshot verbatim, or an honest empty state;
- ``GET /api/v1/markets/overview`` — protected; the LAST published
  ``markets_overview/global`` snapshot verbatim, or an honest empty state;
- ``GET /api/v1/system/capabilities`` — protected; the declared capability
  manifest crossed with the latest persisted probe snapshot, plus health;
- ``GET /api/v1/events/stream`` — protected; signal-only SSE
  (``{resource, version}`` head changes and keepalive pings, no business
  data).

Protected routes depend on :func:`vertex_api.auth.require_session` (LOT-09):
a valid WebAuthn session cookie — plus the CSRF double-submit header on every
mutation — or a generic 401 with code ``AUTH_REQUIRED``, fail-closed.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from vertex_api.auth import require_session
from vertex_api.capability_manifest import CapabilityManifest
from vertex_api.events import StreamSettings, get_stream_settings, snapshot_event_stream
from vertex_api.schemas import (
    AdvicePreviewRequest,
    AttentionSnapshotResponse,
    EngineInfoResponse,
    HealthResponse,
    MarketsOverviewResponse,
    SystemCapabilitiesResponse,
)
from vertex_api.snapshot_reader import Clock, SnapshotReader, get_clock, get_snapshot_reader
from vertex_api.snapshot_views import (
    build_attention_response,
    build_capabilities_response,
    build_markets_overview_response,
)
from vertex_core.contracts.decision import AdviceResult
from vertex_core.decision import GATE_VERSIONS, AdviceEngine
from vertex_core.version import ENGINE_VERSION

__all__ = [
    "get_advice_engine",
    "get_capability_manifest",
    "parse_advice_preview_request",
    "protected_router",
    "public_router",
]

SNAPSHOT_KIND_ATTENTION = "attention"
SNAPSHOT_KIND_CAPABILITIES = "capabilities"
SNAPSHOT_KIND_MARKETS = "markets_overview"
SNAPSHOT_KEY_GLOBAL = "global"

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


@protected_router.get(
    "/markets/overview",
    operation_id="get_markets_overview",
    response_model=MarketsOverviewResponse,
    summary="Last published markets overview snapshot (or honest empty state)",
)
def get_markets_overview(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
) -> MarketsOverviewResponse:
    """Serve the LAST ``markets_overview/global`` snapshot exactly as persisted.

    The API relays the worker's published content — population (``SYNTHETIC``
    shown as-is), sectors/tickers with their server-computed returns and
    weights, breadth, coverage account and the deterministic conclusion — and
    computes nothing. With no snapshot ever published the answer is a 200
    with ``state = "empty"``: absent stays absent, nothing is invented.
    """
    snapshot = reader.current(kind=SNAPSHOT_KIND_MARKETS, key=SNAPSHOT_KEY_GLOBAL)
    return build_markets_overview_response(snapshot)


def get_capability_manifest(request: Request) -> CapabilityManifest:
    """Provide the manifest parsed once at startup (``create_app``)."""
    return request.app.state.capability_manifest


@protected_router.get(
    "/today/attention",
    operation_id="get_today_attention",
    response_model=AttentionSnapshotResponse,
    summary="Last published attention snapshot (or honest empty state)",
)
def get_today_attention(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
) -> AttentionSnapshotResponse:
    """Serve the LAST ``attention/global`` snapshot exactly as persisted.

    The API relays the worker's published content — population (``SYNTHETIC``
    shown as-is), coverage, items with provenance — and computes nothing.
    With no snapshot ever published the answer is a 200 with ``state =
    "empty"``: absent stays absent, nothing is invented.
    """
    snapshot = reader.current(kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL)
    return build_attention_response(snapshot)


@protected_router.get(
    "/system/capabilities",
    operation_id="get_system_capabilities",
    response_model=SystemCapabilitiesResponse,
    summary="Declared capabilities crossed with really-probed statuses, plus health",
)
def get_system_capabilities(
    manifest: Annotated[CapabilityManifest, Depends(get_capability_manifest)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SystemCapabilitiesResponse:
    """Cross the FULL declared manifest with the latest persisted probes.

    Every manifest entry is present (``total`` equals the manifest size); a
    capability never probed answers ``ERROR`` with reason ``NEVER_TESTED``.
    Health blocks report the database (``SELECT 1``), both snapshot heads,
    and the worker through the explicitly labeled ``heartbeat_proxy``.
    """
    capabilities = reader.current(kind=SNAPSHOT_KIND_CAPABILITIES, key=SNAPSHOT_KEY_GLOBAL)
    attention = reader.current(kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL)
    return build_capabilities_response(
        manifest,
        snapshot=capabilities,
        attention=attention,
        db_ok=reader.ping(),
        now=clock(),
    )


@protected_router.get(
    "/events/stream",
    operation_id="get_events_stream",
    summary="Signal-only SSE: snapshot head version changes and pings",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": (
                "text/event-stream of `snapshot` events "
                '(`{"resource": "<kind>/<key>", "version": <int>}`) and '
                "keepalive `ping` events. Signal only — no business data; "
                "clients refetch through the REST endpoints."
            ),
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
async def get_events_stream(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    settings: Annotated[StreamSettings, Depends(get_stream_settings)],
) -> StreamingResponse:
    """Stream head-version change signals (database polling, coalesced)."""
    return StreamingResponse(
        snapshot_event_stream(reader, settings),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
