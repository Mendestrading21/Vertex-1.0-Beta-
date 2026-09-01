/**
 * Page Catalyseurs — création (LOT-10).
 *
 * Ce que ces tests protègent, dans l'ordre d'importance :
 *
 * 1. la SÉLECTION est un filtre, jamais une invention : seul un événement que
 *    le snapshot relie lui-même à une thèse ou à une position est un
 *    catalyseur, et les autres sont comptés, pas masqués ;
 * 2. la page ne crée AUCUNE donnée en croisant deux snapshots — une thèse
 *    citée par un événement mais absente de la file de revue est dite absente,
 *    jamais complétée ;
 * 3. les deux snapshots restent INDÉPENDANTS : une file manquante ne fait pas
 *    disparaître la timeline, et réciproquement ;
 * 4. les états dégradés du serveur (`empty`, `not_entitled`, `stale`) sont
 *    relayés sans qu'aucun contenu ne soit reconstruit.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeCalendarEvent,
  makeCalendarResponse,
  makeFollowUpQueue,
  makeNotEntitledCalendarResponse,
  makeQueueContent,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { calendarEventsOf } from '../calendar/calendarView.ts';
import { catalystFrameStateOf } from './CatalystsPage.tsx';
import { selectCatalysts, selectedCatalystOf } from './catalystsView.ts';
import { queueContentOf } from './review/followUpView.ts';

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

function mockRoutes(
  handlers: { readonly calendar?: () => Response; readonly queue?: () => Response } = {},
): void {
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (method === 'GET' && url.includes('/v1/calendar')) {
      return handlers.calendar?.() ?? jsonResponse(makeCalendarResponse());
    }
    if (method === 'GET' && url.endsWith('/v1/follow-up/queue')) {
      return handlers.queue?.() ?? jsonResponse(makeFollowUpQueue());
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

async function renderCatalysts(): Promise<void> {
  renderApp('/catalysts');
  await screen.findByRole('heading', { level: 1, name: 'Catalyseurs' });
}

/** Un événement relié à la thèse `thesisId`, sinon identique au synthétique. */
function linkedEvent(eventId: string, thesisId: number, title: string): Record<string, unknown> {
  return makeCalendarEvent({
    event_id: eventId,
    event_context: {
      positions: [],
      theses: [{ thesis_id: thesisId, title, status: 'ACTIVE' }],
      links: [],
    },
  });
}

