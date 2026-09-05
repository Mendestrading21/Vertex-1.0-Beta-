/**
 * Fixtures SYNTHÉTIQUES de test — statut `SYNTHETIC` explicite, minimales et
 * déterministes. Aucune donnée réelle IBKR/TradingView, aucun horodatage issu
 * d'une horloge : tous les instants sont des constantes.
 */
import type {
  AiAnswer,
  AnalysisResponse,
  AttentionItem,
  AttentionSnapshot,
  CapabilityEntry,
  FreshnessPolicyView,
  MarketsBreadth,
  MarketsOverview,
  MarketsSector,
  MarketsTicker,
  OptionChainContract,
  OptionChainExpiration,
  OptionChainResponse,
  CalendarResponse,
  OpportunitiesResponse,
  SecFundamentalsResponse,
  SimulationPreviewResponse,
  SystemCapabilities,
  SystemHealth,
} from '../api/client.ts';

export const SYNTHETIC_AS_OF = '2026-08-25T12:00:00+00:00';

/**
 * Budget de fraîcheur PUBLIÉ par le serveur — coordonnées de la jauge
 * âge / TTL (`freshness_policy`). Valeurs SYNTHÉTIQUES de test : le client
 * ne recopie aucun registre et ne calcule rien à partir d'elles.
 */
export function makeFreshnessPolicy(
  overrides: Partial<FreshnessPolicyView> = {},
): FreshnessPolicyView {
  return { budget_seconds: 259200, kind: 'daily_bar', version: '1.0.0', ...overrides };
}

function makeCapabilityEntry(overrides: Partial<CapabilityEntry> = {}): CapabilityEntry {
  return {
    capability_id: 'syn_capability_a',
    family: 'market_data',
    declared_mode: 'INFORMATION_ONLY',
    description: 'SYNTHETIC — entrée de test',
    tested_status: 'ERROR',
    tested_at: null,
    reason: 'NEVER_TESTED',
    ...overrides,
  };
}

/** 14 entrées synthétiques, familles et statuts variés (comme le manifeste). */
export function makeCapabilityEntries(): CapabilityEntry[] {
  const families = ['market_data', 'historical_data', 'contract_reference', 'not_provided_by_source'];
  const statuses: CapabilityEntry['tested_status'][] = [
    'AVAILABLE',
    'DELAYED',
    'NOT_ENTITLED',
    'UNSUPPORTED',
    'ERROR',
    'MANUAL_EXPORT',
  ];
  return Array.from({ length: 14 }, (_, index) => {
    const tested = statuses[index % statuses.length]!;
    return makeCapabilityEntry({
      capability_id: `syn_capability_${String(index).padStart(2, '0')}`,
      family: families[index % families.length]!,
      tested_status: tested,
      tested_at: index % 3 === 0 ? null : SYNTHETIC_AS_OF,
      reason: index % 2 === 0 ? null : 'SYNTHETIC_REASON',
    });
  });
}

function makeSystemHealth(overrides: Partial<SystemHealth> = {}): SystemHealth {
  return {
    db: { status: 'ok' },
    attention_snapshot: { present: true, version: 3, as_of: SYNTHETIC_AS_OF, age_seconds: 120 },
    capabilities_snapshot: { present: true, version: 2, as_of: SYNTHETIC_AS_OF, age_seconds: 60 },
    worker: { method: 'heartbeat_proxy', last_snapshot_as_of: SYNTHETIC_AS_OF, age_seconds: 60 },
    ...overrides,
  };
}

export function makeCapabilities(
  overrides: Partial<SystemCapabilities> = {},
): SystemCapabilities {
  const capabilities = overrides.capabilities ?? makeCapabilityEntries();
  return {
    checked_at: SYNTHETIC_AS_OF,
    snapshot_version: 2,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    // Aucun budget de relais pour cette famille : absence DÉCLARÉE (null).
    freshness_policy: null,
    total: capabilities.length,
    capabilities,
    unknown_probed_capability_ids: [],
    health: makeSystemHealth(),
    ...overrides,
  };
}

export function makeAttentionItem(index: number, overrides: Partial<AttentionItem> = {}): AttentionItem {
  const id = `syn-item-${String(index).padStart(2, '0')}`;
  return {
    id,
    title: `[SYNTHETIC] Élément d'attention ${index}`,
    sources: ['synthetic-dev'],
    rights: ['SYNTHETIC'],
    relevance_reasons: ['SOURCE_TIER', 'FRESHNESS'],
    synthetic: true,
    provenance: {
      cluster_id: `syn-cluster-${index}`,
      member_event_ids: [`${id}-event-1`, `${id}-event-2`],
      sources: ['synthetic-dev'],
      rights: ['SYNTHETIC'],
      first_published_at: '2026-08-25T11:30:00+00:00',
      last_received_at: '2026-08-25T11:45:00+00:00',
      instrument_ref: index % 2 === 0 ? `SYN${index}` : null,
    },
    ...overrides,
  };
}

export function makeAttentionSnapshot(
  overrides: Partial<AttentionSnapshot> = {},
): AttentionSnapshot {
  const items = overrides.items ?? Array.from({ length: 3 }, (_, index) => makeAttentionItem(index));
  return {
    state: 'ok',
    snapshot_version: 3,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy({ kind: 'news_attention', budget_seconds: 3600 }),
    population: 'SYNTHETIC',
    coverage: { published_items: items.length },
    items,
    rejected_count: 0,
    reason: null,
    ...overrides,
  };
}

export function makeEmptyAttentionSnapshot(): AttentionSnapshot {
  return {
    state: 'empty',
    snapshot_version: null,
    as_of: null,
    age_seconds: null,
    freshness_policy: makeFreshnessPolicy({ kind: 'news_attention', budget_seconds: 3600 }),
    population: null,
    coverage: null,
    items: [],
    rejected_count: null,
    reason: 'no snapshot published',
  };
}

// ---------------------------------------------------------------------------
// Marchés — snapshot markets_overview SYNTHÉTIQUE (chaînes serveur verbatim)
// ---------------------------------------------------------------------------

export function makeMarketsTicker(overrides: Partial<MarketsTicker> = {}): MarketsTicker {
  return {
    ticker: 'SYN-TECH-01',
    sector: 'SYN-TECH',
    trading_day: '2026-08-24',
    previous_trading_day: '2026-08-23',
    last_close: '110.00',
    previous_close: '100.00',
    currency: 'SYN',
    return_1d: '0.10000000000000009',
    return_1d_pct: '+10.00',
    weight_in_sector: '0.709677',
    weight_in_sector_pct: '70.97',
    weight_global: '0.354838',
    weight_global_pct: '35.48',
    quality: 'VALID',
    synthetic: true,
    calculation: {
      calculation_id: 'market.simple_return',
      engine_version: 'vertex_core@0.1.0',
      method: 'simple_return p1/p0 - 1 (1 trading day)',
      input_hash: `sha256:${'a'.repeat(64)}`,
      result_hash: `sha256:${'b'.repeat(64)}`,
      status: 'OK',
    },
    ...overrides,
  };
}

