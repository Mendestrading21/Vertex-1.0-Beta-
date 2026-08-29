"""Application factory of the Vertex One API.

``create_app`` builds a deterministic FastAPI application: fixed route order,
explicit ``operation_id`` on every route and an OpenAPI document whose
component set is completed with the request contract — so two fresh
applications always render byte-identical OpenAPI output (see
``vertex_api.openapi_export``).
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

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

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = _build_openapi_schema(app)
        return app.openapi_schema

    app.openapi = custom_openapi
    return app
