"""Opportunities API (page 04): verbatim snapshot relay.

The API computes NO gate, NO rank and NO verdict here: it relays the
worker's ``opportunities/global`` snapshot exactly as persisted (or an
honest empty state), after a fail-closed shape check that refuses to relay a
snapshot violating the page's core invariant.

That invariant crosses the PUBLISHED FACTS, never the status string alone
(mirror of ``vertex_worker.opportunities.build_opportunities_content``):

1. a qualified candidate carries an open status;
2. every published gate carries a CANONICAL status (``PASS``/``DEGRADE``/
   ``BLOCK``), a CANONICAL identity (its ``gate_id`` belongs to
   :data:`~vertex_core.decision.gates.GATE_CATALOG`, read here, never
   redefined) and appears at most once — a verdict vouched by no gate, by a
   made-up gate, by the same gate twice, or by a gate closed under another
   label (``block``, ``CLOSED``...), is refused instead of read as harmless;
3. a qualified candidate publishes the COMPLETE catalog — ``AdviceEngine``
   evaluates every gate of the catalog for every dossier, so a positive card
   vouched for by a subset hides the gates that were never run — and NO
   ``BLOCK`` gate: a blocking gate can never coexist with membership of the
   qualified group, whatever the status says;
4. a qualified candidate holds every required evidence of the profile
   (``missing_evidence`` empty and every ``required_evidence`` entry
   present);
5. the required-evidence set of EVERY candidate is exactly the set the
   REFERENCED profile declares in ``manifests/strategy-profiles.yaml``, and
   the published horizon is one of that profile's declared decision
   horizons.

Symmetrically, every excluded candidate must publish WHY it is excluded: a
canonical closed status attributed to a gate that is REALLY ``BLOCK``, or the
missing required evidence of the profile. Finally, a candidate is identified
by its ``ticker`` and belongs to EXACTLY ONE group: the same instrument shown
as admissible and as closed on the same page is a contradiction, not two
cards. A snapshot that fails any of these is refused instead of displayed.

Two facts about the referenced profile cannot be checked against the snapshot
alone, so the relay reads the SAME committed manifest the worker reads
(``manifests/strategy-profiles.yaml``, the documented source-checkout path,
injectable through ``profiles_path``) — exactly the pattern
``vertex_api.capability_manifest`` already uses for the IBKR capability
manifest. The relay parses it read-only; it never recomputes an evidence, a
gate or a verdict. The alternative (the snapshot publishing its own required
set) would let a forged snapshot declare its own admissibility rules, so the
manifest stays the authority.

FRESHNESS (fail-closed, ``financial-safety.md``: never silently keep an old
verdict). The worker refuses to publish a snapshot it cannot vouch for
(fail-closed ``RuntimeError`` -> retry -> DEAD message): nothing new is then
persisted, and without a bound the page would keep serving the previous
verdict as current, forever. Past :data:`OPPORTUNITIES_MAX_AGE` the relay
serves ``state = "stale"`` with the age and the reason — never ``ok``. The
age is measured on SERVER timestamps (the persisted ``as_of`` COLUMN and the
relay clock), never on the ``as_of`` string inside the content, which is
persisted data like any other.

CLOCK DRIFT (P2-J). The worker and the API are DISTINCT PROCESSES reading
their own clock, so a snapshot dated slightly ahead of the relay is a normal
scheduling artefact, not a forged payload. Up to
:data:`OPPORTUNITIES_CLOCK_DRIFT_TOLERANCE` the drift is absorbed (the age is
clamped to zero — a negative age never reaches the wire). BEYOND it the relay
answers ``state = "clock_inconsistent"``: the snapshot cannot be dated, so no
verdict is served, and the reason names the CLOCK — never "invalid snapshot
content", which would blame the persisted payload for a server-side clock
problem.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import Field

from vertex_api.snapshot_views import (
    SnapshotContentError,
    _parse_utc,
    _require_list,
    _require_mapping,
    _require_str,
    _wire_mapping,
    checked_relayed_content,
)
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_core.data.freshness import get_freshness_policy
from vertex_core.decision.gates import GATE_CATALOG
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "CLOSED_STATUSES",
    "DEFAULT_PROFILES_PATH",
    "EXCLUSION_KIND_CLOSED_STATUS",
    "EXCLUSION_KIND_MISSING_EVIDENCE",
    "GATE_CATALOG_IDS",
    "GATE_STATUSES",
    "OPPORTUNITIES_CLOCK_DRIFT_TOLERANCE",
    "OPPORTUNITIES_FRESHNESS_POLICY",
    "OPPORTUNITIES_MAX_AGE",
    "QUALIFIED_STATUSES",
    "REASON_CLOCK_INCONSISTENT",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "REASON_SNAPSHOT_STALE",
    "SNAPSHOT_KIND_OPPORTUNITIES",
    "OpportunitiesResponse",
    "RelayStrategyProfile",
    "StrategyProfileManifestError",
    "build_opportunities_response",
    "load_relay_strategy_profiles",
]

SNAPSHOT_KIND_OPPORTUNITIES = "opportunities"
SNAPSHOT_KEY_GLOBAL = "global"

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"

QUALIFIED_STATUSES = frozenset({"OBSERVE", "REVIEW", "QUALIFIED"})
"""The ONLY statuses the qualified group may carry (relay-side guard)."""

CLOSED_STATUSES = frozenset({"BLOCKED", "INSUFFICIENT_DATA"})
"""The ONLY statuses a status-based exclusion may carry."""

GATE_STATUSES = frozenset({"PASS", "DEGRADE", "BLOCK"})
"""The ONLY gate statuses the canonical ``AdviceResult`` contract defines.