export function makeMarketsSectors(): MarketsSector[] {
  return [
    {
      sector: 'SYN-ENER',
      label: 'Énergie synthétique',
      declared_count: 2,
      covered_count: 2,
      tickers: [
        makeMarketsTicker({
          ticker: 'SYN-ENER-01',
          sector: 'SYN-ENER',
          last_close: '45.00',
          previous_close: '50.00',
          return_1d: '-0.09999999999999998',
          return_1d_pct: '-10.00',
          weight_in_sector_pct: '60.00',
          weight_global_pct: '14.52',
        }),
        makeMarketsTicker({
          ticker: 'SYN-ENER-02',
          sector: 'SYN-ENER',
          last_close: '30.00',
          previous_close: '30.00',
          return_1d: '0',
          return_1d_pct: '+0.00',
          weight_in_sector_pct: '40.00',
          weight_global_pct: '9.68',
          quality: 'PARTIAL',
        }),
      ],
    },
    {
      sector: 'SYN-TECH',
      label: 'Technologie synthétique',
      declared_count: 2,
      covered_count: 2,
      tickers: [
        makeMarketsTicker(),
        makeMarketsTicker({
          ticker: 'SYN-TECH-02',
          last_close: '124.00',
          previous_close: '120.00',
          return_1d: '0.033333333333333326',
          return_1d_pct: '+3.33',
          weight_in_sector_pct: '29.03',
          weight_global_pct: '40.32',
        }),
      ],
    },
  ];
}

export function makeMarketsBreadth(overrides: Partial<MarketsBreadth> = {}): MarketsBreadth {
  return {
    status: 'OK',
    reason: null,
    value: '0.5',
    value_pct: '50.0',
    above_count: 2,
    down_count: 1,
    flat_count: 1,
    covered_count: 4,
    universe_size: 4,
    coverage_pct: '100.0',
    coverage_threshold: '0.8',
    coverage_threshold_pct: '80.0',
    calculation: {
      calculation_id: 'market.breadth',
      engine_version: 'vertex_core@0.1.0',
      method: 'participation ratio above_count / covered_count',
      input_hash: `sha256:${'c'.repeat(64)}`,
      result_hash: `sha256:${'d'.repeat(64)}`,
      status: 'OK',
    },
    ...overrides,
  };
}

export function makeMarketsOverview(overrides: Partial<MarketsOverview> = {}): MarketsOverview {
  return {
    state: 'ok',
    snapshot_version: 5,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy(),
    population: 'SYNTHETIC',
    data_state: 'ok',
    unit: 'return_ratio',
    display_unit: '%',
    engine_version: 'vertex_core@0.1.0',
    conclusion:
      'Sur 4 instruments synthétiques attendus, 4 sont couverts et 0 écartés ; ' +
      '2 en hausse, 1 en baisse, 1 stables ; breadth 50.0 % (seuil de couverture 80.0 %).',
    sectors: makeMarketsSectors(),
    breadth: makeMarketsBreadth(),
    coverage: {
      expected: 4,
      received: 4,
      covered: 4,
      discarded: 0,
      discarded_tickers: [],
      rejected_records: [],
      observations_considered: 8,
      lookback_seconds: 259200,
    },
    reason: null,
    ...overrides,
  };
}

export function makeEmptyMarketsOverview(): MarketsOverview {
  return {
    state: 'empty',
    snapshot_version: null,
    as_of: null,
    age_seconds: null,
    freshness_policy: makeFreshnessPolicy(),
    population: null,
    data_state: null,
    unit: null,
    display_unit: null,
    engine_version: null,
    conclusion: null,
    sectors: [],
    breadth: null,
    coverage: null,
    reason: 'no snapshot published',
  };
}

// ---------------------------------------------------------------------------
// Options — snapshot option_chain SYNTHÉTIQUE (chaînes serveur verbatim)
// ---------------------------------------------------------------------------

function makeCalculationMeta(id: string): Record<string, unknown> {
  return {
    calculation_id: id,
    engine_version: 'vertex_core@0.1.0',
    method: `SYNTHETIC — méthode de test ${id}`,
    input_hash: `sha256:${'e'.repeat(64)}`,
    result_hash: `sha256:${'f'.repeat(64)}`,
    status: 'OK',
  };
}

export function makeChainContract(
  overrides: Partial<OptionChainContract> = {},
): OptionChainContract {
  return {
    con_id: 900000101,
    strike: '100.00',
    right: 'CALL',
    expiration: '2026-09-26',
    trading_class: 'SYN-TECH-01',
    multiplier: 100,
    currency: 'SYN',
    exchange: 'SYNTH',
    style: 'EUROPEAN',
    settlement: 'CASH',
    quote: {
      bid: '4.10',
      ask: '4.30',
      bid_size: 10,
      ask_size: 12,
      observed_at: '2026-08-25T11:30:00+00:00',
      age_seconds: 1800,
      status: 'OK',
    },
    volume: 120,
    open_interest: 900,
    open_interest_status: 'OI_DELAYED',
    iv: {
      status: 'OK',
      value: '0.24500000000000001',
      quote_side: 'MID',
      value_nature: 'THEORETICAL',
      calculation: makeCalculationMeta('options.implied_volatility'),
    },
    greeks: {
      status: 'OK',
      delta: '0.52',
      gamma: '0.031',
      vega: '0.181',
      vega_per_point: '0.00181',
      theta: '-9.2',
      theta_per_calendar_day: '-0.0252',
      rho: '0.11',
      rho_per_bp: '0.000011',
      value_nature: 'THEORETICAL',
      calculation: makeCalculationMeta('options.greeks'),
    },
    synthetic: true,
    ...overrides,
  };
}

/** Contrat SANS IV : quote croisée → raison typée, jamais un zéro. */
export function makeAbsentIvContract(
  overrides: Partial<OptionChainContract> = {},
): OptionChainContract {
  return makeChainContract({
    con_id: 900000102,
    strike: '105.00',
    quote: {
      bid: '4.40',
      ask: '4.20',
      bid_size: 5,
      ask_size: 4,
      observed_at: '2026-08-25T11:30:00+00:00',
      age_seconds: 1800,
      status: 'CROSSED',
    },
    iv: { status: 'ABSENT', reason: 'crossed_quote' },
    greeks: { status: 'ABSENT', reason: 'iv_unresolved' },
    ...overrides,
  });
}

