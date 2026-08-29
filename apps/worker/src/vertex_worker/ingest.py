"""Ingestion entry point: observation insert + outbox enqueue, one transaction.

``ingest_envelope`` writes the observation (idempotent by ``event_id``) and,
only when a row was actually written, enqueues the ``observation.ingested``
outbox message in the SAME transaction (ADR-006 atomicity: the business write
and its job commit or roll back together). Nothing is committed here — the
caller owns the transaction.

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
    # Wake-up signal only, delivered on commit; its loss is tolerated because
    # the worker polls the outbox table (ADR-006: NOTIFY is never the queue).
    session.execute(
        text("SELECT pg_notify(:channel, :topic)"),
        {"channel": OUTBOX_NOTIFY_CHANNEL, "topic": TOPIC_OBSERVATION_INGESTED},
    )
    return IngestResult(
        event_id=envelope.event_id, inserted=True, outbox_message_id=message_id
    )
