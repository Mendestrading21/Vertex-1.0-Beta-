"""SEC EDGAR point-in-time normalisation, entirely synthetic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality, canonical_json_hash
from vertex_edge_official.sec import SecNormalizationError, normalize_sec_edgar

RECEIVED_AT = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _raw(schema: str, family: str, response: dict) -> DataEnvelope[dict]:
    payload = {"cik": "0000320193", "family": family, "response": response}
    return DataEnvelope[dict](
        event_id=f"raw:{family}",
        schema_version=schema,
        source="sec_edgar",
        source_event_id=f"CIK0000320193:{family}",
        entitlement_id=None,
        instrument_id=None,
        observed_at=None,
        published_at=None,
        received_at=RECEIVED_AT,
        as_of=RECEIVED_AT,
        stale_after=RECEIVED_AT + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.UNKNOWN,
        connection_epoch=None,
        rights="R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28",
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


def _submissions() -> DataEnvelope[dict]:
    return _raw(
        "sec.edgar.submissions/1",
        "submissions",
        {
            "cik": "320193",
            "name": "Apple Inc.",
            "tickers": ["AAPL"],
            "exchanges": ["Nasdaq"],
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-26-000001", "0000320193-26-000002"],
                    "filingDate": ["2026-01-30", "2026-02-02"],
                    "reportDate": ["2025-12-27", "2025-12-27"],
                    "acceptanceDateTime": ["2026-01-30T21:05:01.000Z", "2026-02-02T22:06:02.000Z"],
                    "form": ["10-Q", "10-Q/A"],
                    "primaryDocument": ["aapl-20251227.htm", "aapl-20251227x10qa.htm"],
                    "primaryDocDescription": ["10-Q", "10-Q amendment"],
                    "isXBRL": [1, 1],
                    "isInlineXBRL": [1, 1],
                }
            },
        },
    )


def _company_facts() -> DataEnvelope[dict]:
    return _raw(
        "sec.edgar.company-facts/1",
        "api/xbrl/companyfacts",
        {
            "cik": 320193,
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "label": "Assets",
                        "description": "Total assets",
                        "units": {
                            "USD": [
                                {
                                    "end": "2025-12-27",
                                    "val": 12345678901234567890,
                                    "accn": "0000320193-26-000001",
                                    "fy": 2026,
                                    "fp": "Q1",
                                    "form": "10-Q",
                                    "filed": "2026-01-30",
                                    "frame": "CY2025Q4I",
                                },
                                {
                                    "end": "2025-12-27",
                                    "val": 12345678901234567891,
                                    "accn": "0000320193-26-000002",
                                    "fy": 2026,
                                    "fp": "Q1",
                                    "form": "10-Q/A",
                                    "filed": "2026-02-02",
                                    "frame": "CY2025Q4I",
                                },
                            ]
                        },
                    }
                }
            },
        },
    )


def test_normalizer_preserves_filings_amendment_exact_decimal_and_available_at() -> None:
    envelopes = normalize_sec_edgar(
        _submissions(), _company_facts(), instrument_ref="AAPL"
    )

    filings = [item for item in envelopes if item.schema_version == "sec.edgar.filing/1"]
    facts = [item for item in envelopes if item.schema_version == "sec.edgar.fundamental-fact/1"]
    assert len(filings) == 2
    assert len(facts) == 2
    assert all(item.instrument_id == "AAPL" for item in envelopes)
    assert facts[0].payload["value"] == "12345678901234567890"
    assert facts[1].payload["is_amendment"] is True
    assert facts[1].published_at == datetime(2026, 2, 2, 22, 6, 2, tzinfo=UTC)
    assert facts[1].as_of == facts[1].published_at
    assert facts[1].stale_after == facts[1].published_at + timedelta(days=7)
    assert filings[1].payload["supersedes_accession"] == "0000320193-26-000001"
    assert len(facts[1].payload["source_observation_ids"]) == 2
    assert all(
        value.startswith("sha256:")
        for value in facts[1].payload["source_payload_hashes"]
    )


def test_normalizer_is_order_independent() -> None:
    first = normalize_sec_edgar(_submissions(), _company_facts(), instrument_ref="AAPL")
    payload = _company_facts().payload["response"]
    payload["facts"]["us-gaap"]["Assets"]["units"]["USD"].reverse()
    reordered = normalize_sec_edgar(
        _submissions(),
        _raw("sec.edgar.company-facts/1", "api/xbrl/companyfacts", payload),
        instrument_ref="AAPL",
    )
    assert [item.event_id for item in first] == [item.event_id for item in reordered]


def test_normalizer_refuses_mismatched_parallel_submission_arrays() -> None:
    submissions = _submissions()
    submissions.payload["response"]["filings"]["recent"]["form"].pop()
    with pytest.raises(SecNormalizationError, match="parallel arrays"):
        normalize_sec_edgar(submissions, _company_facts(), instrument_ref="AAPL")


def test_missing_acceptance_uses_next_day_and_excludes_future_fact() -> None:
    submissions = _submissions()
    recent = submissions.payload["response"]["filings"]["recent"]
    recent["filingDate"][1] = "2026-08-31"
    recent["acceptanceDateTime"][1] = ""
    facts = _company_facts()
    amended = facts.payload["response"]["facts"]["us-gaap"]["Assets"]["units"]["USD"][1]
    amended["filed"] = "2026-08-31"

    envelopes = normalize_sec_edgar(submissions, facts, instrument_ref="AAPL")

    assert all(item.payload["accession"] != "0000320193-26-000002" for item in envelopes)
