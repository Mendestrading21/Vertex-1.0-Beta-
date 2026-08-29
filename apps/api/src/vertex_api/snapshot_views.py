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
    AnalysisResponse,
    AttentionItem,
    AttentionSnapshotResponse,
    CapabilityStatusEntry,
    DbHealth,
    MarketsBreadth,
    MarketsCoverage,
    MarketsDiscardedTicker,
    MarketsOverviewResponse,
    MarketsRejectedRecord,
    MarketsSector,
    MarketsTicker,
    OptionChainContract,
    OptionChainExpiration,
    OptionChainResponse,
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
    "build_analysis_response",
    "build_attention_response",
    "build_capabilities_response",
    "build_markets_overview_response",
    "build_option_chain_response",
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
# Markets overview
# ---------------------------------------------------------------------------


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SnapshotContentError(f"{field}: non-empty string required")
    return value


def _optional_str(value: Any, *, field: str) -> Optional[str]:
    if value is None:
        return None
    return _require_str(value, field=field)


def _require_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotContentError(f"{field}: integer required")
    return value


def _require_bool(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise SnapshotContentError(f"{field}: boolean required")
    return value


def _markets_ticker(raw: Any, *, field: str) -> MarketsTicker:
    entry = _require_mapping(raw, field=field)
    return MarketsTicker(
        ticker=_require_str(entry.get("ticker"), field=f"{field}.ticker"),
        sector=_require_str(entry.get("sector"), field=f"{field}.sector"),
        trading_day=_require_str(entry.get("trading_day"), field=f"{field}.trading_day"),
        previous_trading_day=_require_str(
            entry.get("previous_trading_day"), field=f"{field}.previous_trading_day"
        ),
        last_close=_require_str(entry.get("last_close"), field=f"{field}.last_close"),
        previous_close=_require_str(
            entry.get("previous_close"), field=f"{field}.previous_close"
        ),
        currency=_optional_str(entry.get("currency"), field=f"{field}.currency"),
        return_1d=_require_str(entry.get("return_1d"), field=f"{field}.return_1d"),
        return_1d_pct=_require_str(
            entry.get("return_1d_pct"), field=f"{field}.return_1d_pct"
        ),
        weight_in_sector=_require_str(
            entry.get("weight_in_sector"), field=f"{field}.weight_in_sector"
        ),
        weight_in_sector_pct=_require_str(
            entry.get("weight_in_sector_pct"), field=f"{field}.weight_in_sector_pct"
        ),
        weight_global=_require_str(
            entry.get("weight_global"), field=f"{field}.weight_global"
        ),
        weight_global_pct=_require_str(
            entry.get("weight_global_pct"), field=f"{field}.weight_global_pct"
        ),
        quality=_require_str(entry.get("quality"), field=f"{field}.quality"),
        synthetic=_require_bool(entry.get("synthetic"), field=f"{field}.synthetic"),
        calculation=dict(
            _require_mapping(entry.get("calculation"), field=f"{field}.calculation")
        ),
    )


def _markets_sector(raw: Any, *, index: int) -> MarketsSector:
    field = f"sectors[{index}]"
    entry = _require_mapping(raw, field=field)
    tickers_raw = _require_list(entry.get("tickers"), field=f"{field}.tickers")
    return MarketsSector(
        sector=_require_str(entry.get("sector"), field=f"{field}.sector"),
        label=_require_str(entry.get("label"), field=f"{field}.label"),
        declared_count=_require_int(
            entry.get("declared_count"), field=f"{field}.declared_count"
        ),
        covered_count=_require_int(
            entry.get("covered_count"), field=f"{field}.covered_count"
        ),
        tickers=tuple(
            _markets_ticker(ticker, field=f"{field}.tickers[{i}]")
            for i, ticker in enumerate(tickers_raw)
        ),
    )


def _markets_breadth(raw: Any) -> MarketsBreadth:
    entry = _require_mapping(raw, field="breadth")
    status = entry.get("status")
    if status not in ("OK", "INVALID"):
        raise SnapshotContentError("breadth.status: 'OK' or 'INVALID' required")
    calculation = entry.get("calculation")
    return MarketsBreadth(
        status=status,
        reason=_optional_str(entry.get("reason"), field="breadth.reason"),
        value=_optional_str(entry.get("value"), field="breadth.value"),
        value_pct=_optional_str(entry.get("value_pct"), field="breadth.value_pct"),
        above_count=_require_int(entry.get("above_count"), field="breadth.above_count"),
        covered_count=_require_int(
            entry.get("covered_count"), field="breadth.covered_count"
        ),
        universe_size=_require_int(
            entry.get("universe_size"), field="breadth.universe_size"
        ),
        coverage_pct=_require_str(
            entry.get("coverage_pct"), field="breadth.coverage_pct"
        ),
        coverage_threshold=_require_str(
            entry.get("coverage_threshold"), field="breadth.coverage_threshold"
        ),
        coverage_threshold_pct=_require_str(
            entry.get("coverage_threshold_pct"), field="breadth.coverage_threshold_pct"
        ),
        calculation=(
            None
            if calculation is None
            else dict(_require_mapping(calculation, field="breadth.calculation"))
        ),
    )


def _markets_coverage(raw: Any) -> MarketsCoverage:
    entry = _require_mapping(raw, field="coverage")
    discarded_raw = _require_list(
        entry.get("discarded_tickers"), field="coverage.discarded_tickers"
    )
    rejected_raw = _require_list(
        entry.get("rejected_records"), field="coverage.rejected_records"
    )
    discarded = []
    for i, item in enumerate(discarded_raw):
        mapping = _require_mapping(item, field=f"coverage.discarded_tickers[{i}]")
        discarded.append(
            MarketsDiscardedTicker(
                ticker=_require_str(
                    mapping.get("ticker"), field=f"coverage.discarded_tickers[{i}].ticker"
                ),
                reason=_require_str(
                    mapping.get("reason"), field=f"coverage.discarded_tickers[{i}].reason"
                ),
            )
        )
    rejected = []
    for i, item in enumerate(rejected_raw):
        mapping = _require_mapping(item, field=f"coverage.rejected_records[{i}]")
        rejected.append(
            MarketsRejectedRecord(
                event_id=_require_str(
                    mapping.get("event_id"), field=f"coverage.rejected_records[{i}].event_id"
                ),
                reason=_require_str(
                    mapping.get("reason"), field=f"coverage.rejected_records[{i}].reason"
                ),
            )
        )
    return MarketsCoverage(
        expected=_require_int(entry.get("expected"), field="coverage.expected"),
        received=_require_int(entry.get("received"), field="coverage.received"),
        covered=_require_int(entry.get("covered"), field="coverage.covered"),
        discarded=_require_int(entry.get("discarded"), field="coverage.discarded"),
        discarded_tickers=tuple(discarded),
        rejected_records=tuple(rejected),
        observations_considered=_require_int(
            entry.get("observations_considered"),
            field="coverage.observations_considered",
        ),
        lookback_seconds=_require_int(
            entry.get("lookback_seconds"), field="coverage.lookback_seconds"
        ),
    )


def build_markets_overview_response(
    snapshot: Optional[CurrentSnapshot],
) -> MarketsOverviewResponse:
    """Render the last markets overview snapshot, or the honest empty state.

    Presentation only: the persisted content is validated fail-closed into
    the wire DTOs and relayed VERBATIM — no price, return, weight, breadth or
    percentage is ever recomputed here. Absence of a published snapshot is a
    NORMAL state (200 with ``state = "empty"``), never a 500 and never an
    invented zero.
    """
    if snapshot is None:
        return MarketsOverviewResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            data_state=None,
            unit=None,
            display_unit=None,
            engine_version=None,
            conclusion=None,
            sectors=(),
            breadth=None,
            coverage=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = _require_mapping(snapshot.content, field="content")
    sectors_raw = _require_list(content.get("sectors"), field="sectors")
    data_state = content.get("data_state")
    if data_state not in ("ok", "partial", "stale"):
        raise SnapshotContentError("data_state: 'ok', 'partial' or 'stale' required")

    return MarketsOverviewResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=_require_str(content.get("population"), field="population"),
        data_state=data_state,
        unit=_require_str(content.get("unit"), field="unit"),
        display_unit=_require_str(content.get("display_unit"), field="display_unit"),
        engine_version=_require_str(
            content.get("engine_version"), field="engine_version"
        ),
        conclusion=_require_str(content.get("conclusion"), field="conclusion"),
        sectors=tuple(
            _markets_sector(raw, index=index) for index, raw in enumerate(sectors_raw)
        ),
        breadth=_markets_breadth(content.get("breadth")),
        coverage=_markets_coverage(content.get("coverage")),
        reason=None,
    )


