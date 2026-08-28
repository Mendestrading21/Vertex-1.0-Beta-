#!/usr/bin/env python3
"""Create a privacy-preserving, read-only inventory of a donor repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
TEXT_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".json", ".yaml", ".yml", ".md"}
SENSITIVE_NAMES = {".env", "id_rsa", "id_ed25519", "credentials", "secrets"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--max-hash-bytes", type=int, default=2_000_000)
    return parser.parse_args()


def sha256(path: Path, limit: int) -> str | None:
    if path.stat().st_size > limit:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(json.dumps({"ok": False, "error": "root is not a directory"}))
        return 2
    extensions: Counter[str] = Counter()
    top_level: Counter[str] = Counter()
    records: list[dict[str, object]] = []
    sensitive_paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        suffix = path.suffix.lower() or "(none)"
        extensions[suffix] += 1
        top_level[relative.parts[0]] += 1
        if path.name.lower() in SENSITIVE_NAMES or any(token in path.name.lower() for token in ("secret", "credential")):
            sensitive_paths.append(relative.as_posix())
        records.append(
            {
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "suffix": suffix,
                "sha256": sha256(path, args.max_hash_bytes),
                "text_candidate": suffix in TEXT_SUFFIXES,
            }
        )
    result = {
        "ok": True,
        "root_name": root.name,
        "file_count": len(records),
        "total_bytes": sum(int(item["bytes"]) for item in records),
        "extensions": dict(extensions.most_common()),
        "top_level": dict(top_level.most_common()),
        "sensitive_path_names": sensitive_paths,
        "files": records,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

