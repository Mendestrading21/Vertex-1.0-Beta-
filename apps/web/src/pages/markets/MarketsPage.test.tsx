/**
 * Page Marchés — 8 états, cadre CHART_STANDARD, table équivalente triable,
 * BreadthPanel et absence de tout calcul financier TypeScript (les valeurs
 * affichées sont les chaînes serveur, seulement formatées).
 *
 * Le moteur ECharts est REMPLACÉ par un double : jsdom n'a pas de canvas et
 * le contrat testé ici est celui de la page, pas du rendu Canvas (couvert par
 * Playwright sur le vrai navigateur).
 */
import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeEmptyMarketsOverview,
  makeMarketsBreadth,
  makeMarketsOverview,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { frameStateOf } from './MarketsPage.tsx';
import { marketsCsvCell } from './MarketsTable.tsx';
import { MARKETS_MODULES, absentMarketsModules } from './marketsModules.ts';

const downloadMocks = vi.hoisted(() => ({ saveTextAsFile: vi.fn() }));

vi.mock('../../app/downloadFile.ts', () => downloadMocks);

const setOption = vi.fn();
const dispose = vi.fn();
const resize = vi.fn();
/** LOT-A3 : le double enregistre l'écouteur de clic, pour le déclencher. */
const clickHandlers: Array<(params: { name?: string }) => void> = [];
const on = vi.fn((_event: string, handler: (params: { name?: string }) => void) => {
  clickHandlers.push(handler);
});
const off = vi.fn(() => {
  clickHandlers.length = 0;
});

