"""Wire DTOs of the Vertex One API.

``AdvicePreviewRequest`` IS the engine's ``AdviceInputs`` — same fields, same
validators, same canonical ``advice_id`` hash — with exactly one wire
refinement: ``calculation_statuses`` values are validated into
``CalculationStatus`` members, so the JSON strings a client sends become the
canonical enum values the gates expect. No decision logic lives here; the API
never redefines a contract, it only names its wire boundary.
"""

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, PlainSerializer

from vertex_core.contracts.enums import CalculationStatus, SourceCapabilityStatus
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
    freeze_str_mapping,
)
from vertex_core.decision import AdviceInputs, CalculationsInput

__all__ = [
    "AdvicePreviewRequest",
    "AnalysisResponse",
    "AttentionItem",
    "AttentionSnapshotResponse",
    "CalculationStatusesInput",
    "CapabilityStatusEntry",
    "DbHealth",
    "EngineInfoResponse",
    "HealthResponse",
    "MarketsBreadth",
    "MarketsCoverage",
    "MarketsDiscardedTicker",
    "MarketsOverviewResponse",
    "MarketsRejectedRecord",
    "MarketsSector",
    "MarketsTicker",
    "OptionChainContract",
    "OptionChainExpiration",
    "OptionChainResponse",
    "SecFundamentalsResponse",
    "SnapshotHealth",
    "SystemCapabilitiesResponse",
    "SystemHealth",
    "WorkerHealth",
]

FrozenCalculationStatusMapping = Annotated[
    Mapping[str, CalculationStatus],
    AfterValidator(freeze_str_mapping),
    PlainSerializer(dict, return_type=dict),
]
"""calculation id -> ``CalculationStatus``, frozen at validation time."""

FrozenGateVersionMapping = Annotated[
    Mapping[str, NonEmptyStr],
    AfterValidator(freeze_str_mapping),
    PlainSerializer(dict, return_type=dict),
]
"""gate id -> gate version, frozen at validation time."""


class CalculationStatusesInput(CalculationsInput):
    """Wire form of the gate 6 facts.

    Narrows the engine's ``Any``-valued mapping to ``CalculationStatus``
    members so JSON input (``{"iv_surface": "OK"}``) reaches the gate as
    canonical enum values. An absent mapping stays ``None`` (fail-closed at
    the gate), never an empty default.
    """

    calculation_statuses: FrozenCalculationStatusMapping | None = None


class AdvicePreviewRequest(AdviceInputs):
    """Complete certified input set for one advice preview.

    Field-for-field the engine's own ``AdviceInputs`` (subclass — nothing is
    redefined), with the gate 6 mapping typed for the wire. A field left
    absent stays honestly absent and blocks its gate with ``UNEVALUABLE``.
    """

    calculations: CalculationStatusesInput = Field(default_factory=CalculationStatusesInput)


class HealthResponse(ContractModel):
    """Liveness payload: static status and engine version, nothing sensitive."""

    status: Literal["alive"]
    engine_version: NonEmptyStr


class EngineInfoResponse(ContractModel):
    """Engine and contract versions backing every verdict. Carries no secret.

    ``contracts_version`` equals the ``ENGINE_VERSION`` stamp because the
    canonical contracts are versioned by the same identifier that is recorded
    in every calculation and advice contract (``vertex_core.version``).
    """

    engine_version: NonEmptyStr
    contracts_version: NonEmptyStr
    gate_versions: FrozenGateVersionMapping


# ---------------------------------------------------------------------------
# GET /api/v1/today/attention — last published attention snapshot, verbatim
# ---------------------------------------------------------------------------


class AttentionItem(ContractModel):
    """One published attention item, relayed from the worker snapshot.

    ``synthetic`` and the ``population`` label of the response are shown
    exactly as published — synthetic data never blends into a real
    presentation. ``provenance`` is the cluster provenance block verbatim
    (cluster id, member event ids, sources, rights, timestamps,
    instrument_ref); the API adds nothing and recomputes nothing.
    """

    id: NonEmptyStr
    title: NonEmptyStr
    sources: tuple[NonEmptyStr, ...]
    rights: tuple[NonEmptyStr, ...]
    relevance_reasons: tuple[NonEmptyStr, ...] = Field(max_length=3)
    synthetic: bool
    provenance: FrozenStrMapping


