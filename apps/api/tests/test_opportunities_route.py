"""GET /api/v1/opportunities: verbatim relay, honest empty, guard, 401.

Everything here is SYNTHETIC: the fake reader is injected explicitly through
``dependency_overrides`` and the snapshot content mirrors the exact shape the
worker publishes (``vertex_worker.opportunities.build_opportunities_content``).

The relay guard is the API-side mirror of the worker invariant: the qualified
group crosses status, published gates and required evidence, and every
excluded candidate publishes WHY it is excluded.

Re-audit (P1-8): the guard used to trust three things it never checked — the
gate-status vocabulary (a closed gate labeled ``block`` or ``CLOSED`` walked
into the qualified group), the required-evidence set (only its INTERNAL
consistency was checked, never the set the referenced profile really
requires) and the published horizon (checked worker-side only). Re-audit
(P1-9): the relay had no freshness bound at all, so a worker that refused to
publish (fail-closed ``RuntimeError`` -> retry -> DEAD) left the page serving
``state = "ok"`` with an arbitrarily old verdict and no signal.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import FakeSnapshotReader, synthetic_session
from vertex_api import opportunities as opportunities_module
from vertex_api.auth import require_session
from vertex_api.opportunities import (
    OPPORTUNITIES_MAX_AGE,
    build_opportunities_response,
)
from vertex_api.snapshot_reader import get_snapshot_reader
from vertex_api.snapshot_views import SnapshotContentError
from vertex_persistence.repository.snapshots import CurrentSnapshot

AS_OF = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)

#: Injected relay clock: the snapshots below are FRESH at this instant (no
#: system clock ever reaches a test).
NOW = AS_OF + timedelta(minutes=5)

CLOSED_STATUSES = ("BLOCKED", "INSUFFICIENT_DATA")

#: ``equity_etf_swing_3_12m`` of ``manifests/strategy-profiles.yaml`` — the
#: profile the published ``profile_ref`` below references.
PROFILE_EVIDENCE = (
    "regime",
    "sector",
    "price_volume",
    "fundamentals",
    "catalysts",
    "thesis",
    "invalidation",
    "manual_portfolio_fit",
)
PROFILE_HORIZON = "3m"

_UNSET = object()


def candidate(
    ticker: str,
    status: str,
    *,
    gate_status: Optional[str] = None,
    evidence_present: bool = True,
    absent_evidence: tuple[str, ...] = (),
    horizon: str = PROFILE_HORIZON,
    exclusion: Any = _UNSET,
) -> dict:
    """One candidate in the shape the worker publishes.

    Defaults are the honest ones: a closed status carries its BLOCK gate and
    its ``CLOSED_STATUS`` exclusion, an open status carries neither, and the
    required-evidence map holds EVERY evidence the referenced profile
    requires (what the worker really publishes).
    """
    closed = status in CLOSED_STATUSES
    resolved_gate = gate_status or ("BLOCK" if closed else "PASS")
    missing = tuple(absent_evidence) or (() if evidence_present else ("sector",))
    if exclusion is _UNSET:
        exclusion = (
            {
                "kind": "CLOSED_STATUS",
                "gate_id": "entitlements_sufficient",
                "reason_code": "UNEVALUABLE",
                "missing_evidence": [],
                "detail": "closed by gate entitlements_sufficient",
            }
            if closed
            else None
        )
    return {
        "ticker": ticker,
        "sector": "SYN-TECH",
        "advice": {
            "advice_id": "sha256:" + "b" * 64,
            "status": status,
            "direction": "UNKNOWN",
            "horizon": horizon,
            "as_of": AS_OF.isoformat(),
            "valid_until": AS_OF.isoformat(),
            "engine_version": "vertex_core@0.1.0",
        },
        "gates": [
            {
                "gate_id": "entitlements_sufficient",
                "status": resolved_gate,
                "reason_code": "UNEVALUABLE" if resolved_gate == "BLOCK" else "OK",
            }
        ],
        "degraded_gates": [],
        "required_evidence": {
            name: {
                "present": name not in missing,
                "detail": "SYN-TECH" if name not in missing else "absent",
            }
            for name in PROFILE_EVIDENCE
        },
        "missing_evidence": sorted(missing),
        "evidence_cluster_ids": [],
        "scenario_ids": [],
        "bars_status": "OK",
        "scenarios_status": "ABSENT",
        "population": "SYNTHETIC",
        "synthetic": True,
        "exclusion": exclusion,
        "primary_exclusion_reason": (
            {
                "gate_id": "entitlements_sufficient",
                "reason_code": "UNEVALUABLE",
            }
            if closed
            else None
        ),
    }


def opportunities_content(qualified: list[dict], excluded: list[dict]) -> dict:
    return {
        "schema_version": "vertex.opportunities/1.0",
        "as_of": AS_OF.isoformat(),
        "population": "SYNTHETIC",
        "engine_version": "vertex_core@0.1.0",
        "profile_ref": {
            "id": "equity_etf_swing_3_12m",
            "version": "1.0.0",
            "source": "manifests/strategy-profiles.yaml",
            "applied": ["required_evidence"],
            "not_applied": [
                {"field": "instruments", "reason": "no instrument-class source"}
            ],
        },
        "calendar_ref": {
            "kind": "calendar",
            "key": "global",
            "version": 1,
            "snapshot_as_of": AS_OF.isoformat(),
            "content_as_of": AS_OF.isoformat(),
            "content_schema_version": "vertex.calendar/1.0",
            "status": "USED",
            "max_age_seconds": 259200,
            "events_upcoming": 2,
            "events_ignored_past": 0,
            "events_without_ticker": 0,
            "events_rejected": 0,
        },
        "ordering": {"method": "lexicographic", "keys": [], "note": "documented"},
        "qualified": qualified,
        "excluded": excluded,
        "exclusion_reasons": {
            "entitlements_sufficient:UNEVALUABLE": len(excluded)
        },
        "limitations": ["SYNTHETIC development population"],
        "coverage": {
            "universe_size": 24,
            "qualified_count": len(qualified),
            "excluded_count": len(excluded),
            "status_counts": {},
            "population_counts": {"SYNTHETIC": 24},
            "observations_considered": 4,
            "lookback_seconds": 259200,
        },
    }


def snapshot(
    content: dict, version: int = 1, *, as_of: Optional[datetime] = None
) -> CurrentSnapshot:
    return CurrentSnapshot(
        kind="opportunities",
        key="global",
        version=version,
        content=content,
        content_hash="sha256:" + "c" * 64,
        as_of=AS_OF if as_of is None else as_of,
    )


def relay(content: dict, *, as_of: Optional[datetime] = None, now: datetime = NOW):
    """Build the response with an INJECTED clock (never the system clock)."""
    return build_opportunities_response(snapshot(content, as_of=as_of), now=now)


@pytest.fixture()
def reader() -> FakeSnapshotReader:
    return FakeSnapshotReader()


@pytest.fixture()
def api(
    app: FastAPI, reader: FakeSnapshotReader, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: reader
    # The route owns no clock dependency: the relay's own clock seam is
    # replaced by a FIXED instant so no test depends on the real time.
    monkeypatch.setattr(opportunities_module, "_utc_now", lambda: NOW)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_requires_session(client: TestClient) -> None:
    assert client.get("/api/v1/opportunities").status_code == 401


def test_empty_state_is_honest_200(api: TestClient) -> None:
    body = api.get("/api/v1/opportunities").json()
    assert body == {
        "state": "empty",
        "snapshot_version": None,
        "as_of": None,
        "age_seconds": None,
        "content": None,
        "reason": "no snapshot published",
    }


def test_relay_is_verbatim(api: TestClient, reader: FakeSnapshotReader) -> None:
    content = opportunities_content(
        qualified=[candidate("SYN-TECH-01", "OBSERVE")],
        excluded=[candidate("SYN-TECH-02", "INSUFFICIENT_DATA")],
    )
    reader.snapshots[("opportunities", "global")] = snapshot(content)

    body = api.get("/api/v1/opportunities").json()
    assert body["state"] == "ok"
    assert body["snapshot_version"] == 1
    assert body["content"] == content
    assert body["content"]["profile_ref"]["version"] == "1.0.0"
    assert body["content"]["calendar_ref"]["version"] == 1
    assert body["content"]["exclusion_reasons"]
    assert body["age_seconds"] == int((NOW - AS_OF).total_seconds())


def test_closed_candidate_in_qualified_group_is_refused() -> None:
    content = opportunities_content(
        qualified=[candidate("SYN-TECH-01", "INSUFFICIENT_DATA")],
        excluded=[],
    )
    with pytest.raises(SnapshotContentError):
        relay(content)


def test_qualified_candidate_carrying_a_block_gate_is_refused() -> None:
    # F15 (API mirror): the group is never decided by the status string
    # alone — a published BLOCK gate excludes the candidate whatever its
    # status claims.
    content = opportunities_content(
        qualified=[candidate("SYN-TECH-01", "QUALIFIED", gate_status="BLOCK")],
        excluded=[],
    )
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "BLOCK gate" in str(excinfo.value)


def test_qualified_candidate_missing_a_required_evidence_is_refused() -> None:
    # F16 (API mirror): no positive card while a required evidence is absent.
    content = opportunities_content(
        qualified=[candidate("SYN-TECH-01", "QUALIFIED", evidence_present=False)],
        excluded=[],
    )
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "not admissible" in str(excinfo.value)


def test_qualified_candidate_contradicting_its_evidence_map_is_refused() -> None:
    forged = candidate("SYN-TECH-01", "QUALIFIED", evidence_present=False)
    forged["missing_evidence"] = []  # claims nothing missing, map says sector
    content = opportunities_content(qualified=[forged], excluded=[])
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "contradicts" in str(excinfo.value)


def test_non_canonical_excluded_status_is_refused() -> None:
    content = opportunities_content(
        qualified=[],
        excluded=[
            candidate(
                "SYN-TECH-01",
                "OBSERVE",
                exclusion={
                    "kind": "CLOSED_STATUS",
                    "gate_id": "entitlements_sufficient",
                    "reason_code": "UNEVALUABLE",
                    "missing_evidence": [],
                    "detail": "forged",
                },
            )
        ],
    )
    with pytest.raises(SnapshotContentError):
        relay(content)


def test_excluded_candidate_without_a_published_reason_is_refused() -> None:
    content = opportunities_content(
        qualified=[], excluded=[candidate("SYN-TECH-01", "OBSERVE")]
    )
    with pytest.raises(SnapshotContentError):
        relay(content)


def test_closed_status_attributed_to_missing_evidence_is_refused() -> None:
    content = opportunities_content(
        qualified=[],
        excluded=[
            candidate(
                "SYN-TECH-01",
                "INSUFFICIENT_DATA",
                evidence_present=False,
                exclusion={
                    "kind": "MISSING_REQUIRED_EVIDENCE",
                    "gate_id": None,
                    "reason_code": None,
                    "missing_evidence": ["sector"],
                    "detail": "forged attribution",
                },
            )
        ],
    )
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "blocking gate" in str(excinfo.value)


def test_open_candidate_excluded_for_missing_evidence_relays(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    # The admissibility exclusion is a legitimate published state: an open
    # status may sit in the excluded group ONLY with its evidence reason.
    excluded = candidate(
        "SYN-TECH-01",
        "QUALIFIED",
        evidence_present=False,
        exclusion={
            "kind": "MISSING_REQUIRED_EVIDENCE",
            "gate_id": None,
            "reason_code": None,
            "missing_evidence": ["sector"],
            "detail": "required evidence absent: sector",
        },
    )
    content = opportunities_content(qualified=[], excluded=[excluded])
    reader.snapshots[("opportunities", "global")] = snapshot(content)
    body = api.get("/api/v1/opportunities").json()
    assert body["state"] == "ok"
    assert body["content"]["excluded"][0]["exclusion"]["missing_evidence"] == [
        "sector"
    ]


# ---------------------------------------------------------------------------
# P1-8 — the qualified group is fail-closed on the published facts
# ---------------------------------------------------------------------------


def _qualified_with(**overrides: Any) -> dict:
    """One qualified candidate, then the forged deviation applied on top."""
    forged = candidate("SYN-TECH-01", "QUALIFIED")
    for key, value in overrides.items():
        if key == "horizon":
            forged["advice"]["horizon"] = value
        elif key == "drop_horizon":
            forged["advice"].pop("horizon", None)
        else:
            forged[key] = value
    return forged


_ONE_GATE = [
    {"gate_id": "entitlements_sufficient", "status": "PASS", "reason_code": "OK"}
]

_REFUSED_QUALIFIED = (
    pytest.param(
        {"gates": [{"gate_id": "g", "status": "block", "reason_code": "X"}]},
        "gate status",
        id="gate-BLOCK-lowercased",
    ),
    pytest.param(
        {"gates": [{"gate_id": "g", "status": "CLOSED", "reason_code": "X"}]},
        "gate status",
        id="gate-status-outside-the-canonical-vocabulary",
    ),
    pytest.param(
        {"required_evidence": {}, "missing_evidence": []},
        "required evidence",
        id="required_evidence-empty",
    ),
    pytest.param(
        {
            "required_evidence": {"sector": {"present": True, "detail": "SYN-TECH"}},
            "missing_evidence": [],
        },
        "required evidence",
        id="required_evidence-incomplete-versus-the-profile",
    ),
    pytest.param({"horizon": "1d"}, "horizon", id="horizon-outside-the-profile"),
    pytest.param({"drop_horizon": True}, "horizon", id="horizon-absent"),
    pytest.param({"gates": []}, "gate", id="no-gate-published"),
)


@pytest.mark.parametrize(("override", "expected_reason"), _REFUSED_QUALIFIED)
def test_an_incoherent_qualified_candidate_is_refused(
    override: dict, expected_reason: str
) -> None:
    """P1-8: one row = one refused snapshot, never a displayed card."""
    content = opportunities_content(
        qualified=[_qualified_with(**override)], excluded=[]
    )
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert expected_reason in str(excinfo.value)


def test_a_gate_status_outside_the_vocabulary_is_refused_in_both_groups() -> None:
    """The vocabulary is imposed on the excluded group too (fail-closed)."""
    forged = candidate("SYN-TECH-01", "INSUFFICIENT_DATA")
    forged["gates"] = [{"gate_id": "g", "status": "block", "reason_code": "X"}]
    content = opportunities_content(qualified=[], excluded=[forged])
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "gate status" in str(excinfo.value)


def test_exclusion_gate_id_names_a_published_BLOCK_gate() -> None:
    """An exclusion attributed to a gate that is NOT blocking is refused."""
    forged = candidate("SYN-TECH-01", "BLOCKED")
    forged["gates"] = [
        {"gate_id": "freshness_ok", "status": "PASS", "reason_code": "OK"},
        {"gate_id": "entitlements_sufficient", "status": "BLOCK", "reason_code": "U"},
    ]
    forged["exclusion"] = {
        "kind": "CLOSED_STATUS",
        "gate_id": "freshness_ok",  # a PASS gate, not the blocking one
        "reason_code": "U",
        "missing_evidence": [],
        "detail": "forged attribution",
    }
    content = opportunities_content(qualified=[], excluded=[forged])
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "BLOCK" in str(excinfo.value)


def test_the_exclusion_gate_id_of_the_real_blocking_gate_relays() -> None:
    forged = candidate("SYN-TECH-01", "BLOCKED")
    forged["gates"] = [
        {"gate_id": "freshness_ok", "status": "PASS", "reason_code": "OK"},
        {"gate_id": "entitlements_sufficient", "status": "BLOCK", "reason_code": "U"},
    ]
    content = opportunities_content(qualified=[], excluded=[forged])
    assert relay(content).state == "ok"


def test_an_unknown_referenced_profile_is_refused() -> None:
    content = opportunities_content(qualified=[], excluded=[])
    content["profile_ref"]["id"] = "no_such_profile"
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "profile" in str(excinfo.value)


def test_a_profile_version_the_manifest_does_not_declare_is_refused() -> None:
    content = opportunities_content(qualified=[], excluded=[])
    content["profile_ref"]["version"] = "9.9.9"
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "version" in str(excinfo.value)


def test_the_excluded_group_must_also_publish_the_profile_evidence_set() -> None:
    forged = candidate("SYN-TECH-01", "INSUFFICIENT_DATA")
    forged["required_evidence"] = {"sector": {"present": True, "detail": "SYN-TECH"}}
    forged["missing_evidence"] = []
    content = opportunities_content(qualified=[], excluded=[forged])
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content)
    assert "required evidence" in str(excinfo.value)


# ---------------------------------------------------------------------------
# P1-9 — a worker that stopped publishing is never served as current
# ---------------------------------------------------------------------------


def test_a_snapshot_older_than_its_budget_is_served_as_stale_not_ok() -> None:
    """The worker refused to publish (DEAD message): the page must say so.

    ``financial-safety.md`` forbids silently keeping an old verdict. Beyond
    the documented freshness budget the served state is ``stale`` — with the
    age and the reason — never ``ok``.
    """
    content = opportunities_content(
        qualified=[candidate("SYN-TECH-01", "OBSERVE")], excluded=[]
    )
    stale_as_of = AS_OF
    now = stale_as_of + OPPORTUNITIES_MAX_AGE + timedelta(seconds=1)

    response = relay(content, as_of=stale_as_of, now=now)

    assert response.state == "stale"
    assert response.age_seconds == int((now - stale_as_of).total_seconds())
    assert response.reason is not None
    assert "budget" in response.reason
    # The content is still relayed verbatim: the page shows WHAT is old.
    assert response.content == content
    assert response.snapshot_version == 1


def test_a_snapshot_at_the_budget_boundary_is_still_ok() -> None:
    content = opportunities_content(qualified=[], excluded=[])
    now = AS_OF + OPPORTUNITIES_MAX_AGE

    response = relay(content, now=now)

    assert response.state == "ok"
    assert response.reason is None
    assert response.age_seconds == int(OPPORTUNITIES_MAX_AGE.total_seconds())


def test_a_stale_snapshot_is_served_as_stale_over_http(
    api: TestClient, reader: FakeSnapshotReader
) -> None:
    content = opportunities_content(qualified=[], excluded=[])
    old = NOW - OPPORTUNITIES_MAX_AGE - timedelta(hours=1)
    reader.snapshots[("opportunities", "global")] = snapshot(content, as_of=old)

    body = api.get("/api/v1/opportunities").json()

    assert body["state"] == "stale"
    assert body["age_seconds"] == int((NOW - old).total_seconds())
    assert "budget" in body["reason"]


def test_a_snapshot_dated_in_the_future_is_refused() -> None:
    content = opportunities_content(qualified=[], excluded=[])
    with pytest.raises(SnapshotContentError) as excinfo:
        relay(content, as_of=NOW + timedelta(seconds=1), now=NOW)
    assert "future" in str(excinfo.value)
