#!/usr/bin/env python3
"""Fail when tracked code reaches forbidden IBKR account/order capabilities.

Source of truth: ``manifests/forbidden-capabilities.yaml`` (groups
``ibkr-orders`` and ``ibkr-account-portfolio``). The built-in sets below are a
superset fallback used only when the manifest or PyYAML is unavailable, so the
scanner never silently weakens when its input is missing (fail-closed).

The check reports only file, line and forbidden symbol. It deliberately avoids
printing source lines that might contain credentials or user data.

PORTÉE RÉELLE DE L'ANALYSE — à lire avant de s'y fier :
elle est STATIQUE et LITTÉRALE. Elle voit un symbole écrit tel quel dans le
source — appel, accès d'attribut, import, définition, liaison, mention en
chaîne, fragment de route — et les littéraux qu'elle peut replier sans exécuter
le programme. Elle ne voit PAS un nom assemblé à l'exécution.

Ce que la porte NE couvre PAS est énuméré dans ``OUT_OF_STATIC_REACH`` ; cette
liste fait partie de son contrat. Ne pas la décrire plus large qu'elle n'est :
les deux correctifs précédents ont échoué exactement là.
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
# le produit (plus de 400 occurrences, dont le module `vertex_api.portfolio`).
# Les signaler en tant que simple mention rendrait la porte illisible — donc
# inappliquée.
# Ils restent signalés en APPEL et en ACCÈS D'ATTRIBUT (`ib.positions`,
# `ib.portfolio()`), qui sont les formes réellement dangereuses, et dans les
# formats non-Python dès que la ligne nomme explicitement un courtier.
AMBIGUOUS_BARE_SYMBOLS = {
    "portfolio",
    "positions",
}
BROKER_CONTEXT = re.compile(r"iserver|ibkr|interactive\s*brokers|clientportal", re.IGNORECASE)

# Formats analysés. Le manifeste déclare
# `scope: [runtime, tests, dependencies, routes, permissions, ai_tools]` : les
# routes vivent aussi dans `openapi.json`, `wrangler.toml` et les scripts
# shell ; les permissions et les outils IA dans les manifestes YAML. Restreindre
# l'analyse à `.py`/`.ts` laissait le périmètre DÉCLARÉ plus large que le
# périmètre ANALYSÉ (8e audit) : `deploy.sh` appelant une route d'ordre par
# `curl` n'était vu par personne.
CODE_SUFFIXES = {
    # exécutables
    ".py", ".pyi", ".mako",
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
    ".sh", ".bash", ".zsh",
    ".html", ".pine",
    # déclaratifs : routes, permissions, dépendances, outils IA
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".csv", ".txt", ".example", ".npmrc", ".sql", ".env",
}
# Fichiers dont le NOM porte le sens : un point initial vide `Path.suffix`
# (`.npmrc` n'a pas d'extension), et `CODEOWNERS` n'en a jamais eu. Sans cette
# liste, un fichier de permissions ou de dépendances passait au travers alors
# que le manifeste déclare `dependencies` et `permissions` dans son `scope`.
CODE_FILENAMES = {".npmrc", ".env", "CODEOWNERS", "Procfile"}
CODE_FILENAME_PREFIXES = ("Dockerfile", "Makefile")

# Ne sont écartés que les répertoires GÉNÉRÉS ou VENDUS — jamais un nom qui
# peut désigner du code de production. `tests` et `tools` étaient écartés : un
# appel interdit y passait la porte la plus critique du programme (6e audit).
# `build` et `fixtures` l'étaient aussi À N'IMPORTE QUELLE PROFONDEUR, si bien
# que `apps/edge-ibkr/src/vertex_edge_ibkr/build/orders.py` et
# `apps/api/src/vertex_api/fixtures/accounts.py` étaient invisibles (7e audit).
# Ce qui nomme légitimement une capacité interdite passe par l'allowlist, qui
# est NOMMÉE et n'exempte que la mention.
SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", ".vite"}

ALLOWLIST_FILENAME = "financial-boundary-allowlist.yaml"

#: Ce que cette porte NE COUVRE PAS. Énuméré pour que personne ne la croie
#: exhaustive : les deux correctifs précédents ont échoué parce qu'ils
#: décrivaient une couverture plus large que la couverture réelle.
OUT_OF_STATIC_REACH = (
    "nom assemblé à l'exécution : getattr(ib, 'place' + suffixe), f-string à "
    "trou, str.join, base64, rot13, table de correspondance",
    "indirection par valeur : ib.__getattribute__(nom), __getattr__, "
    "operator.methodcaller(variable), setattr d'un alias",
    "import indirect : from module import * (le nom importé n'est pas écrit), "
    "importlib.import_module(variable), __import__(variable)",
    "réflexion inverse : parcours de dir(ib) ou de vars(ib) filtré à l'exécution",
    "répertoires écartés par SKIP_PARTS : code généré au build ou vendu "
    "(node_modules, dist, .vite) — s'il devient exécutable, il faut l'analyser",
    "classement textuel hors Python : sans arbre syntaxique, `call`, "
    "`attribute` et `import` sont déduits de la ligne ; un symbole cité dans un "
    "commentaire posé sur une ligne d'import est classé `import`, donc refusé "
    "d'exemption — la porte se trompe alors dans le sens strict, pas laxiste",
    "concaténation non littérale hors Python : `ib[\"place\" + suffixe]` n'est "
    "pas replié, seuls deux littéraux adjacents le sont",
    "documentation Markdown : le manifeste la classe `comment_or_documentation: "
    "review_required`, pas `deny` — elle passe par la revue humaine",
    "SVG, images et binaires : non analysés",
    "sémantique du receveur : la porte ne sait pas si `x.positions` porte sur un "
    "client IBKR ou sur le portefeuille manuel de Vertex ; hors Python elle exige "
    "un contexte courtier explicite sur la ligne pour les deux noms ambigus",
)


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


#: Formes d'accès qu'une exemption ne peut JAMAIS couvrir. Un APPEL, un ACCÈS
#: D'ATTRIBUT, un IMPORT et une DÉFINITION créent ou obtiennent le point
#: d'entrée. Restent exemptables la mention (`string`, `reference`), le
#: fragment de route et la liaison de nom (`binding`) — c'est le cas du test
#: qui prouve l'absence, du manifeste de politique et de cette porte.
#:
#: `import` a rejoint la liste au 8e audit : `from ib_insync.ib import
#: placeOrder as _send` n'était vu par RIEN — `scan_python` ne visitait pas les
#: nœuds `ast.alias`. Un renommage n'est pas une mention, c'est l'obtention de
#: la référence sous une autre étiquette.
#:
#: `definition` aussi : `def placeOrder(...)` ou `class reqPositions` fabrique
#: le point d'entrée interdit sous le toit de Vertex. Si le corps atteint IBKR
#: par un nom construit — hors de portée statique —, la définition est la SEULE
#: trace visible. Aucun motif ne la rend légitime : `financial-safety.md`
#: interdit d'ajouter la commande, pas seulement de l'appeler.
#:
#: `binding` reste exemptable : `executions = [...]` est un nom de variable,
#: pas un point d'entrée, et « executions » est aussi un mot anglais courant.
NEVER_EXEMPTABLE_KINDS = frozenset({"call", "attribute", "import", "definition"})


def _entry_symbols(entry: dict[str, object]) -> list[str]:
    """Symboles d'une entrée : ``symbol:`` scalaire ou ``symbols:`` en liste.

    La forme liste ne relâche RIEN : chaque symbole reste NOMMÉ, la forme
    d'accès reste contrôlée et une entrée sans occurrence reste signalée comme
    dette morte. Elle évite seulement de répéter cinquante fois le même motif —
    une allowlist illisible est une allowlist qu'on ne relit plus, et c'est
    ainsi que le 7e audit a trouvé une exemption qui couvrait autre chose que
    ce qu'elle disait. Il n'existe AUCUN joker : ``symbols: ["*"]`` n'exempte
    que le symbole littéral ``*``.
    """
    scalar = entry.get("symbol")
    listed = entry.get("symbols")
    if listed is not None and not isinstance(listed, list):
        raise SystemExit(
            f"manifests/{ALLOWLIST_FILENAME} : `symbols` doit être une liste "
            f"({entry.get('path')})"
        )
    symbols = [str(s) for s in (listed or []) if str(s).strip()]
    if scalar:
        symbols.insert(0, str(scalar))
    return symbols


def load_allowlist(root: Path) -> dict[str, str]:
    """Exemptions NOMMÉES : ``"<chemin>:<symbole>:<forme>" -> motif``.

    Une entrée porte ``symbol:`` (un symbole) ou ``symbols:`` (plusieurs,
    même chemin, même forme, même motif). Voir ``_entry_symbols``.

    La clé porte la FORME D'ACCÈS. Sans elle, l'exemption écrite « il les nomme
    en CHAÎNES uniquement — jamais en appel ni en accès d'attribut » n'était
    appliquée par RIEN : quatre capacités interdites réellement APPELÉES dans
    un fichier exempté franchissaient la porte (7e audit). Le motif était
    exact, seulement il n'était pas exécutable.

    Une entrée qui tente d'exempter un ``call``, un ``attribute`` ou un
    ``import`` est REFUSÉE au chargement : ce n'est pas une exemption
    discutable, c'est le chemin qu'on interdit.

    Fail-closed : un fichier d'exemptions illisible n'accorde AUCUNE exemption.
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
        symbols = _entry_symbols(entry)
        missing = [k for k in ("path", "kind", "reason") if not entry.get(k)]
        if not symbols:
            missing.append("symbol")
        if missing:
            raise SystemExit(
                f"manifests/{ALLOWLIST_FILENAME} : entrée incomplète, "
                f"champs manquants {sorted(missing)}"
            )
        kind = str(entry["kind"])
        if kind in NEVER_EXEMPTABLE_KINDS:
            raise SystemExit(
                f"manifests/{ALLOWLIST_FILENAME} : {entry['path']} tente d'exempter "
                f"un « {kind} » sur {symbols[0]} — un appel, un accès "
                "d'attribut et un import atteignent la capacité, ils ne sont "
                "jamais exemptables."
            )
        for symbol in symbols:
            allowed[f"{entry['path']}:{symbol}:{kind}"] = str(entry["reason"])
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


