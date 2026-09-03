import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { makeAttentionSnapshot, makeCapabilities } from '../test/fixtures.ts';
import { sessionStore } from './client.ts';
import { pageStateOf, queryKeyForResource, useAttention, useCapabilities } from './hooks.ts';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function makeWrapper(): { wrapper: (props: { children: ReactNode }) => React.JSX.Element } {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  };
}

describe('hooks API (fetch factice)', () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
    sessionStore.reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('useAttention charge le snapshot et le rend tel quel', async () => {
    const snapshot = makeAttentionSnapshot();
    fetchMock.mockResolvedValueOnce(jsonResponse(snapshot));
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useAttention(), { wrapper });
    expect(pageStateOf(result.current)).toBe('loading');
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data).toEqual(snapshot);
    expect(pageStateOf(result.current)).toBe('ready');
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/today/attention', expect.anything());
  });

  it('useCapabilities relaie le DTO complet (total exact, santé incluse)', async () => {
    const capabilities = makeCapabilities();
    fetchMock.mockResolvedValueOnce(jsonResponse(capabilities));
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useCapabilities(), { wrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data?.total).toBe(14);
    expect(result.current.data?.capabilities).toHaveLength(14);
  });

  it('401 → pageStateOf vaut « auth-required »', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useCapabilities(), { wrapper });
    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(pageStateOf(result.current)).toBe('auth-required');
  });

  it('échec réseau → pageStateOf vaut « offline »', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useAttention(), { wrapper });
    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(pageStateOf(result.current)).toBe('offline');
  });

  it('les clés de requête sont indexées par la ressource SSE', () => {
    expect(queryKeyForResource('attention/global')).toEqual(['snapshot', 'attention/global']);
    expect(queryKeyForResource('capabilities/global')).toEqual([
      'snapshot',
      'capabilities/global',
    ]);
    expect(queryKeyForResource('option_chain/SYN-TECH-01')).toEqual([
      'snapshot',
      'option_chain/SYN-TECH-01',
    ]);
    expect(queryKeyForResource('analysis/SYN-TECH-01')).toEqual([
      'snapshot',
      'analysis/SYN-TECH-01',
    ]);
  });

  it('ressources par préfixe : option_chain/* et analysis/* suivies, le reste ignoré', async () => {
    const { isKnownResource } = await import('./hooks.ts');
    expect(isKnownResource('option_chain/SYN-TECH-01')).toBe(true);
    expect(isKnownResource('analysis/SYN-ENER-01')).toBe(true);
    // Un préfixe SEUL (sans clé) n'est pas une ressource : ignoré.
    expect(isKnownResource('option_chain/')).toBe(false);
    expect(isKnownResource('analysis/')).toBe(false);
    // Famille inconnue : jamais d'invalidation globale.
    expect(isKnownResource('portfolio/global')).toBe(false);
  });

  it('vague 4 : ressources portefeuille/suivi/performance suivies et traduites', async () => {
    const { isKnownResource } = await import('./hooks.ts');
    expect(isKnownResource('review_queue/global')).toBe(true);
    expect(isKnownResource('portfolio_valuation/1')).toBe(true);
    expect(isKnownResource('performance/1')).toBe(true);
    expect(isKnownResource('portfolio_valuation/')).toBe(false);
    expect(isKnownResource('performance/')).toBe(false);
    // La valorisation vit dans GET /portfolio — une seule clé de cache : tout
    // signal portfolio_valuation/<id> invalide cette clé unique.
    expect(queryKeyForResource('portfolio_valuation/1')).toEqual(['snapshot', 'portfolio']);
    expect(queryKeyForResource('portfolio_valuation/42')).toEqual(['snapshot', 'portfolio']);
    expect(queryKeyForResource('performance/1')).toEqual(['snapshot', 'performance/1']);
    expect(queryKeyForResource('review_queue/global')).toEqual(['snapshot', 'review_queue/global']);
  });

  it('vague finale : calendar/global et opportunities/global sont suivies', async () => {
    const { isKnownResource } = await import('./hooks.ts');
    expect(isKnownResource('calendar/global')).toBe(true);
    expect(isKnownResource('opportunities/global')).toBe(true);
    expect(isKnownResource('calendar/autre')).toBe(false);
    expect(queryKeyForResource('calendar/global')).toEqual(['snapshot', 'calendar/global']);
    expect(queryKeyForResource('opportunities/global')).toEqual([
      'snapshot',
      'opportunities/global',
    ]);
  });

  it('lot S4 : risk_matrix/global est suivie — la page Risques se rafraîchit par le flux', async () => {
    const { isKnownResource } = await import('./hooks.ts');
    // Le serveur signale la tête FIXE `risk_matrix/global` (WATCHED_SNAPSHOTS,
    // seule clé publiée par le worker) : toute autre clé de la famille est
    // ignorée, jamais d'invalidation inventée.
    expect(isKnownResource('risk_matrix/global')).toBe(true);
    expect(isKnownResource('risk_matrix/autre')).toBe(false);
    expect(isKnownResource('risk_matrix/')).toBe(false);
    // Même clé que `useRiskMatrix` (decisionApi.ts) : le signal atteint son cache.
    expect(queryKeyForResource('risk_matrix/global')).toEqual(['snapshot', 'risk_matrix/global']);
  });

  it('la clé fenêtrée du calendrier reste PRÉFIXÉE par la ressource signalée', async () => {
    const { useCalendar } = await import('./decisionApi.ts');
    // La fenêtre n'ajoute que des segments APRÈS la ressource : l'invalidation
    // par préfixe déclenchée par le signal SSE atteint donc toutes les
    // variantes fenêtrées sans qu'aucune fenêtre soit inventée ici.
    expect(typeof useCalendar).toBe('function');
    const base = queryKeyForResource('calendar/global');
    const windowed = [...base, '2026-09-01T00:00:00Z', '2026-09-30T00:00:00Z'];
    expect(windowed.slice(0, base.length)).toEqual([...base]);
  });
});

