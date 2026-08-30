#!/usr/bin/env python3
"""Volet `notices` de la porte `release` de docs/06-quality/CI_GATES.md.

« SBOM, provenance, signature, notices ; bloque si preuve absente. »

Ce script couvre UNIQUEMENT les **notices**. La SBOM est produite par le job
`supply-chain`. Ce qui reste — provenance et signature — est traité dans
`docs/99-status/DEBT.md` : ce dépôt ne publie aucun artefact et n'a pas de
démon de conteneur, donc rien de vérifiable n'est produit ici. Aucune porte
verte n'est simulée pour cela.

Ce que la porte vérifie, hors ligne
-----------------------------------
1. INVENTAIRE — tout composant tiers présent dans `uv.lock` ou
   `apps/web/pnpm-lock.yaml` a une entrée dans `manifests/licenses.yaml`, à la
   même version. Une entrée du registre absente des verrous échoue aussi
   (registre fantôme).
2. LICENCE — chaque entrée porte une expression SPDX non vide, dont chaque
   identifiant figure dans `licenses.allowed_spdx` de `manifests/policy.yaml`.
   `UNKNOWN`, `NOASSERTION`, une licence vide, une licence de
   `licenses.denied_spdx` ou une licence qu'aucune liste ne classe BLOQUENT
   (.claude/rules/security.md : « Toute licence inconnue […] bloque la
   fusion »). `licenses.acknowledged_spdx` recense les licences non
   permissives reconnues AVEC un motif écrit : elles sont signalées à chaque
   exécution et ne bloquent pas ; sans motif, elles bloquent.
3. FRAÎCHEUR — le tableau généré de `THIRD_PARTY_NOTICES.md`, entre ses
   marqueurs, est identique au rendu du registre. Un verrou modifié sans
   régénération des notices échoue.

Régénération (réseau requis)
----------------------------
    python3 tools/check_notices.py --refresh

`--refresh` relit les verrous, interroge les registres officiels
(`https://pypi.org/pypi/<nom>/<version>/json` et
`https://registry.npmjs.org/<nom>/<version>`), réécrit
`manifests/licenses.yaml` puis le tableau de `THIRD_PARTY_NOTICES.md`. Les
licences ne sont donc jamais devinées : elles viennent des métadonnées publiées
par les distributeurs eux-mêmes.

CE QUE CETTE PORTE NE PROUVE PAS
--------------------------------
- Elle croit la métadonnée du registre. Un paquet qui déclare `MIT` alors que
  son code est sous une autre licence n'est pas détecté : aucun fichier
  `LICENSE` n'est lu, aucun audit juridique n'est fait.
- `role: runtime` / `development` est dérivé du graphe des verrous, pas d'une
  observation de ce qui est réellement embarqué dans un artefact — ce dépôt n'en
  produit aucun.
- Elle ne vérifie pas la présence physique des textes de licence ni des
  fichiers `NOTICE` exigés par Apache-2.0 : ces obligations restent des
  exigences rédigées dans `THIRD_PARTY_NOTICES.md`.
- Elle ne dit rien de la compatibilité des licences entre elles.
"""

from __future__ import annotations

import argparse
import email
import io
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

BLOCK_START = "<!-- COMPOSANTS-DEBUT (genere par tools/check_notices.py --refresh) -->"
BLOCK_END = "<!-- COMPOSANTS-FIN -->"

UNKNOWN_LICENSES = {"", "unknown", "noassertion", "none", "null", "see license file"}

# Correspondance classificateur Trove -> identifiant SPDX. Utilisée seulement
# quand le paquet ne publie ni `license_expression` ni `license` exploitable.
_TROVE_TO_SPDX = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: BSD License": "BSD-3-Clause",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "License :: OSI Approved :: GNU Affero General Public License v3": "AGPL-3.0-only",
    "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
}

# Textes de licence non SPDX rencontrés dans les métadonnées, normalisés vers
# l'identifiant SPDX correspondant. Chaque ligne est une lecture de la
# métadonnée publiée, pas une supposition.
_LICENSE_ALIASES = {
    "mit license": "MIT",
    "the mit license": "MIT",
    "mit": "MIT",
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "bsd-3-clause license": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "modified bsd license": "BSD-3-Clause",
    "3-clause bsd license": "BSD-3-Clause",
    "2-clause bsd license": "BSD-2-Clause",
    "apache 2.0": "Apache-2.0",
    "apache-2.0 license": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "isc license": "ISC",
    "apache license, version 2.0": "Apache-2.0",
    "apache license version 2.0": "Apache-2.0",
    "sil open font license": "OFL-1.1",
    "sil open font license 1.1": "OFL-1.1",
    "the sil open font license": "OFL-1.1",
    "python software foundation license": "PSF-2.0",
    "mpl-2.0": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
}

