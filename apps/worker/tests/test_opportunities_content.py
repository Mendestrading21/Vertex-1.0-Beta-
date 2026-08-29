"""Unit tests of the pure opportunities content builder (SYNTHETIC only).

The candidates' verdicts come from the SAME analysis pipeline (hence THE
single ``AdviceEngine``); these tests verify the honest grouping, the
documented ordering, the profile reference and the evidence-presence checks.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
)
from vertex_worker.calendar import (
    DEV_SYNTHETIC_CALENDAR_CONFIG,
    build_calendar_content,
)
from vertex_worker.analysis import BarRecord
from vertex_worker.opportunities import (
    DEFAULT_PROFILES_PATH,
    DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
    EXCLUDED_STATUSES,
    QUALIFIED_ORDERING_KEYS,
    QUALIFIED_STATUSES,
    StrategyProfileError,
    build_opportunities_content,
    group_for_status,
    load_strategy_profile,
)
from test_calendar_content import record_from_envelope

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 20260825


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


@pytest.fixture(scope="module")
def profile():
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
    bars = [
        bar_record(e)
        for e in generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    ]
    return build_opportunities_content(
        bars,
        [],
        chain_by_instrument={},
        calendar_content=calendar_content,
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


def test_profile_ref_matches_the_committed_manifest(profile, content) -> None:
    manifest = yaml.safe_load(
        Path(DEFAULT_PROFILES_PATH).read_text(encoding="utf-8")
    )
    entry = next(
        p for p in manifest["profiles"] if p["id"] == "equity_etf_swing_3_12m"
    )
    assert content["profile_ref"] == {
        "id": entry["id"],
        "version": entry["version"],
        "source": "manifests/strategy-profiles.yaml",
    }
    assert profile.required_evidence == tuple(entry["required_evidence"])


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(StrategyProfileError):
        load_strategy_profile("does_not_exist")


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
        assert candidate["primary_exclusion_reason"] is None
    for candidate in content["excluded"]:
        assert candidate["advice"]["status"] in EXCLUDED_STATUSES


def test_synthetic_population_is_mostly_excluded_by_design(content) -> None:
    # On the honest synthetic inputs nobody can prove entitlements, session,
    # liquidity, contradictions or constraints: EVERY candidate is excluded
    # INSUFFICIENT_DATA. This is the WANTED outcome, and the distribution of
    # exclusion reasons is published as the page's honest empty state.
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


def test_ordering_is_documented_lexicographic(content) -> None:
    assert content["ordering"]["method"] == "lexicographic"
    assert content["ordering"]["keys"] == list(QUALIFIED_ORDERING_KEYS)
    assert [c["ticker"] for c in content["excluded"]] == sorted(
        c["ticker"] for c in content["excluded"]
    )


def test_required_evidence_checks_are_honest(content) -> None:
    by_ticker = {c["ticker"]: c for c in content["excluded"]}

    with_bars_and_thesis = by_ticker["SYN-TECH-01"]
    checks = with_bars_and_thesis["required_evidence"]
    assert checks["sector"]["present"] is True
    assert checks["price_volume"]["present"] is True  # validated bars exist
    assert checks["catalysts"]["present"] is True  # published calendar events
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


def test_universe_covers_the_24_declared_tickers(content) -> None:
    tickers = {c["ticker"] for c in content["excluded"]} | {
        c["ticker"] for c in content["qualified"]
    }
    assert len(tickers) == 24
    assert set(SYNTHETIC_FOCUS_TICKERS) <= tickers


def test_determinism(profile, calendar_content) -> None:
    bars = [
        bar_record(e)
        for e in generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
    ]
    kwargs = dict(
        chain_by_instrument={},
        calendar_content=calendar_content,
        theses_by_ticker={},
        now=NOW,
        config=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        profile=profile,
    )
    assert build_opportunities_content(bars, [], **kwargs) == (
        build_opportunities_content(list(bars), [], **kwargs)
    )


def test_empty_inputs_are_an_empty_population(profile) -> None:
    content = build_opportunities_content(
        [],
        [],
        chain_by_instrument={},
        calendar_content=None,
        theses_by_ticker={},
        now=NOW,
        config=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        profile=profile,
    )
    assert content["population"] == "EMPTY"
    assert content["qualified"] == []
    assert len(content["excluded"]) == 24
