"""Export the canonical OpenAPI document of the Vertex One API.

Writes ``apps/api/openapi.json`` in the single canonical byte form (sorted
keys, indent 2, ``ensure_ascii=False``, one trailing newline — see
``vertex_api.openapi_export``). Running the export twice yields byte-identical
files; CI and tests compare the committed file against a fresh rendering.

Usage: ``python tools/export_openapi.py``
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_IMPORT_PATHS = (
    _REPO_ROOT / "apps" / "api" / "src",
    _REPO_ROOT / "packages" / "python" / "vertex_core" / "src",
    _REPO_ROOT / "packages" / "python" / "vertex_persistence" / "src",
)

DEFAULT_TARGET = _REPO_ROOT / "apps" / "api" / "openapi.json"


def main(target: Path | None = None) -> Path:
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
    # Une cible peut être passée en argument, pour exporter deux fois vers des
    # chemins distincts et comparer les octets : c'est ainsi que le déterminisme
    # se PROUVE. Sans cet argument, la porte CI qui promettait un « double
    # export byte-identique » écrivait deux fois le même fichier canonique et
    # ne comparait rien.
    if len(sys.argv) > 2:
        sys.stderr.write("usage: export_openapi.py [cible]\n")
        raise SystemExit(2)
    main(Path(sys.argv[1]) if len(sys.argv) == 2 else None)
