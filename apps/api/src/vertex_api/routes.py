"""HTTP routes of the Vertex One API.

- ``GET /api/v1/health`` — public liveness, no sensitive data;
- ``POST /api/v1/advice/preview`` — protected; a pure pass-through to the
  single ``AdviceEngine`` of ``vertex_core.decision`` (the API computes no
  score, no gate and no verdict of its own);
- ``GET /api/v1/system/engine`` — protected; engine/contract versions only;
- ``GET /api/v1/today/attention`` — protected; the LAST published
  ``attention/global`` snapshot verbatim, or an honest empty state;
- ``GET /api/v1/markets/overview`` — protected; the LAST published
  ``markets_overview/global`` snapshot verbatim, or an honest empty state;
- ``GET /api/v1/system/capabilities`` — protected; the declared capability
  manifest crossed with the latest persisted probe snapshot, plus health;
- ``GET /api/v1/events/stream`` — protected; signal-only SSE
  (``{resource, version}`` head changes and keepalive pings, no business
  data).

Protected routes depend on :func:`vertex_api.auth.require_session` (LOT-09):
a valid WebAuthn session cookie — plus the CSRF double-submit header on every
mutation — or a generic 401 with code ``AUTH_REQUIRED``, fail-closed.
"""

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from vertex_api.ai_explain import (
    ERROR_NO_SNAPSHOT_FOR_SUBJECT,
    SUBJECT_SNAPSHOT_KINDS,
    AiAnswer,
    AiExplainRequest,
    AiStatusResponse,
    build_ai_answer,
)
from vertex_api.auth import require_session
from vertex_api.calendar import (
    SNAPSHOT_KIND_CALENDAR,
    CalendarResponse,
    build_calendar_response,
    validate_window,
)
from vertex_api.capability_manifest import CapabilityManifest
from vertex_api.events import StreamSettings, get_stream_settings, snapshot_event_stream
from vertex_api.follow_up import (
    ERROR_IDEMPOTENCY_KEY_REUSED,
    ERROR_UNKNOWN_PORTFOLIO,
    ERROR_UNKNOWN_THESIS,
    SNAPSHOT_KEY_REVIEW_QUEUE,
    SNAPSHOT_KIND_REVIEW_QUEUE,
    CreateThesisRequest,
    CreateThesisResponse,
    DbFollowUpGateway,
    FollowUpGateway,
    FollowUpQueueResponse,
    ThesisRevisionRequest,
    ThesisRevisionResponse,
    build_follow_up_queue_response,
)
from vertex_api.opportunities import (
    SNAPSHOT_KIND_OPPORTUNITIES,
    OpportunitiesResponse,
    build_opportunities_response,
)
from vertex_api.performance import (
    SNAPSHOT_KIND_PERFORMANCE,
    PerformanceExportResponse,
    PerformanceSnapshotResponse,
    build_performance_export,
    build_performance_response,
)
from vertex_api.portfolio import (
    ERROR_ALREADY_COMPENSATED,
    ERROR_ECHO_HASH_MISMATCH,
    ERROR_EFFECTIVE_AT_IN_FUTURE,
    ERROR_IMPORT_ROW_INVALID,
    ERROR_UNKNOWN_TRANSACTION,
    EXPORT_SCHEMA_VERSION,
    CompensateTransactionRequest,
    CompensateTransactionResponse,
    CsvImportError,
    CsvImportPreviewRequest,
    DbPortfolioGateway,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    PortfolioGateway,
    PortfolioResponse,
    RecordTransactionRequest,
    RecordTransactionResponse,
    build_portfolio_response,
    detect_potential_duplicates,
    parse_import_csv,
    render_export_csv,
    validate_import_fields,
)
from vertex_api.risk import (
    SNAPSHOT_KIND_RISK,
    RiskMatrixResponse,
    build_risk_response,
)
from vertex_api.schemas import (
    AdvicePreviewRequest,
    AnalysisResponse,
    AttentionSnapshotResponse,
    EngineInfoResponse,
    HealthResponse,
    MarketsOverviewResponse,
    OptionChainResponse,
    SecFundamentalsResponse,
    SystemCapabilitiesResponse,
)
from vertex_api.simulation import (
    SimulationPreviewRequest,
    SimulationPreviewResponse,
    SimulationRejectedError,
    run_simulation_preview,
)
from vertex_api.snapshot_reader import Clock, SnapshotReader, get_clock, get_snapshot_reader
from vertex_api.snapshot_views import (
    build_analysis_response,
    build_attention_response,
    build_capabilities_response,
    build_markets_overview_response,
    build_option_chain_response,
    build_sec_fundamentals_response,
)
from vertex_core.calculations.options import OptionInputError
from vertex_core.contracts.decision import AdviceResult
from vertex_core.decision import GATE_VERSIONS, AdviceEngine
from vertex_core.version import ENGINE_VERSION

__all__ = [
    "get_advice_engine",
    "get_capability_manifest",
    "parse_advice_preview_request",
    "protected_router",
    "public_router",
]

SNAPSHOT_KIND_ATTENTION = "attention"
SNAPSHOT_KIND_CAPABILITIES = "capabilities"
SNAPSHOT_KIND_MARKETS = "markets_overview"
SNAPSHOT_KIND_OPTION_CHAIN = "option_chain"
SNAPSHOT_KIND_ANALYSIS = "analysis"
SNAPSHOT_KIND_SEC_FUNDAMENTALS = "sec_fundamentals"
SNAPSHOT_KEY_GLOBAL = "global"