export function makeChainGroup(
  overrides: Partial<OptionChainExpiration> = {},
): OptionChainExpiration {
  const contracts = overrides.contracts ?? [
    makeChainContract(),
    makeChainContract({ con_id: 900000111, right: 'PUT', strike: '100.00' }),
    makeAbsentIvContract(),
  ];
  return {
    expiration: '2026-09-26',
    trading_class: 'SYN-TECH-01',
    exchange: 'SYNTH',
    style: 'EUROPEAN',
    settlement: 'CASH',
    multiplier: 100,
    currency: 'SYN',
    maturity_years: '0.0767',
    quality: 'VALID',
    source_event_id: 'synthetic-dev:1234:oc0000',
    coverage: {
      expected: contracts.length,
      quotes_received: contracts.length,
      quotes_valid: contracts.length - 1,
      iv_resolved: contracts.length - 1,
      discarded: [{ con_id: 900000102, strike: '105.00', right: 'CALL', reason: 'crossed_quote' }],
    },
    contracts,
    ...overrides,
  };
}

export function makeOptionChain(
  overrides: Partial<OptionChainResponse> = {},
): OptionChainResponse {
  const expirations = overrides.expirations ?? [
    makeChainGroup(),
    // MÊME date, AUTRE trading class : deux groupes distincts, jamais fusionnés.
    makeChainGroup({
      trading_class: 'SYN-TECH-01W',
      source_event_id: 'synthetic-dev:1234:oc0001',
      contracts: [
        makeChainContract({ con_id: 900000121, iv: { status: 'OK', value: '0.27', quote_side: 'MID', value_nature: 'THEORETICAL', calculation: makeCalculationMeta('options.implied_volatility') } }),
      ],
      coverage: { expected: 1, quotes_received: 1, quotes_valid: 1, iv_resolved: 1, discarded: [] },
    }),
    makeChainGroup({
      expiration: '2026-10-24',
      source_event_id: 'synthetic-dev:1234:oc0002',
      contracts: [makeChainContract({ con_id: 900000131 })],
      coverage: { expected: 1, quotes_received: 1, quotes_valid: 1, iv_resolved: 1, discarded: [] },
    }),
  ];
  return {
    state: 'ok',
    snapshot_version: 12,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy({ kind: 'option_surface', budget_seconds: 3600 }),
    population: 'SYNTHETIC',
    underlying: 'SYN-TECH-01',
    engine_version: 'vertex_core@0.1.0',
    value_nature: 'THEORETICAL',
    spot: {
      value: '102.50',
      currency: 'SYN',
      observed_at: '2026-08-25T11:30:00+00:00',
      source_event_id: 'synthetic-dev:1234:oc0000',
    },
    assumptions: {
      rate: '0.02',
      dividend_yield: '0.00',
      quote_side_for_iv: 'MID',
      max_quote_age_seconds: 21600,
    },
    expirations,
    row_budget: { max_rows: 240, total_rows: 5, published_rows: 5, truncated_rows: 0 },
    coverage: {
      observations_considered: 3,
      groups_published: expirations.length,
      rejected_records: [],
      lookback_seconds: 259200,
    },
    reason: null,
    ...overrides,
  };
}

export function makeEmptyOptionChain(): OptionChainResponse {
  return {
    state: 'empty',
    snapshot_version: null,
    as_of: null,
    age_seconds: null,
    freshness_policy: makeFreshnessPolicy({ kind: 'option_surface', budget_seconds: 3600 }),
    population: null,
    underlying: 'SYN-TECH-01',
    engine_version: null,
    value_nature: null,
    spot: null,
    assumptions: null,
    expirations: [],
    row_budget: null,
    coverage: null,
    reason: 'no snapshot published',
  };
}

// ---------------------------------------------------------------------------
// Analyse — dossier analysis SYNTHÉTIQUE
// ---------------------------------------------------------------------------

export function makeAnalysisBars(count = 3): Record<string, unknown> {
  const bars = Array.from({ length: count }, (_, index) => ({
    trading_day: `2026-08-${String(20 + index).padStart(2, '0')}`,
    open: `100.${String(10 + index)}`,
    high: `101.${String(10 + index)}`,
    low: `99.${String(10 + index)}`,
    close: `100.${String(50 + index)}`,
    volume: 10000 + index,
  }));
  return {
    status: 'OK',
    count,
    currency: 'SYN',
    adjustment_basis: 'synthetic-unadjusted',
    first_trading_day: bars[0]!.trading_day,
    last_trading_day: bars[bars.length - 1]!.trading_day,
    last_close: bars[bars.length - 1]!.close,
    quality: 'VALID',
    fresh: true,
    source_event_id: 'synthetic-dev:1234:db0002',
    observed_as_of: SYNTHETIC_AS_OF,
    discarded: [],
    bars,
  };
}

function makeAnalysisAdvice(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    advice_id: `sha256:${'a'.repeat(64)}`,
    instrument_id: 'SYN-TECH-01',
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    valid_until: '2026-08-25T13:00:00+00:00',
    input_snapshot_id: 'synthetic-dev:1234:db0002',
    engine_version: 'vertex_core@0.1.0',
    status: 'INSUFFICIENT_DATA',
    direction: 'UNKNOWN',
    horizon: '1d',
    risk_summary: 'SYNTHETIC development data; deterministic fixtures',
    // LOT P2b — LA PREUVE SERVIE, AUX FORMES EXACTES DU MOTEUR.
    // `observed_values` et `thresholds` sont recopiés des points de retour de
    // `vertex_core/decision/gates.py`, pas devinés :
    //   · `instrument_resolved` DEGRADE publie `identity_status` + un BOOLÉEN
    //     `resolved_with_conid: false` (gates.py:126-136) ;
    //   · `_unevaluable` (gates.py:62-69) ne publie NI observé NI seuil —
    //     c'est le cas qui prouve qu'un groupe vide n'est pas rendu ;
    //   · `snapshot_fresh_and_coherent` publie `quality` + `fresh`
    //     (gates.py:238).
    // Un `false` deviné en chaîne `'false'` aurait fait passer le test sur une
    // forme que le serveur ne publie pas.
    gates: [
      {
        gate_id: 'instrument_resolved',
        version: '1.0.0',
        status: 'DEGRADE',
        reason_code: 'RESOLVED_WITHOUT_CONID',
        message: 'identity resolved without an IBKR con_id confirmation',
        observed_values: { identity_status: 'RESOLVED', resolved_with_conid: false },
        thresholds: {},
      },
      {
        gate_id: 'entitlements_sufficient',
        version: '1.0.0',
        status: 'BLOCK',
        reason_code: 'UNEVALUABLE',
        message: 'capability_status is missing or invalid',
        observed_values: {},
        thresholds: {},
      },
      {
        gate_id: 'snapshot_fresh_and_coherent',
        version: '1.0.0',
        status: 'PASS',
        reason_code: 'FRESH_AND_COHERENT',
        message: 'snapshot is fresh and coherent',
        observed_values: { quality: 'GOOD', fresh: true },
        thresholds: {},
      },
    ],
    limitations: ['SYNTHETIC development population'],
    explanation_facts: ['3 synthetic daily bars from 2026-08-20 to 2026-08-22'],
    evidence_ids: [],
    scenario_ids: [],
    probability_evidence: null,
    supersedes: null,
    ...overrides,
  };
}

