#!/usr/bin/env python3
"""Audit déterministe du socle Titanium Ledger.

Le script vérifie uniquement des invariants structurels stables. Il ne prétend
pas valider la qualité visuelle des douze écrans.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED_LEDGER_CODES = {
    "today": "TL / 01",
    "opportunities": "TL / 02",
    "analysis": "TL / 03",
    "options": "TL / 04",
    "simulator": "TL / 05",
    "calendar": "TL / 06",
    "markets": "TL / 07",
    "portfolio": "TL / 08",
    "follow-up": "TL / 09",
    "performance": "TL / 10",
    "ai": "TL / 11",
    "system": "TL / 12",
}

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


def parse_args() -> argparse.Namespace:
    inferred = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=inferred)
    return parser.parse_args()


def read(root: Path, relative: str, errors: list[str]) -> str:
    path = root / relative
    if not path.is_file():
        errors.append(f"fichier requis absent: {relative}")
        return ""
    return path.read_text(encoding="utf-8")


def audit(root: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    tokens_source = read(root, "apps/web/src/design/tokens.ts", errors)
    app_shell = read(root, "apps/web/src/shell/AppShell.tsx", errors)
    visual_system = read(
        root, "docs/05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md", errors
    )
    nav_rail = read(root, "apps/web/src/shell/NavRail.tsx", errors)

    token_keys = set(re.findall(r"^\s*'([^']+)'\s*:", tokens_source, re.MULTILINE))
    missing_tokens = sorted(REQUIRED_COLOR_TOKENS - token_keys)
    if missing_tokens:
        errors.append("tokens Titanium manquants: " + ", ".join(missing_tokens))

    mapping_block = re.search(
        r"LEDGER_CODE_BY_PAGE[^=]*=\s*\{(?P<body>.*?)\n\};",
        app_shell,
        re.DOTALL,
    )
    actual_codes: dict[str, str] = {}
    if mapping_block is None:
        errors.append("mapping LEDGER_CODE_BY_PAGE introuvable")
    else:
        for raw_key, quoted_key, value in re.findall(
            r"(?:'([^']+)'|([A-Za-z][\w-]*))\s*:\s*'([^']+)'",
            mapping_block.group("body"),
        ):
            actual_codes[raw_key or quoted_key] = value

        for key, expected in EXPECTED_LEDGER_CODES.items():
            if actual_codes.get(key) != expected:
                errors.append(
                    f"code Ledger invalide pour {key}: "
                    f"{actual_codes.get(key)!r}, attendu {expected!r}"
                )

        page_codes = [actual_codes.get(key) for key in EXPECTED_LEDGER_CODES]
        if len(set(page_codes)) != len(EXPECTED_LEDGER_CODES):
            errors.append("les douze codes Ledger ne sont pas uniques")

    if "Titanium Ledger" not in visual_system:
        errors.append("la spécification visuelle ne nomme pas Titanium Ledger")
    if "VX" not in nav_rail or "Titanium Ledger" not in nav_rail:
        errors.append("le rail ne porte pas le monogramme VX et la signature Titanium Ledger")

    if len(actual_codes) > len(EXPECTED_LEDGER_CODES) + 1:
        warnings.append("le mapping contient des routes additionnelles; vérifier leur statut")

    return {
        "status": "PASS" if not errors else "FAIL",
        "repo": str(root.resolve()),
        "checks": {
            "required_tokens": len(REQUIRED_COLOR_TOKENS),
            "ledger_pages": len(EXPECTED_LEDGER_CODES),
            "visual_spec": bool(visual_system),
            "brand_in_nav": "VX" in nav_rail and "Titanium Ledger" in nav_rail,
        },
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    args = parse_args()
    result = audit(args.repo_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))  # noqa: T201
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
