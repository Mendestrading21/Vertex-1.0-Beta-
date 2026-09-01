"""``ib_async`` implementation of the information-only IBKR port.

Safety invariants enforced here (ADR-004, docs/04-integrations/IBKR.md):

- loopback only: any host other than ``127.0.0.1`` is refused at construction;
- ``client_id`` is mandatory and non-zero (default 71, never the master 0);
- ``readonly=True`` is ALWAYS passed to ``IB.connectAsync``, and the startup
  fetch mask is empty so the session never requests account-scoped data;
- every outgoing observation is a ``vertex_core`` ``DataEnvelope[Any]`` with
  ``source='ibkr'``, the current connection epoch, aware UTC
  ``observed_at``/``received_at`` and an honest ``delay_status``;
- tick semantics follow the capability manifest: live option computations
  (ticks 10-13) and delayed ones (ticks 80-83) are DISTINCT observations and
  the reported market-data type is preserved verbatim;
- ``-1``/``-2``/NaN sentinels and absent values stay ``None`` — never zero;
- every envelope quality is DERIVED from the required fields actually
  received (``_derive_quality``), never assumed by the call site: an
  incomplete quote AND an incomplete option computation both degrade to
  ``PARTIAL`` so the snapshot gate can see it;
- an empty provider answer (zero rows, zero providers) is a real answer;
  a MISSING answer (``None``) is ``INSUFFICIENT_DATA`` — the two never merge;
- every subscription opened by a snapshot is cancelled in ``finally``.

This module is the only one importing ``ib_async``; domain code never does.
"""

from __future__ import annotations

import asyncio
import math
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from ib_async import IB
from ib_async.contract import Contract
from ib_async.ib import StartupFetch
from ib_async.objects import ScannerSubscription, WshEventData

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    canonical_json_hash,
)
from vertex_edge_ibkr.pacing import LineBudget
from vertex_edge_ibkr.port import (
    DELAYED_GREEK_TICKS,
    LIVE_GREEK_TICKS,
    BarObservation,
    BarsPayload,
    ContractQualificationError,
    ContractSpec,
    EdgeIbkrError,
    GreeksObservation,
    MarketDataSnapshotResult,
    NewsArticlePayload,
    NewsHeadline,
    NewsHeadlinesPayload,
    NewsProviderInfo,
    NewsProvidersPayload,
    OptionChainDefinition,
    ProviderErrorInfo,
    QuoteObservation,
    ScannerDefinition,
    ScannerPayload,
    ScannerRow,
    WshEventRequest,
    WshEventsPayload,
)
from vertex_edge_ibkr.state import ConnectionStateMachine

__all__ = [
    "CONTEXT_GREEK_FIELDS",
    "DEFAULT_CLIENT_ID",
    "LOOPBACK_HOST",
    "REQUIRED_GREEK_FIELDS",
    "IbAsyncInformationAdapter",
]

#: The only host this adapter will ever talk to.
LOOPBACK_HOST = "127.0.0.1"

#: Fixed, non-zero, non-master client id (docs/04-integrations/IBKR.md).
DEFAULT_CLIENT_ID = 71

#: Empty startup fetch mask: the session never pulls account-scoped data.
_NO_STARTUP_FETCH = StartupFetch(0)

#: Repli explicite pour une charge utile non encore cartographiee. Il reste
#: reconnaissable comme IBKR, ce que « 1 » n'etait pas.
_SCHEMA_VERSION = "ibkr.observation/1"

#: Un schema par NATURE de donnee. Le worker ne declenche ses pages que sur des
#: PREFIXES de schema (`is_daily_quote_schema`, `is_option_chain_schema`) : une
#: valeur unique pour tout rendait les donnees IBKR indiscernables et donc
#: invisibles a l'ecran.
_SCHEMA_BY_PAYLOAD: dict[str, str] = {
    "QuoteObservation": "ibkr.daily-quote/1",
    "GreeksObservation": "ibkr.option-computation/1",
    "BarsPayload": "ibkr.bars/1",
    "ScannerPayload": "ibkr.scanner/1",
    "NewsProvidersPayload": "ibkr.news-providers/1",
    "NewsHeadlinesPayload": "ibkr.news-headlines/1",
    "NewsArticlePayload": "ibkr.news-article/1",
    "WshEventsPayload": "ibkr.corporate-events/1",
    "OptionChainDefinition": "ibkr.option-chain/1",
}


