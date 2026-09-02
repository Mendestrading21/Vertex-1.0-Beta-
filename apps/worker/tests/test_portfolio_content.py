"""Unit tests of the portfolio valuation content builder (status: SYNTHETIC).

Pure-function tests over deterministic in-memory views — no database, no
network, no real clock. They pin the fail-closed valuation contract: a lot
without a usable mark is EXCLUDED with its reason (never valued at zero),
every valuation carries the ``mark_population`` DECLARED BY ITS SOURCE (and
``EMPTY`` when the source declares none), compensation pairs net out of the
lots, and every financial figure keeps its vertex_core
``CalculationRecord`` lineage.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vertex_worker.portfolio import (
    LOT_METHOD_VERSION,
    MARK_POPULATION_SYNTHETIC,
    MARK_POPULATION_UNQUALIFIED,
    PORTFOLIO_VALUATION_SCHEMA_VERSION,
    REASON_INVALID_MARK,
    REASON_MARK_CURRENCY_MISMATCH,
    REASON_MISSING_MARK,
    REASON_NO_MARK_SOURCE,
    REASON_OVERSOLD_POSITION,
    LedgerEventView,
    MarkQuote,
    MarksView,
    PortfolioView,
    build_portfolio_valuation_content,
    extract_marks_from_markets_content,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
T0 = datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC)
T1 = datetime(2026, 8, 21, 10, 0, 0, tzinfo=UTC)

PORTFOLIO = PortfolioView(id=1, name="main", base_currency="USD")


def make_event(
    event_id: int,
    kind: str,
    *,
    ticker: str | None = None,
    quantity: str | None = None,
    price: str | None = None,
    amount: str = "0",
    fees: str = "0",
    currency: str = "SYN",
    compensates: int | None = None,
    effective_at: datetime = T0,
) -> LedgerEventView:
    return LedgerEventView(
        id=event_id,
        kind=kind,
        instrument=None if ticker is None else {"ticker": ticker},
        quantity=None if quantity is None else Decimal(quantity),
        price=None if price is None else Decimal(price),
        amount=Decimal(amount),
        currency=currency,
        fees=Decimal(fees),
        effective_at=effective_at,
        source="MANUAL",
        compensates=compensates,
    )


def make_marks(population: str = "SYNTHETIC", **closes: str) -> MarksView:
    """Marques de test. La nature est DECLAREE, jamais laissee au hasard.

    Depuis que `mark_population` est relayee depuis la source, une fixture qui
    ne declare rien vaut « nature inconnue » et ne valorise plus rien — ce qui
    est le comportement fail-closed voulu, mais pas ce que ces tests veulent
    eprouver.
    """
    return MarksView(
        population=population,
        snapshot_version=7,
        as_of_text=NOW.isoformat(),
        closes={
            ticker: MarkQuote(
                ticker=ticker, close=Decimal(value), currency="SYN", trading_day="d"
            )
            for ticker, value in closes.items()
        },
        invalid_tickers=(),
    )


def build(events, marks):
    return build_portfolio_valuation_content(
        events, portfolio=PORTFOLIO, marks=marks, now=NOW
    )


def test_lot_without_mark_is_excluded_with_reason_never_zero() -> None:
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-A", quantity="10", price="100", amount="-1000"),
        make_event(2, "BUY_RECORDED", ticker="SYN-X", quantity="5", price="20", amount="-100"),
    ]
    content = build(events, make_marks(**{"SYN-A": "120"}))

    excluded = content["excluded_lots"]
    assert excluded == [
        {"lot_id": "ledger-2", "ticker": "SYN-X", "currency": "SYN", "reason": REASON_MISSING_MARK}
    ]
    group = content["positions_by_currency"][0]
    valued_ids = [lot["lot_id"] for lot in group["unrealized"]["lots"]]
    assert valued_ids == ["ledger-1"]
    # The excluded lot contributes NOTHING: the total is the valued lot only.
    assert group["unrealized"]["total_unrealized"] == "200"
    assert content["coverage"]["lots_open"] == 2
    assert content["coverage"]["lots_valued"] == 1
    assert content["coverage"]["lots_excluded"] == 1


def test_no_markets_snapshot_yields_absent_totals_never_zero() -> None:
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-A", quantity="10", price="100", amount="-1000"),
    ]
    content = build(events, None)

    assert content["marks"]["status"] == "ABSENT"
    assert content["marks"]["reason"] == REASON_NO_MARK_SOURCE
    group = content["positions_by_currency"][0]
    assert group["unrealized"]["status"] == "ABSENT"
    assert group["unrealized"]["reason"] == "no_lot_valued"
    assert group["unrealized"]["total_unrealized"] is None  # absence, not 0
    assert group["concentration"]["status"] == "ABSENT"
    assert content["excluded_lots"] == [
        {
            "lot_id": "ledger-1",
            "ticker": "SYN-A",
            "currency": "SYN",
            "reason": REASON_NO_MARK_SOURCE,
        }
    ]


def test_mark_population_follows_its_source_and_fails_closed() -> None:
    """REECRIT. Son nom et son assertion GRAVAIENT le defaut du §4.1.

    L'ancien test s'appelait `test_mark_population_is_always_synthetic` et
    exigeait `SYNTHETIC` MEME SANS AUCUNE MARQUE. Il ne testait donc pas une
    propriete du produit : il figeait une constante ecrite en dur, et rendait
    la correction impossible sans le toucher.

    Ce n'est PAS un affaiblissement : la nouvelle version verifie une
    propriete plus forte — la nature SUIT sa source, et l'absence de source
    ferme au lieu de choisir une etiquette par defaut.
    """
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-A", quantity="1", price="10", amount="-10"),
    ]
    synthetiques = build(events, make_marks(**{"SYN-A": "12"}))
    assert synthetiques["mark_population"] == MARK_POPULATION_SYNTHETIC

    # Une source REELLE donne des marques reelles — le cas du poste de travail.
    reelles = build(events, make_marks(population="REAL", **{"SYN-A": "12"}))
    assert reelles["mark_population"] == "REAL"

    # AUCUNE source : rien n'est qualifiable, donc rien n'est affirme.
    sans_marques = build(events, None)
    assert sans_marques["mark_population"] == MARK_POPULATION_UNQUALIFIED

    assert synthetiques["schema_version"] == PORTFOLIO_VALUATION_SCHEMA_VERSION
    assert synthetiques["lot_method"] == LOT_METHOD_VERSION


def test_compensated_pair_nets_out_of_the_lots() -> None:
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-A", quantity="10", price="100", amount="-1000"),
        make_event(
            2,
            "BUY_RECORDED",
            ticker="SYN-A",
            quantity="10",
            price="100",
            amount="1000",
            compensates=1,
            effective_at=T0,
        ),
    ]
    content = build(events, make_marks(**{"SYN-A": "120"}))

    assert content["coverage"]["compensation_pairs"] == 1
    assert content["coverage"]["lots_open"] == 0
    assert content["positions_by_currency"] == []  # net zero: nothing to value
    assert content["excluded_lots"] == []


def test_fifo_realized_pnl_with_calculation_lineage() -> None:
    events = [
        make_event(
            1,
            "BUY_RECORDED",
            ticker="SYN-A",
            quantity="10",
            price="100",
            amount="-1000",
            effective_at=T0,
        ),
        make_event(
            2,
            "BUY_RECORDED",
            ticker="SYN-A",
            quantity="10",
            price="110",
            amount="-1100",
            effective_at=T1,
        ),
        make_event(
            3,
            "SELL_RECORDED",
            ticker="SYN-A",
            quantity="12",
            price="120",
            amount="1440",
            fees="3",
            effective_at=T1,
        ),
    ]
    content = build(events, make_marks(**{"SYN-A": "130"}))
    group = content["positions_by_currency"][0]
    realized = group["realized"]
    assert realized["status"] == "OK"
    # FIFO: 10 from the first lot, 2 from the second.
    per_lot = {entry["lot_id"]: entry for entry in realized["lots"]}
    assert per_lot["ledger-1"]["quantity_closed"] == "10"
    assert per_lot["ledger-2"]["quantity_closed"] == "2"
    # total = 12*120 - (10*100 + 2*110) - 3
    assert realized["total_pnl"] == "217"
    assert realized["total_fees"] == "3"
    calculation = realized["calculation"]
    assert calculation["calculation_id"] == "portfolio.realized_pnl"
    assert calculation["input_hash"].startswith("sha256:")
    assert calculation["status"] == "OK"
    # Unrealized on the remaining 8 of lot 2 only.
    unrealized = group["unrealized"]
    assert [lot["lot_id"] for lot in unrealized["lots"]] == ["ledger-2"]
    assert unrealized["lots"][0]["quantity"] == "8"
    assert unrealized["total_unrealized"] == "160"
    assert unrealized["calculation"]["calculation_id"] == "portfolio.unrealized_pnl"


def test_concentration_weights_and_lineage() -> None:
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-A", quantity="10", price="100", amount="-1000"),
        make_event(2, "BUY_RECORDED", ticker="SYN-B", quantity="10", price="100", amount="-1000"),
    ]
    content = build(events, make_marks(**{"SYN-A": "30", "SYN-B": "10"}))
    concentration = content["positions_by_currency"][0]["concentration"]
    assert concentration["status"] == "OK"
    assert concentration["weights"] == {"SYN-A": "0.75", "SYN-B": "0.25"}
    assert concentration["total_value"] == "400"
    assert concentration["calculation"]["calculation_id"] == "portfolio.concentration"


def test_oversold_position_is_excluded_fail_closed() -> None:
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-A", quantity="5", price="100", amount="-500"),
        make_event(
            2,
            "SELL_RECORDED",
            ticker="SYN-A",
            quantity="6",
            price="120",
            amount="720",
            effective_at=T1,
        ),
        make_event(3, "BUY_RECORDED", ticker="SYN-B", quantity="2", price="10", amount="-20"),
    ]
    content = build(events, make_marks(**{"SYN-A": "120", "SYN-B": "12"}))
    assert content["coverage"]["invalid_positions"] == [
        {"ticker": "SYN-A", "currency": "SYN", "reason": REASON_OVERSOLD_POSITION}
    ]
    group = content["positions_by_currency"][0]
    # Only the sane position remains anywhere in the figures.
    assert [lot["lot_id"] for lot in group["unrealized"]["lots"]] == ["ledger-3"]
    assert group["realized"]["status"] == "ABSENT"


def test_invalid_position_event_is_listed_with_reason() -> None:
    events = [
        make_event(1, "BUY_RECORDED", quantity="5", price="100", amount="-500"),  # no ticker
        make_event(2, "DIVIDEND", amount="12"),
    ]
    content = build(events, make_marks())
    assert content["coverage"]["invalid_events"] == [
        {"event_id": 1, "reason": "missing_instrument_ticker"}
    ]
    assert content["coverage"]["cash_events"] == 1
    assert content["coverage"]["position_events"] == 1


def test_mark_currency_mismatch_excludes_the_lot() -> None:
    events = [
        make_event(
            1,
            "BUY_RECORDED",
            ticker="SYN-A",
            quantity="1",
            price="10",
            amount="-10",
            currency="USD",
        ),
    ]
    content = build(events, make_marks(**{"SYN-A": "12"}))  # mark currency SYN
    assert content["excluded_lots"] == [
        {
            "lot_id": "ledger-1",
            "ticker": "SYN-A",
            "currency": "USD",
            "reason": REASON_MARK_CURRENCY_MISMATCH,
        }
    ]


def test_builder_is_deterministic() -> None:
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-A", quantity="10", price="100", amount="-1000"),
        make_event(
            2,
            "SELL_RECORDED",
            ticker="SYN-A",
            quantity="4",
            price="110",
            amount="440",
            fees="1",
            effective_at=T1,
        ),
        make_event(3, "DEPOSIT", amount="5000"),
    ]
    marks = make_marks(**{"SYN-A": "115"})
    assert build(events, marks) == build(events, marks)


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError, match="naive"):
        build_portfolio_valuation_content(
            [],
            portfolio=PORTFOLIO,
            marks=None,
            now=datetime(2026, 8, 25, 12, 0, 0),  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
        )


def test_extract_marks_rejects_invalid_closes_fail_closed() -> None:
    content = {
        "as_of": NOW.isoformat(),
        "population": "SYNTHETIC",
        "sectors": [
            {
                "sector": "SYN-TECH",
                "tickers": [
                    {
                        "ticker": "SYN-A",
                        "last_close": "123.45",
                        "currency": "SYN",
                        "trading_day": "d",
                    },
                    {"ticker": "SYN-B", "last_close": "not-a-number", "currency": "SYN"},
                    {"ticker": "SYN-C", "last_close": "0", "currency": "SYN"},
                    {"ticker": "SYN-D"},
                ],
            }
        ],
    }
    marks = extract_marks_from_markets_content(content, snapshot_version=3)
    assert set(marks.closes) == {"SYN-A"}
    assert marks.closes["SYN-A"].close == Decimal("123.45")
    assert marks.invalid_tickers == ("SYN-B", "SYN-C", "SYN-D")
    # A lot on an invalid-mark ticker carries the invalid_mark reason.
    events = [
        make_event(1, "BUY_RECORDED", ticker="SYN-B", quantity="1", price="10", amount="-10"),
    ]
    valuation = build(events, marks)
    assert valuation["excluded_lots"][0]["reason"] == REASON_INVALID_MARK
