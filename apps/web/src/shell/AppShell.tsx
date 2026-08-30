import { useCallback, useState } from 'react';
import { Outlet, useMatches } from 'react-router-dom';

import type { PageDef } from '../app/pages.ts';
import { ContextBar } from './ContextBar.tsx';
import { NavRail } from './NavRail.tsx';

/** Clé localStorage de l'état replié du rail. */
export const RAIL_COLLAPSED_STORAGE_KEY = 'vx.rail.collapsed';

interface PageHandle {
  readonly page: PageDef;
}

function isPageHandle(handle: unknown): handle is PageHandle {
  return (
    typeof handle === 'object' &&
    handle !== null &&
    'page' in handle &&
    typeof (handle as { page?: { key?: unknown } }).page?.key === 'string'
  );
}

const LEDGER_CODE_BY_PAGE: Readonly<Record<string, string>> = {
  today: 'TL / 01',
  opportunities: 'TL / 02',
  analysis: 'TL / 03',
  options: 'TL / 04',
  simulator: 'TL / 05',
  calendar: 'TL / 06',
  markets: 'TL / 07',
  portfolio: 'TL / 08',
  'follow-up': 'TL / 09',
  performance: 'TL / 10',
  ai: 'TL / 11',
  system: 'TL / 12',
  auth: 'TL / ACCESS',
};

function readStoredCollapsed(): boolean {
  try {
    return window.localStorage.getItem(RAIL_COLLAPSED_STORAGE_KEY) === '1';
  } catch {
    // Stockage indisponible (navigation privée, quota) : état par défaut déployé.
    return false;
  }
}

function writeStoredCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(RAIL_COLLAPSED_STORAGE_KEY, collapsed ? '1' : '0');
  } catch {
    // Persistance impossible : l'état reste valable pour la session en cours.
  }
}

/**
 * Coquille applicative desktop : lien d'évitement, rail de navigation
 * (landmark nav), barre de contexte (landmark header) et contenu (landmark
 * main). Desktop only — aucune variante téléphone (Mobile = LATER).
 */
export function AppShell() {
  const [collapsed, setCollapsed] = useState(readStoredCollapsed);
  const matches = useMatches();
  const pageMatch = [...matches].reverse().find((match) => isPageHandle(match.handle));
  const pageKey =
    pageMatch !== undefined && isPageHandle(pageMatch.handle) ? pageMatch.handle.page.key : 'unknown';

  const toggle = useCallback(() => {
    setCollapsed((previous) => {
      const next = !previous;
      writeStoredCollapsed(next);
      return next;
    });
  }, []);

  return (
    <div className="vx-shell" data-rail={collapsed ? 'collapsed' : 'open'}>
      <a className="vx-skip-link" href="#vx-main">
        Aller au contenu principal
      </a>
      <NavRail collapsed={collapsed} onToggle={toggle} />
      <div className="vx-shell-body">
        <ContextBar />
        <main
          id="vx-main"
          className="vx-main"
          tabIndex={-1}
          data-page={pageKey}
          data-ledger-code={LEDGER_CODE_BY_PAGE[pageKey] ?? 'TL / —'}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
