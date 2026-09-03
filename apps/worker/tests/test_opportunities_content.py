"""Unit tests of the pure opportunities content builder (SYNTHETIC only).

The candidates' verdicts come from the SAME analysis pipeline (hence THE
single ``AdviceEngine``); these tests verify the honest grouping, the
ADMISSIBILITY invariant (status x published gates x required evidence), the
documented ordering, the profile reference, the calendar provenance and the
evidence-presence checks.

Every fixture here is SYNTHETIC and deterministic. Two doubles of the single
engine are used and clearly labelled: a CANONICAL one (real ``AdviceResult``
objects) to exercise a non-empty qualified group, and a FORGED one (a raw
mapping that violates the ``AdviceResult`` contract) to prove the builder
refuses to publish a false card.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_calendar_content import record_from_envelope

from vertex_core.contracts.decision import AdviceResult, GateResult
from vertex_core.contracts.enums import AdviceStatus, Direction, GateStatus
from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
)
from vertex_worker.analysis import AnalysisConfig, BarRecord
from vertex_worker.calendar import (
    DEV_SYNTHETIC_CALENDAR_CONFIG,
    build_calendar_content,
)
from vertex_worker.handlers import ObservationRecord
from vertex_worker.opportunities import (
    CALENDAR_REF_ABSENT,
    CALENDAR_REF_FUTURE,
    CALENDAR_REF_STALE,
    CALENDAR_REF_USED,
    DEFAULT_PROFILES_PATH,
    DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
    EXCLUDED_STATUSES,
    EXCLUSION_KIND_CLOSED_STATUS,
    EXCLUSION_KIND_MISSING_EVIDENCE,
    QUALIFIED_ORDERING_KEYS,
    QUALIFIED_STATUSES,
    TOPIC_OPPORTUNITIES_REFRESH,
    CalendarSnapshotRef,
    StrategyProfile,
    StrategyProfileError,
    build_opportunities_content,
    group_for_status,
    load_strategy_profile,
    register_opportunities_handler,
)
from vertex_worker.registry import HandlerRegistry

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 20260825

CALENDAR_REF = CalendarSnapshotRef(
    kind="calendar", key="global", version=1, as_of=NOW
)


def bar_record(envelope) -> BarRecord:
    return BarRecord(
        event_id=envelope.event_id,
        source=envelope.source,
        instrument_ref=envelope.instrument_id,
        as_of=envelope.as_of,
        quality_status=envelope.quality_status.value,
        rights=envelope.rights,
        schema_version=envelope.schema_version,
        payload=dict(envelope.payload),
    )


def synthetic_bars() -> list[BarRecord]:
    return [
        bar_record(e)
        for e in generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    ]


# --------------------------------------------------------------------------
# SYNTHETIC doubles of the single AdviceEngine (never a second engine: they
# only let the tests exercise verdicts the honest synthetic data cannot
# produce, and the forged one proves the builder distrusts its input).
# --------------------------------------------------------------------------


class CanonicalEngineDouble:
    """Returns real ``AdviceResult`` objects with chosen OPEN statuses."""

    def __init__(
        self,
        *,
        statuses: Mapping[str, str],
        default_status: str = "OBSERVE",
        degraded: Mapping[str, int] | None = None,
    ) -> None:
        self._statuses = dict(statuses)
        self._default = default_status
        self._degraded = dict(degraded or {})

    def evaluate(self, inputs) -> AdviceResult:
        ticker = inputs.instrument_id
        degraded = self._degraded.get(ticker, 0)
        gates = [
            GateResult(
                gate_id=f"synthetic_double_gate_{index}",
                version="1.0.0",
                status=GateStatus.DEGRADE if index < degraded else GateStatus.PASS,
                reason_code="SYNTHETIC_DOUBLE",
                message="SYNTHETIC double of the single engine",
            )
            for index in range(3)
        ]
        return AdviceResult(
            advice_id="sha256:" + "a" * 64,
            instrument_id=ticker,
            as_of=inputs.as_of,
            valid_until=inputs.valid_until,
            input_snapshot_id=inputs.input_snapshot_id,
            engine_version="vertex_core@synthetic-double",
            status=AdviceStatus(self._statuses.get(ticker, self._default)),
            direction=Direction.UNKNOWN,
            horizon=inputs.horizon,
            gates=tuple(gates),
            risk_summary="SYNTHETIC double: no real risk assessment",
        )


class _ForgedAdvice:
    """Raw mapping that VIOLATES the AdviceResult contract on purpose."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return dict(self._payload)


