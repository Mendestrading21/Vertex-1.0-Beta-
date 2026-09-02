/**
 * Page Graphiques (LOT-A2) — la planche §8 est COMPLÈTE : douze modules
 * présents, trois servis par le contrat Analyse, neuf déclarés absents avec
 * un motif du vocabulaire fermé. Une seule dominante. Aucune valeur inventée.
 *
 * Le moteur Lightweight Charts est REMPLACÉ par un double : jsdom n'a pas de
 * canvas ; le rendu réel est couvert par Playwright (`e2e/charts.spec.ts`).
 */
import { screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { makeAnalysis, makeEmptyAnalysis, makeMarketsOverview } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { CHARTS_MODULES, absentModules } from './chartsView.ts';

vi.mock('../../charts/lightweightChartsLoader.ts', () => ({
  CandlestickSeries: { name: 'Candlestick' },
  HistogramSeries: { name: 'Histogram' },
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({ setData: vi.fn() })),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    remove: vi.fn(),
  })),
}));

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Une Response FRAÎCHE par appel, routée par URL (un corps ne se lit qu'une fois). */
function repondre(reponse: Response): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/markets/overview')) {
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    }
    return Promise.resolve(reponse.clone());
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderCharts(path = '/charts/SYN-TECH-01'): Promise<void> {
  renderApp(path);
  await screen.findByRole('heading', { level: 1, name: 'Graphiques' });
}

describe('Graphiques — la planche §8 est complète, servie ou déclarée', () => {
  it('sans instrument : question, sélecteur, état vide explicite, et les modules absents déjà présents', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderCharts('/charts');
    expect(
      screen.getByText('Quelles relations puis-je explorer sans perdre méthode et contexte ?'),
    ).toBeDefined();
    expect(screen.getByRole('navigation', { name: 'Instruments disponibles' })).toBeDefined();
    expect(screen.getByText(/Aucun instrument sélectionné/)).toBeDefined();
    // Les absences sont déclarées même sans instrument : leur motif ne dépend
    // pas de la série ouverte, il dépend de ce que le dépôt publie.
    for (const module of absentModules()) {
      expect(document.querySelector(`[data-module="${module.id}"]`)).not.toBeNull();
    }
  });

  it('avec un dossier publié : les DOUZE modules de la planche sont rendus', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderCharts();
    await screen.findByRole('heading', { level: 2, name: /Graphiques — SYN-TECH-01/ });
    for (const module of CHARTS_MODULES) {
      expect(
        document.querySelector(`[data-module="${module.id}"]`),
        `module « ${module.title} » (${module.id}) absent du DOM`,
      ).not.toBeNull();
    }
  });

  it('une seule dominante rendue : l’espace graphique', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderCharts();
    await screen.findByRole('heading', { level: 2, name: /Graphiques — SYN-TECH-01/ });
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.getAttribute('data-module')).toBe('main-chart');
  });

  it('chaque module absent porte son titre, sa question et le libellé de son motif fermé', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderCharts();
    await screen.findByRole('heading', { level: 2, name: /Graphiques — SYN-TECH-01/ });
    for (const module of absentModules()) {
      const conteneur = document.querySelector(`[data-module="${module.id}"]`);
      expect(conteneur).not.toBeNull();
      const zone = within(conteneur as HTMLElement);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(module.question)).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByText(module.status.note)).toBeDefined();
    }
  });

  it('la comparaison base 100 dit « CONTRAT SERVEUR ABSENT », pas « aucune source »', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderCharts();
    await screen.findByRole('heading', { level: 2, name: /Graphiques — SYN-TECH-01/ });
    const zone = within(document.querySelector('[data-module="comparison"]') as HTMLElement);
    expect(zone.getByText(ABSENCE_REASONS.SERVER_CONTRACT_MISSING.label)).toBeDefined();
    expect(zone.queryByText(ABSENCE_REASONS.NO_SOURCE.label)).toBeNull();
  });

  it('l’inspecteur porte la DÉFINITION de la série : devise, base, fraîcheur, référence, exclusions', async () => {
    const dossier = makeAnalysis();
    repondre(jsonResponse(dossier));
    await renderCharts();
    const definition = await screen.findByTestId('charts-series-definition');
    const zone = within(definition);
    expect(zone.getByText(/clôtures journalières OHLCV de SYN-TECH-01/)).toBeDefined();
    const devise = typeof dossier.bars?.['currency'] === 'string' ? dossier.bars['currency'] : null;
    if (devise !== null) {
      expect(zone.getAllByText(devise).length).toBeGreaterThan(0);
    }
    // Aucun tiret ambigu : une valeur absente est DITE « non publié ».
    expect(definition.textContent).not.toContain('—');
  });

  it('dossier vide serveur : état empty avec la raison publiée, aucune série inventée', async () => {
    repondre(jsonResponse(makeEmptyAnalysis()));
    await renderCharts();
    expect(await screen.findByText(/Aucun dossier publié pour « SYN-TECH-01 »/)).toBeDefined();
    expect(document.querySelector('[data-module="main-chart"]')).toBeNull();
  });

  it('hors ligne : état offline explicite, rien d’autre', async () => {
    fetchMock.mockImplementation((entree: unknown) => {
      const url = typeof entree === 'string' ? entree : String((entree as Request).url);
      if (url.includes('/markets/overview')) {
        return Promise.resolve(jsonResponse(makeMarketsOverview()));
      }
      throw new TypeError('Failed to fetch');
    });
    await renderCharts();
    expect(await screen.findByText(/L'API locale est injoignable/)).toBeDefined();
    expect(document.querySelector('[data-module="main-chart"]')).toBeNull();
  });
});
