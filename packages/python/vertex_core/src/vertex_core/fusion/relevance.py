"""Deterministic attention and relevance engine (gates, ranking, budgets).

Mandatory gates run BEFORE any ranking: ``RIGHTS_OK``, ``IDENTITY_OK``,
``TIME_OK``, ``SOURCE_OK``, ``QUALITY_OK``. A refused item is excluded from
the ranking with a stable ``filtered_reason``; no priority — critical
blockers included — ever crosses a rights or identity gate.

Ranking is lexicographic over the documented priorities
(docs/02-architecture/DATA_FLOW.md): security/quality incident > manual
position > active thesis or alert > watchlist > recently analyzed instrument
> global market event > novelty/freshness. Manifest penalties are applied,
never inert: within an identical priority-flag profile, each penalty demotes
the item behind every otherwise-identical cleaner item (before freshness),
and ``missing_rights`` closes the ``RIGHTS_OK`` gate even when the upstream
boolean claims the rights are usable (fail-closed cross-invariant).
Sub-scores are kept separately — an opaque summed score is forbidden.
Attention budgets per page mirror ``manifests/relevance-policy.yaml`` (the
manifest is authoritative; a sync test enforces exact equality).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from types import MappingProxyType
from typing import Any

from pydantic import Field, model_validator

from vertex_core.contracts import (
    ContractModel,
    EnvelopeQuality,
    IdentityStatus,
    NonEmptyStr,
    UtcDatetime,
    ensure_utc,
)
from vertex_core.fusion.models import ContentObservation, SourceTier

__all__ = [
    "ATTENTION_BUDGETS",
    "GATE_IDENTITY_OK",
    "GATE_QUALITY_OK",
    "GATE_RIGHTS_OK",
    "GATE_SOURCE_OK",
    "GATE_TIME_OK",
    "PENALTY_CODES",
    "PENALTY_MISSING_RIGHTS",
    "POLICY_AUTHORITY",
    "POLICY_VERSION",
    "REQUIRED_GATES",
    "UNLIMITED",
    "GateEvaluation",
    "RankedItem",
    "RelevanceInput",
    "RelevanceInputError",
    "RelevanceRanking",
    "RelevanceRejection",
    "RelevanceSubscores",
    "UnknownAttentionBudgetError",
    "apply_attention_budget",
    "evaluate_gates",
    "rank_items",
]


POLICY_VERSION = 1
"""Mirrors ``schema_version`` of ``manifests/relevance-policy.yaml``."""

POLICY_AUTHORITY = "vertex_core.attention"
"""Mirrors ``authority`` of the manifest."""

UNLIMITED = "UNLIMITED"
"""Budget sentinel: no volume cap (gates still apply, always)."""

GATE_RIGHTS_OK = "RIGHTS_OK"
GATE_IDENTITY_OK = "IDENTITY_OK"
GATE_TIME_OK = "TIME_OK"
GATE_SOURCE_OK = "SOURCE_OK"
GATE_QUALITY_OK = "QUALITY_OK"

REQUIRED_GATES = (
    GATE_RIGHTS_OK,
    GATE_IDENTITY_OK,
    GATE_TIME_OK,
    GATE_SOURCE_OK,
    GATE_QUALITY_OK,
)
"""Canonical gate order; the first failed gate names ``filtered_reason``."""

PENALTY_CODES = (
    "duplicate",
    "syndicated_copy",
    "stale",
    "ambiguous_entity",
    "single_unverified_source",
    "probable_spam_or_bot",
    "missing_rights",
    "outside_universe_without_propagation",
)
"""Mirrors ``penalties`` of the manifest, in manifest order."""

PENALTY_MISSING_RIGHTS = "missing_rights"
"""Penalty code carrying a rights problem: it closes the ``RIGHTS_OK`` gate
regardless of the upstream ``rights_usable`` boolean (fail-closed)."""

ATTENTION_BUDGETS: Mapping[str, Mapping[str, int | str]] = MappingProxyType(
    {
        "today": MappingProxyType({"major_events": 3, "changes": 3, "blockers": UNLIMITED}),
        "markets": MappingProxyType({"dominant_narratives": 1, "contradictions": 3}),
        "opportunities": MappingProxyType(
            {"qualified_candidates": 5, "rejection_reasons_per_candidate": 3}
        ),
        "analysis": MappingProxyType({"evidence_groups": 5}),
        "options": MappingProxyType({"explained_anomalies": 5}),
    }
)
"""Mirrors ``attention_budgets`` of the manifest exactly (sync-tested)."""

MAX_RELEVANCE_REASONS = 3

_REASON_BY_FLAG = (
    ("security_or_quality_incident", "SECURITY_OR_QUALITY_INCIDENT"),
    ("manual_position", "MANUAL_POSITION"),
    ("active_thesis_or_alert", "ACTIVE_THESIS_OR_ALERT"),
    ("watchlist", "WATCHLIST"),
    ("recently_analyzed", "RECENTLY_ANALYZED_INSTRUMENT"),
    ("global_market_event", "GLOBAL_MARKET_EVENT"),
    ("novelty", "NOVELTY"),
)

_REASON_FRESHNESS = "FRESHNESS"

_ACCEPTED_QUALITIES = frozenset({EnvelopeQuality.VALID, EnvelopeQuality.PARTIAL})


class RelevanceInputError(ValueError):
    """Raised when the ranking input set is invalid (fail-closed)."""


class UnknownAttentionBudgetError(LookupError):
    """Raised for a page or category absent from the attention-budget policy."""


class RelevanceInput(ContractModel):
    """One candidate item plus the typed context needed by gates and ranking.

    ``rights_usable`` and ``source_allowed`` are decided upstream by the
    rights/source registries (data_quality owner); this engine never guesses
    them. All flags default to ``False`` — relevance must be proven.
    """

    observation: ContentObservation
    identity_status: IdentityStatus
    rights_usable: bool
    source_allowed: bool
    security_or_quality_incident: bool = False
    manual_position: bool = False
    active_thesis_or_alert: bool = False
    watchlist: bool = False
    recently_analyzed: bool = False
    global_market_event: bool = False
    novelty: bool = False
    penalties: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def _check_penalties(self) -> RelevanceInput:
        unknown = [code for code in self.penalties if code not in PENALTY_CODES]
        if unknown:
            raise ValueError(f"unknown penalty codes rejected: {unknown!r}")
        if len(set(self.penalties)) != len(self.penalties):
            duplicated = sorted({code for code in self.penalties if self.penalties.count(code) > 1})
            raise ValueError(f"duplicate penalty codes rejected: {duplicated!r}")
        return self

    @property
    def item_id(self) -> str:
        return self.observation.content_id


class GateEvaluation(ContractModel):
    """Result of the five mandatory gates for one item (no ranking data)."""

    item_id: NonEmptyStr
    rights_ok: bool
    identity_ok: bool
    time_ok: bool
    source_ok: bool
    quality_ok: bool

    @property
    def all_ok(self) -> bool:
        return (
            self.rights_ok
            and self.identity_ok
            and self.time_ok
            and self.source_ok
            and self.quality_ok
        )

    @property
    def failed_gates(self) -> tuple[str, ...]:
        """Failed gate names in canonical ``REQUIRED_GATES`` order."""
        flags = {
            GATE_RIGHTS_OK: self.rights_ok,
            GATE_IDENTITY_OK: self.identity_ok,
            GATE_TIME_OK: self.time_ok,
            GATE_SOURCE_OK: self.source_ok,
            GATE_QUALITY_OK: self.quality_ok,
        }
        return tuple(gate for gate in REQUIRED_GATES if not flags[gate])


class RelevanceSubscores(ContractModel):
    """Named sub-scores of one ranked item, kept strictly separate.

    There is deliberately no aggregate/total field: an opaque sum is
    forbidden by the attention doctrine.
    """

    security_or_quality_incident: bool
    manual_position: bool
    active_thesis_or_alert: bool
    watchlist: bool
    recently_analyzed: bool
    global_market_event: bool
    novelty: bool
    age_seconds: int = Field(ge=0)
    source_tier: SourceTier
    penalties: tuple[NonEmptyStr, ...]


class RelevanceRejection(ContractModel):
    """A gated-out item: excluded from ranking, with stable reasons."""

    item_id: NonEmptyStr
    filtered_reason: NonEmptyStr
    failed_gates: tuple[NonEmptyStr, ...] = Field(min_length=1)


class RankedItem(ContractModel):
    """One item admitted by every gate, with its lexicographic standing."""

    item_id: NonEmptyStr
    priority_class: int = Field(ge=1, le=7)
    subscores: RelevanceSubscores
    relevance_reasons: tuple[NonEmptyStr, ...] = Field(
        min_length=1, max_length=MAX_RELEVANCE_REASONS
    )
    policy_version: int


class RelevanceRanking(ContractModel):
    """Deterministic, replayable ranking outcome for one snapshot instant."""

    policy_version: int
    as_of: UtcDatetime
    ranked: tuple[RankedItem, ...]
    rejected: tuple[RelevanceRejection, ...]

    @property
    def filtered_count(self) -> int:
        return len(self.rejected)


def evaluate_gates(item: RelevanceInput, as_of: datetime) -> GateEvaluation:
    """Evaluate the five mandatory gates for ``item`` at instant ``as_of``.

    ``as_of`` must be timezone-aware (naive datetimes are rejected).
    ``TIME_OK`` fails on any future timestamp; ``QUALITY_OK`` fails for
    deleted content and for any quality outside {VALID, PARTIAL}.
    ``RIGHTS_OK`` fails when ``rights_usable`` is false OR when the upstream
    expressed a rights problem through the ``missing_rights`` penalty code —
    the two vocabularies must never contradict each other into a rankable
    item (fail-closed cross-invariant).
    """
    as_of = ensure_utc(as_of)
    observation = item.observation
    return GateEvaluation(
        item_id=item.item_id,
        rights_ok=item.rights_usable and PENALTY_MISSING_RIGHTS not in item.penalties,
        identity_ok=item.identity_status is IdentityStatus.RESOLVED,
        time_ok=(
            observation.received_at <= as_of
            and (observation.published_at is None or observation.published_at <= as_of)
        ),
        source_ok=item.source_allowed,
        quality_ok=(observation.quality in _ACCEPTED_QUALITIES and not observation.is_deleted),
    )


def _age_seconds(item: RelevanceInput, as_of: datetime) -> int:
    """Whole seconds since the item's best event time (floor, deterministic)."""
    basis = (
        item.observation.published_at
        if item.observation.published_at is not None
        else item.observation.received_at
    )
    delta = as_of - basis
    return delta.days * 86400 + delta.seconds


