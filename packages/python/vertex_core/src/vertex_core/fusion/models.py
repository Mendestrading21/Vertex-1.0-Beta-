"""Contracts of the deterministic content-fusion engine.

``ContentObservation`` is one sourced content item (news, filing, event) as
observed; ``FusionDecision`` records one replayable deduplication decision;
``ContentCluster`` groups observations without ever deleting one. All models
are strict, frozen, timezone-aware and fail-closed: absent metadata stays
``None`` and is never fabricated. No transactional concept exists here.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from enum import Enum, unique
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from vertex_core.contracts import ContractModel, EnvelopeQuality, NonEmptyStr, UtcDatetime

__all__ = [
    "REVERSIBLE_FLAG_ACTIONS",
    "ContentCluster",
    "ContentObservation",
    "FusionAction",
    "FusionDecision",
    "SourceTier",
]


SourceTier = Annotated[str, StringConstraints(pattern=r"^P[0-4]$")]
"""Source trust tier: ``P0`` (highest, primary/regulatory) through ``P4``."""


def _require_strictly_sorted_unique(values: Sequence[str], field_name: str) -> None:
    """Reject a sequence that is not strictly sorted (implies uniqueness)."""
    if any(a >= b for a, b in itertools.pairwise(values)):
        raise ValueError(f"{field_name} must be strictly sorted and unique")


@unique
class FusionAction(str, Enum):
    """Canonical action recorded by one fusion decision.

    ``LINKED_*`` actions join members into one cluster; ``FLAGGED_SIMILAR``
    is a reversible cross-cluster hint that never merges;
    ``FLAGGED_POLARITY_CONFLICT`` names two observations asserting opposite
    directions (``+``/``-``, ``>``/``<``) — it never merges and never
    splits, it publishes the contradiction; ``KEPT_DISTINCT`` records that
    no rule linked an observation to another.
    """

    LINKED_NATIVE_ID = "LINKED_NATIVE_ID"
    LINKED_CANONICAL_URL = "LINKED_CANONICAL_URL"
    LINKED_FINGERPRINT = "LINKED_FINGERPRINT"
    FLAGGED_SIMILAR = "FLAGGED_SIMILAR"
    FLAGGED_POLARITY_CONFLICT = "FLAGGED_POLARITY_CONFLICT"
    KEPT_DISTINCT = "KEPT_DISTINCT"


REVERSIBLE_FLAG_ACTIONS = frozenset(
    {FusionAction.FLAGGED_SIMILAR, FusionAction.FLAGGED_POLARITY_CONFLICT}
)
"""Flag actions that must always be reversible (never a destructive merge)."""


class ContentObservation(ContractModel):
    """One immutable sourced content observation (market information only).

    ``native_id``, ``canonical_url`` and ``published_at`` stay ``None`` when
    the provider did not supply them — absence is never replaced by a
    fabricated value. ``is_deleted`` marks provider-side deletion; the
    observation itself is always retained (no physical deletion anywhere).
    """

    content_id: NonEmptyStr
    source: NonEmptyStr
    source_tier: SourceTier
    native_id: NonEmptyStr | None = None
    canonical_url: NonEmptyStr | None = None
    title: NonEmptyStr
    entities: tuple[NonEmptyStr, ...]
    published_at: UtcDatetime | None = None
    received_at: UtcDatetime
    rights: NonEmptyStr
    quality: EnvelopeQuality
    is_deleted: bool = False


class FusionDecision(ContractModel):
    """One deterministic, replayable deduplication decision.

    Invariants: every ``FLAGGED_*`` action is always reversible (a flag is
    never a destructive merge, and a published contradiction is never a
    verdict); ``KEPT_DISTINCT`` names exactly one input; every other action
    names exactly two; inputs are strictly sorted.
    """

    decision_id: NonEmptyStr
    rule_id: NonEmptyStr
    rule_version: NonEmptyStr
    inputs: tuple[NonEmptyStr, ...] = Field(min_length=1)
    action: FusionAction
    rationale: NonEmptyStr
    reversible: bool

    @model_validator(mode="after")
    def _check_decision_invariants(self) -> FusionDecision:
        if self.action in REVERSIBLE_FLAG_ACTIONS and not self.reversible:
            raise ValueError(f"{self.action.value} decisions must be reversible")
        if self.action is FusionAction.KEPT_DISTINCT:
            if len(self.inputs) != 1:
                raise ValueError("KEPT_DISTINCT decisions take exactly one input")
        elif len(self.inputs) != 2:
            raise ValueError("linking and flagging decisions take exactly two inputs")
        _require_strictly_sorted_unique(self.inputs, "inputs")
        return self


class ContentCluster(ContractModel):
    """A deterministic cluster of content observations.

    A cluster preserves every provider, tier, right and update date of its
    members and carries every :class:`FusionDecision` that shaped or flagged
    it. ``first_published_at`` is ``None`` when no member carries a
    publication timestamp — never defaulted to another timestamp.
    """

    cluster_id: NonEmptyStr
    member_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    sources: tuple[NonEmptyStr, ...] = Field(min_length=1)
    tiers: tuple[SourceTier, ...] = Field(min_length=1)
    rights: tuple[NonEmptyStr, ...] = Field(min_length=1)
    first_published_at: UtcDatetime | None = None
    last_received_at: UtcDatetime
    decisions: tuple[FusionDecision, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_cluster_invariants(self) -> ContentCluster:
        _require_strictly_sorted_unique(self.member_ids, "member_ids")
        _require_strictly_sorted_unique(self.sources, "sources")
        _require_strictly_sorted_unique(self.tiers, "tiers")
        _require_strictly_sorted_unique(self.rights, "rights")
        members = set(self.member_ids)
        for decision in self.decisions:
            if not members.intersection(decision.inputs):
                raise ValueError(
                    "every decision attached to a cluster must reference at least one member"
                )
        return self
