#!/usr/bin/env python3
"""Assemble the performance measurement report the budgets gate consumes.

This tool does not invent a number. It runs the measurement producers, collects
what the machine can actually state about itself, and refuses to write a field
it could not determine — an absent metadata field makes
``tools/check_performance_budgets.py`` fail with ``missing_profile_metadata``,
which is the honest outcome: a measurement taken on an undescribed machine is
not comparable to anything.

The report echoes the SHA-256 of ``manifests/performance-budgets.yaml`` so the
gate can detect that a report was produced against a different set of budgets.

The report contains byte counts, durations, versions and a kernel string. It
carries no ticker, instrument, portfolio identifier, user text or trace id;
those labels are refused by the gate itself
(``observability.forbidden_metric_labels``).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_performance_budgets import manifest_hash
from measure_web_bundle import BundleError, measure


def _run(command: list[str]) -> str | None:
    """First line of a command's output, or None when it cannot be obtained."""
    executable = shutil.which(command[0])
    if executable is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argument vectors only
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    line = (completed.stdout or completed.stderr).strip().splitlines()
    return line[0].strip() if line else None


def _memory_mib() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, ValueError, OSError):
        return None
    return int(pages * size / (1024 * 1024))


def _cpu() -> str | None:
    count = os.cpu_count()
    machine = platform.machine() or None
    if count is None or machine is None:
        return None
    return f"{machine} x{count}"


def _disk(root: Path) -> str | None:
    try:
        usage = shutil.disk_usage(root)
    except OSError:
        return None
    return f"{usage.total // (1024**3)}GiB total"


def runner_metadata(root: Path) -> dict[str, Any]:
    """What this machine can truthfully state about itself.

    Fields it cannot determine are simply absent. They are never guessed and
    never filled with a placeholder: a placeholder would satisfy the gate's
    presence check while describing no machine at all.
    """
    fields: dict[str, Any] = {}

    # In GitHub Actions the image name and version are published by the runner
    # itself; off a runner there is no image, and claiming one would be false.
    image = os.environ.get("ImageOS")
    version = os.environ.get("ImageVersion")
    if image:
        fields["runner_image"] = f"{image}/{version}" if version else image

    for key, value in (
        ("cpu", _cpu()),
        ("ram_mib", _memory_mib()),
        ("disk", _disk(root)),
        ("os_kernel", f"{platform.system()} {platform.release()}"),
        ("python_version", platform.python_version()),
        ("node_version", _run(["node", "--version"])),
        ("postgresql_version", _run(["psql", "--version"])),
        ("browser_version", os.environ.get("VERTEX_BROWSER_VERSION")),
        ("cpu_model", _run(["uname", "-p"])),
    ):
        if value:
            fields[key] = value
    return fields


def build(root: Path, profile_id: str, dist: Path) -> dict[str, Any]:
    bundle = measure(dist)
    measurements: list[dict[str, Any]] = [
        {
            "metric_id": "frontend.bundles.initial_gzip_bytes",
            "value": bundle["initial_gzip_bytes"],
            "unit": "byte",
            "samples": 1,
            "scenario_id": "production_build",
            "cache_state": "cold",
            "detail": {
                "initial_files": bundle["initial_files"],
                "gzip_level": bundle["gzip_level"],
            },
        },
        {
            "metric_id": "frontend.bundles.chart_engines_route_chunked",
            "value": bundle["chart_engines_route_chunked"],
            "unit": "boolean",
            "samples": 1,
            "scenario_id": "production_build",
            "cache_state": "cold",
            "detail": {
                "chart_engine_chunks": bundle["chart_engine_chunks"],
                "in_initial_closure": bundle["chart_engines_in_initial_closure"],
            },
        },
    ]

    git_sha = _run(["git", "-C", str(root), "rev-parse", "HEAD"])
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "profile_id": profile_id,
        "dataset_id": "production_build_output",
        "git_sha": git_sha,
        "manifest_hash": manifest_hash(root / "manifests" / "performance-budgets.yaml"),
        "runner_metadata": runner_metadata(root),
        "measurements": measurements,
        "hard_failures_observed": [],
    }


def main(argv: list[str] | None = None) -> int:
    root_default = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="P-CI", help="measurement profile identifier")
    parser.add_argument(
        "--dist",
        type=Path,
        default=root_default / "apps" / "web" / "dist",
        help="built web output directory",
    )
    parser.add_argument("--out", type=Path, required=True, help="report file to write")
    parser.add_argument("root", nargs="?", type=Path, default=root_default)
    args = parser.parse_args(argv)
    try:
        report = build(args.root.resolve(), args.profile, args.dist.resolve())
    except BundleError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "report": str(args.out), "measurements": len(report["measurements"])},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