#: Profondeur maximale du repliement de littéraux. Une expression plus
#: profonde n'est plus « écrite telle quelle » ; elle relève de
#: ``OUT_OF_STATIC_REACH``.
_FOLD_DEPTH = 6
_FOLD_MAX_LEN = 512


def literal_strings(node: ast.AST, depth: int = 0) -> set[str]:
    """Chaînes que ce nœud vaut de façon STATIQUE et LITTÉRALE.

    Replie ce qu'un lecteur humain replie sans exécuter le programme :
    ``"place" + "Order"``, une f-string sans trou, un littéral d'octets. Une
    variable, un appel ou une f-string à trou rend l'ensemble vide — c'est une
    limite assumée, pas un oubli (``OUT_OF_STATIC_REACH``).
    """
    if depth > _FOLD_DEPTH:
        return set()
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return {node.value} if len(node.value) <= _FOLD_MAX_LEN else set()
        if isinstance(node.value, bytes) and len(node.value) <= _FOLD_MAX_LEN:
            try:
                return {node.value.decode("utf-8")}
            except UnicodeDecodeError:
                return set()
        return set()
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            resolved = literal_strings(value, depth + 1)
            if len(resolved) != 1:
                return set()  # un trou : plus rien n'est littéral
            parts.append(next(iter(resolved)))
        joined = "".join(parts)
        return {joined} if len(joined) <= _FOLD_MAX_LEN else set()
    if isinstance(node, ast.FormattedValue):
        return set()
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = literal_strings(node.left, depth + 1)
        right = literal_strings(node.right, depth + 1)
        return {
            a + b for a in left for b in right if len(a) + len(b) <= _FOLD_MAX_LEN
        }
    return set()


