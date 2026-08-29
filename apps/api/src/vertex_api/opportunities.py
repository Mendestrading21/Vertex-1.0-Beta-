"""Opportunities API (page 04): verbatim snapshot relay.

The API computes NO gate, NO rank and NO verdict here: it relays the
worker's ``opportunities/global`` snapshot exactly as persisted (or an
honest empty state), after a fail-closed shape check that refuses to relay
a snapshot violating the page's core invariant — a closed candidate
(``BLOCKED``/``INSUFFICIENT_DATA``) inside the qualified group.
"""

from __future__ import annotations

from typing import Literal, Optional

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


class OpportunitiesResponse(ContractModel):
    """The last published opportunities snapshot — or an honest empty state.

    ``state = "ok"`` relays the persisted content VERBATIM: profile
    reference (id + version), documented lexicographic ordering, qualified
    and excluded candidates with their gates and honest evidence checks, and
    the distribution of exclusion reasons (the page's honest empty state on
    synthetic data). ``state = "empty"`` means the worker never published.
    """

    state: Literal["ok", "empty"]
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    content: Optional[FrozenStrMapping]
    reason: Optional[NonEmptyStr]


def build_opportunities_response(
    snapshot: Optional[CurrentSnapshot],
) -> OpportunitiesResponse:
    """Relay the last opportunities snapshot verbatim, or the empty state.

    Fail-closed relay guard (never a recomputation): the qualified group
    must carry only open statuses and every excluded candidate must carry a
    canonical closed status — a snapshot violating this is refused instead
    of displayed.
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
        advice = _require_mapping(
            candidate.get("advice"), field=f"qualified[{index}].advice"
        )
        if advice.get("status") not in QUALIFIED_STATUSES:
            raise SnapshotContentError(
                f"qualified[{index}]: closed status "
                f"{advice.get('status')!r} may never sit in the qualified group"
            )
    for index, raw in enumerate(excluded):
        candidate = _require_mapping(raw, field=f"excluded[{index}]")
        advice = _require_mapping(
            candidate.get("advice"), field=f"excluded[{index}].advice"
        )
        if advice.get("status") not in ("BLOCKED", "INSUFFICIENT_DATA"):
            raise SnapshotContentError(
                f"excluded[{index}]: canonical closed status required"
            )
    _require_mapping(content.get("exclusion_reasons"), field="exclusion_reasons")

    return OpportunitiesResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        content=dict(content),
        reason=None,
    )
