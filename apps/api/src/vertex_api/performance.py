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

FAIL-CLOSED SHAPE CHECK (P1-G). "Verbatim relay" is not "unchecked relay".
This relay used to publish ``dict(snapshot.content)`` with no shape check at
all: the only constraint was pydantic's strict typing of the FIRST-LEVEL KEYS
of a ``FrozenStrMapping``, so ANY payload whose keys happened to be strings
was served ``200 state="ok"`` — a nested object where an instant belongs, a
string carrying NUL/BEL/ANSI escapes, a 5000-character value, an entirely
foreign schema. Presenting an unverified payload as a canonical performance
result is exactly what ``financial-safety.md`` forbids.

:func:`build_performance_response` and :func:`build_performance_export` now
validate the SHAPE of every field the worker publishes
(``vertex_worker.performance.build_performance_content``), at the same level
as the five ``vertex_api.snapshot_views`` relays and with the same
discipline: the refusal is a typed :class:`SnapshotContentError` naming its
FIELD PATH only, so no stored value reaches the response body or a log
record. Nothing is recomputed, corrected or defaulted: a content that does
not match its published schema is REFUSED, never repaired.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final, Literal

from vertex_api.freshness import closed_session_budget, evaluate_relay_freshness
from vertex_api.portfolio import neutralize_csv_cell
from vertex_api.snapshot_views import (
    SnapshotContentError,
    _optional_str,
    _parse_utc,
    _require_bool,
    _require_list,
    _require_mapping,
    _require_non_negative_int,
    _require_positive_int,
    _require_str,
    _wire_mapping,
    checked_relayed_content,
    require_snapshot_as_of,
)
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_core.data.freshness import get_freshness_policy
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "EXPORT_SCHEMA_VERSION",
    "PERFORMANCE_CONTENT_SCHEMA_VERSION",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "SNAPSHOT_KIND_PERFORMANCE",
    "PerformanceExportResponse",
    "PerformanceSnapshotResponse",
    "build_performance_export",
    "build_performance_response",
    "checked_performance_content",
]

SNAPSHOT_KIND_PERFORMANCE = "performance"
"""Snapshot kind published by the worker; the key is the portfolio id."""

EXPORT_SCHEMA_VERSION: Final = "vertex.performance-export/1.0"

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

PERFORMANCE_CONTENT_SCHEMA_VERSION = "vertex.performance/1.0"
"""The ONLY content schema this relay knows how to read.

Cross-process exchanges use a versioned contract (``architecture.md``): a
payload announcing another version — or none — is refused rather than read
with rules that no longer describe it. Raising the worker's version is
therefore an explicit, reviewed migration on both sides, never a silent
reinterpretation.
"""

_SERIES_STATUSES = frozenset({"OK", "INSUFFICIENT_DATA"})
"""Statuses ``vertex_worker.performance`` publishes for the value series."""

_BLOCK_STATUSES = frozenset({"OK", "INVALID", "INSUFFICIENT_DATA"})
"""Statuses of a metric block or of the heatmap. Deny-by-default: any other
label is refused rather than read as "not OK, hence harmless"."""

_POINT_DECIMAL_FIELDS: tuple[str, ...] = (
    "gross_value",
    "net_value",
    "cash",
    "position_value",
    "fees_cumulative",
)
"""Money fields of a daily point: DECIMAL TEXT, never a float on the wire
(``python.md``). The relay checks they are non-empty strings; it never parses,
rounds or recomputes them."""

_COVERAGE_COUNTS: tuple[str, ...] = (
    "days_with_close",
    "days_valued",
    "days_excluded",
    "days_before_first_ledger_event",
    "events_considered",
    "external_cashflows",
    "observations_considered",
)


def _status_block(
    value: Any, *, field: str, allowed: frozenset[str], extra_lists: tuple[str, ...] = ()
) -> Mapping[str, Any]:
    """A worker result block: canonical status, optional reason, no invention."""
    block = _require_mapping(value, field=field)
    status = block.get("status")
    if status not in allowed:
        raise SnapshotContentError(
            f"{field}.status: canonical status required", field=f"{field}.status"
        )
    _optional_str(block.get("reason"), field=f"{field}.reason")
    for name in extra_lists:
        _require_list(block.get(name), field=f"{field}.{name}")
    return block


def _optional_wire_mapping(value: Any, *, field: str) -> None:
    if value is not None:
        _wire_mapping(value, field=field)