UNDERLYING_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
"""Accepted shape of an underlying snapshot key (path parameter): a plain
canonical ticker identifier — anything else is rejected before any lookup."""

public_router = APIRouter(prefix="/api/v1")

protected_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_session)],
    responses={
        401: {
            "description": (
                "Authentication required: no valid WebAuthn session cookie (or "
                "missing/invalid CSRF header on a mutation). Always the same "
                "generic body with detail code AUTH_REQUIRED."
            )
        }
    },
)


def get_advice_engine() -> AdviceEngine:
    """Provide the single, stateless ``AdviceEngine`` (pure, deterministic)."""
    return AdviceEngine()


async def parse_advice_preview_request(request: Request) -> AdvicePreviewRequest:
    """Validate the raw JSON body in pydantic JSON mode (fail-closed 422).

    The canonical contracts are strict models: python-mode validation (what
    FastAPI applies to an already-parsed body) would reject the legitimate
    wire forms (ISO datetime strings, decimal strings, enum values). Parsing
    the raw bytes with ``model_validate_json`` keeps the contracts strict
    while accepting exactly the canonical JSON wire encoding — any deviation
    (naive datetime, non-finite decimal, unknown field) is rejected as 422.
    """
    raw_body = await request.body()
    try:
        return AdvicePreviewRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


@public_router.get(
    "/health",
    operation_id="get_health",
    response_model=HealthResponse,
    summary="Liveness probe",
)
def get_health() -> HealthResponse:
    """Report process liveness and the engine version. No sensitive data."""
    return HealthResponse(status="alive", engine_version=ENGINE_VERSION)


@protected_router.post(
    "/advice/preview",
    operation_id="post_advice_preview",
    response_model=AdviceResult,
    summary="Evaluate gate inputs through the single AdviceEngine",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AdvicePreviewRequest"}
                }
            },
        }
    },
)
def post_advice_preview(
    inputs: Annotated[AdvicePreviewRequest, Depends(parse_advice_preview_request)],
    engine: Annotated[AdviceEngine, Depends(get_advice_engine)],
) -> AdviceResult:
    """Return the canonical ``AdviceResult`` for certified gate inputs.

    Pass-through only: the route validates the wire payload and hands it to
    the single ``AdviceEngine``. Decimals serialize as strings and datetimes
    as ISO-8601 UTC. The result is analytical — the human decides outside
    Vertex.
    """
    return engine.evaluate(inputs)


async def parse_simulation_preview_request(
    request: Request,
) -> SimulationPreviewRequest:
    """Validate the raw JSON body in pydantic JSON mode (fail-closed 422).

    Same rationale as :func:`parse_advice_preview_request`: the simulation
    contracts are strict models whose wire form carries decimal strings —
    ``model_validate_json`` accepts exactly the canonical JSON encoding and
    rejects every deviation (missing strike, zero quantity, oversized grid,
    non-finite decimal, unknown field) as 422.
    """
    raw_body = await request.body()
    try:
        return SimulationPreviewRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


@protected_router.post(
    "/simulations/preview",
    operation_id="post_simulations_preview",
    response_model=SimulationPreviewResponse,
    summary="THEORETICAL preview of one declared structure (no persistence)",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/SimulationPreviewRequest"
                    }
                }
            },
        }
    },
    responses={
        422: {
            "description": (
                "Rejected fail-closed with the exact machine-readable reason: "
                "either a wire-contract violation, or the defined-risk "
                "verifier's code (e.g. OUTSIDE_CLOSED_CATALOG, "
                "UNCOVERED_SHORT_UPSIDE_TAIL, VERTICAL_DEBIT_NOT_BELOW_WIDTH), "
                "or a typed calculation-domain violation from vertex_core."
            )
        }
    },
)
async def post_simulations_preview(
    inputs: Annotated[
        SimulationPreviewRequest, Depends(parse_simulation_preview_request)
    ],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SimulationPreviewResponse:
    """Run one THEORETICAL simulation preview through vertex_core.

    Orchestration only: the mandatory ``defined_risk_check``, the exact
    ``payoff_at_expiry``, the authority-certified breakevens and the bounded
    ``scenario_grid`` all run inside ``vertex_core.calculations.options`` on
    a worker thread (``run_in_threadpool`` — the event loop never computes).
    Nothing is persisted; nothing here is, or ever becomes, an order.
    """
    try:
        return await run_in_threadpool(
            run_simulation_preview, inputs, now=clock()
        )
    except (SimulationRejectedError, OptionInputError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.reason, "message": exc.detail},
        ) from exc


@protected_router.get(
    "/system/engine",
    operation_id="get_system_engine",
    response_model=EngineInfoResponse,
    summary="Engine and contract versions",
)
def get_system_engine() -> EngineInfoResponse:
    """Report the engine, contract and per-gate versions. Never a secret."""
    return EngineInfoResponse(
        engine_version=ENGINE_VERSION,
        contracts_version=ENGINE_VERSION,
        gate_versions=dict(GATE_VERSIONS),
    )