def _schema_for(payload: Any) -> str:
    """Schema derive du type de la charge utile, repli explicite sinon."""
    return _SCHEMA_BY_PAYLOAD.get(type(payload).__name__, _SCHEMA_VERSION)
_SOURCE = "ibkr"

#: Delay status by reported IBKR market data type; anything else is UNKNOWN.
_DELAY_BY_TYPE = {
    1: DelayStatus.LIVE,
    2: DelayStatus.FROZEN,
    3: DelayStatus.DELAYED,
    4: DelayStatus.DELAYED_FROZEN,
}


#: Option-computation fields REQUIRED for a VALID greeks observation: the risk
#: set every downstream option evaluation consumes. Losing any one of them
#: makes the observation incomplete, so the envelope degrades to PARTIAL and
#: ``evaluate_snapshot_fresh_and_coherent`` reports PARTIAL_SNAPSHOT.
REQUIRED_GREEK_FIELDS: tuple[str, ...] = (
    "implied_volatility",
    "delta",
    "gamma",
    "vega",
    "theta",
)

#: Provider CONTEXT fields: IBKR legitimately omits them (no dividend, a
#: non-model basis), so their absence never downgrades the observation.
#: Requiring them would degrade nearly every real computation and turn the
#: degradation signal into noise. They still count as content: an observation
#: carrying only context is emitted, and derived INSUFFICIENT_DATA.
CONTEXT_GREEK_FIELDS: tuple[str, ...] = (
    "option_price",
    "pv_dividend",
    "underlying_price",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _derive_quality(required: tuple[Decimal | None, ...]) -> EnvelopeQuality:
    """Derive an envelope quality from the REQUIRED fields of one observation.

    The SAME rule serves every observation kind (top-of-book quote, option
    computation): all required fields present -> ``VALID``; some present ->
    ``PARTIAL`` (the snapshot gate degrades); none -> ``INSUFFICIENT_DATA``.
    A quality is always derived from the evidence actually received, never
    assumed by the call site (CONSTITUTION §4).
    """
    if not required:
        raise ValueError("a quality cannot be derived from an empty required-field set")
    if all(value is not None for value in required):
        return EnvelopeQuality.VALID
    if any(value is not None for value in required):
        return EnvelopeQuality.PARTIAL
    return EnvelopeQuality.INSUFFICIENT_DATA


def _is_unset(value: Any) -> bool:
    if value is None:
        return True
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return True
    return math.isnan(as_float) or math.isinf(as_float)


def _price(value: Any) -> Decimal | None:
    """Price sanitizer: NaN/inf/absent/-1 sentinel -> None, never zero."""
    if _is_unset(value):
        return None
    if float(value) == -1.0:
        return None
    return Decimal(str(value))


def _size(value: Any) -> Decimal | None:
    """Size/volume sanitizer: NaN/inf/absent/negative sentinel -> None."""
    if _is_unset(value):
        return None
    if float(value) < 0.0:
        return None
    return Decimal(str(value))


def _non_negative(value: Any) -> Decimal | None:
    """Non-negative metric sanitizer (volatilities): negative -> None."""
    if _is_unset(value):
        return None
    if float(value) < 0.0:
        return None
    return Decimal(str(value))


def _greek(value: Any, sentinel: float) -> Decimal | None:
    """Greek sanitizer: the protocol sentinel and NaN/inf stay None."""
    if _is_unset(value):
        return None
    if float(value) == sentinel:
        return None
    return Decimal(str(value))


def _halted(value: Any) -> bool | None:
    if _is_unset(value):
        return None
    numeric = float(value)
    if numeric < 0.0:
        return None
    return numeric >= 1.0


def _aware_or_none(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return None  # a naive provider timestamp is ambiguous: drop it
    return value.astimezone(UTC)


class IbAsyncInformationAdapter:
    """Read-only, loopback-only, information-only IBKR adapter.

    ``ib`` is injectable so protocol fakes drive every test; no network is
    ever required. ``state`` (the connection state machine) provides the
    connection epoch stamped on every envelope.
    """

    def __init__(
        self,
        *,
        ib: IB | None = None,
        host: str = LOOPBACK_HOST,
        port: int = 7497,
        client_id: int = DEFAULT_CLIENT_ID,
        state: ConnectionStateMachine | None = None,
        manage_connection_state: bool = True,
        clock: Callable[[], datetime] = _utc_now,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        connect_timeout_seconds: float = 4.0,
        snapshot_timeout_seconds: float = 5.0,
        snapshot_poll_seconds: float = 0.05,
        quote_stale_after_seconds: float = 10.0,
        bars_stale_after_seconds: float = 3600.0,
        reference_stale_after_seconds: float = 21600.0,
        rights: str = "IBKR_MARKET_DATA_DISPLAY_ONLY",
        line_budget: LineBudget | None = None,
        event_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        if host != LOOPBACK_HOST:
            raise ValueError(
                f"refused host {host!r}: this adapter only connects to {LOOPBACK_HOST}"
            )
        if not isinstance(client_id, int) or isinstance(client_id, bool) or client_id <= 0:
            raise ValueError("client_id must be a non-zero positive integer (never master 0)")
        if snapshot_timeout_seconds <= 0 or snapshot_poll_seconds <= 0:
            raise ValueError("snapshot timeouts must be strictly positive")
        self._ib = ib if ib is not None else IB()
        self._host = LOOPBACK_HOST
        self._port = port
        self._client_id = client_id
        self._state = state
        self._manage_connection_state = manage_connection_state
        self._clock = clock
        self._sleep = sleep
        self._connect_timeout = connect_timeout_seconds
        self._snapshot_timeout = snapshot_timeout_seconds
        self._snapshot_poll = snapshot_poll_seconds
        self._quote_stale = quote_stale_after_seconds
        self._bars_stale = bars_stale_after_seconds
        self._reference_stale = reference_stale_after_seconds
        self._rights = rights
        self._line_budget = line_budget
        self._event_id_factory = event_id_factory
        self._subscriptions: dict[str, tuple[Contract, list[ProviderErrorInfo]]] = {}
        error_event = getattr(self._ib, "errorEvent", None)
        if error_event is not None:
            error_event += self._on_error_event

    # -- connection --------------------------------------------------------

    async def connect(self) -> None:
        """Open the session: loopback, read-only, empty startup fetch mask."""
        if self._state is not None and self._manage_connection_state:
            self._state.begin_connect()
        try:
            await self._ib.connectAsync(
                host=self._host,
                port=self._port,
                clientId=self._client_id,
                timeout=self._connect_timeout,
                readonly=True,
                fetchFields=_NO_STARTUP_FETCH,
            )
        except Exception:
            if self._state is not None and self._manage_connection_state:
                self._state.on_connect_failed()
            raise
        if self._state is not None and self._manage_connection_state:
            self._state.on_connected()

    async def disconnect(self) -> None:
        self._ib.disconnect()
        if self._state is not None and self._manage_connection_state:
            self._state.stop()

    async def server_time(self) -> datetime:
        value = await self._ib.reqCurrentTimeAsync()
        aware = _aware_or_none(value)
        if aware is None:
            raise EdgeIbkrError("provider returned a naive server time; refusing ambiguity")
        return aware

    # -- identities --------------------------------------------------------

    async def qualify_contracts(self, *specs: ContractSpec) -> tuple[ContractSpec, ...]:
        contracts = [self._to_contract(spec) for spec in specs]
        qualified = await self._ib.qualifyContractsAsync(*contracts)
        results: list[ContractSpec] = []
        failures: list[int] = []
        for index, item in enumerate(qualified):
            if isinstance(item, Contract) and item.conId:
                results.append(self._from_contract(item))
            else:
                failures.append(index)
        if failures or len(results) != len(specs):
            raise ContractQualificationError(
                f"unqualified contract indexes: {failures or 'count mismatch'}"
            )
        return tuple(results)

    async def sec_def_opt_params(
        self, underlying: ContractSpec
    ) -> tuple[OptionChainDefinition, ...]:
        if underlying.con_id is None:
            raise ValueError("sec_def_opt_params requires an exact underlying con_id")
        chains = await self._ib.reqSecDefOptParamsAsync(
            underlying.symbol or "",
            "",
            underlying.sec_type,
            underlying.con_id,
        )
        definitions: list[OptionChainDefinition] = []
        for chain in chains or ():
            definitions.append(
                OptionChainDefinition(
                    exchange=chain.exchange,
                    underlying_con_id=int(chain.underlyingConId),
                    trading_class=chain.tradingClass,
                    multiplier=str(chain.multiplier),
                    expirations=tuple(sorted(chain.expirations)),
                    strikes=tuple(Decimal(str(strike)) for strike in sorted(chain.strikes)),
                )
            )
        return tuple(definitions)

    # -- market data snapshot ---------------------------------------------

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> MarketDataSnapshotResult:
        if market_data_type not in (1, 2, 3, 4):
            raise ValueError("market_data_type must be 1, 2, 3 or 4")
        if self._line_budget is not None:
            self._line_budget.acquire()  # explicit refusal beyond the 80% cap
        contract = self._to_contract(spec)
        subscription_id = self._event_id_factory()
        errors: list[ProviderErrorInfo] = []
        self._subscriptions[subscription_id] = (contract, errors)
        cancelled = False
        try:
            self._ib.reqMarketDataType(int(market_data_type))
            ticker = self._ib.reqMktData(
                contract,
                genericTickList=",".join(str(tick) for tick in generic_ticks),
                snapshot=False,
                regulatorySnapshot=False,
            )
            timeout = timeout_seconds if timeout_seconds is not None else self._snapshot_timeout
            waited = 0.0
            while not self._quote_ready(ticker) and waited < timeout and not errors:
                await self._sleep(self._snapshot_poll)
                waited += self._snapshot_poll
        finally:
            self._ib.cancelMktData(contract)
            cancelled = True
            self._subscriptions.pop(subscription_id, None)
            if self._line_budget is not None:
                self._line_budget.release()
        envelopes = self._build_snapshot_envelopes(spec, ticker, market_data_type)
        return MarketDataSnapshotResult(
            envelopes=envelopes,
            provider_errors=tuple(errors),
            requested_market_data_type=market_data_type,
            reported_market_data_type=self._reported_type(ticker),
            generic_ticks=tuple(generic_ticks),
            subscription_id=subscription_id,
            cancelled=cancelled,
        )

    async def cancel_subscription(self, subscription_id: str) -> bool:
        entry = self._subscriptions.pop(subscription_id, None)
        if entry is None:
            return False
        contract, _errors = entry
        self._ib.cancelMktData(contract)
        return True

    # -- historical bars ---------------------------------------------------

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
        if end is not None and _aware_or_none(end) is None:
            raise ValueError("end must be timezone-aware when present")
        bars = await self._ib.reqHistoricalDataAsync(
            self._to_contract(spec),
            endDateTime=end or "",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=2,
        )
        observations: list[BarObservation] = []
        for bar in bars or ():
            time_value = bar.date
            if isinstance(time_value, datetime):
                bar_time = _aware_or_none(time_value)
            else:
                bar_time = datetime(
                    time_value.year, time_value.month, time_value.day, tzinfo=UTC
                )
            if bar_time is None:
                continue  # ambiguous naive timestamp: refuse rather than guess
            observations.append(
                BarObservation(
                    time=bar_time,
                    open=_price(bar.open),
                    high=_price(bar.high),
                    low=_price(bar.low),
                    close=_price(bar.close),
                    volume=_size(bar.volume),
                    average=_price(bar.average),
                    bar_count=int(bar.barCount) if bar.barCount and bar.barCount > 0 else None,
                )
            )
        payload = BarsPayload(
            con_id=spec.con_id,
            bar_size=bar_size,
            what_to_show=what_to_show,
            use_rth=use_rth,
            bars=tuple(observations),
        )
        quality = EnvelopeQuality.VALID if observations else EnvelopeQuality.INSUFFICIENT_DATA
        return self._envelope(
            payload,
            con_id=spec.con_id,
            observed_at=observations[-1].time if observations else None,
            delay_status=DelayStatus.UNKNOWN,
            quality=quality,
            stale_seconds=self._bars_stale,
        )

    # -- scanner -----------------------------------------------------------

    async def scanner_run(self, definition: ScannerDefinition) -> DataEnvelope[Any]:
        subscription = ScannerSubscription(
            numberOfRows=definition.number_of_rows,
            instrument=definition.instrument,
            locationCode=definition.location_code,
            scanCode=definition.scan_code,
        )
        rows = await self._ib.reqScannerDataAsync(subscription)
        # ``None`` = the provider answered nothing; ``()`` = the scan matched
        # nothing. Absent and zero are never the same evidence.
        answered = rows is not None
        entries: list[ScannerRow] = []
        for row in rows or ():
            details = getattr(row, "contractDetails", None)
            contract = getattr(details, "contract", None)
            entries.append(
                ScannerRow(
                    rank=int(row.rank),
                    con_id=int(contract.conId) if contract is not None and contract.conId else None,
                    symbol=getattr(contract, "symbol", None) or None,
                )
            )
        payload = ScannerPayload(
            scan_code=definition.scan_code,
            instrument=definition.instrument,
            location_code=definition.location_code,
            rows=tuple(entries),
        )
        return self._envelope(
            payload,
            con_id=None,
            observed_at=None,
            delay_status=DelayStatus.UNKNOWN,
            quality=EnvelopeQuality.VALID if answered else EnvelopeQuality.INSUFFICIENT_DATA,
            stale_seconds=self._quote_stale,
        )

    # -- news --------------------------------------------------------------

    async def news_providers(self) -> DataEnvelope[Any]:
        providers = await self._ib.reqNewsProvidersAsync()
        # Same rule as the scanner: no answer at all is INSUFFICIENT_DATA, an
        # empty provider list is a real (VALID) answer.
        answered = providers is not None
        payload = NewsProvidersPayload(
            providers=tuple(
                NewsProviderInfo(code=item.code, name=item.name or None)
                for item in providers or ()
            )
        )
        return self._envelope(
            payload,
            con_id=None,
            observed_at=None,
            delay_status=DelayStatus.UNKNOWN,
            quality=EnvelopeQuality.VALID if answered else EnvelopeQuality.INSUFFICIENT_DATA,
            stale_seconds=self._reference_stale,
        )

    async def news_headlines(
        self,
        con_id: int,
        provider_codes: tuple[str, ...],
        *,
        start: str = "",
        end: str = "",
        max_results: int = 100,
    ) -> DataEnvelope[Any]:
        if con_id <= 0:
            raise ValueError("con_id must be strictly positive")
        if not (1 <= max_results <= 300):
            raise ValueError("max_results must be between 1 and 300")
        raw = await self._ib.reqHistoricalNewsAsync(
            con_id, ",".join(provider_codes), start, end, max_results
        )
        if raw is None:
            rows: tuple[Any, ...] = ()
        elif isinstance(raw, (list, tuple)):
            rows = tuple(raw)
        else:
            rows = (raw,)
        headlines = tuple(
            NewsHeadline(
                provider_code=row.providerCode,
                article_id=row.articleId,
                headline=row.headline,
                time=_aware_or_none(getattr(row, "time", None)),
            )
            for row in rows
        )
        payload = NewsHeadlinesPayload(con_id=con_id, headlines=headlines)
        quality = EnvelopeQuality.VALID if headlines else EnvelopeQuality.INSUFFICIENT_DATA
        return self._envelope(
            payload,
            con_id=con_id,
            observed_at=None,
            delay_status=DelayStatus.UNKNOWN,
            quality=quality,
            stale_seconds=self._reference_stale,
        )

    async def news_article(self, provider_code: str, article_id: str) -> DataEnvelope[Any]:
        if not provider_code or not article_id:
            raise ValueError("provider_code and article_id are required")
        article = await self._ib.reqNewsArticleAsync(provider_code, article_id)
        article_type = getattr(article, "articleType", None)
        payload = NewsArticlePayload(
            provider_code=provider_code,
            article_id=article_id,
            article_type=(
                int(article_type)
                if article_type is not None and article_type != ""
                else None
            ),
            text=getattr(article, "articleText", None) or "",
        )
        return self._envelope(
            payload,
            con_id=None,
            observed_at=None,
            delay_status=DelayStatus.UNKNOWN,
            quality=EnvelopeQuality.VALID
            if article is not None
            else EnvelopeQuality.INSUFFICIENT_DATA,
            stale_seconds=self._reference_stale,
        )

    # -- WSH events --------------------------------------------------------

    async def wsh_events(self, request: WshEventRequest) -> DataEnvelope[Any]:
        kwargs: dict[str, Any] = {
            "filter": "",
            # Market-event data only: every account-adjacent fill flag is
            # forced off, whatever the caller asked.
            "fillWatchlist": False,
            "fillPortfolio": False,
            "fillCompetitors": False,
            "startDate": request.start_date,
            "endDate": request.end_date,
        }
        if request.con_id is not None:
            kwargs["conId"] = request.con_id
        if request.total_limit is not None:
            kwargs["totalLimit"] = request.total_limit
        raw = await self._ib.getWshEventDataAsync(WshEventData(**kwargs))
        payload = WshEventsPayload(con_id=request.con_id, raw=raw or "")
        return self._envelope(
            payload,
            con_id=request.con_id,
            observed_at=None,
            delay_status=DelayStatus.UNKNOWN,
            quality=EnvelopeQuality.VALID if raw else EnvelopeQuality.INSUFFICIENT_DATA,
            stale_seconds=self._reference_stale,
        )

    # -- internals ---------------------------------------------------------

    def _on_error_event(
        self, req_id: Any, code: Any, message: Any = "", contract: Any = None, *extra: Any
    ) -> None:
        try:
            numeric_code = int(code)
        except (TypeError, ValueError):
            return
        if self._state is not None and numeric_code in (1100, 1101, 1102, 1300, 502):
            self._state.on_error_code(numeric_code)
        info = ProviderErrorInfo(
            code=numeric_code,
            message=str(message)[:200],
            req_id=int(req_id) if isinstance(req_id, int) else None,
        )
        for sub_contract, errors in self._subscriptions.values():
            contract_con_id = getattr(contract, "conId", 0)
            sub_con_id = getattr(sub_contract, "conId", -1)
            if contract is None or contract is sub_contract or (
                contract_con_id and contract_con_id == sub_con_id
            ):
                errors.append(info)

    def _quote_ready(self, ticker: Any) -> bool:
        return (
            not _is_unset(getattr(ticker, "bid", None))
            and not _is_unset(getattr(ticker, "ask", None))
            and not _is_unset(getattr(ticker, "last", None))
        )

    def _reported_type(self, ticker: Any) -> int | None:
        value = getattr(ticker, "marketDataType", None)
        if value in (1, 2, 3, 4):
            return int(value)
        return None

    def _delay_status(self, requested: int, reported: int | None) -> DelayStatus:
        if requested in (3, 4) and reported in (1, 2):
            # Contradictory evidence: asked delayed, told live. Never label
            # LIVE on doubt — the observation stays UNKNOWN (fail-closed).
            return DelayStatus.UNKNOWN
        if reported in _DELAY_BY_TYPE:
            return _DELAY_BY_TYPE[reported]
        return DelayStatus.UNKNOWN

    def _build_snapshot_envelopes(
        self, spec: ContractSpec, ticker: Any, requested_type: int
    ) -> tuple[DataEnvelope[Any], ...]:
        reported = self._reported_type(ticker)
        delay = self._delay_status(requested_type, reported)
        delayed_regime = requested_type in (3, 4) or reported in (3, 4)
        observed_at = _aware_or_none(getattr(ticker, "time", None))
        con_id = spec.con_id

        quote = QuoteObservation(
            con_id=con_id,
            symbol=spec.symbol,
            bid=_price(getattr(ticker, "bid", None)),
            bid_size=_size(getattr(ticker, "bidSize", None)),
            ask=_price(getattr(ticker, "ask", None)),
            ask_size=_size(getattr(ticker, "askSize", None)),
            last=_price(getattr(ticker, "last", None)),
            last_size=_size(getattr(ticker, "lastSize", None)),
            volume=_size(getattr(ticker, "volume", None)),
            close=_price(getattr(ticker, "close", None)),
            halted=_halted(getattr(ticker, "halted", None)),
            market_data_type=reported,
            call_volume=_size(getattr(ticker, "callVolume", None)),
            put_volume=_size(getattr(ticker, "putVolume", None)),
            call_open_interest=_size(getattr(ticker, "callOpenInterest", None)),
            put_open_interest=_size(getattr(ticker, "putOpenInterest", None)),
            historical_volatility_30d=_non_negative(getattr(ticker, "histVolatility", None)),
            average_option_volume=_size(getattr(ticker, "avOptionVolume", None)),
            option_implied_volatility_30d=_non_negative(getattr(ticker, "impliedVolatility", None)),
        )
        quality = _derive_quality((quote.bid, quote.ask, quote.last))
        envelopes = [
            self._envelope(
                quote,
                con_id=con_id,
                observed_at=observed_at,
                delay_status=delay,
                quality=quality,
                stale_seconds=self._quote_stale,
            )
        ]

        tick_map = DELAYED_GREEK_TICKS if delayed_regime else LIVE_GREEK_TICKS
        for basis, attr in (
            ("bid", "bidGreeks"),
            ("ask", "askGreeks"),
            ("last", "lastGreeks"),
            ("model", "modelGreeks"),
        ):
            computation = getattr(ticker, attr, None)
            if computation is None:
                continue
            observation = GreeksObservation(
                con_id=con_id,
                basis=basis,
                tick_type=tick_map[basis],
                market_data_type=reported,
                implied_volatility=_greek(getattr(computation, "impliedVol", None), -1.0),
                delta=_greek(getattr(computation, "delta", None), -2.0),
                gamma=_greek(getattr(computation, "gamma", None), -2.0),
                vega=_greek(getattr(computation, "vega", None), -2.0),
                theta=_greek(getattr(computation, "theta", None), -2.0),
                option_price=_greek(getattr(computation, "optPrice", None), -1.0),
                pv_dividend=_greek(getattr(computation, "pvDividend", None), -1.0),
                underlying_price=_greek(getattr(computation, "undPrice", None), -1.0),
            )
            has_content = any(
                getattr(observation, name) is not None
                for name in REQUIRED_GREEK_FIELDS + CONTEXT_GREEK_FIELDS
            )
            if not has_content:
                continue
            envelopes.append(
                self._envelope(
                    observation,
                    con_id=con_id,
                    observed_at=observed_at,
                    delay_status=delay,
                    # Derived exactly like the quote above: a computation with
                    # 7 sentinels out of 8 must degrade, never pass as complete.
                    quality=_derive_quality(
                        tuple(getattr(observation, name) for name in REQUIRED_GREEK_FIELDS)
                    ),
                    stale_seconds=self._quote_stale,
                )
            )
        return tuple(envelopes)

    def _envelope(
        self,
        payload: Any,
        *,
        con_id: int | None,
        observed_at: datetime | None,
        delay_status: DelayStatus,
        quality: EnvelopeQuality,
        stale_seconds: float,
    ) -> DataEnvelope[Any]:
        received_at = self._clock()
        if observed_at is not None and observed_at > received_at:
            observed_at = None  # clock skew: an impossible timestamp is dropped
        return DataEnvelope(
            event_id=self._event_id_factory(),
            schema_version=_schema_for(payload),
            source=_SOURCE,
            instrument_id=str(con_id) if con_id is not None else None,
            observed_at=observed_at,
            received_at=received_at,
            as_of=observed_at if observed_at is not None else received_at,
            stale_after=received_at + timedelta(seconds=stale_seconds),
            quality_status=quality,
            delay_status=delay_status,
            connection_epoch=self._state.connection_epoch if self._state is not None else None,
            rights=self._rights,
            payload_hash=canonical_json_hash(payload),
            payload=payload,
        )

    def _to_contract(self, spec: ContractSpec) -> Contract:
        contract = Contract(secType=spec.sec_type)
        if spec.con_id is not None:
            contract.conId = spec.con_id
        if spec.symbol:
            contract.symbol = spec.symbol
        if spec.exchange:
            contract.exchange = spec.exchange
        if spec.currency:
            contract.currency = spec.currency
        if spec.last_trade_date:
            contract.lastTradeDateOrContractMonth = spec.last_trade_date
        if spec.strike is not None:
            contract.strike = float(spec.strike)
        if spec.right:
            contract.right = spec.right
        if spec.trading_class:
            contract.tradingClass = spec.trading_class
        if spec.multiplier:
            contract.multiplier = spec.multiplier
        if spec.local_symbol:
            contract.localSymbol = spec.local_symbol
        return contract

    def _from_contract(self, contract: Contract) -> ContractSpec:
        strike = getattr(contract, "strike", 0.0)
        right = getattr(contract, "right", "") or None
        if right in ("CALL",):
            right = "C"
        elif right in ("PUT",):
            right = "P"
        return ContractSpec(
            sec_type=contract.secType,
            con_id=int(contract.conId) if contract.conId else None,
            symbol=contract.symbol or None,
            exchange=contract.exchange or None,
            currency=contract.currency or None,
            last_trade_date=contract.lastTradeDateOrContractMonth or None,
            strike=Decimal(str(strike)) if strike and strike > 0 else None,
            right=right if right in ("C", "P") else None,
            trading_class=contract.tradingClass or None,
            multiplier=contract.multiplier or None,
            local_symbol=contract.localSymbol or None,
        )