class ForgedEngineDouble:
    """Publishes an arbitrary (status, gates) pair — the adversarial case."""

    def __init__(self, *, status: str, gate_statuses: tuple[str, ...]) -> None:
        self._status = status
        self._gate_statuses = gate_statuses

    def evaluate(self, inputs) -> _ForgedAdvice:
        return _ForgedAdvice(
            {
                "advice_id": "sha256:" + "f" * 64,
                "instrument_id": inputs.instrument_id,
                "status": self._status,
                "direction": "UNKNOWN",
                "horizon": inputs.horizon,
                "as_of": inputs.as_of.isoformat(),
                "valid_until": inputs.valid_until.isoformat(),
                "engine_version": "forged",
                "gates": [
                    {
                        "gate_id": gate_id,
                        "status": gate_status,
                        "reason_code": "UNEVALUABLE",
                    }
                    for gate_id, gate_status in zip(
                        (
                            "entitlements_sufficient",
                            "session_and_event_known",
                            "minimum_liquidity",
                            "calculations_valid",
                            "critical_contradictions_resolved",
                            "user_constraints_versioned",
                        ),
                        self._gate_statuses, strict=False,
                    )
                ],
                "evidence_ids": [],
                "scenario_ids": [],
            }
        )


@pytest.fixture(scope="module")
def profile() -> StrategyProfile:
    return load_strategy_profile()


@pytest.fixture(scope="module")
def calendar_content():
    envelopes = generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    return build_calendar_content(
        [record_from_envelope(e) for e in envelopes],
        now=NOW,
        config=DEV_SYNTHETIC_CALENDAR_CONFIG,
        positions_by_ticker={},
        theses_by_ticker={},
    )


@pytest.fixture(scope="module")
def content(profile, calendar_content):
    return build_opportunities_content(
        synthetic_bars(),
        [],
        chain_by_instrument={},
        calendar_content=calendar_content,
        calendar_ref=CALENDAR_REF,
        theses_by_ticker={
            "SYN-TECH-01": [
                {
                    "thesis_id": 1,
                    "title": "synthetic thesis",
                    "status": "ACTIVE",
                    "invalidation": "synthetic falsifier",
                }
            ]
        },
        now=NOW,
        config=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        profile=profile,
    )


def build(**overrides):
    """Build one snapshot on empty market inputs unless overridden."""
    kwargs: dict[str, Any] = {
        "chain_by_instrument": {},
        "calendar_content": None,
        "calendar_ref": None,
        "theses_by_ticker": {},
        "now": NOW,
        "config": DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
    }
    bars = overrides.pop("bars", [])
    kwargs.update(overrides)
    return build_opportunities_content(bars, [], **kwargs)


# --------------------------------------------------------------------------
# Profile reference and manifest (F20, F21)
# --------------------------------------------------------------------------


def test_profile_ref_matches_the_committed_manifest(profile, content) -> None:
    manifest = yaml.safe_load(
        Path(DEFAULT_PROFILES_PATH).read_text(encoding="utf-8")
    )
    entry = next(
        p for p in manifest["profiles"] if p["id"] == "equity_etf_swing_3_12m"
    )
    profile_ref = content["profile_ref"]
    assert profile_ref["id"] == entry["id"]
    assert profile_ref["version"] == entry["version"]
    assert profile_ref["source"] == "manifests/strategy-profiles.yaml"
    assert profile.required_evidence == tuple(entry["required_evidence"])
    assert profile.decision_horizons_months == tuple(
        entry["decision_horizons_months"]
    )
    # The reference NEVER claims a fully applied profile: what the snapshot
    # does not honor is published field by field.
    not_applied = {item["field"] for item in profile_ref["not_applied"]}
    assert {"instruments", "review_cadence", "common_gates"} <= not_applied
    assert all(item["reason"] for item in profile_ref["not_applied"])
    assert profile_ref["applied"]


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(StrategyProfileError):
        load_strategy_profile("does_not_exist")


