"""Portfolio valuation chain integration test (real PostgreSQL, migrations).

Chain under test: manual ledger writes through the EXISTING
``vertex_persistence.repository.ledger`` API + synthetic daily-quote
ingestion -> bounded worker run. The markets handler publishes
``markets_overview/global`` and — in the same transaction — enqueues one
``portfolio.valuation.refresh`` per portfolio, whose handler publishes
``portfolio_valuation/{portfolio_id}``: SYNTHETIC mark population, valued
lots against the published closes, fail-closed exclusion of a ticker
without a mark, compensation netting to zero, and publish-if-changed
replay semantics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from vertex_core.synthetic import (
    SYNTHETIC_MARKET_CURRENCY,
    SYNTHETIC_SECTOR_TICKERS,
    generate_daily_quote_envelopes,
)
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.ledger import (
    compensate_ledger_event,
    create_portfolio,
    record_ledger_event,
)
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.markets import SNAPSHOT_KIND_MARKETS
from vertex_worker.portfolio import (
    REASON_MISSING_MARK,
    SNAPSHOT_KIND_PORTFOLIO_VALUATION,
    TOPIC_PORTFOLIO_VALUATION_REFRESH,
)
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
BASE_TIME = NOW - timedelta(minutes=30)
OPENED_AT = NOW - timedelta(days=2)
SEED = 424242

TICKER_A = SYNTHETIC_SECTOR_TICKERS["SYN-TECH"][0]
TICKER_B = SYNTHETIC_SECTOR_TICKERS["SYN-ENER"][0]
TICKER_UNKNOWN = "SYN-NOWHERE-99"  # never quoted: must be excluded, never zero


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_PORTFOLIO_VALUATION_REFRESH in registry.topics
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def _drain_clean(runner: WorkerRunner, session_factory) -> None:
    runner.drain(max_batches=30)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0
    with session_factory() as session:
        remaining = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert remaining == 0


def _record_buy(session, portfolio_id: int, ticker: str, quantity: str, price: str) -> int:
    quantity_d = Decimal(quantity)
    price_d = Decimal(price)
    return record_ledger_event(
        session,
        portfolio_id=portfolio_id,
        kind="BUY_RECORDED",
        amount=-(quantity_d * price_d),
        currency=SYNTHETIC_MARKET_CURRENCY,
        fees=Decimal("0"),
        effective_at=OPENED_AT,
        recorded_at=OPENED_AT,
        instrument={"ticker": ticker},
        quantity=quantity_d,
        price=price_d,
        note="SYNTHETIC test fact recorded after an execution outside Vertex",
    )


def test_portfolio_valuation_chain_end_to_end(session_factory) -> None:
    # 1. Manual ledger: one portfolio, two marked lots, one unmarked lot.
    with session_factory() as session:
        portfolio_id = create_portfolio(
            session, name="main", base_currency="USD"
        )
        buy_a = _record_buy(session, portfolio_id, TICKER_A, "10", "100")
        _record_buy(session, portfolio_id, TICKER_B, "5", "50")
        _record_buy(session, portfolio_id, TICKER_UNKNOWN, "3", "20")
        session.commit()

    # 2. Synthetic quotes -> markets snapshot -> per-portfolio revaluation
    #    enqueued by the markets handler in the same transaction.
    envelopes = generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
    with session_factory() as session:
        for envelope in envelopes:
            ingest_envelope(session, envelope)
        session.commit()

    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)
    _drain_clean(runner, session_factory)

    with session_factory() as session:
        markets = get_current_snapshot(session, kind=SNAPSHOT_KIND_MARKETS, key="global")
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_PORTFOLIO_VALUATION, key=str(portfolio_id)
        )
    assert markets is not None and snapshot is not None
    content = snapshot.content

    assert content["schema_version"] == "vertex.portfolio-valuation/1.0"
    assert content["mark_population"] == "SYNTHETIC"
    assert content["as_of"] == NOW.isoformat()
    assert content["portfolio"] == {
        "id": portfolio_id,
        "name": "main",
        "base_currency": "USD",
    }
    assert content["marks"]["source"]["snapshot_version"] == markets.version

    # Marks come from the published closes; totals cover ONLY the valued lots.
    closes = {
        entry["ticker"]: Decimal(entry["last_close"])
        for sector in markets.content["sectors"]
        for entry in sector["tickers"]
    }
    group = content["positions_by_currency"][0]
    assert group["currency"] == SYNTHETIC_MARKET_CURRENCY
    valued = {lot["ticker"]: lot for lot in group["unrealized"]["lots"]}
    assert set(valued) == {TICKER_A, TICKER_B}
    assert Decimal(valued[TICKER_A]["mark"]) == closes[TICKER_A]
    expected_total = (closes[TICKER_A] - Decimal("100")) * 10 + (
        closes[TICKER_B] - Decimal("50")
    ) * 5
    assert Decimal(group["unrealized"]["total_unrealized"]) == expected_total
    assert group["unrealized"]["calculation"]["calculation_id"] == "portfolio.unrealized_pnl"
    assert group["concentration"]["status"] == "OK"

    # The unquoted ticker is EXCLUDED with its reason — never valued at zero.
    excluded = content["excluded_lots"]
    assert [(entry["ticker"], entry["reason"]) for entry in excluded] == [
        (TICKER_UNKNOWN, REASON_MISSING_MARK)
    ]
    assert content["coverage"]["lots_valued"] == 2
    assert content["coverage"]["lots_excluded"] == 1

    # 3. Compensation (the only correction path): the pair nets out of the lots.
    with session_factory() as session:
        compensate_ledger_event(
            session,
            event_id=buy_a,
            note="SYNTHETIC correction: wrong quantity typed",
            recorded_at=NOW,
        )
        enqueue_outbox(
            session,
            TOPIC_PORTFOLIO_VALUATION_REFRESH,
            {"portfolio_id": portfolio_id},
        )
        session.commit()
    _drain_clean(runner, session_factory)

    with session_factory() as session:
        revalued = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_PORTFOLIO_VALUATION, key=str(portfolio_id)
        )
    assert revalued is not None and revalued.version > snapshot.version
    content2 = revalued.content
    assert content2["coverage"]["compensation_pairs"] == 1
    group2 = content2["positions_by_currency"][0]
    tickers2 = {lot["ticker"] for lot in group2["unrealized"]["lots"]}
    assert TICKER_A not in tickers2  # net zero: the compensated buy is gone
    assert tickers2 == {TICKER_B}

    # 4. Replay with identical state: publish-if-changed keeps the version.
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_PORTFOLIO_VALUATION_REFRESH,
            {"portfolio_id": portfolio_id},
        )
        session.commit()
    _drain_clean(runner, session_factory)
    with session_factory() as session:
        replayed = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_PORTFOLIO_VALUATION, key=str(portfolio_id)
        )
    assert replayed is not None
    assert replayed.version == revalued.version
    assert replayed.content_hash == revalued.content_hash
