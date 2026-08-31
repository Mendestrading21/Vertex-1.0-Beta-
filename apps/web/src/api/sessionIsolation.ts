import type { QueryClient } from '@tanstack/react-query';

import { sessionStore, type SessionState } from './client.ts';

/**
 * Purge toute donnée liée à la session dès qu'une session AUTHENTIFIÉE se
 * termine — logout, expiration, ou 401 sur une session ouverte.
 *
 * L'annulation est demandée avant `clear()` afin qu'une réponse tardive ne
 * puisse pas repeupler le cache après un logout ou un 401. `clear()` retire
 * immédiatement queries et mutations, ce qui force aussi le DOM à abandonner
 * les anciennes valeurs au lieu de les montrer sous une nouvelle session.
 *
 * POURQUOI LA TRANSITION EST RESTREINTE À `authenticated`. La première version
 * purgeait sur `next === 'unauthenticated' && previous !== 'unauthenticated'`.
 * Or `sessionState` démarre à `'unknown'` : sans cookie, le tout premier appel
 * protégé recevait 401 et déclenchait donc la purge. `clear()` effaçait la
 * requête AVEC son erreur — celle dont `hooks.ts` dérive l'état
 * `auth-required`. La page repartait en chargement, refaisait l'appel,
 * reprenait un 401, purgeait à nouveau, et `[data-state="auth-required"]`
 * n'était jamais rendu. `e2e/auth.spec.ts:14` échouait sur les trois viewports.
 *
 * Découvrir qu'aucune session n'existe n'est pas la FIN d'une session : rien
 * n'a été servi sous authentification, il n'y a donc rien à purger. La
 * propriété de sécurité visée par le LOT-02 est intacte, elle est seulement
 * attachée à la transition qui la porte réellement.
 */
export function installSessionIsolation(queryClient: QueryClient): () => void {
  let previous: SessionState = sessionStore.getState();

  function sync(): void {
    const next = sessionStore.getState();
    if (next === 'unauthenticated' && previous === 'authenticated') {
      void queryClient.cancelQueries();
      queryClient.clear();
    }
    previous = next;
  }

  const unsubscribe = sessionStore.subscribe(sync);
  sync();
  return unsubscribe;
}
