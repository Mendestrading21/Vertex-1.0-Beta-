"""Unit tests of the capabilities snapshot builder (honest empty snapshot)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from vertex_worker.handlers import (
    CAPABILITIES_SCHEMA_VERSION,
    ObservationRecord,
    build_capabilities_content,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


def capability_record(
    source: str, number: int, *, probe_id: str = "probe-0001"
) -> ObservationRecord:
    as_of = NOW - timedelta(hours=2) + timedelta(minutes=number)
    return ObservationRecord(
        event_id=f"{source}:capability:{number:04d}",
        source=source,
        source_event_id=None,
        instrument_ref=None,
        published_at=None,
        received_at=as_of,
        as_of=as_of,
        quality_status="VALID",
        rights="DEMO",
        schema_version="source-capability/1.0",
        payload={
            "probe_id": probe_id,
            "connection_epoch": 1,
            "tested_at": as_of.isoformat(),
            "fields": [
                {"capability_id": "quotes", "field": "bid", "status": "DELAYED"}
            ],
        },
    )


class TestBuildCapabilitiesContent:
    def test_empty_is_honest_never_invented(self) -> None:
        content = build_capabilities_content([], now=NOW)
        assert content == {
            "schema_version": CAPABILITIES_SCHEMA_VERSION,
            "as_of": NOW.isoformat(),
            "probed_sources": [],
        }

    def test_latest_probe_per_source_wins(self) -> None:
        records = [
            capability_record("edge-demo", 1, probe_id="probe-old"),
            capability_record("edge-demo", 2, probe_id="probe-new"),
        ]
        content = build_capabilities_content(records, now=NOW)
        assert len(content["probed_sources"]) == 1
        entry = content["probed_sources"][0]
        assert entry["source"] == "edge-demo"
        assert entry["snapshot"]["probe_id"] == "probe-new"

    def test_sources_sorted_and_probe_payload_relayed_verbatim(self) -> None:
        records = [
            capability_record("zeta-source", 1),
            capability_record("alpha-source", 2),
        ]
        content = build_capabilities_content(records, now=NOW)
        assert [e["source"] for e in content["probed_sources"]] == [
            "alpha-source",
            "zeta-source",
        ]
        for entry in content["probed_sources"]:
            assert entry["snapshot"]["fields"][0]["status"] == "DELAYED"
            assert entry["synthetic"] is False
            assert entry["as_of"] is not None

    def test_naive_now_rejected(self) -> None:
        with pytest.raises(ValueError):
            build_capabilities_content([], now=datetime(2026, 8, 25, 12, 0, 0))
