"""Test path bootstrap for apps/edge-ibkr (no plugin, no network, no clock)."""

from __future__ import annotations

import pathlib
import sys

_TESTS_DIR = pathlib.Path(__file__).resolve().parent
_EDGE_SRC = _TESTS_DIR.parent / "src"
_REPO_ROOT = _TESTS_DIR.parents[2]
_CORE_SRC = _REPO_ROOT / "packages" / "python" / "vertex_core" / "src"

for _path in (_EDGE_SRC, _CORE_SRC):
    _entry = str(_path)
    if _entry not in sys.path:
        sys.path.insert(0, _entry)
