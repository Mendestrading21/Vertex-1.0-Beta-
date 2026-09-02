"""Governance guard: the calculation registry must not drift from the code.

Two layers:

1. the real repository must pass ``tools/check_calculation_registry.py``
   (no unknown identifier, no unapproved identifier in production, no missing
   runtime field, no missing test or implementation file);
2. the scanner itself is unit-tested on SYNTHETIC temporary repositories, so a
   green result really means "the checker can fail".

All fixtures are SYNTHETIC: no market data, no secret, no network, no clock.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CHECKER_PATH = REPO_ROOT / "tools" / "check_calculation_registry.py"
REGISTRY_PATH = REPO_ROOT / "docs" / "03-domain" / "calculations" / "CALCULATION_REGISTRY.yaml"


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "_vertex_check_calculation_registry", CHECKER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_checker()


# --- Layer 1: the real repository ------------------------------------------


class TestRealRepository:
    def test_checker_and_registry_exist(self):
        assert CHECKER_PATH.is_file()
        assert REGISTRY_PATH.is_file()

    def test_repository_passes_the_guard(self):
        report = checker.check(REPO_ROOT)
        assert report["ok"], json.dumps(report["findings"], indent=2, sort_keys=True)

    def test_guard_runs_as_a_script_and_exits_zero(self):
        completed = subprocess.run(  # noqa: S603 (argv littéral, sans shell)
            [sys.executable, str(CHECKER_PATH), str(REPO_ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        assert payload["findings"] == []

    def test_every_production_identifier_is_approved(self):
        document = checker.load_registry(REGISTRY_PATH)
        entries = {entry["id"]: entry for entry in document["calculations"]}
        families = {identifier.split(".", 1)[0] for identifier in entries}
        usage = checker.scan_production_usage(REPO_ROOT, set(entries), families)
        assert usage, "the scanner must find the calculation identifiers used in production"
        for identifier in usage:
            assert identifier in entries, identifier
            assert entries[identifier]["runtime_status"] == checker.APPROVED, identifier

    def test_registry_declares_no_partial_approval(self):
        document = checker.load_registry(REGISTRY_PATH)
        required = document["required_runtime_fields"]
        for entry in document["calculations"]:
            if entry["runtime_status"] == checker.APPROVED:
                missing = [field for field in required if not entry.get(field)]
                assert not missing, f"{entry['id']} misses {missing}"
            else:
                assert entry.get("blocking_reason"), entry["id"]


# --- Layer 2: the scanner itself, on synthetic repositories -----------------

MINIMAL_ENTRY = """\
  - id: market.simple_return
    runtime_status: APPROVED
    spec_version: "1.0.0"
    method: closed_form_price_ratio_minus_one
    assumptions: ["synthetic fixture"]
    parameter_schema: {price_t0: {type: float}}
    tolerances: {float64_rel_tol: 1.0e-9}
    oracle: hand_derived_golden_vectors
    criticality: high
    tests: [tests/test_market.py]
"""

REGISTRY_HEADER = """\
schema_version: 2
registry_status: synthetic_fixture
required_runtime_fields:
  - spec_version
  - method
  - assumptions
  - parameter_schema
  - tolerances
  - oracle
  - criticality
  - tests