export function makeAnalysis(overrides: Partial<AnalysisResponse> = {}): AnalysisResponse {
  return {
    state: 'ok',
    snapshot_version: 16,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy(),
    population: 'SYNTHETIC',
    instrument: 'SYN-TECH-01',
    engine_version: 'vertex_core@0.1.0',
    bars: makeAnalysisBars(),
    indicators: {
      realized_volatility: {
        status: 'OK',
        window: 20,
        unit: 'annualized_ratio',
        value: '0.2795203803922421',
        value_pct: '27.95',
        calculation: {
          calculation_id: 'market.realized_volatility',
          method: 'unbiased sample stdev of daily simple returns, annualized',
          engine_version: 'vertex_core@0.1.0',
          input_hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000001',
          result_hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000002',
          status: 'OK',
        },
      },
      atr: {
        status: 'INSUFFICIENT_SAMPLE',
        lookback: 14,
        available_bars: 3,
        detail: '15 barres requises ; 3 disponibles',
      },
      rebased_comparison: {
        status: 'OK',
        benchmark: 'SYN-IDX-01',
        unit: 'index',
        base_value: '100',
        currency: 'SYN',
        adjustment_basis: 'synthetic-unadjusted',
        common_sessions: 3,
        first_trading_day: '2026-08-21',
        last_trading_day: '2026-08-24',
        series: [
          { trading_day: '2026-08-21', instrument: '100.0', benchmark: '100.0' },
          { trading_day: '2026-08-22', instrument: '96.07843137254902', benchmark: '101.5' },
          { trading_day: '2026-08-24', instrument: '102.45098039215686', benchmark: '103.0' },
        ],
        calculation: {
          calculation_id: 'market.rebased_series',
          method: 'base_value * p_i / p_0 sur les seules séances communes aux deux séries',
          engine_version: 'vertex_core@0.1.0',
          input_hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000003',
          result_hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000004',
          status: 'OK',
        },
        benchmark_calculation: {
          calculation_id: 'market.rebased_series',
          method: 'base_value * p_i / p_0 sur les seules séances communes aux deux séries',
          engine_version: 'vertex_core@0.1.0',
          input_hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000005',
          result_hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000006',
          status: 'OK',
        },
      },
    },
    evidence: {
      source: 'fusion',
      ruleset_version: '1.0.0',
      considered: 0,
      clusters_total: 0,
      clusters: [],
    },
    scenarios: { status: 'ABSENT', reason: 'no_healthy_contract' },
    advice: makeAnalysisAdvice(),
    coverage: { observations_considered: 1, rejected_records: [], lookback_seconds: 259200 },
    reason: null,
    ...overrides,
  };
}

export function makeEmptyAnalysis(): AnalysisResponse {
  return {
    state: 'empty',
    snapshot_version: null,
    as_of: null,
    age_seconds: null,
    freshness_policy: makeFreshnessPolicy(),
    population: null,
    instrument: 'SYN-TECH-01',
    engine_version: null,
    bars: null,
    indicators: null,
    evidence: null,
    scenarios: null,
    advice: null,
    coverage: null,
    reason: 'no snapshot published',
  };
}

// ---------------------------------------------------------------------------
// Faits SEC officiels — relais verbatim (LOT-A4)
// ---------------------------------------------------------------------------

/**
 * Snapshot SEC SYNTHÉTIQUE : forme du contrat, valeurs fictives. L'accession,
 * le CIK et l'URL suivent la grammaire EDGAR sans désigner un émetteur réel.
 */
export function makeSecFundamentals(
  overrides: Partial<SecFundamentalsResponse> = {},
): SecFundamentalsResponse {
  return {
    state: 'ok',
    snapshot_version: 3,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 120,
    freshness_policy: makeFreshnessPolicy({ kind: 'fundamental_filing', budget_seconds: 604800 }),
    population: 'SYNTHETIC',
    instrument: 'SYN-TECH-01',
    source: 'sec_edgar',
    rights: 'R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28',
    identity_state: 'RESOLVED',
    cik: '0000000001',
    entity_name: '[SYNTHETIC] Fictional Tech One Inc.',
    data_as_of: SYNTHETIC_AS_OF,
    filings: [
      {
        accession: '0000000001-26-000001',
        form: '10-Q',
        available_at: SYNTHETIC_AS_OF,
        primary_document_url: 'https://www.sec.gov/Archives/edgar/data/1/000000000126000001/syn.htm',
      },
    ],
    facts: [
      {
        taxonomy: 'us-gaap',
        concept: 'Assets',
        value: '110',
        unit: 'USD',
        period_end: '2026-06-30',
        available_at: SYNTHETIC_AS_OF,
        accession: '0000000001-26-000001',
      },
      {
        taxonomy: 'us-gaap',
        concept: 'Revenues',
        value: '42',
        unit: 'USD',
        period_end: '2026-06-30',
        available_at: SYNTHETIC_AS_OF,
        accession: '0000000001-26-000001',
      },
    ],
    conflicts: [],
    coverage: {
      observations_considered: 2,
      published_filings: 1,
      published_facts: 2,
      truncated_facts: 0,
      conflicting_fact_keys: 0,
      corrections_observed: 0,
    },
    reason: null,
    ...overrides,
  };
}

export function makeEmptySecFundamentals(): SecFundamentalsResponse {
  return {
    state: 'empty',
    snapshot_version: null,
    as_of: null,
    age_seconds: null,
    freshness_policy: makeFreshnessPolicy({ kind: 'fundamental_filing', budget_seconds: 604800 }),
    population: null,
    instrument: 'SYN-TECH-01',
    source: null,
    rights: null,
    identity_state: null,
    cik: null,
    entity_name: null,
    data_as_of: null,
    filings: [],
    facts: [],
    conflicts: [],
    coverage: null,
    reason: 'no snapshot published',
  };
}

// ---------------------------------------------------------------------------
// Simulateur — réponse de prévisualisation THÉORIQUE
// ---------------------------------------------------------------------------