class AttentionSnapshotResponse(ContractModel):
    """The last ``attention/global`` snapshot — or an honest empty state.

    ``state = "empty"`` means NO snapshot was ever published: every
    snapshot-derived field is ``None`` (never zero, never invented) and
    ``reason`` says why. ``state = "ok"`` carries the persisted snapshot
    version, ``as_of``, ``population`` (``SYNTHETIC`` shown as-is),
    the full coverage block and the published items.

    ``state = "stale"`` relaie le MÊME contenu, mais dit que l'instantané
    a dépassé son budget de fraîcheur (news_attention) : le worker n'a rien
    publié de plus récent. ``age_seconds`` est publié dans TOUS les états
    datables — son absence faisait passer un instantané de trois jours
    pour un instantané d'une minute.
    """

    state: Literal["ok", "stale", "empty"]
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    population: NonEmptyStr | None
    coverage: FrozenStrMapping | None
    items: tuple[AttentionItem, ...]
    rejected_count: Annotated[int, Field(ge=0)] | None
    reason: NonEmptyStr | None


# ---------------------------------------------------------------------------
# GET /api/v1/markets/overview — last published markets snapshot, verbatim
# ---------------------------------------------------------------------------


class MarketsTicker(ContractModel):
    """One covered ticker, relayed from the worker snapshot verbatim.

    Every price and ratio is a DECIMAL STRING computed server-side (the last
    close verbatim from the observation payload, the 1-day return from
    ``market.simple_return``, weights and display percentages rendered by the
    worker). The API and the client format — they never recompute.
    ``calculation`` is the preserved ``CalculationRecord`` lineage subset
    (engine_version, input_hash, result_hash, method, status).
    """

    ticker: NonEmptyStr
    sector: NonEmptyStr
    trading_day: NonEmptyStr
    previous_trading_day: NonEmptyStr
    last_close: NonEmptyStr
    previous_close: NonEmptyStr
    currency: NonEmptyStr | None
    return_1d: NonEmptyStr
    return_1d_pct: NonEmptyStr
    weight_in_sector: NonEmptyStr
    weight_in_sector_pct: NonEmptyStr
    weight_global: NonEmptyStr
    weight_global_pct: NonEmptyStr
    quality: NonEmptyStr
    synthetic: bool
    calculation: FrozenStrMapping


class MarketsSector(ContractModel):
    """One declared sector with its covered tickers (possibly none)."""

    sector: NonEmptyStr
    label: NonEmptyStr
    declared_count: Annotated[int, Field(ge=0)]
    covered_count: Annotated[int, Field(ge=0)]
    tickers: tuple[MarketsTicker, ...]


class MarketsBreadth(ContractModel):
    """Global breadth block — ``market.breadth`` result or an honest INVALID.

    ``status = "INVALID"`` (coverage below the threshold gate) carries the
    typed reason and NO value — a breadth computed on a sliver of the
    universe is never presented. All percentages are server-rendered strings.

    ``above_count`` (advancers), ``down_count`` (decliners) and
    ``flat_count`` (unchanged) are the worker's exact counts over the covered
    instruments and PARTITION ``covered_count`` (up + down + flat = covered);
    they are published in both states, since an INVALID block refuses the
    ratio, not the counted facts. The API relays them verbatim and never
    derives one from the others.
    """

    status: Literal["OK", "INVALID"]
    reason: NonEmptyStr | None
    value: NonEmptyStr | None
    value_pct: NonEmptyStr | None
    above_count: Annotated[int, Field(ge=0)]
    down_count: Annotated[int, Field(ge=0)]
    flat_count: Annotated[int, Field(ge=0)]
    covered_count: Annotated[int, Field(ge=0)]
    universe_size: PositiveInt
    coverage_pct: NonEmptyStr
    coverage_threshold: NonEmptyStr
    coverage_threshold_pct: NonEmptyStr
    calculation: FrozenStrMapping | None