@protected_router.get(
    "/markets/overview",
    operation_id="get_markets_overview",
    response_model=MarketsOverviewResponse,
    summary="Last published markets overview snapshot (or honest empty state)",
)
def get_markets_overview(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> MarketsOverviewResponse:
    """Serve the LAST ``markets_overview/global`` snapshot exactly as persisted.

    The API relays the worker's published content — population (``SYNTHETIC``
    shown as-is), sectors/tickers with their server-computed returns and
    weights, breadth, coverage account and the deterministic conclusion — and
    computes nothing. With no snapshot ever published the answer is a 200
    with ``state = "empty"``: absent stays absent, nothing is invented.
    """
    snapshot = reader.current(kind=SNAPSHOT_KIND_MARKETS, key=SNAPSHOT_KEY_GLOBAL)
    return build_markets_overview_response(snapshot, now=clock())


@protected_router.get(
    "/analysis/{instrument}",
    operation_id="get_analysis",
    response_model=AnalysisResponse,
    summary="Last published analysis dossier for one instrument (or honest empty state)",
)
def get_analysis(
    instrument: Annotated[str, Path(pattern=UNDERLYING_PATTERN)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AnalysisResponse:
    """Serve the LAST ``analysis/{instrument}`` snapshot exactly as persisted.

    The API relays the worker's published dossier — the canonical
    ``AdviceResult`` of the single ``AdviceEngine`` with its ten gates and
    reason codes, the validated OHLCV bars, the fusion evidence rail and the
    ``THEORETICAL`` scenario block (or its typed absence reason) — and
    computes nothing. With no snapshot ever published for this instrument
    the answer is a 200 with ``state = "empty"``: absent stays absent,
    nothing is invented.
    """
    snapshot = reader.current(kind=SNAPSHOT_KIND_ANALYSIS, key=instrument)
    return build_analysis_response(snapshot, instrument=instrument, now=clock())


@protected_router.get(
    "/sources/sec/{instrument}/fundamentals",
    operation_id="get_sec_fundamentals",
    response_model=SecFundamentalsResponse,
    summary="Official point-in-time SEC filings and facts for one instrument",
)
def get_sec_fundamentals(
    instrument: Annotated[str, Path(pattern=UNDERLYING_PATTERN)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SecFundamentalsResponse:
    """Relay the last SEC snapshot; no ratio, score or advice is computed."""
    snapshot = reader.current(kind=SNAPSHOT_KIND_SEC_FUNDAMENTALS, key=instrument)
    return build_sec_fundamentals_response(snapshot, instrument=instrument, now=clock())


@protected_router.get(
    "/options/{underlying}/chain",
    operation_id="get_option_chain",
    response_model=OptionChainResponse,
    summary="Last published option chain for one underlying (or honest empty state)",
)
def get_option_chain(
    underlying: Annotated[str, Path(pattern=UNDERLYING_PATTERN)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> OptionChainResponse:
    """Serve the LAST ``option_chain/{underlying}`` snapshot exactly as persisted.

    The API relays the worker's published content — per-(expiration,
    trading_class) groups with complete contract identities, verbatim quotes
    and their quality, the worker's Vertex IV/Greeks (``THEORETICAL``, with
    their ``CalculationRecord`` lineage) or their typed refusal reasons, the
    coverage account and the displayed row budget — and computes nothing.
    With no snapshot ever published for this underlying the answer is a 200
    with ``state = "empty"``: absent stays absent, nothing is invented.
    """
    snapshot = reader.current(kind=SNAPSHOT_KIND_OPTION_CHAIN, key=underlying)
    return build_option_chain_response(snapshot, underlying=underlying, now=clock())


@protected_router.get(
    "/calendar",
    operation_id="get_calendar",
    response_model=CalendarResponse,
    summary="Last published calendar snapshot (or honest empty state)",
    responses={
        422: {
            "description": (
                "Rejected fail-closed window: WINDOW_INCOMPLETE (one bound "
                "without the other), WINDOW_NAIVE_DATETIME, WINDOW_INVERTED "
                "or WINDOW_TOO_LARGE (bounded to 90 days)."
            )
        }
    },
)
def get_calendar(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    window_from: Annotated[datetime | None, Query(alias="from")] = None,
    window_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> CalendarResponse:
    """Serve the LAST ``calendar/global`` snapshot exactly as persisted.

    The API relays the worker's published agenda — importance from the
    versioned rule, distinct ESTIMATED/CONFIRMED labels, revisions with
    their preserved previous values, conserved exchange timezones and the
    position/thesis event context — and computes nothing. The optional
    ``from``/``to`` query window (both bounds, aware datetimes, at most 90
    days) SELECTS events without altering any. With no snapshot ever
    published the answer is a 200 with ``state = "empty"``.
    """
    window = validate_window(window_from, window_to)
    snapshot = reader.current(kind=SNAPSHOT_KIND_CALENDAR, key=SNAPSHOT_KEY_GLOBAL)
    return build_calendar_response(snapshot, window=window)


@protected_router.get(
    "/opportunities",
    operation_id="get_opportunities",
    response_model=OpportunitiesResponse,
    summary="Last published opportunities snapshot (or honest empty state)",
)
def get_opportunities(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
) -> OpportunitiesResponse:
    """Serve the LAST ``opportunities/global`` snapshot exactly as persisted.

    The API relays the worker's published candidates — the single
    ``AdviceEngine``'s statuses under the manifest profile (id + version),
    the documented lexicographic ordering, the honest evidence-presence
    checks and the exclusion-reason distribution — and computes nothing. A
    relay guard refuses a snapshot carrying a closed candidate in the
    qualified group. With no snapshot ever published the answer is a 200
    with ``state = "empty"``.
    """
    snapshot = reader.current(
        kind=SNAPSHOT_KIND_OPPORTUNITIES, key=SNAPSHOT_KEY_GLOBAL
    )
    return build_opportunities_response(snapshot)


# ---------------------------------------------------------------------------
# Vertex AI (page 11 — LOT-21 socle): deterministic template ONLY. No AI
# provider exists (human decision B-05 pending); nothing here calls a model.
# ---------------------------------------------------------------------------


async def parse_ai_explain_request(request: Request) -> AiExplainRequest:
    """Strict JSON-mode validation of the explain body (fail-closed 422)."""
    raw_body = await request.body()
    try:
        return AiExplainRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


@protected_router.get(
    "/ai/status",
    operation_id="get_ai_status",
    response_model=AiStatusResponse,
    summary="AI provider state: DISABLED pending human decision B-05",
)
def get_ai_status() -> AiStatusResponse:
    """Report the honest AI state: no provider, deterministic template only."""
    return AiStatusResponse(
        provider="DISABLED",
        reason="B-05_HUMAN_DECISION_PENDING",
        deterministic_template_available=True,
    )


@protected_router.post(
    "/ai/explain",
    operation_id="post_ai_explain",
    response_model=AiAnswer,
    summary="Deterministic template explanation of one persisted snapshot",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AiExplainRequest"}
                }
            },
        }
    },
    responses={
        404: {
            "description": (
                "No snapshot was ever published for this subject (code "
                "NO_SNAPSHOT_FOR_SUBJECT) — there is nothing honest to "
                "explain."
            )
        }
    },
)
def post_ai_explain(
    inputs: Annotated[AiExplainRequest, Depends(parse_ai_explain_request)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
) -> AiAnswer:
    """Explain ONE persisted snapshot through the DETERMINISTIC template.

    Pure presentation of already-certified data: no network, no model, no
    financial computation, no clock beyond the snapshot's own ``as_of``.
    Every claim cites evidence really present in the snapshot (validated
    fail-closed); the answer is labeled ``DETERMINISTIC_TEMPLATE`` and its
    limitations always carry the B-05 notice. An absent snapshot is a clean
    404 — never an invented explanation.
    """
    kind = SUBJECT_SNAPSHOT_KINDS[inputs.subject.kind]
    snapshot = reader.current(kind=kind, key=inputs.subject.key)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ERROR_NO_SNAPSHOT_FOR_SUBJECT,
                "message": "no snapshot published for this subject",
            },
        )
    return build_ai_answer(inputs.subject, snapshot)


def get_capability_manifest(request: Request) -> CapabilityManifest:
    """Provide the manifest parsed once at startup (``create_app``)."""
    return cast(CapabilityManifest, request.app.state.capability_manifest)


@protected_router.get(
    "/today/attention",
    operation_id="get_today_attention",
    response_model=AttentionSnapshotResponse,
    summary="Last published attention snapshot (or honest empty state)",
)
def get_today_attention(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AttentionSnapshotResponse:
    """Serve the LAST ``attention/global`` snapshot exactly as persisted.

    The API relays the worker's published content — population (``SYNTHETIC``
    shown as-is), coverage, items with provenance — and computes nothing.
    With no snapshot ever published the answer is a 200 with ``state =
    "empty"``: absent stays absent, nothing is invented.
    """
    snapshot = reader.current(kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL)
    return build_attention_response(snapshot, now=clock())


@protected_router.get(
    "/system/capabilities",
    operation_id="get_system_capabilities",
    response_model=SystemCapabilitiesResponse,
    summary="Declared capabilities crossed with really-probed statuses, plus health",
)
def get_system_capabilities(
    manifest: Annotated[CapabilityManifest, Depends(get_capability_manifest)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SystemCapabilitiesResponse:
    """Cross the FULL declared manifest with the latest persisted probes.

    Every manifest entry is present (``total`` equals the manifest size); a
    capability never probed answers ``ERROR`` with reason ``NEVER_TESTED``.
    Health blocks report the database (``SELECT 1``), both snapshot heads,
    and the worker through the explicitly labeled ``heartbeat_proxy``.
    """
    capabilities = reader.current(kind=SNAPSHOT_KIND_CAPABILITIES, key=SNAPSHOT_KEY_GLOBAL)
    attention = reader.current(kind=SNAPSHOT_KIND_ATTENTION, key=SNAPSHOT_KEY_GLOBAL)
    return build_capabilities_response(
        manifest,
        snapshot=capabilities,
        attention=attention,
        db_ok=reader.ping(),
        now=clock(),
    )


@protected_router.get(
    "/events/stream",
    operation_id="get_events_stream",
    summary="Signal-only SSE: snapshot head version changes and pings",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": (
                "text/event-stream of `snapshot` events "
                '(`{"resource": "<kind>/<key>", "version": <int>}`) and '
                "keepalive `ping` events. Signal only — no business data; "
                "clients refetch through the REST endpoints."
            ),
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
async def get_events_stream(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    settings: Annotated[StreamSettings, Depends(get_stream_settings)],
) -> StreamingResponse:
    """Stream head-version change signals (database polling, coalesced)."""
    return StreamingResponse(
        snapshot_event_stream(reader, settings),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Manual portfolio journal (accounting semantics — records of PAST facts
# executed outside Vertex; nothing here is, or ever becomes, an order)
# ---------------------------------------------------------------------------


def get_portfolio_gateway(request: Request) -> PortfolioGateway:
    """FastAPI dependency: the real gateway (tests override with fakes)."""
    return DbPortfolioGateway(request.app)


async def parse_record_transaction_request(
    request: Request,
) -> RecordTransactionRequest:
    """Validate the raw JSON body in pydantic JSON mode (fail-closed 422).

    Same rationale as :func:`parse_advice_preview_request`: the journal DTO
    is a strict model whose wire form carries decimal strings and ISO
    datetimes — any deviation (naive datetime, non-finite decimal, missing
    instrument on a position fact, unknown field) is rejected as 422.
    """
    raw_body = await request.body()
    try:
        return RecordTransactionRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


async def parse_compensate_request(request: Request) -> CompensateTransactionRequest:
    """Strict JSON-mode validation of the compensation body (fail-closed 422)."""
    raw_body = await request.body()
    try:
        return CompensateTransactionRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


async def parse_import_preview_request(request: Request) -> CsvImportPreviewRequest:
    """Strict JSON-mode validation of the CSV preview body (fail-closed 422)."""
    raw_body = await request.body()
    try:
        return CsvImportPreviewRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


async def parse_import_confirm_request(request: Request) -> ImportConfirmRequest:
    """Strict JSON-mode validation of the CSV confirm body (fail-closed 422)."""
    raw_body = await request.body()
    try:
        return ImportConfirmRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


@protected_router.get(
    "/portfolio",
    operation_id="get_portfolio",
    response_model=PortfolioResponse,
    summary="Manual journal, declared lots and last published valuation",
)
def get_portfolio(
    gateway: Annotated[PortfolioGateway, Depends(get_portfolio_gateway)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> PortfolioResponse:
    """Serve the manual ledger verbatim plus the LAST valuation snapshot.

    The default portfolio ``main`` is created on first use (documented
    get-or-create). The valuation block relays the worker's snapshot exactly
    as persisted (``mark_population = "SYNTHETIC"`` shown as-is) or an honest
    empty state — the API computes no P&L, mark, weight or total.
    """
    return build_portfolio_response(gateway.overview(), now=clock())


@protected_router.post(
    "/portfolio/transactions",
    operation_id="record_transaction",
    response_model=RecordTransactionResponse,
    summary="Record one past transaction already executed outside Vertex",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/RecordTransactionRequest"
                    }
                }
            },
        }
    },
    responses={
        422: {
            "description": (
                "Rejected fail-closed: wire-contract violation or "
                "EFFECTIVE_AT_IN_FUTURE (a fact that has not happened yet "
                "cannot be recorded)."
            )
        }
    },
)
def record_transaction(
    inputs: Annotated[
        RecordTransactionRequest, Depends(parse_record_transaction_request)
    ],
    gateway: Annotated[PortfolioGateway, Depends(get_portfolio_gateway)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> RecordTransactionResponse:
    """Append one accounting-journal fact and enqueue the revaluation.

    The ledger write and the ``portfolio.valuation.refresh`` outbox message
    commit in the SAME transaction (outbox atomicity). This endpoint records
    what already happened outside Vertex — it never transmits anything to a
    broker and no such capability exists.
    """
    now = clock()
    if inputs.effective_at > now:
        raise HTTPException(
            status_code=422,
            detail={
                "code": ERROR_EFFECTIVE_AT_IN_FUTURE,
                "message": "effective_at must not be in the future",
            },
        )
    transaction_id = gateway.record_transaction(
        kind=inputs.kind.value,
        instrument=(
            {"ticker": inputs.instrument.ticker} if inputs.instrument else None
        ),
        quantity=inputs.quantity,
        price=inputs.price,
        amount=inputs.amount,
        currency=inputs.currency,
        fees=inputs.fees,
        effective_at=inputs.effective_at,
        note=inputs.note,
        now=now,
    )
    return RecordTransactionResponse(
        transaction_id=transaction_id, refresh_enqueued=True
    )


@protected_router.post(
    "/portfolio/transactions/{transaction_id}/compensate",
    operation_id="compensate_transaction",
    response_model=CompensateTransactionResponse,
    summary="Correct one recorded fact by appending its compensating row",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/CompensateTransactionRequest"
                    }
                }
            },
        }
    },
    responses={
        404: {"description": "Unknown transaction (code UNKNOWN_TRANSACTION)."},
        409: {
            "description": (
                "The transaction already has a compensating row (code "
                "ALREADY_COMPENSATED) — history is append-only, a fact is "
                "corrected at most once."
            )
        },
    },
)
def compensate_transaction(
    transaction_id: Annotated[int, Path(ge=1)],
    inputs: Annotated[CompensateTransactionRequest, Depends(parse_compensate_request)],
    gateway: Annotated[PortfolioGateway, Depends(get_portfolio_gateway)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> CompensateTransactionResponse:
    """Append the compensating row of one recorded fact (never an edit).

    The original row stays untouched forever; the compensating row negates
    amount, fees and quantity and carries the mandatory reason note. A second
    compensation of the same row is a clean 409 conflict.
    """
    from vertex_persistence.errors import (
        AlreadyCompensatedError,
        UnknownLedgerEventError,
    )

    now = clock()
    try:
        compensation_id = gateway.compensate_transaction(
            event_id=transaction_id, note=inputs.note, now=now
        )
    except AlreadyCompensatedError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": ERROR_ALREADY_COMPENSATED, "message": str(exc)},
        ) from exc
    except UnknownLedgerEventError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": ERROR_UNKNOWN_TRANSACTION, "message": str(exc)},
        ) from exc
    return CompensateTransactionResponse(
        compensation_id=compensation_id,
        compensates=transaction_id,
        refresh_enqueued=True,
    )


@protected_router.post(
    "/portfolio/import/preview",
    operation_id="preview_portfolio_import",
    response_model=ImportPreviewResponse,
    summary="Typed CSV preview: rows, per-row errors, duplicates — NO write",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/CsvImportPreviewRequest"
                    }
                }
            },
        }
    },
    responses={
        422: {
            "description": (
                "Whole-input rejection: CSV_TOO_LARGE (256 KiB), "
                "CSV_TOO_MANY_ROWS (500 data rows), CSV_HEADER_INVALID or "
                "CSV_MALFORMED (a cell the CSV reader itself refuses; the "
                "stdlib message is never relayed, it can quote the file)."
            )
        }
    },
)
def preview_portfolio_import(
    inputs: Annotated[CsvImportPreviewRequest, Depends(parse_import_preview_request)],
    gateway: Annotated[PortfolioGateway, Depends(get_portfolio_gateway)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> ImportPreviewResponse:
    """Validate a CSV import WITHOUT writing anything.

    Every data row becomes either a typed, hash-stamped echo (to be sent
    back verbatim to the confirm endpoint) or a per-row error list. Valid
    rows matching already-recorded facts are flagged as potential duplicates
    — information for the user, never a silent drop.
    """
    from vertex_api.portfolio import MAX_IMPORT_BYTES, MAX_IMPORT_ROWS, ImportRowEcho

    now = clock()
    try:
        valid, invalid = parse_import_csv(inputs.csv, now=now)
    except CsvImportError as exc:
        raise HTTPException(
            status_code=422, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    ledger = gateway.overview().transactions
    duplicates = detect_potential_duplicates(valid, ledger)
    return ImportPreviewResponse(
        rows_total=len(valid) + len(invalid),
        rows_valid=tuple(
            ImportRowEcho(
                row_number=row.row_number,
                kind=row.canonical_fields["kind"],
                ticker=row.canonical_fields["ticker"],
                quantity=row.canonical_fields["quantity"],
                price=row.canonical_fields["price"],
                amount=row.canonical_fields["amount"],
                currency=row.canonical_fields["currency"],
                fees=row.canonical_fields["fees"],
                effective_at=row.canonical_fields["effective_at"],
                note=row.canonical_fields["note"],
                row_hash=row.row_hash,
            )
            for row in valid
        ),
        rows_invalid=tuple(invalid),
        potential_duplicates=tuple(duplicates),
        max_rows=MAX_IMPORT_ROWS,
        max_bytes=MAX_IMPORT_BYTES,
    )


@protected_router.post(
    "/portfolio/import/confirm",
    operation_id="confirm_portfolio_import",
    response_model=ImportConfirmResponse,
    summary="Record the previewed rows (validation replayed, hash verified)",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ImportConfirmRequest"}
                }
            },
        }
    },
    responses={
        422: {
            "description": (
                "Rejected fail-closed: IMPORT_ROW_INVALID (a row no longer "
                "passes the replayed validation) or ECHO_HASH_MISMATCH (an "
                "echoed row was altered after the preview). Nothing is "
                "written on rejection."
            )
        }
    },
)
def confirm_portfolio_import(
    inputs: Annotated[ImportConfirmRequest, Depends(parse_import_confirm_request)],
    gateway: Annotated[PortfolioGateway, Depends(get_portfolio_gateway)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> ImportConfirmResponse:
    """Record ONLY rows that re-pass the full validation with intact hashes.

    The confirm never trusts the echo: each row's fields are re-validated
    exactly like at preview time and its integrity hash is recomputed; any
    divergence rejects the WHOLE request before any write. Accepted rows are
    recorded with source ``IMPORT_CONFIRMED`` and one revaluation is
    enqueued in the same transaction.
    """
    now = clock()
    validated = []
    for echo in inputs.rows:
        fields = {
            "kind": echo.kind,
            "ticker": echo.ticker,
            "quantity": echo.quantity,
            "price": echo.price,
            "amount": echo.amount,
            "currency": echo.currency,
            "fees": echo.fees,
            "effective_at": echo.effective_at,
            "note": echo.note,
        }
        row, errors = validate_import_fields(
            fields, row_number=echo.row_number, now=now
        )
        if row is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": ERROR_IMPORT_ROW_INVALID,
                    "message": f"row {echo.row_number} failed the replayed validation",
                    "errors": errors,
                },
            )
        if row.row_hash != echo.row_hash:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": ERROR_ECHO_HASH_MISMATCH,
                    "message": (
                        f"row {echo.row_number}: the echoed content does not "
                        "match its integrity hash"
                    ),
                },
            )
        validated.append(row)
    recorded = gateway.record_import(validated, now=now)
    return ImportConfirmResponse(
        recorded_transaction_ids=tuple(recorded),
        source="IMPORT_CONFIRMED",
        refresh_enqueued=True,
    )