export function makeSimulationPreview(
  overrides: Partial<SimulationPreviewResponse> = {},
): SimulationPreviewResponse {
  return {
    value_nature: 'THEORETICAL',
    defined_risk: {
      is_defined_risk: true,
      reason_code: 'DEFINED_RISK',
      detail: 'BULL_CALL_DEBIT: 1 pair(s) long K=100.00 / short K=110.00, multiplier 100',
    },
    payoff_points: [
      { spot: '0', pnl: '-400.00' },
      { spot: '90', pnl: '-400.00' },
      { spot: '100.00', pnl: '-400.00' },
      { spot: '110.00', pnl: '600.00' },
      { spot: '120', pnl: '600.00' },
    ],
    breakevens: [
      { spot: '104.00', payoff_at_spot: '0.00', bracket_low: '100.00', bracket_high: '110.00' },
    ],
    max_gain_on_grid: { pnl: '600.00', at_spot: '110.00' },
    max_loss_on_grid: { pnl: '-400.00', at_spot: '100.00' },
    scenario_spot_grid: ['90', '100', '110', '120'],
    scenario_time_grid_years: ['0.0767', '0'],
    scenario_grid: [[['-120.5', '-40.2', '210.8', '590.1'], ['-400.00', '-400.00', '600.00', '600.00']]],
    calculations: {
      payoff: makeCalculationMeta('options.payoff'),
      scenario_grid: makeCalculationMeta('options.scenario_grid'),
    },
    assumptions: {
      spot: '102.50',
      volatility: '0.25',
      rate: '0.02',
      dividend_yield: '0.00',
      fees: '0',
      spot_grid: ['90', '100', '110', '120'],
      time_grid_years: ['0.0767', '0'],
    },
    warnings: [
      'THEORETICAL values from declared assumptions; never quotes, never executable prices, no transaction capability exists',
    ],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Vague 4 — portefeuille, suivi, performance (fixtures SYNTHETIC/DEMO)
// ---------------------------------------------------------------------------

import type {
  FollowUpQueueResponse,
  LedgerTransactionEntry,
  PerformanceSnapshotResponse,
  PortfolioResponse,
} from '../api/client.ts';

export function makeLedgerEntry(
  overrides: Partial<LedgerTransactionEntry> = {},
): LedgerTransactionEntry {
  return {
    id: 1,
    kind: 'DEPOSIT',
    instrument: null,
    quantity: null,
    price: null,
    amount: '10000',
    currency: 'SYN',
    fees: '0',
    effective_at: '2026-08-20T09:00:00+00:00',
    recorded_at: '2026-08-25T10:00:00+00:00',
    source: 'MANUAL',
    note: '[SYNTHETIC] dépôt de test',
    compensates: null,
    compensated_by: null,
    ...overrides,
  };
}

/** Contenu de valorisation SYNTHETIC complet : 1 lot valorisé + 1 exclu. */
export function makeValuationContent(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    schema_version: 'vertex.portfolio-valuation/1.0',
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    engine_version: 'vertex-core/0.0-test',
    portfolio: { id: 1, name: 'main', base_currency: 'USD' },
    mark_population: 'SYNTHETIC',
    lot_method: 'fifo/1.0',
    marks: {
      status: 'OK',
      reason: null,
      source: { kind: 'markets_overview', key: 'global', snapshot_version: 7, as_of: SYNTHETIC_AS_OF },
      tickers_marked: 22,
      invalid_mark_tickers: [],
    },
    positions_by_currency: [
      {
        currency: 'SYN',
        unrealized: {
          status: 'OK',
          reason: null,
          total_unrealized: '55',
          lots: [
            {
              lot_id: 'ledger-2',
              ticker: 'SYN-TECH-01',
              quantity: '5',
              unit_cost: '100',
              mark: '111',
              market_value: '555',
              unrealized_pnl: '55',
            },
          ],
          calculation: {
            calculation_id: 'portfolio.unrealized_pnl',
            engine_version: 'vertex-core/0.0-test',
            method: 'per-lot unrealized P&L (fifo/1.0)',
            input_hash: 'sha256:aa',
            result_hash: 'sha256:bb',
            status: 'OK',
          },
        },
        realized: {
          status: 'OK',
          reason: null,
          gross_proceeds: '550',
          cost_basis: '500',
          total_fees: '1',
          total_pnl: '49',
          lots: [],
          calculation: {
            calculation_id: 'portfolio.realized_pnl',
            engine_version: 'vertex-core/0.0-test',
            method: 'per-lot realized P&L (fifo/1.0)',
            input_hash: 'sha256:cc',
            result_hash: 'sha256:dd',
            status: 'OK',
          },
        },
        concentration: {
          status: 'OK',
          reason: null,
          total_value: '555',
          weights: { 'SYN-TECH-01': '1' },
          herfindahl_index: '1',
          calculation: {
            calculation_id: 'portfolio.concentration',
            engine_version: 'vertex-core/0.0-test',
            method: 'normalized marked-value weights',
            input_hash: 'sha256:ee',
            result_hash: 'sha256:ff',
            status: 'OK',
          },
        },
      },
    ],
    excluded_lots: [
      { lot_id: 'ledger-9', ticker: 'SYN-NOMARK-01', currency: 'SYN', reason: 'missing_mark' },
    ],
    coverage: {
      events_considered: 5,
      position_events: 3,
      cash_events: 2,
      compensation_pairs: 0,
      invalid_events: [],
      invalid_positions: [],
      lots_open: 2,
      lots_valued: 1,
      lots_excluded: 1,
    },
    ...overrides,
  };
}

export function makePortfolioResponse(
  overrides: Partial<PortfolioResponse> = {},
): PortfolioResponse {
  return {
    portfolio: { id: 1, name: 'main', base_currency: 'USD' },
    transactions: [
      makeLedgerEntry(),
      makeLedgerEntry({
        id: 2,
        kind: 'BUY_RECORDED',
        instrument: { ticker: 'SYN-TECH-01' },
        quantity: '10',
        price: '100',
        amount: '-1000',
        fees: '1',
        note: '[SYNTHETIC] achat enregistré le 2026-08-20',
      }),
    ],
    lots: [],
    valuation: {
      state: 'ok',
      snapshot_version: 3,
      as_of: SYNTHETIC_AS_OF,
      age_seconds: 60,
      freshness_policy: makeFreshnessPolicy({ kind: 'portfolio_mark', budget_seconds: 86400 }),
      reason: null,
      content: makeValuationContent(),
    },
    ...overrides,
  };
}

export function makeEmptyPortfolioResponse(): PortfolioResponse {
  return makePortfolioResponse({
    transactions: [],
    valuation: {
      state: 'empty',
      snapshot_version: null,
      as_of: null,
      age_seconds: null,
      freshness_policy: makeFreshnessPolicy({ kind: 'portfolio_mark', budget_seconds: 86400 }),
      reason: 'never_published',
      content: null,
    },
  });
}

/** Contenu de file de revues SYNTHETIC : 2 thèses dont 1 due avec nouveauté. */
export function makeQueueContent(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const thesisDue = {
    thesis: {
      id: 1,
      portfolio_id: null,
      instrument: { ticker: 'SYN-TECH-01' },
      title: '[SYNTHETIC] Thèse due — rotation vers SYN-TECH-01',
      hypotheses: 'Hypothèse synthétique de test.',
      invalidation: 'Invalidée si la clôture synthétique retombe sous 90.',
      horizon: '3 mois',
      review_due_at: '2026-08-20T00:00:00+00:00',
      created_at: '2026-08-01T00:00:00+00:00',
    },
    state: {
      status: 'ACTIVE',
      review_due_at: '2026-08-20T00:00:00+00:00',
      is_due: true,
      snooze_until: null,
      last_reviewed_at: null,
      last_action: 'CREATED',
      last_recorded_at: '2026-08-01T00:00:00+00:00',
      revision_count: 1,
    },
    instrument_ticker: 'SYN-TECH-01',
    information_context: {
      population: 'SYNTHETIC',
      clusters: [
        {
          cluster_id: 'cluster-0001',
          title: '[SYNTHETIC] information de test',
          tickers: ['SYN-TECH-01'],
          synthetic: true,
          provenance: {
            member_event_ids: ['evt-1'],
            sources: ['synthetic-dev'],
            rights: ['SYNTHETIC'],
            first_published_at: '2026-08-24T10:00:00+00:00',
            last_received_at: '2026-08-24T10:05:00+00:00',
          },
        },
      ],
    },
    has_new_information: true,
    urgency_reasons: [
      {
        code: 'NEW_INFORMATION_SINCE_LAST_REVIEW',
        cluster_id: 'cluster-0001',
        last_received_at: '2026-08-24T10:05:00+00:00',
        reference_instant: '2026-08-01T00:00:00+00:00',
      },
    ],
  };
  const thesisQuiet = {
    thesis: {
      id: 2,
      portfolio_id: null,
      instrument: null,
      title: '[SYNTHETIC] Thèse sans instrument',
      hypotheses: 'Autre hypothèse synthétique.',
      invalidation: 'Invalidée si X.',
      horizon: null,
      review_due_at: null,
      created_at: '2026-08-10T00:00:00+00:00',
    },
    state: {
      status: 'ACTIVE',
      review_due_at: null,
      is_due: false,
      snooze_until: null,
      last_reviewed_at: null,
      last_action: 'CREATED',
      last_recorded_at: '2026-08-10T00:00:00+00:00',
      revision_count: 1,
    },
    instrument_ticker: null,
    information_context: { population: 'SYNTHETIC', clusters: [] },
    has_new_information: false,
    urgency_reasons: [],
  };
  return {
    schema_version: 'vertex.review-queue/1.0',
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    populations: { theses: 'USER_DECLARED', information_context: 'SYNTHETIC' },
    ordering: {
      method: 'lexicographic',
      keys: ['effective_review_due_at asc', 'base_review_due_at asc', 'last_recorded_at asc', 'thesis_id asc'],
      note: 'une nouvelle information élève l’urgence visible mais ne modifie jamais la thèse',
    },
    theses: [thesisDue, thesisQuiet],
    due: [
      {
        rank: 1,
        thesis_id: 1,
        title: '[SYNTHETIC] Thèse due — rotation vers SYN-TECH-01',
        review_due_at: '2026-08-20T00:00:00+00:00',
        overdue_seconds: 432000,
        last_recorded_at: '2026-08-01T00:00:00+00:00',
        has_new_information: true,
        urgency_reasons: thesisDue.urgency_reasons,
      },
    ],
    coverage: {
      theses_total: 2,
      due_count: 1,
      theses_with_instrument: 1,
      theses_with_new_information: 1,
      observations_considered: 3,
      content_observations: 3,
      clusters: 1,
      lookback_seconds: 86400,
    },
    ...overrides,
  };
}

export function makeFollowUpQueue(
  overrides: Partial<FollowUpQueueResponse> = {},
): FollowUpQueueResponse {
  return {
    state: 'ok',
    snapshot_version: 4,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy({ kind: 'news_attention', budget_seconds: 3600 }),
    reason: null,
    content: makeQueueContent(),
    ...overrides,
  };
}

function makePerfMetricTwr(): Record<string, unknown> {
  return {
    status: 'OK',
    reason: null,
    total_return: '0.0140909090909090909090909091',
    total_return_pct: '+1.41',
    periods: [
      { from_day: '2026-08-20', to_day: '2026-08-21', return: '0.0090909090909090909090909091' },
    ],
    cashflows_embedded_in_opening: 1,
    cashflows_after_last_valuation: 0,
    calculation: {
      calculation_id: 'performance.twr',
      engine_version: 'vertex-core/0.0-test',
      method: 'chain-linked TWR',
      input_hash: 'sha256:11',
      result_hash: 'sha256:22',
      status: 'OK',
    },
  };
}

/** Contenu performance SYNTHETIC_MARKS_REAL_LEDGER complet (2 jours). */
export function makePerformanceContent(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    schema_version: 'vertex.performance/1.0',
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    engine_version: 'vertex-core/0.0-test',
    portfolio: { id: 1, name: 'main', base_currency: 'USD' },
    population: 'SYNTHETIC_MARKS_REAL_LEDGER',
    population_components: { marks: 'SYNTHETIC', ledger: 'USER_DECLARED' },
    currency: 'SYN',
    lot_method: 'fifo/1.0',
    conventions: {
      valuation_instant: 'trading day at 23:59:59 UTC (end of day)',
      cashflow_timing: 'flux au début de la période close',
      net_definition: 'net_value(day) = gross_value(day) - frais cumulés',
      external_cashflow_kinds: ['DEPOSIT', 'WITHDRAWAL'],
      xirr_sign_convention: 'dépôt négatif, retrait positif, valeur terminale positive',
    },
    series: {
      status: 'OK',
      reason: null,
      points: [
        {
          trading_day: '2026-08-20',
          at: '2026-08-20T23:59:59+00:00',
          gross_value: '10000',
          net_value: '9999',
          cash: '9000',
          position_value: '1000',
          fees_cumulative: '1',
          lots_valued: 1,
        },
        {
          trading_day: '2026-08-21',
          at: '2026-08-21T23:59:59+00:00',
          gross_value: '10140',
          net_value: '10139',
          cash: '9000',
          position_value: '1140',
          fees_cumulative: '1',
          lots_valued: 1,
        },
      ],
      excluded_days: [],
    },
    external_cashflows: [
      {
        event_id: 1,
        kind: 'DEPOSIT',
        amount: '10000',
        currency: 'SYN',
        effective_at: '2026-08-20T09:00:00+00:00',
      },
    ],
    metrics: {
      twr_gross: makePerfMetricTwr(),
      twr_net: makePerfMetricTwr(),
      xirr_gross: {
        status: 'OK',
        reason: null,
        rate: '0.42',
        rate_pct: '+42.00',
        npv_at_rate: '0.0',
        cashflows_after_last_valuation: 0,
        calculation: {
          calculation_id: 'performance.xirr',
          engine_version: 'vertex-core/0.0-test',
          method: 'XIRR',
          input_hash: 'sha256:33',
          result_hash: 'sha256:44',
          status: 'OK',
        },
      },
      xirr_net: { status: 'INSUFFICIENT_DATA', reason: 'no_external_cashflow', calculation: null },
      drawdown_gross: {
        status: 'OK',
        reason: null,
        max_drawdown: '0',
        max_drawdown_pct: '0.00',
        peak_at: '2026-08-20T23:59:59+00:00',
        trough_at: null,
        points: [
          { trading_day: '2026-08-20', drawdown: '0' },
          { trading_day: '2026-08-21', drawdown: '0' },
        ],
        calculation: {
          calculation_id: 'performance.drawdown',
          engine_version: 'vertex-core/0.0-test',
          method: 'max drawdown',
          input_hash: 'sha256:55',
          result_hash: 'sha256:66',
          status: 'OK',
        },
      },
      drawdown_net: { status: 'INVALID', reason: 'insufficient_valuations', calculation: null },
    },
    heatmap: {
      status: 'OK',
      reason: null,
      months: [
        {
          month: '2026-08',
          return: '0.0140909090909090909090909091',
          return_pct: '+1.41',
          periods: 1,
          complete: false,
          incomplete_reasons: ['first_month_of_series', 'last_month_of_series'],
        },
      ],
      method: 'chain-linked product of the authoritative performance.twr period returns',
      derived_from_calculation: null,
    },
    coverage: {
      days_with_close: 2,
      days_valued: 2,
      days_excluded: 0,
      days_before_first_ledger_event: 0,
      coverage_ratio: '1.000000',
      events_considered: 3,
      external_cashflows: 1,
      observations_considered: 44,
      observations_truncated: false,
      rejected_records: [],
    },
    ...overrides,
  };
}

