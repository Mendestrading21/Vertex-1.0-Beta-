/**
 * Page Simulateur — composeur borné, unique action « Calculer », résultat
 * THÉORIQUE (breakevens certifiés rendus avec leur résidu), 422 affiché avec
 * la raison EXACTE du serveur, état invalid_input, honnêteté sur l'absence
 * de sauvegarde. Le moteur ECharts est substitué (jsdom sans canvas).
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { makeSimulationPreview } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { buildPreviewRequest, rejectionViewOf, splitGrid } from './simulatorView.ts';
import { EMPTY_ASSUMPTIONS, makeLegDraft } from './simulatorView.ts';
import { parseSimulatorTransfer } from './transfer.ts';

const setOption = vi.fn();
const dispose = vi.fn();
const resize = vi.fn();

vi.mock('../../charts/echartsLoader.ts', () => ({
  echarts: { init: vi.fn(() => ({ setOption, dispose, resize })) },
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
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderSimulator(): Promise<void> {
  renderApp('/simulator');
  await screen.findByRole('heading', { level: 1, name: 'Simulateur' });
}

async function fillMinimalForm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText('Strike (décimal)'), '100.00');
  await user.type(screen.getByLabelText('Prime unitaire déclarée (décimal)'), '4.30');
  await user.type(screen.getByLabelText('Spot déclaré (décimal)'), '102.50');
  await user.type(
    screen.getByLabelText('Volatilité annualisée (décimal, 0.25 = 25 %/an)'),
    '0.25',
  );
  await user.type(screen.getByLabelText('Taux annualisé (décimal)'), '0.02');
  await user.type(screen.getByLabelText('Rendement de dividende annualisé (décimal)'), '0.00');
  await user.type(
    screen.getByLabelText('Grille de spots (1 à 41 valeurs, séparées par des virgules)'),
    '90, 100, 110, 120',
  );
}

describe('simulatorView — construction et refus', () => {
  it('splitGrid découpe virgules/espaces et ignore le vide', () => {
    expect(splitGrid('90, 100  110;120,')).toEqual(['90', '100', '110', '120']);
    expect(splitGrid('')).toEqual([]);
  });

  it('buildPreviewRequest : chaînes verbatim, quantité signée par le sens', () => {
    const { request, issues } = buildPreviewRequest(
      [
        makeLegDraft({ side: 'LONG', count: '2', right: 'CALL', strike: '100.5', premium: '4.30' }),
        makeLegDraft({ side: 'SHORT', count: '1', right: 'PUT', strike: '95', premium: '2.10' }),
      ],
      { ...EMPTY_ASSUMPTIONS, spot: '102.5', volatility: '0.25', rate: '0.02', dividendYield: '0', spotGrid: '90 100', timeGridYears: '0' },
    );
    expect(issues).toEqual([]);
    expect(request?.legs[0]).toEqual({
      quantity: 2,
      right: 'CALL',
      strike: '100.5',
      premium: '4.30',
      multiplier: 100,
    });
    expect(request?.legs[1]?.quantity).toBe(-1);
    expect(request?.assumptions.spot_grid).toEqual(['90', '100']);
  });

  it('invalid_input structurel : STOCK avec strike, quantité non entière, grille absente', () => {
    const { request, issues } = buildPreviewRequest(
      [makeLegDraft({ right: 'STOCK', strike: '100', count: '1.5', premium: '' })],
      EMPTY_ASSUMPTIONS,
    );
    expect(request).toBeNull();
    expect(issues.some((issue) => issue.includes('STOCK'))).toBe(true);
    expect(issues.some((issue) => issue.includes('entier'))).toBe(true);
    expect(issues.some((issue) => issue.includes('grille de spots'))).toBe(true);
  });

  it('rejectionViewOf : code typé + explication française, ou défauts wire', () => {
    const refusal = rejectionViewOf({
      detail: { code: 'UNCOVERED_SHORT_UPSIDE_TAIL', message: 'net tail is -100 < 0' },
    });
    expect(refusal?.kind).toBe('refusal');
    expect(refusal?.code).toBe('UNCOVERED_SHORT_UPSIDE_TAIL');
    expect(refusal?.explanation).toContain('perte théorique n’est pas bornée');
    const wire = rejectionViewOf({
      detail: [{ loc: ['body', 'legs', 0, 'strike'], msg: 'Field required', type: 'missing' }],
    });
    expect(wire?.kind).toBe('wire');
    expect(wire?.wireIssues[0]).toContain('strike');
    expect(rejectionViewOf('nonsense')).toBeNull();
  });

  it('parseSimulatorTransfer : fail-closed sur état absent/malformé', () => {
    expect(parseSimulatorTransfer(undefined)).toBeNull();
    expect(parseSimulatorTransfer({ version: 99 })).toBeNull();
    expect(
      parseSimulatorTransfer({
        version: 1,
        source: 'options',
        underlying: 'SYN-TECH-01',
        right: 'CALL',
        strike: '100.00',
        expiration: '2026-09-26',
        tradingClass: 'SYN-TECH-01',
        multiplier: 100,
        currency: 'SYN',
      })?.strike,
    ).toBe('100.00');
  });
});

describe('Page Simulateur — parcours', () => {
  it('honnêteté : sauvegarde NON_IMPLÉMENTÉ, aucun résultat précalculé (empty)', async () => {
    await renderSimulator();
    expect(screen.getByText(/NON_IMPLÉMENTÉ/)).toBeDefined();
    expect(screen.getByText(/lot ultérieur/)).toBeDefined();
    expect(screen.getByText(/Aucun résultat/)).toBeDefined();
    expect(screen.getByRole('button', { name: 'Calculer' })).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('composeur borné : 8 jambes maximum, ajout désactivé au plafond', async () => {
    const user = userEvent.setup();
    await renderSimulator();
    const addLeg = screen.getByRole('button', { name: 'Ajouter une jambe' });
    for (let index = 0; index < 7; index += 1) {
      await user.click(addLeg);
    }
    expect(screen.getByText('Structure déclarée (8/8 jambes)')).toBeDefined();
    expect((addLeg as HTMLButtonElement).disabled).toBe(true);
  });

  it('invalid_input : rien n’est envoyé, défauts listés', async () => {
    const user = userEvent.setup();
    await renderSimulator();
    await user.click(screen.getByRole('button', { name: 'Calculer' }));
    const invalid = await screen.findByTestId('sim-invalid-input');
    expect(invalid.textContent).toContain('rien n\'a été envoyé');
    expect(invalid.textContent).toContain('strike est requis');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('Calculer → résultat THÉORIQUE : breakevens rendus avec résidu certifié, écho, avertissements', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse(makeSimulationPreview()));
    await renderSimulator();
    await fillMinimalForm(user);
    await user.click(screen.getByRole('button', { name: 'Calculer' }));

    const result = await screen.findByTestId('sim-result');
    const scoped = within(result);
    expect(scoped.getAllByText('THÉORIQUE').length).toBeGreaterThanOrEqual(1);
    // Breakevens certifiés avec résidu et encadrement.
    const breakevens = scoped.getByTestId('sim-breakevens');
    expect(breakevens.textContent).toContain('104.00');
    expect(breakevens.textContent).toContain('0.00');
    expect(breakevens.textContent).toContain('100.00');
    expect(breakevens.textContent).toContain('110.00');
    // Gain/perte max sur la grille.
    expect(scoped.getByText(/Gain max/)).toBeDefined();
    expect(scoped.getAllByText('600.00').length).toBeGreaterThanOrEqual(1);
    expect(scoped.getAllByText('-400.00').length).toBeGreaterThanOrEqual(1);
    // Hypothèses écho (serveur) + avertissements verbatim.
    expect(scoped.getByText('102.50')).toBeDefined();
    expect(scoped.getByText(/THEORETICAL values from declared assumptions/)).toBeDefined();
    // Vérification de risque défini relayée.
    expect(scoped.getByText(/BULL_CALL_DEBIT/)).toBeDefined();
    // Le moteur substitué a reçu les points serveur (dominante montée).
    expect(setOption).toHaveBeenCalled();
    // Table équivalente des points (chaînes exactes).
    const table = scoped.getByRole('table', { name: /Points de P&L/ });
    expect(within(table).getAllByRole('row')).toHaveLength(1 + 5);
  });

  it('422 : raison EXACTE affichée (code + message serveur + explication française)', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          detail: {
            code: 'UNCOVERED_SHORT_UPSIDE_TAIL',
            message: 'net multiplier-weighted CALL+STOCK quantity on the S->inf tail is -100 < 0',
          },
        },
        422,
      ),
    );
    await renderSimulator();
    await fillMinimalForm(user);
    await user.click(screen.getByRole('button', { name: 'Calculer' }));
    const rejection = await screen.findByTestId('sim-rejection');
    expect(rejection.textContent).toContain('422');
    expect(rejection.textContent).toContain('UNCOVERED_SHORT_UPSIDE_TAIL');
    expect(rejection.textContent).toContain('net multiplier-weighted CALL+STOCK quantity');
    expect(rejection.textContent).toContain('perte théorique n’est pas bornée');
    expect(screen.queryByTestId('sim-result')).toBeNull();
  });

  it('422 wire : les défauts exacts de validation sont listés', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(
      jsonResponse(
        { detail: [{ loc: ['body', 'assumptions', 'spot'], msg: 'Invalid decimal', type: 'value_error' }] },
        422,
      ),
    );
    await renderSimulator();
    await fillMinimalForm(user);
    await user.click(screen.getByRole('button', { name: 'Calculer' }));
    const rejection = await screen.findByTestId('sim-rejection');
    expect(rejection.textContent).toContain('body.assumptions.spot');
    expect(rejection.textContent).toContain('Invalid decimal');
  });

  it('offline honnête : aucun calcul effectué', async () => {
    const user = userEvent.setup();
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    await renderSimulator();
    await fillMinimalForm(user);
    await user.click(screen.getByRole('button', { name: 'Calculer' }));
    await screen.findByText('Hors ligne');
    expect(screen.getByText(/aucun calcul n'a été effectué/)).toBeDefined();
  });

  it('session requise sur 401', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));
    await renderSimulator();
    await fillMinimalForm(user);
    await user.click(screen.getByRole('button', { name: 'Calculer' }));
    await screen.findByText('Session requise');
  });
});
