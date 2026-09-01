#!/usr/bin/env python3
"""Inventaire en lecture seule du socle Vertex et de la cible canonique.

Ce script collecte des preuves structurelles et des candidats à examiner. Il ne
modifie rien et ne remplace ni l'exécution des tests, ni l'audit humain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

TARGET_PAGES = (
    "today",
    "markets",
    "opportunities",
    "analysis",
    "options",
    "simulator",
    "portfolio",
    "charts",
    "risks",
    "catalysts",
    "calendar",
    "sources-reports",
)

# Correspondances route historique -> destination cible, alignées sur
# `references/pages.md`, qui est le CONTRAT des douze pages (titre du document)
# et fait donc autorité sur ce script, simple heuristique d'inventaire.
#
# Deux entrées ont été corrigées le 2026-08-31 : elles contredisaient le
# contrat qu'elles étaient censées mesurer.
#   - `performance` pointait vers `charts`. Or Graphiques est « un espace
#     graphique configurable avec séries autorisées », pour explorer un
#     instrument ; Performance mesure le registre manuel. Le contrat range
#     l'« historique » du registre dans les widgets de Portefeuille (§7).
#   - `follow-up` pointait vers `risks`. Or Risques est « la matrice des
#     risques avec exposition, horizon, sévérité et preuve » ; la file de
#     revue de thèses répond à la question de Catalyseurs (§10) : « quels
#     événements vérifiés peuvent modifier LA THÈSE et quand ? »
LEGACY_PAGE_ALIASES = {
    "follow-up": "catalysts",
    "performance": "portfolio",
    "ai": "sources-reports",
    "system": "sources-reports",
}

REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "references/canonical-visual.md",
    "references/full-audit.md",
    "references/data-truth.md",
    "references/pages.md",
    "references/component-system.md",
    "references/charts.md",
    "references/visual-identity.md",
    "references/workflow.md",
    "assets/vertex-dashboard-canonical.png",
    "assets/pages-01-02-today-markets.png",
    "assets/pages-03-04-opportunities-analysis.png",
    "assets/pages-05-06-options-simulator.png",
    "assets/pages-07-08-portfolio-charts.png",
    "assets/pages-09-10-risks-catalysts.png",
    "assets/pages-11-12-calendar-sources-reports.png",
)

REQUIRED_GOVERNANCE = (
    "CLAUDE.md",
    "docs/00-foundation/CONSTITUTION.md",
    "docs/99-status/NOW.md",
    "docs/05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md",
)

CANONICAL_IMAGE_SHA256 = (
    "eb2eb0fc2105a98203e571381aec7765775d80aacec3513def10e99c9fdc7ace"
)

REQUIRED_COLOR_TOKENS = {
    "app",
    "surface-0",
    "surface-1",
    "surface-2",
    "surface-3",
    "grid-line",
    "silver",
    "titanium",
    "titanium-soft",
    "signal",
    "signal-bright",
    "signal-deep",
    "signal-soft",
    "signal-faint",
    "positive",
    "negative",
    "option",
    "macro",
    "scrim",
}

SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql"}
TEST_MARKERS = ("test_", ".test.", ".spec.")
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
}
TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?im)^\s*(?:export\s+)?(?:const\s+)?"
    r"([A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY))\s*="
)
FRONTEND_FINANCIAL_ASSIGNMENT = re.compile(
    r"(?im)\b(?:const|let|var)\s+"
    r"([A-Za-z_$][\w$]*(?:greek|iv|payoff|breakeven|drawdown|probability|score|risk)[\w$]*)\s*="
)


def parse_args() -> argparse.Namespace:
    inferred = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=inferred)
    parser.add_argument(
        "--strict-target",
        action="store_true",
        help="Retourne un échec si la cible visuelle ou les destinations manquent.",
    )
    return parser.parse_args()


def run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(  # noqa: S603 -- arguments are internal constants
            ("/usr/bin/git", *args),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def relative_locations(root: Path, pattern: re.Pattern[str], paths: list[Path]) -> list[str]:
    locations: list[str] = []
    for path in paths:
        text = read_text(path)
        for line_number, line in enumerate(text.splitlines(), 1):
            for match in pattern.finditer(line):
                name = match.group(1) if match.lastindex else match.group(0)
                locations.append(f"{path.relative_to(root)}:{line_number}:{name}")
    return locations


def parse_route_keys(app_shell: str) -> list[str]:
    mapping = re.search(
        r"LEDGER_CODE_BY_PAGE[^=]*=\s*\{(?P<body>.*?)\n\};",
        app_shell,
        re.DOTALL,
    )
    if mapping is None:
        return []
    return [
        raw_key or quoted_key
        for raw_key, quoted_key in re.findall(
            r"(?:'([^']+)'|([A-Za-z][\w-]*))\s*:\s*'[^']+'",
            mapping.group("body"),
        )
    ]


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    skill_root = root / ".claude/skills/vertex-titanium-ledger"
    errors: list[str] = []
    target_gaps: list[str] = []

    missing_governance = [name for name in REQUIRED_GOVERNANCE if not (root / name).is_file()]
    missing_skill = [name for name in REQUIRED_SKILL_FILES if not (skill_root / name).is_file()]
    if missing_governance:
        errors.extend(f"gouvernance absente: {name}" for name in missing_governance)
    if missing_skill:
        errors.extend(f"ressource du skill absente: {name}" for name in missing_skill)

    canonical_hash = sha256(skill_root / "assets/vertex-dashboard-canonical.png")
    if canonical_hash is not None and canonical_hash != CANONICAL_IMAGE_SHA256:
        errors.append("l'empreinte de la capture canonique a changé sans validation")

    all_files = [
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in EXCLUDED_DIRS for part in path.parts)
    ]
    source_files = [path for path in all_files if path.suffix.lower() in SOURCE_SUFFIXES]
    frontend_files = [
        path
        for path in source_files
        if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}
        and "apps/web" in path.as_posix()
    ]

    suffix_counts = Counter(path.suffix.lower() or "[sans extension]" for path in all_files)
    tests = [
        path
        for path in all_files
        if any(marker in path.name.lower() for marker in TEST_MARKERS)
    ]
    workflows = list((root / ".github/workflows").glob("*.y*ml"))

    tokens_source = read_text(root / "apps/web/src/design/tokens.ts")
    token_keys = set(re.findall(r"^\s*'([^']+)'\s*:", tokens_source, re.MULTILINE))
    missing_tokens = sorted(REQUIRED_COLOR_TOKENS - token_keys)
    if missing_tokens:
        target_gaps.append("tokens requis absents: " + ", ".join(missing_tokens))

    app_shell = read_text(root / "apps/web/src/shell/AppShell.tsx")
    current_pages = parse_route_keys(app_shell)
    normalized_pages = {LEGACY_PAGE_ALIASES.get(page, page) for page in current_pages}
    missing_pages = [page for page in TARGET_PAGES if page not in normalized_pages]
    legacy_pages = [page for page in current_pages if page in LEGACY_PAGE_ALIASES]
    if missing_pages:
        target_gaps.append(
            "destinations cibles sans équivalent détecté: " + ", ".join(missing_pages)
        )
    if legacy_pages:
        target_gaps.append("routes historiques à arbitrer: " + ", ".join(legacy_pages))

    nav_rail = read_text(root / "apps/web/src/shell/NavRail.tsx")
    if "VX" in nav_rail:
        target_gaps.append(
            "le rail contient encore le monogramme VX, refusé par la capture canonique"
        )

    todo_locations = relative_locations(root, TODO_PATTERN, source_files)
    sensitive_locations = relative_locations(root, SENSITIVE_ASSIGNMENT, source_files)
    formula_candidates = relative_locations(root, FRONTEND_FINANCIAL_ASSIGNMENT, frontend_files)

    tracked_env = []
    tracked = run_git(root, "ls-files")
    if tracked:
        tracked_env = sorted(
            name
            for name in tracked.splitlines()
            if Path(name).name.startswith(".env") and not name.endswith(".example")
        )
        if tracked_env:
            errors.append("fichier d'environnement suivi par Git: " + ", ".join(tracked_env))

    branch = run_git(root, "branch", "--show-current")
    head = run_git(root, "rev-parse", "--short=12", "HEAD")
    dirty = run_git(root, "status", "--short")

    return {
        "status": "FAIL" if errors else ("TARGET_GAPS" if target_gaps else "PASS"),
        "repo": str(root),
        "git": {
            "branch": branch,
            "head": head,
            "dirty": bool(dirty),
            "dirty_entries": 0 if not dirty else len(dirty.splitlines()),
        },
        "inventory": {
            "files": len(all_files),
            "source_files": len(source_files),
            "test_files": len(tests),
            "workflows": len(workflows),
            "top_suffixes": suffix_counts.most_common(12),
        },
        "canonical_target": {
            "skill_resources_present": len(REQUIRED_SKILL_FILES) - len(missing_skill),
            "skill_resources_expected": len(REQUIRED_SKILL_FILES),
            "canonical_image_sha256": canonical_hash,
            "current_page_keys": current_pages,
            "target_page_keys": list(TARGET_PAGES),
            "missing_target_pages": missing_pages,
            "legacy_pages_to_arbitrate": legacy_pages,
            "missing_color_tokens": missing_tokens,
        },
        "audit_seeds_not_confirmed_findings": {
            "todo_markers": todo_locations,
            "sensitive_assignment_names_only": sensitive_locations,
            "frontend_financial_assignment_candidates": formula_candidates,
            "tracked_environment_files": tracked_env,
        },
        "errors": errors,
        "target_gaps": target_gaps,
        "disclaimer": (
            "Les candidats exigent une revue humaine. Aucun secret ni valeur "
            "d'affectation n'est imprimé. Les tests applicatifs ne sont pas exécutés."
        ),
    }


def main() -> int:
    args = parse_args()
    result = audit(args.repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))  # noqa: T201
    if result["errors"]:
        return 1
    if args.strict_target and result["target_gaps"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
