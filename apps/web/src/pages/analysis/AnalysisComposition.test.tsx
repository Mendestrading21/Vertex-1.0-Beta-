/**
 * Page Analyse — la planche §4 est complète, servie ou déclarée (LOT-A4).
 *
 * Invariants : dix-neuf modules dans le DOM, une seule dominante (le cadre
 * des chandeliers), huit absences au motif fermé sans chiffre, l'en-tête
 * porte la clôture PUBLIÉE et la variation 1 j du snapshot Marchés, les
 * faits SEC sont relayés verbatim (ou leur absence dite), les catalyseurs
 * sont ceux de l'instrument, et l'inspecteur du dossier est monté.
 *
 * Le moteur Lightweight Charts est REMPLACÉ par un double (jsdom sans canvas).
 */
import { screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import {
  makeAiAnswer,
  makeAnalysis,
  makeCalendarEvent,
  makeCalendarResponse,
  makeEmptySecFundamentals,
  makeMarketsOverview,
  makeRevisedCalendarEvent,
  makeSecFundamentals,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { ANALYSIS_MODULES, absentAnalysisModules } from './analysisModules.ts';

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

function servir(
  overrides: {
    readonly sec?: unknown;
    readonly calendar?: unknown;
    readonly analysis?: unknown;
  } = {},
): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/markets/overview')) {
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    }
    if (url.includes('/v1/ai/status')) {
      return Promise.resolve(
        jsonResponse({ provider: 'DISABLED', reason: 'B-05_HUMAN_DECISION_PENDING', deterministic_template_available: true }),
      );
    }
    if (url.includes('/v1/ai/explain')) {
      return Promise.resolve(jsonResponse(makeAiAnswer()));
    }
    if (url.includes('/v1/calendar')) {
      return Promise.resolve(jsonResponse(overrides.calendar ?? makeCalendarResponse()));
    }
    if (url.includes('/sources/sec/')) {
      return Promise.resolve(jsonResponse(overrides.sec ?? makeEmptySecFundamentals()));
    }
    return Promise.resolve(jsonResponse(overrides.analysis ?? makeAnalysis()));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderAnalysis(): Promise<void> {
  renderApp('/analysis/SYN-TECH-01');
  await screen.findByRole('heading', { level: 2, name: 'Analyse — SYN-TECH-01' });
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Analyse — composition (LOT-A4)', () => {
  it('rend les DIX-NEUF modules de la planche, chacun à sa place', async () => {
    servir();
    await renderAnalysis();
    for (const module of ANALYSIS_MODULES) {
      expect(
        document.querySelector(`[data-module="${module.id}"]`),
        `module « ${module.title} » (${module.id}) absent du DOM`,
      ).not.toBeNull();
    }
  });

  it('une seule dominante : le cadre des chandeliers', async () => {
    servir();
    await renderAnalysis();
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.getAttribute('data-module')).toBe('chart');
  });

  it('les SEPT modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    // LOT P2 — huit → sept : `oscillators` n'est plus absent, le worker les
    // publie depuis le LOT-S6. Même assertion, sur un compte devenu juste.
    servir();
    await renderAnalysis();
    expect(absentAnalysisModules()).toHaveLength(7);
    for (const module of absentAnalysisModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('LOT P2 — les oscillateurs SERVIS sont affichés, plus déclarés absents', async () => {
    // L'ABSENCE AVAIT CESSÉ D'ÊTRE VRAIE. Le module affirmait « le registre des
    // calculs ne publie aucun oscillateur » ; le worker publie RSI et MACD
    // depuis le LOT-S6, et Graphiques les affiche déjà. Ce test sert le bloc
    // exactement comme le worker le publie et exige qu'il atteigne l'écran.
    const base = makeAnalysis() as Record<string, unknown>;
    const contenu = base as { indicators?: Record<string, unknown> };
    servir({
      analysis: {
        ...base,
        indicators: {
          ...(contenu.indicators ?? {}),
          oscillators: {
            rsi: {
              status: 'OK',
              unit: 'index_0_100',
              calculation: {
                calculation_id: 'market.rsi',
                method: 'Wilder smoothing over 14 sessions',
                engine_version: 'vertex_core@0.1.0',
                status: 'OK',
              },
              parameters: { window: 14 },
              points: [
                { trading_day: '2026-09-03', value: '52.1' },
                { trading_day: '2026-09-04', value: '58.4' },
              ],
            },
            macd: {
              status: 'OK',
              unit: 'price',
              calculation: {
                calculation_id: 'market.macd',
                method: 'EMA(12) − EMA(26), signal EMA(9)',
                engine_version: 'vertex_core@0.1.0',
                status: 'OK',
              },
              parameters: { fast: 12, slow: 26, signal: 9 },
              // Forme RÉELLE du worker (`analysis.py:1127`) : `lines` déclare
              // les NOMS, `series` porte les données. La deviner autrement
              // aurait fait passer un test sur une forme que personne ne sert.
              lines: ['macd', 'signal'],
              series: {
                macd: [
                  { trading_day: '2026-09-03', value: '1.10' },
                  { trading_day: '2026-09-04', value: '1.35' },
                ],
                signal: [
                  { trading_day: '2026-09-03', value: '0.90' },
                  { trading_day: '2026-09-04', value: '1.05' },
                ],
              },
            },
          },
        },
      },
    });
    await renderAnalysis();

    const zone = cellule('oscillators');
    // Le module n'est plus une carte d'absence.
    expect(zone.queryByTestId('absent-body')).toBeNull();
    // Le RSI prend l'arc PARCE QUE le serveur déclare l'échelle bornée.
    expect(zone.getByTestId('analysis-rsi')).toBeDefined();
    expect(zone.getByRole('meter')).toBeDefined();
    // Le MACD n'a pas d'échelle déclarée : ses dernières valeurs servies se
    // lisent telles quelles, sans forme inventée.
    expect(zone.getByTestId('analysis-macd')).toBeDefined();
    expect(zone.getByText('1.35')).toBeDefined();
    expect(zone.getByText('1.05')).toBeDefined();
  });

  it('l’en-tête porte la clôture PUBLIÉE du dossier, la variation 1 j de Marchés et une série tracée', async () => {
    servir();
    await renderAnalysis();
    // `100.52` est `last_close` du dossier (3 barres) → virgule française.
    expect(screen.getByTestId('instrument-header-price').textContent).toContain('100,52');
    // Marchés publie SYN-TECH-01 avec un rendement 1 j : la pastille le relaie.
    const delta = await screen.findByTestId('instrument-header-delta');
    expect(delta.getAttribute('data-sign')).not.toBeNull();
    expect(delta.textContent).toContain('%');
    expect(within(screen.getByTestId('instrument-header')).getByTestId('spark-line')).toBeDefined();
  });

  it('l’identité dit « non publié » pour industrie, capitalisation et bêta — jamais une valeur', async () => {
    servir();
    await renderAnalysis();
    const identite = cellule('identity-facts');
    expect(identite.getByText('SYN')).toBeDefined();
    expect(identite.getAllByText('non publié').length).toBeGreaterThanOrEqual(3);
  });

  it('faits SEC absents : état vide HONNÊTE, rien à la place', async () => {
    servir();
    await renderAnalysis();
    expect(await screen.findByTestId('sec-empty')).toBeDefined();
    expect(screen.queryByTestId('sec-facts')).toBeNull();
  });

  it('faits SEC publiés : dépôts, faits et identité relayés verbatim, lien officiel seul', async () => {
    servir({ sec: makeSecFundamentals() });
    await renderAnalysis();
    const facts = await screen.findByTestId('sec-facts');
    expect(facts.textContent).toContain('[SYNTHETIC] Fictional Tech One Inc.');
    expect(facts.textContent).toContain('RESOLVED');
    expect(within(facts).getByText('Assets')).toBeDefined();
    expect(within(facts).getByText('110')).toBeDefined();
    expect(within(facts).getByText('Revenues')).toBeDefined();
    const lien = within(facts).getByRole('link', { name: /document officiel/ });
    expect(lien.getAttribute('href')).toMatch(/^https:\/\/www\.sec\.gov\//);
    // Aucun ratio n'est écrit : rien n'est calculé sur ces faits.
    expect(facts.textContent).not.toMatch(/ratio|marge|rendement/i);
  });

  it('les catalyseurs sont ceux de l’instrument seulement, dans l’ordre publié', async () => {
    // Agenda à deux événements : SYN-ENER-01 (révisé) puis SYN-TECH-01. Seul
    // le second concerne ce dossier ; le premier n'est jamais montré ici.
    servir({
      calendar: makeCalendarResponse({ agenda: [makeRevisedCalendarEvent(), makeCalendarEvent()] }),
    });
    await renderAnalysis();
    const liste = await screen.findByTestId('analysis-catalysts');
    const lignes = within(liste).getAllByRole('listitem');
    expect(lignes).toHaveLength(1);
    expect(lignes[0]?.textContent).toContain('SYN-TECH-01');
    expect(liste.textContent).not.toContain('SYN-ENER-01');
  });

  it('sans événement pour l’instrument : une absence dite, aucun événement d’un autre instrument', async () => {
    servir();
    await renderAnalysis();
    const vide = await screen.findByTestId('analysis-catalysts-empty');
    expect(vide.textContent).toContain('SYN-TECH-01');
    expect(screen.queryByTestId('analysis-catalysts')).toBeNull();
  });

  it('les risques déclarés relaient résumé, gates non passées et limites du verdict', async () => {
    servir();
    await renderAnalysis();
    const risques = cellule('key-risks').getByTestId('analysis-risks');
    expect(risques.textContent).toContain('SYNTHETIC development data');
    expect(risques.textContent).toContain('entitlements_sufficient');
    expect(risques.textContent).toContain('UNEVALUABLE');
    expect(risques.textContent).not.toContain('snapshot_fresh_and_coherent');
  });

  it('les pairs sont les autres instruments du secteur publié par Marchés', async () => {
    servir();
    await renderAnalysis();
    const pairs = await screen.findByTestId('analysis-peers');
    expect(pairs.textContent).not.toContain('SYN-TECH-01');
    expect(within(pairs).getAllByRole('listitem').length).toBeGreaterThanOrEqual(1);
  });

  it('l’inspecteur du dossier est monté, avant le panneau d’explication', async () => {
    servir();
    await renderAnalysis();
    const facts = await screen.findByTestId('analysis-dossier-facts');
    expect(facts.textContent).toContain('vertex_core@0.1.0');
    expect(facts.textContent).toContain('INSUFFICIENT_DATA');
    expect(facts.textContent).toContain('non publiée'); // thèse, invalidation
    const titres = screen.getAllByRole('heading', { level: 2, name: /^Inspecteur — / });
    expect(titres[0]?.textContent).toBe('Inspecteur — Dossier SYN-TECH-01');
  });
});