@protected_router.get(
    "/portfolio/export",
    operation_id="export_portfolio",
    summary="CSV export of the manual ledger (version stamp, ledger only)",
    response_class=Response,
    responses={
        200: {
            "description": (
                "text/csv: one version-stamp comment line, the header row and "
                "the ledger rows — no other data. Cells starting with "
                "'=', '+', '-' or '@' are neutralized with a leading "
                "apostrophe against spreadsheet formula injection."
            ),
            "content": {"text/csv": {"schema": {"type": "string"}}},
        }
    },
)
def export_portfolio(
    gateway: Annotated[PortfolioGateway, Depends(get_portfolio_gateway)],
) -> Response:
    """Export the journal as CSV. Nothing but the ledger leaves the server."""
    overview = gateway.overview()
    return Response(
        content=render_export_csv(overview.transactions),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="vertex-portfolio-ledger.csv"',
            "X-Vertex-Export-Version": EXPORT_SCHEMA_VERSION,
        },
    )


# ---------------------------------------------------------------------------
# Follow-up (page 09 — theses and review queue) and performance (page 10)
# ---------------------------------------------------------------------------


def get_follow_up_gateway(request: Request) -> FollowUpGateway:
    """FastAPI dependency: the real gateway (tests override with fakes)."""
    return DbFollowUpGateway(request.app)


