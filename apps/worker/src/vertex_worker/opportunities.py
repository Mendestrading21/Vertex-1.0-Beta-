"""Opportunities snapshot chain (page 04): ``opportunities.refresh`` handler.

Topic decision (documented, same pattern as ``analysis.ingested``):
``vertex_worker.ingest.ingest_envelope`` enqueues one ADDITIONAL
``opportunities.refresh`` message for every newly written daily-bars,
option-chain or calendar-event observation — the three families that change
a candidate's advice basis or its catalyst evidence. One handler per topic.

Known cost (documented budget, NOT coalesced today): one message recomputes
the WHOLE universe, so ``n`` ingested observations cost ``n x len(universe)``
dossiers. The queue stays correct (each run is idempotent and publication is
publish-if-changed) but the work is amplified; coalescing several pending
``opportunities.refresh`` messages into one belongs to the ingest/outbox
owner, not to this module.

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
  UPCOMING published calendar catalysts, live user thesis and its mandatory
  invalidation); evidence nobody holds (regime, fundamentals,
  manual_portfolio_fit) is honestly absent — never fabricated;
- admissibility to the QUALIFIED group crosses THREE independent facts, never
  the status string alone:

  1. the status is open (``OBSERVE``/``REVIEW``/``QUALIFIED``);
  2. the PUBLISHED gates carry no ``BLOCK`` — a candidate carrying a blocking
     gate can never be qualified whatever its status says;
  3. every required evidence of the profile is present — a required evidence
     missing makes the candidate INADMISSIBLE (published reason), not merely
     worse ranked.

  Facts 1 and 2 must agree: an open status carrying a ``BLOCK`` gate, or a
  closed status carrying none, contradicts the ``AdviceResult`` contract
  itself; the snapshot is then REFUSED (fail-closed ``RuntimeError``) instead
  of published, because the status of such a candidate is vouched for by no
  engine. Fact 3 is a data condition, so the candidate moves to the EXCLUDED
  group with ``exclusion.kind = "MISSING_REQUIRED_EVIDENCE"``;
- every excluded candidate publishes its ``exclusion`` block: the FIRST
  closed gate in the canonical gate order for a closed status, or the missing
  required evidence otherwise. No candidate is excluded without a reason;
- the qualified ranking is a DOCUMENTED lexicographic ordering
  (:data:`QUALIFIED_ORDERING_KEYS`) — never an opaque score;
- on synthetic data every candidate is EXCLUDED ``INSUFFICIENT_DATA`` — this
  is the WANTED honest outcome; the distribution of exclusion reasons is
  published (the page's honest empty state);
- ``population`` and ``limitations`` are DERIVED from the dossiers actually
  computed: a snapshot never claims a synthetic limitation on a real
  population, nor the reverse;
- the calendar snapshot feeding the catalyst evidence publishes its
  provenance (kind/key/version/as_of) and is used only when it is fresh
  enough; only events strictly AFTER the computation instant count as
  upcoming catalysts.

The strategy-profile manifest path is INJECTED (``profiles_path`` at
registration, ``path`` on :func:`load_strategy_profile`);
:data:`DEFAULT_PROFILES_PATH` is only the documented source-checkout
fallback, so a deployment outside a checkout stays startable.

Publication follows publish-if-changed: identical inputs and clock republish
nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    "ADMISSIBLE_THESIS_STATUSES",
    "CALENDAR_REF_ABSENT",
    "CALENDAR_REF_FUTURE",
    "CALENDAR_REF_STALE",
    "CALENDAR_REF_USED",
    "DEFAULT_PROFILE_ID",
    "DEFAULT_PROFILES_PATH",
    "DEV_SYNTHETIC_OPPORTUNITIES_CONFIG",
    "EXCLUDED_STATUSES",
    "EXCLUSION_KIND_CLOSED_STATUS",
    "EXCLUSION_KIND_MISSING_EVIDENCE",
    "OPPORTUNITIES_SCHEMA_VERSION",
    "PROFILE_FIELDS_NOT_APPLIED",
    "QUALIFIED_ORDERING_KEYS",
    "QUALIFIED_STATUSES",
    "SNAPSHOT_KEY_GLOBAL",
    "SNAPSHOT_KIND_OPPORTUNITIES",
    "TOPIC_OPPORTUNITIES_REFRESH",
    "CalendarSnapshotRef",
    "OpportunitiesHandler",
    "StrategyProfile",
    "StrategyProfileError",
    "build_opportunities_content",
    "group_for_status",
    "horizon_label",
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
"""Open statuses. NECESSARY but NOT sufficient to enter the qualified group."""

EXCLUDED_STATUSES = ("BLOCKED", "INSUFFICIENT_DATA")
"""Statuses of the excluded group (closed verdicts). NEVER in qualified."""

GATE_STATUS_BLOCK = "BLOCK"
GATE_STATUS_DEGRADE = "DEGRADE"

EXCLUSION_KIND_CLOSED_STATUS = "CLOSED_STATUS"
"""Excluded because THE engine closed the verdict on a blocking gate."""

EXCLUSION_KIND_MISSING_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
"""Excluded because a required evidence of the profile is absent."""

ADMISSIBLE_THESIS_STATUSES = frozenset({"ACTIVE", "SNOOZED"})
"""Thesis states that still carry a live user commitment. ``ARCHIVED`` (or
any unknown state) is parked: it proves neither thesis nor invalidation."""

_STATUS_RANK = {"QUALIFIED": 0, "REVIEW": 1, "OBSERVE": 2}

QUALIFIED_ORDERING_KEYS: tuple[str, ...] = (
    "status_rank asc (QUALIFIED=0, REVIEW=1, OBSERVE=2)",
    "degraded_gates_count asc (moins de portes degradees d'abord)",
    "ticker asc (departage deterministe)",
)
"""Documented lexicographic ordering of the qualified group — never an
opaque score. The excluded group is ordered by ticker asc.

