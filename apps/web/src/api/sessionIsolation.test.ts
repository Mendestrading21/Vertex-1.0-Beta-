import { QueryClient } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { request, sessionStore } from './client.ts';
import { installSessionIsolation } from './sessionIsolation.ts';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('isolation des sessions', () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
    sessionStore.reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('purge immédiatement queries et mutations après un 401', async () => {
    const queryClient = new QueryClient();
    const cancelSpy = vi.spyOn(queryClient, 'cancelQueries');
    const uninstall = installSessionIsolation(queryClient);
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ value: 'synthetic-a' }))
      .mockResolvedValueOnce(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));

    await request({ method: 'GET', path: '/v1/synthetic-a', protectedRoute: true });
    queryClient.setQueryData(['snapshot', 'sensitive-a'], { value: 'synthetic-a' });
    expect(queryClient.getQueryData(['snapshot', 'sensitive-a'])).toBeDefined();

    await expect(
      request({ method: 'GET', path: '/v1/session-expired', protectedRoute: true }),
    ).rejects.toMatchObject({ kind: 'AUTH_REQUIRED' });

    expect(cancelSpy).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(['snapshot', 'sensitive-a'])).toBeUndefined();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    expect(queryClient.getMutationCache().getAll()).toHaveLength(0);
    uninstall();
  });
});
