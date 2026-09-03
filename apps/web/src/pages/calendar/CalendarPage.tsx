import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { isApiError } from '../../api/client.ts';
import type { CalendarResponse } from '../../api/client.ts';
import { useCalendar } from '../../api/decisionApi.ts';
import type { CalendarWindowQuery } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import type { PageDataState } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { Card } from '../../components/Card.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import type { ModuleState } from '../../components/moduleState.ts';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import {
  AbsentCalendarModule,
  BlockedAgenda,
  ConflictsModule,
  CountersModule,
  DailyExposureModule,
  DensityModule,
  ImportanceRuleModule,
  NextEventModule,
  ProvenanceModule,
  RevisionsModule,
  TimezoneModule,
  applyFilters,
  timeZoneChoicesOf,
} from './CalendarModules.tsx';
import { EventAgenda } from './EventAgenda.tsx';
import { CalendarSnapshotInspector, EventInspector } from './EventInspector.tsx';
import { calendarModule } from './calendarModules.ts';
import {
  CONFIRMED_STATUS,
  ESTIMATED_STATUS,
  calendarEventsOf,
  categoryLabelOf,
  counterMapOf,
  resolveViewerTimeZone,
  statusLabelOf,
} from './calendarView.ts';
import type { AgendaGrouping, CalendarEventView } from './calendarView.ts';

/**
 * Page Calendrier (`TL / 11`) — question : « Quels événements peuvent
 * affecter mes instruments et mon portefeuille ? »
 *
 * Tout vient du snapshot `calendar/global` publié par le worker et relayé
 * verbatim par l'API. L'interface ne calcule aucune importance, aucun statut
 * et aucune date : elle SÉLECTIONNE (filtres de catégorie/statut persistés
 * dans l'URL), regroupe l'agenda servi et convertit l'instant UTC publié
 * dans un fuseau IANA EXPLICITE choisi par vous (`tz`), jamais deviné.
 *
 * LOT-A7 — LA PLANCHE §11 EN ENTIER. `pages-11-12-calendar-sources-reports.png`
 * (moitié gauche) compose treize modules. Onze sont SERVIS : la fenêtre et
 * les filtres (libellés intacts), le fuseau d'affichage, l'agenda en
 * DOMINANTE (dense, régions bornées, jamais une grille horaire inventée),
 * l'exposition du registre par jour et la densité (dénombrements), le
 * prochain événement (premier de l'ordre publié, SANS compte à rebours),
 * les compteurs, la règle d'importance, la provenance, les révisions et les
 * conflits. Deux n'ont aucun contrat : rappels et changements depuis la
 * dernière visite. L'inspecteur porte l'événement ouvert, sinon le snapshot.
 *
 * États honnêtes servis par le contrat (aucun n'est assimilé à un autre, et
 * un état INCONNU échoue fermé plutôt que de passer pour `ok`) :
 * - `ok` : agenda servi ;
 * - `empty` : rien à montrer, avec la raison publiée ;
 * - `empty_window` : la fenêtre DEMANDÉE ne sélectionne aucun événement
 *   publié — c'est le résultat de la sélection, pas un agenda vide ;
 * - `not_entitled` : agenda vidé par un REFUS DE DROIT — le droit manquant
 *   et sa raison sont affichés, jamais une liste vide banale ;
 * - `rejected` : tous les enregistrements considérés étaient invalides ;
 * - `stale` : les événements SONT servis mais tous périmés — ils s'affichent
 *   sous le bandeau « Données périmées », jamais comme un agenda frais ;
 * - `degraded` : le snapshot précède le contrat `agenda_state` ; l'agenda est
 *   relayé, son état est honnêtement inconnu (bandeau « Données partielles »).
 *
 * La fenêtre `from`/`to` est bornée à 90 jours PAR LE SERVEUR : les quatre
 * refus typés (WINDOW_INCOMPLETE, WINDOW_NAIVE_DATETIME, WINDOW_INVERTED,
 * WINDOW_TOO_LARGE) sont affichés en clair, sans être corrigés ici.
 */

