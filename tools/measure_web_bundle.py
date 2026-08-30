#!/usr/bin/env python3
"""Measure the web bundle from Vite's build manifest — facts, not estimates.

This tool answers two questions that ``manifests/performance-budgets.yaml``
asks under ``frontend.bundles``:

1. ``initial_gzip_recommended_max_bytes`` — how many gzipped bytes must a
   browser download BEFORE it can render the first route?
2. ``chart_engines_route_chunked`` — are ECharts and Lightweight Charts kept
   out of that initial payload?

Why the Vite manifest and not the build log: the build log prints one line per
emitted chunk, and an emitted chunk is not necessarily an initial chunk. A
route chunk and a statically-imported chunk look identical there. The manifest
(``dist/.vite/manifest.json``, produced by ``vite build --manifest``) records
``imports`` (static) separately from ``dynamicImports``, which is exactly the
distinction the budget is about. The initial payload is therefore the
transitive closure of ``imports`` — and only ``imports`` — starting from the
entries, plus their CSS.

Why we gzip the files ourselves instead of trusting the printed sizes: the
printed number depends on the reporter's compression level and can change with
a Vite upgrade without a single byte of application code changing. A budget
that moves when the reporter moves is not a budget. We compress at a fixed
level (9) so the number is reproducible across machines and versions.

Documented limitation: gzip size is not transfer size. A server may serve
Brotli, and HTTP/2 header compression is not counted. The budget is expressed
in gzip bytes, so this tool measures gzip bytes; it does not claim to predict
what any particular server will put on the wire.

Output: a measurement document on stdout, in the shape consumed by
``tools/check_performance_budgets.py``. It contains file names, byte counts and
chunk identifiers only — never source contents, secrets or market data.
Read-only with respect to the repository: it reads ``dist/`` and writes
nothing.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any

# Compression level pinned so the measurement is reproducible. Level 9 is the
# strongest gzip level; a server serving level 6 will send slightly MORE bytes,
# so this measurement is the optimistic bound and the budget stays meaningful.
GZIP_LEVEL = 9

# Chunks whose source module lives under one of these prefixes carry a charting
# engine. `manifests/performance-budgets.yaml` requires them to be route
# chunked, i.e. absent from the initial static closure.
CHART_ENGINE_PREFIXES = ("src/charts/",)


class BundleError(RuntimeError):
    """The build output cannot be measured, so no measurement may be claimed."""


def _gzip_bytes(path: Path) -> int:
    """Exact gzipped length of one built file, at a pinned compression level."""
    raw = path.read_bytes()
    # mtime=0 keeps the gzip header byte-identical between runs; without it the
    # measured size is stable but the bytes are not, which makes debugging a
    # regression harder than it needs to be.
    return len(gzip.compress(raw, compresslevel=GZIP_LEVEL, mtime=0))


def _static_closure(manifest: dict[str, Any]) -> set[str]:
    """Manifest keys a browser must fetch before the first render.

    Starts at every entry and follows ``imports`` only. ``dynamicImports`` are
    deliberately NOT followed: that edge is an ``import()`` boundary, which is
    the whole mechanism the ``chart_engines_route_chunked`` budget relies on.
    """
    entries = [key for key, value in manifest.items() if value.get("isEntry")]
    if not entries:
        raise BundleError("the Vite manifest declares no entry; nothing can be measured")

    seen: set[str] = set()
    queue = list(entries)
    while queue:
        key = queue.pop()
        if key in seen:
            continue
        seen.add(key)
        record = manifest.get(key)
        if record is None:
            # A manifest that references a key it does not define is corrupt.
            # Measuring the rest would understate the initial payload.
            raise BundleError(f"the Vite manifest references an undefined chunk: {key}")
        queue.extend(record.get("imports", ()))
    return seen


def measure(dist: Path) -> dict[str, Any]:
    """Measure the built bundle under ``dist``."""
    manifest_path = dist / ".vite" / "manifest.json"
    if not manifest_path.is_file():
        raise BundleError(
            f"{manifest_path} is absent — build with `vite build --manifest` before measuring"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # pragma: no cover - unreadable manifest
        raise BundleError(f"the Vite manifest is unreadable: {exc}") from exc
    if not isinstance(manifest, dict) or not manifest:
        raise BundleError("the Vite manifest is empty or not an object")

    closure = _static_closure(manifest)

    files: dict[str, int] = {}
    for key in sorted(closure):
        record = manifest[key]
        emitted = [record["file"], *record.get("css", ())]
        for relative in emitted:
            path = dist / relative
            if not path.is_file():
                raise BundleError(f"the manifest names a file that does not exist: {relative}")
            files[relative] = _gzip_bytes(path)

    chart_engines_in_closure = sorted(
        key for key in closure if key.startswith(CHART_ENGINE_PREFIXES)
    )
    chart_engine_chunks = sorted(
        key for key in manifest if key.startswith(CHART_ENGINE_PREFIXES)
    )
    if not chart_engine_chunks:
        # Silence here would let the boolean budget pass by deletion: remove the
        # chart modules and "no engine is in the initial payload" becomes true.
        raise BundleError(
            "no chart engine module was found in the manifest; the "
            "chart_engines_route_chunked budget cannot be evaluated"
        )

    return {
        "initial_gzip_bytes": sum(files.values()),
        "initial_files": files,
        "initial_chunk_count": len(closure),
        "chart_engine_chunks": chart_engine_chunks,
        "chart_engines_in_initial_closure": chart_engines_in_closure,
        "chart_engines_route_chunked": not chart_engines_in_closure,
        "gzip_level": GZIP_LEVEL,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dist",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "apps" / "web" / "dist",
        help="built web output directory (must contain .vite/manifest.json)",
    )
    args = parser.parse_args(argv)
    try:
        report = measure(args.dist.resolve())
    except BundleError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": True, **report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
