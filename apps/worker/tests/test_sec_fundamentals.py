"""Pure SEC point-in-time snapshot tests; no database and no network."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.sec_fundamentals import (
    SEC_FACT_SCHEMA,
    SEC_FILING_SCHEMA,
    SEC_SNAPSHOT_SCHEMA_VERSION,
    TOPIC_SEC_FUNDAMENTALS_INGESTED,
    SecObservationRecord,
    build_sec_fundamentals_content,
    is_sec_fundamentals_schema,
)

NOW = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
RIGHTS = "R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28"


def fact_record(
    *,
    event_id: str,
    value: str,
    available_at: datetime,
    accession: str = "0000320193-26-000080",
    cik: str = "0000320193",
) -> SecObservationRecord:
    return SecObservationRecord(
        event_id=event_id,
        source="sec_edgar",
        instrument_ref="AAPL",
        as_of=available_at,
        rights=RIGHTS,
        schema_version=SEC_FACT_SCHEMA,
        payload={
            "authority": "SEC_EDGAR",
            "source_observation_ids": ["sec-raw-submissions", "sec-raw-facts"],
            "source_payload_hashes": ["sha256:" + "a" * 64, "sha256:" + "b" * 64],
            "cik": cik,
            "entity_name": "Apple Inc.",
            "taxonomy": "us-gaap",
            "concept": "Assets",
            "label": "Assets",
            "description": None,
            "value": value,
            "unit": "USD",
            "period_start": None,
            "period_end": "2026-06-27",
            "filed_date": "2026-07-31",
            "available_at": available_at.isoformat(),
            "accession": accession,
            "form": "10-Q",
            "fiscal_year": 2026,
            "fiscal_period": "Q3",
            "frame": "CY2026Q2I",
            "dimensions": {},
            "is_amendment": False,
        },
    )


def filing_record() -> SecObservationRecord:
    available_at = NOW - timedelta(days=28)
    return SecObservationRecord(
        event_id="filing-1",
        source="sec_edgar",
        instrument_ref="AAPL",
        as_of=available_at,
        rights=RIGHTS,
        schema_version=SEC_FILING_SCHEMA,
        payload={
            "authority": "SEC_EDGAR",
            "source_observation_ids": ["sec-raw-submissions", "sec-raw-facts"],
            "source_payload_hashes": ["sha256:" + "a" * 64, "sha256:" + "b" * 64],
            "cik": "0000320193",
            "entity_name": "Apple Inc.",
            "accession": "0000320193-26-000080",
            "form": "10-Q",
            "report_date": "2026-06-27",
            "filed_date": "2026-07-31",
            "accepted_at": available_at.isoformat(),
            "available_at": available_at.isoformat(),
            "primary_document": "aapl-20260627.htm",
            "primary_document_url": (
                "https://www.sec.gov/Archives/edgar/data/320193/"
                "000032019326000080/aapl-20260627.htm"
            ),
            "primary_document_description": "10-Q",
            "is_xbrl": True,
            "is_inline_xbrl": True,
            "is_amendment": False,
            "supersedes_accession": None,
        },
    )


def test_schema_predicate_and_registry_topic() -> None:
    assert is_sec_fundamentals_schema(SEC_FACT_SCHEMA) is True
    assert is_sec_fundamentals_schema(SEC_FILING_SCHEMA) is True
    assert is_sec_fundamentals_schema("sec.edgar.company-facts/1") is False
    registry = build_registry(clock=lambda: NOW, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_SEC_FUNDAMENTALS_INGESTED in registry.topics


def test_snapshot_is_point_in_time_and_keeps_latest_correction() -> None:
    original_at = NOW - timedelta(days=20)
    correction_at = NOW - timedelta(days=10)
    records = [
        filing_record(),
        fact_record(event_id="original", value="100", available_at=original_at),
        fact_record(
            event_id="correction",
            value="110",
            available_at=correction_at,
            accession="0000320193-26-000081",
        ),
        fact_record(
            event_id="future",
            value="999",
            available_at=NOW + timedelta(seconds=1),
            accession="0000320193-26-000082",
        ),
    ]

    content = build_sec_fundamentals_content(records, instrument="AAPL", now=NOW)

    assert content["schema_version"] == SEC_SNAPSHOT_SCHEMA_VERSION
    assert content["population"] == "REAL"
    assert content["identity_state"] == "RESOLVED"
    assert content["cik"] == "0000320193"
    assert content["facts"][0]["value"] == "110"
    assert content["coverage"]["corrections_observed"] == 1
    assert content["coverage"]["future_observations_excluded"] == 1
    assert content["filings"][0]["accession"] == "0000320193-26-000080"


def test_same_availability_conflict_is_exposed_and_not_elected() -> None:
    available_at = NOW - timedelta(days=1)
    content = build_sec_fundamentals_content(
        [
            fact_record(event_id="a", value="100", available_at=available_at),
            fact_record(
                event_id="b",
                value="101",
                available_at=available_at,
                accession="0000320193-26-000081",
            ),
        ],
        instrument="AAPL",
        now=NOW,
    )

    assert content["facts"] == []
    assert content["coverage"]["conflicting_fact_keys"] == 1
    assert content["conflicts"][0]["values"] == ["100", "101"]


def test_conflicting_cik_refuses_business_values() -> None:
    content = build_sec_fundamentals_content(
        [
            fact_record(event_id="a", value="100", available_at=NOW),
            fact_record(
                event_id="b",
                value="200",
                available_at=NOW,
                cik="0000789019",
            ),
        ],
        instrument="AAPL",
        now=NOW,
    )

    assert content["identity_state"] == "CONFLICTING_IDENTITY"
    assert content["cik"] is None
    assert content["facts"] == []