/** Libellés français des quatre refus typés de fenêtre (contrat API). */
export const WINDOW_ERROR_LABELS: Readonly<Record<string, string>> = {
  WINDOW_INCOMPLETE: 'Fenêtre incomplète — les deux bornes « du » et « au » sont requises.',
  WINDOW_NAIVE_DATETIME:
    'Fenêtre sans fuseau — chaque borne doit porter un décalage explicite (par exemple Z).',
  WINDOW_INVERTED: 'Fenêtre inversée — la borne « au » précède la borne « du ».',
  WINDOW_TOO_LARGE: 'Fenêtre trop large — la profondeur servie est bornée à 90 jours.',
};

export interface WindowErrorView {
  readonly code: string;
  readonly message: string | null;
}

/** Extrait le refus typé d'un 422 SANS jamais en inventer le contenu. */
export function windowErrorOf(error: unknown): WindowErrorView | null {
  if (!isApiError(error) || error.status !== 422) {
    return null;
  }
  const body = error.detail;
  if (typeof body !== 'object' || body === null) {
    return null;
  }
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail !== 'object' || detail === null) {
    return null;
  }
  const code = (detail as { code?: unknown }).code;
  const message = (detail as { message?: unknown }).message;
  if (typeof code !== 'string' || code === '') {
    return null;
  }
  return { code, message: typeof message === 'string' && message !== '' ? message : null };
}

export type CalendarFrame =
  | { readonly kind: 'state'; readonly state: DataState | 'auth-required'; readonly detail?: string }
  | { readonly kind: 'blocked'; readonly served: CalendarResponse }
  | {
      readonly kind: 'ok';
      readonly state: DataState;
      readonly served: CalendarResponse;
      readonly detail?: string;
    };

/**
 * Les états servis QUI PRÉSENTENT UN AGENDA, avec l'état d'affichage des 8
 * états canoniques qui leur correspond. `stale` et `degraded` conservent leur
 * contenu SOUS un bandeau explicite ; ils ne valent jamais `ready`.
 */
const AGENDA_BEARING_STATES: Readonly<Record<string, DataState | null>> = {
  ok: null,
  stale: 'stale',
  degraded: 'partial',
};

/** Cadre d'affichage dérivé UNIQUEMENT de faits observés. */
export function calendarFrameOf(
  queryState: PageDataState,
  data: CalendarResponse | undefined,
): CalendarFrame {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return { kind: 'state', state: queryState };
  }
  if (data === undefined) {
    return { kind: 'state', state: 'error' };
  }
  const served: string = data.state;
  if (served === 'not_entitled' || served === 'rejected') {
    return { kind: 'blocked', served: data };
  }
  if (served === 'empty' || served === 'empty_window') {
    return {
      kind: 'state',
      state: 'empty',
      detail:
        (served === 'empty_window'
          ? 'Fenêtre demandée : aucun événement publié ne s’y trouve. '
          : '') +
        (data.reason ??
          'Aucun agenda publié et aucune raison fournie par le serveur : rien n’est affiché.'),
    };
  }
  if (!(served in AGENDA_BEARING_STATES)) {
    // Fail-closed : un état hors contrat n'est jamais rendu comme un succès.
    return {
      kind: 'state',
      state: 'error',
      detail: `État servi hors contrat : « ${served} ». Rien n’est affiché.`,
    };
  }
  const degraded = AGENDA_BEARING_STATES[served] ?? null;
  if (degraded === null) {
    return { kind: 'ok', state: queryState, served: data };
  }
  return {
    kind: 'ok',
    state: degraded,
    served: data,
    detail:
      data.reason ??
      (degraded === 'stale'
        ? 'Tous les événements servis sont périmés (raison non publiée).'
        : 'État de l’agenda inconnu pour ce snapshot (raison non publiée).'),
  };
}

function moduleStateOfFrame(frame: CalendarFrame): ModuleState {
  if (frame.kind === 'ok') {
    return frame.state;
  }
  if (frame.kind === 'blocked') {
    return 'empty';
  }
  return frame.state;
}

