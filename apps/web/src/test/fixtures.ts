/**
 * Fixtures SYNTHÉTIQUES de test — statut `SYNTHETIC` explicite, minimales et
 * déterministes. Aucune donnée réelle IBKR/TradingView, aucun horodatage issu
 * d'une horloge : tous les instants sont des constantes.
 */
import type {
  AttentionItem,
  AttentionSnapshot,
  CapabilityEntry,
  MarketsBreadth,
  MarketsOverview,
  MarketsSector,
  MarketsTicker,
  SystemCapabilities,
  SystemHealth,
} from '../api/client.ts';

export const SYNTHETIC_AS_OF = '2026-08-25T12:00:00+00:00';

export function makeCapabilityEntry(overrides: Partial<CapabilityEntry> = {}): CapabilityEntry {
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

export function makeSystemHealth(overrides: Partial<SystemHealth> = {}): SystemHealth {
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
