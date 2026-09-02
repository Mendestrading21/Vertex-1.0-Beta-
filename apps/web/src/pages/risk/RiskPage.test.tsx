/**
 * Page Risques — matrice servie, refus motivé, vide honnête, et l'absence de
 * tout calcul financier en TypeScript.
 *
 * CE QUE CES TESTS PROTÈGENT EN PRIORITÉ.
 *
 * 1. **Les coefficients affichés sont EXACTEMENT les chaînes serveur.** Pas
 *    d'arrondi refait ici : un `0.927` réaffiché `0.93` serait un nombre
 *    différent de celui que le serveur a certifié.
 * 2. **Les couleurs viennent des bandes PUBLIÉES**, jamais d'une comparaison
 *    locale à un seuil. Le seuil est un jugement de domaine, il vit au
 *    serveur.
 * 3. **Un refus motivé n'est pas un écran vide.** Le motif s'affiche.
 * 4. **L'avertissement de synchronicité est visible.** Sans lui, SPX/N225 à
 *    +0,168 se lirait comme une décorrélation du Japon plutôt que comme un
 *    artefact de fuseau horaire.
 */
import { screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { makeMarketsOverview } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { BAND_LABELS, correlationRowsOf } from './CorrelationMatrix.tsx';
import { DISCARD_LABELS, REFUSAL_LABELS, riskViewOf } from './riskView.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** La forme EXACTE que le relais API sert (vertex.risk-matrix/1.0). */
function makeRiskMatrix(overrides: Record<string, unknown> = {}) {
  return {
    state: 'ok',
    snapshot_version: 6,
    as_of: '2026-09-01T13:02:30+00:00',
    age_seconds: 115,
    reason: null,
    content: {
      schema_version: 'vertex.risk-matrix/1.0',
      as_of: '2026-09-01T13:02:30+00:00',
      population: 'REAL',
      data_state: 'ok',
      unit: 'correlation_coefficient',
      engine_version: '0.1.0',
      conclusion: 'Matrice de corrélation sur 3 instruments et 242 rendements.',
      instruments: [
        { ticker: 'SPX', label: 'S&P 500' },
        { ticker: 'VIX', label: 'Volatilité S&P 500' },
        { ticker: 'N225', label: 'Nikkei 225' },
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
        most_correlated: { a: 'SPX', b: 'N225', value: '0.168' },
        most_opposed: { a: 'SPX', b: 'VIX', value: '-0.803' },
      },
      synchronicity_warning:
        'Les places ne ferment pas à la même heure. Deux rendements « du même jour » peuvent porter sur des instants disjoints.',
      coverage: {
        perimeter: ['SPX', 'VIX', 'N225'],
        perimeter_size: 3,
        retained: ['SPX', 'VIX', 'N225'],
        retained_count: 3,
        discarded: [],
        rejected_records: [],
        common_trading_days: 243,
        minimum_common_days: 30,
        moderate_threshold: '0.30',
        strong_threshold: '0.70',
        trading_days_per_instrument: { SPX: 251, VIX: 252, N225: 257 },
        trading_days_lost_to_alignment: { SPX: 8, VIX: 9, N225: 14 },
        window_start: '2025-09-02',
        window_end: '2026-08-31',
        observations_considered: 3,
        lookback_seconds: 1209600,
        refusal_reason: null,
      },
      ...((overrides.content as Record<string, unknown>) ?? {}),
    },
    ...overrides,
  };
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * Sert la matrice sur /risk/matrix, et l'aperçu des marchés partout ailleurs.
 *
 * Le bandeau du shell (ShellTicker) interroge markets/overview sur TOUTES les
 * pages. Un mock qui renverrait la matrice à chaque appel le ferait planter —
 * et l'échec porterait alors sur le bandeau, pas sur la page testée. Router
 * par URL garde chaque test sur son sujet.
 */
function mockRiskRoute(body: unknown, options: { readonly reject?: boolean } = {}): void {
  fetchMock.mockImplementation((input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (url.includes('/risk/matrix')) {
      return options.reject === true
        ? Promise.reject(new TypeError('Failed to fetch'))
        : Promise.resolve(jsonResponse(body));
    }
    return Promise.resolve(jsonResponse(makeMarketsOverview()));
  });
}

async function renderRisk(): Promise<void> {
  renderApp('/risks');
  await screen.findByRole('heading', { level: 1, name: 'Risques' });
}

describe('riskViewOf — lecture du contrat, aucune arithmétique', () => {
  it('les coefficients traversent la vue SANS être touchés', () => {
    const view = riskViewOf(makeRiskMatrix() as never);
    expect(view.matrix).toEqual([
      ['1.000', '-0.803', '0.168'],
      ['-0.803', '1.000', '-0.092'],
      ['0.168', '-0.092', '1.000'],
    ]);
  });

  it('les seuils restent les CHAÎNES publiées, jamais reformatées', () => {
    const view = riskViewOf(makeRiskMatrix() as never);
    expect(view.coverage.moderateThreshold).toBe('0.30');
    expect(view.coverage.strongThreshold).toBe('0.70');
  });

  it('la perte d’alignement est triée par coût décroissant', () => {
    const view = riskViewOf(makeRiskMatrix() as never);
    expect(view.coverage.alignmentLoss.map((entry) => entry.ticker)).toEqual([
      'N225',
      'VIX',
      'SPX',
    ]);
  });

  it('un motif de refus est traduit, un motif inconnu reste lisible tel quel', () => {
    const refuse = riskViewOf(
      makeRiskMatrix({
        content: { coverage: { refusal_reason: 'insufficient_common_days' } },
      }) as never,
    );
    expect(refuse.refusalReason).toBe(REFUSAL_LABELS.insufficient_common_days);

    const inconnu = riskViewOf(
      makeRiskMatrix({ content: { coverage: { refusal_reason: 'motif_futur' } } }) as never,
    );
    // Jamais avalé : un motif que l'interface ne connaît pas s'affiche brut
    // plutôt que de disparaître.
    expect(inconnu.refusalReason).toBe('motif_futur');
  });

  it('un instrument écarté porte son motif en français', () => {
    const view = riskViewOf(
      makeRiskMatrix({
        content: {
          coverage: { discarded: [{ instrument: 'DAX', reason: 'no_bars' }] },
        },
      }) as never,
    );
    expect(view.coverage.discarded[0]?.reason).toBe(DISCARD_LABELS.no_bars);
  });
});

describe('correlationRowsOf — appariement ligne/colonne', () => {
  it('chaque cellule reçoit la bande de sa position, pas celle d’à côté', () => {
    const rows = correlationRowsOf({
      instruments: [
        { ticker: 'A', label: 'Alpha' },
        { ticker: 'B', label: 'Beta' },
      ],
      matrix: [
        ['1.000', '0.900'],
        ['0.900', '1.000'],
      ],
      bands: [
        ['self', 'strong_positive'],
        ['strong_positive', 'self'],
      ],
    });
    expect(rows[0]?.cells[0]).toEqual({ value: '1.000', band: 'self' });
    expect(rows[0]?.cells[1]).toEqual({ value: '0.900', band: 'strong_positive' });
    expect(rows[1]?.cells[0]).toEqual({ value: '0.900', band: 'strong_positive' });
  });
});

describe('Page Risques — état nominal', () => {
  it('sert la matrice avec ses coefficients EXACTS et ses bandes serveur', async () => {
    mockRiskRoute(makeRiskMatrix());
    await renderRisk();

    const grille = await screen.findByRole('table');
    // Les valeurs affichées sont celles du serveur, au caractère près.
    expect(within(grille).getAllByText('-0.803').length).toBe(2);
    expect(within(grille).getAllByText('0.168').length).toBe(2);

    // La bande vient du serveur : elle est portée par `data-band`, jamais
    // recalculée à partir du nombre.
    const cellules = grille.querySelectorAll('td[data-band]');
    expect(cellules.length).toBe(9);
    expect(cellules[1]?.getAttribute('data-band')).toBe('strong_negative');
    expect(cellules[2]?.getAttribute('data-band')).toBe('weak');
  });

  it('affiche l’avertissement de synchronicité, jamais rangé en note', async () => {
    mockRiskRoute(makeRiskMatrix());
    await renderRisk();
    expect(await screen.findByRole('note')).toBeDefined();
  });

  it('affiche les seuils déclarés — un seuil invisible ne se discute pas', async () => {
    mockRiskRoute(makeRiskMatrix());
    await renderRisk();
    expect(await screen.findByText(/modéré à partir de/)).toBeDefined();
    expect(screen.getByText(/0\.70/)).toBeDefined();
  });

  it('publie le coût de l’alignement séance par séance', async () => {
    mockRiskRoute(makeRiskMatrix());
    await renderRisk();
    expect(await screen.findByText("Ce que l'alignement a coûté")).toBeDefined();
    expect(screen.getByText(/14 séances perdues/)).toBeDefined();
  });

  it('nomme les deux paires extrêmes', async () => {
    mockRiskRoute(makeRiskMatrix());
    await renderRisk();
    expect(await screen.findByText('Paire la plus opposée')).toBeDefined();
    expect(screen.getByText(/SPX et VIX/)).toBeDefined();
  });

  it('la légende nomme les cinq bandes en français', async () => {
    mockRiskRoute(makeRiskMatrix());
    await renderRisk();
    const legende = await screen.findByRole('list', { name: 'Légende des bandes' });
    for (const band of [
      'strong_positive',
      'moderate_positive',
      'weak',
      'moderate_negative',
      'strong_negative',
    ]) {
      expect(within(legende).getByText(BAND_LABELS[band] as string)).toBeDefined();
    }
  });
});

describe('Page Risques — états honnêtes', () => {
  it('un refus du worker AFFICHE son motif, il ne vide pas l’écran', async () => {
    mockRiskRoute(
      makeRiskMatrix({
          content: {
            conclusion: 'Seulement 12 séances communes aux 3 instruments retenus.',
            instruments: [],
            matrix: [],
            matrix_bands: [],
            extremes: null,
            data_state: 'insufficient',
            coverage: {
              perimeter: ['SPX', 'VIX', 'N225'],
              perimeter_size: 3,
              retained: [],
              retained_count: 0,
              discarded: [],
              rejected_records: [],
              common_trading_days: 12,
              minimum_common_days: 30,
              moderate_threshold: '0.30',
              strong_threshold: '0.70',
              refusal_reason: 'insufficient_common_days',
            },
        },
      }),
    );
    await renderRisk();

    // Le motif ET la conclusion serveur sont lisibles : ce n'est pas une panne.
    expect(await screen.findByText(/Seulement 12 séances communes/)).toBeDefined();
    expect(screen.getByText(/sous le seuil déclaré/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('aucun instantané publié : dit pourquoi, n’invente rien', async () => {
    mockRiskRoute({
        state: 'empty',
        snapshot_version: null,
        as_of: null,
        age_seconds: null,
        content: null,
        reason: 'no snapshot published',
    });
    await renderRisk();
    expect(await screen.findByText(/Aucun instantané publié/)).toBeDefined();
    expect(screen.getByText(/no snapshot published/)).toBeDefined();
  });

  it('un instantané périmé sert QUAND MÊME la matrice, sous son bandeau', async () => {
    mockRiskRoute(makeRiskMatrix({ state: 'stale', reason: 'closed session budget exceeded' }));
    await renderRisk();
    // Périmé n'est pas absent : la grille reste lisible.
    expect(await screen.findByRole('table')).toBeDefined();
  });

  it('API injoignable : le dit, sans matrice vide trompeuse', async () => {
    mockRiskRoute(null, { reject: true });
    await renderRisk();
    expect(await screen.findByText(/injoignable/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });
});