class MarketsDiscardedTicker(ContractModel):
    """One universe ticker excluded from the overview, with its reason.

    ``missing_close``: fewer than the two required closes in the window —
    the ticker is counted here, never interpolated.
    """

    ticker: NonEmptyStr
    reason: NonEmptyStr


class MarketsRejectedRecord(ContractModel):
    """One observation refused by the deny-by-default gates, with its reason."""

    event_id: NonEmptyStr
    reason: NonEmptyStr


class MarketsCoverage(ContractModel):
    """Expected / received / covered / discarded account of the universe."""

    expected: Annotated[int, Field(ge=0)]
    received: Annotated[int, Field(ge=0)]
    covered: Annotated[int, Field(ge=0)]
    discarded: Annotated[int, Field(ge=0)]
    discarded_tickers: tuple[MarketsDiscardedTicker, ...]
    rejected_records: tuple[MarketsRejectedRecord, ...]
    observations_considered: Annotated[int, Field(ge=0)]
    lookback_seconds: PositiveInt


class MarketsOverviewResponse(ContractModel):
    """The last ``markets_overview/global`` snapshot — or an honest empty state.

    ``state = "empty"`` means NO snapshot was ever published: every
    snapshot-derived field is ``None`` (never zero, never invented) and
    ``reason`` says why. ``state = "ok"`` relays the persisted content
    verbatim: population (``SYNTHETIC`` shown as-is), the worker's own
    ``data_state`` (``ok``/``partial``/``stale``), the deterministic French
    conclusion sentence, sectors/tickers, breadth and the coverage account.

    ``state = "stale"`` relaie le MÊME contenu, mais dit que l'instantané
    a dépassé son budget de fraîcheur (daily_bar) : le worker n'a rien
    publié de plus récent. ``age_seconds`` est publié dans TOUS les états
    datables — son absence faisait passer un instantané de trois jours
    pour un instantané d'une minute.
    """

    state: Literal["ok", "stale", "empty"]
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    population: NonEmptyStr | None
    data_state: Literal["ok", "partial", "stale"] | None
    unit: NonEmptyStr | None
    display_unit: NonEmptyStr | None
    engine_version: NonEmptyStr | None
    conclusion: NonEmptyStr | None
    sectors: tuple[MarketsSector, ...]
    breadth: MarketsBreadth | None
    coverage: MarketsCoverage | None
    reason: NonEmptyStr | None


# ---------------------------------------------------------------------------
# GET /api/v1/analysis/{instrument} — last published dossier, verbatim
# ---------------------------------------------------------------------------


class AnalysisResponse(ContractModel):
    """The last ``analysis/{instrument}`` snapshot — or an honest empty state.

    ``state = "empty"`` means NO dossier was ever published for this
    instrument: every snapshot-derived field is ``None`` (never invented)
    and ``reason`` says why. ``state = "ok"`` relays the persisted content
    verbatim:

    - ``advice`` is the canonical ``AdviceResult`` produced by THE single
      ``AdviceEngine`` — status, direction, the ten gates with their reason
      codes, limitations — exactly as published; the API neither recomputes
      nor softens it;
    - ``bars`` carries the admitted, validated OHLCV series (decimal strings)
      with its per-bar discard account; its observation may belong to a
      ``REAL`` or ``SYNTHETIC`` population, relayed separately;
    - ``indicators`` carries the technical indicators computed by the
      approved engine (``market.realized_volatility``, ``market.atr``), each
      with its ``CalculationRecord`` lineage — or a NAMED absence
      (``INSUFFICIENT_SAMPLE``) when the declared window exceeds the
      available history. No interpretation is published: a value, never a
      level, a regime or a signal;
    - ``evidence`` is the fusion-cluster rail of the instrument;
    - ``scenarios`` is either the ``THEORETICAL`` scenario grid with its
      ``CalculationRecord`` lineage or an honest ``ABSENT`` block with its
      typed reason.

    ``state = "stale"`` relaie le MÊME contenu, mais dit que l'instantané
    a dépassé son budget de fraîcheur (daily_bar) : le worker n'a rien
    publié de plus récent. ``age_seconds`` est publié dans TOUS les états
    datables — son absence faisait passer un instantané de trois jours
    pour un instantané d'une minute.
    """

    state: Literal["ok", "stale", "empty"]
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    population: NonEmptyStr | None
    instrument: NonEmptyStr
    engine_version: NonEmptyStr | None
    bars: FrozenStrMapping | None
    indicators: FrozenStrMapping | None
    evidence: FrozenStrMapping | None
    scenarios: FrozenStrMapping | None
    advice: FrozenStrMapping | None
    coverage: FrozenStrMapping | None
    reason: NonEmptyStr | None


