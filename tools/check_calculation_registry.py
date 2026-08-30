#!/usr/bin/env python3
"""Guard: production calculation identifiers must be runtime-approved.

The calculation registry (``docs/03-domain/calculations/CALCULATION_REGISTRY.yaml``)
is the AUTHORITY for financial calculations. This checker prevents the drift in
which production code executes a calculation the registry has not approved.

It fails (exit 1) when:

1. a calculation identifier used in production code is absent from the registry
   (``unknown_calculation_id``);
2. a used identifier exists but its ``runtime_status`` is not ``APPROVED``
   (``calculation_not_runtime_approved``);
3. an ``APPROVED`` entry is missing one of ``required_runtime_fields``, or the
   field is empty (``missing_runtime_field``);
4. a non-``APPROVED`` entry carries no ``blocking_reason``
   (``missing_blocking_reason``);
5. a test file cited by an entry does not exist (``missing_test_file``), or an
   entry declares no test at all while being ``APPROVED``;
6. a declared ``implementation`` path names a file that does not exist
   (``missing_implementation_file``);
7. the registry itself is malformed (duplicate ids, unknown
   ``runtime_status`` value, ...).

Detection rules (deliberately narrow and documented, so the checker never
guesses):

- ``record`` evidence: a string literal on the same line as ``calculation_id=``
  or ``calculation_id:``, or a subscript of ``calculation_statuses[...]``.
  These sites build or key a ``CalculationRecord`` / calculation-status map, so
  the literal IS a calculation identifier. Any such literal must exist in the
  registry — this is how a phantom identifier is caught.
- ``core`` evidence: a string literal matching ``<registry family>.<name>``
  inside the calculation authority packages of ``vertex_core``
  (``calculations/`` and ``decision/``). Those modules only use that namespace
  for calculation identifiers, so a phantom id there is caught too.
- ``reference`` evidence: an exact registry identifier appearing as a string
  literal anywhere else in production code. Exact match only, so no false
  positive.

Documented limitation: outside the two authority directories, the
``<family>.<name>`` namespace is NOT reserved (``performance.refresh``, for
instance, is a legitimate worker topic name), so a phantom identifier invented
outside those directories and outside a ``calculation_id=`` site is not
detected. Widening the rule would require reserving the namespace repo-wide.

Output: JSON ``{"ok": bool, "findings": [...]}`` on stdout. Findings carry only
repository-relative paths, line numbers and identifiers — never file contents,
secrets or market data. Read-only: this tool never writes to the repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

REGISTRY_RELATIVE_PATH = "docs/03-domain/calculations/CALCULATION_REGISTRY.yaml"

PRODUCTION_SOURCE_GLOBS = (
    "apps/*/src",
    "packages/python/*/src",
)

# vertex_core packages that own financial calculation identifiers.
AUTHORITY_DIRECTORY_NAMES = ("calculations", "decision")

APPROVED = "APPROVED"
VALID_RUNTIME_STATUSES = frozenset({APPROVED, "RESEARCH_ONLY", "NOT_IMPLEMENTED"})

SKIP_DIRECTORY_NAMES = frozenset(
    {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
)

_STRING_LITERAL = re.compile(r"""["']([^"'\n]+)["']""")
_RECORD_SITE = re.compile(r"""calculation_id\s*[=:]|calculation_statuses\s*\[""")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


class RegistryError(RuntimeError):
    """The registry file itself cannot be used as an authority."""


def load_registry(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RegistryError("PyYAML is required to read the calculation registry") from exc
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"registry not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"registry is not valid YAML: {type(exc).__name__}") from exc
    if not isinstance(document, dict):
        raise RegistryError("registry root must be a mapping")
    if not isinstance(document.get("calculations"), list):
        raise RegistryError("registry must declare a list of calculations")
    return document


def iter_production_files(root: Path) -> Iterable[Path]:
    for pattern in PRODUCTION_SOURCE_GLOBS:
        for source_root in sorted(root.glob(pattern)):
            if not source_root.is_dir():
                continue
            for path in sorted(source_root.rglob("*.py")):
                if any(part in SKIP_DIRECTORY_NAMES for part in path.parts):
                    continue
                yield path


def is_authority_file(root: Path, path: Path) -> bool:
    parts = path.relative_to(root).parts
    return any(name in parts for name in AUTHORITY_DIRECTORY_NAMES)


def scan_production_usage(
    root: Path, registry_ids: set[str], families: set[str]
) -> dict[str, list[dict[str, Any]]]:
    """Map identifier -> list of usage sites found in production code."""
    usage: dict[str, list[dict[str, Any]]] = {}

    def record(identifier: str, path: Path, line_number: int, evidence: str) -> None:
        usage.setdefault(identifier, []).append(
            {
                "file": path.relative_to(root).as_posix(),
                "line": line_number,
                "evidence": evidence,
            }
        )

    for path in iter_production_files(root):
        authority = is_authority_file(root, path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:  # pragma: no cover - defensive
            continue
        for line_number, line in enumerate(lines, start=1):
            literals = _STRING_LITERAL.findall(line)
            if not literals:
                continue
            record_site = bool(_RECORD_SITE.search(line))
            for literal in literals:
                if not _IDENTIFIER.match(literal):
                    continue
                family = literal.split(".", 1)[0]
                if record_site:
                    record(literal, path, line_number, "record")
                elif authority and family in families:
                    record(literal, path, line_number, "core")
                elif literal in registry_ids:
                    record(literal, path, line_number, "reference")
    return usage


def check(root: Path) -> dict[str, Any]:
    registry_path = root / REGISTRY_RELATIVE_PATH
    document = load_registry(registry_path)
    findings: list[dict[str, Any]] = []

    required_fields = document.get("required_runtime_fields") or []
    if not isinstance(required_fields, list) or not required_fields:
        raise RegistryError("registry must declare a non-empty required_runtime_fields list")

    entries: dict[str, dict[str, Any]] = {}
    for position, entry in enumerate(document["calculations"]):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            findings.append(
                {
                    "code": "malformed_registry_entry",
                    "position": position,
                    "detail": "each calculation must be a mapping carrying a string id",
                }
            )
            continue
        identifier = entry["id"]
        if identifier in entries:
            findings.append(
                {
                    "code": "duplicate_calculation_id",
                    "calculation_id": identifier,
                    "detail": "the registry declares this id more than once",
                }
            )
            continue
        entries[identifier] = entry

    families = {identifier.split(".", 1)[0] for identifier in entries}

    # --- registry self-consistency ---------------------------------------
    for identifier, entry in entries.items():
        status = entry.get("runtime_status")
        if status not in VALID_RUNTIME_STATUSES:
            findings.append(
                {
                    "code": "invalid_runtime_status",
                    "calculation_id": identifier,
                    "detail": f"runtime_status must be one of {sorted(VALID_RUNTIME_STATUSES)}",
                }
            )
            continue
        if status == APPROVED:
            for field in required_fields:
                value = entry.get(field)
                if value is None or (isinstance(value, (str, list, dict)) and len(value) == 0):
                    findings.append(
                        {
                            "code": "missing_runtime_field",
                            "calculation_id": identifier,
                            "field": field,
                            "detail": "an APPROVED entry must carry every required runtime field",
                        }
                    )
        else:
            reason = entry.get("blocking_reason")
            if not isinstance(reason, str) or not reason.strip():
                findings.append(
                    {
                        "code": "missing_blocking_reason",
                        "calculation_id": identifier,
                        "detail": f"a {status} entry must name what blocks its approval",
                    }
                )

        for cited in entry.get("tests") or []:
            if not isinstance(cited, str) or not (root / cited).is_file():
                findings.append(
                    {
                        "code": "missing_test_file",
                        "calculation_id": identifier,
                        "path": cited if isinstance(cited, str) else repr(cited),
                        "detail": "a cited test file does not exist in the repository",
                    }
                )

        implementation = entry.get("implementation")
        if isinstance(implementation, str) and implementation:
            module_path = implementation.split("::", 1)[0]
            if not (root / module_path).is_file():
                findings.append(
                    {
                        "code": "missing_implementation_file",
                        "calculation_id": identifier,
                        "path": module_path,
                        "detail": "the declared implementation file does not exist",
                    }
                )

    # --- production usage vs registry ------------------------------------
    usage = scan_production_usage(root, set(entries), families)
    for identifier in sorted(usage):
        sites = usage[identifier]
        entry = entries.get(identifier)
        if entry is None:
            findings.append(
                {
                    "code": "unknown_calculation_id",
                    "calculation_id": identifier,
                    "sites": sites,
                    "detail": "production code uses an identifier absent from the registry",
                }
            )
            continue
        if entry.get("runtime_status") != APPROVED:
            findings.append(
                {
                    "code": "calculation_not_runtime_approved",
                    "calculation_id": identifier,
                    "runtime_status": entry.get("runtime_status"),
                    "sites": sites,
                    "detail": "production code uses a calculation the registry has not approved",
                }
            )

    return {
        "ok": not findings,
        "findings": findings,
        "summary": {
            "registry_entries": len(entries),
            "approved": sum(1 for e in entries.values() if e.get("runtime_status") == APPROVED),
            "research_only": sum(
                1 for e in entries.values() if e.get("runtime_status") == "RESEARCH_ONLY"
            ),
            "not_implemented": sum(
                1 for e in entries.values() if e.get("runtime_status") == "NOT_IMPLEMENTED"
            ),
            "identifiers_used_in_production": len(usage),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Vertex One repository root",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        report = check(root)
    except RegistryError as exc:
        print(json.dumps({"ok": False, "findings": [{"code": "registry_unusable", "detail": str(exc)}]}, indent=2))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