def _symbols_named_by(value: str, forbidden: set[str]) -> set[str]:
    """Symboles interdits qu'une chaîne littérale NOMME.

    La chaîne entière (``"placeOrder"``), ou un segment pointé
    (``"ib_insync.placeOrder"`` passé à ``importlib.import_module``). Les noms
    ambigus sont écartés : ce sont des clés de contenu de Vertex.
    """
    candidates = {value}
    if "." in value and len(value) <= _FOLD_MAX_LEN:
        candidates.update(value.split("."))
    return {c for c in candidates if c in forbidden and c not in AMBIGUOUS_BARE_SYMBOLS}


def scan_python(path: Path, forbidden: set[str]) -> list[dict[str, object]]:
    """Toute façon d'ATTEINDRE une capacité interdite, pas seulement l'appeler.

    Une capacité interdite ne doit pas être ATTEIGNABLE : obtenir la référence
    suffit à l'appeler ailleurs. Sont donc signalés, avec leur forme :

    ``call``       ``ib.placeOrder(...)``
    ``attribute``  ``send = ib.placeOrder`` — méthode liée, décorateur,
                   valeur par défaut, annotation, valeur de dictionnaire
    ``import``     ``from ib_insync.ib import placeOrder as _send`` — le
                   renommage est une obtention de référence ; les nœuds
                   ``ast.alias`` n'étaient visités par RIEN (8e audit)
    ``definition`` ``def placeOrder(...)``, ``class reqPositions`` — fabriquer
                   le point d'entrée interdit sous le toit de Vertex
    ``binding``    ``placeOrder = ...``, paramètre, ``global``, ``except … as``
                   — le nom est créé sans que la capacité soit atteinte
    ``string``     le nom écrit en LITTÉRAL, y compris replié
                   (``"place" + "Order"``, f-string sans trou, octets décodés)
                   et le segment pointé d'un chemin de module

    Ce que la forme ``string`` couvre : ``getattr(ib, "reqPositions")``,
    ``globals()["placeOrder"]``, ``attrgetter("whatIfOrder")``,
    ``importlib.import_module("m.placeOrder")`` — c'est-à-dire un nom
    LITTÉRAL. Elle ne couvre PAS un nom CONSTRUIT à l'exécution
    (``getattr(ib, "place" + suffixe)``) : voir ``OUT_OF_STATIC_REACH``.
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

    def record_import(line: int, name: str | None) -> None:
        """Chaque segment d'un chemin importé, et le nom d'arrivée."""
        if not name:
            return
        for part in name.split("."):
            if part in forbidden and part not in AMBIGUOUS_BARE_SYMBOLS:
                record(line, part, "import")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name in forbidden:
                record(node.lineno, name, "call")
        elif isinstance(node, ast.Attribute):
            if node.attr in forbidden:
                record(node.lineno, node.attr, "attribute")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in forbidden and node.name not in AMBIGUOUS_BARE_SYMBOLS:
                record(node.lineno, node.name, "definition")
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if node.id in forbidden and node.id not in AMBIGUOUS_BARE_SYMBOLS:
                record(node.lineno, node.id, "binding")
        elif isinstance(node, ast.arg):
            if node.arg in forbidden and node.arg not in AMBIGUOUS_BARE_SYMBOLS:
                record(node.lineno, node.arg, "binding")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            for name in node.names:
                if name in forbidden and name not in AMBIGUOUS_BARE_SYMBOLS:
                    record(node.lineno, name, "binding")
        elif isinstance(node, ast.ExceptHandler):
            if node.name in forbidden and node.name not in AMBIGUOUS_BARE_SYMBOLS:
                record(node.lineno, node.name, "binding")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                record_import(alias.lineno, alias.name)
                record_import(alias.lineno, alias.asname)
        elif isinstance(node, ast.ImportFrom):
            record_import(node.lineno, node.module)
            for alias in node.names:
                record_import(alias.lineno, alias.name)
                record_import(alias.lineno, alias.asname)
        elif isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp)):
            for value in literal_strings(node):
                for symbol in _symbols_named_by(value, forbidden):
                    record(node.lineno, symbol, "string")
    return findings


#: Contextes d'import JavaScript/TypeScript, reconnus littéralement.
IMPORT_CONTEXT = re.compile(
    r"(^\s*import\b)|(^\s*export\s+.*\bfrom\s+['\"])|(\brequire\s*\()"
    r"|(\bimport\s*\()|(\bfrom\s+['\"])"
)


#: Concaténation de deux littéraux adjacents — `"place" + "Order"`. L'analyseur
#: Python replie cette forme (``literal_strings``) ; sans cela l'analyseur
#: texte resterait plus faible que lui sur exactement le même découpage.
_TEXT_CONCAT = re.compile(
    r"(['\"`])([^'\"`\n]*)\1\s*\+\s*(['\"`])([^'\"`\n]*)\3"
)


def fold_text_literals(line: str, rounds: int = 4) -> str:
    """Replie les concaténations de littéraux adjacents d'une ligne.

    Statique et littéral uniquement : `"place" + suffixe` n'est pas replié,
    c'est un nom construit (``OUT_OF_STATIC_REACH``).
    """
    for _ in range(rounds):
        folded = _TEXT_CONCAT.sub(lambda m: f'"{m.group(2)}{m.group(4)}"', line)
        if folded == line:
            break
        line = folded
    return line


def _symbol_pattern(forbidden: set[str]) -> re.Pattern[str]:
    # `$` est un caractère d'identifiant en JavaScript : `\b` ne suffit pas.
    alternation = "|".join(map(re.escape, sorted(forbidden, key=len, reverse=True)))
    return re.compile(
        r"(?<![A-Za-z0-9_$])(" + alternation + r")(?![A-Za-z0-9_$])"
    )


def scan_text(
    path: Path, forbidden: set[str], fragments: set[str]
) -> list[dict[str, object]]:
    """Analyseur des formats non-Python, ALIGNÉ sur l'analyseur Python.

    Il n'avait qu'un motif ``symbole\\s*\\(`` : ``const f = ib.placeOrder;`` et
    ``ib["reqPositions"]`` échappaient alors que les MÊMES formes étaient vues
    en Python (8e audit). Chaque occurrence entière est désormais classée :

    ``call``       ``ib.placeOrder(...)``
    ``definition`` ``function placeOrder(...)``, ``class reqPositions``
    ``attribute``  ``ib.placeOrder``, ``ib?.placeOrder``, ``(await import(m)).x``
    ``import``     ``import { placeOrder as send } from …``, ``require(…)``
    ``reference``  toute autre mention littérale : indexation ``ib["x"]``,
                   destructuration ``const { x } = ib``, clé de manifeste,
                   commentaire
    ``fragment``   une route de courtier dans une URL

    Les concaténations de littéraux adjacents sont repliées avant classement
    (``fold_text_literals``), comme le fait l'analyseur Python.

    Faute d'arbre syntaxique, ce classement est TEXTUEL : il ne connaît pas le
    receveur. Les deux noms ambigus (``portfolio``, ``positions``), qui sont le
    vocabulaire du portefeuille MANUEL de Vertex, n'y sont donc retenus que si
    la ligne nomme explicitement un courtier.
    """
    findings: list[dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings
    pattern = _symbol_pattern(forbidden)
    seen: set[tuple[int, str]] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        broker = None
        for match in pattern.finditer(line):
            symbol = match.group(1)
            if symbol in AMBIGUOUS_BARE_SYMBOLS:
                if broker is None:
                    broker = bool(BROKER_CONTEXT.search(line))
                if not broker:
                    continue
            after = line[match.end():]
            before = line[: match.start()].rstrip()
            if re.search(r"\b(function|class|def)$", before):
                kind = "definition"
            elif after.lstrip().startswith("("):
                kind = "call"
            elif before.endswith("."):
                kind = "attribute"
            elif IMPORT_CONTEXT.search(line):
                kind = "import"
            else:
                kind = "reference"
            if (number, symbol) in seen:
                continue
            seen.add((number, symbol))
            findings.append({"line": number, "symbol": symbol, "kind": kind})
        folded = fold_text_literals(line)
        if folded != line:
            for match in pattern.finditer(folded):
                symbol = match.group(1)
                if symbol in AMBIGUOUS_BARE_SYMBOLS and not BROKER_CONTEXT.search(line):
                    continue
                if (number, symbol) in seen:
                    continue
                seen.add((number, symbol))
                findings.append(
                    {"line": number, "symbol": symbol, "kind": "reference"}
                )
        for fragment in fragments:
            if fragment in line:
                if fragment in AMBIGUOUS_FRAGMENTS and not BROKER_CONTEXT.search(line):
                    continue
                findings.append({"line": number, "symbol": fragment, "kind": "fragment"})
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
                findings.append({"line": number, "symbol": fragment, "kind": "fragment"})
    return findings


def is_scanned(path: Path) -> bool:
    """Un fichier suivi est analysé sauf s'il est de la documentation ou binaire.

    `.md` reste dehors : le manifeste classe lui-même
    ``comment_or_documentation: review_required``, pas ``deny``. Cette
    exclusion est une décision, pas un oubli — elle figure dans
    ``OUT_OF_STATIC_REACH``.
    """
    if path.suffix in CODE_SUFFIXES or path.name in CODE_FILENAMES:
        return True
    return path.name.startswith(CODE_FILENAME_PREFIXES)


def main() -> int:
    root = parse_args().root.resolve()
    forbidden, fragments = load_manifest(root)
    allowlist = load_allowlist(root)
    used: set[str] = set()
    results: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not is_scanned(path):
            continue
        relative = path.relative_to(root).as_posix()
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        if path.suffix in {".py", ".pyi"}:
            findings = scan_python(path, forbidden)
            findings.extend(scan_python_fragments(path, fragments))
        else:
            findings = scan_text(path, forbidden, fragments)
        for finding in findings:
            key = f"{relative}:{finding['symbol']}:{finding.get('kind', '?')}"
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