function AgendaModule({
  frame,
  visible,
  grouping,
  displayTimeZone,
  selectedEventId,
  onInspect,
}: {
  readonly frame: CalendarFrame;
  readonly visible: readonly CalendarEventView[];
  readonly grouping: AgendaGrouping;
  readonly displayTimeZone: string;
  readonly selectedEventId: string | null;
  readonly onInspect: (eventId: string) => void;
}) {
  const module = calendarModule('agenda');
  return (
    <Card
      rank="dominant"
      kicker="Ordre publié, regroupé"
      title={module.title}
      titleId="vx-cal-agenda-title"
      className="vx-cal-agenda-card"
      aside={frame.kind === 'ok' ? <>{visible.length} affiché(s) · fuseau {displayTimeZone}</> : undefined}
      footer={<>trois lectures du temps par événement : instant UTC publié, heure de place, fuseau d’affichage ; rien n’est converti implicitement</>}
    >
      {frame.kind === 'blocked' ? (
        <BlockedAgenda served={frame.served} />
      ) : frame.kind === 'state' ? (
        <DataStateBoundary
          state={frame.state === 'auth-required' ? 'error' : frame.state}
          {...(frame.detail !== undefined ? { detail: frame.detail } : {})}
        />
      ) : (
        <DataStateBoundary
          state={frame.state}
          {...(frame.detail !== undefined ? { detail: frame.detail } : {})}
          {...(frame.served.as_of !== null ? { asOfLabel: frame.served.as_of } : {})}
        >
          <EventAgenda events={visible} grouping={grouping} viewerTimeZone={displayTimeZone} selectedEventId={selectedEventId} onInspect={onInspect} />
        </DataStateBoundary>
      )}
    </Card>
  );
}

