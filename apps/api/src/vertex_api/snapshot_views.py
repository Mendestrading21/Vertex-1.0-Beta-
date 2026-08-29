"""Pure builders of the snapshot-backed responses (no I/O, no computation).

These functions translate persisted snapshot content and the declared
capability manifest into the wire DTOs of ``vertex_api.schemas``. They are
presentation only:

- the attention response relays the worker's published items verbatim
  (population, coverage, provenance) and answers an HONEST empty state when
  no snapshot was ever published — never a 500, never invented items;
- the capabilities response crosses the full manifest with what was REALLY
  probed: a capability without any persisted probe is ``ERROR`` with reason
  ``NEVER_TESTED`` (fail-closed), a probe whose status is not a canonical
  ``SourceCapabilityStatus`` is ``ERROR`` with reason ``INVALID_STATUS``,
  and conflicting field statuses inside the winning probe collapse to
  ``ERROR`` with reason ``CONFLICTING_FIELD_STATUSES``.

No price, Greek, score, probability or verdict is ever computed here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from vertex_core.contracts.enums import SourceCapabilityStatus
from vertex_persistence.repository.snapshots import CurrentSnapshot

from vertex_api.capability_manifest import CapabilityDeclaration, CapabilityManifest
from vertex_api.schemas import (
    AttentionItem,
    AttentionSnapshotResponse,
    CapabilityStatusEntry,
    DbHealth,
    SnapshotHealth,
    SystemCapabilitiesResponse,
    SystemHealth,
    WorkerHealth,
)

__all__ = [
    "REASON_CONFLICTING_FIELD_STATUSES",
    "REASON_INVALID_STATUS",
    "REASON_NEVER_TESTED",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "SnapshotContentError",
    "build_attention_response",
    "build_capabilities_response",
    "build_system_health",
]

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"
REASON_NEVER_TESTED = "NEVER_TESTED"
REASON_INVALID_STATUS = "INVALID_STATUS"
REASON_CONFLICTING_FIELD_STATUSES = "CONFLICTING_FIELD_STATUSES"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class SnapshotContentError(ValueError):
    """Persisted snapshot content does not match its published schema."""


def _parse_utc(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SnapshotContentError(f"{field}: ISO-8601 string required")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotContentError(f"{field}: invalid ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise SnapshotContentError(f"{field}: naive datetime rejected")
    return parsed.astimezone(timezone.utc)


def _parse_utc_or_none(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return None
    return parsed.astimezone(timezone.utc)


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SnapshotContentError(f"{field}: mapping required")
    return value


def _require_list(value: Any, *, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise SnapshotContentError(f"{field}: list required")
    return value


def _str_tuple(value: Any, *, field: str) -> tuple[str, ...]:
    items = _require_list(value, field=field)
    result: list[str] = []
    for entry in items:
        if not isinstance(entry, str) or not entry:
            raise SnapshotContentError(f"{field}: non-empty strings required")
        result.append(entry)
    return tuple(result)


# ---------------------------------------------------------------------------
# Attention
# ---------------------------------------------------------------------------


def _attention_item(raw: Any, *, index: int) -> AttentionItem:
    item = _require_mapping(raw, field=f"items[{index}]")
    provenance = _require_mapping(item.get("provenance"), field=f"items[{index}].provenance")
    reasons = _str_tuple(
        item.get("relevance_reasons"), field=f"items[{index}].relevance_reasons"
    )
    synthetic = item.get("synthetic")
    if not isinstance(synthetic, bool):
        raise SnapshotContentError(f"items[{index}].synthetic: boolean required")
    return AttentionItem(
        id=item.get("item_id"),
        title=item.get("title"),
        sources=_str_tuple(provenance.get("sources"), field=f"items[{index}].provenance.sources"),
        rights=_str_tuple(provenance.get("rights"), field=f"items[{index}].provenance.rights"),
        relevance_reasons=reasons[:3],
        synthetic=synthetic,
        provenance=dict(provenance),
    )


def build_attention_response(
    snapshot: Optional[CurrentSnapshot],
) -> AttentionSnapshotResponse:
    """Render the last attention snapshot, or the honest empty state.

    Absence of a published snapshot is a NORMAL state (200): every
    snapshot-derived field stays ``None`` and ``reason`` explains why —
    nothing is invented, nothing degrades into a 500.
    """
    if snapshot is None:
        return AttentionSnapshotResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            coverage=None,
            items=(),
            rejected_count=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = _require_mapping(snapshot.content, field="content")
    items_raw = _require_list(content.get("items"), field="items")
    rejected_raw = _require_list(content.get("rejected"), field="rejected")
    population = content.get("population")
    if not isinstance(population, str) or not population:
        raise SnapshotContentError("population: non-empty string required")
    coverage = _require_mapping(content.get("coverage"), field="coverage")

    return AttentionSnapshotResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=population,
        coverage=dict(coverage),
        items=tuple(
            _attention_item(raw, index=index) for index, raw in enumerate(items_raw)
        ),
        rejected_count=len(rejected_raw),
        reason=None,
    )


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


def _probe_field_entries(
    snapshot: Optional[CurrentSnapshot],
) -> list[tuple[datetime, str, Mapping[str, Any]]]:
    """Flatten every probed field entry as (tested_at, capability_id, field).

    ``tested_at`` comes from the probe payload's own ``tested_at`` when it is
    a valid aware datetime, falling back to the probed source's ``as_of``;
    with neither parseable the entry sorts first (oldest) so any dated probe
    wins over it.
    """
    if snapshot is None:
        return []
    content = _require_mapping(snapshot.content, field="content")
    probed_sources = _require_list(content.get("probed_sources"), field="probed_sources")

    entries: list[tuple[datetime, str, Mapping[str, Any]]] = []
    for source_index, raw_source in enumerate(probed_sources):
        source_entry = _require_mapping(raw_source, field=f"probed_sources[{source_index}]")
        payload = _require_mapping(
            source_entry.get("snapshot"), field=f"probed_sources[{source_index}].snapshot"
        )
        tested_at = _parse_utc_or_none(payload.get("tested_at"))
        if tested_at is None:
            tested_at = _parse_utc_or_none(source_entry.get("as_of"))
        fields = payload.get("fields")
        if not isinstance(fields, list):
            continue
        for raw_field in fields:
            if not isinstance(raw_field, Mapping):
                continue
            capability_id = raw_field.get("capability_id")
            if not isinstance(capability_id, str) or not capability_id:
                continue
            entries.append((tested_at or _EPOCH, capability_id, raw_field))
    return entries


def _entry_for_declaration(
    declaration: CapabilityDeclaration,
    probes: Sequence[tuple[datetime, str, Mapping[str, Any]]],
) -> CapabilityStatusEntry:
    matching = [probe for probe in probes if probe[1] == declaration.capability_id]
    if not matching:
        return CapabilityStatusEntry(
            capability_id=declaration.capability_id,
            family=declaration.family,
            declared_mode=declaration.declared_mode,
            description=declaration.description,
            tested_status=SourceCapabilityStatus.ERROR,
            tested_at=None,
            reason=REASON_NEVER_TESTED,
        )

    latest_at = max(probe[0] for probe in matching)
    winning = [probe for probe in matching if probe[0] == latest_at]
    tested_at = None if latest_at == _EPOCH else latest_at

    statuses = {
        field.get("status") for _, _, field in winning
    }
    if len(statuses) > 1:
        return CapabilityStatusEntry(
            capability_id=declaration.capability_id,
            family=declaration.family,
            declared_mode=declaration.declared_mode,
            description=declaration.description,
            tested_status=SourceCapabilityStatus.ERROR,
            tested_at=tested_at,
            reason=REASON_CONFLICTING_FIELD_STATUSES,
        )

    raw_status = next(iter(statuses))
    try:
        status = SourceCapabilityStatus(raw_status)
    except ValueError:
        return CapabilityStatusEntry(
            capability_id=declaration.capability_id,
            family=declaration.family,
            declared_mode=declaration.declared_mode,
            description=declaration.description,
            tested_status=SourceCapabilityStatus.ERROR,
            tested_at=tested_at,
            reason=REASON_INVALID_STATUS,
        )

    reasons = {
        field.get("reason_code")
        for _, _, field in winning
        if isinstance(field.get("reason_code"), str) and field.get("reason_code")
    }
    reason = "; ".join(sorted(reasons)) if reasons else None
    return CapabilityStatusEntry(
        capability_id=declaration.capability_id,
        family=declaration.family,
        declared_mode=declaration.declared_mode,
        description=declaration.description,
        tested_status=status,
        tested_at=tested_at,
        reason=reason,
    )


def _snapshot_health(
    snapshot: Optional[CurrentSnapshot], *, now: datetime
) -> SnapshotHealth:
    if snapshot is None:
        return SnapshotHealth(present=False, version=None, as_of=None, age_seconds=None)
    return SnapshotHealth(
        present=True,
        version=snapshot.version,
        as_of=snapshot.as_of,
        age_seconds=int((now - snapshot.as_of).total_seconds()),
    )


def build_system_health(
    *,
    db_ok: bool,
    attention: Optional[CurrentSnapshot],
    capabilities: Optional[CurrentSnapshot],
    now: datetime,
) -> SystemHealth:
    """Assemble the health blocks; the worker block is an explicit proxy."""
    published = [s.as_of for s in (attention, capabilities) if s is not None]
    last_as_of = max(published) if published else None
    return SystemHealth(
        db=DbHealth(status="ok" if db_ok else "error"),
        attention_snapshot=_snapshot_health(attention, now=now),
        capabilities_snapshot=_snapshot_health(capabilities, now=now),
        worker=WorkerHealth(
            method="heartbeat_proxy",
            last_snapshot_as_of=last_as_of,
            age_seconds=(
                int((now - last_as_of).total_seconds()) if last_as_of is not None else None
            ),
        ),
    )


def build_capabilities_response(
    manifest: CapabilityManifest,
    *,
    snapshot: Optional[CurrentSnapshot],
    attention: Optional[CurrentSnapshot],
    db_ok: bool,
    now: datetime,
) -> SystemCapabilitiesResponse:
    """Cross the FULL declared manifest with the latest persisted probes."""
    probes = _probe_field_entries(snapshot)
    entries = tuple(
        _entry_for_declaration(declaration, probes)
        for declaration in sorted(manifest.declarations, key=lambda d: d.capability_id)
    )
    declared_ids = manifest.capability_ids
    unknown = tuple(
        sorted({capability_id for _, capability_id, _ in probes if capability_id not in declared_ids})
    )
    snapshot_as_of: Optional[datetime] = None
    if snapshot is not None:
        content = _require_mapping(snapshot.content, field="content")
        snapshot_as_of = _parse_utc(content.get("as_of"), field="as_of")
    return SystemCapabilitiesResponse(
        checked_at=now,
        snapshot_version=None if snapshot is None else snapshot.version,
        as_of=snapshot_as_of,
        total=len(entries),
        capabilities=entries,
        unknown_probed_capability_ids=unknown,
        health=build_system_health(
            db_ok=db_ok, attention=attention, capabilities=snapshot, now=now
        ),
    )
