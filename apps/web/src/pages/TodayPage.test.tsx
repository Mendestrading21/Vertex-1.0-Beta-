import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../components/AbsentModule.tsx';
import {
  makeAnalysis,
  makeAttentionItem,
  makeAttentionSnapshot,
  makeCalendarResponse,
  makeCapabilities,
  makeEmptyAnalysis,
  makeEmptyAttentionSnapshot,
  makeMarketsOverview,
  makeOpportunities,
  makePortfolioResponse,
} from '../test/fixtures.ts';
import { renderApp } from '../test/render.tsx';
import { attentionFrameStateOf } from './TodayPage.tsx';
import { TODAY_MODULES, absentTodayModules } from './todayView.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockToday(attention: unknown): void {
  fetchMock.mockImplementation((input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (url.includes('/today/attention')) {
      return Promise.resolve(jsonResponse(attention));
    }
    if (url.includes('/system/capabilities')) {
      return Promise.resolve(jsonResponse(makeCapabilities()));
    }
    if (url.includes('/calendar')) {
      return Promise.resolve(jsonResponse(makeCalendarResponse()));
    }
    if (url.includes('/opportunities')) {
      return Promise.resolve(jsonResponse(makeOpportunities()));
    }
    if (url.includes('/portfolio')) {
      return Promise.resolve(jsonResponse(makePortfolioResponse()));
    }
    if (url.includes('/analysis/')) {
      return Promise.resolve(jsonResponse(makeAnalysis()));
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

describe("attentionFrameStateOf — l'état servi prime sur le succès HTTP", () => {
  it('relaie les états requête hors succès et refuse un succès sans réponse', () => {
    expect(attentionFrameStateOf('loading', undefined)).toBe('loading');
    expect(attentionFrameStateOf('offline', makeAttentionSnapshot({ state: 'stale' }))).toBe(
      'offline',
    );
    expect(attentionFrameStateOf('auth-required', undefined)).toBe('auth-required');
    expect(attentionFrameStateOf('ready', undefined)).toBe('error');
  });

  it('applique la priorité stale, DELAYED, empty, puis état de requête', () => {
    expect(
      attentionFrameStateOf(
        'refreshing',
        makeAttentionSnapshot({ state: 'stale', population: 'DELAYED' }),
      ),
    ).toBe('stale');
    expect(
      attentionFrameStateOf('refreshing', makeAttentionSnapshot({ population: 'DELAYED' })),
    ).toBe('delayed');
    expect(attentionFrameStateOf('ready', makeEmptyAttentionSnapshot())).toBe('empty');
    expect(attentionFrameStateOf('refreshing', makeAttentionSnapshot())).toBe('refreshing');
    expect(attentionFrameStateOf('ready', makeAttentionSnapshot())).toBe('ready');
  });
});

describe("Page Aujourd'hui — états dégradés du snapshot", () => {
  it('state=stale conserve la file sous un bandeau avec raison, âge et instant', async () => {
    const stale = makeAttentionSnapshot({
      state: 'stale',
      age_seconds: 300_000,
      reason: 'snapshot older than its freshness budget',
    });
    mockToday(stale);
    renderApp('/today');

    await screen.findByRole('heading', { level: 1, name: "Aujourd'hui" });
    const main = screen.getByRole('main');
    await waitFor(() => {
      expect(main.querySelector('[data-state="stale"]')).not.toBeNull();
    });
    const boundary = main.querySelector('[data-state="stale"]') as HTMLElement;
    expect(boundary.textContent).toContain('Données périmées');
    expect(boundary.textContent).toContain('snapshot older than its freshness budget');
    expect(boundary.textContent).toContain('300000 s');
    expect(boundary.textContent).toContain('as_of 2026-08-25T12:00:00+00:00');
    expect(within(boundary).getByText(stale.items[0]!.title)).toBeDefined();
  });

  it('population=DELAYED conserve la file sous un état différé explicite', async () => {
    const delayedItem = makeAttentionItem(0, {
      synthetic: false,
      sources: ['ibkr'],
      rights: ['IBKR_MARKET_DATA'],
      provenance: {
        ...makeAttentionItem(0).provenance,
        sources: ['ibkr'],
        rights: ['IBKR_MARKET_DATA'],
      },
    });
    const delayed = makeAttentionSnapshot({
      population: 'DELAYED',
      age_seconds: 90,
      items: [delayedItem],
    });
    mockToday(delayed);
    renderApp('/today');

    await screen.findByRole('heading', { level: 1, name: "Aujourd'hui" });
    const main = screen.getByRole('main');
    await waitFor(() => {
      expect(main.querySelector('[data-state="delayed"]')).not.toBeNull();
    });
    const boundary = main.querySelector('[data-state="delayed"]') as HTMLElement;
    expect(boundary.textContent).toContain('Données différées');
    expect(boundary.textContent).toContain('DONNÉES RETARDÉES');
    expect(boundary.textContent).toContain('90 s');
    expect(within(boundary).getByText(delayedItem.title)).toBeDefined();
  });
});

describe("Page Aujourd'hui — la planche §1 est complète, servie ou déclarée (LOT-A3)", () => {
  it('rend les ONZE modules de la planche, chacun à sa place', async () => {
    mockToday(makeAttentionSnapshot());
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    for (const module of TODAY_MODULES) {
      expect(
        document.querySelector(`[data-module="${module.id}"]`),
        `module « ${module.title} » (${module.id}) absent du DOM`,
      ).not.toBeNull();
    }
  });

  it('une seule dominante : la file d’attention', async () => {
    mockToday(makeAttentionSnapshot());
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('attention');
  });

  it('les trois modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    mockToday(makeAttentionSnapshot());
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    for (const module of absentTodayModules()) {
      const zone = within(document.querySelector(`[data-module="${module.id}"]`) as HTMLElement);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('les modules servis relaient des chaînes serveur : breadth, catalyseur, capacités, opportunités, portefeuille, agenda', async () => {
    mockToday(makeAttentionSnapshot());
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);
    // Marché global : breadth « 50.0 » servie → « 50,0 % », et la conclusion verbatim.
    expect(await cellule('global-market').findByText('50,0')).toBeDefined();
    expect(cellule('global-market').getByTestId('today-market-conclusion').textContent).toContain(
      'breadth 50.0 %',
    );
    // Les trois comptes servis accompagnent la breadth, avec le total couvert.
    expect(
      cellule('global-market').getByText('2 en hausse, 1 en baisse, 1 stables sur 4 couverts'),
    ).toBeDefined();
    // Catalyseur suivant : le PREMIER de l'agenda publié, sans retri.
    expect(await cellule('next-catalyst').findByText('SYN-ENER-01')).toBeDefined();
    // Santé des sources : base, worker, et le recensement des statuts.
    expect(await cellule('source-health').findByText('Disponible')).toBeDefined();
    expect(cellule('source-health').getByText('AVAILABLE')).toBeDefined();
    // Opportunités : comptes publiés, aucun candidat qualifié DIT, pas caché.
    expect(await cellule('opportunities').findByText('24')).toBeDefined();
    expect(cellule('opportunities').getByRole('status').textContent).toContain('Aucun candidat qualifié');
    // Portefeuille manuel : valeur servie et marques synthétiques nommées.
    expect(await cellule('manual-portfolio').findByText('555')).toBeDefined();
    expect(cellule('manual-portfolio').getByText('MARQUES SYNTHÉTIQUES')).toBeDefined();
    // Calendrier : les événements publiés, dans l'ordre.
    expect((await cellule('calendar').findAllByRole('listitem')).length).toBe(2);
    // Carte sectorielle : une puce par instrument servi.
    expect((await cellule('sectors').findAllByRole('listitem')).length).toBe(4);
  });

  it('l’inspecteur par défaut porte la vérité du snapshot ; un item ouvert le remplace', async () => {
    mockToday(makeAttentionSnapshot());
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    expect(await screen.findByTestId('snapshot-rail')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Snapshot publié' })).toBeDefined();
    const bouton = screen.getAllByRole('button', { expanded: false })[0] as HTMLButtonElement;
    bouton.click();
    await waitFor(() => {
      expect(screen.queryByTestId('snapshot-rail')).toBeNull();
    });
    expect(screen.getByRole('heading', { level: 2, name: /Inspecteur — \[SYNTHETIC\]/ })).toBeDefined();
  });

  it('un module dont la source est hors ligne dit son état, sans valeur de remplacement', async () => {
    fetchMock.mockImplementation((input) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
      if (url.includes('/today/attention')) {
        return Promise.resolve(jsonResponse(makeAttentionSnapshot()));
      }
      if (url.includes('/portfolio')) {
        return Promise.reject(new TypeError('Failed to fetch'));
      }
      if (url.includes('/system/capabilities')) {
        return Promise.resolve(jsonResponse(makeCapabilities()));
      }
      if (url.includes('/calendar')) {
        return Promise.resolve(jsonResponse(makeCalendarResponse()));
      }
      if (url.includes('/opportunities')) {
        return Promise.resolve(jsonResponse(makeOpportunities()));
      }
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    });
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    const cellule = within(document.querySelector('[data-module="manual-portfolio"]') as HTMLElement);
    const etat = await cellule.findByRole('status');
    expect(etat.getAttribute('data-state')).toBe('offline');
    expect(cellule.queryByText('555')).toBeNull();
  });
});

describe("Page Aujourd'hui — instruments suivis (widgets servis)", () => {
  it('un widget par dossier publié : prix et variation du snapshot Marchés, série du dossier, fraîcheur servie', async () => {
    mockToday(makeAttentionSnapshot());
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    const rangee = within(await screen.findByTestId('focus-row'));
    const widgets = await rangee.findAllByTestId('instrument-widget');
    // Le fixture Opportunités ne publie qu'un candidat avec barres : SYN-ENER-01.
    expect(widgets).toHaveLength(1);
    const widget = within(widgets[0] as HTMLElement);
    expect(widget.getByRole('link', { name: 'SYN-ENER-01' })).toBeDefined();
    // Chaînes serveur du snapshot Marchés, virgule française.
    const cotation = makeMarketsOverview().sectors[0]!.tickers[0]!;
    expect(widget.getByText(cotation.last_close.replace('.', ','))).toBeDefined();
    expect(widget.getByText(`${cotation.return_1d_pct.replace('.', ',')} %`)).toBeDefined();
    // La série vient du dossier : un tracé, une description, une fraîcheur servie.
    expect(await widget.findByTestId('spark-line')).toBeDefined();
    expect(widget.getByRole('img', { name: /clôtures publiées/ })).toBeDefined();
    expect(widget.getByText(/dossier/)).toBeDefined();
  });

  it('dossier absent : le cadre de la courbe le DIT, aucune courbe plate à la place', async () => {
    fetchMock.mockImplementation((input) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
      if (url.includes('/today/attention')) {
        return Promise.resolve(jsonResponse(makeAttentionSnapshot()));
      }
      if (url.includes('/analysis/')) {
        return Promise.resolve(jsonResponse(makeEmptyAnalysis()));
      }
      if (url.includes('/system/capabilities')) {
        return Promise.resolve(jsonResponse(makeCapabilities()));
      }
      if (url.includes('/calendar')) {
        return Promise.resolve(jsonResponse(makeCalendarResponse()));
      }
      if (url.includes('/opportunities')) {
        return Promise.resolve(jsonResponse(makeOpportunities()));
      }
      if (url.includes('/portfolio')) {
        return Promise.resolve(jsonResponse(makePortfolioResponse()));
      }
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    });
    renderApp('/today');
    await screen.findByRole('heading', { level: 2, name: "File d'attention" });
    const widget = within((await screen.findAllByTestId('instrument-widget'))[0] as HTMLElement);
    expect((await widget.findByRole('status')).textContent).toContain('Aucun dossier d’analyse publié');
    expect(widget.queryByTestId('spark-line')).toBeNull();
  });
});