export function CalendarPage() {
  const [params, setParams] = useSearchParams();
  const fromParam = params.get('from') ?? '';
  const toParam = params.get('to') ?? '';
  const category = params.get('category') ?? '';
  const status = params.get('status') ?? '';
  const grouping: AgendaGrouping = params.get('grouping') === 'week' ? 'week' : 'day';
  const tzParam = params.get('tz') ?? '';

  const windowQuery: CalendarWindowQuery | null =
    fromParam === '' && toParam === '' ? null : { from: fromParam, to: toParam };
  const query = useCalendar(windowQuery);
  const queryState = pageStateOf(query);
  const frame = calendarFrameOf(queryState, query.data);
  const viewerTimeZone = useMemo(() => resolveViewerTimeZone(), []);
  const windowError = windowErrorOf(query.error);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  function updateParam(key: string, value: string): void {
    const next = new URLSearchParams(params);
    if (value === '') {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    setParams(next, { replace: true });
  }

  const served = frame.kind === 'ok' ? frame.served : null;
  const events = served === null ? [] : calendarEventsOf(served.agenda);
  const visible = applyFilters(events, category, status);
  const servedCategories = served === null ? new Map() : counterMapOf(served.window.categories);
  const servedStatuses = served === null ? new Map() : counterMapOf(served.window.statuses);
  const moduleState = moduleStateOfFrame(frame);
  // Le fuseau d'affichage : celui de l'URL s'il est proposé, sinon celui du
  // navigateur s'il est résolu, sinon UTC — toujours NOMMÉ à l'écran.
  const choices = timeZoneChoicesOf(events, viewerTimeZone);
  const displayTimeZone = tzParam !== '' && choices.includes(tzParam) ? tzParam : (viewerTimeZone ?? 'UTC');
  const selected = selectedEventId === null ? null : (visible.find((event) => event.eventId === selectedEventId) ?? null);
  const agendaEvents = served === null ? null : events;

  return (
    <article className="vx-calendar vx-page" aria-labelledby="vx-page-title-calendar">
      <header className="vx-page-header">
        <h1 id="vx-page-title-calendar">Calendrier</h1>
        <p className="vx-page-question">
          Quels événements peuvent affecter mes instruments et mon portefeuille ?
        </p>
      </header>

      {served !== null ? <SyntheticBanner population={served.population} /> : null}

      {queryState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : (
        <>
          <div className="vx-cal-grid vx-board" data-testid="calendar-grid">
            <div data-module="view-controls">
              <Card
                rank="quiet"
                kicker="Bornes transmises telles quelles"
                title={calendarModule('view-controls').title}
                titleId="vx-cal-window-title"
                className="vx-cal-window"
                footer={<>le serveur valide les bornes et borne la profondeur à 90 jours ; aucune borne n’est corrigée par l’interface</>}
              >
                <div className="vx-matrix-filters">
                  <label>
                    Du (instant avec fuseau)
                    <input type="text" name="from" value={fromParam} placeholder="2026-09-01T00:00:00Z" onChange={(bubble) => updateParam('from', bubble.target.value)} />
                  </label>
                  <label>
                    Au (instant avec fuseau)
                    <input type="text" name="to" value={toParam} placeholder="2026-10-01T00:00:00Z" onChange={(bubble) => updateParam('to', bubble.target.value)} />
                  </label>
                  <label>
                    Catégorie
                    <select name="category" value={category} onChange={(bubble) => updateParam('category', bubble.target.value)}>
                      <option value="">Toutes les catégories</option>
                      {[...servedCategories.entries()].map(([key, count]) => (
                        <option key={key} value={key}>
                          {categoryLabelOf(key)} ({count})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Statut de date
                    <select name="status" value={status} onChange={(bubble) => updateParam('status', bubble.target.value)}>
                      <option value="">Tous les statuts</option>
                      {[ESTIMATED_STATUS, CONFIRMED_STATUS].map((key) => (
                        <option key={key} value={key}>
                          {statusLabelOf(key)} ({servedStatuses.get(key) ?? 0})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Regroupement
                    <select name="grouping" value={grouping} onChange={(bubble) => updateParam('grouping', bubble.target.value)}>
                      <option value="day">Par jour</option>
                      <option value="week">Par semaine</option>
                    </select>
                  </label>
                </div>
                <p className="vx-matrix-count" role="status" data-testid="cal-filter-count">
                  {visible.length} événement{visible.length > 1 ? 's' : ''} affiché
                  {visible.length > 1 ? 's' : ''} sur {events.length} servi{events.length > 1 ? 's' : ''} par le serveur — les
                  compteurs par catégorie et par statut viennent du serveur.
                </p>
                {windowError !== null ? (
                  <p className="vx-cal-window-error" role="alert" data-testid="cal-window-error">
                    <strong>Fenêtre refusée par le serveur — code {windowError.code}</strong>
                    <span>{WINDOW_ERROR_LABELS[windowError.code] ?? 'Refus typé relayé tel quel : aucun libellé local ne le remplace.'}</span>
                    {windowError.message !== null ? <span className="vx-cal-window-error-raw">Message du serveur : {windowError.message}</span> : null}
                  </p>
                ) : null}
              </Card>
            </div>
            <div data-module="timezone">
              <TimezoneModule
                events={agendaEvents}
                viewerTimeZone={viewerTimeZone}
                displayTimeZone={displayTimeZone}
                onChange={(zone) => {
                  updateParam('tz', zone);
                }}
                state={moduleState}
              />
            </div>

            <div data-module="agenda">
              <AgendaModule
                frame={frame}
                visible={visible}
                grouping={grouping}
                displayTimeZone={displayTimeZone}
                selectedEventId={selected?.eventId ?? null}
                onInspect={(eventId) => {
                  setSelectedEventId((previous) => (previous === eventId ? null : eventId));
                }}
              />
            </div>
            <div data-module="next-event">
              <NextEventModule events={agendaEvents === null ? null : visible} displayTimeZone={displayTimeZone} state={moduleState} />
            </div>
            <div data-module="counters">
              <CountersModule served={served} state={moduleState} />
            </div>

            <div data-module="daily-exposure">
              <DailyExposureModule events={agendaEvents} state={moduleState} />
            </div>
            <div data-module="density">
              <DensityModule events={agendaEvents} state={moduleState} />
            </div>

            <AbsentCalendarModule id="reminders" />
            <AbsentCalendarModule id="changes-since-visit" />
            <div data-module="revisions">
              <RevisionsModule events={agendaEvents} state={moduleState} />
            </div>
            <div data-module="conflicts">
              <ConflictsModule events={agendaEvents} state={moduleState} />
            </div>

            <div data-module="importance-rule">
              <ImportanceRuleModule served={served} state={moduleState} />
            </div>
            <div data-module="provenance">
              <ProvenanceModule served={served} state={moduleState} />
            </div>
          </div>

          {selected === null ? (
            <CalendarSnapshotInspector served={served} shown={visible.length} total={events.length} />
          ) : (
            <EventInspector
              event={selected}
              displayTimeZone={displayTimeZone}
              onClose={() => {
                setSelectedEventId(null);
              }}
            />
          )}
        </>
      )}
    </article>
  );
}