async def parse_create_thesis_request(request: Request) -> CreateThesisRequest:
    """Strict JSON-mode validation of the thesis body (fail-closed 422).

    Same rationale as :func:`parse_advice_preview_request`: the DTO is a
    strict model — a blank ``invalidation``, a missing ``idempotency_key``,
    a naive datetime or an unknown field is rejected as 422.
    """
    raw_body = await request.body()
    try:
        return CreateThesisRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


async def parse_thesis_revision_request(request: Request) -> ThesisRevisionRequest:
    """Strict JSON-mode validation of the revision body (fail-closed 422).

    The action allowlist (REVIEWED/SNOOZED/NOTE_UPDATED/ARCHIVED/REACTIVATED
    — never CREATED) and the snooze_until-iff-SNOOZED rule are enforced here
    before any database work.
    """
    raw_body = await request.body()
    try:
        return ThesisRevisionRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


@protected_router.get(
    "/follow-up/queue",
    operation_id="get_follow_up_queue",
    response_model=FollowUpQueueResponse,
    summary="Last published review queue snapshot (or honest empty state)",
)
def get_follow_up_queue(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> FollowUpQueueResponse:
    """Serve the LAST ``review_queue/global`` snapshot exactly as persisted.

    The API relays the worker's published content — projected thesis states,
    the documented lexicographic due ordering, urgency flags and reasons, the
    per-ticker information clusters with provenance, and the two SEPARATE
    population labels — and computes nothing. With no snapshot ever published
    the answer is a 200 with ``state = "empty"``: absent stays absent,
    nothing is invented.
    """
    snapshot = reader.current(
        kind=SNAPSHOT_KIND_REVIEW_QUEUE, key=SNAPSHOT_KEY_REVIEW_QUEUE
    )
    return build_follow_up_queue_response(snapshot, now=clock())


@protected_router.post(
    "/theses",
    operation_id="create_thesis",
    response_model=CreateThesisResponse,
    summary="Append one user-written thesis (statement + mandatory falsifier)",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/CreateThesisRequest"}
                }
            },
        }
    },
    responses={
        200: {
            "description": (
                "Idempotent replay: the client's idempotency_key already "
                "names this thesis — nothing was written, created=false, the "
                "original ids are returned."
            )
        },
        404: {"description": "Unknown portfolio — code UNKNOWN_PORTFOLIO."},
        409: {
            "description": (
                "The idempotency_key already names a DIFFERENT operation "
                "(code IDEMPOTENCY_KEY_REUSED) — keys are never recycled."
            )
        },
        422: {
            "description": (
                "Rejected fail-closed: blank invalidation, missing "
                "idempotency_key or any other wire-contract violation."
            )
        },
    },
)
def create_thesis_route(
    inputs: Annotated[CreateThesisRequest, Depends(parse_create_thesis_request)],
    gateway: Annotated[FollowUpGateway, Depends(get_follow_up_gateway)],
    clock: Annotated[Clock, Depends(get_clock)],
    response: Response,
) -> CreateThesisResponse:
    """Record one thesis and enqueue the review-queue refresh, one transaction.

    Revisions are append-only and the review-queue refresh commits WITH the
    write (outbox atomicity). Replaying the same ``idempotency_key`` answers
    200 with ``created=false`` and writes nothing — never a duplicate.
    """
    from vertex_persistence.errors import (
        IdempotencyKeyReuseError,
        UnknownPortfolioError,
    )

    try:
        result = gateway.create(inputs, now=clock())
    except IdempotencyKeyReuseError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": ERROR_IDEMPOTENCY_KEY_REUSED, "message": str(exc)},
        ) from exc
    except UnknownPortfolioError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": ERROR_UNKNOWN_PORTFOLIO, "message": str(exc)},
        ) from exc
    if not result.created:
        response.status_code = 200
    return CreateThesisResponse(
        thesis_id=result.thesis_id,
        revision_id=result.revision_id,
        created=result.created,
        refresh_enqueued=result.created,
    )


