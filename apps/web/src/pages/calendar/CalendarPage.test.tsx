/**
 * Page Calendrier — invariants testés :
 * - « Estimé » et « Confirmé » ne partagent JAMAIS le même libellé ;
 * - un événement révisé rend ses valeurs ANTÉRIEURES lisibles (statut ET
 *   instant), sans effacement ;
 * - un agenda vidé par un refus de droit affiche le droit manquant et sa
 *   raison, jamais une liste vide banale ;
 * - les quatre refus typés de fenêtre sont affichés en clair ;
 * - les compteurs de la liste servie et les totaux du snapshot restent
 *   distincts et étiquetés.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeCalendarResponse,
  makeEstimatedCalendarEvent,
  makeNotEntitledCalendarResponse,
  makeRevisedCalendarEvent,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { calendarFrameOf, windowErrorOf, WINDOW_ERROR_LABELS } from './CalendarPage.tsx';
import {
  CONFIRMED_STATUS_LABEL,
  ESTIMATED_STATUS_LABEL,
  calendarEventOf,
  calendarEventsOf,
  formatInTimeZone,
  groupAgenda,
  groupKeyOf,
  statusLabelOf,
} from './calendarView.ts';
import { ApiError } from '../../api/client.ts';

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

function mockCalendar(handler: (url: string) => Response): void {
  fetchMock.mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes('/v1/calendar')) {
      return handler(url);
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

async function renderCalendar(path = '/calendar'): Promise<void> {
  renderApp(path);
  await screen.findByRole('heading', { level: 1, name: 'Calendrier' });
}

describe('calendarView — lecture verbatim', () => {
  it('refuse un événement sans identité, catégorie, statut ou instant UTC', () => {
    expect(calendarEventOf(null)).toBeNull();
    expect(calendarEventOf({ event_id: 'x' })).toBeNull();
    expect(calendarEventsOf([{ event_id: 'x' }, makeEstimatedCalendarEvent()])).toHaveLength(1);
  });

  it('les deux statuts canoniques ont des libellés STRICTEMENT distincts', () => {
    expect(ESTIMATED_STATUS_LABEL).not.toBe(CONFIRMED_STATUS_LABEL);
    expect(statusLabelOf('ESTIMATED')).toBe(ESTIMATED_STATUS_LABEL);
    expect(statusLabelOf('CONFIRMED')).toBe(CONFIRMED_STATUS_LABEL);
    // Statut hors contrat : relayé tel quel, jamais assimilé à l'un des deux.
    expect(statusLabelOf('AUTRE')).toBe('AUTRE');
  });

  it('regroupe sur l’instant UTC publié, jour ou semaine ISO', () => {
    expect(groupKeyOf('2026-09-06T15:30:00+00:00', 'day')).toBe('2026-09-06');
    // 2026-09-06 est un dimanche : la semaine ISO commence le lundi 31 août.
    expect(groupKeyOf('2026-09-06T15:30:00+00:00', 'week')).toBe('2026-08-31');
    const events = calendarEventsOf([makeRevisedCalendarEvent(), makeEstimatedCalendarEvent()]);
    expect(groupAgenda(events, 'day')).toHaveLength(1);
  });

  it('rend un instant dans un fuseau EXPLICITE, ou rien s’il est invalide', () => {
    expect(formatInTimeZone('2026-09-06T15:30:00+00:00', 'UTC')).toContain('2026-09-06');
    expect(formatInTimeZone('pas-une-date', 'UTC')).toBeNull();
    expect(formatInTimeZone('2026-09-06T15:30:00+00:00', 'Pas/Un/Fuseau')).toBeNull();
  });
});

describe('calendarFrameOf — états honnêtes', () => {
  it('relaie les états de requête et distingue empty, not_entitled et rejected', () => {
    expect(calendarFrameOf('loading', undefined)).toEqual({ kind: 'state', state: 'loading' });
    expect(calendarFrameOf('ready', undefined)).toEqual({ kind: 'state', state: 'error' });
    const empty = calendarFrameOf('ready', makeCalendarResponse({ state: 'empty', reason: 'rien' }));
    expect(empty).toMatchObject({ kind: 'state', state: 'empty', detail: 'rien' });
    expect(calendarFrameOf('ready', makeNotEntitledCalendarResponse()).kind).toBe('blocked');
    expect(calendarFrameOf('ready', makeCalendarResponse({ state: 'rejected' })).kind).toBe('blocked');
    expect(calendarFrameOf('ready', makeCalendarResponse()).kind).toBe('ok');
  });
});

describe('calendarFrameOf — états ajoutés par le contrat', () => {
  it('empty_window dit que c’est la FENÊTRE qui ne sélectionne rien', () => {
    const frame = calendarFrameOf(
      'ready',
      makeCalendarResponse({ state: 'empty_window', agenda: [], reason: 'window selects none' }),
    );
    expect(frame.kind).toBe('state');
    expect(frame).toMatchObject({ state: 'empty' });
    expect((frame as { detail: string }).detail).toContain('Fenêtre demandée');
    expect((frame as { detail: string }).detail).toContain('window selects none');
  });

  it('stale et degraded conservent l’agenda SOUS un bandeau, jamais ready', () => {
    const stale = calendarFrameOf(
      'ready',
      makeCalendarResponse({ state: 'stale', reason: 'every displayed event is stale' }),
    );
    expect(stale).toMatchObject({ kind: 'ok', state: 'stale' });
    expect((stale as { detail: string }).detail).toContain('every displayed event is stale');
    const degraded = calendarFrameOf(
      'ready',
      makeCalendarResponse({ state: 'degraded', reason: 'state field missing' }),
    );
    expect(degraded).toMatchObject({ kind: 'ok', state: 'partial' });
  });

  it('un état hors contrat échoue fermé, jamais rendu comme un succès', () => {
    const frame = calendarFrameOf(
      'ready',
      makeCalendarResponse({ state: 'inconnu' as 'ok' }),
    );
    expect(frame).toMatchObject({ kind: 'state', state: 'error' });
  });
});

describe('windowErrorOf — refus typés relayés, jamais inventés', () => {
  it('extrait le code du 422 et ignore tout autre échec', () => {
    const error = new ApiError('HTTP', 'x', 422, {
      detail: { code: 'WINDOW_TOO_LARGE', message: 'bounded to 90 days' },
    });
    expect(windowErrorOf(error)).toEqual({
      code: 'WINDOW_TOO_LARGE',
      message: 'bounded to 90 days',
    });
    expect(windowErrorOf(new ApiError('NETWORK', 'x'))).toBeNull();
    expect(windowErrorOf(new ApiError('HTTP', 'x', 422, { detail: {} }))).toBeNull();
    expect(windowErrorOf(new Error('x'))).toBeNull();
  });

  it('les quatre codes du contrat ont un libellé français', () => {
    for (const code of [
      'WINDOW_INCOMPLETE',
      'WINDOW_NAIVE_DATETIME',
      'WINDOW_INVERTED',
      'WINDOW_TOO_LARGE',
    ]) {
      expect(WINDOW_ERROR_LABELS[code]).toBeTruthy();
    }
  });
});

/**
 * LOT P6a — OUVRE L'INSPECTEUR D'UN ÉVÉNEMENT.
 *
 * La ligne d'agenda écrivait DEUX FOIS ce que l'inspecteur portait déjà :
 * description du statut, état de version détaillé, archive des révisions,
 * contexte croisé. La ligne les a rendus ; ces assertions sont donc
 * RELOCALISÉES, pas retirées — chacune exige toujours le même fait, à
 * l'endroit qui en est désormais le propriétaire unique.
 */
