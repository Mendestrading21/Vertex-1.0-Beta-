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
  makeAiAnswer,
  makeAnalysis,
  makeAnalysisBars,
  makeCalendarResponse,
  makeEmptyAnalysis,
  makeEmptySecFundamentals,
  makeMarketsOverview,
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

/**
 * Sert une Response FRAÎCHE par appel, routée par URL.
 *
 * Le sélecteur d'instruments lit la vue Marchés en plus de la ressource de la
 * page. Un `mockResolvedValue` unique rendrait le même objet `Response` aux
 * deux appels, et un corps de réponse ne se lit qu'une fois.
 */
let secResponse: unknown = makeEmptySecFundamentals();

function repondre(reponse: Response): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/markets/overview')) {
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    }
    // Depuis le LOT-12, la page monte le panneau d'explication dans
    // l'inspecteur : elle appelle donc aussi `/v1/ai/*`. Ces routes sont
    // servies explicitement — les laisser tomber dans le repli faisait
    // recevoir au panneau un corps d'ANALYSE en guise d'explication, ce qui a
    // révélé le défaut de robustesse corrigé dans le même lot.
    if (url.includes('/v1/ai/status')) {
      return Promise.resolve(
        jsonResponse({
          provider: 'DISABLED',
          reason: 'B-05_HUMAN_DECISION_PENDING',
          deterministic_template_available: true,
        }),
      );
    }
    if (url.includes('/v1/ai/explain')) {
      return Promise.resolve(jsonResponse(makeAiAnswer()));
    }
    // LOT-A4 : la planche §4 lit aussi l'agenda publié (catalyseurs de
    // l'instrument) et la route SEC (faits officiels). Servies explicitement :
    // les laisser tomber dans le repli leur donnerait un corps d'ANALYSE.
    if (url.includes('/v1/calendar')) {
      return Promise.resolve(jsonResponse(makeCalendarResponse()));
    }
    if (url.includes('/sources/sec/')) {
      return Promise.resolve(jsonResponse(secResponse));
    }
    return Promise.resolve(reponse.clone());
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  setData.mockClear();
  remove.mockClear();
  secResponse = makeEmptySecFundamentals();
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

  it('state=stale du relais prime ; fresh=false publié → stale ; barres dégradées → partial', () => {
    const relayStale = makeAnalysis({
      state: 'stale',
      age_seconds: 300_000,
      reason: 'snapshot older than its freshness budget',
    });
    expect(analysisStateOf('ready', relayStale)).toBe('stale');
    expect(analysisStateOf('ready', makeAnalysis({ population: 'DELAYED' }))).toBe('delayed');
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
    repondre(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    const heading = await screen.findByRole('heading', { level: 2, name: 'Analyse — SYN-TECH-01' });
    // Portée au CADRE : depuis le LOT-A4 l'inspecteur du dossier relaie aussi
    // la référence d'observation ; c'est le cadre qui doit la porter.
    const frame = within(heading.closest('.vx-chartframe') as HTMLElement);
    expect(frame.getByText(/prix OHLC en SYN/)).toBeDefined();
    expect(frame.getByText(/UTC \(stockage\)/)).toBeDefined();
    expect(frame.getByText('synthetic-dev:1234:db0002')).toBeDefined();
    // as_of du cadre (il réapparaît aussi dans la validité de l'AdviceCard).
    expect(screen.getAllByText('2026-08-25T12:00:00+00:00').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/3 barre\(s\) valides/)).toBeDefined();
    // Portée à la PAGE : depuis le LOT-14 le ticker du shell porte sa propre
    // étiquette de population. Chercher dans tout le document trouverait les
    // deux — et surtout ne prouverait plus que la PAGE porte la sienne.
    expect(within(screen.getByRole('main')).getByText('DONNÉES SYNTHÉTIQUES')).toBeDefined();
  });

  it('population REAL : affiche la nature et la référence publiées, sans libellé synthétique local', async () => {
    repondre(
      jsonResponse(
        makeAnalysis({
          population: 'REAL',
          instrument: 'AAPL',
          bars: {
            ...makeAnalysisBars(),
            currency: 'USD',
            adjustment_basis: 'unadjusted',
            source_event_id: 'ibkr-bars-265598',
          },
          advice: null,
        }),
      ),
    );
    await renderAnalysis('/analysis/AAPL');

    const heading = await screen.findByRole('heading', { level: 2, name: 'Analyse — AAPL' });
    const frame = heading.closest('.vx-chartframe');
    expect(frame).not.toBeNull();
    const scoped = within(frame as HTMLElement);

    expect(scoped.getByText('DONNÉES RÉELLES')).toBeDefined();
    expect(scoped.getByText('ibkr-bars-265598')).toBeDefined();
    expect(frame?.textContent).toContain('population REAL déclarée par le worker');
    expect(frame?.textContent).not.toContain('jours de bourse synthétiques');
    expect(frame?.textContent).not.toContain('population SYNTHÉTIQUE de développement');
    expect(frame?.textContent).not.toContain('synthetic-dev');
  });

  it('dominante : moteur substitué monté avec les 60 barres (ici 3) + attribution TradingView', async () => {
    repondre(jsonResponse(makeAnalysis()));
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
    repondre(jsonResponse(analysis));
    await renderAnalysis();
    // La table est passée sur la primitive `DataTable` : son nom accessible
    // vient désormais de son `<caption>` VISIBLE, et non plus d'un `aria-label`
    // invisible à l'écran. L'assertion reste la même — la table doit avoir un
    // nom — mais elle porte maintenant sur un nom que l'utilisateur voit aussi.
    const table = await screen.findByRole('table', {
      name: /Table OHLCV — équivalent exact des chandeliers/,
    });
    // Et la légende est bien RENDUE, pas seulement annoncée.
    expect(table.querySelector('caption')?.textContent).toContain('équivalent exact des chandeliers');
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
    repondre(jsonResponse(makeAnalysis()));
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

    // LOT P2b — LA PREUVE SERVIE EST LUE. Le moteur publie `observed_values`
    // et `thresholds` à chaque point de retour ; la page n'en lisait rien.
    // Ce que la gate a REGARDÉ est désormais visible, verbatim.
    const degradee = scoped.getByText('instrument_resolved').closest('li');
    expect(degradee).not.toBeNull();
    const preuve = within(degradee as HTMLElement);
    expect(preuve.getByText('Observé')).toBeDefined();
    expect(preuve.getByText('identity_status').tagName).toBe('CODE');
    expect(preuve.getByText('RESOLVED').tagName).toBe('CODE');
    expect(preuve.getByText('resolved_with_conid').tagName).toBe('CODE');
    // Le booléen SERVI se lit `false` — jamais « non », jamais un vide, et
    // surtout jamais confondu avec une absence de publication.
    expect(preuve.getByText('false').tagName).toBe('CODE');

    // `_unevaluable` (gates.py:62-69) ne publie NI observé NI seuil : la gate
    // bloquée ne gagne donc AUCUNE rubrique vide.
    const bloquee = scoped.getByText('entitlements_sufficient').closest('li');
    expect(within(bloquee as HTMLElement).queryByText('Observé')).toBeNull();
    expect(within(bloquee as HTMLElement).queryByText('Seuils')).toBeNull();
  });

  it('evidence vide honnête + scénarios absents avec raison typée', async () => {
    repondre(jsonResponse(makeAnalysis()));
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
    // Le sélecteur lit la vue Marchés ; ce qui ne doit PAS être
    // demandé, c'est la ressource d'instrument elle-même.
    const demandes = fetchMock.mock.calls.map(([entree]) => String(entree));
    expect(demandes.some((url) => url.includes('/v1/analysis/'))).toBe(false);
  });

  it('empty honnête avec raison serveur', async () => {
    repondre(jsonResponse(makeEmptyAnalysis()));
    await renderAnalysis();
    await screen.findByText('Aucune donnée');
    expect(screen.getByText(/no snapshot published/)).toBeDefined();
  });

  it('stale publié : bandeau « Données périmées », contenu conservé', async () => {
    repondre(
      jsonResponse(makeAnalysis({ bars: { ...makeAnalysisBars(), fresh: false } })),
    );
    await renderAnalysis();
    await screen.findByText('Données périmées');
    expect(screen.getByText(/fresh = false/)).toBeDefined();
    expect(screen.getByRole('table', { name: /OHLCV/ })).toBeDefined();
  });

  it('state=stale du relais : conserve le dossier et affiche son âge et sa raison publiés', async () => {
    repondre(
      jsonResponse(
        makeAnalysis({
          state: 'stale',
          age_seconds: 300_000,
          reason: 'snapshot older than its freshness budget: age 300000 s',
        }),
      ),
    );
    await renderAnalysis();

    await screen.findByText('Données périmées');
    expect(screen.getByText(/snapshot older than its freshness budget: age 300000 s/)).toBeDefined();
    expect(screen.getByText(/âge publié 300000 s/)).toBeDefined();
    expect(screen.getByRole('table', { name: /OHLCV/ })).toBeDefined();
  });

  it('population DELAYED : état différé explicite et contenu conservé', async () => {
    repondre(
      jsonResponse(
        makeAnalysis({
          population: 'DELAYED',
          instrument: 'AAPL',
          bars: {
            ...makeAnalysisBars(),
            currency: 'USD',
            adjustment_basis: 'unadjusted',
            source_event_id: 'ibkr-bars-delayed-265598',
          },
          advice: null,
        }),
      ),
    );
    await renderAnalysis('/analysis/AAPL');

    await screen.findByText('Données différées');
    expect(screen.getByText('DONNÉES RETARDÉES')).toBeDefined();
    expect(screen.getByText(/Population DELAYED publiée par le worker/)).toBeDefined();
    expect(screen.getByRole('table', { name: /OHLCV/ })).toBeDefined();
  });

  it('offline honnête quand l’API est injoignable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    await renderAnalysis();
    await screen.findByText('Hors ligne');
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('session requise sur 401', async () => {
    repondre(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));
    await renderAnalysis();
    await screen.findByText('Session requise');
  });
});

