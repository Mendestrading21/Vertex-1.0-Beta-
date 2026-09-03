/**
 * Page Opportunités — invariants testés :
 * - un candidat exclu ne peut JAMAIS être rendu dans le groupe qualifié, même
 *   si le serveur le publiait à tort dans la liste `qualified` ;
 * - les deux groupes sont séparés dans le DOM (régions distinctes) ;
 * - chaque exclu publie sa raison, ses gates dégradées et ses preuves
 *   manquantes ;
 * - `profile_ref` montre id, version ET la distinction appliqué / non
 *   appliqué ;
 * - `calendar_ref` est affiché comme provenance des catalyseurs ;
 * - une population entièrement exclue en INSUFFICIENT_DATA est présentée
 *   comme le comportement attendu, avec l'état vide honnête du groupe
 *   qualifié — jamais comme une erreur.
 */
import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { OpportunitiesResponse } from '../../api/client.ts';
import {
  makeExcludedCandidate,
  makeOpportunities,
  makeOpportunitiesContent,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { opportunitiesFrameStateOf } from './OpportunitiesPage.tsx';
import {
  candidateOf,
  disqualifyingFacts,
  opportunitiesContentOf,
  partitionCandidates,
} from './opportunitiesView.ts';

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

function mockOpportunities(response: unknown, status = 200): void {
  fetchMock.mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes('/v1/opportunities')) {
      return jsonResponse(response, status);
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

async function renderOpportunities(): Promise<void> {
  renderApp('/opportunities');
  await screen.findByRole('heading', { level: 1, name: 'Opportunités' });
}

describe('partitionCandidates — un exclu ne peut jamais devenir qualifié', () => {
  it('sépare les deux groupes publiés', () => {
    const partition = partitionCandidates(makeOpportunitiesContent());
    expect(partition.qualified).toHaveLength(0);
    expect(partition.excluded).toHaveLength(1);
    expect(partition.contradictory).toHaveLength(0);
  });

  it('écarte du groupe qualifié tout candidat portant un fait disqualifiant', () => {
    const cases = [
      // statut fermé
      makeExcludedCandidate(),
      // statut ouvert mais gate bloquante publiée
      makeExcludedCandidate({
        advice: { ...(makeExcludedCandidate()['advice'] as object), status: 'QUALIFIED' },
      }),
      // statut ouvert, aucune gate bloquante, mais preuve requise manquante
      makeExcludedCandidate({
        advice: { ...(makeExcludedCandidate()['advice'] as object), status: 'QUALIFIED' },
        gates: [{ gate_id: 'instrument_resolved', status: 'PASS', reason_code: 'OK' }],
        exclusion: null,
        primary_exclusion_reason: null,
      }),
      // statut ouvert, aucune gate bloquante, aucune preuve manquante, mais
      // le serveur publie tout de même une exclusion
      makeExcludedCandidate({
        advice: { ...(makeExcludedCandidate()['advice'] as object), status: 'QUALIFIED' },
        gates: [{ gate_id: 'instrument_resolved', status: 'PASS', reason_code: 'OK' }],
        missing_evidence: [],
      }),
    ];
    for (const poisoned of cases) {
      const partition = partitionCandidates({ qualified: [poisoned], excluded: [] });
      expect(partition.qualified).toEqual([]);
      expect(partition.contradictory).toHaveLength(1);
      const candidate = candidateOf(poisoned);
      expect(candidate).not.toBeNull();
      expect(disqualifyingFacts(candidate!).length).toBeGreaterThan(0);
    }
  });

  it('un candidat réellement admissible reste qualifié', () => {
    const clean = makeExcludedCandidate({
      advice: { ...(makeExcludedCandidate()['advice'] as object), status: 'QUALIFIED' },
      gates: [{ gate_id: 'instrument_resolved', status: 'PASS', reason_code: 'OK' }],
      degraded_gates: [],
      missing_evidence: [],
      exclusion: null,
      primary_exclusion_reason: null,
      rank: 1,
    });
    const partition = partitionCandidates({ qualified: [clean], excluded: [] });
    expect(partition.qualified).toHaveLength(1);
    expect(partition.contradictory).toEqual([]);
  });
});

describe('opportunitiesContentOf / frame', () => {
  it('refuse un contenu illisible et relaie l’état vide du serveur', () => {
    expect(opportunitiesContentOf(null)).toBeNull();
    expect(opportunitiesContentOf({ schema_version: 'x' })).toBeNull();
    expect(opportunitiesFrameStateOf('loading', undefined).state).toBe('loading');
    expect(opportunitiesFrameStateOf('ready', undefined).state).toBe('error');
    expect(
      opportunitiesFrameStateOf('ready', makeOpportunities({ state: 'empty', content: null }))
        .state,
    ).toBe('empty');
    expect(
      opportunitiesFrameStateOf('ready', makeOpportunities({ content: { schema_version: 'x' } }))
        .state,
    ).toBe('error');
    expect(opportunitiesFrameStateOf('ready', makeOpportunities()).state).toBe('ready');
  });

  it('un verdict périmé garde son contenu, mais jamais l’état ready', () => {
    const frame = opportunitiesFrameStateOf('ready', makeOpportunities({ state: 'stale' }));
    expect(frame.state).toBe('stale');
    expect(frame.view).not.toBeNull();
  });

  it('un état hors contrat échoue fermé', () => {
    const frame = opportunitiesFrameStateOf(
      'ready',
      makeOpportunities({ state: 'inconnu' as 'ok' }),
    );
    expect(frame.state).toBe('error');
    expect(frame.view).toBeNull();
  });
});

describe('page Opportunités — rendu', () => {
  it('sépare strictement les deux groupes dans le DOM', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    const qualified = await screen.findByTestId('opp-group-qualified');
    const excluded = screen.getByTestId('opp-group-excluded');
    expect(qualified.contains(excluded)).toBe(false);
    expect(excluded.contains(qualified)).toBe(false);
    expect(within(excluded).getByTestId('opp-row-excluded-SYN-ENER-01')).toBeDefined();
    expect(within(qualified).queryByTestId('opp-row-excluded-SYN-ENER-01')).toBeNull();
    expect(within(qualified).queryByText('SYN-ENER-01')).toBeNull();
  });

  it('un candidat publié à tort comme qualifié n’apparaît jamais chez les qualifiés', async () => {
    mockOpportunities(
      makeOpportunities({
        content: makeOpportunitiesContent({
          qualified: [makeExcludedCandidate({ ticker: 'SYN-POISON-01' })],
          excluded: [],
        }),
      }),
    );
    await renderOpportunities();
    const qualified = await screen.findByTestId('opp-group-qualified');
    const excluded = screen.getByTestId('opp-group-excluded');
    expect(within(qualified).queryByText('SYN-POISON-01')).toBeNull();
    const flagged = within(excluded).getByTestId('opp-contradictory-SYN-POISON-01');
    expect(flagged.textContent).toContain('SNAPSHOT INCOHÉRENT');
    expect(flagged.textContent).toContain('gate bloquante');
  });

  it('affiche statut, direction, raison, gates dégradées, preuves manquantes et population', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    const row = await screen.findByTestId('opp-row-excluded-SYN-ENER-01');
    expect(row.textContent).toContain('INSUFFICIENT_DATA');
    expect(row.textContent).toContain('UNKNOWN');
    expect(row.textContent).toContain('entitlements_sufficient');
    expect(row.textContent).toContain('UNEVALUABLE');
    expect(row.textContent).toContain('instrument_resolved');
    expect(row.textContent).toContain('regime');
    expect(row.textContent).toContain('SYNTHETIC');
    expect(row.textContent).toContain('Statut fermé par une gate bloquante');
  });

  it('publie un état vide HONNÊTE pour le groupe qualifié (comportement attendu)', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    const empty = await screen.findByTestId('opp-empty-qualified');
    expect(empty.getAttribute('data-state')).toBe('empty');
    expect(empty.textContent).toContain('fail-closed');
    expect(empty.textContent).not.toContain('Erreur');
    // Le cadre de page n'est PAS un état d'erreur.
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('affiche profile_ref avec id, version et la distinction appliqué / non appliqué', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    expect((await screen.findByTestId('opp-profile-id')).textContent).toBe(
      'equity_etf_swing_3_12m',
    );
    expect(screen.getByTestId('opp-profile-version').textContent).toBe('1.0.0');
    const applied = screen.getByTestId('opp-profile-applied');
    const notApplied = screen.getByTestId('opp-profile-not-applied');
    expect(applied.textContent).toContain('required_evidence');
    expect(notApplied.textContent).toContain('instruments');
    expect(notApplied.textContent).toContain('no instrument-class source exists');
    expect(applied.contains(notApplied)).toBe(false);
  });

  it('affiche calendar_ref comme provenance des catalyseurs', async () => {
    mockOpportunities(makeOpportunities());
    await renderOpportunities();
    const reference = await screen.findByTestId('opp-calendar-ref');
    expect(reference.getAttribute('data-status')).toBe('USED');
    expect(screen.getByTestId('opp-calref-status').textContent).toBe('USED');
    expect(screen.getByTestId('opp-calref-version').textContent).toBe('21');
    expect(reference.textContent).toContain('calendar/global');
    expect(reference.textContent).toContain('vertex.calendar/1.0');
  });

  it('affiche l’âge PUBLIÉ par le serveur, et le bandeau périmé le cas échéant', async () => {
    mockOpportunities(makeOpportunities({ age_seconds: 3600 }));
    await renderOpportunities();
    expect((await screen.findByTestId('opp-provenance')).textContent).toContain('il y a 1 h');

    fetchMock.mockReset();
    mockOpportunities(makeOpportunities({ state: 'stale', reason: 'past freshness budget' }));
    renderApp('/opportunities');
    await screen.findAllByRole('heading', { level: 1, name: 'Opportunités' });
    await waitFor(() => {
      expect(document.querySelector('[data-state="stale"]')).not.toBeNull();
    });
    expect(document.querySelector('[data-state="stale"]')?.textContent).toContain(
      'past freshness budget',
    );
  });

  it('affiche la répartition des raisons d’exclusion en tableau', async () => {
    mockOpportunities(
      makeOpportunities({
        content: makeOpportunitiesContent({
          exclusion_reasons: { 'entitlements_sufficient:UNEVALUABLE': 24 },
          coverage: {
            universe_size: 24,
            qualified_count: 0,
            excluded_count: 24,
            status_counts: { INSUFFICIENT_DATA: 24 },
            population_counts: { SYNTHETIC: 4, EMPTY: 20 },
            observations_considered: 4,
            lookback_seconds: 259200,
          },
        }),
      }),
    );
    await renderOpportunities();
    const reasons = await screen.findByTestId('opp-exclusion-reasons');
    const row = within(reasons).getByTestId('opp-reason-entitlements_sufficient:UNEVALUABLE');
    expect(within(row).getByRole('cell').textContent).toBe('24');
    // LOT-A4 : les statuts sur l'univers vivent dans leur propre module, en
    // barres de dénombrement — le compte publié reste lisible tel quel.
    const statusRow = screen.getByTestId('opp-status-count-INSUFFICIENT_DATA');
    expect(within(statusRow).getByText('24')).toBeDefined();
  });
});

describe('état clock_inconsistent', () => {
  const base = {
    state: 'clock_inconsistent',
    content: null,
    as_of: null,
    age_seconds: null,
    snapshot_version: null,
  } as unknown as OpportunitiesResponse;

  it('reste fermé : aucun contenu n’est rendu', () => {
    const frame = opportunitiesFrameStateOf('ready', base);
    expect(frame.state).toBe('error');
    expect(frame.view).toBeNull();
  });

  it('affiche la cause PUBLIÉE par le serveur, pas un message générique', () => {
    const reason =
      'clock inconsistent: snapshot as_of is 42 s ahead of the relay clock (tolerance 5 s)';
    const frame = opportunitiesFrameStateOf('ready', {
      ...base,
      reason,
    } as unknown as OpportunitiesResponse);
    expect(frame.detail).toBe(reason);
  });

  it('n’invente aucune cause pour un état hors contrat inconnu', () => {
    const frame = opportunitiesFrameStateOf('ready', {
      ...base,
      state: 'un_etat_que_le_client_ne_connait_pas',
      reason: 'peu importe',
    } as unknown as OpportunitiesResponse);
    expect(frame.state).toBe('error');
    expect(frame.detail).toBeUndefined();
  });
});
