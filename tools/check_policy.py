#!/usr/bin/env python3
"""Porte `policy` de docs/06-quality/CI_GATES.md.

« SHA Actions, permissions, lockfiles, capacités interdites, aucun `latest` ;
bloque si anomalie. »

Avant cette porte, ces règles étaient RESPECTÉES mais rien ne les VÉRIFIAIT :
elles tenaient par la discipline d'une seule personne. La frontière financière
de ce dépôt a été contournée trois fois de suite par des régressions de ses
propres correctifs — la discipline ne suffit pas.

Contrôles (chaque code est prouvé par un test qui INJECTE la violation, voir
`tools/tests/test_check_policy.py`) :

    ACTION_NOT_PINNED        `uses:` sans SHA de commit de 40 caractères
    ACTION_PIN_UNKNOWN       SHA absent de manifests/actions-pins.yaml
    ACTION_PIN_IS_TAG_OBJECT SHA d'un objet-tag annoté, pas d'un commit
    ACTION_PIN_DRIFT         (--resolve-remote) le dépôt distant contredit le
                             manifeste
    WORKFLOW_NO_PERMISSIONS  ni le workflow ni le job ne déclare `permissions`
    PERMISSION_ELEVATION     portée en écriture sans motif écrit
    JOB_NO_TIMEOUT           job sans `timeout-minutes`
    CONTINUE_ON_ERROR        étape ou job qui ne peut pas échouer
    PR_TARGET_CHECKOUT       `pull_request_target` qui extrait le code de la PR
    SELF_HOSTED_RUNNER       `runs-on` auto-hébergé ou hors liste
    RUNNER_UNVERIFIABLE      `runs-on` calculé par une expression
    IMAGE_NO_DIGEST          image de conteneur sans digest immuable
    IMAGE_LATEST             image de conteneur en `:latest`
    IMAGE_UNVERIFIABLE       référence d'image calculée par une expression
    DEP_UNPINNED             dépendance déclarée sans aucune contrainte
    DEP_FLOATING             contrainte flottante (`*`, `^`, `~`, plage, tag)
    DEP_NOT_EXACT            outil dont la sortie est un verdict, non `==`
    DEP_NOT_LOCKED           dépendance absente du verrou
    LOCK_NO_HASH             paquet verrouillé sans hachage
    LOCK_DESYNC              verrou désynchronisé du manifeste
    LOCK_MISSING             manifeste avec dépendances et sans verrou
    GATE_NOT_WIRED           porte non appelée par la CI ou par run_checks.sh
    GATE_NOT_DECLARED        script `tools/check_*.py` absent de la politique

CE QUE CETTE PORTE NE PROUVE PAS
--------------------------------
- Elle ne lit pas le CONTENU de l'action épinglée : un commit épinglé peut être
  malveillant. Elle prouve l'immuabilité de la référence, pas son innocuité.
- `--resolve-remote` interroge le réseau ; il n'est donc PAS exécuté par la
  porte ordinaire. Sans lui, la preuve « ce SHA est un commit » repose sur
  `manifests/actions-pins.yaml`, résolu à la main par `git ls-remote`.
- `LOCK_DESYNC` compare les manifestes aux métadonnées écrites dans les
  verrous. Cela détecte une dérive de déclaration, PAS une résolution périmée :
  seuls `uv lock --check` et `pnpm install --frozen-lockfile` prouvent celle-ci,
  et tous deux exigent le réseau.
- `PR_TARGET_CHECKOUT` détecte l'extraction explicite d'une réf de PR. Un
  workflow `pull_request_target` qui exécuterait du code non fiable par un
  autre chemin (script téléchargé, artefact) n'est pas détecté.
- Les capacités IBKR interdites restent la propriété de
  `tools/check_financial_boundary.py` ; cette porte vérifie seulement que ce
  script est réellement BRANCHÉ dans la CI et dans `run_checks.sh`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}(?:$|\s)")
EXPRESSION = re.compile(r"\$\{\{")
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?:['\"])?([^'\"#\s]+)")
NPM_EXACT = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
PEP508 = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._\-]*)"
    r"(?:\[(?P<extras>[^\]]*)\])?"
    r"\s*(?P<spec>[^;]*)"
    r"(?:;\s*(?P<marker>.*))?$"
)
DOCKER_FROM = re.compile(r"^\s*FROM\s+(?P<rest>.+?)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    """Une anomalie bloquante. `where` porte le fichier et, si connu, la ligne."""

    code: str
    where: str
    message: str

    def render(self) -> str:
        return f"[{self.code}] {self.where} : {self.message}"


# ── Politique ───────────────────────────────────────────────────────────────


def load_policy(root: Path) -> dict[str, Any]:
    path = root / "manifests" / "policy.yaml"
    if not path.is_file():
        raise SystemExit(f"ERREUR: politique absente : {path} — porte NON EXÉCUTÉE.")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERREUR: politique illisible : {path}")
    return data


def load_action_pins(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifests" / "actions-pins.yaml"
    if not path.is_file():
        raise SystemExit(f"ERREUR: épinglages absents : {path} — porte NON EXÉCUTÉE.")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pins: dict[str, dict[str, Any]] = {}
    for entry in data.get("actions") or []:
        pins[str(entry["repository"]).lower()] = entry
    return pins


# ── 1. Épinglage des Actions ────────────────────────────────────────────────


def check_uses(path_label: str, text: str, pins: dict[str, dict[str, Any]]) -> list[Finding]:
    """Chaque `uses:` doit épingler un SHA de COMMIT connu du manifeste."""
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = USES_LINE.match(line)
        if match is None:
            continue
        ref = match.group(1)
        where = f"{path_label}:{lineno}"
        if ref.startswith("./"):
            continue  # action locale : versionnée par ce dépôt lui-même
        if ref.startswith("docker://"):
            findings.extend(check_image_ref(where, ref[len("docker://") :]))
            continue
        if "@" not in ref:
            findings.append(
                Finding("ACTION_NOT_PINNED", where, f"`uses: {ref}` sans référence épinglée")
            )
            continue
        target, _, pin = ref.rpartition("@")
        if not SHA40.match(pin):
            findings.append(
                Finding(
                    "ACTION_NOT_PINNED",
                    where,
                    f"`{ref}` : `{pin}` n'est pas un SHA de commit de 40 caractères",
                )
            )
            continue
        repository = "/".join(target.split("/")[:2]).lower()
        entry = pins.get(repository)
        if entry is None:
            findings.append(
                Finding(
                    "ACTION_PIN_UNKNOWN",
                    where,
                    f"`{repository}` absent de manifests/actions-pins.yaml : "
                    "SHA non résolu, donc non prouvé",
                )
            )
            continue
        tag_object = entry.get("tag_object_sha")
        if tag_object and pin == str(tag_object).lower():
            findings.append(
                Finding(
                    "ACTION_PIN_IS_TAG_OBJECT",
                    where,
                    f"`{repository}` épingle l'objet-tag annoté {pin} et non le commit "
                    f"{entry.get('commit_sha')} — l'ancrage n'est pas un commit",
                )
            )
            continue
        if pin != str(entry.get("commit_sha", "")).lower():
            findings.append(
                Finding(
                    "ACTION_PIN_UNKNOWN",
                    where,
                    f"`{repository}` épingle {pin} ; le manifeste a résolu "
                    f"{entry.get('commit_sha')} pour {entry.get('tag')}",
                )
            )
    return findings


def resolve_remote(pins: dict[str, dict[str, Any]]) -> list[Finding]:
    """Re-résout chaque épinglage par `git ls-remote` (réseau requis)."""
    findings: list[Finding] = []
    for repository, entry in sorted(pins.items()):
        tag = str(entry["tag"])
        url = f"https://github.com/{repository}"
        try:
            completed = subprocess.run(  # noqa: S603 (argv littéral, sans shell)
                ["git", "ls-remote", url, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],  # noqa: S607
                check=True,
                text=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            findings.append(
                Finding(
                    "ACTION_PIN_DRIFT",
                    f"manifests/actions-pins.yaml#{repository}",
                    f"résolution distante impossible ({exc}) — aucune preuve",
                )
            )
            continue
        refs = {}
        for raw in completed.stdout.splitlines():
            sha, _, name = raw.partition("\t")
            refs[name.strip()] = sha.strip()
        peeled = refs.get(f"refs/tags/{tag}^{{}}")
        pointed = refs.get(f"refs/tags/{tag}")
        if pointed is None:
            findings.append(
                Finding(
                    "ACTION_PIN_DRIFT",
                    f"manifests/actions-pins.yaml#{repository}",
                    f"le tag {tag} n'existe plus chez {url}",
                )
            )
            continue
        commit = peeled or pointed
        expected_kind = "annotated" if peeled else "lightweight"
        if commit != str(entry.get("commit_sha", "")).lower():
            findings.append(
                Finding(
                    "ACTION_PIN_DRIFT",
                    f"manifests/actions-pins.yaml#{repository}",
                    f"{tag} résout {commit} ; le manifeste dit {entry.get('commit_sha')}",
                )
            )
        if expected_kind != entry.get("tag_kind"):
            findings.append(
                Finding(
                    "ACTION_PIN_DRIFT",
                    f"manifests/actions-pins.yaml#{repository}",
                    f"{tag} est {expected_kind} ; le manifeste dit {entry.get('tag_kind')}",
                )
            )
        recorded_tag_object = entry.get("tag_object_sha")
        actual_tag_object = pointed if peeled else None
        if (recorded_tag_object or None) != actual_tag_object:
            findings.append(
                Finding(
                    "ACTION_PIN_DRIFT",
                    f"manifests/actions-pins.yaml#{repository}",
                    f"objet-tag {actual_tag_object} ; le manifeste dit {recorded_tag_object}",
                )
            )
    return findings


# ── 2. Permissions, timeouts, runners, pull_request_target ──────────────────


def _workflow_triggers(document: dict[Any, Any]) -> set[str]:
    # PyYAML (YAML 1.1) transforme la clé `on:` en booléen True.
    raw = document.get("on", document.get(True))
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    if isinstance(raw, dict):
        return {str(key) for key in raw}
    return set()


def _permission_findings(
    where: str, scope_owner: str, permissions: Any, text: str, marker: str
) -> list[Finding]:
    findings: list[Finding] = []
    elevated: list[str] = []
    if isinstance(permissions, str):
        if permissions == "write-all":
            elevated.append("write-all")
    elif isinstance(permissions, dict):
        for scope, value in permissions.items():
            if str(value) in {"write", "admin"}:
                elevated.append(str(scope))
    for scope in elevated:
        motivated = any(
            marker in line and scope in line.split(marker, 1)[1] for line in text.splitlines()
        )
        if not motivated:
            findings.append(
                Finding(
                    "PERMISSION_ELEVATION",
                    where,
                    f"{scope_owner} élève `{scope}` en écriture sans commentaire "
                    f"`{marker} {scope}` justifiant l'élévation",
                )
            )
    return findings


def _runner_findings(where: str, job_id: str, runs_on: Any, allowed: set[str]) -> list[Finding]:
    labels: list[str] = []
    if isinstance(runs_on, str):
        labels = [runs_on]
    elif isinstance(runs_on, list):
        labels = [str(item) for item in runs_on]
    elif isinstance(runs_on, dict):
        if "group" in runs_on:
            return [
                Finding(
                    "SELF_HOSTED_RUNNER",
                    where,
                    f"job `{job_id}` : groupe de runners `{runs_on['group']}` "
                    "(auto-hébergé par construction)",
                )
            ]
        labels = [str(item) for item in (runs_on.get("labels") or [])]
    else:
        return [
            Finding("RUNNER_UNVERIFIABLE", where, f"job `{job_id}` : `runs-on` absent ou illisible")
        ]

    findings: list[Finding] = []
    for label in labels:
        if EXPRESSION.search(label):
            findings.append(
                Finding(
                    "RUNNER_UNVERIFIABLE",
                    where,
                    f"job `{job_id}` : `runs-on: {label}` est une expression — non vérifiable",
                )
            )
        elif label == "self-hosted" or label not in allowed:
            findings.append(
                Finding(
                    "SELF_HOSTED_RUNNER",
                    where,
                    f"job `{job_id}` : runner `{label}` hors de la liste autorisée "
                    f"({', '.join(sorted(allowed))})",
                )
            )
    return findings


_PR_REF_MARKERS = (
    "github.event.pull_request",
    "github.head_ref",
    "refs/pull/",
    "github.event.workflow_run.head",
)


def check_workflow(path_label: str, text: str, policy: dict[str, Any]) -> list[Finding]:
    """Permissions, timeouts, runners, `continue-on-error`, `pull_request_target`."""
    findings: list[Finding] = []
    document = yaml.safe_load(text)
    if not isinstance(document, dict):
        return [Finding("WORKFLOW_NO_PERMISSIONS", path_label, "workflow illisible")]

    perms_cfg = policy.get("permissions", {})
    marker = str(perms_cfg.get("motive_marker", "MOTIF-PERMISSION:"))
    allowed_runners = {str(x) for x in (policy.get("runners", {}).get("allowed") or [])}

    top_permissions = document.get("permissions")
    if top_permissions is not None:
        findings += _permission_findings(path_label, "le workflow", top_permissions, text, marker)

    if document.get("continue-on-error"):
        findings.append(
            Finding("CONTINUE_ON_ERROR", path_label, "le workflow ne peut pas échouer")
        )

    triggers = _workflow_triggers(document)
    jobs = document.get("jobs") or {}
    if not isinstance(jobs, dict):
        return findings

    for job_id, job in jobs.items():
        where = f"{path_label}#jobs.{job_id}"
        if not isinstance(job, dict):
            continue
        job_permissions = job.get("permissions")
        if job_permissions is None and top_permissions is None:
            findings.append(
                Finding(
                    "WORKFLOW_NO_PERMISSIONS",
                    where,
                    f"ni le workflow ni le job `{job_id}` ne déclarent `permissions`",
                )
            )
        if job_permissions is not None:
            findings += _permission_findings(
                where, f"le job `{job_id}`", job_permissions, text, marker
            )

        is_reusable = "uses" in job
        if not is_reusable and job.get("timeout-minutes") is None:
            findings.append(
                Finding("JOB_NO_TIMEOUT", where, f"job `{job_id}` sans `timeout-minutes`")
            )
        if job.get("continue-on-error"):
            findings.append(
                Finding("CONTINUE_ON_ERROR", where, f"job `{job_id}` ne peut pas échouer")
            )
        if not is_reusable:
            findings += _runner_findings(where, str(job_id), job.get("runs-on"), allowed_runners)

        container = job.get("container")
        image = container.get("image") if isinstance(container, dict) else container
        if isinstance(image, str):
            findings += check_image_ref(f"{where}.container", image)
        for service_id, service in (job.get("services") or {}).items():
            service_image = service.get("image") if isinstance(service, dict) else service
            if isinstance(service_image, str):
                findings += check_image_ref(f"{where}.services.{service_id}", service_image)

        for index, step in enumerate(job.get("steps") or []):
            if not isinstance(step, dict):
                continue
            step_where = f"{where}.steps[{index}]"
            if step.get("continue-on-error"):
                findings.append(
                    Finding("CONTINUE_ON_ERROR", step_where, "étape qui ne peut pas échouer")
                )
            if "pull_request_target" not in triggers:
                continue
            uses = str(step.get("uses") or "")
            with_block = step.get("with") or {}
            ref = str(with_block.get("ref") or "")
            if uses.split("@")[0].endswith("actions/checkout") and ref:
                if any(m in ref for m in _PR_REF_MARKERS) or EXPRESSION.search(ref):
                    findings.append(
                        Finding(
                            "PR_TARGET_CHECKOUT",
                            step_where,
                            "`pull_request_target` extrait le code de la PR "
                            f"(`ref: {ref}`) : code non fiable avec les secrets du dépôt",
                        )
                    )
    return findings


# ── 3. Images de conteneur ──────────────────────────────────────────────────


def check_image_ref(where: str, ref: str) -> list[Finding]:
    ref = ref.strip()
    if EXPRESSION.search(ref):
        return [Finding("IMAGE_UNVERIFIABLE", where, f"référence calculée : `{ref}`")]
    if re.search(r":latest(?:@|$)", ref):
        return [Finding("IMAGE_LATEST", where, f"`{ref}` utilise le tag mouvant `latest`")]
    if not DIGEST.search(ref + " "):
        return [Finding("IMAGE_NO_DIGEST", where, f"`{ref}` sans digest immuable `@sha256:…`")]
    return []


def check_dockerfile(path_label: str, text: str) -> list[Finding]:
    """`FROM` doit porter un digest, sauf s'il désigne une étape déjà définie."""
    findings: list[Finding] = []
    stages: set[str] = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = DOCKER_FROM.match(line)
        if match is None:
            continue
        parts = [p for p in match.group("rest").split() if not p.startswith("--")]
        if not parts:
            continue
        image = parts[0]
        alias = parts[2] if len(parts) >= 3 and parts[1].lower() == "as" else None
        where = f"{path_label}:{lineno}"
        if image != "scratch" and image not in stages:
            findings += check_image_ref(where, image)
        if alias:
            stages.add(alias)
    return findings