_SPDX_SPLIT = re.compile(r"\s+(?:AND|OR|WITH)\s+", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    code: str
    where: str
    message: str

    def render(self) -> str:
        return f"[{self.code}] {self.where} : {self.message}"


@dataclass(frozen=True)
class Component:
    ecosystem: str
    name: str
    version: str
    role: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.ecosystem, self.name, self.version)


# ── Inventaire depuis les verrous ───────────────────────────────────────────


def python_components(root: Path, first_party: set[str]) -> list[Component]:
    """Composants Python tiers de `uv.lock`, avec leur rôle dérivé du graphe."""
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = lock.get("package") or []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for entry in packages:
        by_name.setdefault(str(entry["name"]).lower(), []).append(entry)

    runtime_names: set[str] = set()
    frontier = []
    for entry in packages:
        if str(entry["name"]).lower() in first_party:
            frontier += [str(d["name"]).lower() for d in entry.get("dependencies") or []]
    while frontier:
        name = frontier.pop()
        if name in runtime_names or name in first_party:
            continue
        runtime_names.add(name)
        for candidate in by_name.get(name, []):
            frontier += [str(d["name"]).lower() for d in candidate.get("dependencies") or []]

    components: list[Component] = []
    for entry in packages:
        name = str(entry["name"]).lower()
        if name in first_party or "registry" not in (entry.get("source") or {}):
            continue
        components.append(
            Component(
                "python",
                name,
                str(entry["version"]),
                "runtime" if name in runtime_names else "development",
            )
        )
    return components


def _strip_peers(reference: str) -> str:
    depth = 0
    out = []
    for char in reference:
        if char == "(":
            depth += 1
            continue
        if char == ")":
            depth -= 1
            continue
        if depth == 0:
            out.append(char)
    return "".join(out)


def javascript_components(root: Path) -> list[Component]:
    """Composants npm de `apps/web/pnpm-lock.yaml`, rôle dérivé du graphe."""
    lock_path = root / "apps" / "web" / "pnpm-lock.yaml"
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {}
    snapshots = lock.get("snapshots") or {}
    packages = lock.get("packages") or {}

    snapshot_by_package: dict[str, list[str]] = {}
    for snapshot_key in snapshots:
        snapshot_by_package.setdefault(_strip_peers(snapshot_key), []).append(snapshot_key)

    importer = (lock.get("importers") or {}).get(".") or {}
    frontier: list[str] = []
    for name, value in (importer.get("dependencies") or {}).items():
        frontier.append(f"{name}@{_strip_peers(str((value or {}).get('version', '')))}")

    runtime: set[str] = set()
    while frontier:
        package_key = frontier.pop()
        if package_key in runtime:
            continue
        runtime.add(package_key)
        for snapshot_key in snapshot_by_package.get(package_key, []):
            snapshot = snapshots.get(snapshot_key) or {}
            for section in ("dependencies", "optionalDependencies"):
                for dep_name, dep_ref in (snapshot.get(section) or {}).items():
                    frontier.append(f"{dep_name}@{_strip_peers(str(dep_ref))}")

    components: list[Component] = []
    for package_key in packages:
        name, _, version = package_key.rpartition("@")
        components.append(
            Component(
                "javascript",
                name,
                version,
                "runtime" if package_key in runtime else "development",
            )
        )
    return components


def inventory(root: Path, policy: dict[str, Any]) -> list[Component]:
    first_party = {
        str(x).lower() for x in (policy["dependencies"].get("first_party_python") or [])
    }
    components = python_components(root, first_party) + javascript_components(root)
    return sorted(components, key=lambda c: (c.ecosystem, c.name, c.version))


# ── Registre des licences ───────────────────────────────────────────────────


