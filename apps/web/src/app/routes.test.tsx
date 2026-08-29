import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../test/render.tsx';
import { ALL_PAGES } from './pages.ts';

describe('routes — chaque page rend un « Lot non installé » honnête', () => {
  for (const page of ALL_PAGES) {
    it(`${page.navPath} → ${page.title} (${page.lot})`, () => {
      renderApp(page.navPath);
      expect(screen.getByRole('heading', { level: 1, name: page.title })).toBeDefined();
      expect(screen.getByText(`NON_IMPLÉMENTÉ — ${page.lot}`)).toBeDefined();
      expect(screen.getByText(page.question)).toBeDefined();
    });
  }

  it('la racine redirige vers /today', () => {
    const { router } = renderApp('/');
    expect(router.state.location.pathname).toBe('/today');
    expect(screen.getByRole('heading', { level: 1, name: "Aujourd'hui" })).toBeDefined();
  });
});

describe('routes — paramètres optionnels arbitrés', () => {
  it('/analysis/:instrument? accepte un identifiant opaque', () => {
    renderApp('/analysis/vx-instr-0000');
    expect(screen.getByRole('heading', { level: 1, name: 'Analyse' })).toBeDefined();
  });

  it('/options/:underlying? accepte un identifiant opaque', () => {
    renderApp('/options/vx-under-0000');
    expect(screen.getByRole('heading', { level: 1, name: 'Options' })).toBeDefined();
  });

  it('/simulator/:id? accepte un identifiant de brouillon', () => {
    renderApp('/simulator/vx-draft-0000');
    expect(screen.getByRole('heading', { level: 1, name: 'Simulateur' })).toBeDefined();
  });
});

describe('routes — inconnues', () => {
  it('une adresse inconnue mène à un état explicite, pas à une autre page', () => {
    renderApp('/inconnue');
    expect(screen.getByRole('heading', { level: 1, name: 'Page introuvable' })).toBeDefined();
  });
});
