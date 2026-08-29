"""Opportunities snapshot chain (page 04): ``opportunities.refresh`` handler.

Topic decision (documented, same pattern as ``analysis.ingested``):
``vertex_worker.ingest.ingest_envelope`` enqueues one ADDITIONAL
``opportunities.refresh`` message for every newly written daily-bars,
option-chain or calendar-event observation — the three families that change
a candidate's advice basis or its catalyst evidence. One handler per topic.

The handler recomputes ONE ``opportunities/global`` snapshot over the WHOLE
declared synthetic universe under the strategy profile
``equity_etf_swing_3_12m`` of ``manifests/strategy-profiles.yaml``:

- per ticker, the dossier is built by the SAME
  :func:`vertex_worker.analysis.build_analysis_content` the analysis page
  uses (bars selection, fusion evidence, THEORETICAL scenarios, honest
  ``AdviceInputs``) and the verdict is whatever THE single ``AdviceEngine``
  returns — the opportunities chain re-implements no gate, no score and no
  second engine;
- the profile's ``required_evidence`` entries become HONEST presence checks
  against facts the worker really holds (declared sector, validated bars,
  published calendar catalysts, user thesis and its mandatory invalidation);
  evidence nobody holds (regime, fundamentals, manual_portfolio_fit) is
  honestly absent — never fabricated;
- candidates split into the QUALIFIED group (statuses
  ``OBSERVE``/``REVIEW``/``QUALIFIED``) and the EXCLUDED group
  (``BLOCKED``/``INSUFFICIENT_DATA``) whose ``primary_exclusion_reason`` is
  the FIRST closed gate in the canonical gate order. No closed candidate can
  ever appear in the qualified group (structural, and tested);
- the qualified ranking is a DOCUMENTED lexicographic ordering
  (:data:`QUALIFIED_ORDERING_KEYS`) — never an opaque score;
- on synthetic data most candidates are EXCLUDED ``INSUFFICIENT_DATA`` —
  this is the WANTED honest outcome; the distribution of exclusion reasons
  is published (the page's honest empty state).

Publication follows publish-if-changed: identical inputs and clock republish
nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

import yaml
from sqlalchemy.orm import Session

from vertex_core.decision import AdviceEngine
from vertex_core.synthetic import SYNTHETIC_SECTOR_TICKERS
from vertex_core.version import ENGINE_VERSION
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_persistence.repository.theses import list_theses

from vertex_worker.analysis import AnalysisConfig, build_analysis_content
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "DEFAULT_PROFILE_ID",
    "DEFAULT_PROFILES_PATH",
    "DEV_SYNTHETIC_OPPORTUNITIES_CONFIG",
    "EXCLUDED_STATUSES",
    "OPPORTUNITIES_SCHEMA_VERSION",
    "QUALIFIED_ORDERING_KEYS",
    "QUALIFIED_STATUSES",
    "SNAPSHOT_KEY_GLOBAL",
    "SNAPSHOT_KIND_OPPORTUNITIES",
    "TOPIC_OPPORTUNITIES_REFRESH",
    "OpportunitiesHandler",
    "StrategyProfile",
    "StrategyProfileError",
    "build_opportunities_content",
    "group_for_status",
    "load_strategy_profile",
    "register_opportunities_handler",
]

log = logging.getLogger("vertex_worker.opportunities")

Clock = Callable[[], datetime]

TOPIC_OPPORTUNITIES_REFRESH = "opportunities.refresh"
"""Outbox topic: recompute the global opportunities snapshot."""

SNAPSHOT_KIND_OPPORTUNITIES = "opportunities"
SNAPSHOT_KEY_GLOBAL = "global"
OPPORTUNITIES_SCHEMA_VERSION = "vertex.opportunities/1.0"

QUALIFIED_STATUSES = ("OBSERVE", "REVIEW", "QUALIFIED")
"""Statuses admitted into the qualified group (open verdicts)."""

EXCLUDED_STATUSES = ("BLOCKED", "INSUFFICIENT_DATA")
"""Statuses of the excluded group (closed verdicts). NEVER in qualified."""

_STATUS_RANK = {"QUALIFIED": 0, "REVIEW": 1, "OBSERVE": 2}

QUALIFIED_ORDERING_KEYS: tuple[str, ...] = (
    "status_rank asc (QUALIFIED=0, REVIEW=1, OBSERVE=2)",
    "missing_evidence_count asc (moins de preuves manquantes d'abord)",
    "ticker asc (departage deterministe)",
)
"""Documented lexicographic ordering of the qualified group — never an
opaque score. The excluded group is ordered by ticker asc."""

DEFAULT_PROFILE_ID = "equity_etf_swing_3_12m"
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PROFILES_PATH = _REPO_ROOT / "manifests" / "strategy-profiles.yaml"


class StrategyProfileError(RuntimeError):
    """The strategy-profiles manifest is missing, unreadable or invalid."""


@dataclass(frozen=True)
class StrategyProfile:
    """One immutable, validated strategy profile from the manifest."""

    profile_id: str
    version: str
    instruments: tuple[str, ...]
    required_evidence: tuple[str, ...]
    source_path: str


def load_strategy_profile(
    profile_id: str = DEFAULT_PROFILE_ID,
    *,
    path: Path = DEFAULT_PROFILES_PATH,
) -> StrategyProfile:
    """Parse ONE profile from the committed manifest (fail-closed).

    The manifest is the single authority on profile id, version and required
    evidence; an absent file, an unknown id or a malformed entry raises —
    nothing is guessed or defaulted.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StrategyProfileError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise StrategyProfileError(f"invalid YAML in {path}") from exc
    if not isinstance(raw, Mapping):
        raise StrategyProfileError("manifest root must be a mapping")
    profiles = raw.get("profiles")
    if not isinstance(profiles, list):
        raise StrategyProfileError("manifest carries no 'profiles' list")
    for entry in profiles:
        if not isinstance(entry, Mapping) or entry.get("id") != profile_id:
            continue
        version = entry.get("version")
        instruments = entry.get("instruments")
        required = entry.get("required_evidence")
        if not isinstance(version, str) or not version:
            raise StrategyProfileError(f"profile {profile_id}: missing version")
        if not isinstance(instruments, list) or not all(
            isinstance(i, str) and i for i in instruments
        ):
            raise StrategyProfileError(
                f"profile {profile_id}: invalid instruments"
            )
        if not isinstance(required, list) or not all(
            isinstance(r, str) and r for r in required
        ):
            raise StrategyProfileError(
                f"profile {profile_id}: invalid required_evidence"
            )
        return StrategyProfile(
            profile_id=profile_id,
            version=version,
            instruments=tuple(instruments),
            required_evidence=tuple(required),
            source_path="manifests/strategy-profiles.yaml",
        )
    raise StrategyProfileError(f"profile {profile_id!r} not found in {path}")


