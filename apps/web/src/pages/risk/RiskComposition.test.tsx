/**
 * Page Risques — la planche §9 est complète, servie ou déclarée (LOT-A6).
 *
 * Invariants : dix-neuf modules dans le DOM, une seule dominante (la
 * matrice), douze absences au motif fermé sans chiffre — dont le score de
 * risque —, la concentration du registre et le drawdown lus par leurs
 * propriétaires, un inspecteur par défaut (la matrice publiée) remplacé par
 * l'instrument ouvert depuis un en-tête de ligne.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { makeMarketsOverview, makePerformanceSnapshot, makePortfolioResponse } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { RISK_MODULES, absentRiskModules } from './riskModules.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

/** La forme EXACTE que le relais API sert (vertex.risk-matrix/1.0), SYNTHÉTIQUE. */
function makeRiskMatrix(): Record<string, unknown> {
  return {
    state: 'ok',
    snapshot_version: 6,
    as_of: '2026-09-01T13:02:30+00:00',
    age_seconds: 115,
    reason: null,
    content: {
      schema_version: 'vertex.risk-matrix/1.0',
      as_of: '2026-09-01T13:02:30+00:00',
      population: 'SYNTHETIC',
      data_state: 'ok',
      unit: 'correlation_coefficient',
      engine_version: '0.1.0',
      conclusion: 'Matrice de corrélation sur 3 instruments et 242 rendements.',
      instruments: [
        { ticker: 'SYN-TECH-01', label: 'Synthetic Tech One' },
        { ticker: 'SYN-BANK-01', label: 'Synthetic Bank One' },
        { ticker: 'SYN-ENER-01', label: 'Synthetic Energy One' },
      ],
      matrix: [
        ['1.000', '-0.803', '0.168'],
        ['-0.803', '1.000', '-0.092'],
        ['0.168', '-0.092', '1.000'],
      ],
      matrix_bands: [
        ['self', 'strong_negative', 'weak'],
        ['strong_negative', 'self', 'weak'],
        ['weak', 'weak', 'self'],
      ],
      extremes: {
        most_correlated: { a: 'SYN-TECH-01', b: 'SYN-ENER-01', value: '0.168' },
        most_opposed: { a: 'SYN-TECH-01', b: 'SYN-BANK-01', value: '-0.803' },
      },
      synchronicity_warning: 'Les places ne ferment pas à la même heure.',
      coverage: {
        perimeter: ['SYN-TECH-01', 'SYN-BANK-01', 'SYN-ENER-01', 'SYN-NOBAR-01'],
        perimeter_size: 4,
        retained: ['SYN-TECH-01', 'SYN-BANK-01', 'SYN-ENER-01'],
        retained_count: 3,
        discarded: [{ instrument: 'SYN-NOBAR-01', reason: 'no_bars' }],
        rejected_records: [],
        common_trading_days: 243,
        minimum_common_days: 30,
        moderate_threshold: '0.30',
        strong_threshold: '0.70',
        trading_days_per_instrument: { 'SYN-TECH-01': 251, 'SYN-BANK-01': 252, 'SYN-ENER-01': 257 },
        trading_days_lost_to_alignment: { 'SYN-TECH-01': 8, 'SYN-BANK-01': 9, 'SYN-ENER-01': 14 },
        window_start: '2025-09-02',
        window_end: '2026-08-31',
        observations_considered: 3,
        lookback_seconds: 1209600,
        refusal_reason: null,
      },
    },
  };
}

