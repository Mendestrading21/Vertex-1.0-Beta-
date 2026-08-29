/**
 * Page Marchés — 8 états, cadre CHART_STANDARD, table équivalente triable,
 * BreadthPanel et absence de tout calcul financier TypeScript (les valeurs
 * affichées sont les chaînes serveur, seulement formatées).
 *
 * Le moteur ECharts est REMPLACÉ par un double : jsdom n'a pas de canvas et
 * le contrat testé ici est celui de la page, pas du rendu Canvas (couvert par
 * Playwright sur le vrai navigateur).
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeEmptyMarketsOverview,
  makeMarketsBreadth,
  makeMarketsOverview,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { frameStateOf } from './MarketsPage.tsx';

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

async function renderMarkets(): Promise<void> {
  renderApp('/markets');
  await screen.findByRole('heading', { level: 1, name: 'Marchés' });
}

describe('frameStateOf — l’état canonique du snapshot prime en succès', () => {
  it('relais des états requête hors succès', () => {
    expect(frameStateOf('loading', undefined)).toBe('loading');
    expect(frameStateOf('offline', undefined)).toBe('offline');
    expect(frameStateOf('auth-required', undefined)).toBe('auth-required');
  });

  it('succès sans données = erreur (jamais un faux succès)', () => {
    expect(frameStateOf('ready', undefined)).toBe('error');
  });

  it('empty/partial/stale viennent du serveur, jamais déduits localement', () => {
    expect(frameStateOf('ready', makeEmptyMarketsOverview())).toBe('empty');
    expect(frameStateOf('ready', makeMarketsOverview({ data_state: 'partial' }))).toBe('partial');
    expect(frameStateOf('ready', makeMarketsOverview({ data_state: 'stale' }))).toBe('stale');
    expect(frameStateOf('ready', makeMarketsOverview())).toBe('ready');
    expect(frameStateOf('refreshing', makeMarketsOverview())).toBe('refreshing');
  });
});

describe('Page Marchés — état nominal', () => {
  it('cadre complet : question, méta, bandeau SYNTHETIC, conclusion serveur, table, breadth', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();

    // Question et titre du cadre.
    await screen.findByText(
      'Comment les secteurs et instruments suivis ont-ils évolué sur la dernière séance ?',
    );
    expect(
      screen.getByRole('heading', { level: 2, name: 'Carte des marchés synthétiques' }),
    ).toBeDefined();

    // Métadonnées : unité, source, as_of, couverture.
    expect(screen.getByText(/rendement 1 jour en %/)).toBeDefined();
    expect(screen.getByText('synthetic-dev')).toBeDefined();
    expect(screen.getByText('2026-08-25T12:00:00+00:00')).toBeDefined();
    expect(screen.getByText('4/4 couverts, 0 écartés, 4 reçus')).toBeDefined();

    // Bandeau population SYNTHETIC non masquable.
    expect(screen.getByText('DONNÉES SYNTHÉTIQUES')).toBeDefined();

    // Conclusion textuelle serveur, verbatim.
    expect(screen.getByTestId('markets-conclusion').textContent).toContain(
      'breadth 50.0 % (seuil de couverture 80.0 %)',
    );

    // La dominante treemap est montée (moteur substitué) avec les données.
    await waitFor(() => {
      expect(setOption).toHaveBeenCalled();
    });
    expect(screen.getByTestId('marketmap-canvas')).toBeDefined();

    // Table équivalente : 4 lignes, mêmes valeurs serveur formatées.
    const table = screen.getByRole('table', {
      name: 'Table équivalente de la carte des marchés',
    });
    expect(within(table).getAllByRole('row')).toHaveLength(5); // 1 en-tête + 4
    const techRow = within(table).getByText('SYN-TECH-01').closest('tr');
    expect(techRow?.textContent).toContain('110,00 SYN');
    expect(techRow?.textContent).toContain('+10,00 %');
    expect(techRow?.textContent).toContain('70,97 %');
    expect(techRow?.textContent).toContain('SYNTHÉTIQUE');

    // Breadth : barres linéaires (role meter), valeurs et couverture serveur.
    const meters = screen.getAllByRole('meter');
    expect(meters).toHaveLength(2);
    expect(screen.getByText('50,0 %')).toBeDefined();
    expect(screen.getByText('100,0 % (seuil 80,0 %)')).toBeDefined();
    expect(screen.getByText('2 en hausse sur 4 couverts (univers 4)')).toBeDefined();

    // Pied : méthode, version moteur et limites.
    expect(screen.getByText('market.simple_return')).toBeDefined();
    expect(screen.getByText('market.breadth')).toBeDefined();
    expect(screen.getByText('vertex_core@0.1.0')).toBeDefined();
  });

  it('tri par colonne au clavier : aria-sort reflété et lignes réordonnées', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();
    const table = await screen.findByRole('table', {
      name: 'Table équivalente de la carte des marchés',
    });

    const sortButton = within(table).getByRole('button', { name: /Rendement 1 j/ });
    sortButton.focus();
    await user.keyboard('{Enter}');

    const returnHeader = sortButton.closest('th');
    expect(returnHeader?.getAttribute('aria-sort')).toBe('ascending');
    let rows = within(table).getAllByRole('row').slice(1);
    expect(rows[0]?.textContent).toContain('SYN-ENER-01'); // -10,00 % en premier

    await user.keyboard('{Enter}');
    expect(returnHeader?.getAttribute('aria-sort')).toBe('descending');
    rows = within(table).getAllByRole('row').slice(1);
    expect(rows[0]?.textContent).toContain('SYN-TECH-01'); // +10,00 % en premier
  });

  it('légende interactive : filtre local qui retire un groupe de la vue', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();
    const table = await screen.findByRole('table', {
      name: 'Table équivalente de la carte des marchés',
    });
    expect(within(table).getAllByRole('row')).toHaveLength(5);

    const chip = screen.getByRole('button', { name: 'En hausse' });
    await user.click(chip);
    expect(chip.getAttribute('aria-pressed')).toBe('false');
    // 2 tickers « up » retirés de la VUE (les valeurs ne changent pas).
    expect(within(table).getAllByRole('row')).toHaveLength(3);
    expect(screen.getByText("Filtre local d'affichage — aucune valeur modifiée.")).toBeDefined();
  });
});

describe('Page Marchés — états dégradés et vides', () => {
  it('empty honnête : aucun snapshot publié, raison serveur affichée', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeEmptyMarketsOverview()));
    await renderMarkets();
    const boundary = await screen.findByText('Aucune donnée');
    expect(boundary).toBeDefined();
    expect(screen.getByText(/no snapshot published/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('partial serveur : bandeau, couverture manquante et instruments écartés', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        makeMarketsOverview({
          data_state: 'partial',
          coverage: {
            expected: 4,
            received: 4,
            covered: 3,
            discarded: 1,
            discarded_tickers: [{ ticker: 'SYN-ENER-02', reason: 'missing_close' }],
            rejected_records: [],
            observations_considered: 7,
            lookback_seconds: 259200,
          },
        }),
      ),
    );
    await renderMarkets();
    await screen.findByText('Données partielles');
    expect(
      screen.getByText(/3 instruments couverts sur 4 attendus, 1 écartés/),
    ).toBeDefined();
    expect(screen.getByText('Instruments écartés (1)')).toBeDefined();
    expect(screen.getByText('missing_close')).toBeDefined();
    // Le contenu daté reste visible sous le bandeau.
    expect(screen.getByRole('table', { name: /Table équivalente/ })).toBeDefined();
  });

  it('stale serveur : bandeau « Données périmées », contenu daté conservé', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview({ data_state: 'stale' })));
    await renderMarkets();
    await screen.findByText('Données périmées');
    expect(screen.getByText(/as_of 2026-08-25T12:00:00\+00:00/)).toBeDefined();
    expect(screen.getByRole('table', { name: /Table équivalente/ })).toBeDefined();
  });

  it('breadth INVALID : raison affichée, aucune valeur de remplacement', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        makeMarketsOverview({
          breadth: makeMarketsBreadth({
            status: 'INVALID',
            reason: 'coverage_below_threshold',
            value: null,
            value_pct: null,
            calculation: null,
          }),
        }),
      ),
    );
    await renderMarkets();
    await screen.findByText('Breadth non calculable');
    expect(screen.getByText(/coverage_below_threshold/)).toBeDefined();
    expect(screen.queryByRole('meter')).toBeNull();
  });

  it('loading au premier chargement (aucun résultat affiché)', async () => {
    fetchMock.mockReturnValue(new Promise<Response>(() => {}));
    await renderMarkets();
    expect(screen.getByText('Chargement')).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('offline honnête quand l’API est injoignable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    await renderMarkets();
    await screen.findByText('Hors ligne');
    expect(screen.getByText(/L'API locale est injoignable/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('erreur de données sur réponse inattendue (500)', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await renderMarkets();
    await screen.findByText('Erreur de données');
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('session requise sur 401 : état dédié, aucune carte', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));
    await renderMarkets();
    await screen.findByText('Session requise');
    expect(screen.queryByRole('table')).toBeNull();
  });
});
