"""Ingestion entry point: observation insert + outbox enqueue, one transaction.

``ingest_envelope`` writes the observation (idempotent by ``event_id``) and,
only when a row was actually written, enqueues the ``observation.ingested``
outbox message in the SAME transaction (ADR-006 atomicity: the business write
and its job commit or roll back together). Nothing is committed here — the
caller owns the transaction.

Daily-quote envelopes additionally enqueue a ``quotes.ingested`` message
(same transaction, same idempotence): the markets overview handler owns that
topic (``vertex_worker.markets``), while ``observation.ingested`` stays owned
by the attention fusion handler — one handler per topic, no overloading.

A best-effort ``NOTIFY`` on :data:`OUTBOX_NOTIFY_CHANNEL` is also emitted so
a listening worker wakes up early; PostgreSQL delivers it only when the
surrounding transaction commits, and losing it is harmless because the
worker's polling remains the delivery guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from vertex_core.contracts import DataEnvelope
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import enqueue_outbox

from vertex_worker.analysis import TOPIC_ANALYSIS_INGESTED, is_daily_bars_schema
from vertex_worker.follow_up import TOPIC_REVIEW_QUEUE_REFRESH
from vertex_worker.markets import TOPIC_QUOTES_INGESTED, is_daily_quote_schema
from vertex_worker.options import (
    TOPIC_OPTION_CHAINS_INGESTED,
    is_option_chain_schema,
)

__all__ = [
    "TOPIC_OBSERVATION_INGESTED",
    "OUTBOX_NOTIFY_CHANNEL",
    "IngestResult",
    "ingest_envelope",
]


TOPIC_OBSERVATION_INGESTED = "observation.ingested"
"""Outbox topic enqueued for every newly written observation."""

OUTBOX_NOTIFY_CHANNEL = "vertex_outbox"
"""LISTEN/NOTIFY wake-up channel (signal only; tables stay the durable source)."""


@dataclass(frozen=True)
class IngestResult:
    """Outcome of one ingestion attempt.

    ``inserted`` is ``False`` for a duplicate ``event_id`` (idempotent
    replay): the original observation is untouched and no outbox message is
    enqueued — the first ingestion already carries the job.
    """

    event_id: str
    inserted: bool
    outbox_message_id: Optional[int]


def ingest_envelope(session: Session, envelope: DataEnvelope) -> IngestResult:
    """Persist ``envelope`` and enqueue its fusion job atomically.

    Runs entirely inside the caller's transaction (no commit here). The
    observation insert is idempotent; the outbox enqueue happens if and only
    if a new row was written, so an at-least-once upstream delivery never
    duplicates jobs for the same observation.
    """
    if not isinstance(envelope, DataEnvelope):
        raise TypeError(
            f"envelope: expected DataEnvelope, got {type(envelope).__name__}"
        )

    inserted = insert_observation(
        session,
        event_id=envelope.event_id,
        schema_version=envelope.schema_version,
        source=envelope.source,
        source_event_id=envelope.source_event_id,
        instrument_ref=envelope.instrument_id,
        observed_at=envelope.observed_at,
        published_at=envelope.published_at,
        received_at=envelope.received_at,
        as_of=envelope.as_of,
        stale_after=envelope.stale_after,
        quality_status=envelope.quality_status.value,
        delay_status=envelope.delay_status.value,
        connection_epoch=envelope.connection_epoch,
        rights=envelope.rights,
        payload=envelope.payload,
    )
    if not inserted:
        return IngestResult(event_id=envelope.event_id, inserted=False, outbox_message_id=None)

    message_id = enqueue_outbox(
        session,
        TOPIC_OBSERVATION_INGESTED,
        {
            "event_id": envelope.event_id,
            "source": envelope.source,
            "schema_version": envelope.schema_version,
        },
    )
    if is_daily_quote_schema(envelope.schema_version):
        # Additional markets job, same transaction and same idempotence: it is
        # enqueued only when the observation row was actually inserted.
        enqueue_outbox(
            session,
            TOPIC_QUOTES_INGESTED,
            {
                "event_id": envelope.event_id,
                "source": envelope.source,
                "schema_version": envelope.schema_version,
            },
        )
    if is_option_chain_schema(envelope.schema_version):
        # Additional option-chain job (same transaction, same idempotence):
        # the option-chain handler owns that topic (vertex_worker.options).
        enqueue_outbox(
            session,
            TOPIC_OPTION_CHAINS_INGESTED,
            {
                "event_id": envelope.event_id,
                "source": envelope.source,
                "schema_version": envelope.schema_version,
            },
        )
    if is_daily_bars_schema(envelope.schema_version) or is_option_chain_schema(
        envelope.schema_version
    ):
        # Analysis dossier job: bars change the series, a chain changes the
        # scenario basis. For a chain envelope this message is enqueued
        # AFTER its option-chain job, so a drained outbox recomputes the
        # chain snapshot before the dossier reads it.
        enqueue_outbox(
            session,
            TOPIC_ANALYSIS_INGESTED,
            {
                "event_id": envelope.event_id,
                "source": envelope.source,
                "schema_version": envelope.schema_version,
            },
        )
    # Review-queue refresh "après observation.ingested" (page 09, documented
    # here): every NEWLY inserted observation may change the novelty context
    # of a thesis, so one review_queue.refresh job is enqueued in the SAME
    # transaction with the same idempotence (only when the row was actually
    # written). The registry is one-handler-per-topic, so the review-queue
    # handler owns its own topic instead of sharing observation.ingested.
    enqueue_outbox(
        session,
        TOPIC_REVIEW_QUEUE_REFRESH,
        {
            "event_id": envelope.event_id,
            "source": envelope.source,
            "schema_version": envelope.schema_version,
        },
    )
    # Wake-up signal only, delivered on commit; its loss is tolerated because
    # the worker polls the outbox table (ADR-006: NOTIFY is never the queue).
    session.execute(
        text("SELECT pg_notify(:channel, :topic)"),
        {"channel": OUTBOX_NOTIFY_CHANNEL, "topic": TOPIC_OBSERVATION_INGESTED},
    )
    return IngestResult(
        event_id=envelope.event_id, inserted=True, outbox_message_id=message_id
    )
