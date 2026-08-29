#!/usr/bin/env python3
"""Fail when production code calls forbidden IBKR account/order capabilities.

Source of truth: ``manifests/forbidden-capabilities.yaml`` (groups
``ibkr-orders`` and ``ibkr-account-portfolio``). The built-in sets below are a
superset fallback used only when the manifest or PyYAML is unavailable, so the
scanner never silently weakens when its input is missing (fail-closed).

The check reports only file, line and forbidden symbol. It deliberately avoids
printing source lines that might contain credentials or user data.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# Superset fallback — kept in sync with manifests/forbidden-capabilities.yaml.
FALLBACK_CALLS = {
    "accountSummary",
    "cancelOrder",
    "completedOrders",
    "executions",
    "exerciseOptions",
    "managedAccounts",
    "openOrders",
    "placeOrder",
    "portfolio",
    "positions",
    "reqAccountSummary",
    "reqAccountUpdates",
    "reqAccountUpdatesMulti",
    "reqAllOpenOrders",
    "reqAutoOpenOrders",
    "reqCompletedOrders",
    "reqExecutions",
    "reqGlobalCancel",
    "reqIds",
    "reqOpenOrders",
    "reqPnL",
    "reqPnLSingle",
    "reqPositions",
    "reqPositionsMulti",
    "whatIfOrder",
}

FALLBACK_FRAGMENTS = {
    "/iserver/account/order",
    "/iserver/account/orders",
    "/iserver/account/trades",
    "/iserver/account/pnl",
    "/pa/performance",
    "/portfolio/accounts",
    "/portfolio/",
}

# Fragments generic enough to collide with legitimate Vertex routes (the manual
# portfolio page) are only flagged when the line clearly targets a broker API.
AMBIGUOUS_FRAGMENTS = {"/portfolio/", "/portfolio/accounts"}
BROKER_CONTEXT = re.compile(r"iserver|ibkr|interactive\s*brokers|clientportal", re.IGNORECASE)

CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
# "tools" is excluded because this scanner itself must name the forbidden
# symbols and endpoint fragments; tools/ is dev-only, never runtime code.
SKIP_PARTS = {".git", ".venv", "node_modules", "tests", "fixtures", "docs", "dist", "build", "tools"}


def load_manifest(root: Path) -> tuple[set[str], set[str]]:
    """Return (symbols, endpoint fragments) from the manifest, or fallbacks."""
    manifest = root / "manifests" / "forbidden-capabilities.yaml"
    try:
        import yaml  # type: ignore
    except ImportError:
        return set(FALLBACK_CALLS), set(FALLBACK_FRAGMENTS)
    if not manifest.is_file():
        return set(FALLBACK_CALLS), set(FALLBACK_FRAGMENTS)
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return set(FALLBACK_CALLS), set(FALLBACK_FRAGMENTS)
    symbols: set[str] = set()
    fragments: set[str] = set()
    for group in data.get("forbidden_groups", []):
        if group.get("id") in {"ibkr-orders", "ibkr-account-portfolio"}:
            symbols.update(group.get("symbols") or [])
            fragments.update(group.get("endpoint_fragments") or [])
    # Union with the fallback so a trimmed manifest can never weaken the scan.
    return symbols | FALLBACK_CALLS, fragments | FALLBACK_FRAGMENTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    return parser.parse_args()


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def scan_python(path: Path, forbidden: set[str]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return findings
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name in forbidden:
                findings.append({"line": node.lineno, "symbol": name})
    return findings


def scan_text(
    path: Path, forbidden: set[str], fragments: set[str]
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings
    call_pattern = re.compile(
        r"\b(" + "|".join(map(re.escape, sorted(forbidden))) + r")\s*\("
    )
    for number, line in enumerate(text.splitlines(), start=1):
        for match in call_pattern.finditer(line):
            findings.append({"line": number, "symbol": match.group(1)})
        for fragment in fragments:
            if fragment in line:
                if fragment in AMBIGUOUS_FRAGMENTS and not BROKER_CONTEXT.search(line):
                    continue
                findings.append({"line": number, "symbol": fragment})
    return findings


def scan_python_fragments(
    path: Path, fragments: set[str]
) -> list[dict[str, object]]:
    """String-literal fragment scan for Python (endpoint URLs live in strings)."""
    findings: list[dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings
    for number, line in enumerate(text.splitlines(), start=1):
        for fragment in fragments:
            if fragment in line:
                if fragment in AMBIGUOUS_FRAGMENTS and not BROKER_CONTEXT.search(line):
                    continue
                findings.append({"line": number, "symbol": fragment})
    return findings


def main() -> int:
    root = parse_args().root.resolve()
    forbidden, fragments = load_manifest(root)
    results: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in CODE_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        if path.suffix == ".py":
            findings = scan_python(path, forbidden)
            findings.extend(scan_python_fragments(path, fragments))
        else:
            findings = scan_text(path, forbidden, fragments)
        for finding in findings:
            results.append({"path": path.relative_to(root).as_posix(), **finding})
    print(json.dumps({"ok": not results, "findings": results}, indent=2))
    return 0 if not results else 1


if __name__ == "__main__":
    sys.exit(main())