describe('selectCatalysts — filtre et appariement, jamais un calcul', () => {
  it('ne retient QUE les événements que le snapshot relie lui-même', () => {
    const events = calendarEventsOf([
      makeCalendarEvent({ event_id: 'ev-libre' }),
      linkedEvent('ev-these', 7, 'Thèse SYN-TECH-01'),
      makeCalendarEvent({
        event_id: 'ev-position',
        // Une position est publiée comme un OBJET portant `portfolio_id`,
        // jamais comme un entier nu : le lecteur d'agenda ne lit que ce
        // champ, et un entier nu serait ignoré en silence.
        event_context: { positions: [{ portfolio_id: 42 }], theses: [], links: [] },
      }),
    ]);
    const selection = selectCatalysts(events, []);

    expect(selection.catalysts.map((entry) => entry.event.eventId)).toEqual([
      'ev-these',
      'ev-position',
    ]);
    // L'événement non relié n'est pas montré comme catalyseur, et il n'est pas
    // non plus effacé du décompte : il est DIT.
    expect(selection.unlinkedCount).toBe(1);
  });

  it("conserve l'ordre servi par le worker, sans aucun tri local", () => {
    const events = calendarEventsOf([
      linkedEvent('ev-c', 1, 'C'),
      linkedEvent('ev-a', 2, 'A'),
      linkedEvent('ev-b', 3, 'B'),
    ]);
    expect(selectCatalysts(events, []).catalysts.map((entry) => entry.event.eventId)).toEqual([
      'ev-c',
      'ev-a',
      'ev-b',
    ]);
  });

  it('dit qu’une thèse citée par un événement est absente de la file, sans la compléter', () => {
    const events = calendarEventsOf([linkedEvent('ev-1', 999, 'Thèse jamais publiée')]);
    const selection = selectCatalysts(events, []);
    const thesis = selection.catalysts[0]?.theses[0];

    expect(thesis?.knownInQueue).toBe(false);
    // Aucun état inventé : ni échéance, ni « due », ni information nouvelle.
    expect(thesis?.effectiveReviewDueAt).toBeNull();
    expect(thesis?.isDue).toBe(false);
    expect(thesis?.hasNewInformation).toBe(false);
    // Le titre reste celui de l'ÉVÉNEMENT, jamais remplacé.
    expect(thesis?.title).toBe('Thèse jamais publiée');
  });

  it('relaie l’état de la file quand la thèse y est, sans le recalculer', () => {
    const queue = queueContentOf(makeQueueContent());
    expect(queue).not.toBeNull();
    const known = queue!.theses[0];
    expect(known).toBeDefined();

    const events = calendarEventsOf([linkedEvent('ev-1', known!.id, known!.title)]);
    const thesis = selectCatalysts(events, queue!.theses).catalysts[0]?.theses[0];

    expect(thesis?.knownInQueue).toBe(true);
    expect(thesis?.isDue).toBe(known!.isDue);
    expect(thesis?.hasNewInformation).toBe(known!.hasNewInformation);
    expect(thesis?.effectiveReviewDueAt).toBe(known!.effectiveReviewDueAt);
  });

  it('liste les thèses qu’aucun événement servi ne touche', () => {
    const queue = queueContentOf(makeQueueContent());
    const selection = selectCatalysts([], queue!.theses);
    expect(selection.thesesWithoutCatalyst).toHaveLength(queue!.theses.length);
    expect(selection.catalysts).toEqual([]);
  });
});

describe('catalystFrameStateOf — états serveur relayés', () => {
  it('relaie requête, vide, périmé et refus sans jamais reconstruire', () => {
    expect(catalystFrameStateOf('loading', undefined)).toBe('loading');
    expect(catalystFrameStateOf('offline', undefined)).toBe('offline');
    expect(catalystFrameStateOf('ready', undefined)).toBe('error');
    expect(catalystFrameStateOf('ready', 'empty')).toBe('empty');
    expect(catalystFrameStateOf('ready', 'empty_window')).toBe('empty');
    expect(catalystFrameStateOf('ready', 'stale')).toBe('stale');
    expect(catalystFrameStateOf('ready', 'degraded')).toBe('partial');
    expect(catalystFrameStateOf('ready', 'ok')).toBe('ready');
  });

  it("un refus de droit n'est PAS un état partiel : rien n'est servi", () => {
    // `not_entitled` et `rejected` ne dégradent pas un contenu : il n'y a
    // aucun contenu. Les traiter en `partial` laisserait croire qu'une partie
    // est affichée.
    expect(catalystFrameStateOf('ready', 'not_entitled')).toBe('error');
    expect(catalystFrameStateOf('ready', 'rejected')).toBe('error');
  });
});