@protected_router.post(
    "/theses/{thesis_id}/revisions",
    operation_id="record_thesis_revision",
    response_model=ThesisRevisionResponse,
    summary="Append one review-lifecycle revision (append-only history)",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ThesisRevisionRequest"}
                }
            },
        }
    },
    responses={
        200: {
            "description": (
                "Idempotent replay: the client's idempotency_key already "
                "names this exact revision — nothing was written, "
                "created=false, the original revision id is returned. Ten "
                "replays leave exactly one row."
            )
        },
        404: {"description": "Unknown thesis (code UNKNOWN_THESIS)."},
        409: {
            "description": (
                "The idempotency_key already names a DIFFERENT operation "
                "(code IDEMPOTENCY_KEY_REUSED) — keys are never recycled."
            )
        },
        422: {
            "description": (
                "Rejected fail-closed: action outside the allowlist "
                "(CREATED included), snooze_until missing on SNOOZED or "
                "present elsewhere, or any wire-contract violation."
            )
        },
    },
)
def record_thesis_revision_route(
    thesis_id: Annotated[int, Path(ge=1)],
    inputs: Annotated[ThesisRevisionRequest, Depends(parse_thesis_revision_request)],
    gateway: Annotated[FollowUpGateway, Depends(get_follow_up_gateway)],
    clock: Annotated[Clock, Depends(get_clock)],
    response: Response,
) -> ThesisRevisionResponse:
    """Append one revision and enqueue the review-queue refresh, one transaction.

    History is append-only: nothing edits or deletes an earlier revision;
    the projected status is recomputed by the repository, never stored.
    """
    from vertex_persistence.errors import (
        IdempotencyKeyReuseError,
        UnknownThesisError,
        ValidationFailedError,
    )

    try:
        result = gateway.record_revision(thesis_id, inputs, now=clock())
    except IdempotencyKeyReuseError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": ERROR_IDEMPOTENCY_KEY_REUSED, "message": str(exc)},
        ) from exc
    except UnknownThesisError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": ERROR_UNKNOWN_THESIS, "message": str(exc)},
        ) from exc
    except ValidationFailedError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_FAILED", "message": str(exc)},
        ) from exc
    if not result.created:
        response.status_code = 200
    return ThesisRevisionResponse(
        thesis_id=thesis_id,
        revision_id=result.revision_id,
        created=result.created,
        refresh_enqueued=result.created,
    )