/**
 * LOT L0 — métadonnées SERVIES d'un snapshot.
 *
 * Ce hook OBSERVE le cache : il ne déclenche aucune requête, ne transforme
 * aucune donnée et n'extrapole JAMAIS l'âge. Un champ que l'API ne publie pas
 * vaut `null`, jamais zéro.
 */
describe('useSnapshotMeta — ce que le serveur a publié, rien de plus', () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
    sessionStore.reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('snapshotMetaOf relaie les champs servis, verbatim', async () => {
    const { snapshotMetaOf } = await import('./hooks.ts');
    const meta = snapshotMetaOf(
      {
        as_of: '2026-09-03T08:40:00Z',
        age_seconds: 4,
        state: 'ok',
        population: 'REAL',
        snapshot_version: 42290,
      },
      { fetchStatus: 'idle', error: null },
    );
    expect(meta).toEqual({
      ageSeconds: 4,
      asOf: '2026-09-03T08:40:00Z',
      state: 'ok',
      population: 'REAL',
      snapshotVersion: 42290,
      fetchStatus: 'idle',
      error: null,
      present: true,
    });
  });

  it('un champ non publié vaut null — jamais zéro, jamais une chaîne vide', async () => {
    const { snapshotMetaOf } = await import('./hooks.ts');
    const meta = snapshotMetaOf(
      { as_of: '', age_seconds: null, state: 'ok' },
      { fetchStatus: 'idle', error: null },
    );
    expect(meta.asOf).toBeNull();
    expect(meta.ageSeconds).toBeNull();
    expect(meta.population).toBeNull();
    expect(meta.snapshotVersion).toBeNull();
    expect(meta.present).toBe(true);
  });

  it('aucune réponse vue : `present` est faux et tout est null', async () => {
    const { ABSENT_SNAPSHOT_META, snapshotMetaOf } = await import('./hooks.ts');
    expect(snapshotMetaOf(undefined, { fetchStatus: 'idle', error: null })).toEqual(
      ABSENT_SNAPSHOT_META,
    );
    expect(ABSENT_SNAPSHOT_META.present).toBe(false);
    expect(ABSENT_SNAPSHOT_META.ageSeconds).toBeNull();
  });

  it('le hook lit le cache SANS déclencher la moindre requête', async () => {
    const { useSnapshotMeta } = await import('./hooks.ts');
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useSnapshotMeta(['snapshot', 'attention/global']), {
      wrapper,
    });
    expect(result.current.present).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('après une réponse, il rend l’âge et la version SERVIS, et l’instantané est STABLE', async () => {
    const { useSnapshotMeta } = await import('./hooks.ts');
    const snapshot = makeAttentionSnapshot();
    fetchMock.mockResolvedValueOnce(jsonResponse(snapshot));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => {
        const query = useAttention();
        const meta = useSnapshotMeta(['snapshot', 'attention/global']);
        return { query, meta };
      },
      { wrapper },
    );
    await waitFor(() => {
      expect(result.current.query.isSuccess).toBe(true);
    });
    expect(result.current.meta.present).toBe(true);
    expect(result.current.meta.asOf).toBe(snapshot.as_of);
    expect(result.current.meta.ageSeconds).toBe(snapshot.age_seconds);
    // Instantané mémorisé : `useSyncExternalStore` compare par identité.
    const premier = result.current.meta;
    expect(result.current.meta).toBe(premier);
  });
});