def _sort_key(item: RelevanceInput, age_seconds: int) -> tuple[Any, ...]:
    """Lexicographic key over the documented priorities; no summed score.

    Manifest penalties demote strictly within an identical priority-flag
    profile and BEFORE freshness: a clean item always outranks an
    otherwise-identical penalized item, however fresh the penalized one is,
    and more penalties rank lower. Penalties never promote a lower documented
    priority class above a higher one.
    """
    return (
        0 if item.security_or_quality_incident else 1,
        0 if item.manual_position else 1,
        0 if item.active_thesis_or_alert else 1,
        0 if item.watchlist else 1,
        0 if item.recently_analyzed else 1,
        0 if item.global_market_event else 1,
        0 if item.novelty else 1,
        len(item.penalties),
        age_seconds,
        item.observation.source_tier,
        item.item_id,
    )


def _priority_class(item: RelevanceInput) -> int:
    ordered_flags = (
        item.security_or_quality_incident,
        item.manual_position,
        item.active_thesis_or_alert,
        item.watchlist,
        item.recently_analyzed,
        item.global_market_event,
    )
    for index, flag in enumerate(ordered_flags, start=1):
        if flag:
            return index
    return 7


def _relevance_reasons(item: RelevanceInput) -> tuple[str, ...]:
    reasons = [reason for flag_name, reason in _REASON_BY_FLAG if getattr(item, flag_name)]
    if len(reasons) < MAX_RELEVANCE_REASONS:
        reasons.append(_REASON_FRESHNESS)
    return tuple(reasons[:MAX_RELEVANCE_REASONS])