def test_published_horizon_matches_the_referenced_profile(
    profile, content
) -> None:
    # F20: the published advice horizon belongs to the referenced profile.
    assert profile.horizons == ("3m", "6m", "12m")
    horizons = {
        candidate["advice"]["horizon"]
        for candidate in (*content["qualified"], *content["excluded"])
    }
    assert horizons == {"3m"}
    assert horizons <= set(profile.horizons)
    # A horizon foreign to the profile is refused, never published while
    # claiming the profile.
    foreign = replace(DEV_SYNTHETIC_OPPORTUNITIES_CONFIG, horizon="1d")
    with pytest.raises(StrategyProfileError) as excinfo:
        build(config=foreign, profile=profile)
    assert "1d" in str(excinfo.value)


def test_gate_not_required_is_not_claimed_when_the_profile_requires_portfolio_fit(
    profile, content
) -> None:
    # F20: gate 7 is OBSERVED (fail-closed on the absent user declaration),
    # never satisfied by declaration while the profile requires the evidence.
    assert "manual_portfolio_fit" in profile.required_evidence
    for candidate in content["excluded"]:
        gate = next(
            g
            for g in candidate["gates"]
            if g["gate_id"] == "manual_portfolio_risk_available"
        )
        assert gate["status"] == "BLOCK"
        assert gate["reason_code"] == "UNEVALUABLE"
        assert candidate["required_evidence"]["manual_portfolio_fit"][
            "present"
        ] is False
    declared = replace(
        DEV_SYNTHETIC_OPPORTUNITIES_CONFIG, portfolio_risk_required=False
    )
    with pytest.raises(StrategyProfileError) as excinfo:
        build(config=declared, profile=profile)
    assert "manual_portfolio_fit" in str(excinfo.value)


