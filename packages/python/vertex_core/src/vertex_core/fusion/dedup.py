"""Deterministic, replayable content deduplication (five documented levels).

Levels (docs/04-integrations/DATA_FUSION.md):

1. exact provider ``native_id`` per source;
2. normalized ``canonical_url`` (lowercase scheme/host, listed tracking
   parameters stripped, fragment stripped, remaining query sorted) within a
   bounded time window;
3. fingerprint of the normalized title (case, punctuation, whitespace and
   accents removed) plus sorted normalized entities;
4. time-window similarity: a **reversible flag only** (``FLAGGED_SIMILAR``),
   never a destructive merge;
5. cluster construction preserving every provider, right, date and every
   :class:`FusionDecision`.

Nothing is physically deleted: every input observation stays a member of
exactly one cluster (enforced by :class:`FusionResult`), and a member linked
as a duplicate keeps its full observation. The pipeline is a pure function of
its input set — input order never changes cluster ids, decisions or the
canonical hash of the result.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Optional, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, model_validator

from vertex_core.contracts import ContractModel, NonEmptyStr, canonical_json_hash
from vertex_core.fusion.models import (
    ContentCluster,
    ContentObservation,
    FusionAction,
    FusionDecision,
)

__all__ = [
    "CANONICAL_URL_WINDOW",
    "FUSION_RULESET_VERSION",
    "FusionInputError",
    "FusionResult",
    "RULE_CANONICAL_URL",
    "RULE_FINGERPRINT",
    "RULE_KEPT_DISTINCT",
    "RULE_NATIVE_ID",
    "RULE_SIMILARITY_FLAG",
    "SIMILARITY_MIN_JACCARD_PERCENT",
    "SIMILARITY_MIN_SHARED_ENTITIES",
    "SIMILARITY_WINDOW",
    "TRACKING_PARAMS",
    "TRACKING_PARAM_PREFIXES",
    "fuse",
    "fusion_result_hash",
    "normalize_canonical_url",
    "normalize_title",
    "title_fingerprint",
]


FUSION_RULESET_VERSION = "1.0.0"
"""Version stamped on every decision; bump on any behavioral rule change."""

RULE_NATIVE_ID = "fusion.dedup.native_id"
RULE_CANONICAL_URL = "fusion.dedup.canonical_url"
RULE_FINGERPRINT = "fusion.dedup.title_fingerprint"
RULE_SIMILARITY_FLAG = "fusion.dedup.similarity_window_flag"
RULE_KEPT_DISTINCT = "fusion.dedup.kept_distinct"

CANONICAL_URL_WINDOW = timedelta(hours=48)
"""Maximum event-time gap for two same-canonical-URL observations to link."""

SIMILARITY_WINDOW = timedelta(hours=24)
"""Maximum event-time gap for the reversible similarity flag (level 4)."""

SIMILARITY_MIN_SHARED_ENTITIES = 1
"""Minimum shared normalized entities for a similarity-flag candidate pair."""

SIMILARITY_MIN_JACCARD_PERCENT = 60
"""Minimum title-token Jaccard similarity, in integer percent (no floats)."""

TRACKING_PARAM_PREFIXES = ("utm_",)
"""Query-parameter name prefixes stripped during URL normalization."""

TRACKING_PARAMS = frozenset(
    {
        "cmpid",
        "fbclid",
        "gclid",
        "icid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "mkt_tok",
        "msclkid",
        "s_kwcid",
        "smid",
        "spm",
        "twclid",
        "yclid",
        "_ga",
    }
)
"""Exact query-parameter names stripped during URL normalization."""


class FusionInputError(ValueError):
    """Raised when the input observation set is invalid (fail-closed)."""


class FusionResult(ContractModel):
    """Immutable outcome of one deterministic fusion run.

    Invariants: clusters are sorted by ``cluster_id`` and partition the input
    exactly — every observation is a member of exactly one cluster and every
    observation is retained verbatim (zero physical deletion).
    """

    ruleset_version: NonEmptyStr
    clusters: tuple[ContentCluster, ...]
    observations: tuple[ContentObservation, ...] = Field(min_length=0)

    @model_validator(mode="after")
    def _check_partition(self) -> "FusionResult":
        cluster_ids = [cluster.cluster_id for cluster in self.clusters]
        if any(a >= b for a, b in zip(cluster_ids, cluster_ids[1:])):
            raise ValueError("clusters must be strictly sorted by cluster_id")
        observation_ids = [obs.content_id for obs in self.observations]
        if any(a >= b for a, b in zip(observation_ids, observation_ids[1:])):
            raise ValueError("observations must be strictly sorted by content_id")
        member_ids = [member for cluster in self.clusters for member in cluster.member_ids]
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("cluster memberships must not overlap")
        if set(member_ids) != set(observation_ids):
            raise ValueError(
                "clusters must partition the observations exactly (zero deletion, zero invention)"
            )
        return self


def normalize_title(title: str) -> str:
    """Normalize a title: accents, case, punctuation and whitespace removed.

    Unicode is NFKD-decomposed and combining marks dropped, the result is
    casefolded, every non-alphanumeric character becomes a separator and
    whitespace collapses to single spaces. Pure and deterministic.
    """
    decomposed = unicodedata.normalize("NFKD", title)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    folded = stripped.casefold()
    separated = "".join(ch if ch.isalnum() else " " for ch in folded)
    return " ".join(separated.split())


def _normalize_entities(entities: Iterable[str]) -> tuple[str, ...]:
    """Return sorted, unique, normalized, non-empty entity labels."""
    normalized = {normalize_title(entity) for entity in entities}
    normalized.discard("")
    return tuple(sorted(normalized))


def _is_tracking_param(name: str) -> bool:
    lowered = name.casefold()
    if lowered in TRACKING_PARAMS:
        return True
    return any(lowered.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES)


def normalize_canonical_url(url: str) -> str:
    """Normalize a URL for deduplication (level 2).

    Scheme and network location are lowercased (host names are
    case-insensitive), the fragment is dropped, listed tracking parameters
    are removed and the remaining query pairs are sorted for a canonical
    form. The path keeps its case (paths are case-sensitive).
    """
    parts = urlsplit(url)
    kept_pairs = sorted(
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_param(name)
    )
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            parts.path,
            urlencode(kept_pairs),
            "",
        )
    )


def title_fingerprint(title: str, entities: Iterable[str]) -> Optional[str]:
    """Deterministic fingerprint of a normalized title plus sorted entities.

    Returns ``None`` when the normalized title is empty (a punctuation-only
    title must not link unrelated items — fail-closed, no wildcard bucket).
    """
    normalized_title = normalize_title(title)
    if not normalized_title:
        return None
    return canonical_json_hash(
        {"title": normalized_title, "entities": list(_normalize_entities(entities))}
    )


def _event_time(observation: ContentObservation) -> datetime:
    """Best available event time: ``published_at`` when present, else ``received_at``."""
    if observation.published_at is not None:
        return observation.published_at
    return observation.received_at


def _decision_id(rule_id: str, action: FusionAction, inputs: Sequence[str]) -> str:
    return canonical_json_hash(
        {
            "rule_id": rule_id,
            "rule_version": FUSION_RULESET_VERSION,
            "action": action.value,
            "inputs": list(inputs),
        }
    )


def _make_decision(
    rule_id: str,
    action: FusionAction,
    inputs: Sequence[str],
    rationale: str,
    reversible: bool,
) -> FusionDecision:
    ordered = tuple(sorted(inputs))
    return FusionDecision(
        decision_id=_decision_id(rule_id, action, ordered),
        rule_id=rule_id,
        rule_version=FUSION_RULESET_VERSION,
        inputs=ordered,
        action=action,
        rationale=rationale,
        reversible=reversible,
    )


class _UnionFind:
    """Union-find with deterministic roots (smallest content_id wins)."""

    def __init__(self, ids: Iterable[str]) -> None:
        self._parent: dict[str, str] = {content_id: content_id for content_id in ids}

    def find(self, content_id: str) -> str:
        parent = self._parent
        root = content_id
        while parent[root] != root:
            root = parent[root]
        while parent[content_id] != root:
            parent[content_id], content_id = root, parent[content_id]
        return root

    def union(self, first: str, second: str) -> None:
        root_a, root_b = self.find(first), self.find(second)
        if root_a == root_b:
            return
        keep, absorb = (root_a, root_b) if root_a < root_b else (root_b, root_a)
        self._parent[absorb] = keep


def _link_group(
    union: _UnionFind,
    member_ids: Sequence[str],
    rule_id: str,
    action: FusionAction,
    rationale: str,
    decisions: list[FusionDecision],
) -> None:
    """Link a group via edges from its smallest member (deterministic)."""
    ordered = sorted(member_ids)
    representative = ordered[0]
    for other in ordered[1:]:
        decisions.append(
            _make_decision(rule_id, action, (representative, other), rationale, reversible=False)
        )
        union.union(representative, other)


def fuse(observations: Sequence[ContentObservation]) -> FusionResult:
    """Run the five deterministic deduplication levels and build clusters.

    Pure function of the input set: any permutation of ``observations``
    yields identical cluster ids, identical decisions and an identical
    canonical result hash. Raises :class:`FusionInputError` on duplicate
    ``content_id`` values (two distinct observations may not share an id).
    """
    by_id: dict[str, ContentObservation] = {}
    for observation in observations:
        if observation.content_id in by_id:
            raise FusionInputError(
                f"duplicate content_id rejected: {observation.content_id!r} appears more than once"
            )
        by_id[observation.content_id] = observation

    ordered_ids = sorted(by_id)
    union = _UnionFind(ordered_ids)
    link_decisions: list[FusionDecision] = []

    # Level 1 — exact provider native id, per source.
    native_groups: dict[tuple[str, str], list[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        if observation.native_id is not None:
            native_groups.setdefault((observation.source, observation.native_id), []).append(
                content_id
            )
    for (source, native_id), members in sorted(native_groups.items()):
        if len(members) > 1:
            _link_group(
                union,
                members,
                RULE_NATIVE_ID,
                FusionAction.LINKED_NATIVE_ID,
                f"same provider native id {native_id!r} from source {source!r}",
                link_decisions,
            )

    # Level 2 — normalized canonical URL within a bounded time window.
    url_groups: dict[str, list[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        if observation.canonical_url is not None:
            url_groups.setdefault(normalize_canonical_url(observation.canonical_url), []).append(
                content_id
            )
    for normalized_url, members in sorted(url_groups.items()):
        if len(members) < 2:
            continue
        timeline = sorted(members, key=lambda cid: (_event_time(by_id[cid]), cid))
        for previous, current in zip(timeline, timeline[1:]):
            gap = _event_time(by_id[current]) - _event_time(by_id[previous])
            if gap <= CANONICAL_URL_WINDOW:
                link_decisions.append(
                    _make_decision(
                        RULE_CANONICAL_URL,
                        FusionAction.LINKED_CANONICAL_URL,
                        (previous, current),
                        f"same normalized canonical url {normalized_url!r} within "
                        f"{CANONICAL_URL_WINDOW}",
                        reversible=False,
                    )
                )
                union.union(previous, current)

    # Level 3 — normalized title + sorted entities fingerprint.
    fingerprint_groups: dict[str, list[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        fingerprint = title_fingerprint(observation.title, observation.entities)
        if fingerprint is not None:
            fingerprint_groups.setdefault(fingerprint, []).append(content_id)
    for fingerprint, members in sorted(fingerprint_groups.items()):
        if len(members) > 1:
            _link_group(
                union,
                members,
                RULE_FINGERPRINT,
                FusionAction.LINKED_FINGERPRINT,
                f"same normalized title and entity fingerprint {fingerprint}",
                link_decisions,
            )

    # Level 4 — time-window similarity: reversible flag only, never a merge.
    entity_index: dict[str, list[str]] = {}
    tokens: dict[str, frozenset[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        tokens[content_id] = frozenset(normalize_title(observation.title).split())
        for entity in _normalize_entities(observation.entities):
            entity_index.setdefault(entity, []).append(content_id)
    candidate_pairs: set[tuple[str, str]] = set()
    for members in entity_index.values():
        for index, first in enumerate(members):
            for second in members[index + 1 :]:
                candidate_pairs.add((first, second))
    flag_decisions: list[FusionDecision] = []
    for first, second in sorted(candidate_pairs):
        if union.find(first) == union.find(second):
            continue
        obs_a, obs_b = by_id[first], by_id[second]
        gap = abs(_event_time(obs_a) - _event_time(obs_b))
        if gap > SIMILARITY_WINDOW:
            continue
        shared_entities = set(_normalize_entities(obs_a.entities)).intersection(
            _normalize_entities(obs_b.entities)
        )
        if len(shared_entities) < SIMILARITY_MIN_SHARED_ENTITIES:
            continue
        union_tokens = tokens[first] | tokens[second]
        intersection_tokens = tokens[first] & tokens[second]
        if not union_tokens:
            continue
        # Integer cross-multiplication: no float comparison in the rule.
        if 100 * len(intersection_tokens) < SIMILARITY_MIN_JACCARD_PERCENT * len(union_tokens):
            continue
        flag_decisions.append(
            _make_decision(
                RULE_SIMILARITY_FLAG,
                FusionAction.FLAGGED_SIMILAR,
                (first, second),
                "similar title and shared entities within "
                f"{SIMILARITY_WINDOW}; reversible flag, never a merge",
                reversible=True,
            )
        )

    # Level 5 — cluster construction: every provider, right, date and
    # decision is preserved; nothing is deleted.
    members_by_root: dict[str, list[str]] = {}
    for content_id in ordered_ids:
        members_by_root.setdefault(union.find(content_id), []).append(content_id)

    decisions_by_root: dict[str, list[FusionDecision]] = {}
    for decision in link_decisions:
        root = union.find(decision.inputs[0])
        decisions_by_root.setdefault(root, []).append(decision)
    for decision in flag_decisions:
        touched_roots = {union.find(content_id) for content_id in decision.inputs}
        for root in touched_roots:
            decisions_by_root.setdefault(root, []).append(decision)

    clusters: list[ContentCluster] = []
    for root, members in members_by_root.items():
        decisions = decisions_by_root.get(root, [])
        if len(members) == 1:
            # A singleton was linked by no rule; similarity flags (if any) are
            # not links, so the KEPT_DISTINCT record is always due.
            decisions = decisions + [
                _make_decision(
                    RULE_KEPT_DISTINCT,
                    FusionAction.KEPT_DISTINCT,
                    (members[0],),
                    "no deduplication rule linked this observation to another",
                    reversible=True,
                )
            ]
        decisions = sorted(decisions, key=lambda d: (d.rule_id, d.inputs, d.decision_id))
        member_observations = [by_id[content_id] for content_id in members]
        published = [
            obs.published_at for obs in member_observations if obs.published_at is not None
        ]
        clusters.append(
            ContentCluster(
                cluster_id=canonical_json_hash({"members": members}),
                member_ids=tuple(members),
                sources=tuple(sorted({obs.source for obs in member_observations})),
                tiers=tuple(sorted({obs.source_tier for obs in member_observations})),
                rights=tuple(sorted({obs.rights for obs in member_observations})),
                first_published_at=min(published) if published else None,
                last_received_at=max(obs.received_at for obs in member_observations),
                decisions=tuple(decisions),
            )
        )

    return FusionResult(
        ruleset_version=FUSION_RULESET_VERSION,
        clusters=tuple(sorted(clusters, key=lambda cluster: cluster.cluster_id)),
        observations=tuple(by_id[content_id] for content_id in ordered_ids),
    )


def fusion_result_hash(result: FusionResult) -> str:
    """Canonical ``sha256:`` hash of a fusion result (replay comparison aid)."""
    return canonical_json_hash(result)
