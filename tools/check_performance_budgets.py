#!/usr/bin/env python3
"""Guard: performance budgets are measured, not asserted.

``manifests/performance-budgets.yaml`` states ``policy.missing_measurement_is_pass:
false``. That single line is what this gate exists to enforce: a budget with no
measurement behind it is a failure, not a pass. Every other rule here follows
from refusing to let an unmeasured budget look satisfied.

The manifest — never the report — owns the list of required measurements. If
the report declared its own scope, shipping an empty report would make the gate
green: coverage would be self-attested. So ``required_measurements`` lives in
the manifest, and a ``MEASURED`` entry with no matching measurement fails.

Findings (exit 1 when any is blocking):

1. ``manifest_unusable`` / ``report_unusable`` — one of the two documents is
   absent or malformed. Nothing can be concluded, so nothing passes.
2. ``manifest_drift`` — the report was produced against a different version of
   the budgets manifest. A measurement of another budget is not a measurement
   of this one.
3. ``unknown_profile`` — the report claims a profile the manifest does not
   define, so the manifest cannot say whether its budgets are absolute.
4. ``missing_profile_metadata`` — the profile's ``required_metadata`` is
   incomplete. Without the runner description a number is not comparable to
   anything, including itself.
5. ``missing_measurement`` — a ``MEASURED`` entry has no measurement.
6. ``unmeasured_without_exception`` — a ``NOT_YET_MEASURED`` entry lacks
   ``owner``, ``reason``, ``expires_at`` or ``closure_criterion``. Undocumented
   debt is indistinguishable from a forgotten budget.
7. ``expired_exception`` — ``expires_at`` has passed. The exception was dated
   precisely so it could not become permanent.
8. ``unresolvable_budget_path`` — ``budget_path`` points nowhere. A budget that
   cannot be read is not a budget that is met.
9. ``insufficient_samples`` — a percentile reported with fewer samples than
   ``measurement.minimum_samples`` requires. A p99 over 12 samples is a
   sentence, not a statistic.
10. ``undeclared_measurement`` — the report carries a metric the manifest does
    not require. A second, undeclared channel of numbers is how a favourable
    metric gets substituted for the required one.
11. ``budget_exceeded`` — the value is beyond budget. Blocking under a profile
    whose ``absolute_release_gate`` is true, AND — whatever the profile —
    whenever the metric declares ``machine_independent: true``. That second
    rule exists because an audit measured a bundle **32x** over budget passing
    this gate under ``P-CI``: the profile has no absolute authority, so the
    overrun was only a warning. A gzip byte count does not depend on the
    machine that measured it; there is no runner on which 10 MB is acceptable.
    Machine-sensitive budgets (latency, throughput) stay profile-gated, which
    is what ``enforcement.absolute_targets_block_pr: false`` was written for.
    Any other overrun is recorded as a warning, never dropped.
15. ``machine_independence_undeclared`` — a ``MEASURED`` ``max`` budget that
    does not say whether it is machine-independent. Fail-closed: omitting the
    field would silently buy the permissive path, which is exactly how the
    32x overrun went unnoticed.
12. ``regression_blocked`` / ``regression_warning`` — relative degradation
    against the reported baseline, per ``regression.warning_fraction`` and
    ``regression.block_fraction``. These block regardless of profile:
    ``enforcement.relative_regressions_block_pr_when_repeated`` is true.
13. ``hard_failure_observed`` — anything in ``hard_failures``. Unconditional.
14. ``forbidden_metric_label`` — the report carries a label listed in
    ``observability.forbidden_metric_labels`` (``ticker``, ``portfolio_id``,
    ``trace_id``, ...). A performance report is a place personal and market
    data must never reach.

Output: JSON ``{"ok": bool, "findings": [...], "warnings": [...]}`` on stdout.
Findings carry metric identifiers, numbers and repository-relative paths only.
Read-only: this tool never writes to the repository.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

MANIFEST_RELATIVE = Path("manifests/performance-budgets.yaml")

# Fields an exception must carry, mirroring `regression.exception_fields` in the
# manifest. `closure_criterion` replaces that section's `closure_criterion`
# spelling and `financial_and_user_impact` / `mitigation` are not demanded of a
# not-yet-measured budget: nothing has degraded, the measurement simply does not
# exist yet.
EXCEPTION_FIELDS = ("owner", "reason", "expires_at", "closure_criterion")

PERCENTILE_SUFFIXES = ("p50", "p90", "p95", "p99", "max")


class DocumentError(RuntimeError):
    """A required document is absent or unusable."""


def manifest_hash(path: Path) -> str:
    """Content hash of the budgets manifest, as the report must echo it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(document: Any, path: str) -> Any:
    """Resolve a ``budget_path`` against the manifest.

    ``a.b.c`` descends through mappings. ``segments#identifier`` selects the
    list element whose ``id`` equals ``identifier`` — the manifest describes hot
    path segments as a list of records, and addressing them by position would
    silently point at a different segment the day one is inserted.
    """
    current = document
    for token in path.split("."):
        if "#" in token:
            key, _, wanted = token.partition("#")
            current = current[key] if isinstance(current, dict) else None
            if not isinstance(current, list):
                raise KeyError(path)
            for element in current:
                if isinstance(element, dict) and element.get("id") == wanted:
                    current = element
                    break
            else:
                raise KeyError(path)
            continue
        if not isinstance(current, dict) or token not in current:
            raise KeyError(path)
        current = current[token]
    return current


