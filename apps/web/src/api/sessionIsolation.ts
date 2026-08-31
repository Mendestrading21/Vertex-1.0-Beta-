import type { QueryClient } from '@tanstack/react-query';

import { sessionStore, type SessionState } from './client.ts';

/**
 * Purge toute donnée liée à la session dès qu'une fin de session est observée.
 *
 * L'annulation est demandée avant `clear()` afin qu'une réponse tardive ne
 * puisse pas repeupler le cache après un logout ou un 401. `clear()` retire
 * immédiatement queries et mutations, ce qui force aussi le DOM à abandonner
 * les anciennes valeurs au lieu de les montrer sous une nouvelle session.
 */
export function installSessionIsolation(queryClient: QueryClient): () => void {
  let previous: SessionState = sessionStore.getState();

  function sync(): void {
    const next = sessionStore.getState();
    if (next === 'unauthenticated' && previous !== 'unauthenticated') {
      void queryClient.cancelQueries();
      queryClient.clear();
    }
    previous = next;
  }

  const unsubscribe = sessionStore.subscribe(sync);
  sync();
  return unsubscribe;
}
