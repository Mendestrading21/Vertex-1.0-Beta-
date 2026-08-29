/**
 * Fixtures SYNTHÉTIQUES de test — statut `SYNTHETIC` explicite, minimales et
 * déterministes. Aucune donnée réelle IBKR/TradingView, aucun horodatage issu
 * d'une horloge : tous les instants sont des constantes.
 */
import type {
  AttentionItem,
  AttentionSnapshot,
  CapabilityEntry,
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
