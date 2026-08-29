import { useRef } from 'react';
import type { KeyboardEvent } from 'react';
import { NavLink } from 'react-router-dom';

import { NAV_GROUPS } from '../app/pages.ts';

export interface NavRailProps {
  readonly collapsed: boolean;
  readonly onToggle: () => void;
}

/**
 * Rail de navigation desktop — 232 px, rétractable à 68 px.
 * - bouton de bascule accessible (`aria-expanded`) ;
 * - navigation clavier : flèches haut/bas, Début/Fin, Entrée (activation
 *   native des liens) ;
 * - `aria-current="page"` posé par NavLink sur la route active ;
 * - en mode replié, l'intitulé complet reste l'accessible name du lien.
 */
export function NavRail({ collapsed, onToggle }: NavRailProps) {
  const navRef = useRef<HTMLElement | null>(null);

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      return;
    }
    const nav = navRef.current;
    if (nav === null) {
      return;
    }
    const items = Array.from(nav.querySelectorAll<HTMLElement>('[data-rail-focusable]'));
    if (items.length === 0) {
      return;
    }
    const active = document.activeElement;
    const current = active instanceof HTMLElement ? items.indexOf(active) : -1;
    let next: number;
    if (event.key === 'Home') {
      next = 0;
    } else if (event.key === 'End') {
      next = items.length - 1;
    } else if (current === -1) {
      next = 0;
    } else if (event.key === 'ArrowDown') {
      next = (current + 1) % items.length;
    } else {
      next = (current - 1 + items.length) % items.length;
    }
    items[next]?.focus();
    event.preventDefault();
  };

  return (
    <nav
      ref={navRef}
      className="vx-rail"
      aria-label="Navigation principale"
      onKeyDown={handleKeyDown}
    >
      <div className="vx-rail-head">
        {!collapsed && <span className="vx-rail-wordmark">Vertex</span>}
        <button
          type="button"
          className="vx-rail-toggle"
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Déployer la navigation' : 'Réduire la navigation'}
          data-rail-focusable=""
          onClick={onToggle}
        >
          <span aria-hidden="true">{collapsed ? '»' : '«'}</span>
        </button>
      </div>

      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="vx-rail-group" role="group" aria-label={group.label}>
          <p className="vx-rail-group-label" aria-hidden="true">
            {collapsed ? '·' : group.label}
          </p>
          <ul className="vx-rail-list">
            {group.pages.map((page) => (
              <li key={page.key}>
                <NavLink
                  to={page.navPath}
                  className="vx-rail-link"
                  aria-label={page.title}
                  title={collapsed ? page.title : undefined}
                  data-rail-focusable=""
                >
                  <span className="vx-rail-link-short" aria-hidden="true">
                    {page.shortLabel}
                  </span>
                  {!collapsed && (
                    <span className="vx-rail-link-label" aria-hidden="true">
                      {page.title}
                    </span>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