describe('Page Catalyseurs — rendu', () => {
  it('affiche la question du contrat et les deux populations séparément', async () => {
    mockRoutes();
    await renderCatalysts();
    expect(
      screen.getByText('Quels événements vérifiés peuvent modifier la thèse et quand ?'),
    ).toBeDefined();
    const populations = await screen.findByTestId('cat-populations');
    expect(populations.textContent).toContain('SYNTHETIC');
  });

  it('sépare exactement les événements reliés des autres, sur l’agenda synthétique par défaut', async () => {
    // L'agenda synthétique publie deux événements : le RÉVISÉ porte une thèse
    // et une position, l'ESTIMÉ ne porte rien. La page doit donc montrer un
    // seul catalyseur et DIRE que le second n'est relié à rien — ni le
    // masquer, ni le compter comme catalyseur.
    mockRoutes();
    await renderCatalysts();
    const liste = await screen.findByTestId('cat-list');
    expect(within(liste).getAllByRole('listitem').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId('cat-syn-ev-earnings-SYN-ENER-01')).toBeDefined();
    expect(screen.queryByTestId('cat-syn-ev-earnings-SYN-FINL-01')).toBeNull();
    expect(screen.getByTestId('cat-unlinked').textContent).toBe('1');
  });

  it('un agenda sans aucun événement relié affiche un vide EXPLICITE', async () => {
    mockRoutes({
      calendar: () =>
        jsonResponse(makeCalendarResponse({ agenda: [makeCalendarEvent({ event_id: 'ev-libre' })] })),
    });
    await renderCatalysts();
    expect(await screen.findByTestId('cat-empty')).toBeDefined();
    expect(screen.queryByTestId('cat-list')).toBeNull();
    expect(screen.getByTestId('cat-unlinked').textContent).toBe('1');
  });

  it('un événement relié apparaît avec son motif, son statut marqué et sa provenance', async () => {
    mockRoutes({
      calendar: () =>
        jsonResponse(
          makeCalendarResponse({ agenda: [linkedEvent('ev-lie', 1, 'Thèse liée')] }),
        ),
    });
    await renderCatalysts();
    const item = await screen.findByTestId('cat-ev-lie');
    expect(within(item).getByText('thèse liée')).toBeDefined();
    // Statut : marque textuelle ET libellé — jamais la couleur seule.
    expect(item.textContent).toContain('✓ Confirmé');
    expect(item.textContent).toContain('synthetic-dev');
    expect(screen.getByTestId('cat-unlinked').textContent).toBe('0');
  });

  it('le widget « consensus fourni » du contrat est déclaré ABSENT, pas approximé', async () => {
    mockRoutes();
    await renderCatalysts();
    const note = await screen.findByTestId('cat-missing-widget');
    expect(note.textContent).toContain('ABSENT');
  });

  it('agenda sans droit → refus honnête, et la revue reste lisible', async () => {
    // Preuve d'indépendance des deux snapshots : l'agenda est refusé, la file
    // répond, et le module de revue reste affiché avec son propre contenu.
    mockRoutes({ calendar: () => jsonResponse(makeNotEntitledCalendarResponse()) });
    await renderCatalysts();
    await waitFor(() => {
      expect(document.querySelector('[data-state="error"]')).not.toBeNull();
    });
    expect(screen.queryByTestId('cat-list')).toBeNull();
    expect(await screen.findByRole('heading', { level: 2, name: 'Revue des thèses' })).toBeDefined();
  });

  it('agenda vide → raison serveur affichée, aucune timeline inventée', async () => {
    mockRoutes({
      calendar: () =>
        jsonResponse(
          makeCalendarResponse({ state: 'empty', agenda: [], reason: 'never_published' }),
        ),
    });
    await renderCatalysts();
    expect(await screen.findByText(/raison serveur : never_published/)).toBeDefined();
    expect(screen.queryByTestId('cat-list')).toBeNull();
  });

  it('réseau coupé → état hors ligne honnête, aucun catalyseur', async () => {
    fetchMock.mockRejectedValue(new TypeError('network down'));
    renderApp('/catalysts');
    await waitFor(() => {
      expect(document.querySelector('[data-state="offline"]')).not.toBeNull();
    });
    expect(screen.queryByTestId('cat-list')).toBeNull();
  });
});

