"""Canonical, byte-stable rendering of the Vertex One API OpenAPI document.

Single source of the export format: sorted keys, two-space indent,
``ensure_ascii=False`` and one trailing newline. Rendering twice — from two
fresh applications — always yields byte-identical output; the committed
``apps/api/openapi.json`` is exactly this rendering.
"""

import json

from vertex_api.app import create_app

__all__ = ["render_openapi_document", "render_openapi_document_bytes"]


def render_openapi_document() -> str:
    """Return the OpenAPI document of a fresh application in canonical form."""
    app = create_app()
    schema = app.openapi()
    return json.dumps(schema, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def render_openapi_document_bytes() -> bytes:
    """Return the canonical OpenAPI document as UTF-8 bytes."""
    return render_openapi_document().encode("utf-8")