vi.mock('../../charts/echartsLoader.ts', () => ({
  echarts: {
    init: vi.fn(() => ({ setOption, dispose, resize, on, off })),
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

function makeObservedMarketsOverview(population: 'REAL' | 'DELAYED' = 'REAL') {
  const base = makeMarketsOverview();
  const original = base.sectors[0]!.tickers[0]!;
  return makeMarketsOverview({
    population,
    sectors: [
      {
        sector: 'TECH',
        label: 'Technologie',
        declared_count: 1,
        covered_count: 1,
        tickers: [
          {
            ...original,
            ticker: 'AAPL',
            sector: 'TECH',
            currency: 'USD',
            synthetic: false,
          },
        ],
      },
    ],
    breadth: null,
    coverage: {
      expected: 1,
      received: 1,
      covered: 1,
      discarded: 0,
      discarded_tickers: [],
      rejected_records: [],
      observations_considered: 2,
      lookback_seconds: 259200,
    },
    conclusion: 'Un instrument couvert.',
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('ResizeObserver', FakeResizeObserver);
  fetchMock.mockReset();
  downloadMocks.saveTextAsFile.mockClear();
  setOption.mockClear();
  dispose.mockClear();
  clickHandlers.length = 0;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderMarkets(): Promise<void> {
  renderApp('/markets');
  await screen.findByRole('heading', { level: 1, name: 'Marchés' });
}

describe('export Marchés — sérialisation CSV pure', () => {
  it.each([
    ['texte', 'texte'],
    ['TECH;NORD', '"TECH;NORD"'],
    ['dit "oui"', '"dit ""oui"""'],
    ['ligne 1\nligne 2', '"ligne 1\nligne 2"'],
    ['ligne 1\rligne 2', '"ligne 1\rligne 2"'],
    ['=2+3', "'=2+3"],
    ['+5.00', "'+5.00"],
    ['-5.00', "'-5.00"],
    ['@QUALITY', "'@QUALITY"],
  ])('encode %j sans perdre la valeur', (raw, expected) => {
    expect(marketsCsvCell(raw)).toBe(expected);
  });
});

describe('frameStateOf — l’état canonique du snapshot prime en succès', () => {
  it('relais des états requête hors succès', () => {
    expect(frameStateOf('loading', undefined)).toBe('loading');
    expect(frameStateOf('offline', undefined)).toBe('offline');
    expect(frameStateOf('auth-required', undefined)).toBe('auth-required');
  });

  it('succès sans données = erreur (jamais un faux succès)', () => {
    expect(frameStateOf('ready', undefined)).toBe('error');
  });

  it('empty/stale/delayed/partial viennent du serveur avec leur priorité canonique', () => {
    expect(frameStateOf('ready', makeEmptyMarketsOverview())).toBe('empty');
    expect(
      frameStateOf('ready', makeMarketsOverview({ state: 'stale', data_state: 'ok' })),
    ).toBe('stale');
    expect(
      frameStateOf(
        'ready',
        makeMarketsOverview({ state: 'stale', population: 'DELAYED', data_state: 'partial' }),
      ),
    ).toBe('stale');
    expect(
      frameStateOf('ready', makeMarketsOverview({ population: 'DELAYED', data_state: 'partial' })),
    ).toBe('delayed');
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
    // §4.1 : le titre ne QUALIFIE plus la nature. Il disait « synthétiques »
    // en dur, au-dessus de 161 instruments IBKR réels sur le poste de travail.
    // La nature appartient au bandeau de population, son seul propriétaire.
    expect(screen.getByRole('heading', { level: 2, name: 'Carte des marchés' })).toBeDefined();
    expect(
      screen.queryByRole('heading', { level: 2, name: /synthétiques/ }),
    ).toBeNull();
    // Et la provenance est RECENSÉE depuis les drapeaux servis, plus écrite
    // en dur : le fixture déclare 4 instruments, tous synthétiques.
    expect(
      screen.getByText(/4 instruments servis, tous déclarés synthétiques par le worker\./),
    ).toBeDefined();
    expect(screen.queryByText('synthetic-dev')).toBeNull();

    // Métadonnées : unité, source, as_of, couverture — dans la PAGE. Depuis
    // le LOT-A3 l'inspecteur du shell relaie aussi l'as_of du snapshot ; le
    // cadre doit porter le sien, près de la donnée qu'il qualifie.
    const main = screen.getByRole('main');
    expect(within(main).getByText(/rendement 1 jour en %/)).toBeDefined();
    expect(within(main).getByText('2026-08-25T12:00:00+00:00')).toBeDefined();
    expect(within(main).getByText('4/4 couverts, 0 écartés, 4 reçus')).toBeDefined();

    // Bandeau population SYNTHETIC non masquable.
    // Portée à la PAGE : depuis le LOT-14 le ticker du shell porte sa propre
    // étiquette de population. Chercher dans tout le document trouverait les
    // deux — et surtout ne prouverait plus que la PAGE porte la sienne.
    expect(within(screen.getByRole('main')).getByText('DONNÉES SYNTHÉTIQUES')).toBeDefined();

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
    // Les trois comptes servis (hausses, baisses, inchangés) sont relayés
    // avec le total couvert : aucun compte n'est déduit des deux autres.
    expect(
      screen.getByText('2 en hausse, 1 en baisse, 1 stables sur 4 couverts (univers 4)'),
    ).toBeDefined();

    // Pied : méthode, version moteur et limites — dans la PAGE (l'inspecteur
    // du shell relaie aussi la version du moteur depuis le LOT-A3).
    expect(within(main).getByText('market.simple_return')).toBeDefined();
    expect(within(main).getByText('market.breadth')).toBeDefined();
    expect(within(main).getByText('vertex_core@0.1.0')).toBeDefined();
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

  it('export REAL : nom générique et contenu servi, jamais « marches-synthetiques.csv »', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse(makeObservedMarketsOverview()));
    await renderMarkets();

    await user.click(await screen.findByRole('button', { name: 'Exporter (CSV)' }));

    const conclusion = screen.getByTestId('markets-conclusion').textContent;
    expect(conclusion).toBe('Un instrument couvert.');
    expect(conclusion).not.toContain('synthétique');
    expect(downloadMocks.saveTextAsFile).toHaveBeenCalledTimes(1);
    expect(downloadMocks.saveTextAsFile).toHaveBeenCalledWith(
      expect.stringContaining('AAPL'),
      'marches.csv',
      'text/csv;charset=utf-8',
    );
  });

  it('export SYNTHETIC : conserve le nom explicitement synthétique', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();

    await user.click(await screen.findByRole('button', { name: 'Exporter (CSV)' }));

    expect(downloadMocks.saveTextAsFile).toHaveBeenCalledWith(
      expect.any(String),
      'marches-synthetiques.csv',
      'text/csv;charset=utf-8',
    );
  });

  it('export hostile : échappe le CSV et neutralise chaque préfixe de formule', async () => {
    const user = userEvent.setup();
    const base = makeObservedMarketsOverview();
    const original = base.sectors[0]!.tickers[0]!;
    fetchMock.mockResolvedValue(
      jsonResponse({
        ...base,
        sectors: [
          {
            ...base.sectors[0]!,
            sector: 'TECH;"Nord"',
            tickers: [
              {
                ...original,
                ticker: '=2+3',
                sector: 'TECH;"Nord"',
                trading_day: '2026-09-02\nsuite',
                last_close: '-100.00',
                currency: '@USD',
                return_1d: '"quoted"',
                return_1d_pct: '+5.00',
                weight_in_sector: '0;5',
                weight_global: '\r\nnext',
                quality: '@QUALITY',
              },
            ],
          },
        ],
      }),
    );
    await renderMarkets();

    await user.click(await screen.findByRole('button', { name: 'Exporter (CSV)' }));

    const csv: unknown = downloadMocks.saveTextAsFile.mock.calls[0]?.[0];
    expect(typeof csv).toBe('string');
    if (typeof csv !== 'string') {
      throw new TypeError('CSV non produit');
    }
    expect(csv).toContain(`\n'=2+3;"TECH;""Nord""";"2026-09-02\nsuite";`);
    expect(csv).toContain(
      `;'-100.00;'@USD;"""quoted""";'+5.00;"0;5";"\r\nnext";'@QUALITY;`,
    );
    expect(csv).not.toContain('\n=2+3;');
    expect(downloadMocks.saveTextAsFile).toHaveBeenCalledWith(
      csv,
      'marches.csv',
      'text/csv;charset=utf-8',
    );
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

  it('state=stale du relais : conserve la carte et affiche âge et raison publiés', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        makeMarketsOverview({
          state: 'stale',
          data_state: 'ok',
          age_seconds: 300_000,
          reason: 'snapshot older than its freshness budget: age 300000 s',
        }),
      ),
    );
    await renderMarkets();

    await screen.findByText('Données périmées');
    // Raison et âge DANS le cadre périmé — le module Santé des marchés
    // relaie aussi l'âge publié (LOT-A3) ; ce n'est pas lui qui est testé ici.
    const cadre = screen.getByRole('main').querySelector('[data-state="stale"]') as HTMLElement;
    expect(
      within(cadre).getByText(/snapshot older than its freshness budget: age 300000 s/),
    ).toBeDefined();
    expect(within(cadre).getByText(/âge publié 300000 s/)).toBeDefined();
    expect(screen.getByRole('table', { name: /Table équivalente/ })).toBeDefined();
  });

  it('population DELAYED : état différé explicite et contenu conservé', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeObservedMarketsOverview('DELAYED')));
    await renderMarkets();

    await screen.findByText('Données différées');
    expect(within(screen.getByRole('main')).getByText('DONNÉES RETARDÉES')).toBeDefined();
    expect(screen.getByText(/Population DELAYED publiée par le worker/)).toBeDefined();
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
    // Les comptes restent des faits publiés, même sans ratio.
    expect(
      screen.getByText('2 en hausse, 1 en baisse, 1 stables sur 4 couverts (univers 4)'),
    ).toBeDefined();
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

describe('Page Marchés — la planche §2 est complète, servie ou déclarée (LOT-A3)', () => {
  it('rend les DOUZE modules de la planche, une seule dominante : la carte', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();
    await screen.findByRole('heading', { level: 2, name: 'Carte des marchés' });
    for (const module of MARKETS_MODULES) {
      expect(
        document.querySelector(`[data-module="${module.id}"]`),
        `module « ${module.title} » (${module.id}) absent du DOM`,
      ).not.toBeNull();
    }
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.getAttribute('data-module')).toBe('market-map');
  });

  it('les sept modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();
    await screen.findByRole('heading', { level: 2, name: 'Carte des marchés' });
    for (const module of absentMarketsModules()) {
      const zone = within(document.querySelector(`[data-module="${module.id}"]`) as HTMLElement);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('inspecteur par défaut : la vérité du snapshot ; une ligne de table sélectionnée : l’instrument et sa lignée', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();
    expect(await screen.findByTestId('markets-snapshot-facts')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Carte des marchés' })).toBeDefined();

    await user.click(screen.getByRole('button', { name: 'Inspecter SYN-TECH-01' }));
    const faits = await screen.findByTestId('markets-instrument-facts');
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — SYN-TECH-01' })).toBeDefined();
    // Chaînes serveur verbatim, virgule française : clôture, rendement, poids.
    expect(faits.textContent).toContain('110,00');
    expect(faits.textContent).toContain('+10,00 %');
    expect(faits.textContent).toContain('70,97 %');
    // La lignée du calcul, jamais un chiffre neuf.
    const lignee = screen.getByTestId('markets-instrument-lineage');
    expect(lignee.textContent).toContain('market.simple_return');
    expect(lignee.textContent).toContain('vertex_core@0.1.0');
    expect(screen.queryByTestId('markets-snapshot-facts')).toBeNull();
    // La ligne et la puce sectorielle disent la sélection (aria-pressed).
    expect(screen.getByRole('button', { name: 'Inspecter SYN-TECH-01' }).getAttribute('aria-pressed')).toBe('true');

    // Fermer rend l'inspecteur par défaut.
    await user.click(screen.getByRole('button', { name: 'Fermer' }));
    expect(await screen.findByTestId('markets-snapshot-facts')).toBeDefined();
  });

  it('un clic sur une TUILE de la carte sélectionne l’instrument ; un nœud de secteur, non', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeMarketsOverview()));
    await renderMarkets();
    await waitFor(() => {
      expect(clickHandlers.length).toBeGreaterThan(0);
    });
    const handler = clickHandlers[clickHandlers.length - 1]!;
    act(() => {
      handler({ name: 'Technologie synthétique' });
    });
    expect(screen.queryByTestId('markets-instrument-facts')).toBeNull();
    act(() => {
      handler({ name: 'SYN-TECH-01' });
    });
    expect(await screen.findByTestId('markets-instrument-facts')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — SYN-TECH-01' })).toBeDefined();
  });
});
