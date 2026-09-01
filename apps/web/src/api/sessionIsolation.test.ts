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

  it("ne purge PAS quand il n'y a jamais eu de session", async () => {
    // RÉGRESSION MESURÉE. `sessionState` démarre à 'unknown'. Sans cookie, le
    // tout premier appel protégé reçoit 401 et passe à 'unauthenticated' :
    // la condition `previous !== 'unauthenticated'` était donc VRAIE dès ce
    // premier 401, et `clear()` effaçait la requête AVEC son erreur.
    //
    // Or `hooks.ts` dérive l'état `auth-required` de cette erreur. Effacée,
    // la page repartait en chargement, refaisait la requête, reprenait un
    // 401, purgeait à nouveau — et `[data-state="auth-required"]` n'était
    // jamais rendu. Les trois viewports d'`e2e/auth.spec.ts:14` échouaient.
    //
    // Découvrir qu'aucune session n'existe n'est pas la FIN d'une session :
    // il n'y a rien à purger, aucune donnée authentifiée n'a été servie.
    const queryClient = new QueryClient();
    const cancelSpy = vi.spyOn(queryClient, 'cancelQueries');
    const uninstall = installSessionIsolation(queryClient);
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));

    // Ce que la page a mis en cache AVANT de savoir qu'elle n'a pas de session
    // (état de chargement, erreur d'une route publique...) doit survivre.
    queryClient.setQueryData(['snapshot', 'avant-401'], { value: 'synthetic-b' });

    await expect(
      request({ method: 'GET', path: '/v1/jamais-connecte', protectedRoute: true }),
    ).rejects.toMatchObject({ kind: 'AUTH_REQUIRED' });

    expect(sessionStore.getState()).toBe('unauthenticated');
    expect(cancelSpy).not.toHaveBeenCalled();
    expect(queryClient.getQueryData(['snapshot', 'avant-401'])).toBeDefined();
    uninstall();
  });
});