# ---------------------------------------------------------------------------
# Analysis dossier
# ---------------------------------------------------------------------------

_ADVICE_STATUSES = frozenset(
    {"BLOCKED", "INSUFFICIENT_DATA", "OBSERVE", "REVIEW", "QUALIFIED"}
)
_GATE_STATUSES = frozenset({"PASS", "DEGRADE", "BLOCK"})


def _checked_advice(value: Any) -> Mapping[str, Any]:
    """Fail-closed shape check of the published ``AdviceResult`` mapping.

    The API never recomputes a verdict; it only refuses to relay a snapshot
    whose advice block does not look like the canonical contract (missing
    id, unknown status, gate without a reason code).
    """
    advice = _require_mapping(value, field="advice")
    _require_str(advice.get("advice_id"), field="advice.advice_id")
    _require_str(advice.get("engine_version"), field="advice.engine_version")
    status = advice.get("status")
    if status not in _ADVICE_STATUSES:
        raise SnapshotContentError("advice.status: canonical AdviceStatus required")
    gates = _require_list(advice.get("gates"), field="advice.gates")
    for index, raw_gate in enumerate(gates):
        gate = _require_mapping(raw_gate, field=f"advice.gates[{index}]")
        _require_str(gate.get("gate_id"), field=f"advice.gates[{index}].gate_id")
        _require_str(
            gate.get("reason_code"), field=f"advice.gates[{index}].reason_code"
        )
        if gate.get("status") not in _GATE_STATUSES:
            raise SnapshotContentError(
                f"advice.gates[{index}].status: PASS/DEGRADE/BLOCK required"
            )
    return advice