def load_registry(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    path = root / "manifests" / "licenses.yaml"
    if not path.is_file():
        raise SystemExit(
            f"ERREUR: registre de licences absent : {path} — porte notices NON EXÉCUTÉE."
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    registry: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in data.get("components") or []:
        key = (str(entry["ecosystem"]), str(entry["name"]), str(entry["version"]))
        registry[key] = entry
    return registry


def normalize_license(raw: str | None, classifiers: list[str] | None = None) -> str:
    value = (raw or "").strip()
    if value.lower() in UNKNOWN_LICENSES or len(value) > 120:
        value = ""
    if not value and classifiers:
        found = [_TROVE_TO_SPDX[c] for c in classifiers if c in _TROVE_TO_SPDX]
        if found:
            value = found[0]
    alias = _LICENSE_ALIASES.get(value.lower())
    return alias or value or "UNKNOWN"


def spdx_identifiers(expression: str) -> list[str]:
    tokens = _SPDX_SPLIT.split(expression)
    return [token.strip().strip("()").strip() for token in tokens if token.strip()]


def check_licenses(
    components: list[Component],
    registry: dict[tuple[str, str, str], dict[str, Any]],
    policy: dict[str, Any],
) -> list[Finding]:
    allowed = {str(x) for x in (policy["licenses"].get("allowed_spdx") or [])}
    denied = {str(x) for x in (policy["licenses"].get("denied_spdx") or [])}
    acknowledged: dict[str, str] = {}
    findings: list[Finding] = []
    for item in policy["licenses"].get("acknowledged_spdx") or []:
        identifier = str(item.get("id") or "")
        reason = str(item.get("reason") or "").strip()
        if not reason:
            findings.append(
                Finding(
                    "LICENSE_ACK_WITHOUT_REASON",
                    "manifests/policy.yaml",
                    f"`{identifier}` reconnu sans motif écrit — reconnaissance silencieuse "
                    "interdite",
                )
            )
            continue
        acknowledged[identifier] = reason
    seen: set[tuple[str, str, str]] = set()

    for component in components:
        entry = registry.get(component.key)
        where = f"{component.ecosystem}:{component.name}@{component.version}"
        if entry is None:
            findings.append(
                Finding(
                    "NOTICE_MISSING_COMPONENT",
                    where,
                    "présent dans le verrou, absent de manifests/licenses.yaml — "
                    "licence inconnue, donc bloquant",
                )
            )
            continue
        seen.add(component.key)
        expression = str(entry.get("license") or "").strip()
        if not expression or expression.lower() in UNKNOWN_LICENSES:
            findings.append(
                Finding("LICENSE_UNKNOWN", where, "licence absente ou `UNKNOWN` dans le registre")
            )
            continue
        for identifier in spdx_identifiers(expression):
            if identifier in denied:
                findings.append(
                    Finding(
                        "LICENSE_DENIED",
                        where,
                        f"`{identifier}` figure dans licenses.denied_spdx",
                    )
                )
            elif identifier in acknowledged:
                print(
                    f"[LICENSE_ACKNOWLEDGED] {where} : `{identifier}` — "
                    f"{' '.join(acknowledged[identifier].split())}"
                )
            elif identifier not in allowed:
                findings.append(
                    Finding(
                        "LICENSE_NOT_ALLOWED",
                        where,
                        f"`{identifier}` n'est pas dans licenses.allowed_spdx "
                        "(licence inconnue de la politique)",
                    )
                )
        if str(entry.get("role") or "") != component.role:
            findings.append(
                Finding(
                    "NOTICE_STALE",
                    where,
                    f"rôle `{entry.get('role')}` au registre, `{component.role}` au verrou",
                )
            )

    for key in sorted(set(registry) - seen):
        findings.append(
            Finding(
                "NOTICE_GHOST_COMPONENT",
                f"{key[0]}:{key[1]}@{key[2]}",
                "présent dans manifests/licenses.yaml, absent des verrous — "
                "notices non régénérées",
            )
        )
    return findings


# ── Rendu du tableau des notices ────────────────────────────────────────────


def render_table(
    components: list[Component], registry: dict[tuple[str, str, str], dict[str, Any]]
) -> str:
    runtime = [c for c in components if c.role == "runtime"]
    development = [c for c in components if c.role != "runtime"]
    lines = [BLOCK_START, ""]
    lines.append(
        "Tableau **généré** : ne pas éditer à la main. "
        "`python3 tools/check_notices.py --refresh` le régénère depuis "
        "`uv.lock`, `apps/web/pnpm-lock.yaml` et `manifests/licenses.yaml` ; "
        "la porte `release` échoue s'il diverge."
    )
    for title, subset, note in (
        (
            "Composants distribués (rôle `runtime`)",
            runtime,
            "Atteignables depuis les dépendances non optionnelles des membres du "
            "workspace, ou depuis les `dependencies` de `apps/web/package.json`.",
        ),
        (
            "Composants d'outillage et de test (rôle `development`)",
            development,
            "Présents dans les verrous, non atteignables depuis un chemin runtime. "
            "Ils ne sont pas distribués ; leur licence est vérifiée quand même.",
        ),
    ):
        lines += ["", f"### {title}", "", note, ""]
        lines += [
            "| Composant | Version | Licence (SPDX) | Écosystème | Source |",
            "|---|---|---|---|---|",
        ]
        for component in subset:
            entry = registry.get(component.key, {})
            lines.append(
                f"| `{component.name}` | `{component.version}` | "
                f"{entry.get('license', 'UNKNOWN')} | {component.ecosystem} | "
                f"{entry.get('source', '—')} |"
            )
    lines += [
        "",
        f"Total : {len(runtime)} distribués, {len(development)} outillage.",
        "",
        BLOCK_END,
    ]
    return "\n".join(lines)


def extract_block(text: str) -> str | None:
    if BLOCK_START not in text or BLOCK_END not in text:
        return None
    start = text.index(BLOCK_START)
    end = text.index(BLOCK_END) + len(BLOCK_END)
    return text[start:end]


def check_notices_document(root: Path, expected: str) -> list[Finding]:
    path = root / "THIRD_PARTY_NOTICES.md"
    if not path.is_file():
        return [Finding("NOTICE_MISSING_DOCUMENT", "THIRD_PARTY_NOTICES.md", "fichier absent")]
    block = extract_block(path.read_text(encoding="utf-8"))
    if block is None:
        return [
            Finding(
                "NOTICE_MISSING_DOCUMENT",
                "THIRD_PARTY_NOTICES.md",
                "bloc généré absent — exécuter `python3 tools/check_notices.py --refresh`",
            )
        ]
    if block.strip() != expected.strip():
        return [
            Finding(
                "NOTICE_STALE",
                "THIRD_PARTY_NOTICES.md",
                "le tableau ne correspond plus aux verrous — "
                "exécuter `python3 tools/check_notices.py --refresh`",
            )
        ]
    return []


# ── Rafraîchissement (réseau) ───────────────────────────────────────────────


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(  # noqa: S310 (schéma https littéral ci-dessous)
        url, headers={"Accept": "application/json", "User-Agent": "vertex-notices-gate"}
    )
    if not url.startswith("https://"):
        raise ValueError(f"URL non https refusée : {url}")
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    return payload


def _license_from_wheel(url: str) -> str:
    """Lit `License-Expression:`/`License:` dans le METADATA d'une roue.

    Recours utilisé quand l'API JSON de PyPI ne publie AUCUNE licence — c'est le
    cas de `mypy-extensions`, dont la roue porte pourtant
    `License-Expression: MIT`. La roue est celle EXACTEMENT référencée par
    `uv.lock` : c'est la distribution réellement installée, pas une supposition.
    """
    if not url.startswith("https://"):
        raise ValueError(f"URL non https refusée : {url}")
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if not names:
            return "UNKNOWN"
        headers = email.message_from_string(archive.read(names[0]).decode("utf-8", "replace"))
    raw = headers.get("License-Expression") or headers.get("License")
    return normalize_license(raw, headers.get_all("Classifier"))


def fetch_license(component: Component, wheel_url: str | None = None) -> tuple[str, str]:
    """Retourne (licence SPDX, URL de la métadonnée consultée)."""
    if component.ecosystem == "python":
        url = f"https://pypi.org/pypi/{component.name}/{component.version}/json"
        try:
            info = _fetch_json(url).get("info") or {}
        except (urllib.error.URLError, OSError, ValueError):
            return "UNKNOWN", url
        raw = info.get("license_expression") or info.get("license")
        resolved = normalize_license(raw, info.get("classifiers"))
        if resolved == "UNKNOWN" and wheel_url:
            try:
                from_wheel = _license_from_wheel(wheel_url)
            except (urllib.error.URLError, OSError, ValueError, zipfile.BadZipFile):
                from_wheel = "UNKNOWN"
            if from_wheel != "UNKNOWN":
                return from_wheel, wheel_url
        return resolved, url
    url = f"https://registry.npmjs.org/{component.name}/{component.version}"
    try:
        data = _fetch_json(url)
    except (urllib.error.URLError, OSError, ValueError):
        return "UNKNOWN", url
    raw = data.get("license")
    if isinstance(raw, dict):
        raw = raw.get("type")
    return normalize_license(str(raw) if raw else None), url


def _wheel_urls(root: Path) -> dict[tuple[str, str], str]:
    """Roue (ou archive source) exacte référencée par `uv.lock`, par paquet."""
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    urls: dict[tuple[str, str], str] = {}
    for entry in lock.get("package") or []:
        wheels = entry.get("wheels") or []
        if wheels:
            urls[(str(entry["name"]).lower(), str(entry["version"]))] = str(wheels[0]["url"])
    return urls


def refresh(root: Path, policy: dict[str, Any]) -> int:
    components = inventory(root, policy)
    wheels = _wheel_urls(root)
    entries = []
    for index, component in enumerate(components, start=1):
        license_id, url = fetch_license(component, wheels.get((component.name, component.version)))
        print(
            f"  [{index:3d}/{len(components)}] {component.ecosystem} "
            f"{component.name}@{component.version} -> {license_id}"
        )
        entries.append(
            {
                "ecosystem": component.ecosystem,
                "name": component.name,
                "version": component.version,
                "license": license_id,
                "role": component.role,
                "source": url,
            }
        )
    header = (
        "# Registre des licences des composants tiers\n"
        "#\n"
        "# GÉNÉRÉ par `python3 tools/check_notices.py --refresh`. Chaque licence\n"
        "# vient de la métadonnée publiée par le distributeur lui-même :\n"
        "#   Python     https://pypi.org/pypi/<nom>/<version>/json\n"
        "#              (license_expression, à défaut license, à défaut classifiers)\n"
        "#   JavaScript https://registry.npmjs.org/<nom>/<version> (champ license)\n"
        "#\n"
        "# Aucune valeur n'est devinée : une métadonnée absente reste `UNKNOWN`,\n"
        "# et `UNKNOWN` fait ÉCHOUER la porte `release`.\n"
        "#\n"
        "# `role` est dérivé du graphe des verrous : `runtime` = atteignable depuis\n"
        "# les dépendances non optionnelles des membres du workspace Python ou\n"
        "# depuis `dependencies` de apps/web/package.json ; `development` sinon.\n"
    )
    payload = {"schema_version": 1, "components": entries}
    (root / "manifests" / "licenses.yaml").write_text(
        header + yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    registry = load_registry(root)
    table = render_table(components, registry)
    notices_path = root / "THIRD_PARTY_NOTICES.md"
    text = notices_path.read_text(encoding="utf-8")
    existing = extract_block(text)
    if existing is None:
        text = text.rstrip() + "\n\n" + table + "\n"
    else:
        text = text.replace(existing, table)
    notices_path.write_text(text, encoding="utf-8")
    print(f"Registre et notices régénérés : {len(entries)} composants.")
    return 0


# ── Orchestration ───────────────────────────────────────────────────────────


def collect_findings(root: Path) -> list[Finding]:
    policy_path = root / "manifests" / "policy.yaml"
    if not policy_path.is_file():
        raise SystemExit(f"ERREUR: politique absente : {policy_path} — porte NON EXÉCUTÉE.")
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    components = inventory(root, policy)
    registry = load_registry(root)
    findings = check_licenses(components, registry, policy)
    findings += check_notices_document(root, render_table(components, registry))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Volet `notices` de la porte `release`.")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="régénère le registre et le tableau depuis les registres officiels (réseau)",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.refresh:
        policy = yaml.safe_load((root / "manifests" / "policy.yaml").read_text(encoding="utf-8"))
        return refresh(root, policy)

    findings = collect_findings(root)
    for finding in sorted(findings, key=lambda f: (f.code, f.where)):
        print(finding.render())
    if findings:
        print(f"\nPORTE release/notices : ÉCHEC — {len(findings)} anomalie(s).")
        return 1
    print("PORTE release/notices : OK — inventaire, licences et notices concordants.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
