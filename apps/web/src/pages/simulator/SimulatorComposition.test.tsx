/**
 * Page Simulateur — la planche §6 est complète, servie ou déclarée (LOT-A5).
 *
 * Invariants : quatorze modules dans le DOM, AUCUNE dominante à vide, une
 * seule après calcul (le payoff), cinq absences au motif fermé sans chiffre,
 * les modules de résultat disent « aucun calcul » avant Calculer et relaient
 * les chaînes serveur après, la grille de scénarios est rendue, l'inspecteur
 * porte l'étude, et aucune requête n'est ouverte sans sous-jacent déclaré.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { makeSimulationPreview } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { SHELL_TICKER_PATH, calledPaths, withShellTicker } from '../../test/shellQueries.ts';
import { SIMULATOR_MODULES, absentSimulatorModules } from './simulatorModules.ts';

vi.mock('../../charts/echartsLoader.ts', () => ({
  echarts: { init: vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn(), resize: vi.fn() })) },
}));

class FakeResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('ResizeObserver', FakeResizeObserver);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderSimulator(): Promise<void> {
  renderApp('/simulator');
  await screen.findByRole('heading', { level: 1, name: 'Simulateur' });
}

async function fillMinimalForm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText('Strike (décimal)'), '100.00');
  await user.type(screen.getByLabelText('Prime unitaire déclarée (décimal)'), '4.30');
  await user.type(screen.getByLabelText('Spot déclaré (décimal)'), '102.50');
  await user.type(screen.getByLabelText('Volatilité annualisée (décimal, 0.25 = 25 %/an)'), '0.25');
  await user.type(screen.getByLabelText('Taux annualisé (décimal)'), '0.02');
  await user.type(screen.getByLabelText('Rendement de dividende annualisé (décimal)'), '0.00');
  await user.type(screen.getByLabelText('Grille de spots (1 à 41 valeurs, séparées par des virgules)'), '90, 100, 110, 120');
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Simulateur — composition (LOT-A5)', () => {
  it('rend les QUATORZE modules de la planche, sans aucune dominante à vide, sans requête', async () => {
    await renderSimulator();
    for (const module of SIMULATOR_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
    expect(document.querySelectorAll('.vx-main [data-rank="dominant"]')).toHaveLength(0);
    // Sans sous-jacent déclaré, aucun catalyseur n'est cherché : la page n'a
    // lancé aucun appel hors la requête du shell.
    expect(calledPaths(fetchMock.mock.calls).filter((path) => !path.includes(SHELL_TICKER_PATH))).toEqual([]);
    expect(cellule('catalysts').getByRole('status').textContent).toContain('Aucun sous-jacent déclaré');
    for (const id of ['sim-kpi-empty', 'sim-scenarios-empty', 'sim-echo-empty', 'sim-method-empty']) {
      expect(screen.getByTestId(id).textContent).toContain('Aucun calcul effectué');
    }
  });

  it('les cinq modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    await renderSimulator();
    for (const module of absentSimulatorModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('après Calculer : une seule dominante (le payoff), grille de scénarios, résultats, écho et méthode servis', async () => {
    const user = userEvent.setup();
    fetchMock.mockImplementation(withShellTicker(() => jsonResponse(makeSimulationPreview())));
    await renderSimulator();
    await fillMinimalForm(user);
    await user.click(screen.getByRole('button', { name: 'Calculer' }));
    await screen.findByTestId('sim-result');
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('payoff');
    // Grille de scénarios : temps × spots, chaînes serveur verbatim.
    const grille = screen.getByTestId('sim-scenarios');
    expect(within(grille).getAllByRole('row')).toHaveLength(1 + 2);
    expect(grille.textContent).toContain('-120.5');
    expect(grille.textContent).toContain('590.1');
    // Méthode : lignée des calculs et nature des valeurs.
    const methode = screen.getByTestId('sim-method');
    expect(methode.textContent).toContain('options.payoff');
    expect(methode.textContent).toContain('options.scenario_grid');
    expect(methode.textContent).toContain('THEORETICAL');
    // Inspecteur : l'étude, avec la nature et le risque défini après calcul.
    const etude = screen.getByTestId('sim-study-facts');
    expect(etude.textContent).toContain('THEORETICAL');
    expect(etude.textContent).toContain('DEFINED_RISK');
    expect(etude.textContent).toContain('saisie manuelle');
  });

  it('l’inspecteur porte le contrat de l’étude avant tout calcul', async () => {
    await renderSimulator();
    const etude = await screen.findByTestId('sim-study-facts');
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Étude' })).toBeDefined();
    expect(etude.textContent).toContain('1 / 8');
    expect(etude.textContent).toContain('aucun calcul effectué');
    expect(etude.textContent).toContain('/api/v1/simulations/preview');
  });
});
