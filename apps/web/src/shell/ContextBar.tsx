import { useSyncExternalStore } from 'react';
import { Link, useMatches } from 'react-router-dom';

import { sessionStore } from '../api/client.ts';
import type { SessionState } from '../api/client.ts';
import type { PageDef } from '../app/pages.ts';

/** `handle` de route portant la définition de page (posé dans routes.tsx). */
export interface PageHandle {
  readonly page: PageDef;
}

function isPageHandle(handle: unknown): handle is PageHandle {
  if (typeof handle !== 'object' || handle === null || !('page' in handle)) {
    return false;
  }
  const page = (handle as { page: unknown }).page;
  return (
    typeof page === 'object' &&
    page !== null &&
    'title' in page &&
    typeof (page as { title: unknown }).title === 'string'
  );
}

/**
 * Libellés d'état de session — uniquement des faits observés sur l'API :
 * `unknown` tant qu'aucune réponse n'a été vue (jamais un état deviné),
 * puis « Connecté » / « Non connecté » selon les réponses réelles.
 */
const SESSION_LABELS: Readonly<Record<SessionState, string>> = {
  unknown: 'Session non vérifiée',
  authenticated: 'Connecté',
  unauthenticated: 'Non connecté',
};

/** Barre de contexte — page courante et état de session réel. */
export function ContextBar() {
  const matches = useMatches();
  const session = useSyncExternalStore(sessionStore.subscribe, sessionStore.getState);
  const pageMatch = [...matches].reverse().find((match) => isPageHandle(match.handle));
  const title =
    pageMatch !== undefined && isPageHandle(pageMatch.handle)
      ? pageMatch.handle.page.title
      : 'Page introuvable';

  return (
    <header className="vx-contextbar">
      <div className="vx-contextbar-title">
        <span className="vx-contextbar-app" aria-hidden="true">
          Vertex
        </span>
        <span className="vx-contextbar-page">{title}</span>
      </div>
      <p className="vx-contextbar-status" data-session={session}>
        <span className="vx-status-dot" aria-hidden="true" />
        {SESSION_LABELS[session]}
        {session === 'unauthenticated' ? <Link to="/auth">Accès</Link> : null}
      </p>
    </header>
  );
}