def _checked_point(raw: Any, *, field: str) -> None:
    """One daily valuation point, exactly as the worker publishes it."""
    point = _require_mapping(raw, field=field)
    _require_str(point.get("trading_day"), field=f"{field}.trading_day")
    _parse_utc(point.get("at"), field=f"{field}.at")
    for name in _POINT_DECIMAL_FIELDS:
        _require_str(point.get(name), field=f"{field}.{name}")
    _require_non_negative_int(point.get("lots_valued"), field=f"{field}.lots_valued")


def _checked_series(value: Any) -> int:
    """The value series; returns how many points are really published."""
    series = _status_block(
        value, field="series", allowed=_SERIES_STATUSES, extra_lists=("excluded_days",)
    )
    points = _require_list(series.get("points"), field="series.points")
    for index, raw in enumerate(points):
        _checked_point(raw, field=f"series.points[{index}]")
    for index, raw in enumerate(series["excluded_days"]):
        _wire_mapping(raw, field=f"series.excluded_days[{index}]")
    return len(points)


def _checked_coverage(value: Any, *, points: int, excluded_days: int) -> None:
    """Coverage counts — and their agreement with the published series.

    A coverage block contradicting the payload it describes (a truncated
    series presented under a full count) is a defect, not a display detail:
    the relay refuses it instead of showing a total nothing supports. This is
    a CONSISTENCY check, never a recomputation — no ratio, return or value is
    derived here.
    """
    coverage = _require_mapping(value, field="coverage")
    for name in _COVERAGE_COUNTS:
        _require_non_negative_int(coverage.get(name), field=f"coverage.{name}")
    _optional_str(coverage.get("coverage_ratio"), field="coverage.coverage_ratio")
    _require_bool(
        coverage.get("observations_truncated"), field="coverage.observations_truncated"
    )
    rejected = _require_list(
        coverage.get("rejected_records"), field="coverage.rejected_records"
    )
    for index, raw in enumerate(rejected):
        _wire_mapping(raw, field=f"coverage.rejected_records[{index}]")
    if coverage["days_valued"] != points:
        raise SnapshotContentError(
            "coverage.days_valued: contradicts the number of published points",
            field="coverage.days_valued",
        )
    if coverage["days_excluded"] != excluded_days:
        raise SnapshotContentError(
            "coverage.days_excluded: contradicts the published excluded days",
            field="coverage.days_excluded",
        )
    if coverage["days_with_close"] != points + excluded_days:
        raise SnapshotContentError(
            "coverage.days_with_close: contradicts the published series",
            field="coverage.days_with_close",
        )


def checked_performance_content(content: Any) -> Mapping[str, Any]:
    """Fail-closed shape check of ONE persisted performance content.

    Two contracts, both fail-closed, neither replacing the other:

    * the CLASS contract (:func:`checked_relayed_content`) — every string leaf
      must match the shape of its kind: a decimal is a decimal, a nature label
      belongs to a closed set, prose is bounded and control-free. Without it
      this relay served ``strike``-like values, and the ``population`` label
      that separates SYNTHETIC from real, as arbitrary 5000-character strings;
    * the STRUCTURE contract below — the fields the worker publishes are all
      present, consistent with one another, and in the expected arrangement.

    The content is returned UNCHANGED — the relay stays verbatim. Any deviation
    raises a :class:`SnapshotContentError` naming its field path only; no value,
    no return, no ratio is ever recomputed, corrected or defaulted here.
    """
    checked_relayed_content(content)
    mapping = _wire_mapping(content, field="content")
    schema_version = _require_str(
        mapping.get("schema_version"), field="schema_version"
    )
    if schema_version != PERFORMANCE_CONTENT_SCHEMA_VERSION:
        raise SnapshotContentError(
            "schema_version: this relay reads "
            f"{PERFORMANCE_CONTENT_SCHEMA_VERSION} only",
            field="schema_version",
        )
    _parse_utc(mapping.get("as_of"), field="as_of")
    _require_str(mapping.get("engine_version"), field="engine_version")

    portfolio = _require_mapping(mapping.get("portfolio"), field="portfolio")
    _require_positive_int(portfolio.get("id"), field="portfolio.id")
    _require_str(portfolio.get("name"), field="portfolio.name")
    _require_str(portfolio.get("base_currency"), field="portfolio.base_currency")

    _require_str(mapping.get("population"), field="population")
    _wire_mapping(mapping.get("population_components"), field="population_components")
    # ``currency`` is legitimately absent when no series could be valued: an
    # absent currency and an empty one are NOT the same thing.
    _optional_str(mapping.get("currency"), field="currency")
    _require_str(mapping.get("lot_method"), field="lot_method")
    _wire_mapping(mapping.get("conventions"), field="conventions")

    points = _checked_series(mapping.get("series"))
    excluded_days = len(mapping["series"]["excluded_days"])

    flows = _require_list(
        mapping.get("external_cashflows"), field="external_cashflows"
    )
    for index, raw in enumerate(flows):
        _wire_mapping(raw, field=f"external_cashflows[{index}]")

    metrics = _require_mapping(mapping.get("metrics"), field="metrics")
    for name in _METRIC_NAMES:
        block = _status_block(
            metrics.get(name), field=f"metrics.{name}", allowed=_BLOCK_STATUSES
        )
        _optional_wire_mapping(
            block.get("calculation"), field=f"metrics.{name}.calculation"
        )

    heatmap = _status_block(
        mapping.get("heatmap"),
        field="heatmap",
        allowed=_BLOCK_STATUSES,
        extra_lists=("months",),
    )
    _optional_wire_mapping(
        heatmap.get("derived_from_calculation"),
        field="heatmap.derived_from_calculation",
    )
    for index, raw in enumerate(heatmap["months"]):
        _wire_mapping(raw, field=f"heatmap.months[{index}]")

    _checked_coverage(
        mapping.get("coverage"), points=points, excluded_days=excluded_days
    )
    return mapping


