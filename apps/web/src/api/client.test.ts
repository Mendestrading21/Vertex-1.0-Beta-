import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  ApiError,
  CSRF_HEADER_NAME,
  getAttention,
  getCapabilities,
  isApiError,
  postLogout,
  readCsrfCookie,
  sessionStore,
} from './client.ts';

/** Réponse JSON synthétique (fixture SYNTHETIC de test, jamais en production). */
function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function clearCsrfCookie(): void {
  document.cookie = 'vertex_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
}

describe('client API — transport', () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
    sessionStore.reset();
    clearCsrfCookie();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    clearCsrfCookie();
  });

  it('GET : credentials include, base /api, aucun en-tête CSRF', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ state: 'empty' }));
    await getAttention();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/v1/today/attention');
    expect(init?.credentials).toBe('include');
    const headers = init?.headers as Record<string, string>;
    expect(headers[CSRF_HEADER_NAME]).toBeUndefined();
  });

  it('mutation : recopie le cookie CSRF lisible dans X-Vertex-CSRF', async () => {
    document.cookie = 'vertex_csrf=jeton-csrf-synthetique';
    expect(readCsrfCookie()).toBe('jeton-csrf-synthetique');
    fetchMock.mockResolvedValueOnce(jsonResponse({ logged_out: true }));
    await postLogout();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/v1/auth/logout');
    expect(init?.method).toBe('POST');
    const headers = init?.headers as Record<string, string>;
    expect(headers[CSRF_HEADER_NAME]).toBe('jeton-csrf-synthetique');
  });

  it('mutation sans cookie CSRF : aucun en-tête inventé', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ logged_out: true }));
    await postLogout();
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = init?.headers as Record<string, string>;
    expect(headers[CSRF_HEADER_NAME]).toBeUndefined();
  });

  it('401 → ApiError AUTH_REQUIRED et session observée « unauthenticated »', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: { code: 'AUTH_REQUIRED', message: 'authentication required' } }, 401),
    );
    const failure = await getCapabilities().catch((error: unknown) => error);
    expect(isApiError(failure)).toBe(true);
    expect((failure as ApiError).kind).toBe('AUTH_REQUIRED');
    expect((failure as ApiError).status).toBe(401);
    expect(sessionStore.getState()).toBe('unauthenticated');
  });

  it('échec réseau → ApiError NETWORK (état hors ligne, jamais un zéro)', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));
    const failure = await getAttention().catch((error: unknown) => error);
    expect(isApiError(failure)).toBe(true);
    expect((failure as ApiError).kind).toBe('NETWORK');
    expect(sessionStore.getState()).toBe('unknown');
  });

  it('statut inattendu → ApiError HTTP avec le statut réel', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'x' }, 503));
    const failure = await getAttention().catch((error: unknown) => error);
    expect((failure as ApiError).kind).toBe('HTTP');
    expect((failure as ApiError).status).toBe(503);
  });

  it('succès d’une route protégée → session observée « authenticated »', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ state: 'empty' }));
    await getAttention();
    expect(sessionStore.getState()).toBe('authenticated');
  });
});
