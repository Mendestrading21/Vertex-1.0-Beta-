"""Declared IBKR market-data capability manifest (read once at startup).

``manifests/ibkr-market-data-capabilities.yaml`` is the single declaration of
every market-data capability the edge probe may test. This module parses that
YAML into an immutable, validated structure the API can cross with the latest
persisted ``capabilities`` snapshot (what was REALLY probed).

The manifest carries no explicit ``family`` field, so the family is derived
deterministically from the declared ``request_method`` (the mechanism family
of the capability); an undeclared method fails the load (deny by default,
never a silent guess). ``description`` is relayed only when the manifest
carries one — an absent description stays ``None``.

``declared_mode`` is the capability's own ``default_status`` when declared
(e.g. ``UNSUPPORTED`` for capabilities the TWS API does not provide),
otherwise the manifest-level ``mode`` (``INFORMATION_ONLY``). Nothing here
performs any probe, any IBKR call or any financial computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml

__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "CapabilityDeclaration",
    "CapabilityManifest",
    "CapabilityManifestError",
    "FAMILY_BY_REQUEST_METHOD",
    "load_capability_manifest",
]

_REPO_ROOT = Path(__file__).resolve().parents[4]

DEFAULT_MANIFEST_PATH = _REPO_ROOT / "manifests" / "ibkr-market-data-capabilities.yaml"

FAMILY_BY_REQUEST_METHOD: Mapping[str, str] = {
    "reqSecDefOptParams": "contract_reference",
    "reqMktData": "market_data",
    "reqHistoricalData": "historical_data",
    "NONE": "not_provided_by_source",
}
"""Deterministic family per declared request method (deny-by-default)."""


class CapabilityManifestError(RuntimeError):
    """The capability manifest is missing, unreadable or structurally invalid."""


@dataclass(frozen=True)
class CapabilityDeclaration:
    """One declared capability: identifier, family, mode, optional description."""

    capability_id: str
    family: str
    declared_mode: str
    description: Optional[str]


@dataclass(frozen=True)
class CapabilityManifest:
    """The full, immutable set of declared capabilities (order preserved)."""

    schema_version: int
    mode: str
    declarations: tuple[CapabilityDeclaration, ...]

    @property
    def capability_ids(self) -> frozenset[str]:
        return frozenset(d.capability_id for d in self.declarations)


def _require_str(document: Mapping[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityManifestError(f"manifest field {key!r}: non-empty string required")
    return value


def _declaration_from_entry(entry: Any) -> CapabilityDeclaration:
    if not isinstance(entry, Mapping):
        raise CapabilityManifestError("capabilities[]: each entry must be a mapping")
    capability_id = entry.get("id")
    if not isinstance(capability_id, str) or not capability_id.strip():
        raise CapabilityManifestError("capabilities[].id: non-empty string required")

    request_method = entry.get("request_method")
    if not isinstance(request_method, str) or request_method not in FAMILY_BY_REQUEST_METHOD:
        raise CapabilityManifestError(
            f"capability {capability_id!r}: undeclared request_method "
            f"{request_method!r} (deny by default — extend FAMILY_BY_REQUEST_METHOD "
            "deliberately, never guess a family)"
        )

    default_status = entry.get("default_status")
    if default_status is not None and (
        not isinstance(default_status, str) or not default_status.strip()
    ):
        raise CapabilityManifestError(
            f"capability {capability_id!r}: default_status must be a non-empty string"
        )

    description = entry.get("description")
    if description is not None and (not isinstance(description, str) or not description.strip()):
        raise CapabilityManifestError(
            f"capability {capability_id!r}: description must be a non-empty string when present"
        )

    return CapabilityDeclaration(
        capability_id=capability_id,
        family=FAMILY_BY_REQUEST_METHOD[request_method],
        # Filled by the caller when default_status is absent (manifest mode).
        declared_mode=default_status if default_status is not None else "",
        description=description,
    )


def load_capability_manifest(path: Optional[Path] = None) -> CapabilityManifest:
    """Parse and validate the manifest; any structural defect fails the load."""
    manifest_path = DEFAULT_MANIFEST_PATH if path is None else path
    if not manifest_path.is_file():
        raise CapabilityManifestError(f"capability manifest not found: {manifest_path}")
    try:
        document = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CapabilityManifestError(f"capability manifest is not valid YAML: {exc}") from exc
    if not isinstance(document, Mapping):
        raise CapabilityManifestError("capability manifest: top-level mapping required")

    schema_version = document.get("schema_version")
    if not isinstance(schema_version, int):
        raise CapabilityManifestError("manifest field 'schema_version': integer required")
    mode = _require_str(document, "mode")

    raw_capabilities = document.get("capabilities")
    if not isinstance(raw_capabilities, list) or not raw_capabilities:
        raise CapabilityManifestError("manifest field 'capabilities': non-empty list required")

    declarations: list[CapabilityDeclaration] = []
    seen: set[str] = set()
    for entry in raw_capabilities:
        declaration = _declaration_from_entry(entry)
        if declaration.capability_id in seen:
            raise CapabilityManifestError(
                f"duplicate capability id in manifest: {declaration.capability_id!r}"
            )
        seen.add(declaration.capability_id)
        if not declaration.declared_mode:
            declaration = CapabilityDeclaration(
                capability_id=declaration.capability_id,
                family=declaration.family,
                declared_mode=mode,
                description=declaration.description,
            )
        declarations.append(declaration)

    return CapabilityManifest(
        schema_version=schema_version, mode=mode, declarations=tuple(declarations)
    )