Deny-by-default: any other label (``block``, ``CLOSED``, ``KO``...) is refused
rather than treated as "not BLOCK, hence harmless" — that reading is exactly
how a closed gate used to walk into the qualified group.
"""

GATE_STATUS_BLOCK = "BLOCK"

GATE_CATALOG_IDS: frozenset[str] = frozenset(spec.gate_id for spec in GATE_CATALOG)
"""Canonical decision-gate identities, READ from ``vertex_core`` (P2-I).

The relay never redefines, extends or shortens this set: ``vertex_core`` is
the single authority of the decision gates (``architecture.md``). A published
``gate_id`` outside it names a gate NO engine of this system evaluates, so it
vouches for nothing; and the qualified group must publish this set ENTIRELY,
since ``AdviceEngine`` evaluates the whole catalog for every dossier.
"""

EXCLUSION_KIND_CLOSED_STATUS = "CLOSED_STATUS"
EXCLUSION_KIND_MISSING_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
_EXCLUSION_KINDS = frozenset(
    {EXCLUSION_KIND_CLOSED_STATUS, EXCLUSION_KIND_MISSING_EVIDENCE}
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

DEFAULT_PROFILES_PATH = _REPO_ROOT / "manifests" / "strategy-profiles.yaml"
"""Documented source-checkout path of the strategy-profile manifest.

Same contract as ``vertex_api.capability_manifest.DEFAULT_MANIFEST_PATH``:
a committed file, read-only, so the relay stays deterministic. Every entry
point can inject another path (``profiles_path=``).
"""

OPPORTUNITIES_FRESHNESS_POLICY = "daily_bar"
"""Freshness policy of the FRESHEST input an opportunities snapshot can have.

Every candidate dossier is built from validated DAILY BARS, so the snapshot
can never be fresher than that observation family. The bound below is the
registry's own versioned value — not a number invented here.
"""

_FRESHNESS_POLICY = get_freshness_policy(OPPORTUNITIES_FRESHNESS_POLICY)

OPPORTUNITIES_MAX_AGE = timedelta(seconds=_FRESHNESS_POLICY.ttl_closed_seconds)
"""Freshness budget of the relayed snapshot (CLOSED-session TTL of the
``daily_bar`` policy: it covers a normal weekend, so a legitimate quiet
period is never mislabeled). The relay knows no session state, hence the
conservative bound of the two. Past it the snapshot is served ``stale``.
"""

REASON_SNAPSHOT_STALE = (
    "snapshot older than its freshness budget: age {age} s for a budget of "
    "{budget} s ({policy}@{version} closed-session TTL); the worker published "
    "nothing newer"
)
"""Served instead of ``reason = None`` when the budget is exceeded."""

OPPORTUNITIES_CLOCK_DRIFT_TOLERANCE = timedelta(seconds=5)
"""Accepted lead of the persisted ``as_of`` over the relay clock (P2-J).