``missing_evidence_count`` is deliberately NOT an ordering key: a missing
required evidence excludes the candidate, it never merely lowers its rank."""

PROFILE_FIELDS_NOT_APPLIED: tuple[dict[str, str], ...] = (
    {
        "field": "instruments",
        "reason": (
            "no instrument-class source exists for this population: the "
            "declared STOCK/ETF restriction is not verified"
        ),
    },
    {
        "field": "review_cadence",
        "reason": "no review scheduler consumes this snapshot",
    },
    {
        "field": "common_gates",
        "reason": (
            "the gate catalog is owned by the single AdviceEngine, never by "
            "the manifest"
        ),
    },
    {
        "field": "default_state",
        "reason": "the status is produced by the single AdviceEngine only",
    },
)
"""Manifest fields the snapshot does NOT apply — published so ``profile_ref``
never claims a profile is fully applied when it is not."""

DEFAULT_PROFILE_ID = "equity_etf_swing_3_12m"
PROFILES_MANIFEST_RELATIVE_PATH = "manifests/strategy-profiles.yaml"
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PROFILES_PATH = _REPO_ROOT / "manifests" / "strategy-profiles.yaml"
"""Documented FALLBACK only (source checkout layout). Every entry point takes
an explicit path: nothing in this module requires that layout to exist."""

CALENDAR_REF_ABSENT = "ABSENT"
CALENDAR_REF_USED = "USED"
CALENDAR_REF_STALE = "STALE"
CALENDAR_REF_FUTURE = "REJECTED_FUTURE_AS_OF"


class StrategyProfileError(RuntimeError):
    """The strategy-profiles manifest is missing, unreadable or invalid."""


def horizon_label(months: int) -> str:
    """Canonical horizon label of one declared decision horizon in months."""
    if isinstance(months, bool) or not isinstance(months, int) or months < 1:
        raise ValueError(f"months: positive int required, got {months!r}")
    return f"{months}m"


@dataclass(frozen=True)
class StrategyProfile:
    """One immutable, validated strategy profile from the manifest."""

    profile_id: str
    version: str
    instruments: tuple[str, ...]
    required_evidence: tuple[str, ...]
    source_path: str
    decision_horizons_months: tuple[int, ...] = ()

    @property
    def horizons(self) -> tuple[str, ...]:
        """Canonical labels of the declared decision horizons."""
        return tuple(horizon_label(m) for m in self.decision_horizons_months)


def load_strategy_profile(
    profile_id: str = DEFAULT_PROFILE_ID,
    *,
    path: Optional[Path] = None,
) -> StrategyProfile:
    """Parse ONE profile from the INJECTED manifest path (fail-closed).

    ``path`` is the injection point; it defaults to
    :data:`DEFAULT_PROFILES_PATH`, the documented source-checkout fallback.
    The manifest is the single authority on profile id, version, decision
    horizons and required evidence; an absent file, an unknown id or a
    malformed entry raises — nothing is guessed or defaulted.
    """
    resolved = Path(path) if path is not None else DEFAULT_PROFILES_PATH
    hint = (
        "inject an explicit manifest path (load_strategy_profile(path=...) "
        "or register_opportunities_handler(profiles_path=...))"
    )
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StrategyProfileError(f"cannot read {resolved}: {exc}; {hint}") from exc
    except yaml.YAMLError as exc:
        raise StrategyProfileError(f"invalid YAML in {resolved}") from exc
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
            source_path=PROFILES_MANIFEST_RELATIVE_PATH,
            decision_horizons_months=_parse_horizons(entry, profile_id),
        )
    raise StrategyProfileError(
        f"profile {profile_id!r} not found in {resolved}; {hint}"
    )


def _parse_horizons(entry: Mapping[str, Any], profile_id: str) -> tuple[int, ...]:
    """Validated ``decision_horizons_months`` (absent stays honestly empty)."""
    horizons = entry.get("decision_horizons_months")
    if horizons is None:
        return ()
    if not isinstance(horizons, list) or not horizons:
        raise StrategyProfileError(
            f"profile {profile_id}: invalid decision_horizons_months"
        )
    for value in horizons:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise StrategyProfileError(
                f"profile {profile_id}: invalid decision_horizons_months"
            )
    return tuple(horizons)


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
    # The shortest decision horizon DECLARED by equity_etf_swing_3_12m: the
    # published advice horizon must belong to the referenced profile.
    horizon="3m",
    # The profile requires manual_portfolio_fit, so gate 7 must be OBSERVED
    # (fail-closed on the absent user declaration), never declared
    # NOT_REQUIRED.
    portfolio_risk_required=True,
)
"""Development-only registry: the FULL declared 24-ticker synthetic universe
under the synthetic source/rights only. Population ``SYNTHETIC``."""


def group_for_status(status: str) -> str:
    """Canonical grouping of one advice status (fail-closed on unknown).

    Status alone NEVER decides admissibility: see
    :func:`build_opportunities_content`, which also crosses the published
    gates and the profile's required evidence.
    """
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


@dataclass(frozen=True)
class CalendarSnapshotRef:
    """Provenance of the calendar snapshot consumed as catalyst evidence."""

    kind: str
    key: str
    version: int
    as_of: datetime


def _parse_aware(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return None
    return parsed.astimezone(timezone.utc)


def _calendar_evidence(
    calendar_content: Optional[Mapping[str, Any]],
    calendar_ref: Optional[CalendarSnapshotRef],
    *,
    now: datetime,
    max_age: timedelta,
) -> tuple[dict[str, int], dict[str, Any]]:
    """UPCOMING published calendar events per ticker, with provenance.

    Fail-closed: content and provenance travel together, a calendar snapshot
    dated in the future or older than ``max_age`` proves no catalyst, and only
    events strictly after ``now`` are counted — a past event is never an
    upcoming catalyst.
    """
    if (calendar_content is None) != (calendar_ref is None):
        raise ValueError(
            "calendar snapshot and its provenance must be supplied together "
            "(fail-closed: an untraceable catalyst evidence is refused)"
        )
    ref: dict[str, Any] = {
        "kind": None if calendar_ref is None else calendar_ref.kind,
        "key": None if calendar_ref is None else calendar_ref.key,
        "version": None if calendar_ref is None else calendar_ref.version,
        "snapshot_as_of": None,
        "content_as_of": None,
        "content_schema_version": None,
        "status": CALENDAR_REF_ABSENT,
        "max_age_seconds": int(max_age.total_seconds()),
        "events_upcoming": 0,
        "events_ignored_past": 0,
        "events_without_ticker": 0,
        "events_rejected": 0,
    }
    if calendar_ref is None or calendar_content is None:
        return {}, ref

    snapshot_as_of = _require_aware_utc(calendar_ref.as_of)
    ref["snapshot_as_of"] = snapshot_as_of.isoformat()
    if isinstance(calendar_content, Mapping):
        content_as_of = calendar_content.get("as_of")
        ref["content_as_of"] = content_as_of if isinstance(content_as_of, str) else None
        schema = calendar_content.get("schema_version")
        ref["content_schema_version"] = schema if isinstance(schema, str) else None

    if snapshot_as_of > now:
        ref["status"] = CALENDAR_REF_FUTURE
        return {}, ref
    if (now - snapshot_as_of) > max_age:
        ref["status"] = CALENDAR_REF_STALE
        return {}, ref

    counts: dict[str, int] = {}
    upcoming = past = untargeted = rejected = 0
    agenda = calendar_content.get("agenda")
    if not isinstance(agenda, list):
        ref["status"] = CALENDAR_REF_USED
        return counts, ref
    for entry in agenda:
        if not isinstance(entry, Mapping):
            rejected += 1
            continue
        ticker = entry.get("ticker")
        if not isinstance(ticker, str) or not ticker:
            # Scope-global events (macro) carry no ticker: they are no
            # instrument catalyst, and they are not a defect either.
            untargeted += 1
            continue
        event_time = _parse_aware(entry.get("event_time_utc"))
        if event_time is None:
            rejected += 1
            continue
        if event_time <= now:
            past += 1
            continue
        counts[ticker] = counts.get(ticker, 0) + 1
        upcoming += 1
    ref["status"] = CALENDAR_REF_USED
    ref["events_upcoming"] = upcoming
    ref["events_ignored_past"] = past
    ref["events_without_ticker"] = untargeted
    ref["events_rejected"] = rejected
    return counts, ref


def _live_theses(
    theses: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    """Theses that still carry a live user commitment (ARCHIVED excluded)."""
    return tuple(
        entry
        for entry in theses
        if isinstance(entry, Mapping)
        and entry.get("status") in ADMISSIBLE_THESIS_STATUSES
    )


def _required_evidence_checks(
    *,
    profile: StrategyProfile,
    sector: Optional[str],
    bars_ok: bool,
    catalyst_events: int,
    theses: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Honest presence check per required evidence of the profile.

    Present ONLY when the worker genuinely holds the fact; everything nobody
    holds stays absent with its honest detail. No value is fabricated. An
    archived (parked) thesis proves neither the thesis nor its invalidation.
    """
    live = _live_theses(theses)
    parked = len(theses) - len(live)
    thesis_present = len(live) > 0
    invalidation_present = any(
        isinstance(entry.get("invalidation"), str) and entry["invalidation"].strip()
        for entry in live
    )
    parked_note = f" ({parked} parked thesis(es) ignored)" if parked else ""
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
            f"{catalyst_events} upcoming published calendar event(s) for this ticker"
            if catalyst_events > 0
            else "no upcoming published calendar event for this ticker",
        ),
        "thesis": (
            thesis_present,
            f"{len(live)} live user thesis(es) declared{parked_note}"
            if thesis_present
            else f"no live user thesis declared{parked_note}",
        ),
        "invalidation": (
            invalidation_present,
            "live thesis carries its falsifier"
            if invalidation_present
            else f"no live thesis invalidation declared{parked_note}",
        ),
        "manual_portfolio_fit": (
            False,
            "no declared portfolio-fit assessment exists; gate "
            "manual_portfolio_risk_available is observed, never declared "
            "NOT_REQUIRED",
        ),
    }
    checks: dict[str, dict[str, Any]] = {}
    for name in profile.required_evidence:
        present, detail = known.get(
            name, (False, "no holder exists for this evidence")
        )
        checks[name] = {"present": present, "detail": detail}
    return checks