function servir(matrix: unknown = makeRiskMatrix()): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/risk/matrix')) {
      return Promise.resolve(jsonResponse(matrix));
    }
    if (url.includes('/v1/performance/')) {
      return Promise.resolve(jsonResponse(makePerformanceSnapshot()));
    }
    if (url.endsWith('/v1/portfolio')) {
      return Promise.resolve(jsonResponse(makePortfolioResponse()));
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

async function renderRisk(): Promise<void> {
  renderApp('/risks');
  await screen.findByRole('heading', { level: 1, name: 'Risques' });
  await screen.findByTestId('risk-grid');
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Risques — composition (LOT-A6)', () => {
  it('rend les DIX-NEUF modules de la planche, chacun à sa place', async () => {
    servir();
    await renderRisk();
    for (const module of RISK_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
  });

  it('une seule dominante : la matrice, qui garde son témoin', async () => {
    servir();
    await renderRisk();
    await screen.findByTestId('risk-grid');
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('correlations');
    expect(dominantes[0]?.querySelector('.vx-riskmatrix')).not.toBeNull();
  });

  it('les douze modules absents portent leur motif fermé, sans chiffre — le score de risque en tête', async () => {
    servir();
    await renderRisk();
    for (const module of absentRiskModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
    expect(cellule('risk-score').getByText(ABSENCE_REASONS.NO_SOURCE.label)).toBeDefined();
  });

  it('concentration du registre et drawdown : lus par leurs propriétaires, chaînes verbatim, sans table', async () => {
    servir();
    await renderRisk();
    const concentration = await screen.findByTestId('risk-concentration');
    expect(within(concentration).getByTestId('risk-bars-SYN')).toBeDefined();
    expect(within(concentration).getByTestId('risk-herfindahl-SYN').textContent).toContain('1');
    const drawdown = await screen.findByTestId('risk-drawdown');
    expect(within(drawdown).getByTestId('risk-drawdown_gross')).toBeDefined();
    // La seule table VISIBLE de la page reste la matrice. Les formes v2
    // (barres sur rail, aire sous une série) portent chacune leur table
    // ÉQUIVALENTE, exigée par `docs/05-design/CHART_STANDARD.md` pour les
    // lecteurs d'écran : elle vit repliée dans un `<details>` fermé, et
    // n'ajoute donc aucune grille de chiffres à l'écran. L'invariant est
    // vérifié ici plus strictement qu'avant : on compte les tables visibles
    // ET on exige que chacune des autres soit bien repliée.
    const tables = screen.getAllByRole('table');
    const visibles = tables.filter((table) => table.closest('details') === null);
    expect(visibles).toHaveLength(1);
    expect(visibles[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('correlations');
    for (const table of tables) {
      if (table.closest('details') !== null) {
        expect(table.closest('details')?.hasAttribute('open')).toBe(false);
      }
    }
  });

  it('couverture, alignement et écarts sont servis avec le périmètre retenu', async () => {
    servir();
    await renderRisk();
    expect((await screen.findByTestId('risk-coverage')).textContent).toContain('3 sur 4 déclarés');
    expect(screen.getByTestId('risk-alignment').textContent).toContain('SYN-ENER-01');
    expect(screen.getByTestId('risk-discards').textContent).toContain('aucune barre quotidienne collectée');
  });

  it('l’inspecteur porte la matrice publiée ; un en-tête de ligne ouvre l’instrument ; « Fermer » y revient', async () => {
    const user = userEvent.setup();
    servir();
    await renderRisk();
    expect(await screen.findByTestId('risk-matrix-facts')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Matrice publiée' })).toBeDefined();
    await user.click(screen.getByRole('button', { name: 'Inspecter SYN-BANK-01 (Synthetic Bank One)' }));
    const faits = await screen.findByTestId('risk-instrument-facts');
    expect(faits.textContent).toContain('252');
    const coefficients = screen.getByTestId('risk-instrument-coefficients');
    expect(within(coefficients).getAllByRole('listitem')).toHaveLength(2);
    expect(coefficients.textContent).toContain('-0.803');
    expect(coefficients.textContent).toContain('Fortement liés, sens contraire');
    expect(screen.queryByTestId('risk-matrix-facts')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Fermer' }));
    await waitFor(() => {
      expect(screen.queryByTestId('risk-instrument-facts')).toBeNull();
    });
    expect(await screen.findByTestId('risk-matrix-facts')).toBeDefined();
  });

  it('aucun instantané publié : la planche reste composée, la dominante porte l’aveu', async () => {
    servir({ state: 'empty', snapshot_version: null, as_of: null, age_seconds: null, content: null, reason: 'no snapshot published' });
    await renderRisk();
    for (const module of RISK_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
    expect(cellule('correlations').getByText(/no snapshot published/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('une bande NON publiée reste « inconnue » et visible — jamais « peu liés »', async () => {
    /**
     * Le composant précédent remplaçait une bande absente par `weak`, ce qui
     * affirmait « peu liés » sur une case dont le serveur n'avait rien publié.
     * La grille v2 rend `data-band="unknown"`, visible et nommée, et la case
     * sans coefficient se lit « non publié ».
     */
    const snapshot = makeRiskMatrix();
    const contenu = snapshot.content as Record<string, unknown>;
    const bandes = (contenu.matrix_bands as string[][]).map((ligne) => [...ligne]);
    const valeurs = (contenu.matrix as string[][]).map((ligne) => [...ligne]);
    // Une bande retirée par la source, et un coefficient publié dans une forme
    // que l'interface ne sait pas lire.
    bandes[0]![1] = '';
    valeurs[0]![1] = null as unknown as string;
    servir({ ...snapshot, content: { ...contenu, matrix_bands: bandes, matrix: valeurs } });
    await renderRisk();

    const grille = document.querySelector('[data-module="correlations"] table') as HTMLElement;
    const inconnues = grille.querySelectorAll('[data-band="unknown"]');
    expect(inconnues.length).toBeGreaterThan(0);
    expect((inconnues[0] as HTMLElement).getAttribute('title')).toBe('bande non publiée par le serveur');
    expect(inconnues[0]?.textContent).toBe('non publié');
    expect(grille.querySelectorAll('[data-band="weak"]').length).toBe(
      // Aucune case ne devient « peu liés » par défaut : seules celles que le
      // serveur a réellement publiées en `weak` portent cette bande.
      bandes.flat().filter((band) => band === 'weak').length,
    );
  });
});
