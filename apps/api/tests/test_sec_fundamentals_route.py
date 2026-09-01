"""SEC fundamentals route: protected, verbatim and honestly absent."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from snapshot_fakes import FakeSnapshotReader, synthetic_session

from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError, build_sec_fundamentals_response
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
INSTRUMENT = "AAPL"


def content() -> dict:
    return {
        "schema_version": "vertex.sec-fundamentals/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "REAL",
        "instrument": INSTRUMENT,
        "source": "sec_edgar",
        "rights": "R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28",
        "identity_state": "RESOLVED",
        "cik": "0000320193",
        "entity_name": "Apple Inc.",
        "data_as_of": AS_OF.isoformat(),
        "filings": [
            {
                "accession": "0000320193-26-000080",
                "form": "10-Q",
                "available_at": AS_OF.isoformat(),
                "primary_document_url": (
                    "https://www.sec.gov/Archives/edgar/data/320193/"
                    "000032019326000080/aapl-20260627.htm"
                ),
            }
        ],
        "facts": [
            {
                "taxonomy": "us-gaap",
                "concept": "Assets",
                "value": "110",
                "unit": "USD",
                "period_end": "2026-06-27",
                "available_at": AS_OF.isoformat(),
                "accession": "0000320193-26-000080",
            }
        ],
        "conflicts": [],
        "coverage": {
            "observations_considered": 2,
            "published_filings": 1,
            "published_facts": 1,
            "conflicting_fact_keys": 0,
        },
    }


def snapshot() -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="sec_fundamentals",
        key=INSTRUMENT,
        version=3,
        content=content(),
        content_hash="sha256:" + "a" * 64,
        as_of=AS_OF,
    )


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def sec_client(app: FastAPI, reader: FakeSnapshotReader) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    app.dependency_overrides[get_clock] = lambda: (lambda: AS_OF + timedelta(hours=1))
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def test_requires_session(client: TestClient) -> None:
    assert client.get(f"/api/v1/sources/sec/{INSTRUMENT}/fundamentals").status_code == 401


def test_absence_is_an_honest_empty_state(sec_client: TestClient) -> None:
    body = sec_client.get(f"/api/v1/sources/sec/{INSTRUMENT}/fundamentals").json()
    assert body["state"] == "empty"
    assert body["facts"] == []
    assert body["filings"] == []
    assert body["reason"] == "no snapshot published"


def test_official_snapshot_is_relayed_without_calculation(
    sec_client: TestClient, reader: FakeSnapshotReader
) -> None:
    reader.snapshots[("sec_fundamentals", INSTRUMENT)] = snapshot()

    response = sec_client.get(f"/api/v1/sources/sec/{INSTRUMENT}/fundamentals")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert body["source"] == "sec_edgar"
    assert body["facts"] == content()["facts"]
    assert body["filings"] == content()["filings"]
    assert "ratio" not in body
    assert "advice" not in body


def test_snapshot_key_mismatch_is_refused() -> None:
    with pytest.raises(SnapshotContentError):
        build_sec_fundamentals_response(
            snapshot(), instrument="MSFT", now=AS_OF + timedelta(hours=1)
        )