@protected_router.get(
    "/risk/matrix",
    operation_id="get_risk_matrix",
    response_model=RiskMatrixResponse,
    summary="Last published correlation matrix (or honest empty state)",
)
def get_risk_matrix(
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> RiskMatrixResponse:
    """Serve the LAST ``risk_matrix/global`` snapshot as persisted.

    The API relays the worker's published content — the declared perimeter,
    the matrix ALREADY RENDERED AS STRINGS, the extreme pairs, the coverage
    and its alignment cost — and computes no coefficient. The key is
    ``global`` because the matrix describes the declared perimeter, not a
    portfolio.

    With no snapshot ever published the answer is a 200 with
    ``state = "empty"``: that happens when no perimeter is declared, or when
    no bars have been collected yet. Absent stays absent.

    A snapshot carrying ``coverage.refusal_reason`` stays ``state = "ok"``:
    the worker DID publish, and what it published is a reasoned refusal —
    too short a perimeter, too few common sessions, a constant series.
    Downgrading it to ``empty`` would erase the reason and leave the screen
    blank as if something had broken.
    """
    snapshot = reader.current(kind=SNAPSHOT_KIND_RISK, key="global")
    return build_risk_response(snapshot, now=clock())


@protected_router.get(
    "/performance/{portfolio_id}",
    operation_id="get_performance",
    response_model=PerformanceSnapshotResponse,
    summary="Last published performance snapshot (or honest empty state)",
)
def get_performance(
    portfolio_id: Annotated[int, Path(ge=1)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> PerformanceSnapshotResponse:
    """Serve the LAST ``performance/{portfolio_id}`` snapshot as persisted.

    The API relays the worker's published content — daily valuation series,
    explicit gross/net metrics with their ``CalculationRecord`` lineage,
    honest INSUFFICIENT_DATA / INVALID gate outcomes, monthly heatmap,
    coverage and the ``SYNTHETIC_MARKS_REAL_LEDGER`` population shown as-is —
    and computes nothing. With no snapshot ever published the answer is a
    200 with ``state = "empty"``: absent stays absent, nothing is invented.
    """
    snapshot = reader.current(
        kind=SNAPSHOT_KIND_PERFORMANCE, key=str(portfolio_id)
    )
    return build_performance_response(
        snapshot, portfolio_id=portfolio_id, now=clock()
    )


@protected_router.get(
    "/performance/{portfolio_id}/export",
    operation_id="export_performance",
    response_model=PerformanceExportResponse,
    summary="Reproducible export: CSV points + JSON manifest (methods, versions, hashes)",
    responses={
        404: {
            "description": (
                "No performance snapshot was ever published for this "
                "portfolio — code NO_PERFORMANCE_SNAPSHOT — there is nothing "
                "honest to export."
            )
        }
    },
)
def export_performance(
    portfolio_id: Annotated[int, Path(ge=1)],
    reader: Annotated[SnapshotReader, Depends(get_snapshot_reader)],
) -> PerformanceExportResponse:
    """Export the daily points (CSV) and the audit manifest (JSON).

    A PURE function of the persisted snapshot: two calls over the same
    snapshot version return byte-identical bodies; ``as_of`` is the
    snapshot's own instant (documented), never the request clock.
    """
    snapshot = reader.current(
        kind=SNAPSHOT_KIND_PERFORMANCE, key=str(portfolio_id)
    )
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_PERFORMANCE_SNAPSHOT",
                "message": "no performance snapshot published for this portfolio",
            },
        )
    return build_performance_export(snapshot, portfolio_id=portfolio_id)
