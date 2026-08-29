"""Append-only observation store (idempotent by ``event_id``)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vertex_core.contracts import canonical_json_hash

from vertex_persistence.enums import (
    OBSERVATION_DELAY_STATUSES,
    OBSERVATION_QUALITY_STATUSES,
    validate_enum_value,
)
from vertex_persistence.errors import ValidationFailedError
from vertex_persistence.json_codec import to_jsonb_object
from vertex_persistence.models import Observation
from vertex_persistence.repository._validation import (
    require_aware_utc,
    require_non_empty_str,
    require_optional_str,
)

__all__ = ["insert_observation"]


def insert_observation(
    session: Session,
    *,
    event_id: str,
    schema_version: str,
    source: str,
    received_at: datetime,
    as_of: datetime,
    stale_after: datetime,
    quality_status: str,
    delay_status: str,
    rights: str,
    payload: Any,
    source_event_id: Optional[str] = None,
    instrument_ref: Optional[str] = None,
    observed_at: Optional[datetime] = None,
    published_at: Optional[datetime] = None,
    connection_epoch: Optional[int] = None,
) -> bool:
    """Insert one observation; return ``True`` if a row was written.

    Idempotent: ``INSERT .. ON CONFLICT (event_id) DO NOTHING``. A duplicate
    ``event_id`` writes nothing and returns ``False`` — the original row is
    never overwritten (observations are append-only facts).

    The payload is encoded fail-closed (Decimal -> exact string, aware
    datetime -> UTC ISO, naive/NaN/Infinity rejected) and its
    ``payload_hash`` is the canonical JSON hash of the stored form.
    Runs inside the caller's transaction; nothing is committed here.
    """
    encoded_payload = to_jsonb_object("payload", payload)
    if connection_epoch is not None and (
        not isinstance(connection_epoch, int) or isinstance(connection_epoch, bool)
    ):
        raise ValidationFailedError(
            f"connection_epoch: expected int or None, got {type(connection_epoch).__name__}"
        )

    values: dict[str, Any] = {
        "event_id": require_non_empty_str("event_id", event_id),
        "schema_version": require_non_empty_str("schema_version", schema_version),
        "source": require_non_empty_str("source", source),
        "source_event_id": require_optional_str("source_event_id", source_event_id),
        "instrument_ref": require_optional_str("instrument_ref", instrument_ref),
        "observed_at": (
            require_aware_utc("observed_at", observed_at) if observed_at is not None else None
        ),
        "published_at": (
            require_aware_utc("published_at", published_at) if published_at is not None else None
        ),
        "received_at": require_aware_utc("received_at", received_at),
        "as_of": require_aware_utc("as_of", as_of),
        "stale_after": require_aware_utc("stale_after", stale_after),
        "quality_status": validate_enum_value(
            "quality_status", quality_status, OBSERVATION_QUALITY_STATUSES
        ),
        "delay_status": validate_enum_value(
            "delay_status", delay_status, OBSERVATION_DELAY_STATUSES
        ),
        "connection_epoch": connection_epoch,
        "rights": require_non_empty_str("rights", rights),
        "payload": encoded_payload,
        "payload_hash": canonical_json_hash(encoded_payload),
    }

    statement = (
        pg_insert(Observation)
        .values(**values)
        .on_conflict_do_nothing(index_elements=[Observation.event_id])
        # Explicit RETURNING makes idempotence observable: a conflicting
        # event_id returns no row (driver rowcount is unreliable here).
        .returning(Observation.id)
    )
    result = session.execute(statement)
    return result.first() is not None
