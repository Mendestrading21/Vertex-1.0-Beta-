/**
 * Page Options — la planche §5 est complète, servie ou déclarée (LOT-A5).
 *
 * Invariants : quinze modules dans le DOM, une seule dominante (la chaîne),
 * six absences au motif fermé sans chiffre, le spot et les hypothèses du
 * calcul d'IV relayés verbatim, un sourire d'IV par groupe publié, un
 * inspecteur par défaut (la chaîne publiée) remplacé par le contrat ouvert.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { makeAnalysis, makeCalendarResponse, makeMarketsOverview, makeOptionChain } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { OPTIONS_MODULES, absentOptionsModules } from './optionsModules.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function servir(chain: unknown = makeOptionChain()): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/markets/overview')) {
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    }
    if (url.includes('/v1/analysis/')) {
      return Promise.resolve(jsonResponse(makeAnalysis()));
    }
    if (url.includes('/v1/calendar')) {
      return Promise.resolve(jsonResponse(makeCalendarResponse()));
    }
    return Promise.resolve(jsonResponse(chain));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderOptions(): Promise<void> {
  renderApp('/options/SYN-TECH-01');
  await screen.findByRole('heading', { level: 2, name: "Chaîne d'options — SYN-TECH-01" });
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Options — composition (LOT-A5)', () => {
  it('rend les QUINZE modules de la planche, chacun à sa place', async () => {
    servir();
    await renderOptions();
    for (const module of OPTIONS_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
  });

  it('une seule dominante : la chaîne', async () => {
    servir();
    await renderOptions();
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.getAttribute('data-module')).toBe('chain');
  });

  it('les six modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    servir();
    await renderOptions();
    for (const module of absentOptionsModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('spot, taux et dividende sont les chaînes PUBLIÉES du snapshot ; le budget et les références restent lisibles', async () => {
    servir();
    await renderOptions();
    expect(screen.getByTestId('options-spot').textContent).toContain('102,50');
    expect(screen.getByTestId('options-rate').textContent).toContain('0,02');
    expect(screen.getByTestId('options-dividend').textContent).toContain('0,00');
    expect(screen.getByTestId('chain-row-budget').textContent).toContain('plafond 240');
    expect(screen.getByTestId('chain-source-references').textContent).toContain('synthetic-dev:1234:oc0000');
  });

  it('sourire d’IV du groupe affiché et petits multiples par groupe, jamais fusionnés', async () => {
    servir();
    await renderOptions();
    const smile = cellule('iv-smile');
    expect(smile.getByTestId('iv-smile')).toBeDefined();
    // Groupe par défaut : deux IV résolues (CALL et PUT 100.00), une absente.
    expect(smile.getByTestId('iv-smile').textContent).toContain('1 sans IV');
    const multiples = cellule('vol-structure').getByTestId('options-vol-structure');
    expect(within(multiples).getAllByRole('listitem')).toHaveLength(3);
    expect(multiples.textContent).toContain('SYN-TECH-01W');
  });

  it('le sous-jacent : widget de Marchés et série du dossier', async () => {
    servir();
    await renderOptions();
    expect(await cellule('underlying').findByTestId('instrument-widget')).toBeDefined();
    expect(await cellule('underlying-series').findByTestId('options-underlying-series')).toBeDefined();
  });

  it('l’inspecteur porte la chaîne publiée ; « Détail » ouvre le contrat ; Échap y revient', async () => {
    const user = userEvent.setup();
    servir();
    await renderOptions();
    expect(await screen.findByTestId('options-snapshot-facts')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Chaîne publiée' })).toBeDefined();
    await user.click(screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!);
    await screen.findByTestId('option-inspector');
    expect(screen.queryByTestId('options-snapshot-facts')).toBeNull();
    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByTestId('option-inspector')).toBeNull();
    });
    expect(await screen.findByTestId('options-snapshot-facts')).toBeDefined();
  });
});