# ── 4. Dépendances et verrous — Python ──────────────────────────────────────


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_requirement(raw: str) -> tuple[str, str, str | None] | None:
    match = PEP508.match(raw)
    if match is None:
        return None
    spec = (match.group("spec") or "").strip()
    marker = (match.group("marker") or "").strip() or None
    return normalize(match.group("name")), spec, marker


def _pyproject_requirements(data: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    """(nom, spécificateur, marqueur) pour les dépendances et chaque extra."""
    out: list[tuple[str, str, str | None]] = []
    project = data.get("project") or {}
    for raw in project.get("dependencies") or []:
        parsed = _parse_requirement(str(raw))
        if parsed:
            out.append(parsed)
    for extra, entries in (project.get("optional-dependencies") or {}).items():
        for raw in entries:
            parsed = _parse_requirement(str(raw))
            if parsed:
                name, spec, marker = parsed
                combined = f"extra == '{extra}'" if marker is None else marker
                out.append((name, spec, combined))
    return out


def _lock_requires_dist(entry: dict[str, Any]) -> set[tuple[str, str, str | None]]:
    out: set[tuple[str, str, str | None]] = set()
    for item in (entry.get("metadata") or {}).get("requires-dist") or []:
        if "editable" in item or "virtual" in item:
            continue
        out.add(
            (
                normalize(str(item["name"])),
                str(item.get("specifier") or ""),
                item.get("marker"),
            )
        )
    return out


def check_python_dependencies(root: Path, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    root_pyproject = root / "pyproject.toml"
    if not root_pyproject.is_file():
        return findings
    root_data = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))

    members = [root_pyproject]
    for member in ((root_data.get("tool") or {}).get("uv") or {}).get("workspace", {}).get(
        "members", []
    ):
        candidate = root / str(member) / "pyproject.toml"
        if candidate.is_file():
            members.append(candidate)

    lock_path = root / "uv.lock"
    if not lock_path.is_file():
        findings.append(
            Finding("LOCK_MISSING", "uv.lock", "verrou Python absent — aucune version prouvée")
        )
        return findings
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = lock.get("package") or []
    locked_versions: dict[str, set[str]] = {}
    lock_by_name: dict[str, dict[str, Any]] = {}
    for entry in packages:
        name = normalize(str(entry["name"]))
        locked_versions.setdefault(name, set()).add(str(entry.get("version", "")))
        lock_by_name[name] = entry

    first_party = {normalize(x) for x in (policy["dependencies"].get("first_party_python") or [])}
    exact_required = {
        normalize(x) for x in (policy["dependencies"].get("exact_pin_required") or [])
    }

    for pyproject in members:
        label = str(pyproject.relative_to(root))
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        requirements = _pyproject_requirements(data)
        for name, spec, _marker in requirements:
            if name in first_party:
                continue
            if not spec:
                findings.append(
                    Finding("DEP_UNPINNED", label, f"`{name}` déclaré sans aucune contrainte")
                )
            elif "*" in spec:
                findings.append(Finding("DEP_FLOATING", label, f"`{name}{spec}` est flottant"))
            elif name in exact_required and not spec.startswith("=="):
                findings.append(
                    Finding(
                        "DEP_NOT_EXACT",
                        label,
                        f"`{name}{spec}` : la sortie de cet outil est un verdict de porte, "
                        "elle doit être épinglée exactement (`==`)",
                    )
                )
            if name not in locked_versions:
                findings.append(
                    Finding("DEP_NOT_LOCKED", label, f"`{name}` absent de uv.lock")
                )

        # Désynchronisation : uv écrit les exigences du manifeste dans le verrou.
        project_name = normalize(str((data.get("project") or {}).get("name") or ""))
        lock_entry = lock_by_name.get(project_name)
        if lock_entry is None:
            continue
        declared = {(n, s, m) for (n, s, m) in requirements if n not in first_party}
        recorded = {(n, s, m) for (n, s, m) in _lock_requires_dist(lock_entry)}
        if declared != recorded:
            missing = sorted(declared - recorded)
            extra = sorted(recorded - declared)
            findings.append(
                Finding(
                    "LOCK_DESYNC",
                    label,
                    f"uv.lock ne reflète plus `{project_name}` — "
                    f"absent du verrou : {missing or '—'} ; "
                    f"absent du manifeste : {extra or '—'}",
                )
            )

    for entry in packages:
        source = entry.get("source") or {}
        if "registry" not in source:
            continue  # membre du workspace ou source locale : pas de hachage attendu
        name = str(entry["name"])
        has_sdist_hash = bool((entry.get("sdist") or {}).get("hash"))
        has_wheel_hash = any(w.get("hash") for w in entry.get("wheels") or [])
        if not (has_sdist_hash or has_wheel_hash):
            findings.append(
                Finding(
                    "LOCK_NO_HASH",
                    "uv.lock",
                    f"`{name}=={entry.get('version')}` verrouillé sans aucun hachage",
                )
            )
    return findings