The worker and the API are distinct processes: each stamps its own clock
reading, and the snapshot row can legitimately carry an instant a fraction of
a second — occasionally a few seconds, under load or right after an NTP step
— AHEAD of the instant the relay reads. That is a scheduling artefact of two
processes, never a statement about the content, so it is absorbed here and
the published age is clamped to zero.

The bound is deliberately SMALL and named: it covers process skew, not a
misconfigured clock. Beyond it the relay stops guessing and says so (see
:data:`REASON_CLOCK_INCONSISTENT`) rather than dating a verdict it cannot
date, or blaming the stored content for a clock problem.
"""

REASON_CLOCK_INCONSISTENT = (
    "server clock inconsistency: the snapshot is dated {drift} s ahead of the "
    "relay clock, beyond the declared drift tolerance of {tolerance} s. The "
    "verdict cannot be dated, so it is not served. This is a CLOCK problem "
    "between the worker and the API, NOT an invalid snapshot content"
)
"""Served with ``state = "clock_inconsistent"`` past the drift tolerance."""

_ZERO = timedelta(0)


class StrategyProfileManifestError(RuntimeError):
    """The strategy-profile manifest is missing, unreadable or invalid.

    A committed file the deployment must carry — like the capability
    manifest, whose absence already fails application startup. It is NOT a
    snapshot-content defect, so it is never reported as one.
    """


@dataclass(frozen=True)
class RelayStrategyProfile:
    """The two profile facts the relay must cross with a snapshot."""

    profile_id: str
    version: str
    required_evidence: frozenset[str]
    horizons: frozenset[str]


def _manifest_str(entry: Mapping[str, Any], key: str, profile_id: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise StrategyProfileManifestError(
            f"profile {profile_id}: {key} must be a non-empty string"
        )
    return value


def _manifest_required_evidence(
    entry: Mapping[str, Any], profile_id: str
) -> frozenset[str]:
    """The profile's admissibility facts — never empty (fail-closed).

    An empty ``required_evidence`` list would silently disable EVERY
    admissibility check of the profile, so the relay refuses to load such a
    profile instead of qualifying candidates against nothing.
    """
    raw = entry.get("required_evidence")
    if not isinstance(raw, list) or not raw:
        raise StrategyProfileManifestError(
            f"profile {profile_id}: required_evidence must be a non-empty list"
        )
    names: set[str] = set()
    for name in raw:
        if not isinstance(name, str) or not name:
            raise StrategyProfileManifestError(
                f"profile {profile_id}: required_evidence entries must be "
                "non-empty strings"
            )
        names.add(name)
    return frozenset(names)


def _manifest_horizons(entry: Mapping[str, Any], profile_id: str) -> frozenset[str]:
    """Canonical labels of the declared decision horizons (may be empty).

    A profile declaring none cannot vouch for any published horizon; the
    relay refuses such a snapshot at check time rather than at load time, so
    the other profiles of the manifest stay loadable.
    """
    raw = entry.get("decision_horizons_months")
    if raw is None:
        return frozenset()
    if not isinstance(raw, list) or not raw:
        raise StrategyProfileManifestError(
            f"profile {profile_id}: decision_horizons_months must be a "
            "non-empty list when declared"
        )
    labels: set[str] = set()
    for months in raw:
        if isinstance(months, bool) or not isinstance(months, int) or months < 1:
            raise StrategyProfileManifestError(
                f"profile {profile_id}: decision_horizons_months must be "
                "positive integers"
            )
        labels.add(f"{months}m")
    return frozenset(labels)


@lru_cache(maxsize=8)
def _load_profiles(resolved: str) -> Mapping[str, RelayStrategyProfile]:
    try:
        raw = yaml.safe_load(Path(resolved).read_text(encoding="utf-8"))
    except OSError as exc:
        raise StrategyProfileManifestError(
            f"cannot read the strategy-profile manifest {resolved}"
        ) from exc
    except yaml.YAMLError as exc:
        raise StrategyProfileManifestError(
            f"invalid YAML in the strategy-profile manifest {resolved}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise StrategyProfileManifestError("manifest root must be a mapping")
    profiles = raw.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise StrategyProfileManifestError("manifest carries no 'profiles' list")
    parsed: dict[str, RelayStrategyProfile] = {}
    for entry in profiles:
        if not isinstance(entry, Mapping):
            raise StrategyProfileManifestError("every profile must be a mapping")
        profile_id = _manifest_str(entry, "id", "<unnamed>")
        if profile_id in parsed:
            raise StrategyProfileManifestError(
                f"profile {profile_id}: declared twice"
            )
        parsed[profile_id] = RelayStrategyProfile(
            profile_id=profile_id,
            version=_manifest_str(entry, "version", profile_id),
            required_evidence=_manifest_required_evidence(entry, profile_id),
            horizons=_manifest_horizons(entry, profile_id),
        )
    return parsed


def load_relay_strategy_profiles(
    path: Path | None = None,
) -> Mapping[str, RelayStrategyProfile]:
    """Parse the committed strategy-profile manifest (cached, read-only)."""
    resolved = Path(path) if path is not None else DEFAULT_PROFILES_PATH
    return _load_profiles(str(resolved))


def _utc_now() -> datetime:
    """Relay clock seam.

    The opportunities route carries no clock dependency, so the default
    instant is read here; every caller may inject ``now`` instead (tests
    always do — no test depends on the real time).
    """
    return datetime.now(UTC)


class OpportunitiesResponse(ContractModel):
    """The last published opportunities snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted content VERBATIM: profile
    reference (id + version + what is really applied), calendar provenance,
    documented lexicographic ordering, qualified and excluded candidates with
    their gates, honest evidence checks and published exclusion reasons (the
    page's honest empty state on synthetic data). ``state = "stale"`` relays
    the SAME content, but says it is past its freshness budget and publishes
    why — an old verdict is never presented as current. ``state = "empty"``
    means the worker never published. ``state = "clock_inconsistent"`` means
    the snapshot is dated further ahead of the relay clock than the declared
    drift tolerance: the verdict cannot be dated, so the content is WITHHELD
    (``content = None``) and ``reason`` names the clock — the fault is
    server-side, not in the persisted payload.

    ``age_seconds`` is published in every DATABLE state (server timestamps
    only), so the interface can always show how old the verdict is; it stays
    ``None`` exactly when no honest age exists (``empty``,
    ``clock_inconsistent``).
    """

    state: Literal["ok", "stale", "empty", "clock_inconsistent"]
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: Annotated[int, Field(ge=0)] | None
    content: FrozenStrMapping | None
    reason: NonEmptyStr | None


def _published_gates(
    candidate: Mapping[str, Any], *, field: str
) -> tuple[tuple[str, str], ...]:
    """Every published gate as ``(gate_id, status)``, vocabulary and identity
    enforced.

    Fail-closed on four counts: an unknown gate STATUS is refused (never read
    as "not BLOCK, hence harmless"); a gate IDENTITY outside the canonical
    :data:`GATE_CATALOG_IDS` is refused, because a gate no engine of this
    system evaluates vouches for nothing (P2-I); the same gate published
    TWICE is refused, since a duplicate can pad an evaluation while a real
    gate stays missing; and a candidate publishing NO gate is refused too —
    its verdict would then be vouched for by nothing.
    """
    gates = _require_list(candidate.get("gates"), field=f"{field}.gates")
    if not gates:
        raise SnapshotContentError(
            f"{field}.gates: no gate published, the verdict of this candidate "
            "is vouched for by no gate",
            field=f"{field}.gates",
        )
    published: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(gates):
        gate = _require_mapping(raw, field=f"{field}.gates[{index}]")
        gate_id = _require_str(
            gate.get("gate_id"), field=f"{field}.gates[{index}].gate_id"
        )
        status = _require_str(
            gate.get("status"), field=f"{field}.gates[{index}].status"
        )
        if status not in GATE_STATUSES:
            raise SnapshotContentError(
                f"{field}.gates[{index}].status: canonical gate status "
                "PASS/DEGRADE/BLOCK required",
                field=f"{field}.gates[{index}].status",
            )
        if gate_id not in GATE_CATALOG_IDS:
            raise SnapshotContentError(
                f"{field}.gates[{index}].gate_id: gate absent from the "
                "canonical decision-gate catalog of vertex_core "
                "(GATE_CATALOG); it vouches for nothing",
                field=f"{field}.gates[{index}].gate_id",
            )
        if gate_id in seen:
            raise SnapshotContentError(
                f"{field}.gates[{index}].gate_id: this gate is published "
                "twice; a duplicate can pad an evaluation while a real gate "
                "stays missing",
                field=f"{field}.gates[{index}].gate_id",
            )
        seen.add(gate_id)
        published.append((gate_id, status))
    return tuple(published)


def _missing_evidence(
    candidate: Mapping[str, Any], *, field: str, profile: RelayStrategyProfile
) -> list[str]:
    """Missing required evidence, cross-checked against profile and map.

    Two independent checks: the published evidence set must be EXACTLY the
    set the referenced profile requires (a snapshot never gets to shrink its
    own admissibility rules), and ``missing_evidence`` must agree with the
    presence map.
    """
    published = _require_list(
        candidate.get("missing_evidence"), field=f"{field}.missing_evidence"
    )
    missing = [
        _require_str(name, field=f"{field}.missing_evidence[{index}]")
        for index, name in enumerate(published)
    ]
    checks = _require_mapping(
        candidate.get("required_evidence"), field=f"{field}.required_evidence"
    )
    if frozenset(checks) != profile.required_evidence:
        raise SnapshotContentError(
            f"{field}.required_evidence: the published required evidence set "
            f"is not the set profile {profile.profile_id}@{profile.version} "
            "declares",
            field=f"{field}.required_evidence",
        )
    absent: list[str] = []
    for name, raw in checks.items():
        check = _require_mapping(
            raw, field=f"{field}.required_evidence.{name}"
        )
        if check.get("present") is not True:
            absent.append(str(name))
    absent.sort()
    if sorted(missing) != absent:
        raise SnapshotContentError(
            f"{field}: missing_evidence {sorted(missing)} contradicts the "
            f"published required_evidence presence {absent}",
            field=f"{field}.missing_evidence",
        )
    return missing


def _checked_horizon(
    advice: Mapping[str, Any], *, field: str, profile: RelayStrategyProfile
) -> str:
    """The published horizon must be one the referenced profile declares."""
    horizon = _require_str(advice.get("horizon"), field=f"{field}.advice.horizon")
    if not profile.horizons:
        raise SnapshotContentError(
            f"{field}.advice.horizon: profile {profile.profile_id}@"
            f"{profile.version} declares no decision horizon, so no published "
            "horizon can be vouched for",
            field=f"{field}.advice.horizon",
        )
    if horizon not in profile.horizons:
        raise SnapshotContentError(
            f"{field}.advice.horizon: the published horizon is not a declared "
            f"decision horizon of profile {profile.profile_id}@"
            f"{profile.version}",
            field=f"{field}.advice.horizon",
        )
    return horizon


def _check_qualified(
    candidate: Mapping[str, Any], *, field: str, profile: RelayStrategyProfile
) -> None:
    advice = _require_mapping(candidate.get("advice"), field=f"{field}.advice")
    status = advice.get("status")
    if status not in QUALIFIED_STATUSES:
        raise SnapshotContentError(
            f"{field}: closed status {status!r} may never sit in the "
            "qualified group",
            field=f"{field}.advice.status",
        )
    _checked_horizon(advice, field=field, profile=profile)
    gates = _published_gates(candidate, field=field)
    if frozenset(gate_id for gate_id, _ in gates) != GATE_CATALOG_IDS:
        raise SnapshotContentError(
            f"{field}.gates: the published gates are not the complete "
            "canonical decision-gate catalog of vertex_core; a verdict "
            "vouched for by a partial evaluation may never sit in the "
            "qualified group",
            field=f"{field}.gates",
        )
    if GATE_STATUS_BLOCK in {status for _, status in gates}:
        raise SnapshotContentError(
            f"{field}: a candidate carrying a BLOCK gate may never sit in "
            "the qualified group",
            field=f"{field}.gates",
        )
    missing = _missing_evidence(candidate, field=field, profile=profile)
    if missing:
        raise SnapshotContentError(
            f"{field}: required evidence {missing} absent, the candidate is "
            "not admissible to the qualified group",
            field=f"{field}.missing_evidence",
        )


def _check_excluded(
    candidate: Mapping[str, Any], *, field: str, profile: RelayStrategyProfile
) -> None:
    advice = _require_mapping(candidate.get("advice"), field=f"{field}.advice")
    status = advice.get("status")
    exclusion = _require_mapping(candidate.get("exclusion"), field=f"{field}.exclusion")
    kind = _require_str(exclusion.get("kind"), field=f"{field}.exclusion.kind")
    if kind not in _EXCLUSION_KINDS:
        raise SnapshotContentError(
            f"{field}.exclusion.kind: unknown kind {kind!r}",
            field=f"{field}.exclusion.kind",
        )
    _checked_horizon(advice, field=field, profile=profile)
    gates = _published_gates(candidate, field=field)
    missing = _missing_evidence(candidate, field=field, profile=profile)
    if kind == EXCLUSION_KIND_CLOSED_STATUS:
        if status not in CLOSED_STATUSES:
            raise SnapshotContentError(
                f"{field}: canonical closed status required",
                field=f"{field}.advice.status",
            )
        gate_id = _require_str(
            exclusion.get("gate_id"), field=f"{field}.exclusion.gate_id"
        )
        _require_str(
            exclusion.get("reason_code"), field=f"{field}.exclusion.reason_code"
        )
        blocking = {name for name, gate_status in gates if gate_status == GATE_STATUS_BLOCK}
        if not blocking:
            raise SnapshotContentError(
                f"{field}: a closed status requires a published BLOCK gate",
                field=f"{field}.gates",
            )
        if gate_id not in blocking:
            raise SnapshotContentError(
                f"{field}.exclusion.gate_id: the exclusion is attributed to a "
                "gate that publishes no BLOCK status",
                field=f"{field}.exclusion.gate_id",
            )
        return
    if status not in QUALIFIED_STATUSES:
        raise SnapshotContentError(
            f"{field}: a closed status must be attributed to its blocking "
            f"gate, not to {EXCLUSION_KIND_MISSING_EVIDENCE}",
            field=f"{field}.exclusion.kind",
        )
    if not missing:
        raise SnapshotContentError(
            f"{field}: {EXCLUSION_KIND_MISSING_EVIDENCE} requires at least "
            "one missing required evidence",
            field=f"{field}.missing_evidence",
        )


def _register_identity(
    candidate: Mapping[str, Any], *, field: str, seen: set[str]
) -> None:
    """One candidate = one ticker = ONE group (P2-I).

    The same instrument published as admissible AND as closed on the same
    page is a contradiction, not two cards: nothing lets the interface — or
    the reader — tell which verdict holds. Refused rather than displayed.
    """
    ticker = _require_str(candidate.get("ticker"), field=f"{field}.ticker")
    if ticker in seen:
        raise SnapshotContentError(
            f"{field}.ticker: this candidate is published twice across the "
            "qualified and excluded groups; a candidate belongs to exactly "
            "one group",
            field=f"{field}.ticker",
        )
    seen.add(ticker)


def _referenced_profile(
    content: Mapping[str, Any], *, profiles_path: Path | None
) -> RelayStrategyProfile:
    """The declared profile the snapshot references (fail-closed)."""
    profile_ref = _require_mapping(content.get("profile_ref"), field="profile_ref")
    profile_id = _require_str(profile_ref.get("id"), field="profile_ref.id")
    version = _require_str(profile_ref.get("version"), field="profile_ref.version")
    profiles = load_relay_strategy_profiles(profiles_path)
    profile = profiles.get(profile_id)
    if profile is None:
        raise SnapshotContentError(
            "profile_ref.id: the referenced strategy profile is not declared "
            "in the manifest",
            field="profile_ref.id",
        )
    if profile.version != version:
        raise SnapshotContentError(
            "profile_ref.version: the referenced version is not the version "
            "the manifest declares for this profile",
            field="profile_ref.version",
        )
    return profile


def _snapshot_age(snapshot: CurrentSnapshot, *, now: datetime) -> timedelta:
    """Signed age measured on SERVER timestamps only (never on content).

    The result is NEGATIVE when the snapshot row is dated ahead of the relay
    clock. That is a two-process reality, not a content defect, so it is
    returned as-is and interpreted by the caller against
    :data:`OPPORTUNITIES_CLOCK_DRIFT_TOLERANCE` (P2-J). Only a genuinely
    unusable stamp — absent, not a datetime, or naive — is a content defect.
    """
    as_of = snapshot.as_of
    if not isinstance(as_of, datetime):
        raise SnapshotContentError(
            "snapshot.as_of: datetime required", field="snapshot.as_of"
        )
    if as_of.tzinfo is None or as_of.tzinfo.utcoffset(as_of) is None:
        raise SnapshotContentError(
            "snapshot.as_of: naive datetime rejected", field="snapshot.as_of"
        )
    return now.astimezone(UTC) - as_of.astimezone(UTC)


def build_opportunities_response(
    snapshot: CurrentSnapshot | None,
    *,
    now: datetime | None = None,
    profiles_path: Path | None = None,
) -> OpportunitiesResponse:
    """Relay the last opportunities snapshot verbatim, or the empty state.

    Fail-closed relay guard (never a recomputation): the qualified group must
    carry only open statuses, canonical gate statuses, at least one published
    gate, no blocking gate and no missing required evidence; every candidate
    must publish exactly the required-evidence set and a horizon the
    REFERENCED profile declares; and every excluded candidate must publish
    its exclusion, attributed to a gate that is really ``BLOCK``. A snapshot
    violating any of this is refused instead of displayed.

    Every candidate is identified by its ``ticker`` and may appear in exactly
    one group: a candidate published twice is refused, never shown as two
    contradictory cards.

    Past :data:`OPPORTUNITIES_MAX_AGE` the (still valid) content is served
    with ``state = "stale"``, its age and its reason — never ``ok``. A
    snapshot dated ahead of the relay clock beyond
    :data:`OPPORTUNITIES_CLOCK_DRIFT_TOLERANCE` is answered
    ``state = "clock_inconsistent"`` WITHOUT content: a clock problem is
    reported as a clock problem, never as invalid stored content.
    """
    if snapshot is None:
        return OpportunitiesResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
            content=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = _wire_mapping(snapshot.content, field="content")
    profile = _referenced_profile(content, profiles_path=profiles_path)
    qualified = _require_list(content.get("qualified"), field="qualified")
    excluded = _require_list(content.get("excluded"), field="excluded")
    seen_candidates: set[str] = set()
    for index, raw in enumerate(qualified):
        candidate = _require_mapping(raw, field=f"qualified[{index}]")
        _check_qualified(candidate, field=f"qualified[{index}]", profile=profile)
        _register_identity(
            candidate, field=f"qualified[{index}]", seen=seen_candidates
        )
    for index, raw in enumerate(excluded):
        candidate = _require_mapping(raw, field=f"excluded[{index}]")
        _check_excluded(candidate, field=f"excluded[{index}]", profile=profile)
        _register_identity(
            candidate, field=f"excluded[{index}]", seen=seen_candidates
        )
    _require_mapping(content.get("exclusion_reasons"), field="exclusion_reasons")
    # FORM of every relayed value (P1-1). The WHOLE content is served
    # verbatim, so a decimal, a nature label or a piece of prose out of shape
    # must never reach the wire. Run AFTER the invariants above so a broken
    # candidate keeps naming the invariant it breaks rather than the shape of
    # one of its fields.
    checked_relayed_content(content)

    age = _snapshot_age(snapshot, now=_utc_now() if now is None else now)
    if age < -OPPORTUNITIES_CLOCK_DRIFT_TOLERANCE:
        # The snapshot is dated further ahead than two processes can drift:
        # its age is unknown, so no verdict is served — and the reason names
        # the CLOCK, never the persisted content (P2-J).
        return OpportunitiesResponse(
            state="clock_inconsistent",
            snapshot_version=snapshot.version,
            as_of=None,
            age_seconds=None,
            content=None,
            reason=REASON_CLOCK_INCONSISTENT.format(
                drift=int(-age.total_seconds()),
                tolerance=int(OPPORTUNITIES_CLOCK_DRIFT_TOLERANCE.total_seconds()),
            ),
        )
    if age < _ZERO:
        # Tolerated process skew: the age is clamped, never published negative.
        age = _ZERO
    stale = age > OPPORTUNITIES_MAX_AGE
    return OpportunitiesResponse(
        state="stale" if stale else "ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        age_seconds=int(age.total_seconds()),
        content=content,
        reason=(
            REASON_SNAPSHOT_STALE.format(
                age=int(age.total_seconds()),
                budget=int(OPPORTUNITIES_MAX_AGE.total_seconds()),
                policy=_FRESHNESS_POLICY.name,
                version=_FRESHNESS_POLICY.version,
            )
            if stale
            else None
        ),
    )
