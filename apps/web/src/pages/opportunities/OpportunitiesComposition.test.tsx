/**
 * Page Opportunités — la planche §3 est complète, servie ou déclarée (LOT-A4).
 *
 * Invariants : les quatorze modules sont dans le DOM, une seule dominante
 * (le classement, qui contient les deux groupes), six absences au motif
 * fermé sans chiffre, les mesures servies sont les comptes publiés, et
 * l'inspecteur porte la vérité du snapshot jusqu'à ce qu'un candidat soit
 * ouvert — puis y retourne.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import {
  makeExcludedCandidate,
  makeOpportunities,
  makeOpportunitiesContent,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { OPPORTUNITIES_MODULES, absentOpportunitiesModules } from './opportunitiesModules.ts';

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

function mockOpportunities(response: unknown): void {
  fetchMock.mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes('/v1/opportunities')) {
      return jsonResponse(response);
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

async function renderOpportunities(): Promise<void> {
  renderApp('/opportunities');
  await screen.findByRole('heading', { level: 2, name: 'Classement publié' });
}

describe('Page Opportunités — composition (LOT-A4)', () => {
  it('rend les QUATORZE modules de la planche, chacun à sa place', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    for (const module of OPPORTUNITIES_MODULES) {
      expect(
        document.querySelector(`[data-module="${module.id}"]`),
        `module « ${module.title} » (${module.id}) absent du DOM`,
      ).not.toBeNull();
    }
  });

  it('une seule dominante : le classement, qui contient les deux groupes', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    const dominante = dominantes[0] as HTMLElement;
    expect(dominante.closest('[data-module]')?.getAttribute('data-module')).toBe('ranking');
    expect(within(dominante).getByTestId('opp-group-qualified')).toBeDefined();
    expect(within(dominante).getByTestId('opp-group-excluded')).toBeDefined();
  });

  it('les six modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    expect(absentOpportunitiesModules()).toHaveLength(6);
    for (const module of absentOpportunitiesModules()) {
      const zone = within(document.querySelector(`[data-module="${module.id}"]`) as HTMLElement);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('les mesures servies sont les comptes PUBLIÉS : couverture, directions, statuts', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    expect(screen.getByTestId('opp-ideas-universe').textContent).toContain('24');
    expect(screen.getByTestId('opp-ideas-excluded').textContent).toContain('1');
    expect(screen.getByTestId('opp-ideas-qualified').textContent).toContain('0');
    // Une direction UNKNOWN compte comme UNKNOWN — jamais comme neutre.
    const direction = screen.getByTestId('opp-direction-UNKNOWN');
    expect(within(direction).getByText('1')).toBeDefined();
    expect(screen.queryByTestId('opp-direction-NEUTRAL')).toBeNull();
    const statut = screen.getByTestId('opp-status-count-INSUFFICIENT_DATA');
    expect(within(statut).getByText('1')).toBeDefined();
    // Le pied de la dominante porte l'ordre publié, verbatim.
    const dominante = document.querySelector('[data-module="ranking"]') as HTMLElement;
    expect(within(dominante).getByText(/status_rank asc → degraded_gates_count asc → ticker asc/)).toBeDefined();
  });

  it('l’inspecteur porte la vérité du snapshot ; « Inspecter » ouvre le candidat ; « Fermer » y revient', async () => {
    const user = userEvent.setup();
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    expect(await screen.findByTestId('opp-snapshot-facts')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Snapshot publié' })).toBeDefined();

    await user.click(screen.getByRole('button', { name: 'Inspecter SYN-ENER-01' }));
    await waitFor(() => {
      expect(screen.queryByTestId('opp-snapshot-facts')).toBeNull();
    });
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — SYN-ENER-01' })).toBeDefined();
    const facts = screen.getByTestId('opp-candidate-facts');
    expect(facts.textContent).toContain('INSUFFICIENT_DATA');
    expect(facts.textContent).toContain('Statut fermé par une gate bloquante');
    const gates = screen.getByTestId('opp-candidate-gates');
    expect(gates.textContent).toContain('entitlements_sufficient');
    expect(gates.textContent).toContain('UNEVALUABLE');
    const evidence = screen.getByTestId('opp-candidate-evidence');
    expect(within(evidence).getByText('regime').closest('li')?.getAttribute('data-present')).toBe('false');
    expect(within(evidence).getByText('sector').closest('li')?.getAttribute('data-present')).toBe('true');
    expect(screen.getByRole('link', { name: 'Ouvrir le dossier d’analyse' }).getAttribute('href')).toBe(
      '/analysis/SYN-ENER-01',
    );

    await user.click(screen.getByRole('button', { name: 'Fermer' }));
    expect(await screen.findByTestId('opp-snapshot-facts')).toBeDefined();
  });

  it('un candidat contredit ouvert dans l’inspecteur dit ses faits disqualifiants', async () => {
    const user = userEvent.setup();
    mockOpportunities(
      makeOpportunities({
        content: makeOpportunitiesContent({
          qualified: [makeExcludedCandidate({ ticker: 'SYN-POISON-01' })],
          excluded: [],
        }),
      }),
    );
    await renderOpportunities();
    await user.click(screen.getByRole('button', { name: 'Inspecter SYN-POISON-01' }));
    const note = await screen.findByText(/contredit par ses propres faits/);
    expect(note.textContent).toContain('gate bloquante');
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — SYN-POISON-01' })).toBeDefined();
  });

  it('un filtre de statut masque LOCALEMENT sans reclasser ni changer les comptes publiés', async () => {
    const user = userEvent.setup();
    const qualified = makeExcludedCandidate({
      ticker: 'SYN-OK-01',
      advice: { ...(makeExcludedCandidate()['advice'] as object), status: 'REVIEW' },
      gates: [{ gate_id: 'instrument_resolved', status: 'PASS', reason_code: 'OK' }],
      degraded_gates: [],
      missing_evidence: [],
      exclusion: null,
      primary_exclusion_reason: null,
      rank: 1,
    });
    mockOpportunities(
      makeOpportunities({
        content: makeOpportunitiesContent({ qualified: [qualified] }),
      }),
    );
    await renderOpportunities();
    expect(screen.getByTestId('opp-row-qualified-SYN-OK-01')).toBeDefined();
    expect(screen.getByTestId('opp-row-excluded-SYN-ENER-01')).toBeDefined();
    const chip = screen.getByRole('button', { name: 'INSUFFICIENT_DATA', pressed: true });
    await user.click(chip);
    await waitFor(() => {
      expect(screen.queryByTestId('opp-row-excluded-SYN-ENER-01')).toBeNull();
    });
    expect(screen.getByTestId('opp-row-qualified-SYN-OK-01')).toBeDefined();
    // Les comptes publiés ne bougent pas : le filtre est un affichage.
    expect(screen.getByTestId('opp-ideas-excluded').textContent).toContain('1');
  });
});