describe('Page Analyse — indicateurs techniques', () => {
  it('affiche la valeur SERVEUR, sans jamais la recalculer', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    const bloc = await screen.findByTestId('indicator-volatility');
    // `27.95` vient de `value_pct`, produit par le serveur : multiplier par
    // 100 dans le navigateur serait le calcul financier interdit.
    expect(bloc.textContent).toContain('27.95');
    expect(bloc.textContent).toContain('%');
    expect(bloc.textContent).toContain('20');
  });

  it('borne la VALEUR au rendu, jamais l’UNITÉ', async () => {
    // La valeur et l'unité formaient une seule chaîne : « 4.413571428571428
    // SYN ». Borner le rendu a fait disparaître « SYN » derrière l'ellipse —
    // vu sur capture, pas par un test. Un nombre sans son unité n'est pas une
    // information abrégée, c'est une information fausse.
    repondre(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    const bloc = await screen.findByTestId('indicator-volatility');
    const borne = bloc.querySelector('.vx-served-number');
    expect(borne, 'la valeur doit vivre dans une boîte bornée').not.toBeNull();
    expect(borne?.textContent).toBe('27.95');
    // L'unité est DANS le bloc, mais HORS de la boîte bornée.
    expect(bloc.textContent).toContain('%');
    expect(borne?.textContent ?? '').not.toContain('%');
    // Et la valeur entière reste atteignable au survol.
    expect(borne?.getAttribute('title')).toBe('27.95');
  });

  it('affiche une absence NOMMÉE plutôt qu’une case vide', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    const absent = await screen.findByTestId('indicator-atr-absent');
    expect(absent.textContent).toContain('INSUFFICIENT_SAMPLE');
    // Le compte réel de barres, pas seulement un statut.
    expect(absent.textContent).toContain('3');
  });

  it('publie la méthode du calcul, pas un jugement', async () => {
    repondre(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    await screen.findByTestId('indicator-volatility');
    expect(screen.getByText(/market\.realized_volatility/)).toBeDefined();
  });

  it('n’affiche AUCUNE interprétation de la mesure', async () => {
    /**
     * Un ATR est une amplitude, une volatilité un écart-type annualisé.
     * Les qualifier d’« élevé » supposerait un seuil, et aucun seuil n’est
     * déclaré. Ce test empêche qu’un futur ajout en introduise un en douce.
     */
    repondre(jsonResponse(makeAnalysis()));
    await renderAnalysis();
    const section = (await screen.findByTestId('indicator-volatility')).closest('section');
    expect(section).not.toBeNull();
    const texte = section?.textContent ?? '';
    for (const mot of ['élevé', 'faible', 'normal', 'suracheté', 'survendu', 'signal']) {
      expect(texte.toLowerCase()).not.toContain(mot);
    }
  });
});
