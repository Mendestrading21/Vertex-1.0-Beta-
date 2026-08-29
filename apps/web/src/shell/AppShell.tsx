import { useCallback, useState } from 'react';
import { Outlet } from 'react-router-dom';

import { ContextBar } from './ContextBar.tsx';
import { NavRail } from './NavRail.tsx';

/** Clé localStorage de l'état replié du rail. */
export const RAIL_COLLAPSED_STORAGE_KEY = 'vx.rail.collapsed';

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
        <main id="vx-main" className="vx-main" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