async function ouvrirInspecteur(user: ReturnType<typeof userEvent.setup>, eventId: string) {
  // Par l'IDENTIFIANT de l'événement, pas par son titre : deux fixtures
  // partagent le même titre, et viser le titre ouvrirait la mauvaise ligne
  // sans que le test s'en aperçoive.
  const ligne = await screen.findByTestId(`cal-event-${eventId}`);
  await user.click(within(ligne).getByRole('button', { name: /^Inspecter/ }));
  return screen.findByTestId('cal-event-facts');
}

const ID_ENER = 'syn-ev-earnings-SYN-ENER-01';
const ID_FINL = 'syn-ev-earnings-SYN-FINL-01';

describe('page Calendrier — rendu', () => {
  it('estimé et confirmé ne partagent jamais le même libellé à l’écran', async () => {
    mockCalendar(() => jsonResponse(makeCalendarResponse()));
    await renderCalendar();
    const confirmed = await screen.findByTestId('cal-event-syn-ev-earnings-SYN-ENER-01');
    const estimated = screen.getByTestId('cal-event-syn-ev-earnings-SYN-FINL-01');
    expect(confirmed.getAttribute('data-status')).toBe('CONFIRMED');
    expect(estimated.getAttribute('data-status')).toBe('ESTIMATED');
    // Le badge d'en-tête porte UN seul libellé, propre au statut courant.
    const confirmedHead = screen.getByTestId('cal-head-syn-ev-earnings-SYN-ENER-01');
    expect(within(confirmedHead).getByText(CONFIRMED_STATUS_LABEL)).toBeDefined();
    expect(within(confirmedHead).queryByText(ESTIMATED_STATUS_LABEL)).toBeNull();
    const estimatedHead = screen.getByTestId('cal-head-syn-ev-earnings-SYN-FINL-01');
    expect(within(estimatedHead).getByText(ESTIMATED_STATUS_LABEL)).toBeDefined();
    expect(within(estimatedHead).queryByText(CONFIRMED_STATUS_LABEL)).toBeNull();
    // LA PHRASE DE STATUT A DÉMÉNAGÉ DANS L'INSPECTEUR (lot P6a), et l'exigence
    // est INCHANGÉE : les deux statuts ne peuvent pas se lire pareil. Elle est
    // vérifiée là où elle vit maintenant, sur les DEUX événements.
    const user = userEvent.setup();
    await ouvrirInspecteur(user, ID_ENER);
    const panneauConfirme = await screen.findByTestId('cal-event-status-note');
    expect(panneauConfirme.textContent).toContain('Statut de la date : Confirmé');
    expect(panneauConfirme.textContent).not.toContain('Statut de la date : Estimé');

    await ouvrirInspecteur(user, ID_FINL);
    const panneauEstime = await screen.findByTestId('cal-event-status-note');
    expect(panneauEstime.textContent).toContain('Statut de la date : Estimé');
    expect(panneauEstime.textContent).not.toContain('Statut de la date : Confirmé');
  });

  it('un événement révisé garde ses valeurs antérieures LISIBLES', async () => {
    mockCalendar(() => jsonResponse(makeCalendarResponse()));
    await renderCalendar();
    const user = userEvent.setup();
    await ouvrirInspecteur(user, ID_ENER);
    const details = await screen.findByTestId('cal-revision-syn-ev-earnings-SYN-ENER-01');
    // Le détail est dépliable ; son contenu existe dans le DOM et reste lisible.
    const previousStatus = within(details).getByTestId(
      'cal-previous-status-syn-ev-earnings-SYN-ENER-01',
    );
    expect(within(previousStatus).getByText(ESTIMATED_STATUS_LABEL)).toBeDefined();
    const previousTime = within(details).getByTestId(
      'cal-previous-time-syn-ev-earnings-SYN-ENER-01',
    );
    expect(previousTime.textContent).toContain('2026-09-05T15:30:00+00:00');
    // La révision DÉCLARÉE par la source conserve elle aussi son antériorité.
    expect(
      within(details).getByTestId('cal-declared-previous-time-syn-ev-earnings-SYN-ENER-01')
        .textContent,
    ).toContain('2026-09-05T15:30:00+00:00');
    // L'événement affiché garde sa valeur COURANTE distincte de l'antérieure.
    expect(
      screen.getByTestId('cal-times-syn-ev-earnings-SYN-ENER-01').textContent,
    ).toContain('2026-09-06T15:30:00+00:00');
  });

  it('affiche les trois lectures du temps sans conversion implicite', async () => {
    mockCalendar(() => jsonResponse(makeCalendarResponse()));
    await renderCalendar();
    const times = await screen.findByTestId('cal-times-syn-ev-earnings-SYN-ENER-01');
    expect(times.textContent).toContain('2026-09-06T15:30:00+00:00');
    expect(times.textContent).toContain('2026-09-06T17:30:00+02:00');
    expect(times.textContent).toContain('Europe/Zurich');
    expect(times.textContent).toContain('Votre fuseau');
  });

  it('affiche le rang, le code et la VERSION de la règle d’importance', async () => {
    mockCalendar(() => jsonResponse(makeCalendarResponse()));
    await renderCalendar();
    const importance = await screen.findByTestId('cal-importance-syn-ev-earnings-SYN-ENER-01');
    expect(importance.textContent).toContain('rang 2');
    expect(importance.textContent).toContain('EARNINGS_POSITION_OR_THESIS');
    expect(importance.textContent).toContain('importance_rule/1.1');
    expect(screen.getByTestId('cal-importance-rule').textContent).toContain('importance_rule/1.1');
  });

  it('montre le contexte croisé (position, thèse, liens) publié', async () => {
    mockCalendar(() => jsonResponse(makeCalendarResponse()));
    await renderCalendar();
    const user = userEvent.setup();
    await ouvrirInspecteur(user, ID_ENER);
    const context = await screen.findByTestId('cal-context-syn-ev-earnings-SYN-ENER-01');
    expect(context.textContent).toContain('#1');
    expect(context.textContent).toContain('[SYNTHETIC] These due');
    expect(within(context).getByRole('link', { name: 'ouvrir l’analyse' })).toBeDefined();
    expect(within(context).getByRole('link', { name: 'ouvrir les options' })).toBeDefined();
  });

  it('un agenda vide par manque de droit affiche le droit manquant et sa raison', async () => {
    mockCalendar(() => jsonResponse(makeNotEntitledCalendarResponse()));
    await renderCalendar();
    const blocked = await screen.findByTestId('cal-blocked');
    expect(blocked.getAttribute('data-state')).toBe('not_entitled');
    expect(blocked.textContent).toContain('DROIT MANQUANT');
    expect(blocked.textContent).toContain('rights_not_usable');
    expect(screen.getByTestId('cal-blocked-reason').textContent).toContain(
      'every considered record was rejected: rights not usable',
    );
    expect(screen.getByTestId('cal-rejected-rights_not_usable').textContent).toContain('4');
    // Aucune liste vide banale : l'agenda n'est pas rendu du tout.
    expect(screen.queryByTestId('cal-agenda')).toBeNull();
    expect(screen.queryByTestId('cal-agenda-empty')).toBeNull();
  });

  it('distingue les compteurs de la liste servie et les totaux du snapshot', async () => {
    mockCalendar(() =>
      jsonResponse(
        makeCalendarResponse({
          categories: { EARNINGS: 4, MACRO: 3 },
          statuses: { CONFIRMED: 5, ESTIMATED: 2 },
          window: {
            applied: true,
            from_utc: '2026-09-01T00:00:00Z',
            to_utc: '2026-09-30T00:00:00Z',
            max_days: 90,
            events_total: 7,
            events_in_window: 2,
            categories: { EARNINGS: 2 },
            statuses: { CONFIRMED: 1, ESTIMATED: 1 },
          },
        }),
      ),
    );
    await renderCalendar('/calendar?from=2026-09-01T00:00:00Z&to=2026-09-30T00:00:00Z');
    const counters = await screen.findByTestId('cal-counters');
    expect(counters.textContent).toContain('Liste servie');
    expect(counters.textContent).toContain('Total du snapshot');
    expect(screen.getByTestId('cal-count-served').textContent).toBe('2');
    expect(screen.getByTestId('cal-count-total').textContent).toBe('7');
    const earnings = screen.getByTestId('cal-counter-category-EARNINGS');
    const cells = within(earnings).getAllByRole('cell');
    expect(cells[0]?.textContent).toBe('2');
    expect(cells[1]?.textContent).toBe('4');
    const macro = screen.getByTestId('cal-counter-category-MACRO');
    const macroCells = within(macro).getAllByRole('cell');
    expect(macroCells[0]?.textContent).toBe('0');
    expect(macroCells[1]?.textContent).toBe('3');
  });

  it('affiche en clair le refus typé de fenêtre renvoyé par le serveur', async () => {
    mockCalendar(() =>
      jsonResponse({ detail: { code: 'WINDOW_TOO_LARGE', message: 'bounded to 90 days' } }, 422),
    );
    await renderCalendar('/calendar?from=2026-01-01T00:00:00Z&to=2027-01-01T00:00:00Z');
    const error = await screen.findByTestId('cal-window-error');
    expect(error.textContent).toContain('WINDOW_TOO_LARGE');
    expect(error.textContent).toContain(WINDOW_ERROR_LABELS['WINDOW_TOO_LARGE']);
    expect(error.textContent).toContain('bounded to 90 days');
  });

  it('persiste le filtre de catégorie dans l’URL et filtre la liste servie', async () => {
    mockCalendar(() => jsonResponse(makeCalendarResponse()));
    const { router } = renderApp('/calendar');
    await screen.findByRole('heading', { level: 1, name: 'Calendrier' });
    await screen.findByTestId('cal-agenda');
    const user = userEvent.setup();
    await user.selectOptions(screen.getByRole('combobox', { name: 'Statut de date' }), 'ESTIMATED');
    await waitFor(() => {
      expect(router.state.location.search).toContain('status=ESTIMATED');
    });
    expect(screen.queryByTestId('cal-event-syn-ev-earnings-SYN-ENER-01')).toBeNull();
    expect(screen.getByTestId('cal-event-syn-ev-earnings-SYN-FINL-01')).toBeDefined();
    expect(screen.getByTestId('cal-filter-count').textContent).toContain('1 événement affiché');
  });

  it('publie l’état de version et les révisions refusées quand le worker les donne', async () => {
    mockCalendar(() =>
      jsonResponse(
        makeCalendarResponse({
          agenda: [
            makeRevisedCalendarEvent({
              version_state: 'CONFLICTING_VERSIONS',
              conflicting_versions: [
                {
                  source_event_id: 'synthetic-dev:1236:ev0000',
                  source: 'synthetic-dev',
                  as_of: '2026-08-28T19:01:59+00:00',
                  status: 'ESTIMATED',
                  event_time_utc: '2026-09-04T15:30:00+00:00',
                },
              ],
              rejected_revisions: [
                {
                  reason: 'revision_in_the_future',
                  revision: { revised_at: '2099-01-01T00:00:00+00:00' },
                },
              ],
            }),
          ],
        }),
      ),
    );
    await renderCalendar();
    // LE CONFLIT SE VOIT SANS OUVRIR QUOI QUE CE SOIT — exception assumée du
    // lot P6a : un lecteur qui parcourt la liste doit savoir que cet événement
    // porte des versions contradictoires. Le DÉTAIL, lui, est dans le panneau.
    expect(
      (await screen.findByTestId('cal-conflict-flag-syn-ev-earnings-SYN-ENER-01')).textContent,
    ).toContain('CONFLICTING_VERSIONS');
    const user = userEvent.setup();
    await ouvrirInspecteur(user, ID_ENER);
    const version = await screen.findByTestId('cal-version-syn-ev-earnings-SYN-ENER-01');
    expect(version.textContent).toContain('CONFLICTING_VERSIONS');
    expect(version.textContent).toContain('2026-09-04T15:30:00+00:00');
    expect(
      screen.getByTestId('cal-rejected-revisions-syn-ev-earnings-SYN-ENER-01').textContent,
    ).toContain('revision_in_the_future');
  });

  it('n’invente aucun état de version quand le snapshot n’en publie pas', async () => {
    mockCalendar(() =>
      jsonResponse(
        makeCalendarResponse({
          agenda: [makeEstimatedCalendarEvent({ version_state: null })],
        }),
      ),
    );
    await renderCalendar();
    await screen.findByTestId('cal-agenda');
    // Ni dans la liste — aucun drapeau de conflit…
    expect(screen.queryByTestId('cal-conflict-flag-syn-ev-earnings-SYN-FINL-01')).toBeNull();
    // …ni dans le panneau, où le bloc vit désormais.
    const user = userEvent.setup();
    await ouvrirInspecteur(user, ID_FINL);
    expect(screen.queryByTestId('cal-version-syn-ev-earnings-SYN-FINL-01')).toBeNull();
  });

  it('un agenda périmé reste affiché SOUS le bandeau « Données périmées »', async () => {
    mockCalendar(() =>
      jsonResponse(
        makeCalendarResponse({ state: 'stale', reason: 'every displayed event is stale' }),
      ),
    );
    await renderCalendar();
    await screen.findByTestId('cal-agenda');
    const boundary = document.querySelector('[data-state="stale"]');
    expect(boundary).not.toBeNull();
    expect(boundary?.textContent).toContain('Données périmées');
    expect(boundary?.textContent).toContain('every displayed event is stale');
  });

  it('bascule le regroupement jour ↔ semaine', async () => {
    mockCalendar(() => jsonResponse(makeCalendarResponse()));
    await renderCalendar();
    await screen.findByTestId('cal-agenda');
    const user = userEvent.setup();
    await user.selectOptions(screen.getByRole('combobox', { name: 'Regroupement' }), 'week');
    await waitFor(() => {
      expect(screen.getByTestId('cal-agenda').getAttribute('data-grouping')).toBe('week');
    });
  });
});
