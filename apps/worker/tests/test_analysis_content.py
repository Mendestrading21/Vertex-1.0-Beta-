"""Unit tests of the pure analysis dossier builder (SYNTHETIC only).

The verdict assertions verify HONESTY, not success: with the synthetic
population the entitlement/session/liquidity/contradiction/constraint facts
do not exist, so the single AdviceEngine must return INSUFFICIENT_DATA with
every blocking gate at UNEVALUABLE — the builder never forces a status.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_worker.analysis import (
    ANALYSIS_SCHEMA_VERSION,
    DEV_SYNTHETIC_ANALYSIS_CONFIG,
    REASON_INVALID_BAR,
    REASON_NO_HEALTHY_CONTRACT,
    REASON_NO_OPTION_CHAIN,
    REASON_SOURCE_NOT_ALLOWED,
    TOPIC_ANALYSIS_INGESTED,
    AnalysisConfig,
    BarRecord,
    build_analysis_content,
    is_daily_bars_schema,
)
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, ObservationRecord, build_registry

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
INSTRUMENT = "SYN-TECH-01"

CONFIG = AnalysisConfig(
    instruments=("SYN-TECH-01", "SYN-TECH-02"),
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)


def bar(day: str, o: str, h: str, low: str, c: str, volume: int = 1000) -> dict:
    return {"trading_day": day, "open": o, "high": h, "low": low, "close": c, "volume": volume}


def good_bars() -> list[dict]:
    return [
        bar("2026-08-21", "100.00", "103.00", "99.00", "102.00"),
        bar("2026-08-22", "102.00", "102.50", "97.50", "98.00"),
        bar("2026-08-24", "98.00", "105.00", "98.00", "104.50"),
    ]


def bars_record(
    *,
    ticker: str = INSTRUMENT,
    bars: list[dict] | None = None,
    event_id: str = "synthetic-dev:t:db0001",
    source: str = SYNTHETIC_SOURCE,
    rights: str = SYNTHETIC_RIGHTS,
    as_of: datetime | None = None,
    quality: str = "VALID",
) -> BarRecord:
    return BarRecord(
        event_id=event_id,
        source=source,
        instrument_ref=ticker,
        as_of=as_of or NOW - timedelta(hours=2),
        quality_status=quality,
        rights=rights,
        schema_version="synthetic-daily-bars/1.0",
        payload={
            "type": "daily_bars",
            "synthetic": True,
            "ticker": ticker,
            "sector": "SYN-TECH",
            "currency": "SYN",
            "adjustment_basis": "synthetic-unadjusted",
            "bars": bars if bars is not None else good_bars(),
        },
    )


def news_record(
    event_id: str,
    title: str,
    *,
    ticker: str = INSTRUMENT,
    native_id: str | None = None,
) -> ObservationRecord:
    return ObservationRecord(
        event_id=event_id,
        source=SYNTHETIC_SOURCE,
        source_event_id=native_id or f"native-{event_id}",
        instrument_ref=ticker,
        published_at=NOW - timedelta(hours=3),
        received_at=NOW - timedelta(hours=3),
        as_of=NOW - timedelta(hours=3),
        quality_status="VALID",
        rights=SYNTHETIC_RIGHTS,
        schema_version="synthetic-news/1.0",
        payload={
            "type": "news",
            "synthetic": True,
            "title": title,
            "canonical_url": f"https://synthetic.invalid/{event_id}",
            "entities": [ticker],
        },
    )


def healthy_chain_content() -> dict:
    return {
        "schema_version": "vertex.option-chain/1.0",
        "underlying": INSTRUMENT,
        "spot": {"value": "100.00", "currency": "SYN"},
        "assumptions": {"rate": "0.02", "dividend_yield": "0.00"},
        "expirations": [
            {
                "expiration": "2026-09-22",
                "trading_class": INSTRUMENT,
                "maturity_years": "0.076712",
                "contracts": [
                    {
                        "con_id": 900000001,
                        "strike": "100.00",
                        "right": "CALL",
                        "expiration": "2026-09-22",
                        "trading_class": INSTRUMENT,
                        "multiplier": 100,
                        "currency": "SYN",
                        "quote": {"bid": "3.50", "ask": "3.70", "status": "OK"},
                        "iv": {"status": "OK", "value": "0.25"},
                    }
                ],
            }
        ],
    }


def build(
    records=None,
    *,
    evidence=(),
    chain=None,
    chain_version=None,
    config=CONFIG,
) -> dict:
    return build_analysis_content(
        records if records is not None else [bars_record()],
        instrument=INSTRUMENT,
        evidence_records=evidence,
        option_chain_content=chain,
        option_chain_version=chain_version,
        now=NOW,
        config=config,
    )


def test_schema_predicate_and_registry_topic() -> None:
    assert is_daily_bars_schema("synthetic-daily-bars/1.0") is True
    assert is_daily_bars_schema("synthetic-daily-quote/1.0") is False
    registry = build_registry(clock=lambda: NOW, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_ANALYSIS_INGESTED in registry.topics


def test_bars_are_relayed_verbatim_with_last_close() -> None:
    content = build()
    assert content["schema_version"] == ANALYSIS_SCHEMA_VERSION
    assert content["population"] == "SYNTHETIC"
    bars_block = content["bars"]
    assert bars_block["status"] == "OK"
    assert bars_block["count"] == 3
    assert bars_block["last_close"] == "104.50"
    assert bars_block["first_trading_day"] == "2026-08-21"
    assert bars_block["last_trading_day"] == "2026-08-24"
    assert bars_block["bars"][0]["open"] == "100.00"
    assert bars_block["discarded"] == []
    assert bars_block["fresh"] is True


@pytest.mark.parametrize(
    "bad",
    [
        bar("2026-08-23", "100.00", "99.00", "98.00", "100.00"),  # high < max(o,c)
        bar("2026-08-23", "100.00", "101.00", "100.50", "100.00"),  # low > min
        bar("2026-08-23", "100.00", "101.00", "99.00", "junk"),  # non-decimal
        bar("2026-08-23", "100.00", "101.00", "99.00", "100.00", volume=-1),
        {"trading_day": "2026-08-23"},  # missing fields
    ],
)
def test_invalid_bars_are_discarded_with_reason(bad) -> None:
    content = build([bars_record(bars=[*good_bars(), bad])])
    bars_block = content["bars"]
    assert bars_block["count"] == 3
    assert bars_block["discarded"] == [{"index": 3, "reason": REASON_INVALID_BAR}]
    # A partial series honestly degrades the snapshot quality fact.
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["snapshot_fresh_and_coherent"]["reason_code"] == "PARTIAL_SNAPSHOT"


def test_advice_is_the_engines_honest_verdict_never_forced() -> None:
    content = build(evidence=[news_record("e1", "[SYNTHETIC] item one")])
    advice = content["advice"]
    # The synthetic population cannot prove entitlements, session, liquidity,
    # contradictions or constraints: INSUFFICIENT_DATA is the WANTED result.
    assert advice["status"] == "INSUFFICIENT_DATA"
    assert advice["direction"] == "UNKNOWN"
    gates = {g["gate_id"]: g for g in advice["gates"]}
    assert len(gates) == 10
    for gate_id in (
        "entitlements_sufficient",
        "session_and_event_known",
        "minimum_liquidity",
        "critical_contradictions_resolved",
        "user_constraints_versioned",
    ):
        assert gates[gate_id]["status"] == "BLOCK"
        assert gates[gate_id]["reason_code"] == "UNEVALUABLE"
    assert gates["instrument_resolved"]["status"] == "DEGRADE"
    assert gates["instrument_resolved"]["reason_code"] == "RESOLVED_WITHOUT_CONID"
    assert gates["snapshot_fresh_and_coherent"]["status"] == "PASS"
    assert gates["manual_portfolio_risk_available"]["reason_code"] == "NOT_REQUIRED"
    assert gates["probability_calibrated_if_used"]["status"] == "PASS"
    assert advice["probability_evidence"] is None
    assert "SYNTHETIC development population" in advice["limitations"]


def test_evidence_clusters_come_from_fusion_for_this_ticker_only() -> None:
    evidence = [
        news_record("e1", "[SYNTHETIC] story one about SYN-TECH-01"),
        # NATIVE duplicate of e1: same provider native id -> same cluster.
        news_record("e2", "[SYNTHETIC] rewritten story one", native_id="native-e1"),
        news_record("e3", "[SYNTHETIC] other ticker story", ticker="SYN-UTIL-04"),
    ]
    content = build(evidence=evidence)
    block = content["evidence"]
    assert block["source"] == "fusion"
    assert block["considered"] == 2  # the SYN-UTIL-04 story is out of scope
    assert block["clusters_total"] == 1
    (cluster,) = block["clusters"]
    assert cluster["member_count"] == 2
    assert set(cluster["member_event_ids"]) == {"e1", "e2"}
    assert cluster["synthetic"] is True
    assert content["advice"]["evidence_ids"] == [cluster["cluster_id"]]


def test_scenarios_absent_without_chain_snapshot() -> None:
    content = build(chain=None)
    assert content["scenarios"] == {
        "status": "ABSENT",
        "reason": REASON_NO_OPTION_CHAIN,
    }
    assert content["advice"]["scenario_ids"] == []
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    # No calculation ran: gate 6 stays honestly unevaluable.
    assert gates["calculations_valid"]["reason_code"] == "UNEVALUABLE"


def test_scenarios_absent_without_a_healthy_contract() -> None:
    chain = healthy_chain_content()
    chain["expirations"][0]["contracts"][0]["iv"] = {
        "status": "ABSENT",
        "reason": "crossed_quote",
    }
    content = build(chain=chain)
    assert content["scenarios"] == {
        "status": "ABSENT",
        "reason": REASON_NO_HEALTHY_CONTRACT,
    }


def test_scenarios_grid_via_the_single_authority_when_contract_is_healthy() -> None:
    content = build(chain=healthy_chain_content(), chain_version=4)
    scenarios = content["scenarios"]
    assert scenarios["status"] == "OK"
    assert scenarios["value_nature"] == "THEORETICAL"
    basis = scenarios["basis"]
    assert basis["right"] == "CALL"
    assert basis["premium"] == "3.70"
    assert basis["premium_side"] == "ASK"
    assert basis["chain_snapshot_version"] == 4
    assert len(scenarios["spot_grid"]) == 5
    assert len(scenarios["time_grid_years"]) == 3
    grid = scenarios["grid"]
    assert len(grid) == 1  # one scenario: IV unchanged
    assert len(grid[0]) == 3 and all(len(row) == 5 for row in grid[0])
    assert all(isinstance(cell, str) for row in grid[0] for cell in row)
    calc = scenarios["calculation"]
    assert calc["calculation_id"] == "options.scenario_grid"
    assert calc["input_hash"].startswith("sha256:")
    # The scenario id and the calculation status feed the advice honestly.
    assert content["advice"]["scenario_ids"] == [calc["input_hash"]]
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["calculations_valid"]["reason_code"] == "ALL_CALCULATIONS_VALID"


def test_deny_by_default_sources_and_rights() -> None:
    records = [
        bars_record(event_id="bad", source="unknown-source"),
    ]
    content = build(records)
    assert content["bars"]["status"] == "ABSENT"
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "bad", "reason": REASON_SOURCE_NOT_ALLOWED}
    ]
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["snapshot_fresh_and_coherent"]["reason_code"] == "MISSING_SNAPSHOT"
    assert content["advice"]["status"] == "INSUFFICIENT_DATA"


def test_latest_record_wins_and_determinism() -> None:
    records = [
        bars_record(event_id="old", as_of=NOW - timedelta(hours=10)),
        bars_record(
            event_id="new",
            as_of=NOW - timedelta(hours=1),
            bars=[bar("2026-08-24", "50.00", "51.00", "49.00", "50.50")],
        ),
    ]
    first = build(records)
    second = build(list(reversed(records)))
    assert first == second
    assert first["bars"]["source_event_id"] == "new"
    assert first["bars"]["last_close"] == "50.50"


def test_undeclared_instrument_is_refused() -> None:
    with pytest.raises(ValueError):
        build_analysis_content(
            [],
            instrument="SYN-UTIL-01",
            evidence_records=(),
            option_chain_content=None,
            option_chain_version=None,
            now=NOW,
            config=CONFIG,
        )


def test_dev_config_is_synthetic_only() -> None:
    assert DEV_SYNTHETIC_ANALYSIS_CONFIG.allowed_sources == frozenset(
        {SYNTHETIC_SOURCE}
    )
    assert DEV_SYNTHETIC_ANALYSIS_CONFIG.usable_rights == frozenset({SYNTHETIC_RIGHTS})
    assert len(DEV_SYNTHETIC_ANALYSIS_CONFIG.instruments) == 4
