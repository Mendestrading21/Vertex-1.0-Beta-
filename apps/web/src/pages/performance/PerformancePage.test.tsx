/**
 * Page Performance — bandeau de population non masquable, métriques brut|net
 * verbatim (statut INSUFFICIENT_DATA/INVALID affiché AVEC SA RAISON à la
 * place de toute valeur), heatmap + table équivalente (mois incomplets
 * marqués), série quotidienne exacte et export servi par l'API.
 *
 * Le moteur ECharts est REMPLACÉ par un double : jsdom n'a pas de canvas et
 * le contrat testé ici est celui de la page (Playwright couvre le rendu).
 */
import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makePerformanceContent,
  makePerformanceSnapshot,
  makePortfolioResponse,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { performanceFrameStateOf } from './PerformancePage.tsx';
import { performanceContentOf } from './performanceView.ts';

const setOption = vi.fn();
const dispose = vi.fn();
const resize = vi.fn();

vi.mock('../../charts/echartsLoader.ts', () => ({
  echarts: {
    init: vi.fn(() => ({ setOption, dispose, resize })),
  },
}));

class FakeResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('ResizeObserver', FakeResizeObserver);
  fetchMock.mockReset();
  setOption.mockClear();
  dispose.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockRoutes(handlers: { readonly performance?: () => Response } = {}): void {
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (method === 'GET' && url.endsWith('/v1/portfolio')) {
      return jsonResponse(makePortfolioResponse());
    }
    if (method === 'GET' && /\/v1\/performance\/\d+$/.test(url)) {
      return handlers.performance?.() ?? jsonResponse(makePerformanceSnapshot());
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

async function renderPerformance(): Promise<void> {
  renderApp('/performance');
  await screen.findByRole('heading', { level: 1, name: 'Performance' });
}

describe('performanceFrameStateOf', () => {
  it('relaie les états requête, empty serveur, partial sur signal serveur', () => {
    expect(performanceFrameStateOf('loading', undefined).state).toBe('loading');
    expect(performanceFrameStateOf('ready', undefined).state).toBe('error');
    expect(
      performanceFrameStateOf(
        'ready',
        makePerformanceSnapshot({ state: 'empty', content: null, reason: 'never_published' }),
      ).state,
    ).toBe('empty');
    expect(performanceFrameStateOf('ready', makePerformanceSnapshot()).state).toBe('ready');
    expect(
      performanceFrameStateOf(
        'ready',
        makePerformanceSnapshot({
          content: makePerformanceContent({
            series: {
              status: 'INSUFFICIENT_DATA',
              reason: 'multi_currency_ledger_unsupported',
              points: [],
              excluded_days: [],
            },
          }),
        }),
      ).state,
    ).toBe('partial');
  });

  it('un instantané périmé garde sa performance VISIBLE sous le bandeau', () => {
    const frame = performanceFrameStateOf(
      'ready',
      makePerformanceSnapshot({ state: 'stale', age_seconds: 300_000, reason: 'snapshot older…' }),
    );
    expect(frame.state).toBe('stale');
    expect(frame.view).not.toBeNull();
  });
});

describe('performanceView — lecture verbatim', () => {
  it('métriques relayées avec statut, raison et lignage', () => {
    const view = performanceContentOf(makePerformanceContent());
    expect(view).not.toBeNull();
    expect(view!.metrics.twr_gross.totalReturnPct).toBe('+1.41');
    expect(view!.metrics.xirr_gross.ratePct).toBe('+42.00');
    expect(view!.metrics.drawdown_gross.maxDrawdownPct).toBe('0.00');
    expect(view!.metrics.xirr_net.status).toBe('INSUFFICIENT_DATA');
    expect(view!.metrics.xirr_net.reason).toBe('no_external_cashflow');
    expect(view!.metrics.drawdown_net.status).toBe('INVALID');
    expect(view!.population).toBe('SYNTHETIC_MARKS_REAL_LEDGER');
  });
});

describe('Page Performance — état nominal', () => {
  it('bandeau population non masquable + composantes séparées', async () => {
    mockRoutes();
    await renderPerformance();
    const population = await screen.findByTestId('perf-population');
    expect(population.textContent).toContain('SYNTHETIC_MARKS_REAL_LEDGER');
    expect(within(population).getByText('SYNTHETIC')).toBeDefined();
    expect(within(population).getByText('USER_DECLARED')).toBeDefined();
  });

  it('métriques OK : valeurs serveur verbatim, définition, période et méthode+version', async () => {
    mockRoutes();
    await renderPerformance();
    await screen.findByTestId('perf-metrics');

    expect(screen.getByTestId('perf-metric-value-twr_gross').textContent).toBe('+1.41 %');
    expect(screen.getByTestId('perf-metric-value-xirr_gross').textContent).toBe('+42.00 % / an');
    expect(screen.getByTestId('perf-metric-value-drawdown_gross').textContent).toBe('0.00 %');

    const twr = screen.getByTestId('perf-metric-twr_gross');
    expect(twr.textContent).toContain('2026-08-20');
    expect(twr.textContent).toContain('2026-08-21');
    expect(within(twr).getByText('performance.twr')).toBeDefined();
    expect(twr.textContent).toContain('vertex-core/0.0-test');
  });

  it('INSUFFICIENT_DATA et INVALID : statut + raison affichés, AUCUNE valeur', async () => {
    mockRoutes();
    await renderPerformance();
    await screen.findByTestId('perf-metrics');

    const xirrNet = screen.getByTestId('perf-metric-xirr_net');
    expect(screen.queryByTestId('perf-metric-value-xirr_net')).toBeNull();
    expect(within(xirrNet).getByText('INSUFFICIENT_DATA')).toBeDefined();
    expect(xirrNet.textContent).toContain('no_external_cashflow');

    const ddNet = screen.getByTestId('perf-metric-drawdown_net');
    expect(screen.queryByTestId('perf-metric-value-drawdown_net')).toBeNull();
    expect(within(ddNet).getByText('INVALID')).toBeDefined();
    expect(ddNet.textContent).toContain('insufficient_valuations');
  });

  it('heatmap : table équivalente avec mois incomplet MARQUÉ et raisons', async () => {
    mockRoutes();
    await renderPerformance();
    const row = await screen.findByTestId('perf-month-2026-08');
    expect(within(row).getByText('+1.41')).toBeDefined();
    expect(within(row).getByText('NON — mois incomplet')).toBeDefined();
    expect(within(row).getByText('first_month_of_series')).toBeDefined();
  });

  it('série quotidienne : chaînes serveur exactes dans la table', async () => {
    mockRoutes();
    await renderPerformance();
    await screen.findByTestId('perf-gross-2026-08-20');
    expect(screen.getByTestId('perf-gross-2026-08-20').textContent).toBe('10000');
    expect(screen.getByTestId('perf-gross-2026-08-21').textContent).toBe('10140');
  });
});

describe('Page Performance — série insuffisante, vide, hors ligne', () => {
  it('série INSUFFICIENT_DATA : statut + raison à la place de la courbe', async () => {
    mockRoutes({
      performance: () =>
        jsonResponse(
          makePerformanceSnapshot({
            content: makePerformanceContent({
              series: {
                status: 'INSUFFICIENT_DATA',
                reason: 'multi_currency_ledger_unsupported',
                points: [],
                excluded_days: [],
              },
              metrics: {
                twr_gross: { status: 'INSUFFICIENT_DATA', reason: 'multi_currency_ledger_unsupported', calculation: null },
                twr_net: { status: 'INSUFFICIENT_DATA', reason: 'multi_currency_ledger_unsupported', calculation: null },
                xirr_gross: { status: 'INSUFFICIENT_DATA', reason: 'multi_currency_ledger_unsupported', calculation: null },
                xirr_net: { status: 'INSUFFICIENT_DATA', reason: 'multi_currency_ledger_unsupported', calculation: null },
                drawdown_gross: { status: 'INSUFFICIENT_DATA', reason: 'multi_currency_ledger_unsupported', calculation: null },
                drawdown_net: { status: 'INSUFFICIENT_DATA', reason: 'multi_currency_ledger_unsupported', calculation: null },
              },
              heatmap: {
                status: 'INSUFFICIENT_DATA',
                reason: 'multi_currency_ledger_unsupported',
                months: [],
                method: null,
                derived_from_calculation: null,
              },
            }),
          }),
        ),
    });
    await renderPerformance();
    const blocked = await screen.findByTestId('perf-series-blocked');
    expect(blocked.textContent).toContain('INSUFFICIENT_DATA');
    expect(blocked.textContent).toContain('multi_currency_ledger_unsupported');
    expect(screen.queryByTestId('perf-chart-canvas')).toBeNull();
    expect(screen.getByTestId('perf-heatmap-absent').textContent).toContain(
      'multi_currency_ledger_unsupported',
    );
  });

  it('empty serveur : raison affichée, rien d’inventé', async () => {
    mockRoutes({
      performance: () =>
        jsonResponse(
          makePerformanceSnapshot({ state: 'empty', content: null, reason: 'never_published' }),
        ),
    });
    await renderPerformance();
    await screen.findByText(/raison serveur : never_published/);
    expect(screen.queryByTestId('perf-metrics')).toBeNull();
  });

  it('réseau coupé → offline honnête', async () => {
    fetchMock.mockRejectedValue(new TypeError('network down'));
    await renderPerformance();
    await waitFor(() => {
      expect(document.querySelector('[data-state="offline"]')).not.toBeNull();
    });
    expect(screen.queryByTestId('perf-metrics')).toBeNull();
  });
});
