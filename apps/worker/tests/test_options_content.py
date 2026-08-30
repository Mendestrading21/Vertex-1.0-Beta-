"""Unit tests of the pure option-chain content builder (SYNTHETIC only).

Records are built in memory from explicit decimal strings; quotes for the
happy path are derived from ``vertex_core.calculations.options.european_price``
with a KNOWN volatility so the builder's resolved Vertex IV must round-trip
back to it — the oracle is the single calculation authority, never a
re-implementation. No database, no clock, no network.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

import pytest

from vertex_core.calculations.options import european_price
from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.options import (
    DEV_SYNTHETIC_OPTIONS_CONFIG,
    OPTION_CHAIN_SCHEMA_VERSION,
    QUOTE_STATUS_CROSSED,
    QUOTE_STATUS_MISSING,
    QUOTE_STATUS_OK,
    QUOTE_STATUS_STALE,
    REASON_CONTRACT_EXPIRED,
    REASON_INCOMPLETE_IDENTITY,
    REASON_INVALID_PAYLOAD,
    REASON_IV_UNRESOLVED,
    REASON_QUOTE_CROSSED,
    REASON_QUOTE_MISSING,
    REASON_QUOTE_STALE,
    REASON_RIGHTS_NOT_USABLE,
    REASON_SOURCE_NOT_ALLOWED,
    TOPIC_OPTION_CHAINS_INGESTED,
    OptionChainRecord,
    OptionsConfig,
    build_option_chain_content,
    is_option_chain_schema,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
FRESH = (NOW - timedelta(minutes=30)).isoformat()
STALE = (NOW - timedelta(hours=24)).isoformat()
EXPIRY = date(2026, 9, 22)  # 28 days after NOW
MATURITY_YEARS = 28 / 365.0

SPOT = "100.00"
RATE = "0.02"
DIVIDEND_YIELD = "0.00"
KNOWN_VOL = 0.25

CONFIG = OptionsConfig(
    underlyings=("SYN-TECH-01", "SYN-TECH-02"),
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)

_CENTS = Decimal("0.01")


def sane_quote(strike: str, right: str) -> tuple[str, str]:
    """bid/ask around the theoretical price at the KNOWN volatility."""
    price = european_price(
        Decimal(SPOT),
        Decimal(strike),
        MATURITY_YEARS,
        Decimal(RATE),
        Decimal(DIVIDEND_YIELD),
        KNOWN_VOL,
        right,
    )
    mid = Decimal(repr(price)).quantize(_CENTS, rounding=ROUND_HALF_EVEN)
    return format(mid - Decimal("0.05"), "f"), format(mid + Decimal("0.05"), "f")


def contract(
    con_id: int,
    strike: str,
    right: str,
    *,
    bid: str | None = "auto",
    ask: str | None = "auto",
    observed_at: str | None = FRESH,
) -> dict:
    if bid == "auto" or ask == "auto":
        auto_bid, auto_ask = sane_quote(strike, right)
        bid = auto_bid if bid == "auto" else bid
        ask = auto_ask if ask == "auto" else ask
    return {
        "con_id": con_id,
        "strike": strike,
        "right": right,
        "bid": bid,
        "ask": ask,
        "bid_size": 10 if bid else None,
        "ask_size": 12 if ask else None,
        "volume": 123,
        "open_interest": 4567,
        "open_interest_status": "OI_DELAYED",
        "observed_at": observed_at,
    }


def slice_record(
    *,
    underlying: str = "SYN-TECH-01",
    expiration: str = EXPIRY.isoformat(),
    trading_class: str | None = None,
    contracts: list[dict],
    event_id: str = "synthetic-dev:t:oc0001",
    source: str = SYNTHETIC_SOURCE,
    rights: str = SYNTHETIC_RIGHTS,
    as_of: datetime | None = None,
    spot: str = SPOT,
) -> OptionChainRecord:
    return OptionChainRecord(
        event_id=event_id,
        source=source,
        instrument_ref=underlying,
        as_of=as_of or NOW - timedelta(minutes=29),
        quality_status="VALID",
        rights=rights,
        schema_version="synthetic-option-chain/1.0",
        payload={
            "type": "option_chain_slice",
            "synthetic": True,
            "underlying": underlying,
            "underlying_spot": spot,
            "currency": "SYN",
            "expiration": expiration,
            "trading_class": trading_class or underlying,
            "exchange": "SYNTH",
            "style": "EUROPEAN",
            "settlement": "CASH",
            "multiplier": 100,
            "rate": RATE,
            "dividend_yield": DIVIDEND_YIELD,
            "contracts": contracts,
        },
    )


def test_schema_predicate_and_registry_topic() -> None:
    assert is_option_chain_schema("synthetic-option-chain/1.0") is True
    assert is_option_chain_schema("synthetic-daily-quote/1.0") is False
    assert is_option_chain_schema("") is False
    registry = build_registry(clock=lambda: NOW, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_OPTION_CHAINS_INGESTED in registry.topics


def test_sane_quote_resolves_iv_and_greeks_with_lineage() -> None:
    records = [slice_record(contracts=[contract(1, "100.00", "CALL")])]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    assert content["schema_version"] == OPTION_CHAIN_SCHEMA_VERSION
    assert content["population"] == "SYNTHETIC"
    assert content["value_nature"] == "THEORETICAL"
    assert content["spot"]["value"] == SPOT

    (group,) = content["expirations"]
    assert group["expiration"] == EXPIRY.isoformat()
    assert group["trading_class"] == "SYN-TECH-01"
    (entry,) = group["contracts"]

    # Full identity is present on the contract row.
    for field in (
        "con_id",
        "strike",
        "right",
        "expiration",
        "trading_class",
        "multiplier",
        "currency",
        "exchange",
        "style",
        "settlement",
    ):
        assert entry[field] is not None

    quote = entry["quote"]
    assert quote["status"] == QUOTE_STATUS_OK
    assert quote["bid"] < quote["ask"]

    iv = entry["iv"]
    assert iv["status"] == "OK"
    assert iv["quote_side"] == "MID"
    assert iv["value_nature"] == "THEORETICAL"
    # Round trip: the quote was priced at KNOWN_VOL, so the resolved Vertex
    # IV must land next to it (cent rounding tolerance).
    assert abs(float(iv["value"]) - KNOWN_VOL) < 0.01
    calc = iv["calculation"]
    assert calc["calculation_id"] == "options.implied_volatility"
    assert calc["input_hash"].startswith("sha256:")
    assert calc["result_hash"].startswith("sha256:")
    assert calc["status"] == "OK"

    greeks_block = entry["greeks"]
    assert greeks_block["status"] == "OK"
    assert greeks_block["value_nature"] == "THEORETICAL"
    assert 0.0 < float(greeks_block["delta"]) < 1.0
    assert float(greeks_block["gamma"]) > 0.0
    assert float(greeks_block["vega"]) > 0.0
    assert greeks_block["calculation"]["calculation_id"] == "options.greeks"

    coverage = group["coverage"]
    assert coverage == {
        "expected": 1,
        "quotes_received": 1,
        "quotes_valid": 1,
        "iv_resolved": 1,
        "discarded": [],
    }


@pytest.mark.parametrize(
    ("kwargs", "status", "reason"),
    [
        (
            {"bid": "9.00", "ask": "8.00"},
            QUOTE_STATUS_CROSSED,
            REASON_QUOTE_CROSSED,
        ),
        (
            {"bid": "8.00", "ask": "8.00"},
            QUOTE_STATUS_CROSSED,
            REASON_QUOTE_CROSSED,
        ),
        ({"observed_at": STALE}, QUOTE_STATUS_STALE, REASON_QUOTE_STALE),
        ({"observed_at": None}, QUOTE_STATUS_STALE, REASON_QUOTE_STALE),
        (
            {"bid": None, "ask": None},
            QUOTE_STATUS_MISSING,
            REASON_QUOTE_MISSING,
        ),
    ],
)
def test_unsane_quotes_never_get_an_iv(kwargs, status, reason) -> None:
    records = [slice_record(contracts=[contract(1, "100.00", "CALL", **kwargs)])]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    (group,) = content["expirations"]
    (entry,) = group["contracts"]
    assert entry["quote"]["status"] == status
    assert entry["iv"] == {"status": "ABSENT", "reason": reason}
    assert entry["greeks"] == {"status": "ABSENT", "reason": REASON_IV_UNRESOLVED}
    assert group["coverage"]["iv_resolved"] == 0
    assert group["coverage"]["discarded"] == [
        {"con_id": 1, "strike": "100.00", "right": "CALL", "reason": reason}
    ]


def test_price_outside_bounds_is_an_explicit_iv_refusal() -> None:
    # A "quote" way above the no-arbitrage ceiling: sane spread, absurd level.
    records = [
        slice_record(
            contracts=[contract(1, "100.00", "CALL", bid="150.00", ask="151.00")]
        )
    ]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    (entry,) = content["expirations"][0]["contracts"]
    assert entry["quote"]["status"] == QUOTE_STATUS_OK
    assert entry["iv"]["status"] == "ABSENT"
    assert entry["iv"]["reason"] == "price_outside_no_arbitrage_bounds"


def test_incomplete_identity_blocks_every_calculation() -> None:
    broken = contract(1, "100.00", "CALL")
    del broken["con_id"]
    records = [slice_record(contracts=[broken])]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    (entry,) = content["expirations"][0]["contracts"]
    assert entry["iv"] == {"status": "ABSENT", "reason": REASON_INCOMPLETE_IDENTITY}


def test_expired_contracts_are_discarded_not_priced() -> None:
    records = [
        slice_record(
            expiration="2026-08-25",  # expires today: 0 days on the grid
            contracts=[contract(1, "100.00", "CALL")],
        )
    ]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    (entry,) = content["expirations"][0]["contracts"]
    assert entry["iv"] == {"status": "ABSENT", "reason": REASON_CONTRACT_EXPIRED}


def test_same_expiration_two_trading_classes_stay_separated() -> None:
    records = [
        slice_record(
            trading_class="SYN-TECH-01",
            contracts=[contract(1, "100.00", "CALL")],
            event_id="e1",
        ),
        slice_record(
            trading_class="SYN-TECH-01W",
            contracts=[contract(2, "100.00", "CALL")],
            event_id="e2",
        ),
    ]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    groups = [
        (g["expiration"], g["trading_class"]) for g in content["expirations"]
    ]
    assert groups == [
        (EXPIRY.isoformat(), "SYN-TECH-01"),
        (EXPIRY.isoformat(), "SYN-TECH-01W"),
    ]
    assert content["expirations"][0]["contracts"][0]["con_id"] == 1
    assert content["expirations"][1]["contracts"][0]["con_id"] == 2


def test_latest_record_wins_per_group() -> None:
    records = [
        slice_record(
            contracts=[contract(1, "100.00", "CALL")],
            event_id="old",
            as_of=NOW - timedelta(hours=2),
        ),
        slice_record(
            contracts=[contract(2, "100.00", "CALL")],
            event_id="new",
            as_of=NOW - timedelta(minutes=5),
        ),
    ]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    (group,) = content["expirations"]
    assert group["source_event_id"] == "new"
    assert group["contracts"][0]["con_id"] == 2


def test_deny_by_default_source_rights_and_invalid_payload() -> None:
    records = [
        slice_record(
            contracts=[contract(1, "100.00", "CALL")],
            event_id="bad-source",
            source="unknown-source",
        ),
        slice_record(
            contracts=[contract(2, "100.00", "CALL")],
            event_id="bad-rights",
            rights="UNKNOWN",
        ),
        slice_record(
            contracts=[contract(3, "100.00", "CALL")],
            event_id="bad-spot",
            spot="not-a-number",
        ),
    ]
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    assert content["expirations"] == []
    reasons = {
        entry["event_id"]: entry["reason"]
        for entry in content["coverage"]["rejected_records"]
    }
    assert reasons == {
        "bad-source": REASON_SOURCE_NOT_ALLOWED,
        "bad-rights": REASON_RIGHTS_NOT_USABLE,
        "bad-spot": REASON_INVALID_PAYLOAD,
    }


def test_undeclared_underlying_is_refused_by_the_builder() -> None:
    with pytest.raises(ValueError):
        build_option_chain_content(
            [], underlying="SYN-UTIL-01", now=NOW, config=CONFIG
        )


def test_row_budget_truncates_and_reports() -> None:
    contracts = [
        contract(i, f"{90 + i}.00", "CALL") for i in range(1, 6)
    ]
    records = [slice_record(contracts=contracts)]
    small = OptionsConfig(
        underlyings=CONFIG.underlyings,
        allowed_sources=CONFIG.allowed_sources,
        usable_rights=CONFIG.usable_rights,
        max_chain_rows=3,
    )
    content = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=small
    )
    (group,) = content["expirations"]
    assert len(group["contracts"]) == 3
    assert group["coverage"]["expected"] == 5  # coverage stays honest
    assert content["row_budget"] == {
        "max_rows": 3,
        "total_rows": 5,
        "published_rows": 3,
        "truncated_rows": 2,
    }


def test_no_records_for_underlying_is_empty_population() -> None:
    content = build_option_chain_content(
        [], underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    assert content["population"] == "EMPTY"
    assert content["expirations"] == []
    assert content["spot"] is None


def test_determinism_regardless_of_record_order() -> None:
    records = [
        slice_record(
            trading_class="SYN-TECH-01",
            contracts=[contract(1, "100.00", "CALL"), contract(2, "100.00", "PUT")],
            event_id="e1",
        ),
        slice_record(
            trading_class="SYN-TECH-01W",
            contracts=[contract(3, "105.00", "CALL")],
            event_id="e2",
        ),
    ]
    forward = build_option_chain_content(
        records, underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    backward = build_option_chain_content(
        list(reversed(records)), underlying="SYN-TECH-01", now=NOW, config=CONFIG
    )
    assert forward == backward


def test_dev_config_is_synthetic_only() -> None:
    assert DEV_SYNTHETIC_OPTIONS_CONFIG.allowed_sources == frozenset({SYNTHETIC_SOURCE})
    assert DEV_SYNTHETIC_OPTIONS_CONFIG.usable_rights == frozenset({SYNTHETIC_RIGHTS})
    assert len(DEV_SYNTHETIC_OPTIONS_CONFIG.underlyings) == 4


def test_ingest_routes_option_chain_envelopes_to_the_topic(monkeypatch) -> None:
    import vertex_worker.ingest as ingest_module
    from vertex_core.synthetic import generate_option_chain_envelopes
    from vertex_worker.ingest import TOPIC_OBSERVATION_INGESTED, ingest_envelope

    envelope = generate_option_chain_envelopes(seed=1, base_time=NOW)[0]
    topics: list[str] = []

    monkeypatch.setattr(
        ingest_module, "insert_observation", lambda session, **kwargs: True
    )
    monkeypatch.setattr(
        ingest_module,
        "enqueue_outbox",
        lambda session, topic, payload: topics.append(topic) or 1,
    )

    class _Session:
        def execute(self, statement, params=None):
            return None

    ingest_envelope(_Session(), envelope)
    # A chain envelope feeds the chain handler AND the analysis dossier
    # (whose scenarios read the chain snapshot), chain job first; a chain also
    # changes the advice basis of a candidate, so the opportunities funnel is
    # refreshed too; every inserted observation refreshes the review queue.
    from vertex_worker.analysis import TOPIC_ANALYSIS_INGESTED
    from vertex_worker.follow_up import TOPIC_REVIEW_QUEUE_REFRESH
    from vertex_worker.opportunities import TOPIC_OPPORTUNITIES_REFRESH

    assert topics == [
        TOPIC_OBSERVATION_INGESTED,
        TOPIC_OPTION_CHAINS_INGESTED,
        TOPIC_ANALYSIS_INGESTED,
        TOPIC_OPPORTUNITIES_REFRESH,
        TOPIC_REVIEW_QUEUE_REFRESH,
    ]
