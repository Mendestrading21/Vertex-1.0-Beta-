"""Analysis dossier snapshot chain: ``analysis.ingested`` handler.

Topic decision (documented, same pattern as ``quotes.ingested``): ingestion
enqueues an ADDITIONAL ``analysis.ingested`` message for every daily-bars
envelope AND for every option-chain envelope (a chain update changes the
scenario basis of the dossier). The registry stays one-handler-per-topic;
within one ingestion the chain job is enqueued before the analysis job, so a
drained outbox recomputes the chain snapshot before the dossier reads it.

The handler recomputes one ``analysis/{instrument}`` snapshot per declared
focus instrument present in the recent bars window:

- the ~60 synthetic OHLCV bars relayed VERBATIM (decimal strings) after a
  fail-closed per-bar validation (an invalid bar is discarded WITH its
  reason, never repaired), plus the last close;
- a short evidence rail: the ticker's content clusters from the single
  deterministic fusion engine (``vertex_core.fusion.fuse``) — dedup only,
  no invented relevance;
- simple scenarios through ``vertex_core.calculations.options.scenario_grid``
  ONLY when the published option chain of the instrument carries a healthy
  contract (sane quote AND resolved Vertex IV); otherwise the block is
  honestly ``ABSENT`` with its reason. Scenario values are labeled
  ``value_nature = "THEORETICAL"`` and keep their ``CalculationRecord``
  lineage;
- the canonical ``AdviceResult`` produced by THE single ``AdviceEngine`` on
  ``AdviceInputs`` built HONESTLY from the real state of the synthetic data:
  facts the worker genuinely holds are filled (identity in the declared
  universe without an IBKR con_id, snapshot quality/freshness from the bars,
  the statuses of the calculations actually run, no portfolio-risk
  requirement, no probability used); facts nobody holds (entitlements,
  session/event calendar, liquidity thresholds, contradiction review, user
  constraints) stay ``None`` and their gates BLOCK ``UNEVALUABLE`` —
  fail-closed. The resulting status (typically ``INSUFFICIENT_DATA`` on the
  synthetic population) is published AS IS: the worker NEVER forces a
  status, and ``direction`` stays ``UNKNOWN`` because no upstream analytical
  reading exists.

Publication follows the same publish-if-changed semantics as the other
handlers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_core.calculations.options import (
    OptionInputError,
    OptionLeg,
    scenario_grid,
)
from vertex_core.contracts import CalculationRecord, make_calculation_record
from vertex_core.contracts.enums import (
    CalculationStatus,
    Direction,
    EnvelopeQuality,
    IdentityStatus,
    SnapshotQuality,
)
from vertex_core.decision import AdviceEngine, AdviceInputs
from vertex_core.decision.advice import (
    CalculationsInput,
    InstrumentResolutionInput,
    PortfolioRiskInput,
    ProbabilityInput,
    SnapshotInput,
)
from vertex_core.fusion import fuse
from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
)
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.models import Observation
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_persistence.repository.snapshots import get_current_snapshot

from vertex_worker.registry import HandlerRegistry

if TYPE_CHECKING:  # import-time cycle avoidance (handlers -> ingest -> here)
    from vertex_worker.handlers import ObservationRecord

__all__ = [
    "ANALYSIS_SCHEMA_VERSION",
    "DAILY_BARS_SCHEMA_PREFIXES",
    "DEV_SYNTHETIC_ANALYSIS_CONFIG",
    "REASON_INVALID_BAR",
    "REASON_INVALID_PAYLOAD",
    "REASON_NO_HEALTHY_CONTRACT",
    "REASON_NO_OPTION_CHAIN",
    "REASON_RIGHTS_NOT_USABLE",
    "REASON_SOURCE_NOT_ALLOWED",
    "SNAPSHOT_KIND_ANALYSIS",
    "TOPIC_ANALYSIS_INGESTED",
    "AnalysisConfig",
    "AnalysisHandler",
    "BarRecord",
    "build_analysis_content",
    "is_daily_bars_schema",
    "load_daily_bar_records",
    "register_analysis_handler",
]

log = logging.getLogger("vertex_worker.analysis")

Clock = Callable[[], datetime]

TOPIC_ANALYSIS_INGESTED = "analysis.ingested"
"""Outbox topic enqueued (in addition to ``observation.ingested``) for every
newly written daily-bars or option-chain observation."""

SNAPSHOT_KIND_ANALYSIS = "analysis"
ANALYSIS_SCHEMA_VERSION = "vertex.analysis/1.0"

DAILY_BARS_SCHEMA_PREFIXES: tuple[str, ...] = ("synthetic-daily-bars/",)
"""Schema families recognized as daily OHLCV bars (deny by default)."""

VALUE_NATURE_THEORETICAL = "THEORETICAL"

REASON_INVALID_BAR = "invalid_bar"
REASON_INVALID_PAYLOAD = "invalid_payload"
REASON_SOURCE_NOT_ALLOWED = "source_not_allowed"
REASON_RIGHTS_NOT_USABLE = "rights_not_usable"
REASON_NO_OPTION_CHAIN = "no_option_chain_snapshot"
REASON_NO_HEALTHY_CONTRACT = "no_healthy_option_contract"

_CODE_SHA = f"module:vertex_core.calculations.options@{ENGINE_VERSION}"
_SPOT_SHOCKS = (Decimal("0.90"), Decimal("0.95"), Decimal("1.00"), Decimal("1.05"), Decimal("1.10"))
_CENTS = Decimal("0.01")


def is_daily_bars_schema(schema_version: str) -> bool:
    """``True`` when ``schema_version`` belongs to a declared bars family."""
    return isinstance(schema_version, str) and schema_version.startswith(
        DAILY_BARS_SCHEMA_PREFIXES
    )


@dataclass(frozen=True)
class BarRecord:
    """ORM-free view of one persisted daily-bars observation."""

    event_id: str
    source: str
    instrument_ref: Optional[str]
    as_of: datetime
    quality_status: str
    rights: str
    schema_version: str
    payload: Mapping[str, Any]


def _is_synthetic_bar(record: BarRecord) -> bool:
    return record.rights == SYNTHETIC_RIGHTS or record.source == SYNTHETIC_SOURCE


@dataclass(frozen=True)
class AnalysisConfig:
    """Declared inputs of the analysis dossier builder (owned upstream)."""

    instruments: tuple[str, ...]
    allowed_sources: frozenset[str]
    usable_rights: frozenset[str]
    lookback: timedelta = timedelta(hours=72)
    max_observations: int = 500
    bars_freshness: timedelta = timedelta(hours=48)
    advice_validity: timedelta = timedelta(hours=1)
    max_evidence: int = 5
    horizon: str = "1d"

    def __post_init__(self) -> None:
        if not self.instruments:
            raise ValueError("instruments: at least one instrument required")
        if self.lookback <= timedelta(0):
            raise ValueError("lookback: must be a positive duration")
        if self.bars_freshness <= timedelta(0):
            raise ValueError("bars_freshness: must be a positive duration")
        if self.advice_validity <= timedelta(0):
            raise ValueError("advice_validity: must be a positive duration")
        if not isinstance(self.max_observations, int) or self.max_observations < 1:
            raise ValueError("max_observations: must be an int >= 1")
        if not isinstance(self.max_evidence, int) or self.max_evidence < 1:
            raise ValueError("max_evidence: must be an int >= 1")
        if not self.horizon:
            raise ValueError("horizon: non-empty string required")


DEV_SYNTHETIC_ANALYSIS_CONFIG = AnalysisConfig(
    instruments=SYNTHETIC_FOCUS_TICKERS,
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)
"""Development-only registry: ONLY the synthetic source/rights and the 4
declared focus instruments. Every snapshot it produces is population
``SYNTHETIC``."""


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def load_daily_bar_records(
    session: Session, *, now: datetime, lookback: timedelta, limit: int
) -> list[BarRecord]:
    """Load the bounded recent daily-bars window, deterministically ordered."""
    filters = [
        Observation.schema_version.like(f"{prefix}%")
        for prefix in DAILY_BARS_SCHEMA_PREFIXES
    ]
    schema_filter = filters[0]
    for extra in filters[1:]:
        schema_filter = schema_filter | extra
    rows = (
        session.execute(
            select(Observation)
            .where(
                Observation.as_of <= now,
                Observation.as_of >= now - lookback,
                schema_filter,
            )
            .order_by(Observation.as_of.desc(), Observation.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        BarRecord(
            event_id=row.event_id,
            source=row.source,
            instrument_ref=row.instrument_ref,
            as_of=row.as_of,
            quality_status=row.quality_status,
            rights=row.rights,
            schema_version=row.schema_version,
            payload=row.payload,
        )
        for row in rows
    ]


# --------------------------------------------------------------------------
# Pure content helpers (no session, fully deterministic)
# --------------------------------------------------------------------------


def _num_string(value: float) -> str:
    return format(Decimal(repr(value)), "f")


def _calculation_meta(record: CalculationRecord) -> dict[str, Any]:
    return {
        "calculation_id": record.calculation_id,
        "engine_version": record.engine_version,
        "method": record.method,
        "input_hash": record.input_hash,
        "result_hash": record.result_hash,
        "status": record.status.value,
    }


def _decimal_or_none(value: Any) -> Optional[Decimal]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _validate_bar(raw: Any) -> Optional[dict[str, Any]]:
    """Validate one OHLCV bar fail-closed; returns the verbatim bar or None."""
    if not isinstance(raw, Mapping):
        return None
    trading_day = raw.get("trading_day")
    if not isinstance(trading_day, str) or not trading_day:
        return None
    open_ = _decimal_or_none(raw.get("open"))
    high = _decimal_or_none(raw.get("high"))
    low = _decimal_or_none(raw.get("low"))
    close = _decimal_or_none(raw.get("close"))
    volume = raw.get("volume")
    if open_ is None or high is None or low is None or close is None:
        return None
    if isinstance(volume, bool) or not isinstance(volume, int) or volume < 0:
        return None
    if min(open_, high, low, close) <= 0:
        return None
    if high < max(open_, close) or low > min(open_, close):
        return None
    return {
        "trading_day": trading_day,
        "open": raw["open"],
        "high": raw["high"],
        "low": raw["low"],
        "close": raw["close"],
        "volume": volume,
    }


def _build_evidence(
    evidence_records: Sequence["ObservationRecord"],
    *,
    instrument: str,
    config: AnalysisConfig,
) -> dict[str, Any]:
    """Short evidence rail from the deterministic fusion of the ticker's
    content observations (title-carrying observations mentioning the
    instrument). Dedup only — no relevance invention here."""
    from vertex_worker.handlers import (  # local import: cycle avoidance
        DEFAULT_SOURCE_TIER,
        is_synthetic_record,
    )
    from vertex_core.fusion import ContentObservation

    observations = []
    record_by_id: dict[str, Any] = {}
    for record in evidence_records:
        payload = record.payload if isinstance(record.payload, Mapping) else {}
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        raw_entities = payload.get("entities")
        entities = (
            tuple(e for e in raw_entities if isinstance(e, str) and e.strip())
            if isinstance(raw_entities, (list, tuple))
            else ()
        )
        if instrument not in entities and record.instrument_ref != instrument:
            continue
        url = payload.get("canonical_url")
        observations.append(
            ContentObservation(
                content_id=record.event_id,
                source=record.source,
                source_tier=DEFAULT_SOURCE_TIER,
                native_id=record.source_event_id,
                canonical_url=url if isinstance(url, str) and url else None,
                title=title,
                entities=entities or (instrument,),
                published_at=record.published_at,
                received_at=record.received_at,
                rights=record.rights,
                quality=EnvelopeQuality(record.quality_status),
                is_deleted=False,
            )
        )
        record_by_id[record.event_id] = record

    fusion = fuse(observations)
    observation_by_id = {obs.content_id: obs for obs in fusion.observations}
    clusters = sorted(
        fusion.clusters,
        key=lambda cluster: (cluster.last_received_at, cluster.cluster_id),
        reverse=True,
    )
    entries: list[dict[str, Any]] = []
    for cluster in clusters[: config.max_evidence]:
        representative = observation_by_id[min(cluster.member_ids)]
        entries.append(
            {
                "cluster_id": cluster.cluster_id,
                "title": representative.title,
                "sources": list(cluster.sources),
                "rights": list(cluster.rights),
                "member_count": len(cluster.member_ids),
                "member_event_ids": list(cluster.member_ids),
                "last_received_at": cluster.last_received_at.isoformat(),
                "synthetic": any(
                    is_synthetic_record(record_by_id[member])
                    for member in cluster.member_ids
                ),
            }
        )
    return {
        "source": "fusion",
        "ruleset_version": fusion.ruleset_version,
        "considered": len(observations),
        "clusters_total": len(fusion.clusters),
        "clusters": entries,
    }


def _pick_healthy_contract(
    chain_content: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """First contract with a sane quote AND a resolved Vertex IV, plus its
    group context. CALL contracts are preferred (simple long-call scenario);
    a healthy PUT is used only when no CALL qualifies."""
    fallback: Optional[dict[str, Any]] = None
    expirations = chain_content.get("expirations")
    if not isinstance(expirations, list):
        return None
    spot = chain_content.get("spot")
    assumptions = chain_content.get("assumptions")
    if not isinstance(spot, Mapping) or not isinstance(assumptions, Mapping):
        return None
    for group in expirations:
        if not isinstance(group, Mapping):
            continue
        contracts = group.get("contracts")
        if not isinstance(contracts, list):
            continue
        for entry in contracts:
            if not isinstance(entry, Mapping):
                continue
            quote = entry.get("quote")
            iv = entry.get("iv")
            if not isinstance(quote, Mapping) or not isinstance(iv, Mapping):
                continue
            if quote.get("status") != "OK" or iv.get("status") != "OK":
                continue
            ask = _decimal_or_none(quote.get("ask"))
            strike = _decimal_or_none(entry.get("strike"))
            iv_value = _decimal_or_none(iv.get("value"))
            spot_value = _decimal_or_none(spot.get("value"))
            rate = _decimal_or_none(assumptions.get("rate"))
            dividend_yield = _decimal_or_none(assumptions.get("dividend_yield"))
            maturity = _decimal_or_none(group.get("maturity_years"))
            multiplier = entry.get("multiplier")
            if None in (ask, strike, iv_value, spot_value, rate, dividend_yield, maturity):
                continue
            if not isinstance(multiplier, int) or multiplier <= 0:
                continue
            if ask <= 0 or maturity <= 0:
                continue
            candidate = {
                "entry": entry,
                "group": group,
                "ask": ask,
                "strike": strike,
                "iv": iv_value,
                "spot": spot_value,
                "rate": rate,
                "dividend_yield": dividend_yield,
                "maturity_years": maturity,
                "multiplier": multiplier,
            }
            if entry.get("right") == "CALL":
                return candidate
            if fallback is None and entry.get("right") == "PUT":
                fallback = candidate
    return fallback


def _build_scenarios(
    chain_content: Optional[Mapping[str, Any]],
    *,
    chain_version: Optional[int],
    now: datetime,
) -> dict[str, Any]:
    """Scenario block: ``scenario_grid`` on ONE healthy long option leg, or
    an honest ABSENT block with the typed reason."""
    if chain_content is None:
        return {"status": "ABSENT", "reason": REASON_NO_OPTION_CHAIN}
    picked = _pick_healthy_contract(chain_content)
    if picked is None:
        return {"status": "ABSENT", "reason": REASON_NO_HEALTHY_CONTRACT}

    entry = picked["entry"]
    leg = OptionLeg(
        quantity=1,
        right=entry["right"],
        strike=picked["strike"],
        premium=picked["ask"],  # hypothetical buy of one leg: the observed ask
        multiplier=picked["multiplier"],
    )
    spot_points = [
        (picked["spot"] * shock).quantize(_CENTS) for shock in _SPOT_SHOCKS
    ]
    maturity = float(picked["maturity_years"])
    time_points = (maturity, maturity / 2.0, 0.0)
    iv_value = float(picked["iv"])
    try:
        grid = scenario_grid(
            (leg,),
            tuple(spot_points),
            time_points,
            ((iv_value,),),
            picked["rate"],
            picked["dividend_yield"],
        )
    except OptionInputError as exc:
        return {"status": "ABSENT", "reason": exc.reason}

    record = make_calculation_record(
        calculation_id="options.scenario_grid",
        calculation_type="options",
        code_sha=_CODE_SHA,
        method="BSM repricing grid, single long leg, IV unchanged scenario",
        inputs={
            "leg": leg.model_dump(),
            "spot_grid": spot_points,
            "time_grid_years": [repr(t) for t in time_points],
            "iv_scenarios": [[repr(iv_value)]],
            "rate": picked["rate"],
            "dividend_yield": picked["dividend_yield"],
        },
        result=grid,
        started_at=now,
        completed_at=now,
        assumptions=(
            "premium side ASK (hypothetical buy of one long leg)",
            "single scenario: implied volatility unchanged",
            "P&L before declared costs (scenario_grid contract)",
        ),
    )
    return {
        "status": "OK",
        "value_nature": VALUE_NATURE_THEORETICAL,
        "basis": {
            "con_id": entry.get("con_id"),
            "right": entry.get("right"),
            "strike": entry.get("strike"),
            "expiration": entry.get("expiration"),
            "trading_class": entry.get("trading_class"),
            "multiplier": picked["multiplier"],
            "currency": entry.get("currency"),
            "premium": format(picked["ask"], "f"),
            "premium_side": "ASK",
            "iv": format(picked["iv"], "f"),
            "chain_snapshot_version": chain_version,
        },
        "spot_grid": [format(point, "f") for point in spot_points],
        "time_grid_years": [_num_string(point) for point in time_points],
        "iv_scenarios": [[_num_string(iv_value)]],
        "grid": [
            [[_num_string(cell) for cell in row] for row in scenario]
            for scenario in grid
        ],
        "calculation": _calculation_meta(record),
    }


def build_analysis_content(
    bar_records: Sequence[BarRecord],
    *,
    instrument: str,
    evidence_records: Sequence["ObservationRecord"],
    option_chain_content: Optional[Mapping[str, Any]],
    option_chain_version: Optional[int],
    now: datetime,
    config: AnalysisConfig,
    engine: Optional[AdviceEngine] = None,
) -> dict[str, Any]:
    """Build the ``analysis/{instrument}`` snapshot content (pure).

    Identical inputs produce an identical dict. Every considered bar record
    is used or rejected with a reason, every invalid bar is discarded with a
    reason, and the verdict is whatever THE ``AdviceEngine`` returns on the
    honestly assembled inputs — never forced, never softened.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    if instrument not in config.instruments:
        raise ValueError(f"instrument {instrument!r} is not declared")
    engine = engine if engine is not None else AdviceEngine()

    # -- pick the latest usable bars record for this instrument --------------
    rejected_records: list[dict[str, str]] = []
    chosen: Optional[BarRecord] = None
    considered = 0
    for record in sorted(bar_records, key=lambda r: (r.as_of, r.event_id)):
        payload = record.payload if isinstance(record.payload, Mapping) else {}
        if payload.get("ticker") != instrument:
            continue
        considered += 1
        if record.source not in config.allowed_sources:
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_SOURCE_NOT_ALLOWED}
            )
            continue
        if record.rights not in config.usable_rights:
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_RIGHTS_NOT_USABLE}
            )
            continue
        if not isinstance(payload.get("bars"), list):
            rejected_records.append(
                {"event_id": record.event_id, "reason": REASON_INVALID_PAYLOAD}
            )
            continue
        chosen = record  # ascending order: the latest usable record wins

    # -- bars block (verbatim, fail-closed per bar) ---------------------------
    valid_bars: list[dict[str, Any]] = []
    discarded_bars: list[dict[str, Any]] = []
    synthetic = False
    bars_fresh = False
    if chosen is not None:
        synthetic = _is_synthetic_bar(chosen)
        bars_fresh = (now - chosen.as_of) <= config.bars_freshness
        for index, raw in enumerate(chosen.payload["bars"]):
            bar = _validate_bar(raw)
            if bar is None:
                discarded_bars.append({"index": index, "reason": REASON_INVALID_BAR})
            else:
                valid_bars.append(bar)
        valid_bars.sort(key=lambda bar: bar["trading_day"])
    last_close = valid_bars[-1]["close"] if valid_bars else None
    payload = chosen.payload if chosen is not None else {}
    bars_block: dict[str, Any] = {
        "status": "OK" if valid_bars else "ABSENT",
        "count": len(valid_bars),
        "currency": payload.get("currency") if chosen is not None else None,
        "adjustment_basis": (
            payload.get("adjustment_basis") if chosen is not None else None
        ),
        "first_trading_day": valid_bars[0]["trading_day"] if valid_bars else None,
        "last_trading_day": valid_bars[-1]["trading_day"] if valid_bars else None,
        "last_close": last_close,
        "quality": chosen.quality_status if chosen is not None else None,
        "fresh": bars_fresh if chosen is not None else None,
        "source_event_id": chosen.event_id if chosen is not None else None,
        "observed_as_of": chosen.as_of.isoformat() if chosen is not None else None,
        "discarded": discarded_bars,
        "bars": valid_bars,
    }

    # -- evidence and scenarios ----------------------------------------------
    evidence = _build_evidence(
        evidence_records, instrument=instrument, config=config
    )
    scenarios = _build_scenarios(
        option_chain_content, chain_version=option_chain_version, now=now
    )
    if any(entry["synthetic"] for entry in evidence["clusters"]):
        synthetic = True

    # -- honest AdviceInputs -> the single AdviceEngine -----------------------
    if chosen is None or not valid_bars:
        snapshot_quality = SnapshotQuality.MISSING
    elif discarded_bars or chosen.quality_status != "VALID":
        snapshot_quality = SnapshotQuality.PARTIAL
    else:
        snapshot_quality = SnapshotQuality.GOOD

    calculation_statuses: dict[str, CalculationStatus] = {}
    if scenarios["status"] == "OK":
        calculation_statuses["options.scenario_grid"] = CalculationStatus.OK

    explanation_facts: list[str] = []
    if valid_bars:
        explanation_facts.append(
            f"{len(valid_bars)} synthetic daily bars from "
            f"{bars_block['first_trading_day']} to {bars_block['last_trading_day']}"
        )
        explanation_facts.append(
            f"last synthetic close {last_close} {bars_block['currency']}"
        )
    if evidence["clusters"]:
        explanation_facts.append(
            f"{len(evidence['clusters'])} evidence cluster(s) from fusion"
        )

    inputs = AdviceInputs(
        instrument_id=instrument,
        as_of=now,
        valid_until=now + config.advice_validity,
        input_snapshot_id=(
            chosen.event_id if chosen is not None else f"analysis:{instrument}:none"
        ),
        horizon=config.horizon,
        # No upstream analytical reading exists for the synthetic population:
        # the direction is honestly UNKNOWN, never inferred here.
        direction=Direction.UNKNOWN,
        risk_summary=(
            "SYNTHETIC development data; deterministic fixtures; no real "
            "market risk assessment exists for this instrument"
        ),
        evidence_ids=tuple(entry["cluster_id"] for entry in evidence["clusters"]),
        scenario_ids=(
            (scenarios["calculation"]["input_hash"],)
            if scenarios["status"] == "OK"
            else ()
        ),
        explanation_facts=tuple(explanation_facts),
        limitations=("SYNTHETIC development population",) if synthetic else (),
        instrument=InstrumentResolutionInput(
            identity_status=IdentityStatus.RESOLVED,
            # Synthetic instruments have no IBKR con_id confirmation: the
            # honest fact makes gate 1 DEGRADE (RESOLVED_WITHOUT_CONID).
            resolved_with_conid=False,
        ),
        # entitlements / session_event / liquidity / contradictions /
        # constraints: nobody holds these facts for the synthetic population,
        # so they stay absent and their gates BLOCK UNEVALUABLE (fail-closed;
        # the resulting INSUFFICIENT_DATA is the WANTED honest verdict).
        snapshot=SnapshotInput(quality=snapshot_quality, fresh=bars_fresh),
        calculations=CalculationsInput(
            calculation_statuses=calculation_statuses or None
        ),
        portfolio_risk=PortfolioRiskInput(risk_required=False),
        probability=ProbabilityInput(probability_used=False),
    )
    advice = engine.evaluate(inputs)

    population = "EMPTY" if considered == 0 else ("SYNTHETIC" if synthetic else "REAL")
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "instrument": instrument,
        "engine_version": ENGINE_VERSION,
        "bars": bars_block,
        "evidence": evidence,
        "scenarios": scenarios,
        "advice": advice.model_dump(mode="json"),
        "coverage": {
            "observations_considered": considered,
            "rejected_records": rejected_records,
            "lookback_seconds": int(config.lookback.total_seconds()),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class AnalysisHandler:
    """Handler of ``analysis.ingested``: recompute per-instrument dossiers."""

    def __init__(self, *, config: AnalysisConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock
        self._engine = AdviceEngine()

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local imports avoid a module cycle (handlers imports ingest,
        # ingest imports this module).
        from vertex_worker.handlers import (
            load_recent_observation_records,
            publish_if_changed,
        )
        from vertex_worker.options import SNAPSHOT_KIND_OPTION_CHAIN

        now = self._clock()
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("clock returned a naive datetime; aware UTC required")
        bar_records = load_daily_bar_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )
        evidence_records = load_recent_observation_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )
        seen = {
            record.payload.get("ticker")
            for record in bar_records
            if isinstance(record.payload, Mapping)
        }
        for instrument in self._config.instruments:
            if instrument not in seen:
                # Absence stays absent: no invented dossier, the API answers
                # its honest empty state until bars actually exist.
                continue
            chain = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_OPTION_CHAIN, key=instrument
            )
            content = build_analysis_content(
                bar_records,
                instrument=instrument,
                evidence_records=evidence_records,
                option_chain_content=None if chain is None else chain.content,
                option_chain_version=None if chain is None else chain.version,
                now=now,
                config=self._config,
                engine=self._engine,
            )
            published = publish_if_changed(
                session,
                kind=SNAPSHOT_KIND_ANALYSIS,
                key=instrument,
                content=content,
                as_of=now,
            )
            if published is None:
                log.info(
                    "analysis %s unchanged (message_id=%s)", instrument, message.id
                )
            else:
                log.info(
                    "analysis %s published version=%s (message_id=%s)",
                    instrument,
                    published.version,
                    message.id,
                )


def register_analysis_handler(
    registry: HandlerRegistry, *, clock: Clock, config: AnalysisConfig
) -> None:
    """Register the analysis handler on ``analysis.ingested``."""
    registry.register(
        TOPIC_ANALYSIS_INGESTED, AnalysisHandler(config=config, clock=clock)
    )