def _check_profile_is_applicable(
    *, profile: StrategyProfile, config: AnalysisConfig
) -> None:
    """Fail-closed: refuse to reference a profile the snapshot cannot honor."""
    if not profile.decision_horizons_months:
        raise StrategyProfileError(
            f"profile {profile.profile_id}: no decision horizon declared, the "
            "published horizon cannot be checked against the profile"
        )
    if config.horizon not in profile.horizons:
        raise StrategyProfileError(
            f"profile {profile.profile_id}: published horizon "
            f"{config.horizon!r} is not one of the declared decision horizons "
            f"{list(profile.horizons)}"
        )
    if (
        "manual_portfolio_fit" in profile.required_evidence
        and not config.portfolio_risk_required
    ):
        raise StrategyProfileError(
            f"profile {profile.profile_id}: requires manual_portfolio_fit, so "
            "the portfolio-risk gate must be observed, never declared "
            "NOT_REQUIRED (set AnalysisConfig.portfolio_risk_required)"
        )


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
    calendar_ref: Optional[CalendarSnapshotRef] = None,
    engine: Optional[AdviceEngine] = None,
) -> dict[str, Any]:
    """Build the ``opportunities/global`` snapshot content (pure).

    Identical inputs produce an identical dict. Each candidate's verdict is
    produced by :func:`vertex_worker.analysis.build_analysis_content` (the
    single dossier pipeline, hence THE single ``AdviceEngine``); this builder
    computes no gate, no score and no verdict of its own. It groups, checks
    evidence presence, publishes exclusion reasons and orders — and it
    REFUSES to publish a snapshot whose candidates contradict the
    ``AdviceResult`` contract (see the module docstring).
    """
    now = _require_aware_utc(now)
    _check_profile_is_applicable(profile=profile, config=config)
    engine = engine if engine is not None else AdviceEngine()
    sector_of = _sector_of()
    catalyst_counts, calendar_provenance = _calendar_evidence(
        calendar_content, calendar_ref, now=now, max_age=config.lookback
    )

    qualified: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    exclusion_reasons: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    population_counts: dict[str, int] = {}
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
        dossier_population = dossier["population"]
        population_counts[dossier_population] = (
            population_counts.get(dossier_population, 0) + 1
        )
        considered_total += dossier["coverage"]["observations_considered"]

        evidence_checks = _required_evidence_checks(
            profile=profile,
            sector=sector_of.get(ticker),
            bars_ok=dossier["bars"]["status"] == "OK",
            catalyst_events=catalyst_counts.get(ticker, 0),
            theses=theses_by_ticker.get(ticker, ()),
        )
        missing_evidence = sorted(
            name
            for name, check in evidence_checks.items()
            if not check["present"]
        )
        gates = [
            {
                "gate_id": gate["gate_id"],
                "status": gate["status"],
                "reason_code": gate["reason_code"],
            }
            for gate in advice["gates"]
        ]
        blocking = [gate for gate in gates if gate["status"] == GATE_STATUS_BLOCK]
        degraded = [
            gate["gate_id"] for gate in gates if gate["status"] == GATE_STATUS_DEGRADE
        ]
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
            "gates": gates,
            "degraded_gates": degraded,
            "required_evidence": evidence_checks,
            "missing_evidence": missing_evidence,
            "evidence_cluster_ids": list(advice["evidence_ids"]),
            "scenario_ids": list(advice["scenario_ids"]),
            "bars_status": dossier["bars"]["status"],
            "scenarios_status": dossier["scenarios"]["status"],
            "population": dossier_population,
            "synthetic": dossier_population == "SYNTHETIC",
        }

        group = group_for_status(status)
        # Structural cross-check, fail-closed: the group derived from the
        # status and the PUBLISHED gates must agree. A disagreement means the
        # verdict was not produced by the canonical AdviceResult contract, so
        # nothing is published rather than displaying a false card.
        if group == "QUALIFIED_GROUP" and blocking:
            raise RuntimeError(
                "blocking gate in the qualified group: "
                f"{ticker} ({status}) carries BLOCK gate(s) "
                f"{[gate['gate_id'] for gate in blocking]}"
            )
        if group == "EXCLUDED_GROUP" and not blocking:
            raise RuntimeError(
                "closed candidate without any blocking gate: "
                f"{ticker} ({status}) publishes no BLOCK gate"
            )

        if group == "QUALIFIED_GROUP" and not missing_evidence:
            candidate["exclusion"] = None
            candidate["primary_exclusion_reason"] = None
            qualified.append(candidate)
            continue

        if group == "EXCLUDED_GROUP":
            primary = {
                "gate_id": str(blocking[0]["gate_id"]),
                "reason_code": str(blocking[0]["reason_code"]),
            }
            candidate["primary_exclusion_reason"] = primary
            candidate["exclusion"] = {
                "kind": EXCLUSION_KIND_CLOSED_STATUS,
                "gate_id": primary["gate_id"],
                "reason_code": primary["reason_code"],
                "missing_evidence": list(missing_evidence),
                "detail": (
                    f"closed by gate {primary['gate_id']} "
                    f"({primary['reason_code']})"
                ),
            }
            key = f"{primary['gate_id']}:{primary['reason_code']}"
        else:
            # Open status, no blocking gate, but the profile's required
            # evidence is incomplete: INADMISSIBLE, never merely lower ranked.
            candidate["primary_exclusion_reason"] = None
            candidate["exclusion"] = {
                "kind": EXCLUSION_KIND_MISSING_EVIDENCE,
                "gate_id": None,
                "reason_code": None,
                "missing_evidence": list(missing_evidence),
                "detail": (
                    "required evidence of profile "
                    f"{profile.profile_id}@{profile.version} absent: "
                    + ", ".join(missing_evidence)
                ),
            }
            key = f"required_evidence:{missing_evidence[0]}"
        exclusion_reasons[key] = exclusion_reasons.get(key, 0) + 1
        excluded.append(candidate)

    qualified.sort(
        key=lambda c: (
            _STATUS_RANK[c["advice"]["status"]],
            len(c["degraded_gates"]),
            c["ticker"],
        )
    )
    for rank, candidate in enumerate(qualified, start=1):
        candidate["rank"] = rank
    excluded.sort(key=lambda c: c["ticker"])

    # Population DERIVED from the dossiers actually computed (never declared):
    # a single synthetic dossier makes the whole snapshot synthetic
    # (conservative), and a population is REAL only when a real dossier was
    # really retained.
    if population_counts.get("SYNTHETIC"):
        population = "SYNTHETIC"
    elif population_counts.get("REAL"):
        population = "REAL"
    else:
        population = "EMPTY"

    limitations: list[str] = []
    if population == "SYNTHETIC":
        limitations.append("SYNTHETIC development population")
        if population_counts.get("REAL"):
            limitations.append(
                f"mixed population: {population_counts.get('SYNTHETIC', 0)} "
                f"synthetic and {population_counts.get('REAL', 0)} real "
                "dossier(s); the snapshot is labeled SYNTHETIC (conservative)"
            )
    elif population == "EMPTY":
        limitations.append(
            "EMPTY population: no observation was retained for this universe"
        )
    limitations.append(
        "instrument-class conformity to the profile "
        f"({', '.join(profile.instruments)}) is not verified: no "
        "instrument-class source exists for this population"
    )

    return {
        "schema_version": OPPORTUNITIES_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        "population": population,
        "engine_version": ENGINE_VERSION,
        "profile_ref": {
            "id": profile.profile_id,
            "version": profile.version,
            "source": profile.source_path,
            "applied": [
                "required_evidence (admissibility of every candidate)",
                f"decision_horizons_months (published horizon {config.horizon})",
            ],
            "not_applied": [dict(entry) for entry in PROFILE_FIELDS_NOT_APPLIED],
        },
        "calendar_ref": calendar_provenance,
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
        "limitations": limitations,
        "coverage": {
            "universe_size": len(config.instruments),
            "qualified_count": len(qualified),
            "excluded_count": len(excluded),
            "status_counts": dict(sorted(status_counts.items())),
            "population_counts": dict(sorted(population_counts.items())),
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

    @property
    def profile(self) -> StrategyProfile:
        """The injected strategy profile this handler applies."""
        return self._profile

    @property
    def config(self) -> AnalysisConfig:
        """The injected analysis configuration this handler applies."""
        return self._config

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
        calendar_ref = (
            None
            if calendar is None
            else CalendarSnapshotRef(
                kind=SNAPSHOT_KIND_CALENDAR,
                key=CALENDAR_KEY,
                version=calendar.version,
                as_of=calendar.as_of,
            )
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
            calendar_ref=calendar_ref,
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
    profiles_path: Optional[Path] = None,
) -> None:
    """Register the opportunities handler on ``opportunities.refresh``.

    The profile is INJECTED: either directly (``profile``) or by the manifest
    path to read (``profiles_path``). Without either, the documented
    source-checkout fallback :data:`DEFAULT_PROFILES_PATH` is used.
    """
    if profile is not None and profiles_path is not None:
        raise ValueError(
            "profile and profiles_path are exclusive: inject one authority"
        )
    resolved_profile = (
        profile
        if profile is not None
        else load_strategy_profile(path=profiles_path)
    )
    registry.register(
        TOPIC_OPPORTUNITIES_REFRESH,
        OpportunitiesHandler(
            config=config, profile=resolved_profile, clock=clock
        ),
    )
