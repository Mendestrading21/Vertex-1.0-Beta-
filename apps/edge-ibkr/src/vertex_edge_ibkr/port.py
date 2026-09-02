"""Information-only IBKR port: the ONLY surface Vertex may use against IBKR.

``IbkrInformationPort`` exposes exclusively: connection/server time, contract
qualification, option chain definitions, market-data snapshots (quotes),
historical bars, scanner runs, news (providers/headlines/article), WSH events
and data-subscription cancellation. Nothing else exists on the port — no
order, account, position, P&L, execution or exercise capability, per ADR-004
and ``manifests/forbidden-capabilities.yaml``.

Shared semantic constants (tick-type maps, market-data types) live here so the
adapter and the entitlement probe interpret the protocol identically.

Fail-closed rules carried by these types:

- absent, sentinel or refused values stay ``None``, never zero;
- all datetimes are timezone-aware UTC;
- live and delayed evidence never share a tick identity (10-13 vs 80-83).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from vertex_core.contracts import (
    ContractModel,
    DataEnvelope,
    FiniteDecimal,
    NonEmptyStr,
    UtcDatetime,
)

__all__ = [
    "ALLOWED_PORT_METHODS",
    "DELAYED_GREEK_TICKS",
    "DELAYED_QUOTE_TICKS",
    "LIVE_GREEK_TICKS",
    "LIVE_QUOTE_TICKS",
    "MARKET_DATA_TYPE_DELAY",
    "BarObservation",
    "BarsPayload",
    "ContractQualificationError",
    "ContractSpec",
    "EdgeIbkrError",
    "GreeksObservation",
    "IbkrInformationPort",
    "MarketDataSnapshotResult",
    "NewsArticlePayload",
    "NewsHeadline",
    "NewsHeadlinesPayload",
    "NewsProviderInfo",
    "NewsProvidersPayload",
    "OptionChainDefinition",
    "ProviderError",
    "ProviderErrorInfo",
    "QuoteObservation",
    "ScannerDefinition",
    "ScannerPayload",
    "ScannerRow",
    "WshEventRequest",
    "WshEventsPayload",
]

# --------------------------------------------------------------------------
# Protocol semantics shared by adapter and probe (IBKR tick-type documentation)
# --------------------------------------------------------------------------

#: Live/frozen top-of-book tick ids (IBKR default ticks 0-9).
LIVE_QUOTE_TICKS: dict[str, int] = {
    "bid_size": 0,
    "bid": 1,
    "ask": 2,
    "ask_size": 3,
    "last": 4,
    "last_size": 5,
    "volume": 8,
    "close": 9,
}

#: Delayed top-of-book tick ids (IBKR delayed ticks 66-76).
DELAYED_QUOTE_TICKS: dict[str, int] = {
    "bid": 66,
    "ask": 67,
    "last": 68,
    "bid_size": 69,
    "ask_size": 70,
    "last_size": 71,
    "volume": 74,
    "close": 75,
}

#: Live option computation tick ids per basis (never mixed with delayed).
LIVE_GREEK_TICKS: dict[str, int] = {"bid": 10, "ask": 11, "last": 12, "model": 13}

#: Delayed option computation tick ids per basis (never mixed with live).
DELAYED_GREEK_TICKS: dict[str, int] = {"bid": 80, "ask": 81, "last": 82, "model": 83}

#: IBKR market data type -> canonical delay wording (DataEnvelope.delay_status).
MARKET_DATA_TYPE_DELAY: dict[int, str] = {
    1: "LIVE",
    2: "FROZEN",
    3: "DELAYED",
    4: "DELAYED_FROZEN",
}

#: The complete, closed public surface of the information port.
ALLOWED_PORT_METHODS: tuple[str, ...] = (
    "connect",
    "disconnect",
    "server_time",
    "qualify_contracts",
    "sec_def_opt_params",
    "market_data_snapshot",
    "historical_bars",
    "scanner_run",
    "news_providers",
    "news_headlines",
    "news_article",
    "wsh_events",
    "cancel_subscription",
)


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class EdgeIbkrError(Exception):
    """Base error of the edge-ibkr package."""


class ProviderError(EdgeIbkrError):
    """A provider (TWS/IB Gateway) error surfaced to the caller.

    ``message`` must already be redacted upstream: no account identifier, no
    secret, no raw payload. ``code`` is the stable IBKR error code.
    """

    def __init__(self, code: int, message: str = "") -> None:
        super().__init__(f"provider error {code}: {message}")
        self.code = code
        self.message = message


class ContractQualificationError(EdgeIbkrError):
    """One or more contracts could not be qualified (fail-closed, no guess)."""


# --------------------------------------------------------------------------
# Request shapes
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContractSpec:
    """Exact contract identity used for every IBKR request.

    A symbol alone is never an identity; probes and snapshots should carry
    ``con_id``. ``strike`` stays ``None`` when the instrument has none — it is
    never encoded as zero.
    """

    sec_type: str
    con_id: int | None = None
    symbol: str | None = None
    exchange: str | None = None
    currency: str | None = None
    last_trade_date: str | None = None
    strike: Decimal | None = None
    right: str | None = None
    trading_class: str | None = None
    multiplier: str | None = None
    local_symbol: str | None = None

    def __post_init__(self) -> None:
        if not self.sec_type:
            raise ValueError("sec_type is required")
        if self.right is not None and self.right not in {"C", "P"}:
            raise ValueError("right must be 'C' or 'P' when present")
        if self.strike is not None and self.strike <= 0:
            raise ValueError("strike must be strictly positive when present")
        if self.con_id is not None and self.con_id <= 0:
            raise ValueError("con_id must be strictly positive when present")


@dataclass(frozen=True, slots=True)
class ScannerDefinition:
    """Bounded scanner request: at most 50 rows per scan (integration doc)."""

    instrument: str
    location_code: str
    scan_code: str
    number_of_rows: int = 50

    def __post_init__(self) -> None:
        if not (1 <= self.number_of_rows <= 50):
            raise ValueError("number_of_rows must be between 1 and 50")
        if not (self.instrument and self.location_code and self.scan_code):
            raise ValueError("instrument, location_code and scan_code are required")


@dataclass(frozen=True, slots=True)
class WshEventRequest:
    """Wall Street Horizon event request. Market-event data only.

    The adapter never fills anything from broker account data; the underlying
    request is always sent with every account-adjacent fill flag disabled.
    """

    con_id: int | None = None
    start_date: str = ""
    end_date: str = ""
    total_limit: int | None = None

    def __post_init__(self) -> None:
        if self.con_id is not None and self.con_id <= 0:
            raise ValueError("con_id must be strictly positive when present")
        if self.total_limit is not None and self.total_limit <= 0:
            raise ValueError("total_limit must be strictly positive when present")


# --------------------------------------------------------------------------
# Observation payloads (strict, immutable vertex_core contract models)
# --------------------------------------------------------------------------


class QuoteObservation(ContractModel):
    """Top-of-book snapshot plus optional generic-tick evidence.

    Every value is optional: an absent, sentinel or refused field is ``None``,
    never zero. ``market_data_type`` is the type actually reported by the
    provider callback, preserved verbatim.
    """

    con_id: int | None = None
    symbol: NonEmptyStr | None = None
    bid: FiniteDecimal | None = None
    bid_size: FiniteDecimal | None = None
    ask: FiniteDecimal | None = None
    ask_size: FiniteDecimal | None = None
    last: FiniteDecimal | None = None
    last_size: FiniteDecimal | None = None
    volume: FiniteDecimal | None = None
    close: FiniteDecimal | None = None
    halted: bool | None = None
    market_data_type: int | None = None
    # Generic-tick evidence (underlying-scoped; provider semantics, descriptive
    # only — never directional):
    call_volume: FiniteDecimal | None = None  # tick 29 (generic 100)
    put_volume: FiniteDecimal | None = None  # tick 30 (generic 100)
    call_open_interest: FiniteDecimal | None = None  # tick 27 (generic 101)
    put_open_interest: FiniteDecimal | None = None  # tick 28 (generic 101)
    historical_volatility_30d: FiniteDecimal | None = None  # tick 23 (generic 104)
    average_option_volume: FiniteDecimal | None = None  # tick 87 (generic 105)
    option_implied_volatility_30d: FiniteDecimal | None = None  # tick 24 (generic 106)


class GreeksObservation(ContractModel):
    """One option-computation observation for ONE basis (bid/ask/last/model).

    Live (ticks 10-13) and delayed (ticks 80-83) computations are distinct
    observations and are never merged: ``tick_type`` states which one this is.
    Provider greeks are a provider observation, never Vertex greeks.
    """

    con_id: int | None = None
    basis: NonEmptyStr
    tick_type: int
    market_data_type: int | None = None
    implied_volatility: FiniteDecimal | None = None
    delta: FiniteDecimal | None = None
    gamma: FiniteDecimal | None = None
    vega: FiniteDecimal | None = None
    theta: FiniteDecimal | None = None
    option_price: FiniteDecimal | None = None
    pv_dividend: FiniteDecimal | None = None
    underlying_price: FiniteDecimal | None = None


class BarObservation(ContractModel):
    """One historical bar. Sentinel/absent values stay ``None``."""

    time: UtcDatetime
    open: FiniteDecimal | None = None
    high: FiniteDecimal | None = None
    low: FiniteDecimal | None = None
    close: FiniteDecimal | None = None
    volume: FiniteDecimal | None = None
    average: FiniteDecimal | None = None
    bar_count: int | None = None


class BarsPayload(ContractModel):
    """Historical bars for one exact contract."""

    con_id: int | None = None
    bar_size: NonEmptyStr
    what_to_show: NonEmptyStr
    use_rth: bool
    bars: tuple[BarObservation, ...]


class ScannerRow(ContractModel):
    """One scanner rank entry (candidate universe only, re-validated later)."""

    rank: int
    con_id: int | None = None
    symbol: NonEmptyStr | None = None


class ScannerPayload(ContractModel):
    """One bounded scanner run result."""

    scan_code: NonEmptyStr
    instrument: NonEmptyStr
    location_code: NonEmptyStr
    rows: tuple[ScannerRow, ...]


class NewsProviderInfo(ContractModel):
    """One news provider the technical user is entitled to."""

    code: NonEmptyStr
    name: NonEmptyStr | None = None


class NewsProvidersPayload(ContractModel):
    """Entitled news providers, as reported by the API."""

    providers: tuple[NewsProviderInfo, ...]


class NewsHeadline(ContractModel):
    """One historical news headline with provider and article identity.

    ``time`` ne porte QUE des instants sans ambiguïté. ``time_unzoned`` porte
    l'horodatage du fournisseur quand celui-ci arrive sans fuseau : mesuré le
    2026-09-01, IBKR date toutes ses dépêches mais sans zone. Le jeter perdait
    l'information ; le traiter comme de l'UTC serait une supposition. Il est
    donc conservé sous un nom qui dit son défaut.
    """

    provider_code: NonEmptyStr
    article_id: NonEmptyStr
    headline: NonEmptyStr
    time: UtcDatetime | None = None
    time_unzoned: datetime | None = None


class NewsHeadlinesPayload(ContractModel):
    """Historical headlines for one contract."""

    con_id: int
    headlines: tuple[NewsHeadline, ...]


class NewsArticlePayload(ContractModel):
    """One news article body (only when the entitlement allows it)."""

    provider_code: NonEmptyStr
    article_id: NonEmptyStr
    article_type: int | None = None
    text: str


class WshEventsPayload(ContractModel):
    """Raw WSH event data (JSON string) for one bounded request."""

    con_id: int | None = None
    raw: str


class OptionChainDefinition(ContractModel):
    """One ``reqSecDefOptParams`` result row.

    Definition only: proves chain-definition capability, never quote
    entitlement nor chain quote coverage. Two trading classes sharing an
    expiry stay distinct rows.
    """

    exchange: NonEmptyStr
    underlying_con_id: int
    trading_class: NonEmptyStr
    multiplier: NonEmptyStr
    expirations: tuple[NonEmptyStr, ...]
    strikes: tuple[FiniteDecimal, ...]


# --------------------------------------------------------------------------
# Composite results
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderErrorInfo:
    """A provider error observed during a request window (redacted summary)."""

    code: int
    message: str = ""
    req_id: int | None = None


@dataclass(frozen=True, slots=True)
class MarketDataSnapshotResult:
    """Everything one bounded market-data snapshot produced.

    ``envelopes`` holds distinct ``DataEnvelope`` observations (quote payload,
    then one greeks payload per basis). ``provider_errors`` lists every
    provider error attributable to this request — partial data plus an error
    can coexist and both stay visible.
    """

    envelopes: tuple[DataEnvelope[Any], ...]
    provider_errors: tuple[ProviderErrorInfo, ...]
    requested_market_data_type: int
    reported_market_data_type: int | None
    generic_ticks: tuple[int, ...]
    subscription_id: str
    cancelled: bool

    def quote(self) -> QuoteObservation | None:
        """The quote observation of this snapshot, when one was produced."""
        for envelope in self.envelopes:
            if isinstance(envelope.payload, QuoteObservation):
                return envelope.payload
        return None

    def greeks(self) -> tuple[GreeksObservation, ...]:
        """Every distinct greeks observation of this snapshot."""
        return tuple(
            envelope.payload
            for envelope in self.envelopes
            if isinstance(envelope.payload, GreeksObservation)
        )


# --------------------------------------------------------------------------
# The port
# --------------------------------------------------------------------------


@runtime_checkable
class IbkrInformationPort(Protocol):
    """The only IBKR surface Vertex is allowed to use (information only).

    Implementations MUST be read-only at the API level (``readonly=True``),
    loopback-only, and expose nothing beyond these methods. Any order,
    account, position, P&L, execution or exercise capability is forbidden by
    ADR-004 and enforced by AST scans in CI and tests.
    """

    async def connect(self) -> None:
        """Open the read-only loopback session (fail-closed on any doubt)."""
        ...

    async def disconnect(self) -> None:
        """Close the session and release every data line."""
        ...

    async def server_time(self) -> datetime:
        """Provider server time as an aware UTC datetime."""
        ...

    async def qualify_contracts(self, *specs: ContractSpec) -> tuple[ContractSpec, ...]:
        """Resolve specs into fully qualified identities; unresolved fails."""
        ...

    async def sec_def_opt_params(
        self, underlying: ContractSpec
    ) -> tuple[OptionChainDefinition, ...]:
        """Option chain definitions for one exact underlying (definition only)."""
        ...

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> MarketDataSnapshotResult:
        """Bounded quote/computation snapshot; always cancels its data line."""
        ...

    async def historical_bars(
        self,
        spec: ContractSpec,
        *,
        end: datetime | None = None,
        duration: str = "1 D",
        bar_size: str = "1 hour",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
    ) -> DataEnvelope[Any]:
        """Historical bars for one exact contract (separate pacing applies)."""
        ...

    async def scanner_run(self, definition: ScannerDefinition) -> DataEnvelope[Any]:
        """One bounded scanner run (candidates only, max 50 rows)."""
        ...

    async def news_providers(self) -> DataEnvelope[Any]:
        """News providers the technical user is entitled to."""
        ...

    async def news_headlines(
        self,
        con_id: int,
        provider_codes: tuple[str, ...],
        *,
        start: str = "",
        end: str = "",
        max_results: int = 100,
    ) -> DataEnvelope[Any]:
        """Historical headlines for one contract, entitlement permitting."""
        ...

    async def news_article(self, provider_code: str, article_id: str) -> DataEnvelope[Any]:
        """One article body, only when the entitlement allows restitution."""
        ...

    async def wsh_events(self, request: WshEventRequest) -> DataEnvelope[Any]:
        """WSH corporate event data (one bounded request at a time)."""
        ...

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel one active market-data subscription line; True if it existed."""
        ...