describe('Catalyseurs — inspecteur contextuel (point 6 de l’anatomie)', () => {
  it('aucune colonne morte : l’inspecteur reste masqué tant que rien n’est ouvert', async () => {
    mockRoutes();
    await renderCatalysts();
    const inspecteur = document.getElementById('vx-inspector-slot');
    expect(inspecteur).not.toBeNull();
    // Le nœud existe (une cible de portail doit être montée) mais il est
    // `hidden` : une colonne vide en permanence serait de la chrome.
    expect(inspecteur?.hasAttribute('hidden')).toBe(true);
    expect(screen.queryByRole('heading', { level: 2, name: /^Inspecteur/ })).toBeNull();
  });

  it('ouvrir un catalyseur remplit l’inspecteur avec les cinq champs du contrat §10', async () => {
    const user = userEvent.setup();
    mockRoutes();
    await renderCatalysts();

    const item = await screen.findByTestId('cat-syn-ev-earnings-SYN-ENER-01');
    await user.click(within(item).getByRole('button'));

    const titre = await screen.findByRole('heading', { level: 2, name: /^Inspecteur/ });
    expect(titre.textContent).toContain('SYN-ENER-01');
    expect(document.getElementById('vx-inspector-slot')?.hasAttribute('hidden')).toBe(false);

    const panneau = titre.closest('.vx-inspector-panel');
    expect(panneau).not.toBeNull();
    const texte = panneau!.textContent ?? '';
    // Les cinq champs que le contrat §10 nomme, tous relayés :
    expect(texte).toContain('Source'); // source
    expect(texte).toContain('Europe/Zurich'); // fuseau
    expect(texte).toContain('Historique publié'); // historique
    expect(texte).toContain('Éléments liés'); // instruments liés
    expect(texte).toContain('Statut'); // incertitude factuelle
  });

  it('l’inspecteur n’affiche AUCUNE probabilité et le dit', async () => {
    const user = userEvent.setup();
    mockRoutes();
    await renderCatalysts();
    const item = await screen.findByTestId('cat-syn-ev-earnings-SYN-ENER-01');
    await user.click(within(item).getByRole('button'));

    const titre = await screen.findByRole('heading', { level: 2, name: /^Inspecteur/ });
    const texte = titre.closest('.vx-inspector-panel')?.textContent ?? '';
    expect(texte).toContain('Aucune probabilité n’est affichée');
    // Le contrat d'agenda n'en publie aucune ; en afficher une sans
    // calibration serait interdit par .claude/rules/financial-safety.md.
    expect(texte).not.toMatch(/\d+\s*%\s*de (chance|probabilité)/);
  });

  it('l’état ouvert est porté par aria-pressed, pas par la seule couleur', async () => {
    const user = userEvent.setup();
    mockRoutes();
    await renderCatalysts();
    const item = await screen.findByTestId('cat-syn-ev-earnings-SYN-ENER-01');
    const bouton = within(item).getByRole('button');
    expect(bouton.getAttribute('aria-pressed')).toBe('false');
    await user.click(bouton);
    expect(bouton.getAttribute('aria-pressed')).toBe('true');
  });

  it('une sélection qui ne correspond plus à rien ne laisse pas un panneau figé', () => {
    // La page ne mémorise qu'un IDENTIFIANT. Si le snapshot est rafraîchi et
    // que l'événement n'y est plus, il n'y a plus rien à inspecter : garder
    // l'objet aurait affiché indéfiniment un état périmé sans le dire.
    const servi = selectCatalysts(calendarEventsOf([linkedEvent('ev-1', 1, 'A')]), []);
    expect(selectedCatalystOf(servi, 'ev-1')?.event.eventId).toBe('ev-1');

    const apresRafraichissement = selectCatalysts(
      calendarEventsOf([linkedEvent('ev-2', 2, 'B')]),
      [],
    );
    expect(selectedCatalystOf(apresRafraichissement, 'ev-1')).toBeNull();
    expect(selectedCatalystOf(null, 'ev-1')).toBeNull();
    expect(selectedCatalystOf(servi, null)).toBeNull();
  });
});
