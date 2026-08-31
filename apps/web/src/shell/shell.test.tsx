import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ALL_PAGES, NAV_GROUPS } from '../app/pages.ts';
import { renderApp } from '../test/render.tsx';
import { RAIL_COLLAPSED_STORAGE_KEY } from './AppShell.tsx';

describe('AppShell — landmarks et lien d’évitement', () => {
  it('expose nav, header (banner) et main', () => {
    renderApp('/today');
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeDefined();
    expect(screen.getByRole('banner')).toBeDefined();
    expect(screen.getByRole('main')).toBeDefined();
  });

  it('porte la signature Titanium Ledger propre à la page active', () => {
    renderApp('/markets');
    const main = screen.getByRole('main');
    expect(main.getAttribute('data-page')).toBe('markets');
    expect(main.getAttribute('data-ledger-code')).toBe('TL / 07');
  });

  // Garde-fou d'absorption : à chaque renommage de destination
  // (docs/05-design/PAGE_ARBITRATION.md) une clé oubliée dans
  // LEDGER_CODE_BY_PAGE ne casse rien — la signature retombe en silence sur
  // « TL / — ». C'est arrivé au LOT-07 avec `system`. Ce test rend la
  // régression bruyante pour les absorptions suivantes.
  it('aucune page du rail ne retombe sur la signature de repli « TL / — »', () => {
    const sansSignature: string[] = [];
    for (const page of ALL_PAGES) {
      const { unmount } = renderApp(page.navPath);
      const code = screen.getByRole('main').getAttribute('data-ledger-code');
      if (code === null || code === 'TL / —') {
        sansSignature.push(page.key);
      }
      unmount();
    }
    expect(sansSignature).toEqual([]);
  });

  it('le lien d’évitement pointe vers le contenu principal', () => {
    renderApp('/today');
    const skipLink = screen.getByRole('link', { name: 'Aller au contenu principal' });
    expect(skipLink.getAttribute('href')).toBe('#vx-main');
    expect(screen.getByRole('main').id).toBe('vx-main');
  });
});

describe('ContextBar', () => {
  it('affiche la page courante et un état de session honnête (non vérifié tant qu’aucune réponse API n’a été vue)', () => {
    renderApp('/markets');
    const banner = screen.getByRole('banner');
    expect(within(banner).getByText('Marchés')).toBeDefined();
    expect(within(banner).getByText('Session non vérifiée')).toBeDefined();
  });
});

describe('NavRail — groupes et liens', () => {
  it('rend exactement les 4 groupes canoniques dans l’ordre', () => {
    renderApp('/today');
    const groups = screen.getAllByRole('group');
    expect(groups.map((group) => group.getAttribute('aria-label'))).toEqual([
      'Décider',
      'Observer',
      'Piloter',
      'Assistance',
    ]);
    expect(NAV_GROUPS.map((group) => group.label)).toEqual([
      'Décider',
      'Observer',
      'Piloter',
      'Assistance',
    ]);
  });

  it('rend chaque destination réelle avec son chemin arbitré', () => {
    renderApp('/today');
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    for (const page of ALL_PAGES) {
      const link = within(nav).getByRole('link', { name: page.title });
      expect(link.getAttribute('href')).toBe(page.navPath);
    }
    // Onze destinations pendant les absorptions, douze en cible : le compte
    // exact est asséré dans routes.test.tsx, avec la liste ordonnée.
    expect(ALL_PAGES).toHaveLength(11);
    expect(ALL_PAGES.map((page) => page.navPath)).toContain('/ai');
    expect(ALL_PAGES.map((page) => page.navPath)).not.toContain('/vertex-ai');
  });

  it('pose aria-current="page" sur la route active uniquement', () => {
    renderApp('/calendar');
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    const active = within(nav).getByRole('link', { name: 'Calendrier' });
    expect(active.getAttribute('aria-current')).toBe('page');
    const others = within(nav)
      .getAllByRole('link')
      .filter((link) => link !== active);
    for (const link of others) {
      expect(link.getAttribute('aria-current')).toBeNull();
    }
  });

  it('navigue au clic vers une autre page', async () => {
    const user = userEvent.setup();
    renderApp('/today');
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    await user.click(within(nav).getByRole('link', { name: 'Options' }));
    // /options est chargée paresseusement (React.lazy) : attendre le rendu.
    expect(await screen.findByRole('heading', { level: 1, name: 'Options' })).toBeDefined();
  });
});

describe('NavRail — repli accessible et persisté', () => {
  it('bascule aria-expanded et persiste l’état dans localStorage', async () => {
    const user = userEvent.setup();
    renderApp('/today');
    const toggle = screen.getByRole('button', { name: 'Réduire la navigation' });
    expect(toggle.getAttribute('aria-expanded')).toBe('true');

    await user.click(toggle);
    const collapsedToggle = screen.getByRole('button', { name: 'Déployer la navigation' });
    expect(collapsedToggle.getAttribute('aria-expanded')).toBe('false');
    expect(window.localStorage.getItem(RAIL_COLLAPSED_STORAGE_KEY)).toBe('1');

    await user.click(collapsedToggle);
    expect(
      screen.getByRole('button', { name: 'Réduire la navigation' }).getAttribute('aria-expanded'),
    ).toBe('true');
    expect(window.localStorage.getItem(RAIL_COLLAPSED_STORAGE_KEY)).toBe('0');
  });

  it('restaure un rail replié depuis localStorage au montage', () => {
    window.localStorage.setItem(RAIL_COLLAPSED_STORAGE_KEY, '1');
    renderApp('/today');
    const toggle = screen.getByRole('button', { name: 'Déployer la navigation' });
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
  });

  it('replié, chaque lien conserve son intitulé complet accessible', async () => {
    const user = userEvent.setup();
    renderApp('/today');
    await user.click(screen.getByRole('button', { name: 'Réduire la navigation' }));
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    for (const page of ALL_PAGES) {
      expect(within(nav).getByRole('link', { name: page.title })).toBeDefined();
    }
  });
});

describe('NavRail — navigation clavier (flèches + Entrée)', () => {
  it('les flèches déplacent le focus entre les éléments du rail', async () => {
    const user = userEvent.setup();
    renderApp('/today');
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    const firstLink = within(nav).getByRole('link', { name: "Aujourd'hui" });
    const secondLink = within(nav).getByRole('link', { name: 'Opportunités' });

    firstLink.focus();
    await user.keyboard('{ArrowDown}');
    expect(document.activeElement).toBe(secondLink);

    await user.keyboard('{ArrowUp}');
    expect(document.activeElement).toBe(firstLink);
  });

  it('Fin et Début atteignent les extrémités, avec bouclage des flèches', async () => {
    const user = userEvent.setup();
    renderApp('/today');
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    const toggle = within(nav).getByRole('button', { name: 'Réduire la navigation' });
    const lastLink = within(nav).getByRole('link', { name: 'Sources & Rapports' });

    toggle.focus();
    await user.keyboard('{End}');
    expect(document.activeElement).toBe(lastLink);

    await user.keyboard('{ArrowDown}');
    expect(document.activeElement).toBe(toggle);

    await user.keyboard('{Home}');
    expect(document.activeElement).toBe(toggle);
  });

  it('Entrée active le lien focalisé', async () => {
    const user = userEvent.setup();
    renderApp('/today');
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    within(nav).getByRole('link', { name: 'Marchés' }).focus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('heading', { level: 1, name: 'Marchés' })).toBeDefined();
  });
});
