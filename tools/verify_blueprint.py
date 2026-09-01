#!/usr/bin/env python3
"""Validate the documentary Vertex One blueprint without network access.

This validator never mutates the repository. It parses machine-readable files,
checks the lot sequence, verifies SVG XML and validates known examples against
their JSON Schemas when ``jsonschema`` is installed.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Vertex One repository root",
    )
    return parser.parse_args()


# Generated/vendored trees are not blueprint content: third-party packages ship
# intentionally-invalid fixtures (e.g. Redocly YAML tests) that must not fail
# the blueprint gate. Repository source stays fully scanned.
SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "e2e-artifacts",
}

# LOT-26 prolonge le blueprint avec SEC EDGAR point-in-time. Cette
# constante reste explicite : une numérotation ajoutée sans mettre la porte à
# jour doit continuer à faire échouer la CI.
LAST_BLUEPRINT_LOT = 26


def scan_files(root: Path, *patterns: str) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        for path in root.rglob(pattern):
            if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
                continue
            paths.append(path)
    return sorted(paths)


def add_error(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path.as_posix()}: {message}")


def validate_json(root: Path, errors: list[str], counts: Counter[str]) -> None:
    for path in scan_files(root, "*.json"):
        counts["json"] += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - diagnostic path
            add_error(errors, path.relative_to(root), f"invalid JSON: {type(exc).__name__}: {exc}")


def validate_yaml(root: Path, errors: list[str], counts: Counter[str]) -> None:
    paths = scan_files(root, "*.yaml", "*.yml")
    if not paths:
        return
    try:
        import yaml
    except ImportError:
        errors.append("PyYAML is required to validate YAML files")
        return
    for path in paths:
        counts["yaml"] += 1
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - diagnostic path
            add_error(errors, path.relative_to(root), f"invalid YAML: {type(exc).__name__}: {exc}")


def validate_csv(root: Path, errors: list[str], counts: Counter[str]) -> None:
    for path in scan_files(root, "*.csv"):
        counts["csv"] += 1
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            if not rows:
                add_error(errors, path.relative_to(root), "empty CSV")
                continue
            width = len(rows[0])
            for number, row in enumerate(rows[1:], start=2):
                if len(row) != width:
                    add_error(
                        errors,
                        path.relative_to(root),
                        f"row {number} has {len(row)} columns, expected {width}",
                    )
        except Exception as exc:  # pragma: no cover - diagnostic path
            add_error(errors, path.relative_to(root), f"invalid CSV: {type(exc).__name__}: {exc}")


def validate_svg(root: Path, errors: list[str], counts: Counter[str]) -> None:
    for path in scan_files(root, "*.svg"):
        counts["svg"] += 1
        try:
            tree = ET.parse(path)  # noqa: S314 (SVG suivis du dépôt, entrée non hostile)
            if not tree.getroot().tag.endswith("svg"):
                add_error(errors, path.relative_to(root), "root element is not svg")
        except Exception as exc:  # pragma: no cover - diagnostic path
            add_error(
                errors, path.relative_to(root), f"invalid SVG XML: {type(exc).__name__}: {exc}"
            )


def validate_lots(root: Path, errors: list[str], counts: Counter[str]) -> None:
    lot_dir = root / ".claude" / "lots"
    found: dict[int, Path] = {}
    for path in sorted(lot_dir.glob("LOT-*.md")):
        match = re.match(r"LOT-(\d{2})-", path.name)
        if not match:
            add_error(errors, path.relative_to(root), "invalid lot filename")
            continue
        number = int(match.group(1))
        if number in found:
            add_error(errors, path.relative_to(root), f"duplicate LOT-{number:02d}")
        found[number] = path
    expected = list(range(LAST_BLUEPRINT_LOT + 1))
    if sorted(found) != expected:
        errors.append(f"lot sequence is {sorted(found)}, expected {expected}")
    counts["lots"] = len(found)


def validate_schema_examples(root: Path, errors: list[str], counts: Counter[str]) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        counts["schema_examples_skipped"] += 1
        return
    schema_dir = root / "contracts" / "json-schema"
    example_dir = root / "contracts" / "examples"
    pairs = {
        "tradingview-alert-v1": "tradingview-alert-v1",
        "evidence-snapshot-v1": "evidence-snapshot-v1",
        "decision-snapshot-v1": "decision-snapshot-v1",
        "strategy-profile-v1": "strategy-profile-v1",
        "widget-definition-v1": "widget-definition-v1",
        "option-anomaly-snapshot-v1": "option-anomaly-snapshot-v1",
    }
    for schema_stem, example_stem in pairs.items():
        schema_path = schema_dir / f"{schema_stem}.schema.json"
        example_path = example_dir / f"{example_stem}.json"
        if not schema_path.exists() or not example_path.exists():
            continue
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            example = json.loads(example_path.read_text(encoding="utf-8"))
            validator = jsonschema.Draft202012Validator(
                schema, format_checker=jsonschema.FormatChecker()
            )
            failures = sorted(validator.iter_errors(example), key=lambda item: list(item.path))
            for failure in failures:
                location = ".".join(map(str, failure.path)) or "$"
                add_error(
                    errors,
                    example_path.relative_to(root),
                    f"schema failure at {location}: {failure.message}",
                )
            counts["schema_examples"] += 1
        except Exception as exc:  # pragma: no cover - diagnostic path
            add_error(
                errors,
                example_path.relative_to(root),
                f"schema validation error: {type(exc).__name__}: {exc}",
            )


def validate_markdown_fences(root: Path, errors: list[str], counts: Counter[str]) -> None:
    for path in scan_files(root, "*.md"):
        counts["markdown"] += 1
        text = path.read_text(encoding="utf-8")
        if sum(1 for line in text.splitlines() if line.startswith("```")) % 2:
            add_error(errors, path.relative_to(root), "unbalanced fenced code block")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    counts: Counter[str] = Counter()
    if not (root / "CLAUDE.md").exists():
        print(json.dumps({"ok": False, "errors": [f"{root}: not a Vertex One root"]}, indent=2))
        return 2
    validate_json(root, errors, counts)
    validate_yaml(root, errors, counts)
    validate_csv(root, errors, counts)
    validate_svg(root, errors, counts)
    validate_lots(root, errors, counts)
    validate_schema_examples(root, errors, counts)
    validate_markdown_fences(root, errors, counts)
    result = {
        "ok": not errors,
        "root": str(root),
        "counts": dict(sorted(counts.items())),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
