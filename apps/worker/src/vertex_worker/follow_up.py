"""Review queue snapshot chain (page 09 — follow-up): ``review_queue.refresh``.

The handler recomputes the ``review_queue/global`` snapshot:

- every thesis with its PROJECTED state — status and effective review due are
  recomputed by ``vertex_persistence.repository.theses`` on every run
  (``list_theses`` / ``project_thesis_state``), never read from a stored
  status column;
- the DUE items come from ``review_queue_due`` and are re-ordered by the
  DOCUMENTED lexicographic key (see :data:`DUE_ORDERING_KEYS`): due for the
  longest first (effective due ascending), then the base deadline
  (ascending), then recency (least recently touched first), then thesis id —
  fully deterministic;
- for each thesis linked to an instrument (``instrument.ticker``), the recent
  information CLUSTERS of that ticker (``vertex_core.fusion`` over the recent
  observation window) are attached as CONTEXT with full provenance (cluster
  id, member event ids, sources, rights, instants, synthetic nature);
- a cluster received AFTER the thesis's last review (or after its creation
  when never reviewed) sets ``has_new_information = True`` with an explicit
  machine-readable reason. New information RAISES the visible urgency of the
  review — flag and reasons — but NEVER writes to the thesis: this handler
  performs no thesis or revision write of any kind, the user alone revises a
  thesis (page 09: « une nouvelle information peut rendre une revue urgente,
  mais ne modifie pas la thèse automatiquement »).

Population separation (never aggregated): theses are USER-DECLARED
statements; the information context carries its OWN population label
(``SYNTHETIC``/``REAL``/``EMPTY`` from the observation window). The two
labels live side by side and are never merged into one blended figure.

Enqueue topology (documented choice):

1. the API enqueues ``review_queue.refresh`` IN THE SAME TRANSACTION as
   every accepted thesis write — ``POST /api/v1/theses`` and
   ``POST /api/v1/theses/{id}/revisions`` (``vertex_api.follow_up``) — so a
   new thesis or revision refreshes the queue exactly when it commits;
2. ``vertex_worker.ingest.ingest_envelope`` enqueues one additional
   ``review_queue.refresh`` message for EVERY newly inserted observation
   (same transaction, same idempotence as ``observation.ingested``): new
   information may change the urgency context of any thesis. The registry is
   strictly one-handler-per-topic, so this handler does not share
   ``observation.ingested`` with the attention fusion handler.

Publication follows publish-if-changed: identical inputs and clock republish
nothing.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from vertex_core.fusion import fuse
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_persistence.repository.theses import (
    ProjectedThesis,
    list_theses,
    review_queue_due,
)
from vertex_worker.registry import HandlerRegistry

if TYPE_CHECKING:  # import-time cycle avoidance (ingest -> follow_up -> handlers -> ingest)
    from vertex_worker.handlers import FusionConfig, ObservationRecord

__all__ = [
    "DUE_ORDERING_KEYS",
    "POPULATION_THESES",
    "REASON_NEW_INFORMATION",
    "REVIEW_QUEUE_SCHEMA_VERSION",
    "SNAPSHOT_KEY_GLOBAL",
    "SNAPSHOT_KIND_REVIEW_QUEUE",
    "TOPIC_REVIEW_QUEUE_REFRESH",
    "ReviewQueueHandler",
    "build_review_queue_content",
    "due_sort_key",
    "register_follow_up_handler",
]

log = logging.getLogger("vertex_worker.follow_up")

Clock = Callable[[], datetime]

TOPIC_REVIEW_QUEUE_REFRESH = "review_queue.refresh"
"""Outbox topic: recompute the global review queue (payload is contextual)."""

SNAPSHOT_KIND_REVIEW_QUEUE = "review_queue"
SNAPSHOT_KEY_GLOBAL = "global"
REVIEW_QUEUE_SCHEMA_VERSION = "vertex.review-queue/1.0"

POPULATION_THESES = "USER_DECLARED"
"""Theses are user-written statements: never a market feed, never synthetic
fixtures presented as user input. This label is kept SEPARATE from the
information-context population — populations are never aggregated."""

REASON_NEW_INFORMATION = "NEW_INFORMATION_SINCE_LAST_REVIEW"
"""Machine token: an information cluster of the thesis's ticker was received
after the last review (or after creation when never reviewed)."""

DUE_ORDERING_KEYS: tuple[str, ...] = (
    "effective_review_due_at asc (du depuis le plus longtemps d'abord)",
    "base_review_due_at asc (echeance la plus proche ensuite)",
    "last_recorded_at asc (le moins recemment touche d'abord)",
    "thesis_id asc (departage deterministe)",
)
"""Documented lexicographic ordering of the due items (most urgent first)."""


def _require_aware_utc(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError(f"now: expected datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    return now.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(UTC).isoformat()


def _thesis_ticker(entry: ProjectedThesis) -> str | None:
    instrument = entry.thesis.instrument
    if not isinstance(instrument, Mapping):
        return None
    ticker = instrument.get("ticker")
    if isinstance(ticker, str) and ticker:
        return ticker
    return None


def due_sort_key(entry: ProjectedThesis) -> tuple[datetime, datetime, datetime, int]:
    """Documented lexicographic key of the due queue (see DUE_ORDERING_KEYS).

    ``review_queue_due`` guarantees a non-``None`` effective due on every due
    entry; the base deadline falls back to the effective due when the thesis
    has no base ``review_due_at`` (expired snooze without base deadline).
    """
    effective_due = entry.state.review_due_at
    # narrowing mypy, garde réelle au-dessus
    assert effective_due is not None  # guaranteed by review_queue_due  # noqa: S101
    base_due = entry.thesis.review_due_at
    return (
        effective_due,
        base_due if base_due is not None else effective_due,
        entry.state.last_recorded_at,
        entry.thesis.id,
    )


# --------------------------------------------------------------------------
# Pure content builder (no session, fully deterministic)
# --------------------------------------------------------------------------


def _cluster_context(
    records: Sequence[ObservationRecord], config: FusionConfig
) -> tuple[dict[str, list[dict[str, Any]]], str, int, int]:
    """Fuse the recent observation window into per-ticker cluster context.

    Returns ``(clusters_by_ticker, population, content_count, cluster_count)``.
    Reuses the SAME extraction helpers as the attention fusion handler
    (``vertex_worker.handlers``) so no second content-parsing authority
    exists. Purely derived data: nothing here writes anything.
    """
    # Local import: handlers imports ingest which imports this module.
    from vertex_worker.handlers import (
        POPULATION_EMPTY,
        POPULATION_REAL,
        POPULATION_SYNTHETIC,
        _content_observation,
        _content_title,
        is_synthetic_record,
    )

    content_records: dict[str, ObservationRecord] = {}
    observations = []
    for record in sorted(records, key=lambda r: (r.as_of, r.event_id)):
        title = _content_title(record)
        if title is None:
            continue
        if record.event_id in content_records:
            raise ValueError(f"duplicate event_id in records: {record.event_id!r}")
        content_records[record.event_id] = record
        observations.append(_content_observation(record, config, title))

    fusion = fuse(observations)
    observation_by_id = {obs.content_id: obs for obs in fusion.observations}

    clusters_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for cluster in sorted(fusion.clusters, key=lambda c: c.cluster_id):
        members = [observation_by_id[member_id] for member_id in cluster.member_ids]
        member_records = [content_records[member_id] for member_id in cluster.member_ids]
        tickers = sorted(
            {entity for member in members for entity in member.entities}
        )
        representative = min(
            members,
            key=lambda obs: (
                obs.source_tier,
                obs.published_at if obs.published_at is not None else obs.received_at,
                obs.content_id,
            ),
        )
        entry = {
            "cluster_id": cluster.cluster_id,
            "title": representative.title,
            "tickers": tickers,
            "synthetic": any(is_synthetic_record(r) for r in member_records),
            "provenance": {
                "member_event_ids": list(cluster.member_ids),
                "sources": list(cluster.sources),
                "rights": list(cluster.rights),
                "first_published_at": _iso(cluster.first_published_at),
                "last_received_at": _iso(cluster.last_received_at),
            },
        }
        for ticker in tickers:
            clusters_by_ticker.setdefault(ticker, []).append(entry)

    if not records:
        population = POPULATION_EMPTY
    elif any(is_synthetic_record(record) for record in records):
        population = POPULATION_SYNTHETIC
    else:
        population = POPULATION_REAL
    return clusters_by_ticker, population, len(observations), len(fusion.clusters)


def _urgency(
    entry: ProjectedThesis, clusters: Sequence[Mapping[str, Any]]
) -> tuple[bool, list[dict[str, Any]]]:
    """Novelty flag and reasons for one thesis. Reads only; never writes.

    Reference instant: the last REVIEWED revision, or the thesis creation
    when it was never reviewed. A cluster whose ``last_received_at`` is
    strictly after that instant is NEW information.
    """
    reference = entry.state.last_reviewed_at
    if reference is None:
        reference = entry.thesis.created_at
    reasons: list[dict[str, Any]] = []
    for cluster in clusters:
        raw = cluster["provenance"]["last_received_at"]
        if raw is None:
            continue
        last_received = datetime.fromisoformat(raw)
        if last_received > reference:
            reasons.append(
                {
                    "code": REASON_NEW_INFORMATION,
                    "cluster_id": cluster["cluster_id"],
                    "last_received_at": raw,
                    "reference_instant": _iso(reference),
                }
            )
    return bool(reasons), reasons


def build_review_queue_content(
    projected: Sequence[ProjectedThesis],
    due: Sequence[ProjectedThesis],
    records: Sequence[ObservationRecord],
    *,
    now: datetime,
    config: FusionConfig,
) -> dict[str, Any]:
    """Build the review queue snapshot content. Pure and deterministic.

    Identical ``projected``, ``due``, ``records`` (any order), ``now`` and
    ``config`` produce an identical dict. Nothing here mutates a thesis: the
    builder consumes projections and emits presentation data only.
    """
    now = _require_aware_utc(now)
    clusters_by_ticker, info_population, content_count, cluster_count = (
        _cluster_context(records, config)
    )

    theses_entries: list[dict[str, Any]] = []
    urgency_by_id: dict[int, tuple[bool, list[dict[str, Any]]]] = {}
    with_instrument = 0
    with_new_information = 0
    for entry in sorted(projected, key=lambda item: item.thesis.id):
        ticker = _thesis_ticker(entry)
        clusters = clusters_by_ticker.get(ticker, []) if ticker is not None else []
        if ticker is not None:
            with_instrument += 1
        has_new, reasons = _urgency(entry, clusters)
        if has_new:
            with_new_information += 1
        urgency_by_id[entry.thesis.id] = (has_new, reasons)
        theses_entries.append(
            {
                "thesis": {
                    "id": entry.thesis.id,
                    "portfolio_id": entry.thesis.portfolio_id,
                    "instrument": (
                        dict(entry.thesis.instrument)
                        if entry.thesis.instrument is not None
                        else None
                    ),
                    "title": entry.thesis.title,
                    "hypotheses": entry.thesis.hypotheses,
                    "invalidation": entry.thesis.invalidation,
                    "horizon": entry.thesis.horizon,
                    "review_due_at": _iso(entry.thesis.review_due_at),
                    "created_at": _iso(entry.thesis.created_at),
                },
                "state": {
                    "status": entry.state.status,
                    "review_due_at": _iso(entry.state.review_due_at),
                    "is_due": entry.state.is_due,
                    "snooze_until": _iso(entry.state.snooze_until),
                    "last_reviewed_at": _iso(entry.state.last_reviewed_at),
                    "last_action": entry.state.last_action,
                    "last_recorded_at": _iso(entry.state.last_recorded_at),
                    "revision_count": entry.state.revision_count,
                },
                "instrument_ticker": ticker,
                "information_context": {
                    "population": info_population,
                    "clusters": clusters,
                },
                "has_new_information": has_new,
                "urgency_reasons": reasons,
            }
        )

    due_entries: list[dict[str, Any]] = []
    for rank, entry in enumerate(sorted(due, key=due_sort_key), start=1):
        effective_due = entry.state.review_due_at
        # narrowing mypy, garde réelle au-dessus
        assert effective_due is not None  # due entries always carry one  # noqa: S101
        has_new, reasons = urgency_by_id.get(entry.thesis.id, (False, []))
        due_entries.append(
            {
                "rank": rank,
                "thesis_id": entry.thesis.id,
                "title": entry.thesis.title,
                "review_due_at": _iso(effective_due),
                "overdue_seconds": max(0, int((now - effective_due).total_seconds())),
                "last_recorded_at": _iso(entry.state.last_recorded_at),
                "has_new_information": has_new,
                "urgency_reasons": reasons,
            }
        )

    return {
        "schema_version": REVIEW_QUEUE_SCHEMA_VERSION,
        "as_of": now.isoformat(),
        # Two SEPARATE population labels, deliberately never merged into one:
        # user-declared theses on one side, sourced information on the other.
        "populations": {
            "theses": POPULATION_THESES,
            "information_context": info_population,
        },
        "ordering": {
            "method": "lexicographic",
            "keys": list(DUE_ORDERING_KEYS),
            "note": (
                "new information raises visible urgency (flag + reasons) but "
                "never rewrites the thesis, its revisions or its due instant"
            ),
        },
        "theses": theses_entries,
        "due": due_entries,
        "coverage": {
            "theses_total": len(theses_entries),
            "due_count": len(due_entries),
            "theses_with_instrument": with_instrument,
            "theses_with_new_information": with_new_information,
            "observations_considered": len(records),
            "content_observations": content_count,
            "clusters": cluster_count,
            "lookback_seconds": int(config.lookback.total_seconds()),
        },
    }


# --------------------------------------------------------------------------
# Handler and registration
# --------------------------------------------------------------------------


class ReviewQueueHandler:
    """Handler of ``review_queue.refresh``: recompute the global review queue.

    Read-only over theses (projection + due filter through the repository)
    and observations; the ONLY write is the snapshot publication. No thesis,
    revision or ledger row is ever created, updated or deleted here.
    """

    def __init__(self, *, config: FusionConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        # Local import avoids a module cycle (handlers -> ingest -> follow_up).
        from vertex_worker.handlers import (
            load_recent_observation_records,
            publish_if_changed,
        )

        now = _require_aware_utc(self._clock())
        projected = list_theses(session, now=now)
        due = review_queue_due(session, now=now)
        records = load_recent_observation_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
        )
        content = build_review_queue_content(
            projected, due, records, now=now, config=self._config
        )
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_REVIEW_QUEUE,
            key=SNAPSHOT_KEY_GLOBAL,
            content=content,
            as_of=now,
        )
        if published is None:
            log.info("review queue snapshot unchanged (message_id=%s)", message.id)
        else:
            log.info(
                "review queue snapshot published version=%s (message_id=%s)",
                published.version,
                message.id,
            )


def register_follow_up_handler(
    registry: HandlerRegistry, *, clock: Clock, config: FusionConfig
) -> None:
    """Register the review queue handler on ``review_queue.refresh``."""
    registry.register(
        TOPIC_REVIEW_QUEUE_REFRESH, ReviewQueueHandler(config=config, clock=clock)
    )