def build_analysis_response(
    snapshot: Optional[CurrentSnapshot], *, instrument: str
) -> AnalysisResponse:
    """Render the last analysis dossier, or the honest empty state.

    Presentation only: the persisted content is shape-checked fail-closed
    and relayed VERBATIM — no bar, cluster, scenario value or verdict is
    ever recomputed here. Absence of a published snapshot is a NORMAL state
    (200 with ``state = "empty"``), never a 500 and never an invented
    dossier.
    """
    if snapshot is None:
        return AnalysisResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            instrument=instrument,
            engine_version=None,
            bars=None,
            evidence=None,
            scenarios=None,
            advice=None,
            coverage=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = _require_mapping(snapshot.content, field="content")
    published_instrument = _require_str(content.get("instrument"), field="instrument")
    if published_instrument != instrument:
        raise SnapshotContentError(
            "instrument: snapshot content does not match the requested key"
        )
    bars = _require_mapping(content.get("bars"), field="bars")
    scenarios = _require_mapping(content.get("scenarios"), field="scenarios")
    scenario_status = scenarios.get("status")
    if scenario_status not in ("OK", "ABSENT"):
        raise SnapshotContentError("scenarios.status: 'OK' or 'ABSENT' required")
    if scenario_status == "OK" and scenarios.get("value_nature") != "THEORETICAL":
        raise SnapshotContentError(
            "scenarios.value_nature: 'THEORETICAL' required on a computed grid"
        )
    if scenario_status == "ABSENT":
        _require_str(scenarios.get("reason"), field="scenarios.reason")
    return AnalysisResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=_require_str(content.get("population"), field="population"),
        instrument=published_instrument,
        engine_version=_require_str(
            content.get("engine_version"), field="engine_version"
        ),
        bars=dict(bars),
        evidence=dict(_require_mapping(content.get("evidence"), field="evidence")),
        scenarios=dict(scenarios),
        advice=dict(_checked_advice(content.get("advice"))),
        coverage=dict(_require_mapping(content.get("coverage"), field="coverage")),
        reason=None,
    )


# ---------------------------------------------------------------------------
# Option chain
# ---------------------------------------------------------------------------


def _optional_non_negative_int(value: Any, *, field: str) -> Optional[int]:
    if value is None:
        return None
    result = _require_int(value, field=field)
    if result < 0:
        raise SnapshotContentError(f"{field}: non-negative integer required")
    return result


def _status_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    """A worker result block: a mapping carrying a non-empty ``status``."""
    mapping = _require_mapping(value, field=field)
    status = mapping.get("status")
    if not isinstance(status, str) or not status:
        raise SnapshotContentError(f"{field}.status: non-empty string required")
    return mapping


