/**
 * Page Suivi — file due dans l'ordre SERVEUR, badge « nouvelle information »
 * avec raison et provenance, fiche thèse (invalidation visible, historique
 * append-only honnête), formulaire de thèse (invalidation obligatoire,
 * idempotency_key client réutilisée sur retry, 200 created=false silencieux)
 * et populations JAMAIS additionnées.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { makeFollowUpQueue, makeQueueContent } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { queueFrameStateOf } from './FollowUpPage.tsx';
import { buildRevisionRequest } from './ThesisSheet.tsx';
import { queueContentOf } from './followUpView.ts';

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
  readonly queue?: () => Response;
  readonly thesis?: (body: unknown) => Response;
  readonly revision?: (body: unknown) => Response;
}): void {
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    const body = typeof init?.body === 'string' ? (JSON.parse(init.body) as unknown) : undefined;
    if (method === 'POST' && /\/v1\/theses\/\d+\/revisions$/.test(url)) {
      return handlers.revision?.(body) ?? jsonResponse({}, 500);
    }
    if (method === 'POST' && url.endsWith('/v1/theses')) {
      return handlers.thesis?.(body) ?? jsonResponse({}, 500);
    }
    if (method === 'GET' && url.endsWith('/v1/follow-up/queue')) {
      return handlers.queue?.() ?? jsonResponse(makeFollowUpQueue());
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

async function renderFollowUp(): Promise<void> {
  renderApp('/follow-up');
  await screen.findByRole('heading', { level: 1, name: 'Suivi' });
}

describe('queueFrameStateOf', () => {
  it('relaie les états requête, empty serveur et contenu illisible', () => {
    expect(queueFrameStateOf('loading', undefined).state).toBe('loading');
    expect(queueFrameStateOf('ready', undefined).state).toBe('error');
    expect(
      queueFrameStateOf(
        'ready',
        makeFollowUpQueue({ state: 'empty', content: null, reason: 'never_published' }),
      ).state,
    ).toBe('empty');
    expect(
      queueFrameStateOf('ready', makeFollowUpQueue({ content: { schema_version: 'x/1' } })).state,
    ).toBe('error');
    expect(queueFrameStateOf('ready', makeFollowUpQueue()).state).toBe('ready');
  });

  it('un instantané périmé garde son contenu VISIBLE sous le bandeau', () => {
    // Ce qui était interdit, c'est de servir une file de trois jours sans
    // dire son âge — pas de la servir. `stale` porte la date, le contenu
    // reste lisible.
    const frame = queueFrameStateOf(
      'ready',
      makeFollowUpQueue({ state: 'stale', age_seconds: 90_000, reason: 'snapshot older…' }),
    );
    expect(frame.state).toBe('stale');
    expect(frame.view).not.toBeNull();
  });
});

describe('followUpView — lecture verbatim', () => {
  it('deux populations distinctes, jamais fusionnées', () => {
    const view = queueContentOf(makeQueueContent());
    expect(view).not.toBeNull();
    expect(view!.populationTheses).toBe('USER_DECLARED');
    expect(view!.populationInformation).toBe('SYNTHETIC');
  });

  it('due et theses relayés avec urgence et raisons serveur', () => {
    const view = queueContentOf(makeQueueContent())!;
    expect(view.due).toHaveLength(1);
    expect(view.due[0]!.rank).toBe(1);
    expect(view.due[0]!.hasNewInformation).toBe(true);
    expect(view.due[0]!.urgencyReasons[0]!.code).toBe('NEW_INFORMATION_SINCE_LAST_REVIEW');
    expect(view.theses).toHaveLength(2);
  });
});

describe('buildRevisionRequest — contraintes du contrat', () => {
  const base = { idempotencyKey: 'k-1', note: '', snoozeUntilLocal: '' };

  it('SNOOZED exige une date ; les autres actions ne portent jamais snooze_until', () => {
    expect(buildRevisionRequest({ kind: 'SNOOZED', ...base })).toBeNull();
    const snoozed = buildRevisionRequest({ kind: 'SNOOZED', ...base, snoozeUntilLocal: '2026-09-01T10:00' });
    expect(snoozed).not.toBeNull();
    expect(snoozed!.snooze_until!.endsWith('Z')).toBe(true);
    const reviewed = buildRevisionRequest({ kind: 'REVIEWED', ...base });
    expect(reviewed!.snooze_until).toBeNull();
    expect(reviewed!.idempotency_key).toBe('k-1');
  });

  it('NOTE_UPDATED exige une note non vide', () => {
    expect(buildRevisionRequest({ kind: 'NOTE_UPDATED', ...base })).toBeNull();
    expect(buildRevisionRequest({ kind: 'NOTE_UPDATED', ...base, note: 'n' })).not.toBeNull();
  });
});

describe('Page Suivi — état nominal', () => {
  it('populations séparées affichées, file due ordonnée par le serveur, badge nouvelle information', async () => {
    mockRoutes({});
    await renderFollowUp();

    const populations = await screen.findByTestId('fu-populations');
    expect(within(populations).getByText('USER_DECLARED')).toBeDefined();
    expect(within(populations).getByText('SYNTHETIC')).toBeDefined();

    const due = screen.getByTestId('fu-due-list');
    expect(within(due).getAllByRole('listitem')).toHaveLength(1);
    expect(screen.getByTestId('fu-new-info-1')).toBeDefined();
    expect(within(due).getByText('NEW_INFORMATION_SINCE_LAST_REVIEW')).toBeDefined();

    // Ordre du serveur affiché tel quel (jamais retrié localement).
    expect(screen.getByText(/effective_review_due_at asc/)).toBeDefined();
  });

  it('fiche thèse : invalidation, état projeté, historique append-only honnête', async () => {
    mockRoutes({});
    await renderFollowUp();
    const user = userEvent.setup();

    await user.click(within(await screen.findByTestId('fu-due-list')).getByRole('button'));
    const sheet = await screen.findByTestId('thesis-sheet');
    expect(within(sheet).getByTestId('thesis-invalidation').textContent).toContain(
      'Invalidée si la clôture synthétique retombe sous 90.',
    );
    expect(within(sheet).getByText('ACTIVE')).toBeDefined();
    // Historique honnête : pas de timeline inventée.
    expect(within(sheet).getByText(/NON DISPONIBLE/)).toBeDefined();
    // Provenance du contexte d'information.
    expect(within(sheet).getByText(/synthetic-dev/)).toBeDefined();
  });

  it('revue : POST révision avec idempotency_key client ; created=false traité en succès silencieux', async () => {
    const revisionBodies: unknown[] = [];
    mockRoutes({
      revision: (body) => {
        revisionBodies.push(body);
        return jsonResponse(
          { thesis_id: 1, revision_id: 5, created: false, refresh_enqueued: false },
          200,
        );
      },
    });
    await renderFollowUp();
    const user = userEvent.setup();

    await user.click(within(await screen.findByTestId('fu-due-list')).getByRole('button'));
    const sheet = await screen.findByTestId('thesis-sheet');
    await user.click(within(sheet).getByRole('button', { name: 'Revue faite' }));
    await user.click(within(sheet).getByRole('button', { name: 'Enregistrer la révision' }));

    await screen.findByText(/Révision « Revue faite » enregistrée/);
    expect(revisionBodies).toHaveLength(1);
    const sent = revisionBodies[0] as Record<string, unknown>;
    expect(sent['action']).toBe('REVIEWED');
    expect(typeof sent['idempotency_key']).toBe('string');
    expect((sent['idempotency_key'] as string).length).toBeGreaterThan(0);
    // Aucun message d'erreur pour le rejeu idempotent.
    expect(screen.queryByText(/refusée/)).toBeNull();
  });

  it('revue en échec réseau : « Réessayer » renvoie la MÊME clé de rejeu', async () => {
    const keys: string[] = [];
    let failFirst = true;
    mockRoutes({
      revision: (body) => {
        keys.push((body as Record<string, unknown>)['idempotency_key'] as string);
        if (failFirst) {
          failFirst = false;
          throw new TypeError('network down');
        }
        return jsonResponse(
          { thesis_id: 1, revision_id: 6, created: true, refresh_enqueued: true },
          201,
        );
      },
    });
    await renderFollowUp();
    const user = userEvent.setup();

    await user.click(within(await screen.findByTestId('fu-due-list')).getByRole('button'));
    const sheet = await screen.findByTestId('thesis-sheet');
    await user.click(within(sheet).getByRole('button', { name: 'Revue faite' }));
    await user.click(within(sheet).getByRole('button', { name: 'Enregistrer la révision' }));
    await screen.findByText(/la révision n'est peut-être pas enregistrée/);

    await user.click(within(sheet).getByRole('button', { name: 'Réessayer (même clé de rejeu)' }));
    await screen.findByText(/Révision « Revue faite » enregistrée/);

    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });
});

describe('Formulaire de thèse', () => {
  it('invalidation obligatoire : rien n’est envoyé sans elle', async () => {
    mockRoutes({});
    await renderFollowUp();
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText('Titre'), 'Ma thèse');
    await user.type(screen.getByLabelText(/Hypothèses/), 'Parce que.');
    const postsBefore = fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST').length;
    await user.click(screen.getByRole('button', { name: 'Enregistrer la thèse' }));
    await screen.findByText('invalidation obligatoire — dire ce qui prouverait la thèse fausse');
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(postsBefore);
  });

  it('création : POST avec idempotency_key générée côté client', async () => {
    const bodies: unknown[] = [];
    mockRoutes({
      thesis: (body) => {
        bodies.push(body);
        return jsonResponse(
          { thesis_id: 9, revision_id: 12, created: true, refresh_enqueued: true },
          201,
        );
      },
    });
    await renderFollowUp();
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText('Titre'), 'Ma thèse');
    await user.type(screen.getByLabelText(/Hypothèses/), 'Parce que.');
    await user.type(screen.getByLabelText(/Invalidation \(OBLIGATOIRE/), 'Si X arrive.');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la thèse' }));

    await screen.findByTestId('thesis-form-created');
    const sent = bodies[0] as Record<string, unknown>;
    expect(sent['invalidation']).toBe('Si X arrive.');
    expect(typeof sent['idempotency_key']).toBe('string');
  });
});

describe('Page Suivi — file vide et hors ligne', () => {
  it('empty serveur : raison affichée, formulaire de thèse disponible', async () => {
    mockRoutes({
      queue: () =>
        jsonResponse(
          makeFollowUpQueue({ state: 'empty', content: null, reason: 'never_published' }),
        ),
    });
    await renderFollowUp();
    await screen.findByText(/raison serveur : never_published/);
    expect(screen.getByRole('heading', { name: 'Nouvelle thèse' })).toBeDefined();
  });

  it('réseau coupé → offline honnête', async () => {
    fetchMock.mockRejectedValue(new TypeError('network down'));
    await renderFollowUp();
    await waitFor(() => {
      expect(document.querySelector('[data-state="offline"]')).not.toBeNull();
    });
    expect(screen.queryByTestId('fu-due-list')).toBeNull();
  });
});