def test_profile_path_is_injected_not_derived_from_file_layout(
    tmp_path, monkeypatch
) -> None:
    # F21: nothing requires the source-checkout layout; the manifest path is
    # injected at both entry points.
    manifest = tmp_path / "profiles.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "profiles": [
                    {
                        "id": "equity_etf_swing_3_12m",
                        "version": "9.9.9-injected",
                        "instruments": ["STOCK"],
                        "decision_horizons_months": [3],
                        "required_evidence": ["sector"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "vertex_worker.opportunities.DEFAULT_PROFILES_PATH",
        tmp_path / "no-checkout-here" / "strategy-profiles.yaml",
    )
    injected = load_strategy_profile(path=manifest)
    assert injected.version == "9.9.9-injected"

    registry = HandlerRegistry()
    register_opportunities_handler(
        registry,
        clock=lambda: NOW,
        config=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        profiles_path=manifest,
    )
    handler = registry.get(TOPIC_OPPORTUNITIES_REFRESH)
    assert handler is not None
    assert handler.profile.version == "9.9.9-injected"

    # Without injection the documented fallback is used, and its absence
    # fails closed with the injection hint (never a silent default profile).
    with pytest.raises(StrategyProfileError) as excinfo:
        load_strategy_profile()
    assert "profiles_path" in str(excinfo.value)

    with pytest.raises(ValueError):
        register_opportunities_handler(
            HandlerRegistry(),
            clock=lambda: NOW,
            config=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
            profile=injected,
            profiles_path=manifest,
        )


# --------------------------------------------------------------------------
# Grouping and admissibility (F15, F16)
# --------------------------------------------------------------------------


def test_group_for_status_covers_the_five_canonical_statuses() -> None:
    for status in QUALIFIED_STATUSES:
        assert group_for_status(status) == "QUALIFIED_GROUP"
    for status in EXCLUDED_STATUSES:
        assert group_for_status(status) == "EXCLUDED_GROUP"
    with pytest.raises(ValueError):
        group_for_status("APPROVED")


def test_no_closed_candidate_in_the_qualified_group(content) -> None:
    for candidate in content["qualified"]:
        assert candidate["advice"]["status"] in QUALIFIED_STATUSES
        assert candidate["exclusion"] is None
        assert candidate["primary_exclusion_reason"] is None
    for candidate in content["excluded"]:
        assert candidate["advice"]["status"] in EXCLUDED_STATUSES


def test_candidate_with_a_block_gate_can_never_enter_the_qualified_group(
    profile,
) -> None:
    # F15: an OPEN status carrying BLOCK gates contradicts the AdviceResult
    # contract; the snapshot is refused, never published with a false card.
    forged = ForgedEngineDouble(
        status="QUALIFIED", gate_statuses=("BLOCK",) * 6
    )
    with pytest.raises(RuntimeError) as excinfo:
        build(profile=profile, engine=forged)
    message = str(excinfo.value)
    assert "qualified group" in message
    assert "entitlements_sufficient" in message


def test_closed_candidate_without_a_blocking_gate_is_refused(profile) -> None:
    # Mirror invariant: an exclusion is never unattributed.
    forged = ForgedEngineDouble(
        status="INSUFFICIENT_DATA", gate_statuses=("PASS",) * 6
    )
    with pytest.raises(RuntimeError) as excinfo:
        build(profile=profile, engine=forged)
    assert "without any blocking gate" in str(excinfo.value)


def test_missing_required_evidence_cannot_coexist_with_an_open_status() -> None:
    # F16: a required evidence nobody holds makes the candidate INADMISSIBLE
    # (published reason), it never merely lowers its rank.
    demanding = StrategyProfile(
        profile_id="synthetic_test_profile",
        version="1.0.0-test",
        instruments=("STOCK",),
        required_evidence=("sector", "fundamentals"),
        source_path="tests/synthetic",
        decision_horizons_months=(3,),
    )
    content = build(
        profile=demanding,
        engine=CanonicalEngineDouble(statuses={}, default_status="QUALIFIED"),
    )
    assert content["qualified"] == []
    assert len(content["excluded"]) == 24
    for candidate in content["excluded"]:
        assert candidate["advice"]["status"] == "QUALIFIED"
        assert candidate["missing_evidence"] == ["fundamentals"]
        exclusion = candidate["exclusion"]
        assert exclusion["kind"] == EXCLUSION_KIND_MISSING_EVIDENCE
        assert exclusion["missing_evidence"] == ["fundamentals"]
        assert "fundamentals" in exclusion["detail"]
    assert content["exclusion_reasons"] == {"required_evidence:fundamentals": 24}


def test_qualified_group_is_ordered_by_the_documented_keys(
    calendar_content,
) -> None:
    # T5: the promise of the page — a NON EMPTY qualified group, ranked by
    # the documented lexicographic keys (status rank, degraded gates, ticker).
    admissible = StrategyProfile(
        profile_id="synthetic_test_profile",
        version="1.0.0-test",
        instruments=("STOCK",),
        required_evidence=("sector",),
        source_path="tests/synthetic",
        decision_horizons_months=(3,),
    )
    engine = CanonicalEngineDouble(
        statuses={
            "SYN-TECH-01": "QUALIFIED",
            "SYN-TECH-02": "QUALIFIED",
            "SYN-FINL-01": "REVIEW",
        },
        default_status="OBSERVE",
        degraded={"SYN-TECH-01": 2},
    )
    content = build(
        bars=synthetic_bars(),
        calendar_content=calendar_content,
        calendar_ref=CALENDAR_REF,
        profile=admissible,
        engine=engine,
    )
    assert content["excluded"] == []
    qualified = content["qualified"]
    assert len(qualified) == 24
    assert [c["rank"] for c in qualified] == list(range(1, 25))
    # QUALIFIED before REVIEW before OBSERVE; inside QUALIFIED the candidate
    # with fewer degraded gates first; ties broken by ticker.
    assert [c["ticker"] for c in qualified[:3]] == [
        "SYN-TECH-02",
        "SYN-TECH-01",
        "SYN-FINL-01",
    ]
    assert qualified[0]["degraded_gates"] == []
    assert len(qualified[1]["degraded_gates"]) == 2
    assert [c["advice"]["status"] for c in qualified[:3]] == [
        "QUALIFIED",
        "QUALIFIED",
        "REVIEW",
    ]
    assert [c["advice"]["status"] for c in qualified[3:]] == ["OBSERVE"] * 21
    observing = [c["ticker"] for c in qualified[3:]]
    assert observing == sorted(observing)
    assert content["coverage"]["qualified_count"] == 24
    assert content["ordering"]["keys"] == list(QUALIFIED_ORDERING_KEYS)


def test_synthetic_population_is_fully_excluded_by_design(content) -> None:
    # On the honest synthetic inputs nobody can prove entitlements, session,
    # liquidity, contradictions, constraints or the portfolio fit: EVERY
    # candidate is excluded INSUFFICIENT_DATA. This is the WANTED outcome,
    # and the distribution of exclusion reasons is published as the page's
    # honest empty state.
    assert content["population"] == "SYNTHETIC"
    assert content["qualified"] == []
    assert len(content["excluded"]) == 24
    assert content["coverage"]["status_counts"] == {"INSUFFICIENT_DATA": 24}
    assert content["exclusion_reasons"]
    assert sum(content["exclusion_reasons"].values()) == 24


def test_primary_reason_is_the_first_closed_gate(content) -> None:
    for candidate in content["excluded"]:
        first_block = next(
            gate for gate in candidate["gates"] if gate["status"] == "BLOCK"
        )
        assert candidate["primary_exclusion_reason"] == {
            "gate_id": first_block["gate_id"],
            "reason_code": first_block["reason_code"],
        }
        assert candidate["exclusion"]["kind"] == EXCLUSION_KIND_CLOSED_STATUS
        assert candidate["exclusion"]["gate_id"] == first_block["gate_id"]


def test_ordering_is_documented_lexicographic(content) -> None:
    assert content["ordering"]["method"] == "lexicographic"
    assert content["ordering"]["keys"] == list(QUALIFIED_ORDERING_KEYS)
    assert [c["ticker"] for c in content["excluded"]] == sorted(
        c["ticker"] for c in content["excluded"]
    )


# --------------------------------------------------------------------------
# Evidence honesty (F17, F18)
# --------------------------------------------------------------------------


def test_required_evidence_checks_are_honest(content) -> None:
    by_ticker = {c["ticker"]: c for c in content["excluded"]}

    with_bars_and_thesis = by_ticker["SYN-TECH-01"]
    checks = with_bars_and_thesis["required_evidence"]
    assert checks["sector"]["present"] is True
    assert checks["price_volume"]["present"] is True  # validated bars exist
    assert checks["catalysts"]["present"] is True  # upcoming calendar events
    assert checks["thesis"]["present"] is True
    assert checks["invalidation"]["present"] is True
    # Nobody holds these facts: honestly absent, never fabricated.
    assert checks["regime"]["present"] is False
    assert checks["fundamentals"]["present"] is False
    assert checks["manual_portfolio_fit"]["present"] is False

    no_bars_no_thesis = by_ticker["SYN-UTIL-04"]
    checks = no_bars_no_thesis["required_evidence"]
    assert checks["price_volume"]["present"] is False
    assert checks["thesis"]["present"] is False
    assert checks["catalysts"]["present"] is False
    assert no_bars_no_thesis["missing_evidence"] == sorted(
        name for name, check in checks.items() if not check["present"]
    )


def past_calendar(as_of: str) -> dict[str, Any]:
    """SYNTHETIC calendar snapshot carrying ONE already-passed event."""
    return {
        "schema_version": "vertex.calendar/1.0",
        "as_of": as_of,
        "agenda": [
            {
                "event_id": "syn-ev-past",
                "ticker": "SYN-TECH-01",
                "category": "EARNINGS",
                "event_time_utc": "2019-03-01T13:30:00+00:00",
            }
        ],
    }


def test_past_calendar_events_are_not_counted_as_catalysts(profile) -> None:
    # F17: an event of 2019 is not an upcoming catalyst in 2026, and the
    # consumed calendar snapshot publishes its provenance.
    stale_as_of = datetime(2020, 1, 1, tzinfo=UTC)
    content = build(
        profile=profile,
        calendar_content=past_calendar(stale_as_of.isoformat()),
        calendar_ref=CalendarSnapshotRef(
            kind="calendar", key="global", version=7, as_of=stale_as_of
        ),
    )
    by_ticker = {c["ticker"]: c for c in content["excluded"]}
    catalysts = by_ticker["SYN-TECH-01"]["required_evidence"]["catalysts"]
    assert catalysts["present"] is False
    ref = content["calendar_ref"]
    assert ref["kind"] == "calendar"
    assert ref["key"] == "global"
    assert ref["version"] == 7
    assert ref["snapshot_as_of"] == stale_as_of.isoformat()
    assert ref["content_as_of"] == stale_as_of.isoformat()
    # A snapshot older than the bounded window proves no catalyst at all.
    assert ref["status"] == CALENDAR_REF_STALE
    assert ref["events_upcoming"] == 0

    # Fresh snapshot, past event: counted as ignored, never as a catalyst.
    fresh = build(
        profile=profile,
        calendar_content=past_calendar(NOW.isoformat()),
        calendar_ref=CalendarSnapshotRef(
            kind="calendar", key="global", version=8, as_of=NOW
        ),
    )
    fresh_by_ticker = {c["ticker"]: c for c in fresh["excluded"]}
    assert (
        fresh_by_ticker["SYN-TECH-01"]["required_evidence"]["catalysts"][
            "present"
        ]
        is False
    )
    assert fresh["calendar_ref"]["status"] == CALENDAR_REF_USED
    assert fresh["calendar_ref"]["events_ignored_past"] == 1
    assert fresh["calendar_ref"]["events_upcoming"] == 0


def test_calendar_provenance_is_mandatory_and_fail_closed(
    profile, calendar_content, content
) -> None:
    # A calendar snapshot without provenance is refused (no untraceable
    # evidence), an absent calendar is published as ABSENT, and a snapshot
    # dated in the future proves nothing.
    assert content["calendar_ref"]["status"] == CALENDAR_REF_USED
    assert content["calendar_ref"]["events_upcoming"] == 14
    # The 3 macro events carry no ticker: no instrument catalyst, no defect.
    assert content["calendar_ref"]["events_without_ticker"] == 3
    assert content["calendar_ref"]["events_rejected"] == 0
    with pytest.raises(ValueError):
        build(profile=profile, calendar_content=calendar_content)
    absent = build(profile=profile)
    assert absent["calendar_ref"]["status"] == CALENDAR_REF_ABSENT
    assert absent["calendar_ref"]["version"] is None
    future = build(
        profile=profile,
        calendar_content=calendar_content,
        calendar_ref=CalendarSnapshotRef(
            kind="calendar",
            key="global",
            version=2,
            as_of=NOW + timedelta(minutes=1),
        ),
    )
    assert future["calendar_ref"]["status"] == CALENDAR_REF_FUTURE
    future_by_ticker = {c["ticker"]: c for c in future["excluded"]}
    assert (
        future_by_ticker["SYN-TECH-01"]["required_evidence"]["catalysts"][
            "present"
        ]
        is False
    )


def test_archived_thesis_is_not_admissible_evidence(profile) -> None:
    # F18: a parked (ARCHIVED) thesis proves neither thesis nor invalidation.
    archived = {
        "thesis_id": 1,
        "title": "synthetic archived thesis",
        "status": "ARCHIVED",
        "invalidation": "synthetic falsifier",
    }
    content = build(
        profile=profile, theses_by_ticker={"SYN-TECH-01": [archived]}
    )
    checks = {c["ticker"]: c for c in content["excluded"]}["SYN-TECH-01"][
        "required_evidence"
    ]
    assert checks["thesis"]["present"] is False
    assert checks["invalidation"]["present"] is False
    assert "parked" in checks["thesis"]["detail"]

    live = build(
        profile=profile,
        theses_by_ticker={"SYN-TECH-01": [{**archived, "status": "ACTIVE"}]},
    )
    live_checks = {c["ticker"]: c for c in live["excluded"]}["SYN-TECH-01"][
        "required_evidence"
    ]
    assert live_checks["thesis"]["present"] is True
    assert live_checks["invalidation"]["present"] is True


# --------------------------------------------------------------------------
# Population and limitations (F19)
# --------------------------------------------------------------------------


def foreign_bar(*, source: str, rights: str) -> BarRecord:
    """SYNTHETIC fixture whose source/rights are NOT the synthetic dev ones."""
    return BarRecord(
        event_id="evt-fixture-foreign",
        source=source,
        instrument_ref="SYN-TECH-01",
        as_of=NOW - timedelta(hours=1),
        quality_status="VALID",
        rights=rights,
        schema_version="synthetic-daily-bars/1.0",
        payload={
            "ticker": "SYN-TECH-01",
            "currency": "USD",
            "adjustment_basis": "RAW",
            "bars": [
                {
                    "trading_day": "2026-08-24",
                    "open": "10.00",
                    "high": "11.00",
                    "low": "9.50",
                    "close": "10.50",
                    "volume": 1000,
                }
            ],
        },
    )


def test_limitations_are_derived_from_the_computed_population(profile) -> None:
    # F19: limitations follow the population REALLY computed — no snapshot
    # claims a synthetic limitation on a non-synthetic population, and no
    # population is REAL while nothing real was retained.
    synthetic = build(bars=synthetic_bars(), profile=profile)
    assert synthetic["population"] == "SYNTHETIC"
    assert "SYNTHETIC development population" in synthetic["limitations"]

    # Records rejected (foreign source/rights) retain NOTHING: the population
    # is EMPTY, never REAL, and never labelled SYNTHETIC either.
    rejected = build(
        bars=[foreign_bar(source="foreign-feed", rights="FOREIGN")],
        profile=profile,
    )
    assert rejected["population"] == "EMPTY"
    assert not any(
        "SYNTHETIC" in limitation for limitation in rejected["limitations"]
    )
    assert any("EMPTY" in limitation for limitation in rejected["limitations"])
    assert rejected["coverage"]["observations_considered"] == 1

    # A retained non-synthetic record gives a REAL population, and then no
    # synthetic limitation may be claimed.
    real_config = replace(
        DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        allowed_sources=frozenset({"fixture-external-feed"}),
        usable_rights=frozenset({"FIXTURE_DELAYED"}),
    )
    real = build(
        bars=[
            foreign_bar(
                source="fixture-external-feed", rights="FIXTURE_DELAYED"
            )
        ],
        config=real_config,
        profile=profile,
    )
    assert real["population"] == "REAL"
    assert not any(
        "SYNTHETIC" in limitation for limitation in real["limitations"]
    )
    assert real["coverage"]["population_counts"]["REAL"] == 1


def test_universe_covers_the_24_declared_tickers(content) -> None:
    tickers = {c["ticker"] for c in content["excluded"]} | {
        c["ticker"] for c in content["qualified"]
    }
    assert len(tickers) == 24
    assert set(SYNTHETIC_FOCUS_TICKERS) <= tickers


def test_determinism_under_a_reversed_input_order(
    profile, calendar_content
) -> None:
    bars = synthetic_bars()
    kwargs = {
        "chain_by_instrument": {},
        "calendar_content": calendar_content,
        "calendar_ref": CALENDAR_REF,
        "theses_by_ticker": {},
        "now": NOW,
        "config": DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        "profile": profile,
    }
    reversed_bars = list(reversed(bars))
    assert [r.event_id for r in reversed_bars] != [r.event_id for r in bars]
    assert build_opportunities_content(bars, [], **kwargs) == (
        build_opportunities_content(reversed_bars, [], **kwargs)
    )


def test_empty_inputs_are_an_empty_population(profile) -> None:
    content = build(profile=profile)
    assert content["population"] == "EMPTY"
    assert content["qualified"] == []
    assert len(content["excluded"]) == 24


def test_analysis_config_rejects_a_non_boolean_portfolio_requirement() -> None:
    with pytest.raises(ValueError):
        AnalysisConfig(
            instruments=("SYN-TECH-01",),
            allowed_sources=frozenset({"synthetic-dev"}),
            usable_rights=frozenset({"SYNTHETIC"}),
            portfolio_risk_required="yes",  # type: ignore[arg-type]
        )


def test_a_profile_declaring_no_required_evidence_is_refused(
    tmp_path: Path,
) -> None:
    """An empty ``required_evidence`` list disables admissibility silently.

    ``all(...)`` is true over an empty sequence, so before this guard a profile
    declaring no required evidence was accepted and every candidate passed the
    third admissibility fact by vacuity. A profile that requires nothing is a
    contract error, not a permissive configuration.
    """
    manifest = tmp_path / "strategy-profiles.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "profiles": [
                    {
                        "id": "empty_evidence_profile",
                        "version": "1.0.0",
                        "instruments": ["STOCK"],
                        "required_evidence": [],
                        "decision_horizons_months": [3],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyProfileError, match="invalid required_evidence"):
        load_strategy_profile("empty_evidence_profile", path=manifest)


# --------------------------------------------------------------------------
# Evidence framed per instrument (S0)
# --------------------------------------------------------------------------


def news_record(ticker: str, number: int) -> ObservationRecord:
    """SYNTHETIC news mentioning ``ticker`` only."""
    instant = NOW - timedelta(hours=1, minutes=number)
    return ObservationRecord(
        event_id=f"syn:news:{ticker}:{number}",
        source=SYNTHETIC_SOURCE,
        source_event_id=f"native-{ticker}-{number}",
        instrument_ref=ticker,
        published_at=instant,
        received_at=instant,
        as_of=instant,
        quality_status="VALID",
        rights=SYNTHETIC_RIGHTS,
        schema_version="synthetic-news/1.0",
        payload={
            "title": f"[SYNTHETIC] fictional note {number} on {ticker}",
            "entities": [ticker],
        },
    )


def _candidate(content: Mapping[str, Any], ticker: str) -> Mapping[str, Any]:
    for group in ("qualified", "excluded"):
        for entry in content[group]:
            if entry["ticker"] == ticker:
                return dict(entry)
    raise AssertionError(f"{ticker} absent from both groups")


def test_evidence_window_per_instrument_reaches_only_its_candidate(profile) -> None:
    """Preuves cadrées PAR INSTRUMENT (S0) : la table ``ticker -> fenêtre``.

    Le candidat A voit ses grappes ; B, absent de la table, n'en a aucune —
    jamais celles d'un autre. La fenêtre globale (liste) donne la même
    réponse par filtrage : les deux formes publient les MÊMES grappes.
    """
    a, b = SYNTHETIC_FOCUS_TICKERS[:2]
    evidence_a = [news_record(a, 1), news_record(a, 2)]
    kwargs: dict[str, Any] = {
        "chain_by_instrument": {},
        "calendar_content": None,
        "calendar_ref": None,
        "theses_by_ticker": {},
        "now": NOW,
        "config": DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        "profile": profile,
    }
    framed = build_opportunities_content([], {a: evidence_a}, **kwargs)
    shared = build_opportunities_content([], evidence_a, **kwargs)

    clusters_a = _candidate(framed, a)["evidence_cluster_ids"]
    assert clusters_a, "the framed window must reach its own candidate"
    assert _candidate(framed, b)["evidence_cluster_ids"] == []
    assert _candidate(shared, a)["evidence_cluster_ids"] == clusters_a
    assert _candidate(shared, b)["evidence_cluster_ids"] == []