class PerformanceSnapshotResponse(ContractModel):
    """The last published performance snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted content VERBATIM (series, gates,
    gross/net metrics with their lineage, heatmap, coverage, population
    ``SYNTHETIC_MARKS_REAL_LEDGER`` shown as-is); the API computes no return,
    drawdown or ratio. ``state = "empty"`` means the worker never published
    for this portfolio: nothing is invented, ``reason`` says why.

    ``state = "stale"`` relaie le MÊME contenu, mais dit que l'instantané a
    dépassé le budget de séance fermée de ``daily_bar`` : le worker n'a rien
    publié de plus récent. ``age_seconds`` est publié dans TOUS les états
    datables — son absence faisait passer une performance de trois jours pour
    une performance d'une minute.
    """

    state: Literal["ok", "stale", "empty"]
    portfolio_id: PositiveInt
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    content: FrozenStrMapping | None
    reason: NonEmptyStr | None


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


#: La performance est valorisée par ``load_all_daily_quote_records`` croisé au
#: journal déclaré : la marque LA PLUS FRAÎCHE dont elle peut être issue est
#: une cotation quotidienne. Le choix se LIT dans `vertex_worker.performance`.
PERFORMANCE_FRESHNESS_POLICY = "daily_bar"

_FRESHNESS_POLICY = get_freshness_policy(PERFORMANCE_FRESHNESS_POLICY)

PERFORMANCE_MAX_AGE = closed_session_budget(_FRESHNESS_POLICY)


def build_performance_response(
    snapshot: CurrentSnapshot | None, *, portfolio_id: int, now: datetime
) -> PerformanceSnapshotResponse:
    """Relay the last performance snapshot verbatim, or the honest empty state.

    Verbatim, but never unchecked (P1-G): the persisted content is validated
    fail-closed by :func:`checked_performance_content` and relayed UNCHANGED.
    A content that does not match its published schema raises a typed
    :class:`SnapshotContentError` — it is never served as ``state = "ok"``.
    """
    if snapshot is None:
        return PerformanceSnapshotResponse(
            state="empty",
            portfolio_id=portfolio_id,
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
            content=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )
    freshness = evaluate_relay_freshness(
        require_snapshot_as_of(snapshot), now=now, policy=_FRESHNESS_POLICY
    )
    return PerformanceSnapshotResponse(
        state="stale" if freshness.stale else "ok",
        portfolio_id=portfolio_id,
        snapshot_version=snapshot.version,
        as_of=snapshot.as_of,
        age_seconds=freshness.age_seconds,
        content=dict(checked_performance_content(snapshot.content)),
        reason=freshness.stale_reason,
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

    The exported content is validated fail-closed first (P1-G): an export is
    a relay too, and an unverified payload must not leave the system as an
    auditable artefact.
    """
    content = checked_performance_content(snapshot.content)
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
