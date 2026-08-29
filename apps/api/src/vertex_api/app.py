"""Application factory of the Vertex One API.

``create_app`` builds a deterministic FastAPI application: fixed route order,
explicit ``operation_id`` on every route and an OpenAPI document whose
component set is completed with the request contract — so two fresh
applications always render byte-identical OpenAPI output (see
``vertex_api.openapi_export``).
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from vertex_api.ai_explain import AiExplainRequest
from vertex_api.auth import auth_router
from vertex_api.auth.challenges import ChallengeStore
from vertex_api.capability_manifest import load_capability_manifest
from vertex_api.follow_up import CreateThesisRequest, ThesisRevisionRequest
from vertex_api.portfolio import (
    CompensateTransactionRequest,
    CsvImportPreviewRequest,
    ImportConfirmRequest,
    RecordTransactionRequest,
)
from vertex_api.routes import protected_router, public_router
from vertex_api.schemas import AdvicePreviewRequest
from vertex_api.simulation import SimulationPreviewRequest
from vertex_api.snapshot_views import SnapshotContentError
from vertex_core.version import ENGINE_VERSION

__all__ = ["OpenApiComponentCollisionError", "create_app"]

_API_TITLE = "Vertex One API"
_API_DESCRIPTION = (
    "Local, analysis-only API of Vertex One. It serves the canonical "
    "contracts of vertex_core and delegates every verdict to the single "
    "AdviceEngine. No transactional capability exists; the human remains the "
    "sole decision maker, acting outside Vertex."
)


class OpenApiComponentCollisionError(RuntimeError):
    """Two different schema definitions claimed the same component name."""


def _build_openapi_schema(app: FastAPI) -> dict[str, Any]:
    """Render the OpenAPI document, adding the request contract components.

    The advice route parses its body manually (see
    ``vertex_api.routes.parse_advice_preview_request``), so FastAPI does not
    collect ``AdvicePreviewRequest`` on its own. Its validation schema (and
    the sub-schemas it references) are merged into ``components.schemas``
    deterministically; a name carried by both sources must be identical,
    otherwise the build fails (no silent overwrite).
    """
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    definitions: dict[str, Any] = {}
    for name, model in (
        ("AdvicePreviewRequest", AdvicePreviewRequest),
        ("AiExplainRequest", AiExplainRequest),
        ("SimulationPreviewRequest", SimulationPreviewRequest),
        ("RecordTransactionRequest", RecordTransactionRequest),
        ("CompensateTransactionRequest", CompensateTransactionRequest),
        ("CsvImportPreviewRequest", CsvImportPreviewRequest),
        ("ImportConfirmRequest", ImportConfirmRequest),
        ("CreateThesisRequest", CreateThesisRequest),
        ("ThesisRevisionRequest", ThesisRevisionRequest),
    ):
        request_schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        for def_name, definition in request_schema.pop("$defs", {}).items():
            existing = definitions.get(def_name)
            if existing is not None and existing != definition:
                raise OpenApiComponentCollisionError(
                    f"OpenAPI component {def_name!r} has two different definitions"
                )
            definitions[def_name] = definition
        definitions[name] = request_schema

    components = schema.setdefault("components", {}).setdefault("schemas", {})
    for name in sorted(definitions):
        definition = definitions[name]
        existing = components.get(name)
        if existing is not None and existing != definition:
            raise OpenApiComponentCollisionError(
                f"OpenAPI component {name!r} has two different definitions"
            )
        components[name] = definition
    return schema


def _snapshot_content_response() -> JSONResponse:
    """The single fail-closed answer of a snapshot that cannot be served.

    Stable, typed and value-free: the client renders an honest error state
    and no fragment of the persisted payload travels in the response.
    """
    return JSONResponse(
        status_code=500,
        content={
            "code": "SNAPSHOT_CONTENT_INVALID",
            "detail": (
                "a published snapshot cannot be served: its stored content "
                "does not match the published schema"
            ),
        },
    )


def create_app() -> FastAPI:
    """Build the Vertex One API application.

    Health, the passkey authentication ceremonies (``/api/v1/auth``), and the
    protected advice/system routes behind the fail-closed WebAuthn session
    dependency. Each application carries its own in-memory challenge store
    and the capability manifest parsed once from
    ``manifests/ibkr-market-data-capabilities.yaml`` (a committed file — the
    read stays deterministic); no environment is read here, so the OpenAPI
    document stays deterministic.
    """
    app = FastAPI(
        title=_API_TITLE,
        version=ENGINE_VERSION,
        description=_API_DESCRIPTION,
    )
    app.state.challenge_store = ChallengeStore()
    app.state.capability_manifest = load_capability_manifest()
    app.include_router(public_router)
    app.include_router(auth_router)
    app.include_router(protected_router)

    @app.exception_handler(SnapshotContentError)
    async def _snapshot_content_rejected(
        request: Request, exc: SnapshotContentError
    ) -> JSONResponse:
        """Refuse a stored snapshot whose content breaks its published schema.

        Serving such content would present an unverified payload as a
        canonical result, so the relay fails closed. The client receives a
        stable code it can render as an honest error state; the trace keeps
        the RESOURCE and the offending FIELD PATH only — never the exception
        message, which may quote a stored value
        (``.claude/rules/security.md`` forbids any payload fragment in a
        log, and ``SnapshotContentError.field`` is the sanitized part).
        """
        logging.getLogger("vertex_api.snapshot").error(
            "snapshot content rejected on %s: invalid field %s",
            request.url.path,
            exc.field or "unknown",
        )
        return _snapshot_content_response()

    @app.exception_handler(ValidationError)
    async def _snapshot_content_validation_rejected(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """LAST RAMPART: persisted content refused by a wire contract itself.

        Every relay validates the content it relays and raises
        ``SnapshotContentError`` (the handler above). Should one field escape
        that review, pydantic still refuses to build the DTO — and its
        ``ValidationError`` carries ``input_value``, i.e. THE STORED VALUE.
        Letting it reach the default handler would answer an untyped 500 and
        write that payload fragment into the server log. It is caught here
        instead: same typed code, and a trace reduced to the failing model
        and the pydantic error TYPES (``string_type``, ``greater_than``...),
        never a ``loc`` (a mapping key is itself stored data) and never an
        input value.

        A malformed REQUEST never reaches this handler: every request-parsing
        site converts its ``ValidationError`` into a ``RequestValidationError``
        (422), a distinct class — a client error therefore stays a 4xx.
        """
        kinds = sorted(
            {
                str(error.get("type", "unknown"))
                for error in exc.errors(
                    include_url=False, include_context=False, include_input=False
                )
            }
        )
        logging.getLogger("vertex_api.snapshot").error(
            "snapshot content rejected on %s: %s violated by %s",
            request.url.path,
            exc.title,
            ", ".join(kinds) or "unknown",
        )
        return _snapshot_content_response()

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = _build_openapi_schema(app)
        return app.openapi_schema

    app.openapi = custom_openapi
    return app
