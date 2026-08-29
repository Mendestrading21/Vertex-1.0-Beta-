import { useMatches } from 'react-router-dom';

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
 * Barre de contexte — page courante et état de connexion API.
 * L'état affiché est honnête : aucun client API n'est configuré dans ce socle,
 * donc « API non connectée ». Il deviendra dynamique quand un backend réel
 * fournira un statut (jamais déduit ni simulé côté interface).
 */
export function ContextBar() {
  const matches = useMatches();
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
      <p className="vx-contextbar-status">
        <span className="vx-status-dot" aria-hidden="true" />
        API non connectée
      </p>
    </header>
  );
}