export function makePerformanceSnapshot(
  overrides: Partial<PerformanceSnapshotResponse> = {},
): PerformanceSnapshotResponse {
  return {
    portfolio_id: 1,
    state: 'ok',
    snapshot_version: 2,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy(),
    reason: null,
    content: makePerformanceContent(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Vague finale — Calendrier, Opportunités, Vertex IA
// ---------------------------------------------------------------------------

const SYNTHETIC_EVENT_UTC = '2026-09-06T15:30:00+00:00';
const SYNTHETIC_EVENT_LOCAL = '2026-09-06T17:30:00+02:00';
const SYNTHETIC_PREVIOUS_UTC = '2026-09-05T15:30:00+00:00';

/** Un événement d'agenda SYNTHÉTIQUE, forme exacte du worker. */
export function makeCalendarEvent(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    event_id: 'syn-ev-earnings-SYN-TECH-01',
    category: 'EARNINGS',
    status: 'CONFIRMED',
    title: '[SYNTHETIC] Fictional quarterly results of SYN-TECH-01',
    ticker: 'SYN-TECH-01',
    scope: 'TICKER',
    event_time_utc: SYNTHETIC_EVENT_UTC,
    event_time_local: SYNTHETIC_EVENT_LOCAL,
    exchange_timezone: 'Europe/Zurich',
    importance: { rank: 2, code: 'EARNINGS_POSITION_OR_THESIS', rule_version: 'importance_rule/1.1' },
    revisions: [],
    rejected_revisions: [],
    previous_values: [],
    revised: false,
    version_state: 'RESOLVED',
    conflicting_versions: [],
    event_context: { positions: [], theses: [], links: [] },
    synthetic: true,
    quality: 'VALID',
    fresh: true,
    stale_after: '2026-08-30T01:00:00+00:00',
    delay_status: 'UNKNOWN',
    source: 'synthetic-dev',
    rights: 'SYNTHETIC',
    source_event_id: 'synthetic-dev:1234:ev0000',
    ...overrides,
  };
}

/** Un événement RÉVISÉ : valeurs antérieures conservées et lisibles. */
export function makeRevisedCalendarEvent(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return makeCalendarEvent({
    event_id: 'syn-ev-earnings-SYN-ENER-01',
    ticker: 'SYN-ENER-01',
    revised: true,
    revisions: [
      {
        revised_at: '2026-08-28T19:00:00+00:00',
        previous_status: 'ESTIMATED',
        previous_event_time_utc: SYNTHETIC_PREVIOUS_UTC,
        reason: 'synthetic confirmation of the estimated date',
      },
    ],
    previous_values: [
      {
        source_event_id: 'synthetic-dev:1235:ev0000',
        source: 'synthetic-dev',
        as_of: '2026-08-28T19:01:59+00:00',
        status: 'ESTIMATED',
        event_time_utc: SYNTHETIC_PREVIOUS_UTC,
      },
    ],
    event_context: {
      positions: [{ portfolio_id: 1 }],
      theses: [{ thesis_id: 7, title: '[SYNTHETIC] These due', status: 'ACTIVE' }],
      links: [
        { rel: 'analysis', resource: 'analysis/SYN-ENER-01' },
        { rel: 'option_chain', resource: 'option_chain/SYN-ENER-01' },
      ],
    },
    ...overrides,
  });
}

export function makeEstimatedCalendarEvent(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return makeCalendarEvent({
    event_id: 'syn-ev-earnings-SYN-FINL-01',
    ticker: 'SYN-FINL-01',
    status: 'ESTIMATED',
    importance: { rank: 3, code: 'EARNINGS_WATCHLIST', rule_version: 'importance_rule/1.1' },
    ...overrides,
  });
}

export function makeCalendarResponse(
  overrides: Partial<CalendarResponse> = {},
): CalendarResponse {
  const agenda = [makeRevisedCalendarEvent(), makeEstimatedCalendarEvent()];
  return {
    state: 'ok',
    snapshot_version: 21,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy({ kind: 'corporate_event', budget_seconds: 86400 }),
    population: 'SYNTHETIC',
    importance_rule: {
      version: 'importance_rule/1.1',
      ranks: [
        { rank: 1, code: 'MACRO_GLOBAL', description: 'evenement macro global' },
        { rank: 2, code: 'EARNINGS_POSITION_OR_THESIS', description: 'position ou these' },
        { rank: 3, code: 'EARNINGS_WATCHLIST', description: 'watchlist declaree' },
      ],
    },
    agenda,
    categories: { EARNINGS: 2 },
    statuses: { CONFIRMED: 1, ESTIMATED: 1 },
    coverage: {
      observations_considered: 3,
      events_displayed: 2,
      events_superseded: 1,
      events_stale: 0,
      rejected_records: [],
      rejected_reasons: {},
      window_truncated: false,
    },
    window: {
      applied: false,
      from_utc: null,
      to_utc: null,
      max_days: 90,
      events_total: 2,
      events_in_window: 2,
      categories: { EARNINGS: 2 },
      statuses: { CONFIRMED: 1, ESTIMATED: 1 },
    },
    reason: null,
    ...overrides,
  };
}

export function makeNotEntitledCalendarResponse(): CalendarResponse {
  return makeCalendarResponse({
    state: 'not_entitled',
    agenda: [],
    categories: {},
    statuses: { CONFIRMED: 0, ESTIMATED: 0 },
    coverage: {
      observations_considered: 4,
      events_displayed: 0,
      events_superseded: 0,
      events_stale: 0,
      rejected_records: [],
      rejected_reasons: { rights_not_usable: 4 },
      window_truncated: false,
    },
    window: {
      applied: false,
      from_utc: null,
      to_utc: null,
      max_days: 90,
      events_total: 0,
      events_in_window: 0,
      categories: {},
      statuses: { CONFIRMED: 0, ESTIMATED: 0 },
    },
    reason: 'every considered record was rejected: rights not usable',
  });
}

/** Un candidat exclu SYNTHÉTIQUE (statut fermé, gate bloquante publiée). */
export function makeExcludedCandidate(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    ticker: 'SYN-ENER-01',
    sector: 'SYN-ENER',
    advice: {
      advice_id: 'sha256:0db1',
      status: 'INSUFFICIENT_DATA',
      direction: 'UNKNOWN',
      horizon: '3m',
      as_of: SYNTHETIC_AS_OF,
      age_seconds: 60,
      valid_until: '2026-08-25T13:00:00+00:00',
      engine_version: 'vertex_core@0.1.0',
    },
    gates: [
      { gate_id: 'instrument_resolved', status: 'DEGRADE', reason_code: 'RESOLVED_WITHOUT_CONID' },
      { gate_id: 'entitlements_sufficient', status: 'BLOCK', reason_code: 'UNEVALUABLE' },
    ],
    degraded_gates: ['instrument_resolved'],
    required_evidence: {
      regime: { present: false, detail: 'no regime assessment exists for this population' },
      sector: { present: true, detail: 'SYN-ENER' },
      price_volume: { present: true, detail: 'validated daily bars present' },
    },
    missing_evidence: ['regime'],
    evidence_cluster_ids: [],
    scenario_ids: ['sha256:4fa4'],
    bars_status: 'OK',
    scenarios_status: 'OK',
    population: 'SYNTHETIC',
    synthetic: true,
    primary_exclusion_reason: {
      gate_id: 'entitlements_sufficient',
      reason_code: 'UNEVALUABLE',
    },
    exclusion: {
      kind: 'CLOSED_STATUS',
      gate_id: 'entitlements_sufficient',
      reason_code: 'UNEVALUABLE',
      missing_evidence: ['regime'],
      detail: 'closed by gate entitlements_sufficient (UNEVALUABLE)',
    },
    ...overrides,
  };
}

export function makeOpportunitiesContent(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    schema_version: 'vertex.opportunities/1.0',
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    population: 'SYNTHETIC',
    engine_version: 'vertex_core@0.1.0',
    profile_ref: {
      id: 'equity_etf_swing_3_12m',
      version: '1.0.0',
      source: 'manifests/strategy-profiles.yaml',
      applied: ['required_evidence (admissibility of every candidate)'],
      not_applied: [{ field: 'instruments', reason: 'no instrument-class source exists' }],
    },
    calendar_ref: {
      kind: 'calendar',
      key: 'global',
      version: 21,
      snapshot_as_of: SYNTHETIC_AS_OF,
      content_as_of: SYNTHETIC_AS_OF,
      content_schema_version: 'vertex.calendar/1.0',
      status: 'USED',
      max_age_seconds: 259200,
      events_upcoming: 14,
      events_ignored_past: 0,
      events_without_ticker: 3,
      events_rejected: 0,
    },
    ordering: {
      method: 'lexicographic',
      keys: ['status_rank asc', 'degraded_gates_count asc', 'ticker asc'],
      note: 'aucun score opaque',
    },
    qualified: [],
    excluded: [makeExcludedCandidate()],
    exclusion_reasons: { 'entitlements_sufficient:UNEVALUABLE': 1 },
    limitations: ['SYNTHETIC development population'],
    coverage: {
      universe_size: 24,
      qualified_count: 0,
      excluded_count: 1,
      status_counts: { INSUFFICIENT_DATA: 1 },
      population_counts: { SYNTHETIC: 1 },
      observations_considered: 4,
      lookback_seconds: 259200,
    },
    ...overrides,
  };
}

