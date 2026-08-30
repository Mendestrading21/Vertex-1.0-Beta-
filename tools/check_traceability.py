#!/usr/bin/env python3
"""Guard: every absolute prohibition is mapped to a proof, or to a written gap.

The repository states thirty absolute prohibitions — ten under
``CLAUDE.md § Interdictions absolues`` and twenty in
``.claude/rules/financial-safety.md``. Nothing checked that any of them was
actually proven by a test. A rule nobody can point a test at is a rule that
only exists in prose.

``manifests/traceability.yaml`` maps each prohibition to the tests that prove
it. This gate keeps that map honest in both directions:

1. ``invariant_not_declared`` — a prohibition in the source documents has no
   entry. New rules cannot arrive unnoticed.
2. ``invariant_no_longer_exists`` — an entry no longer matches any
   prohibition. Because entries are keyed by a digest of the rule TEXT, editing
   a rule fires both codes at once: the map must be re-read against the new
   wording, not silently carried over.
3. ``proof_missing`` — an entry claims ``PROVEN`` with no proof.
4. ``proof_file_absent`` / ``proof_test_absent`` / ``proof_not_anchored`` — a
   cited test file does not exist, the named test does not exist, or the
   citation names no test at all. A citation that resolves to nothing is worse
   than no citation: it looks like coverage. Anchoring is REQUIRED because a
   whole-file citation survives emptying the file.
5. ``gap_without_exception`` — a ``NOT_YET_PROVEN`` entry lacks ``owner``,
   ``reason``, ``expires_at`` or ``closure_criterion``.
6. ``expired_exception`` — such an entry's deadline has passed.
7. ``unprovable_without_argument`` — a ``NOT_PROVABLE_BY_TEST`` entry lacks a
   written argument. Declaring a rule untestable must cost a paragraph.
8. ``unknown_status`` — a third status was invented.
9. ``text_diverges_from_rule`` — the entry's ``text`` is not the rule it claims
   to map. It is a copy for the reader's benefit and was never checked against
   the source: 14 of the 30 entries diverged, one of them stating a NARROWER
   prohibition than the document does.

Entries that are not ``PROVEN`` are PRINTED on every run, whether or not the
gate fails. A gap that stops being visible stops being a gap and becomes an
omission.

Output: JSON ``{"ok": bool, "findings": [...], "gaps": [...]}`` on stdout.
Read-only: this tool never writes to the repository.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

MANIFEST_RELATIVE = Path("manifests/traceability.yaml")

#: Documents scanned, and the heading under which prohibitions live. ``None``
#: means the whole document is a list of prohibitions.
SOURCES: tuple[tuple[str, str | None], ...] = (
    ("CLAUDE.md", "Interdictions absolues"),
    (".claude/rules/financial-safety.md", None),
)

EXCEPTION_FIELDS = ("owner", "reason", "expires_at", "closure_criterion")

#: Test-name detection for non-Python proofs. Playwright and Vitest both name
#: tests with a string literal as the first argument.
_TS_TEST = re.compile(r"""\b(?:test|it)\s*\(\s*(['"`])(?P<name>.*?)\1""", re.DOTALL)


class DocumentError(RuntimeError):
    """A required document is absent or unusable."""


def _paragraph_bullets(text: str, section: str | None) -> list[str]:
    """Top-level bullets of a document, joined across continuation lines.

    A bullet wrapped over several lines is ONE rule; splitting on newlines
    would produce digests that change with reflowing and rules that look new
    after a purely cosmetic edit.
    """
    bullets: list[str] = []
    current: list[str] = []
    inside = section is None
    for line in text.splitlines():
        if line.startswith("#"):
            if section is not None:
                inside = section in line
            if current:
                bullets.append(" ".join(current))
                current = []
            continue
        if not inside:
            continue
        if line.startswith("- "):
            if current:
                bullets.append(" ".join(current))
            current = [line[2:].strip()]
        elif current and line.startswith("  ") and line.strip():
            current.append(line.strip())
        elif current and not line.strip():
            bullets.append(" ".join(current))
            current = []
    if current:
        bullets.append(" ".join(current))
    return bullets


def digest(text: str) -> str:
    """Stable key for one prohibition: a digest of its exact wording."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def collect_prohibitions(root: Path) -> dict[str, tuple[str, str]]:
    """``digest -> (source document, rule text)`` for every prohibition."""
    found: dict[str, tuple[str, str]] = {}
    for relative, section in SOURCES:
        path = root / relative
        if not path.is_file():
            raise DocumentError(f"{relative} is absent; prohibitions cannot be enumerated")
        bullets = _paragraph_bullets(path.read_text(encoding="utf-8"), section)
        if not bullets:
            raise DocumentError(
                f"{relative} yielded no prohibition"
                + (f" under « {section} »" if section else "")
                + " — the gate would have nothing to enforce"
            )
        for bullet in bullets:
            found[digest(bullet)] = (relative, bullet)
    return found


def _python_test_names(path: Path) -> set[str]:
    """Names of the TESTS defined in a Python file, methods included.

    Helpers, fixtures and classes are deliberately EXCLUDED. They used to be
    collected too, and combined with the substring match below that made
    ``fichier.py::t`` resolve against any helper containing a ``t``. A citation
    must name a test, not a name that happens to appear in the file.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            names.add(node.name)
    return names


def _other_test_names(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {match.group("name") for match in _TS_TEST.finditer(text)}


def _proof_resolves(root: Path, proof: str) -> str | None:
    """``None`` when the proof resolves, otherwise a finding code.

    Two rules, both written after an audit measured what the previous version
    accepted.

    ANCHORING. A citation must name a test: ``chemin::nom``. A whole-file
    citation used to be accepted on the strength of ``path.is_file()`` alone —
    58 of the 67 citations were of that shape, and ``README.md`` cited as proof
    of « never send an IBKR order » passed. A file is not a proof: it can be
    emptied, its tests renamed, its subject changed, and the map would still
    look green.

    EXACT MATCH. The name used to be matched by SUBSTRING against every
    function AND class in the file, helpers included: ``::t`` resolved. A
    Playwright title is a sentence, so a TypeScript citation is compared to the
    FULL title; a parametrised Python test keeps its bare function name, which
    is what ``ast`` reports.
    """
    relative, _, test_name = proof.partition("::")
    path = root / relative
    if not path.is_file():
        return "proof_file_absent"
    if not test_name:
        return "proof_not_anchored"
    names = _python_test_names(path) if path.suffix == ".py" else _other_test_names(path)
    if test_name in names:
        return None
    return "proof_test_absent"


def _parse_date(value: Any) -> dt.date | None:
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def check(root: Path, today: dt.date) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    manifest_path = root / MANIFEST_RELATIVE
    if not manifest_path.is_file():
        raise DocumentError(f"{MANIFEST_RELATIVE} is absent")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise DocumentError(f"{MANIFEST_RELATIVE} is not a mapping")
    entries = manifest.get("invariants")
    if not isinstance(entries, list) or not entries:
        raise DocumentError(
            f"{MANIFEST_RELATIVE} declares no invariant; the gate must not pass by emptiness"
        )

    prohibitions = collect_prohibitions(root)
    declared: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or "digest" not in entry:
            raise DocumentError("a `invariants` entry has no digest")
        declared[str(entry["digest"])] = entry

    for key, (source, text) in sorted(prohibitions.items()):
        if key not in declared:
            findings.append(
                {
                    "code": "invariant_not_declared",
                    "detail": "this prohibition is mapped to no proof and no written gap",
                    "digest": key,
                    "source": source,
                    "text": text[:160],
                }
            )

    for key, entry in sorted(declared.items()):
        if key not in prohibitions:
            findings.append(
                {
                    "code": "invariant_no_longer_exists",
                    "detail": "no prohibition matches this entry; the rule was edited or removed, "
                    "and the mapping must be re-read against its new wording",
                    "digest": key,
                    "id": entry.get("id"),
                }
            )
            continue

        status = entry.get("status")
        identity = {"digest": key, "id": entry.get("id")}

        # The `text` field is a COPY of the rule, and it was never confronted to
        # the rule: an audit found 14 of the 30 entries diverging, among them
        # one that stated a NARROWER prohibition than the document does. A
        # reader trusting the matrix would have believed the narrower one. The
        # digest keys the entry, so a real edit to the rule fires
        # `invariant_no_longer_exists`; this check catches the other direction —
        # the copy drifting on its own.
        declared_text = " ".join(str(entry.get("text", "")).split())
        actual_text = " ".join(prohibitions[key][1].split())
        if declared_text != actual_text:
            findings.append(
                {
                    **identity,
                    "code": "text_diverges_from_rule",
                    "detail": (
                        "the entry restates the rule differently from the "
                        "source document; a paraphrase is not the rule"
                    ),
                    "declared": declared_text,
                    "actual": actual_text,
                }
            )

        if status == "PROVEN":
            proofs = entry.get("proofs")
            proofs = proofs if isinstance(proofs, list) else []
            if not proofs:
                findings.append(
                    {**identity, "code": "proof_missing", "detail": "PROVEN with no proof cited"}
                )
                continue
            for proof in proofs:
                code = _proof_resolves(root, str(proof))
                if code is not None:
                    findings.append(
                        {
                            **identity,
                            "code": code,
                            "detail": "a citation that resolves to nothing looks like coverage",
                            "proof": proof,
                        }
                    )
            continue

        if status == "NOT_YET_PROVEN":
            missing = [field for field in EXCEPTION_FIELDS if not entry.get(field)]
            if missing:
                findings.append(
                    {
                        **identity,
                        "code": "gap_without_exception",
                        "detail": "an unproven prohibition must be owned, explained and dated",
                        "missing_fields": missing,
                    }
                )
            else:
                expires = _parse_date(entry.get("expires_at"))
                if expires is None:
                    findings.append(
                        {
                            **identity,
                            "code": "gap_without_exception",
                            "detail": "`expires_at` is not an ISO date",
                        }
                    )
                elif expires < today:
                    findings.append(
                        {
                            **identity,
                            "code": "expired_exception",
                            "detail": "the deadline was written so the gap "
                            "could not become permanent",
                            "expires_at": expires.isoformat(),
                        }
                    )
            gaps.append({**identity, "status": status, "reason": entry.get("reason")})
            continue

        if status == "NOT_PROVABLE_BY_TEST":
            if not entry.get("owner") or not entry.get("reason"):
                findings.append(
                    {
                        **identity,
                        "code": "unprovable_without_argument",
                        "detail": "declaring a prohibition untestable must cost a written argument",
                    }
                )
            gaps.append({**identity, "status": status, "reason": entry.get("reason")})
            continue

        findings.append(
            {
                **identity,
                "code": "unknown_status",
                "detail": "only PROVEN, NOT_YET_PROVEN and NOT_PROVABLE_BY_TEST exist",
                "status": status,
            }
        )

    proven = sum(1 for e in declared.values() if e.get("status") == "PROVEN")
    return {
        "ok": not findings,
        "findings": findings,
        "gaps": gaps,
        "prohibitions_found": len(prohibitions),
        "declared": len(declared),
        "proven": proven,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Vertex One repository root",
    )
    args = parser.parse_args(argv)
    try:
        # `dt.date.today()` reads the LOCAL clock: the day used to judge a
        # deadline would then depend on the machine's timezone, and the same
        # commit could pass in one place and fail in another. UTC, like every
        # other instant in this repository.
        report = check(args.root.resolve(), dt.datetime.now(dt.UTC).date())
    except DocumentError as exc:
        print(json.dumps({"ok": False, "findings": [{"code": "unusable", "detail": str(exc)}]}))
        return 1

    # Les écarts sont imprimés à CHAQUE exécution, même quand la porte passe :
    # un manque qui cesse d'être visible cesse d'être un manque.
    for gap in report["gaps"]:
        print(f"[{gap['status']}] {gap['id']} : {gap['reason']}", file=sys.stderr)
    for finding in report["findings"]:
        print(f"[{finding['code']}] {finding.get('id') or finding.get('digest')}", file=sys.stderr)
    print(
        f"PORTE traceability : {'OK' if report['ok'] else 'ÉCHEC'} — "
        f"{report['proven']}/{report['prohibitions_found']} interdictions prouvées, "
        f"{len(report['gaps'])} écart(s) déclaré(s)."
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
