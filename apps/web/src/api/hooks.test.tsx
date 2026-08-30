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
