"""SYNTHETIC protocol fakes for edge-ibkr tests.

Everything here is fabricated test data (status: SYNTHETIC). No network, no
real market payload, no account data, no clock dependency. The fakes mimic the
``ib_async`` protocol surface the adapter uses and the information-port
surface the probe uses — they never call any real IBKR capability.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    canonical_json_hash,
)

from vertex_edge_ibkr.port import (
    GreeksObservation,
    MarketDataSnapshotResult,
    ProviderError,
    ProviderErrorInfo,
    QuoteObservation,
)

NAN = float("nan")

#: Deterministic synthetic instants (no real clock in tests).
T0 = datetime(2026, 8, 28, 14, 0, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(seconds=1)


def fixed_clock(instant: datetime = T1):
    """Deterministic aware-UTC clock."""

    def _clock() -> datetime:
        return instant

    return _clock


class SteppingMonotonic:
    """Deterministic monotonic clock advancing ``step`` seconds per call."""

    def __init__(self, start: float = 0.0, step: float = 0.0) -> None:
        self.now = start
        self.step = step

    def __call__(self) -> float:
        value = self.now
        self.now += self.step
        return value


async def instant_sleep(_seconds: float) -> None:
    """Sleep replacement: yields control without consuming real time."""
    await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# ib_async protocol fakes
# ---------------------------------------------------------------------------


class FakeEvent:
    """Minimal ``eventkit``-style event: supports ``+=`` and ``emit``."""

    def __init__(self) -> None:
        self._handlers: list[Any] = []

    def __iadd__(self, handler: Any) -> "FakeEvent":
        self._handlers.append(handler)
        return self

    def emit(self, *args: Any) -> None:
        for handler in list(self._handlers):
            handler(*args)


class FakeComputation:
    """Synthetic option computation (mirrors ib_async ``OptionComputation``)."""

    def __init__(
        self,
        *,
        tickAttrib: int = 0,
        impliedVol: Optional[float] = None,
        delta: Optional[float] = None,
        optPrice: Optional[float] = None,
        pvDividend: Optional[float] = None,
        gamma: Optional[float] = None,
        vega: Optional[float] = None,
        theta: Optional[float] = None,
        undPrice: Optional[float] = None,
    ) -> None:
        self.tickAttrib = tickAttrib
        self.impliedVol = impliedVol
        self.delta = delta
        self.optPrice = optPrice
        self.pvDividend = pvDividend
        self.gamma = gamma
        self.vega = vega
        self.theta = theta
        self.undPrice = undPrice


class FakeTicker:
    """Synthetic ticker with ib_async field names and NaN 'unset' defaults."""

    def __init__(self, **overrides: Any) -> None:
        self.contract: Any = None
        self.time: Optional[datetime] = T0
        self.marketDataType = 1
        self.bid = NAN
        self.bidSize = NAN
        self.ask = NAN
        self.askSize = NAN
        self.last = NAN
        self.lastSize = NAN
        self.volume = NAN
        self.close = NAN
        self.halted = NAN
        self.callVolume = NAN
        self.putVolume = NAN
        self.callOpenInterest = NAN
        self.putOpenInterest = NAN
        self.histVolatility = NAN
        self.impliedVolatility = NAN
        self.avOptionVolume = NAN
        self.bidGreeks: Optional[FakeComputation] = None
        self.askGreeks: Optional[FakeComputation] = None
        self.lastGreeks: Optional[FakeComputation] = None
        self.modelGreeks: Optional[FakeComputation] = None
        for name, value in overrides.items():
            if not hasattr(self, name):
                raise AttributeError(f"unknown FakeTicker field {name!r}")
            setattr(self, name, value)


class FakeIB:
    """Protocol fake of the ``ib_async.IB`` surface the adapter touches.

    ``subscribe_errors`` is a list of ``(req_id, code, message)`` tuples
    emitted through ``errorEvent`` when ``reqMktData`` is called, exactly like
    a provider refusing a subscription.
    """

    def __init__(
        self,
        *,
        ticker: Optional[FakeTicker] = None,
        subscribe_errors: tuple[tuple[int, int, str], ...] = (),
        server_time: Optional[datetime] = T0,
        chains: tuple[Any, ...] = (),
        qualified: Optional[list[Any]] = None,
        bars: tuple[Any, ...] = (),
        scan_rows: tuple[Any, ...] = (),
        providers: tuple[Any, ...] = (),
        headlines: tuple[Any, ...] = (),
        article: Any = None,
        wsh_raw: str = "[]",
    ) -> None:
        self.errorEvent = FakeEvent()
        self.ticker = ticker if ticker is not None else FakeTicker()
        self.subscribe_errors = subscribe_errors
        self.server_time_value = server_time
        self.chains = chains
        self.qualified = qualified
        self.bars = bars
        self.scan_rows = scan_rows
        self.providers = providers
        self.headlines = headlines
        self.article = article
        self.wsh_raw = wsh_raw
        # Recorded interactions
        self.connect_calls: list[dict[str, Any]] = []
        self.disconnect_calls = 0
        self.market_data_type_requests: list[int] = []
        self.subscriptions: list[tuple[Any, str]] = []
        self.cancellations: list[Any] = []
        self.wsh_requests: list[Any] = []

    # -- session -----------------------------------------------------------

    async def connectAsync(self, **kwargs: Any) -> None:
        self.connect_calls.append(dict(kwargs))

    def disconnect(self) -> None:
        self.disconnect_calls += 1

    async def reqCurrentTimeAsync(self) -> Optional[datetime]:
        return self.server_time_value

    # -- market data -------------------------------------------------------

    def reqMarketDataType(self, market_data_type: int) -> None:
        self.market_data_type_requests.append(market_data_type)

    def reqMktData(
        self,
        contract: Any,
        genericTickList: str = "",
        snapshot: bool = False,
        regulatorySnapshot: bool = False,
    ) -> FakeTicker:
        self.subscriptions.append((contract, genericTickList))
        self.ticker.contract = contract
        for req_id, code, message in self.subscribe_errors:
            self.errorEvent.emit(req_id, code, message, contract)
        return self.ticker

    def cancelMktData(self, contract: Any) -> bool:
        self.cancellations.append(contract)
        return True

    # -- reference / history / news / wsh ---------------------------------

    async def qualifyContractsAsync(self, *contracts: Any) -> list[Any]:
        if self.qualified is not None:
            return list(self.qualified)
        return list(contracts)

    async def reqSecDefOptParamsAsync(
        self, underlyingSymbol: str, futFopExchange: str, underlyingSecType: str, underlyingConId: int
    ) -> tuple[Any, ...]:
        return self.chains

    async def reqHistoricalDataAsync(self, contract: Any, **kwargs: Any) -> tuple[Any, ...]:
        return self.bars

    async def reqScannerDataAsync(self, subscription: Any, *args: Any) -> tuple[Any, ...]:
        return self.scan_rows

    async def reqNewsProvidersAsync(self) -> tuple[Any, ...]:
        return self.providers

    async def reqHistoricalNewsAsync(self, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
        return self.headlines

    async def reqNewsArticleAsync(self, *args: Any, **kwargs: Any) -> Any:
        return self.article

    async def getWshEventDataAsync(self, data: Any) -> str:
        self.wsh_requests.append(data)
        return self.wsh_raw


# ---------------------------------------------------------------------------
# Information-port fake (for the entitlement probe)
# ---------------------------------------------------------------------------


def make_envelope(
    payload: Any,
    *,
    con_id: Optional[int] = None,
    observed_at: Optional[datetime] = T0,
    received_at: datetime = T1,
    delay: DelayStatus = DelayStatus.LIVE,
    quality: EnvelopeQuality = EnvelopeQuality.VALID,
    epoch: int = 1,
) -> DataEnvelope:
    return DataEnvelope(
        event_id=f"evt-{id(payload) & 0xFFFF:x}",
        schema_version="1",
        source="ibkr",
        instrument_id=str(con_id) if con_id is not None else None,
        observed_at=observed_at,
        received_at=received_at,
        as_of=observed_at if observed_at is not None else received_at,
        stale_after=received_at + timedelta(seconds=60),
        quality_status=quality,
        delay_status=delay,
        connection_epoch=epoch,
        rights="SYNTHETIC_TEST",
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


def make_snapshot_result(
    envelopes: tuple[DataEnvelope, ...],
    *,
    errors: tuple[ProviderErrorInfo, ...] = (),
    requested: int = 1,
    reported: Optional[int] = 1,
    generic: tuple[int, ...] = (),
    subscription_id: str = "sub-1",
    cancelled: bool = True,
) -> MarketDataSnapshotResult:
    return MarketDataSnapshotResult(
        envelopes=envelopes,
        provider_errors=errors,
        requested_market_data_type=requested,
        reported_market_data_type=reported,
        generic_ticks=generic,
        subscription_id=subscription_id,
        cancelled=cancelled,
    )


def full_quote(con_id: int, *, market_data_type: int = 1, with_generics: bool = False) -> QuoteObservation:
    generic_values: dict[str, Any] = {}
    if with_generics:
        generic_values = {
            "call_volume": Decimal("1200"),
            "put_volume": Decimal("900"),
            "call_open_interest": Decimal("5000"),
            "put_open_interest": Decimal("4000"),
            "historical_volatility_30d": Decimal("0.22"),
            "average_option_volume": Decimal("1500"),
            "option_implied_volatility_30d": Decimal("0.25"),
        }
    return QuoteObservation(
        con_id=con_id,
        bid=Decimal("100.10"),
        ask=Decimal("100.20"),
        last=Decimal("100.15"),
        volume=Decimal("12345"),
        market_data_type=market_data_type,
        **generic_values,
    )


def full_greeks(con_id: int, *, tick_type: int, basis: str = "model", market_data_type: int = 1) -> GreeksObservation:
    return GreeksObservation(
        con_id=con_id,
        basis=basis,
        tick_type=tick_type,
        market_data_type=market_data_type,
        implied_volatility=Decimal("0.31"),
        delta=Decimal("0.55"),
        gamma=Decimal("0.04"),
        vega=Decimal("0.12"),
        theta=Decimal("-0.05"),
    )


class FakeInformationPort:
    """Scriptable information port for probe tests.

    Behaviors are values, exception instances, or ``("hang", seconds)``
    markers per method. Snapshot behaviors are keyed by
    ``(con_id, market_data_type)``.
    """

    def __init__(
        self,
        *,
        server_time_behavior: Any = T0,
        chain_behavior: Any = ("chain",),
        snapshot_behaviors: Optional[dict[tuple[int, int], Any]] = None,
    ) -> None:
        self.server_time_behavior = server_time_behavior
        self.chain_behavior = chain_behavior
        self.snapshot_behaviors = snapshot_behaviors or {}
        self.snapshot_calls: list[tuple[int, int, tuple[int, ...]]] = []
        self.cancelled_subscriptions: list[str] = []

    async def _apply(self, behavior: Any) -> Any:
        if isinstance(behavior, tuple) and len(behavior) == 2 and behavior[0] == "hang":
            await asyncio.sleep(behavior[1])
            raise AssertionError("hang behavior should always be cut by a timeout")
        if isinstance(behavior, tuple) and len(behavior) == 3 and behavior[0] == "slow":
            await asyncio.sleep(behavior[1])
            return behavior[2]
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior

    async def server_time(self) -> datetime:
        return await self._apply(self.server_time_behavior)

    async def sec_def_opt_params(self, underlying: Any) -> tuple[Any, ...]:
        return await self._apply(self.chain_behavior)

    async def market_data_snapshot(
        self,
        spec: Any,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: Optional[float] = None,
    ) -> MarketDataSnapshotResult:
        self.snapshot_calls.append((spec.con_id, market_data_type, tuple(generic_ticks)))
        key = (spec.con_id, market_data_type)
        if key not in self.snapshot_behaviors:
            raise ProviderError(9999, "unscripted snapshot in fake")
        return await self._apply(self.snapshot_behaviors[key])

    async def cancel_subscription(self, subscription_id: str) -> bool:
        self.cancelled_subscriptions.append(subscription_id)
        return True
