/**
 * Page Analyse — cadre CHART_STANDARD, attribution TradingView visible,
 * table OHLCV équivalente (chaînes serveur verbatim), AdviceCard honnête
 * (INSUFFICIENT_DATA + gates UNEVALUABLE dépliables), evidence, scénarios
 * absents avec raison, états dégradés.
 *
 * Le moteur Lightweight Charts est REMPLACÉ par un double : jsdom n'a pas de
 * canvas ; le rendu réel est couvert par Playwright.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeAnalysis,
  makeAnalysisBars,
  makeEmptyAnalysis,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { analysisStateOf, barsViewOf, scenarioAbsentLabel } from './analysisView.ts';

const setData = vi.fn();
const applyOptions = vi.fn();
const fitContent = vi.fn();
const remove = vi.fn();

vi.mock('../../charts/lightweightChartsLoader.ts', () => ({
  CandlestickSeries: { name: 'Candlestick' },
  HistogramSeries: { name: 'Histogram' },
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({ setData })),
    priceScale: vi.fn(() => ({ applyOptions })),
    timeScale: vi.fn(() => ({ fitContent })),
    remove,
  })),
}));

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  setData.mockClear();
  remove.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderAnalysis(path = '/analysis/SYN-TECH-01'): Promise<void> {
  renderApp(path);
  await screen.findByRole('heading', { level: 1, name: 'Analyse' });
}

describe('analysisStateOf — dérivation depuis les statuts publiés', () => {
  it('relais des états requête et empty serveur', () => {
    expect(analysisStateOf('loading', undefined)).toBe('loading');
    expect(analysisStateOf('ready', undefined)).toBe('error');
    expect(analysisStateOf('ready', makeEmptyAnalysis())).toBe('empty');
    expect(analysisStateOf('ready', makeAnalysis())).toBe('ready');
  });

  it('fresh=false publié → stale ; barres dégradées → partial', () => {
    const stale = makeAnalysis({ bars: { ...makeAnalysisBars(), fresh: false } });
    expect(analysisStateOf('ready', stale)).toBe('stale');
    const partial = makeAnalysis({
      bars: { ...makeAnalysisBars(), discarded: [{ index: 3, reason: 'invalid_bar' }] },
    });
    expect(analysisStateOf('ready', partial)).toBe('partial');
  });
});

describe('Page Analyse — état nominal', () => {
  it('cadre complet : question, méta (unité/devise/timezone/source/as_of/couverture), SYNTHETIC', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    await screen.findByRole('heading', { level: 2, name: 'Analyse — SYN-TECH-01' });
    expect(screen.getByText(/prix OHLC en SYN/)).toBeDefined();
    expect(screen.getByText(/UTC \(stockage\)/)).toBeDefined();
    expect(screen.getByText('synthetic-dev')).toBeDefined();
    // as_of du cadre (il réapparaît aussi dans la validité de l'AdviceCard).
    expect(screen.getAllByText('2026-08-25T12:00:00+00:00').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/3 barre\(s\) valides/)).toBeDefined();
    expect(screen.getByText('DONNÉES SYNTHÉTIQUES')).toBeDefined();
  });

  it('dominante : moteur substitué monté avec les 60 barres (ici 3) + attribution TradingView', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    await screen.findByTestId('candles-canvas');
    // setData appelé pour les chandeliers ET le volume.
    expect(setData).toHaveBeenCalledTimes(2);
    const links = screen.getAllByRole('link', { name: 'TradingView' });
    expect(links.length).toBeGreaterThanOrEqual(2); // légende du cadre + pied
    for (const link of links) {
      expect(link.getAttribute('href')).toBe('https://www.tradingview.com/');
    }
    expect(screen.getAllByText(/Lightweight Charts™/).length).toBeGreaterThanOrEqual(1);
  });

  it('table OHLCV équivalente : mêmes chaînes serveur verbatim', async () => {
    const analysis = makeAnalysis();
    fetchMock.mockResolvedValue(jsonResponse(analysis));
    await renderAnalysis();
    const table = await screen.findByRole('table', {
      name: 'Table OHLCV équivalente des chandeliers',
    });
    const bars = barsViewOf(analysis);
    expect(bars).not.toBeNull();
    expect(within(table).getAllByRole('row')).toHaveLength(1 + bars!.bars.length);
    const first = bars!.bars[0]!;
    const row = within(table).getByText(first.tradingDay).closest('tr');
    expect(row?.textContent).toContain(first.open);
    expect(row?.textContent).toContain(first.high);
    expect(row?.textContent).toContain(first.low);
    expect(row?.textContent).toContain(first.close);
    expect(row?.textContent).toContain(String(first.volume));
  });

  it('AdviceCard : INSUFFICIENT_DATA honnête, direction séparée, gates UNEVALUABLE dépliables', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    const card = await screen.findByTestId('advice-card');
    const scoped = within(card);
    expect(scoped.getByText('INSUFFICIENT_DATA')).toBeDefined();
    expect(scoped.getByText(/données requises insuffisantes/)).toBeDefined();
    expect(scoped.getByText('UNKNOWN')).toBeDefined();
    expect(scoped.getByText(/aucune lecture directionnelle/)).toBeDefined();
    expect(scoped.getByText(/SYNTHETIC development population/)).toBeDefined();
    // Validité affichée (as_of → valid_until).
    expect(scoped.getByText(/horizon 1d/)).toBeDefined();
    // Gates dépliables : résumé (compte) puis détail avec reason_code exact.
    const summary = scoped.getByText(/3 évaluées, 2 non passées/);
    await user.click(summary);
    expect(scoped.getByText('entitlements_sufficient')).toBeDefined();
    expect(scoped.getAllByText('UNEVALUABLE').length).toBeGreaterThanOrEqual(1);
    expect(scoped.getByText('RESOLVED_WITHOUT_CONID')).toBeDefined();
  });

  it('evidence vide honnête + scénarios absents avec raison typée', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    await screen.findByText(/Aucun cluster pertinent/);
    const absent = await screen.findByTestId('scenarios-absent');
    expect(absent.textContent).toBe(scenarioAbsentLabel('no_healthy_contract'));
    expect(absent.textContent).toContain('no_healthy_contract');
    expect(absent.textContent).toContain('aucun contrat sain');
  });
});

describe('Page Analyse — états', () => {
  it('sans instrument : état vide explicite + sélecteur, aucun défaut implicite', async () => {
    await renderAnalysis('/analysis');
    expect(screen.getByText(/Aucun instrument sélectionné/)).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('empty honnête avec raison serveur', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeEmptyAnalysis()));
    await renderAnalysis();
    await screen.findByText('Aucune donnée');
    expect(screen.getByText(/no snapshot published/)).toBeDefined();
  });

  it('stale publié : bandeau « Données périmées », contenu conservé', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(makeAnalysis({ bars: { ...makeAnalysisBars(), fresh: false } })),
    );
    await renderAnalysis();
    await screen.findByText('Données périmées');
    expect(screen.getByText(/fresh = false/)).toBeDefined();
    expect(screen.getByRole('table', { name: /OHLCV/ })).toBeDefined();
  });

  it('offline honnête quand l’API est injoignable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    await renderAnalysis();
    await screen.findByText('Hors ligne');
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('session requise sur 401', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));
    await renderAnalysis();
    await screen.findByText('Session requise');
  });
});