# ── 5. Dépendances et verrous — Node ────────────────────────────────────────

_NPM_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies")


def check_node_dependencies(root: Path, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    exact_required = {str(x) for x in (policy["dependencies"].get("exact_pin_required") or [])}

    for manifest in sorted(root.rglob("package.json")):
        if "node_modules" in manifest.parts or ".venv" in manifest.parts:
            continue
        label = str(manifest.relative_to(root))
        data = json.loads(manifest.read_text(encoding="utf-8"))
        declared: dict[str, dict[str, str]] = {}
        total = 0
        for section in _NPM_SECTIONS:
            entries = data.get(section) or {}
            declared[section] = {str(k): str(v) for k, v in entries.items()}
            total += len(entries)
            for name, spec in entries.items():
                if not NPM_EXACT.match(str(spec)):
                    code = "DEP_NOT_EXACT" if name in exact_required else "DEP_FLOATING"
                    findings.append(
                        Finding(
                            code,
                            label,
                            f"`{name}: {spec}` n'est pas une version exacte "
                            "(règle pnpm_lock_exact_and_save_exact)",
                        )
                    )

        lock_path = manifest.parent / "pnpm-lock.yaml"
        if not lock_path.is_file():
            if total:
                findings.append(
                    Finding(
                        "LOCK_MISSING",
                        label,
                        f"{total} dépendance(s) déclarée(s) sans `pnpm-lock.yaml` voisin",
                    )
                )
            continue
        findings += check_pnpm_lock(
            str(lock_path.relative_to(root)),
            lock_path.read_text(encoding="utf-8"),
            label,
            declared,
        )
    return findings


def check_pnpm_lock(
    lock_label: str, lock_text: str, manifest_label: str, declared: dict[str, dict[str, str]]
) -> list[Finding]:
    findings: list[Finding] = []
    lock = yaml.safe_load(lock_text) or {}
    if not lock.get("lockfileVersion"):
        findings.append(Finding("LOCK_DESYNC", lock_label, "`lockfileVersion` absent"))

    importer = (lock.get("importers") or {}).get(".") or {}
    for section, entries in declared.items():
        recorded = importer.get(section) or {}
        recorded_specs = {
            str(name): str((value or {}).get("specifier", "")) for name, value in recorded.items()
        }
        if recorded_specs != entries:
            missing = sorted(set(entries) - set(recorded_specs))
            surplus = sorted(set(recorded_specs) - set(entries))
            drifted = sorted(
                f"{n}: {entries[n]} ≠ {recorded_specs[n]}"
                for n in set(entries) & set(recorded_specs)
                if entries[n] != recorded_specs[n]
            )
            findings.append(
                Finding(
                    "LOCK_DESYNC",
                    lock_label,
                    f"`{section}` désynchronisé de {manifest_label} — "
                    f"absent du verrou : {missing or '—'} ; "
                    f"absent du manifeste : {surplus or '—'} ; "
                    f"spécificateur divergent : {drifted or '—'}",
                )
            )

    for name, entry in (lock.get("packages") or {}).items():
        resolution = (entry or {}).get("resolution") or {}
        if not resolution.get("integrity"):
            findings.append(
                Finding("LOCK_NO_HASH", lock_label, f"`{name}` verrouillé sans `integrity`")
            )
    return findings


# ── 6. Câblage des portes ───────────────────────────────────────────────────


def check_gate_wiring(root: Path, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    required = [str(x) for x in (policy.get("gates", {}).get("must_be_wired") or [])]
    consumers = {
        ".github/workflows/ci.yml": root / ".github" / "workflows" / "ci.yml",
        "tools/run_checks.sh": root / "tools" / "run_checks.sh",
    }
    texts: dict[str, str] = {}
    for label, path in consumers.items():
        if not path.is_file():
            findings.append(Finding("GATE_NOT_WIRED", label, "consommateur de portes absent"))
            continue
        texts[label] = path.read_text(encoding="utf-8")

    for script in required:
        if not (root / script).is_file():
            findings.append(
                Finding("GATE_NOT_WIRED", script, "script déclaré par la politique mais absent")
            )
            continue
        for label, text in texts.items():
            if script not in text:
                findings.append(
                    Finding("GATE_NOT_WIRED", label, f"`{script}` n'est jamais appelé ici")
                )

    dormant: dict[str, str] = {}
    for item in policy.get("gates", {}).get("known_not_wired") or []:
        script = str(item.get("script") or "")
        reason = str(item.get("reason") or "").strip()
        if not reason:
            findings.append(
                Finding(
                    "GATE_DORMANT_WITHOUT_REASON",
                    "manifests/policy.yaml",
                    f"`{script}` déclaré non branché sans motif écrit",
                )
            )
            continue
        dormant[script] = reason
        if texts and all(script in text for text in texts.values()):
            findings.append(
                Finding(
                    "GATE_DORMANT_BUT_WIRED",
                    script,
                    "listé dans `known_not_wired` alors qu'il est branché partout — "
                    "le déplacer dans `must_be_wired`",
                )
            )
        else:
            print(f"[GATE_DORMANT] {script} : {' '.join(reason.split())}")

    declared = set(required) | set(dormant)
    for script_path in sorted((root / "tools").glob("check_*.py")):
        relative = f"tools/{script_path.name}"
        if relative not in declared:
            findings.append(
                Finding(
                    "GATE_NOT_DECLARED",
                    relative,
                    "porte présente sur le disque mais absente de "
                    "manifests/policy.yaml (ni `gates.must_be_wired`, ni "
                    "`gates.known_not_wired`)",
                )
            )
    return findings


# ── Orchestration ───────────────────────────────────────────────────────────


def collect_findings(root: Path, *, resolve: bool = False) -> list[Finding]:
    policy = load_policy(root)
    pins = load_action_pins(root)
    findings: list[Finding] = []

    workflows_dir = root / ".github" / "workflows"
    workflows = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    if not workflows:
        findings.append(
            Finding("GATE_NOT_WIRED", ".github/workflows", "aucun workflow — aucune porte CI")
        )
    for workflow in workflows:
        label = str(workflow.relative_to(root))
        text = workflow.read_text(encoding="utf-8")
        findings += check_uses(label, text, pins)
        findings += check_workflow(label, text, policy)

    for compose in sorted(root.rglob("compose*.y*ml")):
        if "node_modules" in compose.parts:
            continue
        label = str(compose.relative_to(root))
        document = yaml.safe_load(compose.read_text(encoding="utf-8")) or {}
        for service_id, service in (document.get("services") or {}).items():
            image = (service or {}).get("image")
            if isinstance(image, str):
                findings += check_image_ref(f"{label}#services.{service_id}", image)

    for dockerfile in sorted(root.rglob("Dockerfile*")):
        if "node_modules" in dockerfile.parts:
            continue
        findings += check_dockerfile(
            str(dockerfile.relative_to(root)), dockerfile.read_text(encoding="utf-8")
        )

    findings += check_python_dependencies(root, policy)
    findings += check_node_dependencies(root, policy)
    findings += check_gate_wiring(root, policy)

    if resolve:
        findings += resolve_remote(pins)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Porte `policy` de Vertex 1.0 Beta.")
    parser.add_argument("--root", default=str(REPO_ROOT), help="racine du dépôt à contrôler")
    parser.add_argument(
        "--resolve-remote",
        action="store_true",
        help="re-résout les épinglages d'Actions par `git ls-remote` (réseau requis)",
    )
    args = parser.parse_args(argv)

    findings = collect_findings(Path(args.root).resolve(), resolve=args.resolve_remote)
    for finding in sorted(findings, key=lambda f: (f.code, f.where)):
        print(finding.render())
    if findings:
        print(f"\nPORTE policy : ÉCHEC — {len(findings)} anomalie(s).")
        return 1
    print("PORTE policy : OK — épinglages, permissions, runners, images et verrous conformes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
