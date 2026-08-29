"""Local entry point of the Vertex One API: ``python apps/api/run_local.py``.

Loopback-only and fail-closed: startup is refused if ``VERTEX_API_HOST`` is
set to anything but ``127.0.0.1`` or ``localhost`` (see
``vertex_api.local_server``). This shim only makes the in-repo packages
importable and delegates to the validated runner.
"""

import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _API_DIR.parents[1]
_IMPORT_PATHS = (
    _API_DIR / "src",
    _REPO_ROOT / "packages" / "python" / "vertex_core" / "src",
)
for _path in _IMPORT_PATHS:
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def run() -> None:
    """Start the loopback-only local server (validation before binding)."""
    from vertex_api.local_server import main

    main()


if __name__ == "__main__":
    run()
