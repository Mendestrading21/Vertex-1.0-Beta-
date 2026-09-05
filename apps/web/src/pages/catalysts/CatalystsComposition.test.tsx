/**
 * Page Catalyseurs — la planche §10 est complète, servie ou déclarée (LOT-A7).
 *
 * Invariants : dix-sept modules dans le DOM, une seule dominante (la
 * chronologie), six absences au motif fermé sans chiffre, des dénombrements
 * (jamais des pondérations), des filtres locaux qui masquent sans reclasser,
 * aucun inspecteur par défaut (le témoin « aucune colonne morte » du shell).
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { makeCalendarResponse, makeFollowUpQueue, makeMarketsOverview } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { CATALYSTS_MODULES, absentCatalystsModules } from './catalystsModules.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function servir(calendar: unknown = makeCalendarResponse()): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/v1/calendar')) {
      return Promise.resolve(jsonResponse(calendar));
    }
    if (url.endsWith('/v1/follow-up/queue')) {
      return Promise.resolve(jsonResponse(makeFollowUpQueue()));
    }
    return Promise.resolve(jsonResponse(makeMarketsOverview()));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderCatalysts(): Promise<void> {
  renderApp('/catalysts');
  await screen.findByRole('heading', { level: 1, name: 'Catalyseurs' });
  await screen.findByTestId('catalysts-grid');
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Catalyseurs — composition (LOT-A7)', () => {
  it('rend les DIX-SEPT modules de la planche, chacun à sa place', async () => {
    servir();
    await renderCatalysts();
    for (const module of CATALYSTS_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
  });

  it('une seule dominante : la chronologie, qui garde son témoin', async () => {
    servir();
    await renderCatalysts();
    await screen.findByTestId('cat-list');
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('timeline');
    expect(dominantes[0]?.querySelector('[data-testid="cat-unlinked"]')).not.toBeNull();
  });

  it('les six modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    servir();
    await renderCatalysts();
    for (const module of absentCatalystsModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('comptes, répartition, sources et conflits sont des dénombrements du croisement publié', async () => {
    servir();
    await renderCatalysts();
    const comptes = await screen.findByTestId('cat-count');
    expect(within(comptes).getByTestId('cat-count-linked').textContent).toContain('1');
    expect(cellule('category-split').getByRole('list')).toBeDefined();
    expect(cellule('sources-freshness').getAllByRole('list').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId('cat-conflicts')).toBeDefined();
    expect(screen.getByTestId('cat-window').textContent).toContain('v');
    expect(screen.getByTestId('cat-populations').textContent).toContain('SYNTHETIC');
  });

  it('un filtre local masque sans reclasser : la chronologie dit combien restent affichés', async () => {
    const user = userEvent.setup();
    servir();
    await renderCatalysts();
    await screen.findByTestId('cat-list');
    const liens = within(screen.getByTestId('cat-filter-links'));
    await user.click(liens.getByRole('button', { name: /thèse/i }));
    await user.click(liens.getByRole('button', { name: /position/i }));
    expect(screen.getByTestId('cat-filter-count').textContent).toContain('0 affiché(s) sur 1');
    expect(screen.getByTestId('cat-empty')).toBeDefined();
    await user.click(liens.getByRole('button', { name: /thèse/i }));
    expect(await screen.findByTestId('cat-list')).toBeDefined();
  });

  it('aucun inspecteur par défaut : la colonne reste masquée tant que rien n’est ouvert', async () => {
    servir();
    await renderCatalysts();
    await screen.findByTestId('cat-list');
    expect(screen.queryByRole('heading', { level: 2, name: /^Inspecteur/ })).toBeNull();
  });
});
