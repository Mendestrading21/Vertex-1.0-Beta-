#!/usr/bin/env python3
"""Porte de détection de secrets — locale, déterministe, sans réseau.

Échoue (code 1) si un fichier suivi par Git contient un secret vraisemblable :
clé privée, jeton de fournisseur, JWT, DSN portant un mot de passe non déclaré,
ou affectation d'une valeur à forte entropie à un identifiant de secret.

Principe fail-closed : une catégorie que ce script ne sait pas décider est
signalée, jamais ignorée silencieusement. Les seules exemptions possibles sont
littérales et déclarées dans ``manifests/secret-allowlist.yaml`` avec un motif
écrit ; aucune exemption par expression régulière, par répertoire ou par
extension n'est acceptée.

Ce script ne remplace pas un scanner d'historique : il inspecte l'arbre de
travail suivi, pas les commits antérieurs (voir docs/99-status/DEBT.md).
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, NamedTuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = REPO_ROOT / "manifests" / "secret-allowlist.yaml"

# Extensions binaires : lues en octets, jamais décodées ni citées.
BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".ttf", ".otf", ".ico", ".pdf"}
)

MAX_BYTES = 2_000_000


class Rule(NamedTuple):
    code: str
    label: str
    pattern: re.Pattern[str]


RULES: tuple[Rule, ...] = (
    Rule(
        "PRIVATE_KEY",
        "clé privée en clair",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ),
    Rule("GITHUB_TOKEN", "jeton GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    Rule("SLACK_TOKEN", "jeton Slack", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    Rule("AWS_ACCESS_KEY", "clé d'accès AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    Rule("GOOGLE_API_KEY", "clé API Google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    Rule("STRIPE_KEY", "clé Stripe", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{16,}\b")),
    Rule(
        "ANTHROPIC_KEY",
        "clé de fournisseur d'IA",
        re.compile(r"\b(?:sk-ant-|sk-proj-|sk-)[A-Za-z0-9_-]{24,}\b"),
    ),
    Rule(
        "JWT",
        "jeton JWT signé",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    Rule(
        "DSN_PASSWORD",
        "mot de passe dans une URL de connexion",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[A-Za-z0-9._%-]+:([^@\s/'\"]{4,})@"),
    ),
)

# Identifiants qui, affectés à une valeur à forte entropie, dénoncent un secret.
ASSIGNMENT = re.compile(
    r"""(?ix)
    \b(?P<name>[A-Za-z0-9_.-]*
        (?:secret|token|password|passwd|passphrase|api[_-]?key|private[_-]?key|
           credential|client[_-]?secret|access[_-]?key|auth[_-]?key)
     [A-Za-z0-9_.-]*)
    \s*[:=]\s*
    (?P<quote>["'])(?P<value>[^"'\n]{16,200})(?P=quote)
    """
)

# Une valeur d'affectation qui est manifestement une référence, un exemple ou
# un gabarit n'est pas un secret : elle ne contient aucune donnée.
PLACEHOLDER = re.compile(
    r"""(?ix)
    ^(?:
        \$\{?[A-Za-z0-9_]+\}?           # ${VAR} / $VAR
      | \{\{.*\}\}                      # {{ ... }} (gabarit)
      | \{[A-Za-z0-9_]+\}               # {var} (format Python)
      | <[^>]+>                         # <à remplacer>
      | os\.environ.*
      | process\.env.*
      | .*\b(?:example|exemple|placeholder|change[_-]?me|redacted|fictif|dummy|
              fake|sample|synthetic|xxx+|todo|à-définir|a-definir)\b.*
    )$
    """
)

MIN_ENTROPY_BITS = 3.6


def shannon_bits_per_char(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    total = len(value)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def load_allowlist() -> dict[str, str]:
    """Exemptions littérales : ``"<chemin>:<code>:<extrait exact>" -> motif``."""
    if not ALLOWLIST_PATH.is_file():
        return {}
    raw = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8")) or {}
    entries = raw.get("allow") or []
    allowed: dict[str, str] = {}
    for entry in entries:
        missing = [k for k in ("path", "code", "match", "reason") if not entry.get(k)]
        if missing:
            raise SystemExit(
                f"manifests/secret-allowlist.yaml : entrée incomplète, champs manquants {missing}"
            )
        allowed[f"{entry['path']}:{entry['code']}:{entry['match']}"] = str(entry["reason"])
    return allowed


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    ).stdout
    return [REPO_ROOT / name for name in out.decode("utf-8").split("\0") if name]


class Finding(NamedTuple):
    path: str
    line: int
    code: str
    label: str
    match: str

    def key(self) -> str:
        return f"{self.path}:{self.code}:{self.match}"

    def render(self) -> str:
        # L'extrait n'est JAMAIS affiché : seul son empreinte tronquée l'est,
        # afin qu'un journal de CI ne publie pas le secret qu'il dénonce.
        import hashlib

        digest = hashlib.sha256(self.match.encode("utf-8")).hexdigest()[:12]
        return f"{self.path}:{self.line}: {self.code} ({self.label}) — empreinte {digest}"


def scan_text(path: str, text: str) -> Iterable[Finding]:
    for number, line in enumerate(text.splitlines(), start=1):
        if len(line) > 4000:
            line = line[:4000]
        for rule in RULES:
            for found in rule.pattern.finditer(line):
                captured = found.group(1) if found.groups() else found.group(0)
                if found.groups() and PLACEHOLDER.match(captured.strip()):
                    # Valeur capturée manifestement fictive (``CHANGE_ME``,
                    # ``${VAR}``…) : la forme du secret est là, la donnée non.
                    continue
                yield Finding(path, number, rule.code, rule.label, captured)
        for found in ASSIGNMENT.finditer(line):
            value = found.group("value")
            if PLACEHOLDER.match(value.strip()):
                continue
            if shannon_bits_per_char(value) < MIN_ENTROPY_BITS:
                continue
            yield Finding(
                path,
                number,
                "HIGH_ENTROPY_ASSIGNMENT",
                f"valeur à forte entropie affectée à « {found.group('name')} »",
                value,
            )


def main() -> int:
    allowlist = load_allowlist()
    used: set[str] = set()
    findings: list[Finding] = []

    for absolute in tracked_files():
        if not absolute.is_file():
            continue
        relative = absolute.relative_to(REPO_ROOT).as_posix()
        if absolute.suffix.lower() in BINARY_SUFFIXES:
            continue
        if absolute.stat().st_size > MAX_BYTES:
            continue
        try:
            text = absolute.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # non textuel : aucune règle n'est applicable
        for finding in scan_text(relative, text):
            if finding.key() in allowlist:
                used.add(finding.key())
                continue
            findings.append(finding)

    stale = sorted(set(allowlist) - used)
    if stale:
        print("Exemptions inutilisées dans manifests/secret-allowlist.yaml :", file=sys.stderr)
        for key in stale:
            print(f"  - {key}", file=sys.stderr)
        print(
            "Une exemption sans occurrence est une dette morte : la supprimer.",
            file=sys.stderr,
        )
        return 1

    if findings:
        print("SECRETS VRAISEMBLABLES DÉTECTÉS :", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding.render()}", file=sys.stderr)
        print(
            "\nAucune valeur n'est reproduite ici. Vérifier, RÉVOQUER si réel,"
            " puis purger l'historique avant toute publication.",
            file=sys.stderr,
        )
        return 1

    print(f"Aucun secret détecté ({len(tracked_files())} fichiers suivis).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