export function makeOpportunities(
  overrides: Partial<OpportunitiesResponse> = {},
): OpportunitiesResponse {
  return {
    state: 'ok',
    snapshot_version: 37,
    as_of: SYNTHETIC_AS_OF,
    age_seconds: 60,
    freshness_policy: makeFreshnessPolicy(),
    content: makeOpportunitiesContent(),
    reason: null,
    ...overrides,
  };
}

export function makeAiAnswer(overrides: Partial<AiAnswer> = {}): AiAnswer {
  return {
    provider: 'DETERMINISTIC_TEMPLATE',
    template_version: 'vertex.ai-deterministic-template/1.0',
    subject: { kind: 'analysis', key: 'SYN-TECH-01' },
    locale: 'fr',
    state: 'ok',
    refusal_reason: null,
    as_of: SYNTHETIC_AS_OF,
    snapshot_version: 16,
    content_hash: 'sha256:dcd5',
    claims: [
      {
        text: 'Population des données : SYNTHETIC.',
        kind: 'FACT',
        evidence_refs: ['snapshot:analysis/SYN-TECH-01/v16'],
      },
    ],
    external_excerpts: [
      {
        evidence_ref: 'sha256:b41f',
        label: 'EXTERNAL_UNVERIFIED',
        excerpt: '[SYNTHETIC] &lt;script&gt;alert(1)&lt;/script&gt; titre de source',
        truncated: false,
      },
    ],
    contradictions: [
      {
        code: 'UNEVALUABLE',
        reference: 'entitlements_sufficient',
        text: 'Gate entitlements_sufficient fermée : UNEVALUABLE.',
      },
    ],
    missing_data: ['gate entitlements_sufficient : donnée requise absente (UNEVALUABLE)'],
    limitations: [
      'Fournisseur IA désactivé — décision B-05 en attente ; explication par gabarit déterministe',
      'SYNTHETIC development population',
    ],
    evidence_catalog: [
      {
        evidence_id: 'snapshot:analysis/SYN-TECH-01/v16',
        evidence_type: 'snapshot',
        path: 'analysis/SYN-TECH-01',
      },
      { evidence_id: 'sha256:b41f', evidence_type: 'news_cluster', path: 'evidence.clusters[]' },
    ],
    ...overrides,
  };
}

export function makeRefusedAiAnswer(): AiAnswer {
  return makeAiAnswer({
    state: 'refused',
    refusal_reason: 'empty or unusable corpus: nothing to explain',
    claims: [],
    external_excerpts: [],
    contradictions: [],
    missing_data: ['contenu du snapshot vide ou illisible'],
    limitations: [
      'Fournisseur IA désactivé — décision B-05 en attente ; explication par gabarit déterministe',
      'Réponse refusée : aucune affirmation produite',
    ],
    evidence_catalog: [
      {
        evidence_id: 'snapshot:analysis/SYN-TECH-01/v16',
        evidence_type: 'snapshot',
        path: 'analysis/SYN-TECH-01',
      },
    ],
  });
}