def rank_items(items: Sequence[RelevanceInput], *, as_of: datetime) -> RelevanceRanking:
    """Gate then rank ``items`` deterministically for the instant ``as_of``.

    Every item failing any mandatory gate is excluded from the ranking and
    reported in ``rejected`` with a stable ``filtered_reason`` (the first
    failed gate in canonical order). Admitted items are ordered by the
    lexicographic priority key with ``item_id`` as final tiebreaker, so any
    input permutation replays to the identical ranking.
    """
    as_of = ensure_utc(as_of)
    seen: set[str] = set()
    for item in items:
        if item.item_id in seen:
            raise RelevanceInputError(
                f"duplicate item_id rejected: {item.item_id!r} appears more than once"
            )
        seen.add(item.item_id)

    admitted: list[tuple[tuple[Any, ...], RankedItem]] = []
    rejected: list[RelevanceRejection] = []
    for item in items:
        gates = evaluate_gates(item, as_of)
        if not gates.all_ok:
            failed = gates.failed_gates
            rejected.append(
                RelevanceRejection(
                    item_id=item.item_id,
                    filtered_reason=f"{failed[0]}_FAILED",
                    failed_gates=failed,
                )
            )
            continue
        age = _age_seconds(item, as_of)
        ranked_item = RankedItem(
            item_id=item.item_id,
            priority_class=_priority_class(item),
            subscores=RelevanceSubscores(
                security_or_quality_incident=item.security_or_quality_incident,
                manual_position=item.manual_position,
                active_thesis_or_alert=item.active_thesis_or_alert,
                watchlist=item.watchlist,
                recently_analyzed=item.recently_analyzed,
                global_market_event=item.global_market_event,
                novelty=item.novelty,
                age_seconds=age,
                source_tier=item.observation.source_tier,
                penalties=item.penalties,
            ),
            relevance_reasons=_relevance_reasons(item),
            policy_version=POLICY_VERSION,
        )
        admitted.append((_sort_key(item, age), ranked_item))

    admitted.sort(key=lambda pair: pair[0])
    rejected.sort(key=lambda rejection: rejection.item_id)
    return RelevanceRanking(
        policy_version=POLICY_VERSION,
        as_of=as_of,
        ranked=tuple(ranked_item for _, ranked_item in admitted),
        rejected=tuple(rejected),
    )


def apply_attention_budget(
    ranked: Sequence[RankedItem], page: str, category: str
) -> tuple[RankedItem, ...]:
    """Truncate an already-gated ranking to the page/category budget.

    ``UNLIMITED`` budgets (critical blockers) return every ranked item — but
    only ranked items: a budget can never resurrect an item refused by a
    rights, identity or any other mandatory gate, because refused items never
    enter a ranking. Unknown pages or categories fail closed.
    """
    try:
        page_budgets = ATTENTION_BUDGETS[page]
    except KeyError:
        raise UnknownAttentionBudgetError(f"unknown attention-budget page: {page!r}") from None
    try:
        budget = page_budgets[category]
    except KeyError:
        raise UnknownAttentionBudgetError(
            f"unknown attention-budget category {category!r} for page {page!r}"
        ) from None
    if budget == UNLIMITED:
        return tuple(ranked)
    assert isinstance(budget, int)  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
    return tuple(ranked[:budget])