def _universe() -> tuple[str, ...]:
    return tuple(
        ticker
        for tickers in SYNTHETIC_SECTOR_TICKERS.values()
        for ticker in tickers
    )


def _sector_of() -> dict[str, str]:
    return {
        ticker: sector
        for sector, tickers in SYNTHETIC_SECTOR_TICKERS.items()
        for ticker in tickers
    }


DEV_SYNTHETIC_OPPORTUNITIES_CONFIG = AnalysisConfig(
    instruments=_universe(),
    allowed_sources=frozenset({"synthetic-dev"}),
    usable_rights=frozenset({"SYNTHETIC"}),
)
"""Development-only registry: the FULL declared 24-ticker synthetic universe
under the synthetic source/rights only. Population ``SYNTHETIC``."""


def group_for_status(status: str) -> str:
    """Canonical grouping of one advice status (fail-closed on unknown)."""
    if status in QUALIFIED_STATUSES:
        return "QUALIFIED_GROUP"
    if status in EXCLUDED_STATUSES:
        return "EXCLUDED_GROUP"
    raise ValueError(f"unknown advice status: {status!r}")


def _require_aware_utc(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError(f"now: expected datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    return now.astimezone(timezone.utc)


# --------------------------------------------------------------------------
# Pure content builder (no session, fully deterministic)
# --------------------------------------------------------------------------


def _calendar_event_counts(
    calendar_content: Optional[Mapping[str, Any]],
) -> dict[str, int]:
    """Upcoming published calendar events per ticker (honest catalysts)."""
    counts: dict[str, int] = {}
    if not isinstance(calendar_content, Mapping):
        return counts
    agenda = calendar_content.get("agenda")
    if not isinstance(agenda, list):
        return counts
    for entry in agenda:
        if not isinstance(entry, Mapping):
            continue
        ticker = entry.get("ticker")
        if isinstance(ticker, str) and ticker:
            counts[ticker] = counts.get(ticker, 0) + 1
    return counts


def _required_evidence_checks(
    *,
    ticker: str,
    profile: StrategyProfile,
    sector: Optional[str],
    bars_ok: bool,
    catalyst_events: int,
    theses: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Honest presence check per required evidence of the profile.

    Present ONLY when the worker genuinely holds the fact; everything nobody
    holds stays absent with its honest detail. No value is fabricated.
    """
    thesis_present = len(theses) > 0
    invalidation_present = any(
        isinstance(entry.get("invalidation"), str) and entry["invalidation"].strip()
        for entry in theses
    )
    known: dict[str, tuple[bool, Optional[str]]] = {
        "regime": (False, "no regime assessment exists for this population"),
        "sector": (
            sector is not None,
            sector if sector is not None else "ticker outside the declared universe",
        ),
        "price_volume": (
            bars_ok,
            "validated daily bars present" if bars_ok else "no validated bars",
        ),
        "fundamentals": (False, "no fundamentals source exists for this population"),
        "catalysts": (
            catalyst_events > 0,
            f"{catalyst_events} published calendar event(s) for this ticker"
            if catalyst_events > 0
            else "no published calendar event for this ticker",
        ),
        "thesis": (
            thesis_present,
            f"{len(theses)} user thesis(es) declared"
            if thesis_present
            else "no user thesis declared",
        ),
        "invalidation": (
            invalidation_present,
            "thesis carries its falsifier"
            if invalidation_present
            else "no thesis invalidation declared",
        ),
        "manual_portfolio_fit": (
            False,
            "no declared portfolio-fit assessment exists",
        ),
    }
    checks: dict[str, dict[str, Any]] = {}
    for name in profile.required_evidence:
        present, detail = known.get(
            name, (False, "no holder exists for this evidence")
        )
        checks[name] = {"present": present, "detail": detail}
    return checks


def _primary_exclusion_reason(
    advice: Mapping[str, Any],
) -> Optional[dict[str, str]]:
    """First closed gate in the canonical order (the published gate order)."""
    gates = advice.get("gates")
    if not isinstance(gates, list):
        return None
    for gate in gates:
        if isinstance(gate, Mapping) and gate.get("status") == "BLOCK":
            return {
                "gate_id": str(gate.get("gate_id")),
                "reason_code": str(gate.get("reason_code")),
            }
    return None


def build_opportunities_content(
    bar_records: Sequence[Any],
    evidence_records: Sequence[Any],
    *,
    chain_by_instrument: Mapping[str, tuple[Mapping[str, Any], int]],
    calendar_content: Optional[Mapping[str, Any]],
    theses_by_ticker: Mapping[str, Sequence[Mapping[str, Any]]],
    now: datetime,
    config: AnalysisConfig,
    profile: StrategyProfile,
    engine: Optional[AdviceEngine] = None,
) -> dict[str, Any]:
    """Build the ``opportunities/global`` snapshot content (pure).

    Identical inputs produce an identical dict. Each candidate's verdict is
    produced by :func:`vertex_worker.analysis.build_analysis_content` (the
    single dossier pipeline, hence THE single ``AdviceEngine``); this builder
    only groups, checks evidence presence and orders — it computes no gate,
    no score and no verdict of its own.
    """
    now = _require_aware_utc(now)
    engine = engine if engine is not None else AdviceEngine()
    sector_of = _sector_of()
    catalyst_counts = _calendar_event_counts(calendar_content)

    qualified: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    exclusion_reasons: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    synthetic = False
    considered_total = 0

    for ticker in config.instruments:
        chain = chain_by_instrument.get(ticker)
        dossier = build_analysis_content(
            bar_records,
            instrument=ticker,
            evidence_records=evidence_records,
            option_chain_content=None if chain is None else chain[0],
            option_chain_version=None if chain is None else chain[1],
            now=now,
            config=config,
            engine=engine,
        )
        advice = dossier["advice"]
        status = advice["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        if dossier["population"] == "SYNTHETIC":
            synthetic = True
        considered_total += dossier["coverage"]["observations_considered"]

        theses = theses_by_ticker.get(ticker, ())
        evidence_checks = _required_evidence_checks(
            ticker=ticker,
            profile=profile,
            sector=sector_of.get(ticker),
            bars_ok=dossier["bars"]["status"] == "OK",
            catalyst_events=catalyst_counts.get(ticker, 0),
            theses=theses,
        )
        missing_evidence = sorted(
            name
            for name, check in evidence_checks.items()
            if not check["present"]
        )
        candidate: dict[str, Any] = {
            "ticker": ticker,
            "sector": sector_of.get(ticker),
            "advice": {
                "advice_id": advice["advice_id"],
                "status": status,
                "direction": advice["direction"],
                "horizon": advice["horizon"],
                "as_of": advice["as_of"],
                "valid_until": advice["valid_until"],
                "engine_version": advice["engine_version"],
            },
            "gates": [
                {
                    "gate_id": gate["gate_id"],
                    "status": gate["status"],
                    "reason_code": gate["reason_code"],
                }
                for gate in advice["gates"]
            ],
            "required_evidence": evidence_checks,
            "missing_evidence": missing_evidence,
            "evidence_cluster_ids": list(advice["evidence_ids"]),
            "scenario_ids": list(advice["scenario_ids"]),
            "bars_status": dossier["bars"]["status"],
            "scenarios_status": dossier["scenarios"]["status"],
            "synthetic": dossier["population"] == "SYNTHETIC",
        }

        if group_for_status(status) == "QUALIFIED_GROUP":
            candidate["primary_exclusion_reason"] = None
            qualified.append(candidate)
        else:
            primary = _primary_exclusion_reason(advice)
            candidate["primary_exclusion_reason"] = primary
            if primary is not None:
                key = f"{primary['gate_id']}:{primary['reason_code']}"
                exclusion_reasons[key] = exclusion_reasons.get(key, 0) + 1
            excluded.append(candidate)

    # Structural invariant, enforced fail-closed: NO closed status may sit in
    # the qualified group (a violation is a bug, never published).
    for candidate in qualified:
        if candidate["advice"]["status"] in EXCLUDED_STATUSES:
            raise RuntimeError(
                "closed candidate in the qualified group: "
                f"{candidate['ticker']} ({candidate['advice']['status']})"
            )

    qualified.sort(
        key=lambda c: (
            _STATUS_RANK[c["advice"]["status"]],
            len(c["missing_evidence"]),
            c["ticker"],
        )
    )
    for rank, candidate in enumerate(qualified, start=1):
        candidate["rank"] = rank
    excluded.sort(key=lambda c: c["ticker"])

    if considered_total == 0 and not synthetic:
        population = "EMPTY"
    elif synthetic:
        population = "SYNTHETIC"
    else:
        population = "REAL"

    return {
        "schema_version": OPPORTUNITIES_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "engine_version": ENGINE_VERSION,
        "profile_ref": {
            "id": profile.profile_id,
            "version": profile.version,
            "source": profile.source_path,
        },
        "ordering": {
            "method": "lexicographic",
            "keys": list(QUALIFIED_ORDERING_KEYS),
            "note": (
                "aucun score opaque : le classement des qualifies est la "
                "cle lexicographique documentee ; les exclus sont tries par "
                "ticker"
            ),
        },
        "qualified": qualified,
        "excluded": excluded,
        "exclusion_reasons": dict(sorted(exclusion_reasons.items())),
        "limitations": [
            "SYNTHETIC development population",
            (
                "instrument-class conformity to the profile is not verifiable "
                "on synthetic data"
            ),
        ],
        "coverage": {
            "universe_size": len(config.instruments),
            "qualified_count": len(qualified),
            "excluded_count": len(excluded),
            "status_counts": dict(sorted(status_counts.items())),
            "observations_considered": considered_total,
            "lookback_seconds": int(config.lookback.total_seconds()),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class OpportunitiesHandler:
    """Handler of ``opportunities.refresh``: recompute the global candidates."""

    def __init__(
        self,
        *,
        config: AnalysisConfig,
        profile: StrategyProfile,
        clock: Clock,
    ) -> None:
        self._config = config
        self._profile = profile
        self._clock = clock
        self._engine = AdviceEngine()

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local imports avoid module cycles (handlers -> ingest -> here).
        from vertex_persistence.repository.snapshots import get_current_snapshot
        from vertex_worker.analysis import load_daily_bar_records
        from vertex_worker.calendar import (
            SNAPSHOT_KEY_GLOBAL as CALENDAR_KEY,
            SNAPSHOT_KIND_CALENDAR,
        )
        from vertex_worker.handlers import (
            load_recent_observation_records,
            publish_if_changed,
        )
        from vertex_worker.options import SNAPSHOT_KIND_OPTION_CHAIN

        now = _require_aware_utc(self._clock())
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
        chain_by_instrument: dict[str, tuple[Mapping[str, Any], int]] = {}
        for instrument in self._config.instruments:
            chain = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_OPTION_CHAIN, key=instrument
            )
            if chain is not None:
                chain_by_instrument[instrument] = (chain.content, chain.version)
        calendar = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_CALENDAR, key=CALENDAR_KEY
        )
        theses_by_ticker: dict[str, list[dict[str, Any]]] = {}
        for entry in list_theses(session, now=now):
            instrument = entry.thesis.instrument
            ticker = (
                instrument.get("ticker") if isinstance(instrument, Mapping) else None
            )
            if not isinstance(ticker, str) or not ticker:
                continue
            theses_by_ticker.setdefault(ticker, []).append(
                {
                    "thesis_id": entry.thesis.id,
                    "title": entry.thesis.title,
                    "status": entry.state.status,
                    "invalidation": entry.thesis.invalidation,
                }
            )

        content = build_opportunities_content(
            bar_records,
            evidence_records,
            chain_by_instrument=chain_by_instrument,
            calendar_content=None if calendar is None else calendar.content,
            theses_by_ticker=theses_by_ticker,
            now=now,
            config=self._config,
            profile=self._profile,
            engine=self._engine,
        )
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_OPPORTUNITIES,
            key=SNAPSHOT_KEY_GLOBAL,
            content=content,
            as_of=now,
        )
        if published is None:
            log.info(
                "opportunities snapshot unchanged (message_id=%s)", message.id
            )
        else:
            log.info(
                "opportunities snapshot published version=%s (message_id=%s)",
                published.version,
                message.id,
            )


def register_opportunities_handler(
    registry: HandlerRegistry,
    *,
    clock: Clock,
    config: AnalysisConfig,
    profile: Optional[StrategyProfile] = None,
) -> None:
    """Register the opportunities handler on ``opportunities.refresh``."""
    resolved_profile = (
        profile if profile is not None else load_strategy_profile()
    )
    registry.register(
        TOPIC_OPPORTUNITIES_REFRESH,
        OpportunitiesHandler(
            config=config, profile=resolved_profile, clock=clock
        ),
    )
