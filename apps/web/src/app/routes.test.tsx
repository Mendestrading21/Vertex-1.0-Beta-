import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../test/render.tsx';
import { ALL_PAGES } from './pages.ts';

/** Pages réellement installées (routes + données + états + tests). */
const INSTALLED_KEYS = new Set([
  'today',
  'markets',
  'sources-reports',
  'options',
  'analysis',
  'simulator',
  'portfolio',
  'catalysts',
  'calendar',
  'opportunities',
  'ai',
]);

describe('routes — couverture du blueprint', () => {
  // L'INVARIANT est « aucune façade » : toute entrée du rail est une page
  // réelle. Il est inchangé.
  it('toute entrée du rail est une page réelle : aucune façade « Lot non installé »', () => {
    const missing = ALL_PAGES.filter((entry) => !INSTALLED_KEYS.has(entry.key)).map(
      (entry) => entry.key,
    );
    expect(missing).toEqual([]);
  });

  // Le COMPTE, lui, dit la vérité du moment. La cible est douze
  // (`references/pages.md`) ; le rail en porte onze pendant les absorptions,
  // et l'écart est journalisé dans docs/05-design/PAGE_ARBITRATION.md.
  // Ce test échoue si une destination apparaît ou disparaît sans que
  // l'arbitrage soit mis à jour — il n'est pas relâché, il est déplacé de
  // « combien » vers « lesquelles ».
  it('le rail porte exactement les onze destinations réelles, dans l’ordre', () => {
    expect(ALL_PAGES.map((entry) => entry.key)).toEqual([
      'today',
      'opportunities',
      'analysis',
      'options',
      'simulator',
      'calendar',
      'markets',
      'portfolio',
      'catalysts',
      'ai',
      'sources-reports',
    ]);
  });

  it('les deux destinations cibles restantes ne sont PAS présentes en façade', () => {
    const keys = new Set(ALL_PAGES.map((entry) => entry.key));
    for (const attendue of ['charts', 'risks']) {
      expect(keys.has(attendue)).toBe(false);
    }
  });
});

describe('routes — pages installées : plus de façade « Lot non installé »', () => {
  for (const page of ALL_PAGES.filter((entry) => INSTALLED_KEYS.has(entry.key))) {
    it(`${page.navPath} → ${page.title} réelle`, async () => {
      renderApp(page.navPath);
      // /markets est chargée paresseusement (React.lazy) : attendre le rendu.
      expect(
        await screen.findByRole('heading', { level: 1, name: page.title }),
      ).toBeDefined();
      expect(screen.getByText(page.question)).toBeDefined();
      expect(screen.queryByText(`NON_IMPLÉMENTÉ — ${page.lot}`)).toBeNull();
    });
  }

  it("/auth rend la page Accès (hors rail, sans façade)", () => {
    renderApp('/auth');
    expect(screen.getByRole('heading', { level: 1, name: 'Accès' })).toBeDefined();
    expect(
      screen.getByRole('button', { name: 'Créer la passkey (premier démarrage)' }),
    ).toBeDefined();
  });

  it('la racine redirige vers /today', () => {
    const { router } = renderApp('/');
    expect(router.state.location.pathname).toBe('/today');
    expect(screen.getByRole('heading', { level: 1, name: "Aujourd'hui" })).toBeDefined();
  });
});

describe('routes — paramètres optionnels arbitrés', () => {
  // Les trois pages sont chargées paresseusement (React.lazy) : attendre.
  it('/analysis/:instrument? accepte un identifiant opaque', async () => {
    renderApp('/analysis/vx-instr-0000');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Analyse' }),
    ).toBeDefined();
  });

  it('/options/:underlying? accepte un identifiant opaque', async () => {
    renderApp('/options/vx-under-0000');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Options' }),
    ).toBeDefined();
  });

  it('/simulator/:id? accepte un identifiant de brouillon', async () => {
    renderApp('/simulator/vx-draft-0000');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Simulateur' }),
    ).toBeDefined();
  });
});

describe('routes — destinations absorbées (docs/05-design/PAGE_ARBITRATION.md)', () => {
  // Règle 5 de l'arbitrage : une route retirée est remplacée par une
  // redirection permanente, jamais par un 404. Sans ce test, la redirection
  // n'est pas prouvée et un signet existant casserait en silence.
  it('/system redirige durablement vers /sources-reports', () => {
    const { router } = renderApp('/system');
    expect(router.state.location.pathname).toBe('/sources-reports');
    expect(
      screen.getByRole('heading', { level: 1, name: 'Sources & Rapports' }),
    ).toBeDefined();
  });

  it("l'ancienne adresse ne laisse pas d'entrée dans l'historique (replace)", () => {
    const { router } = renderApp('/system');
    expect(router.state.historyAction).toBe('REPLACE');
  });
});

describe('routes — inconnues', () => {
  it('une adresse inconnue mène à un état explicite, pas à une autre page', () => {
    renderApp('/inconnue');
    expect(screen.getByRole('heading', { level: 1, name: 'Page introuvable' })).toBeDefined();
  });
});
