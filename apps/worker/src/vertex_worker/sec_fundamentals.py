"""Point-in-time SEC EDGAR snapshots built from normalized observations.

The worker relays official filings and XBRL facts.  It never calculates a
ratio, fills a missing value or turns a regulatory publication into advice.
Corrections remain append-only observations; the snapshot selects only facts
available at the injected clock and exposes conflicts instead of electing a
business value from an arbitrary order.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_core.contracts import Filing, FundamentalFact, canonical_json_hash
from vertex_persistence.models import Observation
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "SEC_FACT_SCHEMA",
    "SEC_FILING_SCHEMA",
    "SEC_SNAPSHOT_SCHEMA_VERSION",
    "SNAPSHOT_KIND_SEC_FUNDAMENTALS",
    "TOPIC_SEC_FUNDAMENTALS_INGESTED",
    "SecFundamentalsHandler",
    "SecObservationRecord",
    "build_sec_fundamentals_content",
    "is_sec_fundamentals_schema",
    "load_sec_observation_records",
    "register_sec_fundamentals_handler",
]

log = logging.getLogger("vertex_worker.sec_fundamentals")

Clock = Callable[[], datetime]

SEC_SOURCE = "sec_edgar"
SEC_RIGHTS = "R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28"
SEC_FILING_SCHEMA = "sec.edgar.filing/1"
SEC_FACT_SCHEMA = "sec.edgar.fundamental-fact/1"
SEC_SCHEMAS = (SEC_FILING_SCHEMA, SEC_FACT_SCHEMA)

TOPIC_SEC_FUNDAMENTALS_INGESTED = "sec.fundamentals.ingested"
SNAPSHOT_KIND_SEC_FUNDAMENTALS = "sec_fundamentals"
SEC_SNAPSHOT_SCHEMA_VERSION = "vertex.sec-fundamentals/1.0"

MAX_FACTS = 500
MAX_FILINGS = 50
MAX_OBSERVATIONS = 5_000


def is_sec_fundamentals_schema(schema_version: str) -> bool:
    """Return whether a schema is one of the two normalized SEC families."""
    return isinstance(schema_version, str) and schema_version in SEC_SCHEMAS


def _utc(value: datetime, *, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field}: expected datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{field}: timezone-aware datetime required")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class SecObservationRecord:
    """ORM-free view of one normalized SEC observation."""

    event_id: str
    source: str
    instrument_ref: str | None
    as_of: datetime
    rights: str
    schema_version: str
    payload: Mapping[str, Any]


def load_sec_observation_records(
    session: Session, *, instrument: str, now: datetime, limit: int = MAX_OBSERVATIONS
) -> list[SecObservationRecord]:
    """Load the bounded SEC history available at ``now`` for one instrument."""
    current = _utc(now, field="now")
    if not instrument.strip():
        raise ValueError("instrument: non-empty string required")
    if limit < 1:
        raise ValueError("limit: positive integer required")
    rows = (
        session.execute(
            select(Observation)
            .where(
                Observation.instrument_ref == instrument,
                Observation.source == SEC_SOURCE,
                Observation.schema_version.in_(SEC_SCHEMAS),
                Observation.as_of <= current,
            )
            .order_by(Observation.as_of.desc(), Observation.event_id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        SecObservationRecord(
            event_id=row.event_id,
            source=row.source,
            instrument_ref=row.instrument_ref,
            as_of=row.as_of,
            rights=row.rights,
            schema_version=row.schema_version,
            payload=row.payload,
        )
        for row in rows
    ]


def _fact_key(fact: FundamentalFact) -> tuple[str, ...]:
    dimensions_hash = canonical_json_hash(dict(fact.dimensions))
    return (
        fact.taxonomy,
        fact.concept,
        fact.unit,
        fact.period_start.isoformat() if fact.period_start is not None else "",
        fact.period_end.isoformat(),
        fact.frame or "",
        dimensions_hash,
    )


def _rejection(event_id: str, reason: str) -> dict[str, str]:
    return {"event_id": event_id, "reason": reason}


def build_sec_fundamentals_content(
    records: Sequence[SecObservationRecord], *, instrument: str, now: datetime
) -> dict[str, Any]:
    """Build one deterministic, point-in-time SEC snapshot."""
    current = _utc(now, field="now")
    if not instrument.strip():
        raise ValueError("instrument: non-empty string required")

    filings: list[tuple[SecObservationRecord, Filing]] = []
    facts: list[tuple[SecObservationRecord, FundamentalFact]] = []
    rejected: list[dict[str, str]] = []
    future_count = 0

    for record in sorted(records, key=lambda item: (item.as_of, item.event_id)):
        if record.as_of > current:
            future_count += 1
            continue
        if record.instrument_ref != instrument:
            rejected.append(_rejection(record.event_id, "instrument_mismatch"))
            continue
        if record.source != SEC_SOURCE:
            rejected.append(_rejection(record.event_id, "source_not_allowed"))
            continue
        if record.rights != SEC_RIGHTS:
            rejected.append(_rejection(record.event_id, "rights_not_usable"))
            continue
        try:
            if record.schema_version == SEC_FILING_SCHEMA:
                filing = Filing.model_validate_json(json.dumps(record.payload))
                if filing.available_at != record.as_of:
                    rejected.append(_rejection(record.event_id, "available_at_mismatch"))
                    continue
                filings.append((record, filing))
            elif record.schema_version == SEC_FACT_SCHEMA:
                fact = FundamentalFact.model_validate_json(json.dumps(record.payload))
                if fact.available_at != record.as_of:
                    rejected.append(_rejection(record.event_id, "available_at_mismatch"))
                    continue
                facts.append((record, fact))
            else:
                rejected.append(_rejection(record.event_id, "schema_not_allowed"))
        except ValidationError:
            rejected.append(_rejection(record.event_id, "invalid_payload"))

    identities = sorted(
        {(item.cik, item.entity_name) for _, item in filings}
        | {(item.cik, item.entity_name) for _, item in facts}
    )
    if len(identities) > 1:
        filings = []
        facts = []
        identity_state = "CONFLICTING_IDENTITY"
        cik: str | None = None
        entity_name: str | None = None
    elif identities:
        identity_state = "RESOLVED"
        cik, entity_name = identities[0]
    else:
        identity_state = "ABSENT"
        cik = None
        entity_name = None

    latest_filings: dict[str, tuple[SecObservationRecord, Filing]] = {}
    for record, filing in filings:
        previous = latest_filings.get(filing.accession)
        if previous is None or (record.as_of, record.event_id) > (
            previous[0].as_of,
            previous[0].event_id,
        ):
            latest_filings[filing.accession] = (record, filing)
    filing_values = sorted(
        (item for _, item in latest_filings.values()),
        key=lambda item: (item.available_at, item.accession),
        reverse=True,
    )

    fact_groups: dict[tuple[str, ...], list[tuple[SecObservationRecord, FundamentalFact]]] = (
        defaultdict(list)
    )
    for record, fact in facts:
        fact_groups[_fact_key(fact)].append((record, fact))

    selected_facts: list[FundamentalFact] = []
    conflicts: list[dict[str, Any]] = []
    corrections = 0
    for key in sorted(fact_groups):
        candidates = fact_groups[key]
        corrections += max(0, len(candidates) - 1)
        latest_at = max(item.available_at for _, item in candidates)
        latest = [(record, item) for record, item in candidates if item.available_at == latest_at]
        distinct_values = sorted({format(item.value, "f") for _, item in latest})
        if len(distinct_values) > 1:
            conflicts.append(
                {
                    "fact_key": list(key),
                    "available_at": latest_at.isoformat(),
                    "values": distinct_values,
                    "event_ids": sorted(record.event_id for record, _ in latest),
                }
            )
            continue
        selected_facts.append(
            max(latest, key=lambda pair: (pair[1].accession, pair[0].event_id))[1]
        )

    selected_facts.sort(
        key=lambda item: (
            item.taxonomy,
            item.concept,
            item.unit,
            item.period_end,
            item.available_at,
            item.accession,
        ),
        reverse=True,
    )
    published_facts = selected_facts[:MAX_FACTS]
    published_filings = filing_values[:MAX_FILINGS]
    available_instants = [item.available_at for item in filing_values]
    available_instants.extend(item.available_at for item in selected_facts)
    data_as_of = max(available_instants).isoformat() if available_instants else None

    return {
        "schema_version": SEC_SNAPSHOT_SCHEMA_VERSION,
        "as_of": current.isoformat(),
        "population": "REAL" if records else "EMPTY",
        "instrument": instrument,
        "source": SEC_SOURCE,
        "rights": SEC_RIGHTS,
        "identity_state": identity_state,
        "cik": cik,
        "entity_name": entity_name,
        "data_as_of": data_as_of,
        "filings": [item.model_dump(mode="json") for item in published_filings],
        "facts": [item.model_dump(mode="json") for item in published_facts],
        "conflicts": conflicts,
        "coverage": {
            "observations_considered": len(records),
            "future_observations_excluded": future_count,
            "rejected_records": rejected,
            "valid_filings": len(filing_values),
            "published_filings": len(published_filings),
            "truncated_filings": len(filing_values) - len(published_filings),
            "valid_fact_keys": len(selected_facts),
            "published_facts": len(published_facts),
            "truncated_facts": len(selected_facts) - len(published_facts),
            "corrections_observed": corrections,
            "conflicting_fact_keys": len(conflicts),
        },
    }


class SecFundamentalsHandler:
    """Recompute the SEC snapshot for the instrument carried by one event."""

    def __init__(self, *, clock: Clock) -> None:
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        from vertex_worker.handlers import publish_if_changed

        event_id = message.payload.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("SEC outbox payload requires event_id")
        instrument = session.execute(
            select(Observation.instrument_ref).where(Observation.event_id == event_id)
        ).scalar_one_or_none()
        if not isinstance(instrument, str) or not instrument:
            raise ValueError("SEC observation requires instrument_ref")
        now = _utc(self._clock(), field="clock")
        records = load_sec_observation_records(session, instrument=instrument, now=now)
        content = build_sec_fundamentals_content(records, instrument=instrument, now=now)
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_SEC_FUNDAMENTALS,
            key=instrument,
            content=content,
            as_of=now,
        )
        if published is None:
            log.info("SEC snapshot %s unchanged (message_id=%s)", instrument, message.id)
        else:
            log.info(
                "SEC snapshot %s published version=%s (message_id=%s)",
                instrument,
                published.version,
                message.id,
            )


def register_sec_fundamentals_handler(registry: HandlerRegistry, *, clock: Clock) -> None:
    """Register the sole owner of ``sec.fundamentals.ingested``."""
    registry.register(TOPIC_SEC_FUNDAMENTALS_INGESTED, SecFundamentalsHandler(clock=clock))
