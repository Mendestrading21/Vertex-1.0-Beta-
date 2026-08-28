#!/usr/bin/env python3
"""Fail when production code calls forbidden IBKR account/order capabilities.

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


FORBIDDEN_CALLS = {
    "accountSummary",
    "cancelOrder",
    "completedOrders",
    "executions",
    "managedAccounts",
    "openOrders",
    "placeOrder",
    "portfolio",
    "positions",
    "reqAccountSummary",
    "reqAllOpenOrders",
    "reqCompletedOrders",
    "reqExecutions",
    "reqIds",
    "reqOpenOrders",
    "reqPnL",
    "reqPnLSingle",
    "reqPositions",
}

CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
SKIP_PARTS = {".git", ".venv", "node_modules", "tests", "fixtures", "docs", "dist", "build"}


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


def scan_python(path: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return findings
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name in FORBIDDEN_CALLS:
                findings.append({"line": node.lineno, "symbol": name})
    return findings


def scan_text(path: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, sorted(FORBIDDEN_CALLS))) + r")\s*\(")
    for number, line in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line):
            findings.append({"line": number, "symbol": match.group(1)})
    return findings


def main() -> int:
    root = parse_args().root.resolve()
    results: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in CODE_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        findings = scan_python(path) if path.suffix == ".py" else scan_text(path)
        for finding in findings:
            results.append({"path": path.relative_to(root).as_posix(), **finding})
    print(json.dumps({"ok": not results, "findings": results}, indent=2))
    return 0 if not results else 1


if __name__ == "__main__":
    sys.exit(main())

