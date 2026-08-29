"""AST denylist: no forbidden IBKR capability appears anywhere in src.

The forbidden symbols are written as plain STRING literals (never as calls or
attribute accesses) so this test can never itself trip the repository-level
financial boundary scanner. The test proves ABSENCE: production code neither
calls nor references any order/account/position/P&L/execution capability.
"""

from __future__ import annotations

import ast
import pathlib

from vertex_edge_ibkr.adapter import IbAsyncInformationAdapter
from vertex_edge_ibkr.port import ALLOWED_PORT_METHODS, IbkrInformationPort

SRC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src"

# Forbidden capability names, as string literals only (mission + manifest).
FORBIDDEN_SYMBOLS = frozenset(
    {
        "placeOrder",
        "cancelOrder",
        "reqGlobalCancel",
        "exerciseOptions",
        "whatIfOrder",
        "reqIds",
        "reqAutoOpenOrders",
        "reqPositions",
        "reqPositionsMulti",
        "reqAccountUpdates",
        "reqAccountUpdatesMulti",
        "reqAccountSummary",
        "reqPnL",
        "reqPnLSingle",
        "reqExecutions",
        "reqOpenOrders",
        "reqAllOpenOrders",
        "reqCompletedOrders",
        "managedAccounts",
        "accountSummary",
        "openOrders",
        "completedOrders",
        "executions",
        "portfolio",
        "positions",
    }
)

TRANSACTIONAL_KEYWORDS = (
    "order",
    "account",
    "position",
    "portfolio",
    "execution",
    "pnl",
    "exercise",
)


def _python_files() -> list[pathlib.Path]:
    files = sorted(SRC_DIR.rglob("*.py"))
    assert files, "src tree must exist and contain python files"
    return files


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def test_no_forbidden_symbol_as_call_or_attribute_in_src() -> None:
    findings: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name in FORBIDDEN_SYMBOLS:
                    findings.append(f"{path.name}:{node.lineno} call {name}")
            if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_SYMBOLS:
                findings.append(f"{path.name}:{node.lineno} attribute {node.attr}")
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_SYMBOLS:
                findings.append(f"{path.name}:{node.lineno} name {node.id}")
    assert findings == []


def test_no_forbidden_symbol_defined_or_imported_in_src() -> None:
    findings: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in FORBIDDEN_SYMBOLS:
                    findings.append(f"{path.name}:{node.lineno} def {node.name}")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name in FORBIDDEN_SYMBOLS or alias.asname in FORBIDDEN_SYMBOLS:
                        findings.append(f"{path.name}:{node.lineno} import {alias.name}")
    assert findings == []


def _public_methods(cls: type) -> set[str]:
    return {
        name
        for name, value in vars(cls).items()
        if not name.startswith("_") and callable(value)
    }


def test_port_exposes_exactly_the_information_surface() -> None:
    assert _public_methods(IbkrInformationPort) == set(ALLOWED_PORT_METHODS)


def test_port_has_no_order_account_or_position_method() -> None:
    for name in _public_methods(IbkrInformationPort):
        lowered = name.lower()
        for keyword in TRANSACTIONAL_KEYWORDS:
            assert keyword not in lowered, f"port method {name} carries {keyword!r}"


def test_adapter_public_surface_matches_the_port() -> None:
    assert _public_methods(IbAsyncInformationAdapter) == set(ALLOWED_PORT_METHODS)


def test_adapter_satisfies_the_port_protocol() -> None:
    fake = object.__new__(IbAsyncInformationAdapter)
    assert isinstance(fake, IbkrInformationPort)
