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
  });
});
