"""Generic source envelope wrapping every external observation.

A ``DataEnvelope`` carries provenance (source, event ids, entitlement),
temporality (``observed_at``, ``published_at``, ``received_at``, ``as_of``,
``stale_after``), quality (``EnvelopeQuality``), delay (``DelayStatus``),
rights and a canonical payload hash. Absent metadata stays ``None``; it is
never defaulted to a fabricated value.
"""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import model_validator

from vertex_core.contracts.enums import DelayStatus, EnvelopeQuality
from vertex_core.contracts.types import (
    ContractModel,
    NonEmptyStr,
    Sha256Ref,
    UtcDatetime,
)

__all__ = ["DataEnvelope"]

TPayload = TypeVar("TPayload")


class DataEnvelope(ContractModel, Generic[TPayload]):
    """Strict, immutable envelope for one sourced observation of type ``TPayload``.

    Temporal invariants: all timestamps are timezone-aware UTC, and
    ``observed_at <= received_at`` whenever both are present (an observation
    cannot be observed after it was received).
    """

    event_id: NonEmptyStr
    schema_version: NonEmptyStr
    source: NonEmptyStr
    source_event_id: Optional[NonEmptyStr] = None
    entitlement_id: Optional[NonEmptyStr] = None
    instrument_id: Optional[NonEmptyStr] = None
    observed_at: Optional[UtcDatetime] = None
    published_at: Optional[UtcDatetime] = None
    received_at: UtcDatetime
    as_of: UtcDatetime
    stale_after: UtcDatetime
    quality_status: EnvelopeQuality
    delay_status: DelayStatus
    connection_epoch: Optional[int] = None
    rights: NonEmptyStr
    payload_hash: Sha256Ref
    payload: TPayload

    @model_validator(mode="after")
    def _check_temporal_consistency(self) -> "DataEnvelope[TPayload]":
        if self.observed_at is not None and self.observed_at > self.received_at:
            raise ValueError("observed_at must not be later than received_at")
        return self
