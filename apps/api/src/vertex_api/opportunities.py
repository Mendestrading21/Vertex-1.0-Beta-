"""Opportunities API (page 04): verbatim snapshot relay.

The API computes NO gate, NO rank and NO verdict here: it relays the
worker's ``opportunities/global`` snapshot exactly as persisted (or an
honest empty state), after a fail-closed shape check that refuses to relay a
snapshot violating the page's core invariant.

That invariant crosses THREE published facts, never the status string alone
(mirror of ``vertex_worker.opportunities.build_opportunities_content``):

1. a qualified candidate carries an open status;
2. a qualified candidate publishes NO ``BLOCK`` gate — a blocking gate can
   never coexist with membership of the qualified group, whatever the status
   says;
3. a qualified candidate holds every required evidence of the profile
   (``missing_evidence`` empty and every ``required_evidence`` entry
   present).

Symmetrically, every excluded candidate must publish WHY it is excluded: a
canonical closed status attributed to its blocking gate, or the missing
required evidence of the profile. A snapshot that fails any of these is
refused instead of displayed.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping, Optional

from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot

from vertex_api.snapshot_views import (
    SnapshotContentError,
    _parse_utc,
    _require_list,
    _require_mapping,
    _require_str,
)

__all__ = [
    "CLOSED_STATUSES",
    "EXCLUSION_KIND_CLOSED_STATUS",
    "EXCLUSION_KIND_MISSING_EVIDENCE",
    "QUALIFIED_STATUSES",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "SNAPSHOT_KIND_OPPORTUNITIES",
    "OpportunitiesResponse",
    "build_opportunities_response",
]

SNAPSHOT_KIND_OPPORTUNITIES = "opportunities"
SNAPSHOT_KEY_GLOBAL = "global"

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"

QUALIFIED_STATUSES = frozenset({"OBSERVE", "REVIEW", "QUALIFIED"})
"""The ONLY statuses the qualified group may carry (relay-side guard)."""

CLOSED_STATUSES = frozenset({"BLOCKED", "INSUFFICIENT_DATA"})
"""The ONLY statuses a status-based exclusion may carry."""

GATE_STATUS_BLOCK = "BLOCK"

EXCLUSION_KIND_CLOSED_STATUS = "CLOSED_STATUS"
EXCLUSION_KIND_MISSING_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
_EXCLUSION_KINDS = frozenset(
    {EXCLUSION_KIND_CLOSED_STATUS, EXCLUSION_KIND_MISSING_EVIDENCE}
)


class OpportunitiesResponse(ContractModel):
    """The last published opportunities snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted content VERBATIM: profile
    reference (id + version + what is really applied), calendar provenance,
    documented lexicographic ordering, qualified and excluded candidates with
    their gates, honest evidence checks and published exclusion reasons (the
    page's honest empty state on synthetic data). ``state = "empty"`` means
    the worker never published.
    """

    state: Literal["ok", "empty"]
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    content: Optional[FrozenStrMapping]
    reason: Optional[NonEmptyStr]


def _gate_statuses(candidate: Mapping[str, Any], *, field: str) -> list[str]:
    gates = _require_list(candidate.get("gates"), field=f"{field}.gates")
    statuses: list[str] = []
    for index, raw in enumerate(gates):
        gate = _require_mapping(raw, field=f"{field}.gates[{index}]")
        statuses.append(
            _require_str(
                gate.get("status"), field=f"{field}.gates[{index}].status"
            )
        )
    return statuses


def _missing_evidence(candidate: Mapping[str, Any], *, field: str) -> list[str]:
    """Missing required evidence, cross-checked against the presence map."""
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
            f"published required_evidence presence {absent}"
        )
    return missing


def _check_qualified(candidate: Mapping[str, Any], *, field: str) -> None:
    advice = _require_mapping(candidate.get("advice"), field=f"{field}.advice")
    status = advice.get("status")
    if status not in QUALIFIED_STATUSES:
        raise SnapshotContentError(
            f"{field}: closed status {status!r} may never sit in the "
            "qualified group"
        )
    if GATE_STATUS_BLOCK in _gate_statuses(candidate, field=field):
        raise SnapshotContentError(
            f"{field}: a candidate carrying a BLOCK gate may never sit in "
            "the qualified group"
        )
    missing = _missing_evidence(candidate, field=field)
    if missing:
        raise SnapshotContentError(
            f"{field}: required evidence {missing} absent, the candidate is "
            "not admissible to the qualified group"
        )


def _check_excluded(candidate: Mapping[str, Any], *, field: str) -> None:
    advice = _require_mapping(candidate.get("advice"), field=f"{field}.advice")
    status = advice.get("status")
    exclusion = _require_mapping(candidate.get("exclusion"), field=f"{field}.exclusion")
    kind = _require_str(exclusion.get("kind"), field=f"{field}.exclusion.kind")
    if kind not in _EXCLUSION_KINDS:
        raise SnapshotContentError(f"{field}.exclusion.kind: unknown kind {kind!r}")
    missing = _missing_evidence(candidate, field=field)
    if kind == EXCLUSION_KIND_CLOSED_STATUS:
        if status not in CLOSED_STATUSES:
            raise SnapshotContentError(
                f"{field}: canonical closed status required"
            )
        _require_str(exclusion.get("gate_id"), field=f"{field}.exclusion.gate_id")
        _require_str(
            exclusion.get("reason_code"), field=f"{field}.exclusion.reason_code"
        )
        if GATE_STATUS_BLOCK not in _gate_statuses(candidate, field=field):
            raise SnapshotContentError(
                f"{field}: a closed status requires a published BLOCK gate"
            )
        return
    if status not in QUALIFIED_STATUSES:
        raise SnapshotContentError(
            f"{field}: a closed status must be attributed to its blocking "
            f"gate, not to {EXCLUSION_KIND_MISSING_EVIDENCE}"
        )
    if not missing:
        raise SnapshotContentError(
            f"{field}: {EXCLUSION_KIND_MISSING_EVIDENCE} requires at least "
            "one missing required evidence"
        )


def build_opportunities_response(
    snapshot: Optional[CurrentSnapshot],
) -> OpportunitiesResponse:
    """Relay the last opportunities snapshot verbatim, or the empty state.

    Fail-closed relay guard (never a recomputation): the qualified group must
    carry only open statuses, no blocking gate and no missing required
    evidence, and every excluded candidate must publish its exclusion — a
    snapshot violating this is refused instead of displayed.
    """
    if snapshot is None:
        return OpportunitiesResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            content=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = _require_mapping(snapshot.content, field="content")
    profile_ref = _require_mapping(content.get("profile_ref"), field="profile_ref")
    _require_str(profile_ref.get("id"), field="profile_ref.id")
    _require_str(profile_ref.get("version"), field="profile_ref.version")
    qualified = _require_list(content.get("qualified"), field="qualified")
    excluded = _require_list(content.get("excluded"), field="excluded")
    for index, raw in enumerate(qualified):
        candidate = _require_mapping(raw, field=f"qualified[{index}]")
        _check_qualified(candidate, field=f"qualified[{index}]")
    for index, raw in enumerate(excluded):
        candidate = _require_mapping(raw, field=f"excluded[{index}]")
        _check_excluded(candidate, field=f"excluded[{index}]")
    _require_mapping(content.get("exclusion_reasons"), field="exclusion_reasons")

    return OpportunitiesResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        content=dict(content),
        reason=None,
    )
