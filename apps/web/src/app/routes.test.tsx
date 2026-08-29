import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../test/render.tsx';
import { ALL_PAGES } from './pages.ts';

/** Pages réellement installées (routes + données + états + tests). */
const INSTALLED_KEYS = new Set(['today', 'markets', 'system', 'options', 'analysis', 'simulator']);

describe('routes — pages non installées : « Lot non installé » honnête', () => {
  for (const page of ALL_PAGES.filter((entry) => !INSTALLED_KEYS.has(entry.key))) {
    it(`${page.navPath} → ${page.title} (${page.lot})`, () => {
      renderApp(page.navPath);
      expect(screen.getByRole('heading', { level: 1, name: page.title })).toBeDefined();
      expect(screen.getByText(`NON_IMPLÉMENTÉ — ${page.lot}`)).toBeDefined();
      expect(screen.getByText(page.question)).toBeDefined();
    });
  }
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

describe('routes — inconnues', () => {
  it('une adresse inconnue mène à un état explicite, pas à une autre page', () => {
    renderApp('/inconnue');
    expect(screen.getByRole('heading', { level: 1, name: 'Page introuvable' })).toBeDefined();
  });
});
