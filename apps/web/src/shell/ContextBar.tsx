import { useSyncExternalStore } from 'react';
import { Link, useMatches } from 'react-router-dom';

import { sessionStore } from '../api/client.ts';
import type { SessionState } from '../api/client.ts';
import { sseLinkStore } from '../api/events.ts';
import { isKnownResource, useSnapshotMeta } from '../api/hooks.ts';
import type { PageDef } from '../app/pages.ts';
import { LiveBadge } from '../components/widgets/LiveBadge.tsx';

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

/**
 * Clé de repli quand la page n'a pas de tête fixe : elle n'est jamais
 * interrogée, donc son état de cache est vide et le badge dit « SANS SIGNAL ».
 * Un hook ne peut pas être appelé sous condition ; cette clé le remplace.
 */
const NO_RESOURCE_KEY = ['snapshot', '(aucune tête fixe)'] as const;

/** Barre de contexte — page courante, lien de signalement, état de session. */
export function ContextBar() {
  const matches = useMatches();
  const session = useSyncExternalStore(sessionStore.subscribe, sessionStore.getState);
  const link = useSyncExternalStore(sseLinkStore.subscribe, sseLinkStore.getState);
  const pageMatch = [...matches].reverse().find((match) => isPageHandle(match.handle));
  const page =
    pageMatch !== undefined && isPageHandle(pageMatch.handle) ? pageMatch.handle.page : null;
  const title = page === null ? 'Page introuvable' : page.title;
  const live = page?.live ?? null;
  const meta = useSnapshotMeta(live === null ? NO_RESOURCE_KEY : live.queryKey);
  // « Suivie » veut dire : le flux signale RÉELLEMENT cette tête aujourd'hui.
  const tracked = live?.resource !== null && live?.resource !== undefined
    ? isKnownResource(live.resource)
    : false;

  return (
    <header className="vx-contextbar">
      <div className="vx-contextbar-title">
        <span className="vx-contextbar-app" aria-hidden="true">
          Titanium Ledger
        </span>
        <span className="vx-contextbar-divider" aria-hidden="true">
          /
        </span>
        <span className="vx-contextbar-page">{title}</span>
      </div>
      <div className="vx-contextbar-meta">
        {/*
          POINT 5 DE L'ANATOMIE CANONIQUE — 2/3, et c'est dit.

          La FRAÎCHEUR et le BADGE DE MODE ont désormais un propriétaire : le
          lien de signalement (`sseLinkStore`) et les métadonnées SERVIES de la
          ressource principale de la page (`useSnapshotMeta`). La CLOCHE reste
          absente : aucune file de notifications n'existe côté contrat, et une
          cloche sans file serait une façade (article 17).

          Le badge ne dit jamais « en direct » : le flux est signal-only, il
          prouve un LIEN, pas une cotation.
        */}
        <LiveBadge session={session} link={link.link} mode={link.mode} tracked={tracked} meta={meta} />
        <p className="vx-contextbar-status" data-session={session}>
          <span className="vx-status-dot" aria-hidden="true" />
          {SESSION_LABELS[session]}
          {session === 'unauthenticated' ? <Link to="/auth">Accès</Link> : null}
        </p>
      </div>
    </header>
  );
}
