"""Export the canonical OpenAPI document of the Vertex One API.

Writes ``apps/api/openapi.json`` in the single canonical byte form (sorted
keys, indent 2, ``ensure_ascii=False``, one trailing newline — see
``vertex_api.openapi_export``). Running the export twice yields byte-identical
files; CI and tests compare the committed file against a fresh rendering.

Usage: ``python tools/export_openapi.py``
"""

import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
_IMPORT_PATHS = (
    _REPO_ROOT / "apps" / "api" / "src",
    _REPO_ROOT / "packages" / "python" / "vertex_core" / "src",
)

DEFAULT_TARGET = _REPO_ROOT / "apps" / "api" / "openapi.json"


def main(target: Optional[Path] = None) -> Path:
    """Render the OpenAPI document and write it to ``target`` (canonical path
    by default). Returns the written path."""
    for path in _IMPORT_PATHS:
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    from vertex_api.openapi_export import render_openapi_document_bytes

    destination = DEFAULT_TARGET if target is None else target
    document = render_openapi_document_bytes()
    destination.write_bytes(document)
    sys.stdout.write(f"wrote {destination} ({len(document)} bytes)\n")
    return destination


if __name__ == "__main__":
    main()
