/**
 * Page Sources & Rapports — la planche §12 est complète, servie ou déclarée
 * (LOT-A8).
 *
 * Invariants : dix-sept modules dans le DOM, une seule dominante (le
 * registre), neuf absences au motif fermé sans chiffre — dont la santé
 * globale —, des dénombrements de statuts sondés, aucun inspecteur par défaut
 * (le témoin « aucune colonne morte » du shell lit cette page), la capacité
 * ouverte porte la description du manifeste que la matrice n'affiche pas.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { makeAttentionSnapshot, makeCapabilities, makeMarketsOverview } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { SOURCES_MODULES, absentSourcesModules } from './sourcesModules.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function servir(capabilities: unknown = makeCapabilities()): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/system/capabilities')) {
      return Promise.resolve(jsonResponse(capabilities));
    }
    if (url.includes('/attention')) {
      return Promise.resolve(jsonResponse(makeAttentionSnapshot()));
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

async function renderSources(): Promise<void> {
  renderApp('/sources-reports');
  await screen.findByRole('heading', { level: 1, name: 'Sources & Rapports' });
  await screen.findByTestId('sources-grid');
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Sources & Rapports — composition (LOT-A8)', () => {
  it('rend les DIX-SEPT modules de la planche, chacun à sa place', async () => {
    servir();
    await renderSources();
    for (const module of SOURCES_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
  });

  it('une seule dominante : le registre, qui garde la matrice et ses six en-têtes', async () => {
    servir();
    await renderSources();
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('registry');
    const table = within(dominantes[0] as HTMLElement).getByRole('table');
    expect(within(table).getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
      'capability_id',
      'Famille',
      'Mode déclaré',
      'Statut testé',
      'Raison',
      // L'unité a quitté les parenthèses du titre pour le créneau que
      // `DataTable` lui réserve, sous le nom de colonne. Le nom accessible
      // reste « tested_at UTC » — six en-têtes, mêmes noms, unité à sa place.
      'tested_at UTC',
    ]);
    // La seule table de la page reste la matrice.
    expect(screen.getAllByRole('table')).toHaveLength(1);
  });

  it('les neuf modules absents portent leur motif fermé, sans chiffre — la santé globale en tête', async () => {
    servir();
    await renderSources();
    for (const module of absentSourcesModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
    expect(cellule('global-health').getByText(ABSENCE_REASONS.NO_SOURCE.label)).toBeDefined();
  });

  it('statuts, fraîcheur, dernière vérification, versions et sondes : faits publiés, dénombrements', async () => {
    servir();
    await renderSources();
    expect(cellule('status-census').getByRole('list')).toBeDefined();
    expect(screen.getByTestId('src-status-ERROR')).toBeDefined();
    expect(screen.getByTestId('src-freshness')).toBeDefined();
    expect(screen.getByTestId('src-last-sync').textContent).toContain('v2');
    expect(screen.getByTestId('src-version-capabilities').textContent).toContain('v2');
    expect(screen.getByTestId('src-unknown-probes-empty')).toBeDefined();
    expect(screen.getByTestId('src-exports').textContent).toContain('/api/v1/portfolio/export');
    // La santé des composants garde son témoin et ses faits.
    expect(document.querySelector('.vx-health')).not.toBeNull();
    expect(screen.getByText('ok (SELECT 1)')).toBeDefined();
  });

  it('aucun inspecteur par défaut ; « Détail » ouvre la capacité avec sa description ; « Fermer » referme', async () => {
    const user = userEvent.setup();
    servir();
    await renderSources();
    expect(screen.queryByRole('heading', { level: 2, name: /^Inspecteur/ })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Inspecter syn_capability_00' }));
    const faits = await screen.findByTestId('src-capability-facts');
    expect(faits.textContent).toContain('SYNTHETIC — entrée de test');
    expect(faits.textContent).toContain('jamais sondé');
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — syn_capability_00' })).toBeDefined();
    await user.click(screen.getByRole('button', { name: 'Fermer' }));
    await waitFor(() => {
      expect(screen.queryByTestId('src-capability-facts')).toBeNull();
    });
    expect(screen.queryByRole('heading', { level: 2, name: /^Inspecteur/ })).toBeNull();
  });

  it('des sondes hors manifeste sont relayées telles quelles', async () => {
    servir(makeCapabilities({ unknown_probed_capability_ids: ['ghost_probe_a'] }));
    await renderSources();
    expect((await screen.findByTestId('src-unknown-probes')).textContent).toContain('ghost_probe_a');
  });
});
