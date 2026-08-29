"""Performance API (page 10): snapshot relay and reproducible export.

The API computes NO financial figure here: it relays the worker's
``performance/{portfolio_id}`` snapshot verbatim (or an honest empty state)
and renders the export as a PURE function of that snapshot — the daily
points as CSV plus a JSON manifest carrying the methods, versions and
input/result hashes of every :class:`CalculationRecord` the worker kept.

Reproducibility contract (tested): two export calls over the same snapshot
version return byte-identical bodies. The export injects NO request-time
clock — its ``as_of`` is the snapshot's own ``as_of`` (documented), so the
bytes change exactly when the underlying snapshot version changes.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Literal, Mapping, Optional

from vertex_api.portfolio import neutralize_csv_cell
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "EXPORT_SCHEMA_VERSION",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "SNAPSHOT_KIND_PERFORMANCE",
    "PerformanceExportResponse",
    "PerformanceSnapshotResponse",
    "build_performance_export",
    "build_performance_response",
]

SNAPSHOT_KIND_PERFORMANCE = "performance"
"""Snapshot kind published by the worker; the key is the portfolio id."""

EXPORT_SCHEMA_VERSION = "vertex.performance-export/1.0"

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"

_CSV_COLUMNS: tuple[str, ...] = (
    "trading_day",
    "at",
    "gross_value",
    "net_value",
    "cash",
    "position_value",
    "fees_cumulative",
    "lots_valued",
)

_METRIC_NAMES: tuple[str, ...] = (
    "twr_gross",
    "twr_net",
    "xirr_gross",
    "xirr_net",
    "drawdown_gross",
    "drawdown_net",
)


class PerformanceSnapshotResponse(ContractModel):
    """The last published performance snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted content VERBATIM (series, gates,
    gross/net metrics with their lineage, heatmap, coverage, population
    ``SYNTHETIC_MARKS_REAL_LEDGER`` shown as-is); the API computes no return,
    drawdown or ratio. ``state = "empty"`` means the worker never published
    for this portfolio: nothing is invented, ``reason`` says why.
    """

    state: Literal["ok", "empty"]
    portfolio_id: PositiveInt
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    content: Optional[FrozenStrMapping]
    reason: Optional[NonEmptyStr]


class PerformanceExportResponse(ContractModel):
    """Reproducible export: CSV of the daily points + JSON manifest.

    A pure function of one snapshot version — identical calls return
    identical bytes; ``as_of`` is the SNAPSHOT's instant, never the request
    clock (documented). The manifest carries method, engine version and
    input/result hashes for each kept calculation, plus the conventions and
    coverage, so the figures can be re-derived and audited independently.
    """

    schema_version: Literal["vertex.performance-export/1.0"]
    portfolio_id: PositiveInt
    snapshot_version: PositiveInt
    as_of: UtcDatetime
    csv: NonEmptyStr
    manifest: FrozenStrMapping


def build_performance_response(
    snapshot: Optional[CurrentSnapshot], *, portfolio_id: int
) -> PerformanceSnapshotResponse:
    """Relay the last performance snapshot verbatim, or the honest empty state."""
    if snapshot is None:
        return PerformanceSnapshotResponse(
            state="empty",
            portfolio_id=portfolio_id,
            snapshot_version=None,
            as_of=None,
            content=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )
    return PerformanceSnapshotResponse(
        state="ok",
        portfolio_id=portfolio_id,
        snapshot_version=snapshot.version,
        as_of=snapshot.as_of,
        content=dict(snapshot.content),
        reason=None,
    )


def _render_points_csv(content: Mapping[str, Any]) -> str:
    """Render the daily valuation points as CSV (formula-injection guarded)."""
    buffer = io.StringIO()
    buffer.write(f"# {EXPORT_SCHEMA_VERSION}\n")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)
    series = content.get("series")
    points = series.get("points", []) if isinstance(series, Mapping) else []
    for point in points:
        if not isinstance(point, Mapping):
            continue
        cells = [str(point.get(column, "")) for column in _CSV_COLUMNS]
        writer.writerow([neutralize_csv_cell(cell) for cell in cells])
    return buffer.getvalue()


def _calculation_manifest(content: Mapping[str, Any]) -> dict[str, Any]:
    """The lineage of every kept calculation: method, versions, hashes."""
    metrics = content.get("metrics")
    calculations: dict[str, Any] = {}
    if isinstance(metrics, Mapping):
        for name in _METRIC_NAMES:
            block = metrics.get(name)
            if not isinstance(block, Mapping):
                continue
            calculation = block.get("calculation")
            calculations[name] = {
                "status": block.get("status"),
                "reason": block.get("reason"),
                "calculation": dict(calculation)
                if isinstance(calculation, Mapping)
                else None,
            }
    heatmap = content.get("heatmap")
    if isinstance(heatmap, Mapping):
        derived = heatmap.get("derived_from_calculation")
        calculations["heatmap"] = {
            "status": heatmap.get("status"),
            "reason": heatmap.get("reason"),
            "derived_from_calculation": dict(derived)
            if isinstance(derived, Mapping)
            else None,
        }
    return calculations


def build_performance_export(
    snapshot: CurrentSnapshot, *, portfolio_id: int
) -> PerformanceExportResponse:
    """Build the reproducible export of ONE performance snapshot version.

    Pure presentation: every value is read from the persisted content; the
    manifest points back at the snapshot (kind, key, version, content hash)
    and lists each calculation's method/engine version/input hash/result
    hash so the export is auditable and byte-reproducible.
    """
    content = snapshot.content
    manifest: dict[str, Any] = {
        "snapshot": {
            "kind": snapshot.kind,
            "key": snapshot.key,
            "version": snapshot.version,
            "content_hash": snapshot.content_hash,
            "as_of": snapshot.as_of.isoformat(),
            "schema_version": content.get("schema_version"),
        },
        "population": content.get("population"),
        "population_components": content.get("population_components"),
        "currency": content.get("currency"),
        "engine_version": content.get("engine_version"),
        "lot_method": content.get("lot_method"),
        "conventions": content.get("conventions"),
        "calculations": _calculation_manifest(content),
        "coverage": content.get("coverage"),
        "as_of_note": (
            "as_of is the snapshot's own instant; the export injects no "
            "request-time clock, so identical snapshot versions export "
            "identical bytes"
        ),
    }
    return PerformanceExportResponse(
        schema_version=EXPORT_SCHEMA_VERSION,
        portfolio_id=portfolio_id,
        snapshot_version=snapshot.version,
        as_of=snapshot.as_of,
        csv=_render_points_csv(content),
        manifest=manifest,
    )
