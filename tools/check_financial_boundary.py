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

# Symboles dont le NOM NU est aussi du vocabulaire métier légitime de Vertex :
# le portefeuille MANUEL de l'utilisateur a des « positions » et un
# « portfolio », ce sont des clés de contenu et des noms de champs partout dans
# le produit. Les signaler en tant que chaîne produirait 29 faux positifs et
# rendrait la porte illisible — donc inappliquée.
# Ils restent signalés en APPEL et en ACCÈS D'ATTRIBUT (`ib.positions`,
# `ib.portfolio()`), qui sont les formes réellement dangereuses : c'est la
# façon dont on atteindrait la capacité IBKR.
AMBIGUOUS_BARE_SYMBOLS = {
    "portfolio",
    "positions",
}
BROKER_CONTEXT = re.compile(r"iserver|ibkr|interactive\s*brokers|clientportal", re.IGNORECASE)

CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
# `tests` et `tools` ne sont PLUS ignorés : le manifeste déclare
# `scope: [runtime, tests, dependencies, routes, permissions, ai_tools]`, et le
# scanner les écartait — un appel interdit écrit dans un test passait donc la
# porte la plus critique du programme. Les deux fichiers qui nomment
# légitimement ces symboles sont exemptés NOMMÉMENT dans
# `manifests/financial-boundary-allowlist.yaml`, avec un motif écrit.
# `docs` et `fixtures` restent écartés : ce n'est pas du code, et la
# documentation doit pouvoir NOMMER ce qu'elle interdit.
SKIP_PARTS = {".git", ".venv", "node_modules", "fixtures", "docs", "dist", "build"}

ALLOWLIST_FILENAME = "financial-boundary-allowlist.yaml"


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


def load_allowlist(root: Path) -> dict[str, str]:
    """Exemptions NOMMÉES : ``"<chemin>:<symbole>" -> motif``.

    Deux fichiers du dépôt nomment légitimement les capacités interdites : le
    test qui prouve leur ABSENCE, et ce scanner lui-même. Les exempter par
    chemin explicite, avec un motif écrit, vaut mieux que d'écarter des
    répertoires entiers — ce que faisait `SKIP_PARTS`, et qui laissait passer
    un appel interdit dans n'importe quel test.

    Fail-closed : si le fichier d'exemptions est illisible, AUCUNE exemption
    n'est accordée.
    """
    path = root / "manifests" / ALLOWLIST_FILENAME
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    allowed: dict[str, str] = {}
    for entry in data.get("allow") or []:
        missing = [k for k in ("path", "symbol", "reason") if not entry.get(k)]
        if missing:
            raise SystemExit(
                f"manifests/{ALLOWLIST_FILENAME} : entrée incomplète, "
                f"champs manquants {missing}"
            )
        allowed[f"{entry['path']}:{entry['symbol']}"] = str(entry["reason"])
    return allowed


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
    """Toute MENTION d'une capacité interdite, pas seulement son appel.

    Le scanner ne regardait que ``ast.Call``. Quatre vecteurs de code de
    PRODUCTION passaient donc la porte (reproduits par le 6e audit) ::

        send = ib.placeOrder                 # méthode liée, appelée ailleurs
        read = getattr(ib, "reqPositions")   # nom en chaîne
        fn   = {"p": ib.reqAccountSummary}["p"]
        f    = ib.reqPnL                     # alias

    Une capacité interdite ne doit pas être ATTEIGNABLE, pas seulement
    non appelée : obtenir la référence suffit à l'appeler ailleurs. Sont donc
    signalés l'appel, l'accès d'attribut, et le nom écrit en chaîne — ce
    dernier couvrant ``getattr``, l'indexation par nom et ``importlib``.
    """
    findings: list[dict[str, object]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return findings
    seen: set[tuple[int, str]] = set()

    def record(line: int, symbol: str, kind: str) -> None:
        if (line, symbol) in seen:
            return
        seen.add((line, symbol))
        findings.append({"line": line, "symbol": symbol, "kind": kind})

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name in forbidden:
                record(node.lineno, name, "call")
        elif isinstance(node, ast.Attribute):
            if node.attr in forbidden:
                record(node.lineno, node.attr, "attribute")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in forbidden and node.value not in AMBIGUOUS_BARE_SYMBOLS:
                record(node.lineno, node.value, "string")
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
    allowlist = load_allowlist(root)
    used: set[str] = set()
    results: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in CODE_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        if path.suffix == ".py":
            findings = scan_python(path, forbidden)
            findings.extend(scan_python_fragments(path, fragments))
        else:
            findings = scan_text(path, forbidden, fragments)
        for finding in findings:
            key = f"{relative}:{finding['symbol']}"
            if key in allowlist:
                used.add(key)
                continue
            results.append({"path": relative, **finding})
    stale = sorted(set(allowlist) - used)
    if stale:
        # Une exemption sans occurrence est une dette morte : le fichier a pu
        # être renommé ou nettoyé, et l'exemption couvrirait alors autre chose.
        results.extend({"path": key, "symbol": "STALE_ALLOWLIST_ENTRY", "line": 0} for key in stale)
    print(json.dumps({"ok": not results, "findings": results}, indent=2))
    return 0 if not results else 1


if __name__ == "__main__":
    sys.exit(main())
