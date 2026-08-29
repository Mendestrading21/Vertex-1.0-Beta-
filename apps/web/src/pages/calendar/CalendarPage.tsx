import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

import { isApiError } from '../../api/client.ts';
import type { CalendarResponse } from '../../api/client.ts';
import { useCalendar } from '../../api/decisionApi.ts';
import type { CalendarWindowQuery } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import type { PageDataState } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { EventAgenda } from './EventAgenda.tsx';
import {
  CONFIRMED_STATUS,
  ESTIMATED_STATUS,
  calendarEventsOf,
  categoryLabelOf,
  counterMapOf,
  importanceRuleOf,
  resolveViewerTimeZone,
  statusLabelOf,
} from './calendarView.ts';
import type { AgendaGrouping, CalendarEventView } from './calendarView.ts';

/**
 * Page Calendrier — question : « Quels événements peuvent affecter mes
 * instruments et mon portefeuille ? »
 *
 * Tout vient du snapshot `calendar/global` publié par le worker et relayé
 * verbatim par l'API. L'interface ne calcule aucune importance, aucun statut
 * et aucune date : elle SÉLECTIONNE (filtres de catégorie/statut persistés
 * dans l'URL) et regroupe l'agenda servi.
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

const REASON_RIGHTS_NOT_USABLE = 'rights_not_usable';

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

function BlockedAgenda({ served }: { readonly served: CalendarResponse }) {
  const coverage = served.coverage ?? {};
  const rejectedReasons = counterMapOf((coverage as Record<string, unknown>)['rejected_reasons']);
  const notEntitled = served.state === 'not_entitled';
  return (
    <section
      className="vx-cal-blocked"
      role="status"
      data-state={served.state}
      data-testid="cal-blocked"
      aria-labelledby="vx-cal-blocked-title"
    >
      <p className="vx-badge vx-badge-warning">
        {notEntitled ? 'DROIT MANQUANT — AGENDA NON SERVI' : 'ENREGISTREMENTS REFUSÉS'}
      </p>
      <h2 id="vx-cal-blocked-title">
        {notEntitled
          ? 'Agenda vide par refus de droit'
          : 'Agenda vide : tous les enregistrements considérés sont invalides'}
      </h2>
      <p>
        {notEntitled ? (
          <>
            Le droit manquant est <code>{REASON_RIGHTS_NOT_USABLE}</code> : les enregistrements
            considérés ont été refusés parce que leurs droits ne sont pas exploitables. Ce n’est
            PAS un agenda sans événement.
          </>
        ) : (
          <>
            Aucun événement n’a passé la validation du worker. L’agenda reste vide : rien n’est
            réparé, complété ni estimé.
          </>
        )}
      </p>
      <p className="vx-cal-blocked-reason" data-testid="cal-blocked-reason">
        Raison publiée : {served.reason ?? 'aucune raison publiée par le serveur'}
      </p>
      {rejectedReasons.size > 0 ? (
        <div
          className="vx-cal-scroll"
          tabIndex={0}
          role="region"
          aria-label="Motifs de refus comptés par le worker"
        >
        <table className="vx-matrix-table">
          <caption>Motifs de refus comptés par le worker sur les enregistrements considérés.</caption>
          <thead>
            <tr>
              <th scope="col">Motif</th>
              <th scope="col">Enregistrements</th>
            </tr>
          </thead>
          <tbody>
            {[...rejectedReasons.entries()].map(([reason, count]) => (
              <tr key={reason} data-testid={`cal-rejected-${reason}`}>
                <th scope="row">
                  <code>{reason}</code>
                </th>
                <td className="vx-num">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      ) : (
        <p className="vx-matrix-empty">Aucun compteur de refus publié.</p>
      )}
    </section>
  );
}

function ImportanceRulePanel({ rule }: { readonly rule: unknown }) {
  const view = importanceRuleOf(rule);
  return (
    <details className="vx-cal-rule" data-testid="cal-importance-rule">
      <summary>
        Règle d’importance versionnée : <code>{view.version ?? 'non publiée'}</code>
      </summary>
      <div
        className="vx-cal-scroll"
        tabIndex={0}
        role="region"
        aria-label="Rangs de la règle d’importance publiée"
      >
      <table className="vx-matrix-table">
        <caption>
          Rangs documentés de la règle publiée. L’interface n’attribue aucune importance : elle
          affiche le rang et le code que le worker a appliqués.
        </caption>
        <thead>
          <tr>
            <th scope="col">Rang</th>
            <th scope="col">Code</th>
            <th scope="col">Description publiée</th>
          </tr>
        </thead>
        <tbody>
          {view.ranks.map((entry) => (
            <tr key={`${entry.rank}-${entry.code}`}>
              <th scope="row" className="vx-num">
                {entry.rank ?? '—'}
              </th>
              <td>
                <code>{entry.code ?? '—'}</code>
              </td>
              <td>{entry.description ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </details>
  );
}

function CountersPanel({ served }: { readonly served: CalendarResponse }) {
  const windowEcho = served.window;
  const servedCategories = counterMapOf(windowEcho.categories);
  const servedStatuses = counterMapOf(windowEcho.statuses);
  const totalCategories = counterMapOf(served.categories);
  const totalStatuses = counterMapOf(served.statuses);
  return (
    <div className="vx-cal-counters" data-testid="cal-counters">
      <div
        className="vx-cal-scroll"
        tabIndex={0}
        role="region"
        aria-label="Compteurs de la liste servie et totaux du snapshot"
      >
      <table className="vx-matrix-table">
        <caption>
          Deux comptages DISTINCTS publiés par le serveur : la liste réellement servie (après
          fenêtre) et les totaux du snapshot entier. Ils ne se remplacent jamais.
        </caption>
        <thead>
          <tr>
            <th scope="col">Clé</th>
            <th scope="col">Liste servie (fenêtre appliquée)</th>
            <th scope="col">Total du snapshot</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Événements</th>
            <td className="vx-num" data-testid="cal-count-served">
              {windowEcho.events_in_window}
            </td>
            <td className="vx-num" data-testid="cal-count-total">
              {windowEcho.events_total}
            </td>
          </tr>
          {[...new Set([...servedCategories.keys(), ...totalCategories.keys()])]
            .sort()
            .map((category) => (
              <tr key={`cat-${category}`} data-testid={`cal-counter-category-${category}`}>
                <th scope="row">
                  Catégorie {categoryLabelOf(category)} (<code>{category}</code>)
                </th>
                <td className="vx-num">{servedCategories.get(category) ?? 0}</td>
                <td className="vx-num">{totalCategories.get(category) ?? 0}</td>
              </tr>
            ))}
          {[...new Set([...servedStatuses.keys(), ...totalStatuses.keys()])].sort().map((status) => (
            <tr key={`st-${status}`} data-testid={`cal-counter-status-${status}`}>
              <th scope="row">
                Statut {statusLabelOf(status)} (<code>{status}</code>)
              </th>
              <td className="vx-num">{servedStatuses.get(status) ?? 0}</td>
              <td className="vx-num">{totalStatuses.get(status) ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}

function ProvenanceStrip({ served }: { readonly served: CalendarResponse }) {
  const coverage = (served.coverage ?? {}) as Record<string, unknown>;
  const superseded = coverage['events_superseded'];
  const considered = coverage['observations_considered'];
  const stale = coverage['events_stale'];
  return (
    <p className="vx-cal-provenance" data-testid="cal-provenance">
      Snapshot version <code>{served.snapshot_version ?? '—'}</code> — publié{' '}
      {served.as_of !== null ? <time dateTime={served.as_of}>{served.as_of}</time> : '—'} —
      population <code>{served.population ?? '—'}</code> — fenêtre bornée à{' '}
      <span className="vx-num">{served.window.max_days}</span> jours — observations considérées{' '}
      <span className="vx-num">{typeof considered === 'number' ? considered : '—'}</span> —
      enregistrements supplantés{' '}
      <span className="vx-num">{typeof superseded === 'number' ? superseded : '—'}</span> —
      événements périmés{' '}
      <span className="vx-num">{typeof stale === 'number' ? stale : '—'}</span>
    </p>
  );
}

function applyFilters(
  events: readonly CalendarEventView[],
  category: string,
  status: string,
): readonly CalendarEventView[] {
  return events.filter(
    (event) =>
      (category === '' || event.category === category) &&
      (status === '' || event.status === status),
  );
}

export function CalendarPage() {
  const [params, setParams] = useSearchParams();
  const fromParam = params.get('from') ?? '';
  const toParam = params.get('to') ?? '';
  const category = params.get('category') ?? '';
  const status = params.get('status') ?? '';
  const grouping: AgendaGrouping = params.get('grouping') === 'week' ? 'week' : 'day';

  const windowQuery: CalendarWindowQuery | null =
    fromParam === '' && toParam === '' ? null : { from: fromParam, to: toParam };
  const query = useCalendar(windowQuery);
  const queryState = pageStateOf(query);
  const frame = calendarFrameOf(queryState, query.data);
  const viewerTimeZone = useMemo(() => resolveViewerTimeZone(), []);
  const windowError = windowErrorOf(query.error);

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

  return (
    <article className="vx-calendar" aria-labelledby="vx-page-title-calendar">
      <header className="vx-page-header">
        <h1 id="vx-page-title-calendar">Calendrier</h1>
        <p className="vx-page-question">
          Quels événements peuvent affecter mes instruments et mon portefeuille ?
        </p>
      </header>

      {served !== null ? <SyntheticBanner population={served.population} /> : null}

      <section className="vx-cal-window" aria-labelledby="vx-cal-window-title">
        <h2 id="vx-cal-window-title">Fenêtre servie et filtres</h2>
        <p className="vx-cal-window-note">
          Les deux bornes sont transmises telles quelles au serveur, qui les valide et borne la
          profondeur à 90 jours. Aucune borne n’est corrigée par l’interface.
        </p>
        <div className="vx-matrix-filters">
          <label>
            Du (instant avec fuseau)
            <input
              type="text"
              name="from"
              value={fromParam}
              placeholder="2026-09-01T00:00:00Z"
              onChange={(bubble) => updateParam('from', bubble.target.value)}
            />
          </label>
          <label>
            Au (instant avec fuseau)
            <input
              type="text"
              name="to"
              value={toParam}
              placeholder="2026-10-01T00:00:00Z"
              onChange={(bubble) => updateParam('to', bubble.target.value)}
            />
          </label>
          <label>
            Catégorie
            <select
              name="category"
              value={category}
              onChange={(bubble) => updateParam('category', bubble.target.value)}
            >
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
            <select
              name="status"
              value={status}
              onChange={(bubble) => updateParam('status', bubble.target.value)}
            >
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
            <select
              name="grouping"
              value={grouping}
              onChange={(bubble) => updateParam('grouping', bubble.target.value)}
            >
              <option value="day">Par jour</option>
              <option value="week">Par semaine</option>
            </select>
          </label>
        </div>
        <p className="vx-matrix-count" role="status" data-testid="cal-filter-count">
          {visible.length} événement{visible.length > 1 ? 's' : ''} affiché
          {visible.length > 1 ? 's' : ''} sur {events.length} servi{events.length > 1 ? 's' : ''}{' '}
          par le serveur — les compteurs par catégorie et par statut viennent du serveur.
        </p>
        {windowError !== null ? (
          <p className="vx-cal-window-error" role="alert" data-testid="cal-window-error">
            <strong>Fenêtre refusée par le serveur — code {windowError.code}</strong>
            <span>
              {WINDOW_ERROR_LABELS[windowError.code] ??
                'Refus typé relayé tel quel : aucun libellé local ne le remplace.'}
            </span>
            {windowError.message !== null ? (
              <span className="vx-cal-window-error-raw">Message du serveur : {windowError.message}</span>
            ) : null}
          </p>
        ) : null}
      </section>

      {queryState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : frame.kind === 'blocked' ? (
        <BlockedAgenda served={frame.served} />
      ) : frame.kind === 'state' ? (
        <DataStateBoundary
          state={frame.state as DataState}
          {...(frame.detail !== undefined ? { detail: frame.detail } : {})}
        />
      ) : (
        <DataStateBoundary
          state={frame.state}
          {...(frame.detail !== undefined ? { detail: frame.detail } : {})}
          {...(frame.served.as_of !== null ? { asOfLabel: frame.served.as_of } : {})}
        >
          <ProvenanceStrip served={frame.served} />
          <ImportanceRulePanel rule={frame.served.importance_rule} />
          <CountersPanel served={frame.served} />
          <EventAgenda events={visible} grouping={grouping} viewerTimeZone={viewerTimeZone} />
        </DataStateBoundary>
      )}
    </article>
  );
}