def _percentile_of(metric_id: str) -> str | None:
    """The percentile a metric identifier claims to report, if any."""
    tail = metric_id.rsplit(".", 1)[-1]
    return tail if tail in PERCENTILE_SUFFIXES else None


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


def check(root: Path, report_path: Path, today: dt.date) -> dict[str, Any]:
    """Evaluate the measurement report against the budgets manifest."""
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    manifest_path = root / MANIFEST_RELATIVE
    if not manifest_path.is_file():
        raise DocumentError(f"{MANIFEST_RELATIVE} is absent")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise DocumentError(f"{MANIFEST_RELATIVE} is not a mapping")

    required = manifest.get("required_measurements")
    if not isinstance(required, list) or not required:
        raise DocumentError(
            f"{MANIFEST_RELATIVE} declares no `required_measurements`; the gate "
            "would have nothing to enforce and must not pass by emptiness"
        )

    if not report_path.is_file():
        raise DocumentError(
            f"{report_path} is absent — run the measurement producers before the gate"
        )
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise DocumentError(f"the measurement report is not valid JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise DocumentError("the measurement report is not an object")

    # --- provenance -------------------------------------------------------
    expected_hash = manifest_hash(manifest_path)
    if report.get("manifest_hash") != expected_hash:
        findings.append(
            {
                "code": "manifest_drift",
                "detail": "the report was produced against a different budgets manifest",
                "expected_manifest_hash": expected_hash,
                "reported_manifest_hash": report.get("manifest_hash"),
            }
        )

    profiles = manifest.get("profiles") or {}
    profile_id = report.get("profile_id")
    profile = profiles.get(profile_id) if isinstance(profiles, dict) else None
    absolute_gate = False
    if not isinstance(profile, dict):
        findings.append(
            {
                "code": "unknown_profile",
                "detail": "the report claims a profile the manifest does not define",
                "profile_id": profile_id,
            }
        )
    else:
        absolute_gate = bool(profile.get("absolute_release_gate"))
        metadata = report.get("runner_metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        for field in profile.get("required_metadata", ()):
            if not metadata.get(field):
                findings.append(
                    {
                        "code": "missing_profile_metadata",
                        "detail": "the profile requires this metadata for a comparable run",
                        "profile_id": profile_id,
                        "field": field,
                    }
                )

    # --- hard failures ----------------------------------------------------
    declared_hard = set(manifest.get("hard_failures") or ())
    observed = report.get("hard_failures_observed")
    for name in observed if isinstance(observed, list) else []:
        findings.append(
            {
                "code": "hard_failure_observed",
                "detail": "a hard failure was observed; no profile makes this acceptable",
                "hard_failure": name,
                "declared_in_manifest": name in declared_hard,
            }
        )

    # --- forbidden labels -------------------------------------------------
    observability = manifest.get("observability") or {}
    forbidden = set(observability.get("forbidden_metric_labels") or ())

    measurements = report.get("measurements")
    measurements = measurements if isinstance(measurements, list) else []
    by_id: dict[str, dict[str, Any]] = {}
    for entry in measurements:
        if not isinstance(entry, dict) or "metric_id" not in entry:
            findings.append(
                {"code": "report_unusable", "detail": "a measurement has no metric_id"}
            )
            continue
        by_id[str(entry["metric_id"])] = entry
        labels = entry.get("labels")
        for label in (labels if isinstance(labels, dict) else {}):
            if label in forbidden:
                findings.append(
                    {
                        "code": "forbidden_metric_label",
                        "detail": "this label may carry personal or market data",
                        "metric_id": entry["metric_id"],
                        "label": label,
                    }
                )

    minimum_samples = (manifest.get("measurement") or {}).get("minimum_samples") or {}
    regression = manifest.get("regression") or {}
    warning_fraction = float(regression.get("warning_fraction", 0.10))
    block_fraction = float(regression.get("block_fraction", 0.20))
    repetitions_to_block = int(regression.get("block_after_comparable_repetitions", 3))

    declared_ids: set[str] = set()
    for spec in required:
        if not isinstance(spec, dict) or "metric_id" not in spec:
            raise DocumentError("a `required_measurements` entry has no metric_id")
        metric_id = str(spec["metric_id"])
        declared_ids.add(metric_id)
        status = spec.get("status")

        if status == "NOT_YET_MEASURED":
            missing = [field for field in EXCEPTION_FIELDS if not spec.get(field)]
            if missing:
                findings.append(
                    {
                        "code": "unmeasured_without_exception",
                        "detail": "an unmeasured budget must be owned, explained and dated",
                        "metric_id": metric_id,
                        "missing_fields": missing,
                    }
                )
                continue
            expires = _parse_date(spec.get("expires_at"))
            if expires is None:
                findings.append(
                    {
                        "code": "unmeasured_without_exception",
                        "detail": "`expires_at` is not an ISO date",
                        "metric_id": metric_id,
                        "expires_at": str(spec.get("expires_at")),
                    }
                )
            elif expires < today:
                findings.append(
                    {
                        "code": "expired_exception",
                        "detail": "the exception was dated so it could not become permanent",
                        "metric_id": metric_id,
                        "expires_at": expires.isoformat(),
                    }
                )
            continue

        if status != "MEASURED":
            raise DocumentError(
                f"`{metric_id}` declares an unknown status {status!r}; "
                "only MEASURED and NOT_YET_MEASURED exist"
            )

        try:
            budget = _resolve(manifest, str(spec.get("budget_path", "")))
        except (KeyError, TypeError):
            findings.append(
                {
                    "code": "unresolvable_budget_path",
                    "detail": "a budget that cannot be read is not a budget that is met",
                    "metric_id": metric_id,
                    "budget_path": spec.get("budget_path"),
                }
            )
            continue

        entry = by_id.get(metric_id)
        if entry is None:
            findings.append(
                {
                    "code": "missing_measurement",
                    "detail": "policy.missing_measurement_is_pass is false",
                    "metric_id": metric_id,
                }
            )
            continue

        value = entry.get("value")
        kind = spec.get("kind")

        percentile = _percentile_of(metric_id)
        if percentile is not None and percentile in minimum_samples:
            samples = entry.get("samples")
            needed = int(minimum_samples[percentile])
            if not isinstance(samples, int) or samples < needed:
                findings.append(
                    {
                        "code": "insufficient_samples",
                        "detail": "the percentile is not supported by enough samples",
                        "metric_id": metric_id,
                        "samples": samples,
                        "minimum_samples": needed,
                    }
                )
                continue

        if kind == "boolean_true":
            if value is not True:
                findings.append(
                    {
                        "code": "budget_exceeded",
                        "detail": "this budget is a boolean and must be exactly true",
                        "metric_id": metric_id,
                        "value": value,
                        "blocking": True,
                    }
                )
            continue

        if kind != "max":
            raise DocumentError(f"`{metric_id}` declares an unknown kind {spec.get('kind')!r}")

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            findings.append(
                {
                    "code": "report_unusable",
                    "detail": "a `max` budget needs a numeric measurement",
                    "metric_id": metric_id,
                    "value": value,
                }
            )
            continue
        if not isinstance(budget, (int, float)) or isinstance(budget, bool):
            findings.append(
                {
                    "code": "unresolvable_budget_path",
                    "detail": "the budget this metric points at is not a number",
                    "metric_id": metric_id,
                    "budget_path": spec.get("budget_path"),
                }
            )
            continue

        # A `max` budget must say whether its value depends on the machine.
        # Fail-closed: an omitted field would silently take the permissive
        # branch below, which is how a 32x bundle overrun passed under P-CI.
        declared_independence = spec.get("machine_independent")
        if not isinstance(declared_independence, bool):
            findings.append(
                {
                    "code": "machine_independence_undeclared",
                    "detail": (
                        "a `max` budget must declare `machine_independent`; "
                        "without it the gate cannot know whether a profile "
                        "without absolute authority may downgrade an overrun"
                    ),
                    "metric_id": metric_id,
                }
            )
            continue

        if value > budget:
            record = {
                "code": "budget_exceeded",
                "metric_id": metric_id,
                "value": value,
                "budget": budget,
                "unit": spec.get("unit"),
                "profile_id": profile_id,
                "machine_independent": declared_independence,
            }
            if absolute_gate:
                record["detail"] = "this profile is an absolute release gate"
                record["blocking"] = True
                findings.append(record)
            elif declared_independence:
                # A gzip byte count is the same on every runner. There is no
                # machine on which 10 MB instead of 300 kB is acceptable, so no
                # profile may downgrade this overrun to a warning.
                record["detail"] = (
                    "this budget does not depend on the measuring machine; "
                    "no profile downgrades it to a warning"
                )
                record["blocking"] = True
                findings.append(record)
            else:
                # enforcement.absolute_targets_block_pr is false at this stage,
                # and this budget IS machine-sensitive: a latency measured on a
                # shared runner says little about the target machine. The
                # overrun is recorded, never dropped: a warning that leaves no
                # trace is the same as no measurement.
                record["detail"] = (
                    "absolute targets do not block a pull request at this "
                    "enforcement stage for a machine-sensitive budget; the "
                    "overrun is recorded"
                )
                record["blocking"] = False
                warnings.append(record)

        baseline = entry.get("baseline_value")
        if isinstance(baseline, (int, float)) and not isinstance(baseline, bool) and baseline > 0:
            drift = (value - baseline) / baseline
            repetitions = entry.get("consecutive_comparable_regressions")
            repetitions = repetitions if isinstance(repetitions, int) else 0
            if drift >= block_fraction and repetitions >= repetitions_to_block:
                findings.append(
                    {
                        "code": "regression_blocked",
                        "detail": "a repeated relative regression blocks at every profile",
                        "metric_id": metric_id,
                        "value": value,
                        "baseline_value": baseline,
                        "drift_fraction": round(drift, 4),
                        "consecutive_comparable_regressions": repetitions,
                        "blocking": True,
                    }
                )
            elif drift >= warning_fraction:
                warnings.append(
                    {
                        "code": "regression_warning",
                        "detail": "relative degradation above the warning fraction",
                        "metric_id": metric_id,
                        "value": value,
                        "baseline_value": baseline,
                        "drift_fraction": round(drift, 4),
                        "consecutive_comparable_regressions": repetitions,
                        "blocking": False,
                    }
                )

    for metric_id in sorted(set(by_id) - declared_ids):
        findings.append(
            {
                "code": "undeclared_measurement",
                "detail": "the manifest does not require this metric; an undeclared "
                "channel of numbers can substitute a flattering metric for the required one",
                "metric_id": metric_id,
            }
        )

    return {
        "ok": not findings,
        "findings": findings,
        "warnings": warnings,
        "profile_id": profile_id,
        "absolute_release_gate": absolute_gate,
        "required_measurements": len(required),
        "measured_entries": sum(1 for s in required if s.get("status") == "MEASURED"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="measurement report produced by the performance measurement tools",
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Vertex One repository root",
    )
    args = parser.parse_args(argv)
    try:
        # `dt.date.today()` lit l'horloge LOCALE : le jour retenu pour juger un
        # budget changeait donc selon le fuseau de la machine. Le programme
        # calcule et stocke en UTC (.claude/rules/python.md).
        report = check(
            args.root.resolve(), args.report.resolve(), dt.datetime.now(dt.UTC).date()
        )
    except DocumentError as exc:
        print(
            json.dumps(
                {"ok": False, "findings": [{"code": "report_unusable", "detail": str(exc)}]},
                indent=2,
            )
        )
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