calculations:
"""


def build_repo(tmp_path: Path, registry_body: str, production_source: str) -> Path:
    root = tmp_path / "repo"
    registry_dir = root / "docs" / "03-domain" / "calculations"
    registry_dir.mkdir(parents=True)
    (registry_dir / "CALCULATION_REGISTRY.yaml").write_text(
        REGISTRY_HEADER + registry_body, encoding="utf-8"
    )
    source_dir = root / "apps" / "worker" / "src" / "vertex_worker"
    source_dir.mkdir(parents=True)
    (source_dir / "markets.py").write_text(production_source, encoding="utf-8")
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_market.py").write_text("# SYNTHETIC placeholder\n", encoding="utf-8")
    return root


def codes(report: dict) -> set[str]:
    return {finding["code"] for finding in report["findings"]}


APPROVED_USAGE = 'record = make_calculation_record(calculation_id="market.simple_return")\n'


class TestScannerDetectsDrift:
    def test_clean_synthetic_repository_passes(self, tmp_path):
        root = build_repo(tmp_path, MINIMAL_ENTRY, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"], report["findings"]
        assert report["summary"]["identifiers_used_in_production"] == 1

    def test_phantom_identifier_detected(self, tmp_path):
        root = build_repo(
            tmp_path,
            MINIMAL_ENTRY,
            'record = make_calculation_record(calculation_id="market.sharpe_ratio")\n',
        )
        report = checker.check(root)
        assert report["ok"] is False
        assert "unknown_calculation_id" in codes(report)
        finding = next(f for f in report["findings"] if f["code"] == "unknown_calculation_id")
        assert finding["calculation_id"] == "market.sharpe_ratio"
        assert finding["sites"][0]["file"] == "apps/worker/src/vertex_worker/markets.py"

    def test_used_but_not_approved_detected(self, tmp_path):
        body = MINIMAL_ENTRY.replace(
            "runtime_status: APPROVED",
            "runtime_status: RESEARCH_ONLY\n    blocking_reason: synthetic gap",
        )
        root = build_repo(tmp_path, body, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"] is False
        assert "calculation_not_runtime_approved" in codes(report)

    def test_not_implemented_used_in_production_detected(self, tmp_path):
        body = (
            "  - id: probability.calibration\n"
            "    runtime_status: NOT_IMPLEMENTED\n"
            "    blocking_reason: no implementation exists\n"
        )
        root = build_repo(
            tmp_path,
            body,
            'record = make_calculation_record(calculation_id="probability.calibration")\n',
        )
        report = checker.check(root)
        assert report["ok"] is False
        assert "calculation_not_runtime_approved" in codes(report)

    @pytest.mark.parametrize(
        "field",
        [
            "spec_version",
            "method",
            "assumptions",
            "parameter_schema",
            "tolerances",
            "oracle",
            "criticality",
            "tests",
        ],
    )
    def test_missing_runtime_field_detected(self, tmp_path, field):
        body = (
            "\n".join(
                line
                for line in MINIMAL_ENTRY.splitlines()
                if not line.strip().startswith(f"{field}:")
            )
            + "\n"
        )
        root = build_repo(tmp_path, body, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"] is False
        missing = [f for f in report["findings"] if f["code"] == "missing_runtime_field"]
        assert [f["field"] for f in missing] == [field]

    def test_empty_runtime_field_detected(self, tmp_path):
        body = MINIMAL_ENTRY.replace('assumptions: ["synthetic fixture"]', "assumptions: []")
        root = build_repo(tmp_path, body, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"] is False
        assert "missing_runtime_field" in codes(report)

    def test_cited_test_file_that_does_not_exist_detected(self, tmp_path):
        body = MINIMAL_ENTRY.replace(
            "tests: [tests/test_market.py]", "tests: [tests/test_absent.py]"
        )
        root = build_repo(tmp_path, body, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"] is False
        finding = next(f for f in report["findings"] if f["code"] == "missing_test_file")
        assert finding["path"] == "tests/test_absent.py"

    def test_declared_implementation_file_that_does_not_exist_detected(self, tmp_path):
        body = (
            MINIMAL_ENTRY.rstrip("\n") + "\n    implementation: packages/absent.py::simple_return\n"
        )
        root = build_repo(tmp_path, body, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"] is False
        assert "missing_implementation_file" in codes(report)

    def test_missing_blocking_reason_detected(self, tmp_path):
        body = "  - id: options.gex_estimate\n    runtime_status: NOT_IMPLEMENTED\n"
        root = build_repo(tmp_path, body, "TOPIC = 'worker.refresh'\n")
        report = checker.check(root)
        assert report["ok"] is False
        assert "missing_blocking_reason" in codes(report)

    def test_invalid_runtime_status_detected(self, tmp_path):
        body = MINIMAL_ENTRY.replace("runtime_status: APPROVED", "runtime_status: MAYBE")
        root = build_repo(tmp_path, body, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"] is False
        assert "invalid_runtime_status" in codes(report)

    def test_duplicate_identifier_detected(self, tmp_path):
        root = build_repo(tmp_path, MINIMAL_ENTRY + MINIMAL_ENTRY, APPROVED_USAGE)
        report = checker.check(root)
        assert report["ok"] is False
        assert "duplicate_calculation_id" in codes(report)

    def test_unusable_registry_fails_closed(self, tmp_path):
        root = tmp_path / "empty"
        (root / "docs").mkdir(parents=True)
        with pytest.raises(checker.RegistryError):
            checker.check(root)


class TestScannerDetectionRules:
    def test_non_calculation_namespace_literal_is_not_a_finding(self, tmp_path):
        # A worker topic name outside the authority directories is not a
        # calculation identifier and must not be reported (documented rule).
        root = build_repo(
            tmp_path,
            MINIMAL_ENTRY,
            'TOPIC_PERFORMANCE_REFRESH = "performance.refresh"\n' + APPROVED_USAGE,
        )
        report = checker.check(root)
        assert report["ok"], report["findings"]

    def test_phantom_identifier_inside_authority_directory_detected(self, tmp_path):
        root = build_repo(tmp_path, MINIMAL_ENTRY, APPROVED_USAGE)
        authority = (
            root / "packages" / "python" / "vertex_core" / "src" / "vertex_core" / "calculations"
        )
        authority.mkdir(parents=True)
        (authority / "market.py").write_text(
            'def f(v):\n    return _finite_result(v, "market.sortino_ratio")\n', encoding="utf-8"
        )
        report = checker.check(root)
        assert report["ok"] is False
        finding = next(f for f in report["findings"] if f["code"] == "unknown_calculation_id")
        assert finding["calculation_id"] == "market.sortino_ratio"
        assert finding["sites"][0]["evidence"] == "core"

    def test_exact_registry_reference_outside_authority_counts_as_usage(self, tmp_path):
        body = MINIMAL_ENTRY.replace(
            "runtime_status: APPROVED",
            "runtime_status: RESEARCH_ONLY\n    blocking_reason: synthetic gap",
        )
        root = build_repo(tmp_path, body, 'IDS = ("market.simple_return",)\n')
        report = checker.check(root)
        assert report["ok"] is False
        finding = next(
            f for f in report["findings"] if f["code"] == "calculation_not_runtime_approved"
        )
        assert finding["sites"][0]["evidence"] == "reference"

    def test_calculation_statuses_subscript_is_a_record_site(self, tmp_path):
        root = build_repo(
            tmp_path,
            MINIMAL_ENTRY,
            'calculation_statuses["market.omega_ratio"] = OK\n',
        )
        report = checker.check(root)
        assert report["ok"] is False
        finding = next(f for f in report["findings"] if f["code"] == "unknown_calculation_id")
        assert finding["calculation_id"] == "market.omega_ratio"
        assert finding["sites"][0]["evidence"] == "record"
