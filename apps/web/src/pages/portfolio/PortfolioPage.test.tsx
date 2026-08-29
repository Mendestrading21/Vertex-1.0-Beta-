/**
 * Page Portefeuille — cadre d'états, chiffres serveur VERBATIM (totaux
 * inclus), lots exclus SÉPARÉS avec raison (jamais un zéro), badge de
 * population de marques toujours visible, formulaire de FAIT PASSÉ (422
 * verbatim) et correction compensatoire (409 verbatim).
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeEmptyPortfolioResponse,
  makePortfolioResponse,
  makeValuationContent,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { valuationFrameStateOf } from './PortfolioPage.tsx';
import {
  localDateTimeToUtcIso,
  serverRejectionOf,
  valuationContentOf,
} from './portfolioView.ts';

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
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockRoutes(handlers: {
  readonly portfolio?: () => Response;
  readonly transaction?: () => Response;
  readonly compensate?: () => Response;
}): void {
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (method === 'POST' && url.endsWith('/compensate')) {
      return handlers.compensate?.() ?? jsonResponse({}, 500);
    }
    if (method === 'POST' && url.endsWith('/v1/portfolio/transactions')) {
      return handlers.transaction?.() ?? jsonResponse({}, 500);
    }
    if (method === 'GET' && url.endsWith('/v1/portfolio')) {
      return handlers.portfolio?.() ?? jsonResponse(makePortfolioResponse());
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

async function renderPortfolio(): Promise<void> {
  renderApp('/portfolio');
  await screen.findByRole('heading', { level: 1, name: 'Portefeuille' });
}

describe('valuationFrameStateOf — états dérivés de faits serveur uniquement', () => {
  it('relaie les états requête hors succès', () => {
    expect(valuationFrameStateOf('loading', undefined).state).toBe('loading');
    expect(valuationFrameStateOf('offline', undefined).state).toBe('offline');
    expect(valuationFrameStateOf('auth-required', undefined).state).toBe('auth-required');
  });

  it('succès sans données = erreur, jamais un faux succès', () => {
    expect(valuationFrameStateOf('ready', undefined).state).toBe('error');
  });

  it('valuation.state=empty vient du serveur → empty', () => {
    expect(valuationFrameStateOf('ready', makeEmptyPortfolioResponse()).state).toBe('empty');
  });

  it('lots exclus signalés par le serveur → partial (contenu visible sous bandeau)', () => {
    const frame = valuationFrameStateOf('ready', makePortfolioResponse());
    expect(frame.state).toBe('partial');
    expect(frame.view).not.toBeNull();
  });

  it('aucun exclu et marques OK → ready', () => {
    const data = makePortfolioResponse({
      valuation: {
        state: 'ok',
        snapshot_version: 3,
        as_of: '2026-08-25T12:00:00+00:00',
        reason: null,
        content: makeValuationContent({
          excluded_lots: [],
          coverage: {
            events_considered: 5,
            position_events: 3,
            cash_events: 2,
            compensation_pairs: 0,
            invalid_events: [],
            invalid_positions: [],
            lots_open: 1,
            lots_valued: 1,
            lots_excluded: 0,
          },
        }),
      },
    });
    expect(valuationFrameStateOf('ready', data).state).toBe('ready');
  });

  it('contenu illisible (mauvaise version de schéma) → error', () => {
    const data = makePortfolioResponse({
      valuation: {
        state: 'ok',
        snapshot_version: 3,
        as_of: null,
        reason: null,
        content: { schema_version: 'autre/9.9' },
      },
    });
    expect(valuationFrameStateOf('ready', data).state).toBe('error');
  });
});

describe('portfolioView — lecture verbatim, jamais un calcul', () => {
  it('valuationContentOf relaie les chaînes exactes du serveur', () => {
    const view = valuationContentOf({
      state: 'ok',
      snapshot_version: 3,
      as_of: '2026-08-25T12:00:00+00:00',
      reason: null,
      content: makeValuationContent(),
    });
    expect(view).not.toBeNull();
    expect(view!.blocks[0]!.totalUnrealized).toBe('55');
    expect(view!.blocks[0]!.totalRealized).toBe('49');
    expect(view!.blocks[0]!.totalValue).toBe('555');
    expect(view!.valuedLots).toHaveLength(1);
    expect(view!.valuedLots[0]!.mark).toBe('111');
    expect(view!.excludedLots).toEqual([
      { lotId: 'ledger-9', ticker: 'SYN-NOMARK-01', currency: 'SYN', reason: 'missing_mark' },
    ]);
  });

  it('localDateTimeToUtcIso convertit l’heure locale en instant UTC (suffixe Z)', () => {
    const iso = localDateTimeToUtcIso('2026-08-20T11:30');
    expect(iso).not.toBeNull();
    expect(iso!.endsWith('Z')).toBe(true);
    expect(localDateTimeToUtcIso('')).toBeNull();
    expect(localDateTimeToUtcIso('pas-une-date')).toBeNull();
  });

  it('serverRejectionOf relaie code/message ou défauts Pydantic, sans invention', () => {
    expect(serverRejectionOf({ detail: { code: 'EFFECTIVE_AT_IN_FUTURE', message: 'm' } })).toEqual({
      code: 'EFFECTIVE_AT_IN_FUTURE',
      message: 'm',
      wireIssues: [],
    });
    const wire = serverRejectionOf({
      detail: [{ loc: ['body', 'amount'], msg: 'value is not a valid decimal', type: 'x' }],
    });
    expect(wire!.wireIssues).toEqual(['body.amount : value is not a valid decimal']);
    expect(serverRejectionOf('n’importe quoi')).toBeNull();
  });
});

describe('Page Portefeuille — état nominal', () => {
  it('badge marques SYNTHÉTIQUES, totaux serveur verbatim, provenance et as_of', async () => {
    mockRoutes({});
    await renderPortfolio();

    await screen.findByTestId('pf-marks-badge');
    expect(screen.getByTestId('pf-marks-badge').textContent).toContain('Marks : DONNÉES SYNTHÉTIQUES');
    // Bandeau population non masquable (SyntheticBanner sur mark_population).
    expect(screen.getByText('DONNÉES SYNTHÉTIQUES')).toBeDefined();

    const summary = screen.getByTestId('pf-summary-grid');
    expect(within(summary).getByText('55')).toBeDefined(); // P&L latent — chaîne serveur
    expect(within(summary).getByText('49')).toBeDefined(); // P&L réalisé — chaîne serveur
    expect(within(summary).getByText('555')).toBeDefined(); // valeur — chaîne serveur
    // Espèces : absence honnête, jamais un total local.
    expect(screen.getByTestId('pf-cash-absent')).toBeDefined();
    // Provenance du calcul (lignage, pas un recalcul).
    expect(within(summary).getByText('portfolio.unrealized_pnl')).toBeDefined();
  });

  it('lots exclus dans une section séparée avec raison — jamais un zéro dans la table valorisée', async () => {
    mockRoutes({});
    await renderPortfolio();

    const table = await screen.findByRole('table', {
      name: 'Lots ouverts valorisés (valeurs serveur exactes)',
    });
    expect(within(table).getAllByRole('row')).toHaveLength(2); // entête + 1 lot valorisé
    expect(within(table).queryByText('SYN-NOMARK-01')).toBeNull();

    const excluded = screen.getByTestId('pf-excluded');
    expect(within(excluded).getByText('SYN-NOMARK-01')).toBeDefined();
    expect(within(excluded).getByText('missing_mark')).toBeDefined();
    expect(
      within(excluded).getByText('aucune clôture synthétique publiée pour ce ticker'),
    ).toBeDefined();
  });

  it('concentration : barres + table équivalente, poids = chaîne serveur', async () => {
    mockRoutes({});
    await renderPortfolio();
    await screen.findByTestId('pf-bars-SYN');
    const bars = screen.getByTestId('pf-bars-SYN');
    expect(within(bars).getByText('1')).toBeDefined(); // poids verbatim
    expect(
      screen.getByRole('table', { name: 'Poids de concentration (SYN)' }),
    ).toBeDefined();
  });

  it('journal : lignes verbatim et libellés de faits passés (jamais un impératif)', async () => {
    mockRoutes({});
    await renderPortfolio();
    const row = await screen.findByTestId('pf-ledger-row-2');
    expect(within(row).getByText('BUY_RECORDED')).toBeDefined();
    expect(within(row).getByText('-1000')).toBeDefined();
    expect(within(row).getByRole('button', { name: 'Correction compensatoire' })).toBeDefined();
  });
});

describe('Page Portefeuille — valorisation vide et hors ligne', () => {
  it('valuation empty → état vide avec la raison serveur, formulaire toujours présent', async () => {
    mockRoutes({ portfolio: () => jsonResponse(makeEmptyPortfolioResponse()) });
    await renderPortfolio();
    const empty = await screen.findByText(/raison serveur : never_published/);
    expect(empty).toBeDefined();
    expect(
      screen.getByRole('heading', {
        name: 'Enregistrer une transaction (déjà exécutée hors Vertex)',
      }),
    ).toBeDefined();
  });

  it('réseau coupé → offline honnête, aucune donnée fabriquée', async () => {
    fetchMock.mockRejectedValue(new TypeError('network down'));
    await renderPortfolio();
    await waitFor(() => {
      expect(document.querySelector('[data-state="offline"]')).not.toBeNull();
    });
    expect(screen.queryByTestId('pf-summary-grid')).toBeNull();
  });
});

describe('Formulaire — validation serveur affichée verbatim', () => {
  it('422 : code et message exacts du serveur, rien d’inventé', async () => {
    mockRoutes({
      transaction: () =>
        jsonResponse(
          {
            detail: {
              code: 'EFFECTIVE_AT_IN_FUTURE',
              message: 'a fact that has not happened yet cannot be recorded',
            },
          },
          422,
        ),
    });
    await renderPortfolio();
    await screen.findByRole('heading', {
      name: 'Enregistrer une transaction (déjà exécutée hors Vertex)',
    });
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/Effet le/), '2026-08-30T10:00');
    await user.type(screen.getByLabelText(/Impact de trésorerie signé/), '100');
    await user.type(screen.getByLabelText('Devise'), 'SYN');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la transaction' }));

    const rejected = await screen.findByTestId('pf-form-rejected');
    expect(within(rejected).getByText('EFFECTIVE_AT_IN_FUTURE')).toBeDefined();
    expect(rejected.textContent).toContain('a fact that has not happened yet cannot be recorded');
  });

  it('entrée incomplète : rien n’est envoyé', async () => {
    mockRoutes({});
    await renderPortfolio();
    await screen.findByRole('heading', {
      name: 'Enregistrer une transaction (déjà exécutée hors Vertex)',
    });
    const user = userEvent.setup();
    const postsBefore = fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST').length;
    await user.click(screen.getByRole('button', { name: 'Enregistrer la transaction' }));
    await screen.findByText('Entrée incomplète — rien n\'a été envoyé');
    const postsAfter = fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST').length;
    expect(postsAfter).toBe(postsBefore);
  });
});

describe('Correction compensatoire — confirmation, note obligatoire, 409 verbatim', () => {
  it('note obligatoire avant confirmation ; 409 ALREADY_COMPENSATED affiché', async () => {
    mockRoutes({
      compensate: () =>
        jsonResponse(
          {
            detail: {
              code: 'ALREADY_COMPENSATED',
              message: 'transaction 2 already has a compensating row',
            },
          },
          409,
        ),
    });
    await renderPortfolio();
    const user = userEvent.setup();

    const row = await screen.findByTestId('pf-ledger-row-2');
    await user.click(within(row).getByRole('button', { name: 'Correction compensatoire' }));

    const confirmBox = await screen.findByTestId('pf-compensate-confirm');
    const confirmButton = within(confirmBox).getByRole('button', {
      name: 'Confirmer la correction compensatoire',
    });
    expect((confirmButton as HTMLButtonElement).disabled).toBe(true); // note vide

    await user.type(within(confirmBox).getByLabelText('Raison de la correction'), 'erreur de saisie');
    await user.click(confirmButton);

    const rejected = await screen.findByTestId('pf-compensate-rejected');
    expect(within(rejected).getByText('ALREADY_COMPENSATED')).toBeDefined();
    expect(rejected.textContent).toContain('transaction 2 already has a compensating row');
  });
});
