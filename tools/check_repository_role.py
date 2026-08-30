#!/usr/bin/env python3
"""Verify that a checkout is the intended Vertex donor or Beta target.

Read-only: invokes only ``git remote get-url``, ``git branch --show-current`` and
``git rev-parse``. It never changes Git configuration or working files.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

EXPECTED = {
    "donor": "Mendestrading21/Vertex-",
    "target": "Mendestrading21/Vertex-1.0-Beta-",
}


def run(root: Path, *args: str) -> str:
    completed = subprocess.run(  # noqa: S603 (argv littéral, sans shell)
        ["git", *args],  # noqa: S607 (git résolu par PATH, argv littéral)
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def normalize_remote(value: str) -> str:
    remote = value.strip().removesuffix(".git")
    if remote.startswith("git@github.com:"):
        return remote.split(":", 1)[1]
    marker = "github.com/"
    if marker in remote:
        return remote.split(marker, 1)[1]
    return remote


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=sorted(EXPECTED))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        origin_raw = run(root, "remote", "get-url", "origin")
        branch = run(root, "branch", "--show-current")
        head = run(root, "rev-parse", "HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(json.dumps({"ok": False, "role": args.role, "error": type(exc).__name__}))
        return 2
    actual = normalize_remote(origin_raw)
    expected = EXPECTED[args.role]
    result = {
        "ok": actual == expected,
        "role": args.role,
        "expected": expected,
        "actual": actual,
        "branch": branch,
        "head": head,
        "root_name": root.name,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