# ---------------------------------------------------------------------------
# GET /api/v1/sources/sec/{instrument}/fundamentals — official PIT evidence
# ---------------------------------------------------------------------------


class SecFundamentalsResponse(ContractModel):
    """Official SEC filings and XBRL facts, relayed without financial logic."""

    state: Literal["ok", "stale", "empty"]
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    population: NonEmptyStr | None
    instrument: NonEmptyStr
    source: NonEmptyStr | None
    rights: NonEmptyStr | None
    identity_state: Literal["RESOLVED", "CONFLICTING_IDENTITY", "ABSENT"] | None
    cik: NonEmptyStr | None
    entity_name: NonEmptyStr | None
    data_as_of: UtcDatetime | None
    filings: tuple[FrozenStrMapping, ...]
    facts: tuple[FrozenStrMapping, ...]
    conflicts: tuple[FrozenStrMapping, ...]
    coverage: FrozenStrMapping | None
    reason: NonEmptyStr | None


# ---------------------------------------------------------------------------
# GET /api/v1/options/{underlying}/chain — last published chain, verbatim
# ---------------------------------------------------------------------------


class OptionChainContract(ContractModel):
    """One option contract row, relayed from the worker snapshot verbatim.

    The COMPLETE contract identity (synthetic ``con_id``, trading class,
    strike, right, multiplier, currency, exchange, style, settlement,
    expiration) travels with every row. ``quote`` is the verbatim observed
    quote plus its quality status (``OK``/``CROSSED``/``STALE``/``MISSING``);
    ``iv`` and ``greeks`` are the worker's Vertex results — present ONLY when
    the quote was sane, labeled ``value_nature = "THEORETICAL"`` with their
    preserved ``CalculationRecord`` lineage, otherwise honestly ``ABSENT``
    with the typed refusal reason. The API recomputes nothing.
    """

    con_id: PositiveInt | None
    strike: NonEmptyStr | None
    right: Literal["CALL", "PUT"] | None
    expiration: NonEmptyStr
    trading_class: NonEmptyStr
    multiplier: PositiveInt
    currency: NonEmptyStr
    exchange: NonEmptyStr
    style: NonEmptyStr
    settlement: NonEmptyStr
    quote: FrozenStrMapping
    volume: Annotated[int, Field(ge=0)] | None
    open_interest: Annotated[int, Field(ge=0)] | None
    open_interest_status: NonEmptyStr | None
    iv: FrozenStrMapping
    greeks: FrozenStrMapping
    synthetic: bool


class OptionChainExpiration(ContractModel):
    """One ``(expiration, trading_class)`` group — never merged by date.

    Two trading classes at the same expiration date are two distinct groups
    (distinct identities). ``coverage`` is the worker's honest account:
    expected/received/valid/resolved contracts and the per-contract discard
    reasons.
    """

    expiration: NonEmptyStr
    trading_class: NonEmptyStr
    exchange: NonEmptyStr
    style: NonEmptyStr
    settlement: NonEmptyStr
    multiplier: PositiveInt
    currency: NonEmptyStr
    maturity_years: NonEmptyStr
    quality: NonEmptyStr
    source_event_id: NonEmptyStr
    contracts: tuple[OptionChainContract, ...]
    coverage: FrozenStrMapping


