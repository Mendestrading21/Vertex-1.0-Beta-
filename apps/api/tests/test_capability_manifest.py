"""Capability manifest parsing: complete, validated, deny-by-default."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vertex_api.capability_manifest import (
    DEFAULT_MANIFEST_PATH,
    CapabilityManifestError,
    load_capability_manifest,
)


def test_committed_manifest_loads_completely() -> None:
    manifest = load_capability_manifest()
    raw = yaml.safe_load(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    # Every declared entry is structured — the count is EXACT, nothing dropped.
    assert len(manifest.declarations) == len(raw["capabilities"])
    assert manifest.mode == "INFORMATION_ONLY"
    assert len(manifest.capability_ids) == len(manifest.declarations)
    for declaration in manifest.declarations:
        assert declaration.capability_id
        assert declaration.family
        assert declaration.declared_mode


def _write(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(CapabilityManifestError, match="not found"):
        load_capability_manifest(tmp_path / "absent.yaml")


def test_unknown_request_method_is_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "mode": "INFORMATION_ONLY",
            "capabilities": [{"id": "synthetic_cap", "request_method": "reqSomethingNew"}],
        },
    )
    with pytest.raises(CapabilityManifestError, match="request_method"):
        load_capability_manifest(path)


def test_duplicate_capability_id_is_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "mode": "INFORMATION_ONLY",
            "capabilities": [
                {"id": "synthetic_cap", "request_method": "reqMktData"},
                {"id": "synthetic_cap", "request_method": "reqMktData"},
            ],
        },
    )
    with pytest.raises(CapabilityManifestError, match="duplicate"):
        load_capability_manifest(path)


def test_description_and_default_status_are_relayed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "mode": "INFORMATION_ONLY",
            "capabilities": [
                {
                    "id": "synthetic_cap",
                    "request_method": "NONE",
                    "default_status": "UNSUPPORTED",
                    "description": "synthetic description",
                }
            ],
        },
    )
    manifest = load_capability_manifest(path)
    declaration = manifest.declarations[0]
    assert declaration.family == "not_provided_by_source"
    assert declaration.declared_mode == "UNSUPPORTED"
    assert declaration.description == "synthetic description"
