"""Unit tests of the performance content builder (SYNTHETIC fakes only).

Pure-builder tests over hand-built ledger events and daily-quote records:
gate branches (INSUFFICIENT_DATA / INVALID, each motivated), population
separation, heatmap month completeness and fail-closed day exclusions. The
real chain (routes -> outbox -> worker -> snapshot -> export) runs in
``apps/api/tests_integration/test_performance_api_e2e.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from vertex_worker.markets import DEV_SYNTHETIC_MARKETS_CONFIG, QuoteRecord
from vertex_worker.performance import (
    POPULATION_SYNTHETIC_MARKS_REAL_LEDGER,
    REASON_CASHFLOW_BOUNDARY,
    REASON_INSUFFICIENT_VALUATIONS,
    REASON_MULTI_CURRENCY,
    REASON_NO_EXTERNAL_CASHFLOW,
    build_performance_content,
)
from vertex_worker.portfolio import LedgerEventView, PortfolioView

NOW = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
TICKER = "SYN-TECH-01"
SECTOR = "SYN-TECH"
CURRENCY = "SYN"  # the synthetic mark universe's fictional currency code
PORTFOLIO = PortfolioView(id=1, name="main", base_currency="USD")
TOLERANCE = Decimal("1e-18")

D1, D2, D3 = "2026-08-24", "2026-08-25", "2026-08-26"


def utc(day: str, hour: int) -> datetime:
    year, month, dom = (int(part) for part in day.split("-"))
    return datetime(year, month, dom, hour, 0, 0, tzinfo=timezone.utc)


_EVENT_SEQ = iter(range(1, 10_000))


def make_event(
    kind: str,
    *,
    day: str,
    hour: int = 10,
    amount: str,
    quantity: Optional[str] = None,
    price: Optional[str] = None,
    fees: str = "0",
    currency: str = CURRENCY,
    ticker: Optional[str] = None,
) -> LedgerEventView:
    return LedgerEventView(
        id=next(_EVENT_SEQ),
        kind=kind,
        instrument={"ticker": ticker} if ticker is not None else None,
        quantity=Decimal(quantity) if quantity is not None else None,
        price=Decimal(price) if price is not None else None,
        amount=Decimal(amount),
        currency=currency,
        fees=Decimal(fees),
        effective_at=utc(day, hour),
        source="MANUAL",
        compensates=None,
    )


def make_quote(day: str, close: str, *, ticker: str = TICKER, sector: str = SECTOR) -> QuoteRecord:
    return QuoteRecord(
        event_id=f"syn-quote-{ticker}-{day}",
        source="synthetic-dev",
        instrument_ref=ticker,
        as_of=utc(day, 22),
        quality_status="VALID",
        rights="SYNTHETIC",
        schema_version="synthetic-daily-quote/1.0",
        payload={
            "ticker": ticker,
            "sector": sector,
            "trading_day": day,
            "close": close,
            "currency": CURRENCY,
            "adjustment_basis": "synthetic-unadjusted",
        },
    )


def build(events, quotes, **kwargs):
    return build_performance_content(
        events,
        quotes,
        portfolio=PORTFOLIO,
        now=NOW,
        config=DEV_SYNTHETIC_MARKETS_CONFIG,
        **kwargs,
    )


NOMINAL_EVENTS = [
    make_event("DEPOSIT", day=D1, hour=9, amount="10000"),
    make_event("BUY_RECORDED", day=D1, hour=11, amount="-1000", quantity="10", price="100", ticker=TICKER),
    make_event("DEPOSIT", day=D2, hour=12, amount="1000"),
    make_event("SELL_RECORDED", day=D2, hour=13, amount="550", quantity="5", price="110", ticker=TICKER),
]
NOMINAL_QUOTES = [make_quote(D1, "100"), make_quote(D2, "110"), make_quote(D3, "121")]


# -- nominal series: hand-verified values and boundaries ---------------------


def test_daily_series_and_twr_match_hand_computation() -> None:
    """Hand math (gross):

    V(D1) = cash(10000 - 1000) + 10 x 100      = 10000
    V(D2) = cash(9000 + 1000 + 550) + 5 x 110  = 11100
    V(D3) = cash(10550) + 5 x 121              = 11155
    D1 deposit is on the first valued day -> embedded in V(D1).
    D2 deposit (1000) adjusts the period ending at D2's close:
      r1 = 11100 / (10000 + 1000) - 1 = 100/11000
      r2 = 11155 / 11100 - 1          = 55/11100
      total = 11155/11000 - 1         = 155/11000
    """
    content = build(NOMINAL_EVENTS, NOMINAL_QUOTES)

    points = content["series"]["points"]
    assert [p["trading_day"] for p in points] == [D1, D2, D3]
    assert [p["gross_value"] for p in points] == ["10000", "11100", "11155"]
    assert [p["cash"] for p in points] == ["9000", "10550", "10550"]
    assert [p["position_value"] for p in points] == ["1000", "550", "605"]

    twr = content["metrics"]["twr_gross"]
    assert twr["status"] == "OK"
    expected_r1 = Decimal(100) / Decimal(11000)
    expected_r2 = Decimal(55) / Decimal(11100)
    expected_total = Decimal(155) / Decimal(11000)
    assert abs(Decimal(twr["periods"][0]["return"]) - expected_r1) < TOLERANCE
    assert abs(Decimal(twr["periods"][1]["return"]) - expected_r2) < TOLERANCE
    assert abs(Decimal(twr["total_return"]) - expected_total) < TOLERANCE
    assert twr["cashflows_embedded_in_opening"] == 1
    calc = twr["calculation"]
    assert calc["calculation_id"] == "performance.twr"
    assert calc["input_hash"].startswith("sha256:")
    assert calc["result_hash"].startswith("sha256:")

    xirr = content["metrics"]["xirr_gross"]
    assert xirr["status"] == "OK"
    assert Decimal(xirr["rate"]) > 0
    assert xirr["calculation"]["calculation_id"] == "performance.xirr"

    dd = content["metrics"]["drawdown_gross"]
    assert dd["status"] == "OK"
    assert dd["max_drawdown"] == "0"  # monotone series never draws down
    assert dd["peak_at"] is None and dd["trough_at"] is None
    assert dd["calculation"]["calculation_id"] == "performance.drawdown"

    coverage = content["coverage"]
    assert coverage["days_with_close"] == 3
    assert coverage["days_valued"] == 3
    assert coverage["coverage_ratio"] == "1.000000"


def test_gross_and_net_are_explicit_and_distinct() -> None:
    events = list(NOMINAL_EVENTS)
    events[1] = make_event(
        "BUY_RECORDED", day=D1, hour=11, amount="-1000",
        quantity="10", price="100", ticker=TICKER, fees="7",
    )
    content = build(events, NOMINAL_QUOTES)
    points = content["series"]["points"]
    # Documented net convention: net = gross - cumulative declared fees.
    for point in points:
        assert Decimal(point["net_value"]) == Decimal(point["gross_value"]) - Decimal("7")
    twr_gross = content["metrics"]["twr_gross"]
    twr_net = content["metrics"]["twr_net"]
    assert twr_gross["status"] == twr_net["status"] == "OK"
    assert twr_gross["total_return"] != twr_net["total_return"]
    assert twr_gross["calculation"]["input_hash"] != twr_net["calculation"]["input_hash"]


# -- TWR gate: complete cashflow boundaries or INSUFFICIENT_DATA -------------


def test_cashflow_without_valuation_boundary_is_insufficient_data() -> None:
    events = [
        make_event("DEPOSIT", day=D1, hour=9, amount="10000"),
        make_event("DEPOSIT", day=D2, hour=12, amount="1000"),  # D2 has NO close
    ]
    quotes = [make_quote(D1, "100"), make_quote(D3, "121")]
    content = build(events, quotes)
    for name in ("twr_gross", "twr_net"):
        block = content["metrics"][name]
        assert block["status"] == "INSUFFICIENT_DATA"
        assert block["reason"] == REASON_CASHFLOW_BOUNDARY
        assert block["detail"]["missing_days"] == [D2]
        assert block["calculation"] is None
    # The heatmap mirrors the TWR gate instead of inventing months.
    assert content["heatmap"]["status"] == "INSUFFICIENT_DATA"
    assert content["heatmap"]["months"] == []


def test_single_valuation_day_is_insufficient_for_twr() -> None:
    events = [make_event("DEPOSIT", day=D1, hour=9, amount="1000")]
    content = build(events, [make_quote(D1, "100")])
    assert content["metrics"]["twr_gross"]["status"] == "INSUFFICIENT_DATA"
    assert content["metrics"]["twr_gross"]["reason"] == REASON_INSUFFICIENT_VALUATIONS
    # Drawdown over one point is legal; XIRR needs at least one external flow
    # plus the terminal value (present here) — one deposit and one value.
    assert content["metrics"]["drawdown_gross"]["status"] == "OK"


# -- XIRR gates: motivated INVALID / INSUFFICIENT_DATA -----------------------


def test_xirr_without_any_external_cashflow_is_insufficient() -> None:
    events = [
        make_event("BUY_RECORDED", day=D1, hour=11, amount="-1000", quantity="10", price="100", ticker=TICKER),
    ]
    content = build(events, NOMINAL_QUOTES)
    for name in ("xirr_gross", "xirr_net"):
        assert content["metrics"][name]["status"] == "INSUFFICIENT_DATA"
        assert content["metrics"][name]["reason"] == REASON_NO_EXTERNAL_CASHFLOW


def test_xirr_without_sign_change_is_invalid_with_reason() -> None:
    # Withdrawal only: investor flows are +50 and the terminal value +505 —
    # no strictly negative flow, the sign-change gate closes.
    events = [
        make_event("BUY_RECORDED", day=D1, hour=11, amount="-1000", quantity="10", price="100", ticker=TICKER),
        make_event("WITHDRAWAL", day=D2, hour=12, amount="-50"),
    ]
    content = build(events, NOMINAL_QUOTES)
    xirr = content["metrics"]["xirr_gross"]
    assert xirr["status"] == "INVALID"
    assert "positive" in xirr["reason"] and "negative" in xirr["reason"]
    assert xirr["calculation"] is None
    assert "rate" not in xirr  # an INVALID outcome never carries a number


# -- populations: one explicit label, never aggregated -----------------------


def test_population_is_explicit_and_never_blended() -> None:
    content = build(NOMINAL_EVENTS, NOMINAL_QUOTES)
    assert content["population"] == POPULATION_SYNTHETIC_MARKS_REAL_LEDGER
    assert content["population_components"] == {
        "marks": "SYNTHETIC",
        "ledger": "USER_DECLARED",
    }


def test_multi_currency_ledger_fails_closed_not_blended() -> None:
    events = list(NOMINAL_EVENTS) + [
        make_event("DEPOSIT", day=D1, hour=10, amount="500", currency="EUR"),
    ]
    content = build(events, NOMINAL_QUOTES)
    assert content["series"]["status"] == "INSUFFICIENT_DATA"
    assert content["series"]["reason"] == REASON_MULTI_CURRENCY
    assert content["series"]["points"] == []
    assert content["currency"] is None
    for block in content["metrics"].values():
        assert block["status"] == "INSUFFICIENT_DATA"
        assert block["reason"] == REASON_MULTI_CURRENCY
    # The population label survives untouched — no cross-currency figure was
    # invented to keep a number on screen.
    assert content["population"] == POPULATION_SYNTHETIC_MARKS_REAL_LEDGER


# -- fail-closed day exclusion: absent mark is never a zero ------------------


def test_day_with_missing_mark_is_excluded_with_reason_never_zero() -> None:
    events = [
        make_event("DEPOSIT", day=D1, hour=9, amount="10000"),
        make_event("BUY_RECORDED", day=D1, hour=11, amount="-1000", quantity="10", price="100", ticker=TICKER),
    ]
    quotes = [
        make_quote(D1, "100"),
        # D2 exists as a close day, but only for ANOTHER ticker: the open
        # lot in SYN-TECH-01 has no usable mark that day.
        make_quote(D2, "55", ticker="SYN-TECH-02"),
        make_quote(D3, "121"),
    ]
    content = build(events, quotes)
    points = content["series"]["points"]
    assert [p["trading_day"] for p in points] == [D1, D3]
    excluded = content["series"]["excluded_days"]
    assert len(excluded) == 1
    assert excluded[0]["trading_day"] == D2
    assert excluded[0]["reason"] == "missing_mark"
    assert excluded[0]["detail"] == {"ticker": TICKER}
    coverage = content["coverage"]
    assert coverage["days_with_close"] == 3
    assert coverage["days_valued"] == 2
    assert coverage["coverage_ratio"] == "0.666667"


# -- heatmap: monthly TWR regrouping with incomplete months marked -----------


def test_heatmap_marks_incomplete_months_and_preserves_chaining() -> None:
    days = ["2026-07-31", "2026-08-10", "2026-08-31", "2026-09-01"]
    closes = ["100", "104", "104", "130"]
    events = [
        make_event("DEPOSIT", day="2026-07-31", hour=9, amount="10000"),
        make_event(
            "BUY_RECORDED", day="2026-07-31", hour=10, amount="-1000",
            quantity="10", price="100", ticker=TICKER,
        ),
    ]
    quotes = [make_quote(day, close) for day, close in zip(days, closes)]
    content = build(events, quotes)
    twr = content["metrics"]["twr_gross"]
    assert twr["status"] == "OK"
    heatmap = content["heatmap"]
    assert heatmap["status"] == "OK"
    months = {entry["month"]: entry for entry in heatmap["months"]}
    assert set(months) == {"2026-08", "2026-09"}
    # 2026-08 sits strictly inside the series with no excluded day: complete.
    assert months["2026-08"]["complete"] is True
    assert months["2026-08"]["periods"] == 2
    # 2026-09 closes the series: honestly marked incomplete.
    assert months["2026-09"]["complete"] is False
    assert "last_month_of_series" in months["2026-09"]["incomplete_reasons"]
    # Chain-link invariant: product of month factors == total factor.
    product = Decimal("1")
    for entry in heatmap["months"]:
        product *= Decimal("1") + Decimal(entry["return"])
    total = Decimal("1") + Decimal(twr["total_return"])
    assert abs(product - total) < TOLERANCE
    # The heatmap is derived from the AUTHORITATIVE TWR calculation.
    assert heatmap["derived_from_calculation"]["input_hash"] == twr["calculation"]["input_hash"]


def test_builder_is_deterministic_under_input_shuffle() -> None:
    first = build(NOMINAL_EVENTS, NOMINAL_QUOTES)
    second = build(list(reversed(NOMINAL_EVENTS)), list(reversed(NOMINAL_QUOTES)))
    assert first == second