def _option_contract(raw: Any, *, field: str) -> OptionChainContract:
    entry = _require_mapping(raw, field=field)
    con_id = entry.get("con_id")
    if con_id is not None:
        con_id = _require_int(con_id, field=f"{field}.con_id")
    right = entry.get("right")
    if right is not None and right not in ("CALL", "PUT"):
        raise SnapshotContentError(f"{field}.right: 'CALL', 'PUT' or null required")
    return OptionChainContract(
        con_id=con_id,
        strike=_optional_str(entry.get("strike"), field=f"{field}.strike"),
        right=right,
        expiration=_require_str(entry.get("expiration"), field=f"{field}.expiration"),
        trading_class=_require_str(
            entry.get("trading_class"), field=f"{field}.trading_class"
        ),
        multiplier=_require_int(entry.get("multiplier"), field=f"{field}.multiplier"),
        currency=_require_str(entry.get("currency"), field=f"{field}.currency"),
        exchange=_require_str(entry.get("exchange"), field=f"{field}.exchange"),
        style=_require_str(entry.get("style"), field=f"{field}.style"),
        settlement=_require_str(entry.get("settlement"), field=f"{field}.settlement"),
        quote=dict(_status_mapping(entry.get("quote"), field=f"{field}.quote")),
        volume=_optional_non_negative_int(entry.get("volume"), field=f"{field}.volume"),
        open_interest=_optional_non_negative_int(
            entry.get("open_interest"), field=f"{field}.open_interest"
        ),
        open_interest_status=_optional_str(
            entry.get("open_interest_status"), field=f"{field}.open_interest_status"
        ),
        iv=dict(_status_mapping(entry.get("iv"), field=f"{field}.iv")),
        greeks=dict(_status_mapping(entry.get("greeks"), field=f"{field}.greeks")),
        synthetic=_require_bool(entry.get("synthetic"), field=f"{field}.synthetic"),
    )


def _option_expiration(raw: Any, *, index: int) -> OptionChainExpiration:
    field = f"expirations[{index}]"
    entry = _require_mapping(raw, field=field)
    contracts_raw = _require_list(entry.get("contracts"), field=f"{field}.contracts")
    return OptionChainExpiration(
        expiration=_require_str(entry.get("expiration"), field=f"{field}.expiration"),
        trading_class=_require_str(
            entry.get("trading_class"), field=f"{field}.trading_class"
        ),
        exchange=_require_str(entry.get("exchange"), field=f"{field}.exchange"),
        style=_require_str(entry.get("style"), field=f"{field}.style"),
        settlement=_require_str(entry.get("settlement"), field=f"{field}.settlement"),
        multiplier=_require_int(entry.get("multiplier"), field=f"{field}.multiplier"),
        currency=_require_str(entry.get("currency"), field=f"{field}.currency"),
        maturity_years=_require_str(
            entry.get("maturity_years"), field=f"{field}.maturity_years"
        ),
        quality=_require_str(entry.get("quality"), field=f"{field}.quality"),
        source_event_id=_require_str(
            entry.get("source_event_id"), field=f"{field}.source_event_id"
        ),
        contracts=tuple(
            _option_contract(contract, field=f"{field}.contracts[{i}]")
            for i, contract in enumerate(contracts_raw)
        ),
        coverage=dict(
            _require_mapping(entry.get("coverage"), field=f"{field}.coverage")
        ),
    )


def build_option_chain_response(
    snapshot: Optional[CurrentSnapshot], *, underlying: str
) -> OptionChainResponse:
    """Render the last option-chain snapshot, or the honest empty state.

    Presentation only: the persisted content is validated fail-closed into
    the wire DTOs and relayed VERBATIM — no quote, IV, Greek or coverage
    figure is ever recomputed here. Absence of a published snapshot is a
    NORMAL state (200 with ``state = "empty"``), never a 500 and never an
    invented chain.
    """
    if snapshot is None:
        return OptionChainResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            underlying=underlying,
            engine_version=None,
            value_nature=None,
            spot=None,
            assumptions=None,
            expirations=(),
            row_budget=None,
            coverage=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = _require_mapping(snapshot.content, field="content")
    published_underlying = _require_str(content.get("underlying"), field="underlying")
    if published_underlying != underlying:
        raise SnapshotContentError(
            "underlying: snapshot content does not match the requested key"
        )
    value_nature = content.get("value_nature")
    if value_nature != "THEORETICAL":
        raise SnapshotContentError("value_nature: 'THEORETICAL' required")
    expirations_raw = _require_list(content.get("expirations"), field="expirations")
    spot = content.get("spot")
    assumptions = content.get("assumptions")
    return OptionChainResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=_require_str(content.get("population"), field="population"),
        underlying=published_underlying,
        engine_version=_require_str(
            content.get("engine_version"), field="engine_version"
        ),
        value_nature="THEORETICAL",
        spot=None if spot is None else dict(_require_mapping(spot, field="spot")),
        assumptions=(
            None
            if assumptions is None
            else dict(_require_mapping(assumptions, field="assumptions"))
        ),
        expirations=tuple(
            _option_expiration(raw, index=index)
            for index, raw in enumerate(expirations_raw)
        ),
        row_budget=dict(_require_mapping(content.get("row_budget"), field="row_budget")),
        coverage=dict(_require_mapping(content.get("coverage"), field="coverage")),
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
