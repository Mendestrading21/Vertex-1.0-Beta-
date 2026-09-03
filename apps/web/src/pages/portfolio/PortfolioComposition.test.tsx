/**
 * Page Portefeuille — la planche §7 est complète, servie ou déclarée (LOT-A6).
 *
 * Invariants : dix-huit modules dans le DOM, une seule dominante (la
 * concentration), huit absences au motif fermé sans chiffre, les dividendes
 * listés depuis le journal sans somme, l'exposition par devise verbatim, un
 * inspecteur par défaut (la valorisation publiée) remplacé par le lot ouvert.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import {
  makeCalendarResponse,
  makeEmptyPortfolioResponse,
  makeLedgerEntry,
  makeMarketsOverview,
  makePerformanceSnapshot,
  makePortfolioResponse,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { PORTFOLIO_MODULES, absentPortfolioModules } from './portfolioModules.ts';

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

function servir(portfolio: unknown = makePortfolioResponse()): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/markets/overview')) {
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    }
    if (url.includes('/v1/performance/')) {
      return Promise.resolve(jsonResponse(makePerformanceSnapshot()));
    }
    if (url.includes('/v1/calendar')) {
      return Promise.resolve(jsonResponse(makeCalendarResponse()));
    }
    if (url.endsWith('/v1/portfolio')) {
      return Promise.resolve(jsonResponse(portfolio));
    }
    return Promise.resolve(jsonResponse({ detail: 'unexpected route' }, 500));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('ResizeObserver', FakeResizeObserver);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderPortfolio(): Promise<void> {
  renderApp('/portfolio');
  await screen.findByRole('heading', { level: 1, name: 'Portefeuille' });
  await screen.findByTestId('portfolio-grid');
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Portefeuille — composition (LOT-A6)', () => {
  it('rend les DIX-HUIT modules de la planche, chacun à sa place', async () => {
    servir();
    await renderPortfolio();
    for (const module of PORTFOLIO_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
  });

  it('une seule dominante : la concentration', async () => {
    servir();
    await renderPortfolio();
    await screen.findByTestId('pf-bars-SYN');
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('concentration');
    expect(dominantes[0]?.classList.contains('vx-pf-concentration')).toBe(true);
  });

  it('les huit modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    servir();
    await renderPortfolio();
    for (const module of absentPortfolioModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('exposition par devise et performance totale : chaînes serveur verbatim', async () => {
    servir();
    await renderPortfolio();
    const devise = await screen.findByTestId('pf-currency-SYN');
    expect(devise.textContent).toContain('555');
    expect(devise.textContent).toContain('SYN');
    const totale = await screen.findByTestId('pf-total-performance');
    expect(within(totale).getByTestId('pf-total-twr_gross')).toBeDefined();
  });

  it('les dividendes sont listés depuis le journal, jamais sommés ; vide honnête sinon', async () => {
    servir(
      makePortfolioResponse({
        transactions: [
          makeLedgerEntry(),
          makeLedgerEntry({ id: 7, kind: 'DIVIDEND', instrument: { ticker: 'SYN-TECH-01' }, amount: '12.50' }),
          makeLedgerEntry({ id: 8, kind: 'DIVIDEND', instrument: { ticker: 'SYN-TECH-01' }, amount: '13.25' }),
        ],
      }),
    );
    await renderPortfolio();
    const liste = await screen.findByTestId('pf-dividends');
    expect(within(liste).getAllByRole('listitem')).toHaveLength(2);
    expect(liste.textContent).toContain('12.50');
    expect(liste.textContent).toContain('13.25');
    expect(liste.textContent).not.toContain('25.75');
  });

  it('sans dividende déclaré, le module le dit', async () => {
    servir();
    await renderPortfolio();
    expect((await screen.findByTestId('pf-dividends-empty')).textContent).toContain('Aucun dividende enregistré');
  });

  it('l’inspecteur porte la valorisation publiée ; « Détail » ouvre le lot ; « Fermer » y revient', async () => {
    const user = userEvent.setup();
    servir();
    await renderPortfolio();
    expect(await screen.findByTestId('pf-snapshot-facts')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Valorisation publiée' })).toBeDefined();
    await user.click(await screen.findByRole('button', { name: 'Inspecter SYN-TECH-01 (lot ledger-2)' }));
    const faits = await screen.findByTestId('pf-lot-facts');
    expect(faits.textContent).toContain('555');
    expect(faits.textContent).toContain('journal manuel');
    // Le poids publié du ticker dans sa devise, verbatim.
    expect(within(faits).getByText('1')).toBeDefined();
    // Les faits du journal qui portent ce ticker (le fait enregistré n°2).
    expect(within(screen.getByTestId('pf-lot-journal')).getByText('BUY_RECORDED')).toBeDefined();
    expect(screen.queryByTestId('pf-snapshot-facts')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Fermer' }));
    await waitFor(() => {
      expect(screen.queryByTestId('pf-lot-facts')).toBeNull();
    });
    expect(await screen.findByTestId('pf-snapshot-facts')).toBeDefined();
  });

  it('valorisation vide : la planche reste composée, les modules servis disent l’absence, une seule fois la raison', async () => {
    servir(makeEmptyPortfolioResponse());
    await renderPortfolio();
    for (const module of PORTFOLIO_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
    expect(document.querySelectorAll('.vx-main [data-rank="dominant"]')).toHaveLength(1);
    expect(screen.queryByTestId('pf-summary-grid')).toBeNull();
    expect(screen.getAllByText(/raison serveur : never_published/).length).toBeGreaterThan(0);
  });
});