class OptionChainResponse(ContractModel):
    """The last ``option_chain/{underlying}`` snapshot — or an honest empty.

    ``state = "empty"`` means NO snapshot was ever published for this
    underlying: every snapshot-derived field is ``None`` (never invented) and
    ``reason`` says why. ``state = "ok"`` relays the persisted content
    verbatim: population (``REAL``/``SYNTHETIC`` shown as-is), the published
    spot, the pricing assumptions, the per-(expiration, trading_class) groups
    and the displayed row budget.

    ``state = "stale"`` relaie le MÊME contenu, mais dit que l'instantané
    a dépassé son budget de fraîcheur (option_surface) : le worker n'a rien
    publié de plus récent. ``age_seconds`` est publié dans TOUS les états
    datables — son absence faisait passer un instantané de trois jours
    pour un instantané d'une minute.
    """

    state: Literal["ok", "stale", "empty"]
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    population: NonEmptyStr | None
    underlying: NonEmptyStr
    engine_version: NonEmptyStr | None
    value_nature: Literal["THEORETICAL"] | None
    spot: FrozenStrMapping | None
    assumptions: FrozenStrMapping | None
    expirations: tuple[OptionChainExpiration, ...]
    row_budget: FrozenStrMapping | None
    coverage: FrozenStrMapping | None
    reason: NonEmptyStr | None


# ---------------------------------------------------------------------------
# GET /api/v1/system/capabilities — manifest x latest probed snapshot + health
# ---------------------------------------------------------------------------


class CapabilityStatusEntry(ContractModel):
    """One declared capability crossed with the latest persisted probe.

    A capability never probed is ``tested_status = ERROR`` with
    ``reason = "NEVER_TESTED"`` and ``tested_at = None`` — absence of a probe
    is never presented as availability.
    """

    capability_id: NonEmptyStr
    family: NonEmptyStr
    declared_mode: NonEmptyStr
    description: NonEmptyStr | None
    tested_status: SourceCapabilityStatus
    tested_at: UtcDatetime | None
    reason: NonEmptyStr | None


class DbHealth(ContractModel):
    """Result of the ``SELECT 1`` probe: ``ok`` or ``error``, nothing more."""

    status: Literal["ok", "error"]


class SnapshotHealth(ContractModel):
    """Presence and age of one published snapshot head (no content)."""

    present: bool
    version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    """May be negative under clock drift — reported honestly, never clamped."""


class WorkerHealth(ContractModel):
    """Honest worker liveness proxy: the age of the freshest snapshot.

    The worker exposes no direct heartbeat; the method label
    ``heartbeat_proxy`` names that limitation explicitly instead of
    pretending to observe the process.
    """

    method: Literal["heartbeat_proxy"]
    last_snapshot_as_of: UtcDatetime | None
    age_seconds: int | None
    """May be negative under clock drift — reported honestly, never clamped."""


class SystemHealth(ContractModel):
    """Health blocks: database, both snapshot heads, worker proxy."""

    db: DbHealth
    attention_snapshot: SnapshotHealth
    capabilities_snapshot: SnapshotHealth
    worker: WorkerHealth


class SystemCapabilitiesResponse(ContractModel):
    """Every declared capability with its really-tested status, plus health.

    ``total`` equals the exact number of manifest entries; ``as_of`` and
    ``snapshot_version`` describe the persisted capabilities snapshot
    (``None`` when never published). ``unknown_probed_capability_ids`` lists
    probed ids absent from the manifest — never silently dropped, never
    merged into the declared set. ``checked_at`` is the response instant.

    ``age_seconds`` dit depuis combien de temps cette matrice a été publiée.
    Aucun état ``stale`` n'est ajouté ici et ce n'est PAS un oubli : la
    péremption d'une capacité est portée champ par champ par le
    ``expires_at`` de la sonde qui l'a établie. Déclarer un budget de relais
    pour cette famille inventerait un TTL que le registre ne contient pas.
    """

    checked_at: UtcDatetime
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    total: Annotated[int, Field(ge=0)]
    capabilities: tuple[CapabilityStatusEntry, ...]
    unknown_probed_capability_ids: tuple[NonEmptyStr, ...]
    health: SystemHealth
