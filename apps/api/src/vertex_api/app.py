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

from vertex_api.routes import protected_router, public_router
from vertex_api.schemas import AdvicePreviewRequest
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
    request_schema = AdvicePreviewRequest.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    definitions: dict[str, Any] = dict(request_schema.pop("$defs", {}))
    definitions["AdvicePreviewRequest"] = request_schema

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

    Three routes (health, advice preview, system engine), fail-closed
    authentication on everything except ``/api/v1/health``, and a
    deterministic OpenAPI document titled ``Vertex One API`` versioned by
    ``vertex_core.version.ENGINE_VERSION``.
    """
    app = FastAPI(
        title=_API_TITLE,
        version=ENGINE_VERSION,
        description=_API_DESCRIPTION,
    )
    app.include_router(public_router)
    app.include_router(protected_router)

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = _build_openapi_schema(app)
        return app.openapi_schema

    app.openapi = custom_openapi
    return app
