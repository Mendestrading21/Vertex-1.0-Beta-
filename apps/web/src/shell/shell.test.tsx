import { readFileSync } from 'node:fs';

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ALL_PAGES, NAV_GROUPS } from '../app/pages.ts';
import { renderApp } from '../test/render.tsx';
import { LEDGER_CODE_BY_PAGE, RAIL_COLLAPSED_STORAGE_KEY } from './AppShell.tsx';

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
    // `02` et non `07` : ordre des planches canoniques.
    expect(main.getAttribute('data-ledger-code')).toBe('TL / 02');
  });

  // L'ordre canonique lui-même, épinglé. Le garde-fou d'en dessous ne voyait
  // qu'un code ABSENT ; un code FAUX lui était invisible, et huit destinations
  // sur dix en portaient un. `08 charts` reste réservé : son absence de la
  // table est intentionnelle et vérifiée ici. `09 risks` a été installé le
  // 2026-09-01 — route, données et tests — donc il y figure désormais.
  it('les signatures suivent l’ordre des planches canoniques', () => {
    expect(LEDGER_CODE_BY_PAGE).toEqual({
      today: 'TL / 01',
      markets: 'TL / 02',
      opportunities: 'TL / 03',
      analysis: 'TL / 04',
      options: 'TL / 05',
      simulator: 'TL / 06',
      portfolio: 'TL / 07',
      risks: 'TL / 09',
      catalysts: 'TL / 10',
      calendar: 'TL / 11',
      'sources-reports': 'TL / 12',
      auth: 'TL / ACCESS',
    });
    // `08 charts` reste réservé ; `09 risks` est installé depuis le
    // 2026-09-01 (route, données et tests), donc il DOIT figurer ci-dessus.
    expect(Object.values(LEDGER_CODE_BY_PAGE)).not.toContain('TL / 08');
  });

  // DEUX sources portent le même numéro : `LEDGER_CODE_BY_PAGE` (ici) et les
  // variables `--vx-page-ledger` de global.css. Le 2026-09-01 la première a été
  // corrigée sans la seconde, et chaque page affichait `TL / 03` à côté de
  // `LEDGER 02`. Ce test lie les deux ; il aurait rendu la régression
  // impossible à livrer.
  it('les libellés CSS portent le même numéro que la table du shell', () => {
    // Chemin relatif au répertoire de vitest (apps/web) :
    // `import.meta.url` n'est pas une URL file:// sous ce runner.
    const css = readFileSync('src/styles/global.css', 'utf-8');
    const motif = /\.vx-main\[data-page='([a-z-]+)'\]\s*\{\s*--vx-page-ledger:\s*'LEDGER (\d{2})/g;
    const trouves = new Map<string, string>();
    for (const [, page, numero] of css.matchAll(motif)) {
      // Les groupes de `matchAll` sont optionnels pour TypeScript : un motif
      // qui ne capture pas rendrait `undefined`, et l'ignorer masquerait une
      // page absente du CSS.
      if (page !== undefined && numero !== undefined) {
        trouves.set(page, numero);
      }
    }
    expect(trouves.size).toBeGreaterThan(0);

    const divergences: string[] = [];
    for (const [page, numero] of trouves) {
      const code = LEDGER_CODE_BY_PAGE[page];
      if (code === undefined || code !== `TL / ${numero}`) {
        divergences.push(`${page}: CSS ${numero} vs shell ${code ?? 'absent'}`);
      }
    }
    expect(divergences).toEqual([]);
  });

  it('chaque page du rail porte le code canonique de sa clé', () => {
    const faux: string[] = [];
    for (const page of ALL_PAGES) {
      const { unmount } = renderApp(page.navPath);
      const code = screen.getByRole('main').getAttribute('data-ledger-code');
      if (code !== LEDGER_CODE_BY_PAGE[page.key]) {
        faux.push(`${page.key}: ${code}`);
      }
      unmount();
    }
    expect(faux).toEqual([]);
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

  // Point 7 de l'anatomie canonique. Le DOM est vérifié ici ; le POSITIONNEMENT
  // réel (bas à gauche) et les styles calculés le sont dans
  // e2e/shell-canonical.spec.ts, que jsdom ne peut pas mesurer.
  it('le cartouche d’édition est rendu dans le rail, pas dans l’en-tête', () => {
    renderApp('/today');
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' });
    expect(within(nav).getByText('Vertex 1.0 Beta')).toBeDefined();
    expect(within(screen.getByRole('banner')).queryByText('Vertex 1.0 Beta')).toBeNull();
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
    // Onze destinations : douze en cible, moins Graphiques qui attend encore
    // son contrat serveur. Risques a ete installe le 2026-09-01 avec sa route,
    // ses donnees et ses tests — la condition posee dans app/pages.ts.
    // Le compte exact est asséré dans routes.test.tsx, avec la liste ordonnée.
    expect(ALL_PAGES).toHaveLength(11);
    // `/ai` a quitté le rail au LOT-12 : l'explication vit dans l'inspecteur.
    expect(ALL_PAGES.map((page) => page.navPath)).not.toContain('/ai');
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
