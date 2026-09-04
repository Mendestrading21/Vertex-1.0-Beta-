import type { CalendarResponse } from '../../api/client.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { Metric } from '../../components/Metric.tsx';
import { MODULE_STATE_LABELS } from '../../components/moduleState.ts';
import type { ModuleState } from '../../components/moduleState.ts';
import { AgendaLine } from '../../components/calendar/AgendaLine.tsx';
import { DayBars } from '../../components/widgets/DayBars.tsx';
import type { DayBarEntry } from '../../components/widgets/DayBars.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
import { EventStatusBadge } from './EventAgenda.tsx';
import { calendarModule } from './calendarModules.ts';
import {
  VERSION_STATE_CONFLICTING,
  categoryLabelOf,
  counterMapOf,
  formatInTimeZone,
  groupKeyOf,
  importanceRuleOf,
  statusLabelOf,
} from './calendarView.ts';
import type { CalendarEventView } from './calendarView.ts';

/**
 * Les modules SERVIS de la planche §11, hors la dominante (l'agenda, porté
 * par la page) et hors les contrôles de fenêtre (formulaire conservé). Tous
 * lisent le même snapshot `calendar/global` déjà validé par la page. Aucun
 * calcul : compteurs publiés, dénombrements d'événements servis, instants
 * publiés convertis dans un fuseau IANA EXPLICITE — jamais deviné.
 */

const REASON_RIGHTS_NOT_USABLE = 'rights_not_usable';
const UTC = 'UTC';

export function AbsentCalendarModule({ id }: { readonly id: string }) {
  const module = calendarModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    // `data-size` vient du catalogue comme pour un module servi : la planche
    // compose de la même façon un module absent et un module servi.
    <div data-module={id} data-size={module.size}>
      <AbsentModule title={module.title} question={module.question} reason={module.status.reason} note={module.status.note} />
    </div>
  );
}

/**
 * Ce qu'un module d'agenda montre quand aucun agenda n'est servi. L'état est
 * DIT en clair, sans `data-state` : la seule frontière `data-state` de la
 * page est celle de l'agenda (dominante), que le témoin e2e hors ligne lit.
 */
export function AgendaAbsence({ state }: { readonly state: ModuleState }) {
  if (state === 'empty') {
    return (
      <p className="vx-module-sentence" role="status">
        Aucun agenda servi : rien à dénombrer (voir l’agenda).
      </p>
    );
  }
  if (state === 'ready' || state === 'refreshing') {
    return null;
  }
  return (
    <p className="vx-module-sentence" role="status">
      Agenda non lisible — {MODULE_STATE_LABELS[state].toLowerCase()} : rien à dénombrer (voir l’agenda).
    </p>
  );
}

export function applyFilters(
  events: readonly CalendarEventView[],
  category: string,
  status: string,
): readonly CalendarEventView[] {
  return events.filter(
    (event) => (category === '' || event.category === category) && (status === '' || event.status === status),
  );
}

// ---------------------------------------------------------------------------

export function BlockedAgenda({ served }: { readonly served: CalendarResponse }) {
  const coverage = served.coverage ?? {};
  const rejectedReasons = counterMapOf((coverage as Record<string, unknown>)['rejected_reasons']);
  const notEntitled = served.state === 'not_entitled';
  return (
    <section className="vx-cal-blocked" role="status" data-state={served.state} data-testid="cal-blocked" aria-labelledby="vx-cal-blocked-title">
      <p className="vx-badge vx-badge-warning">{notEntitled ? 'DROIT MANQUANT — AGENDA NON SERVI' : 'ENREGISTREMENTS REFUSÉS'}</p>
      <h3 id="vx-cal-blocked-title">
        {notEntitled ? 'Agenda vide par refus de droit' : 'Agenda vide : tous les enregistrements considérés sont invalides'}
      </h3>
      <p>
        {notEntitled ? (
          <>
            Le droit manquant est <code>{REASON_RIGHTS_NOT_USABLE}</code> : les enregistrements considérés ont été refusés parce que
            leurs droits ne sont pas exploitables. Ce n’est PAS un agenda sans événement.
          </>
        ) : (
          <>Aucun événement n’a passé la validation du worker. L’agenda reste vide : rien n’est réparé, complété ni estimé.</>
        )}
      </p>
      <p className="vx-cal-blocked-reason" data-testid="cal-blocked-reason">
        Raison publiée : {served.reason ?? 'aucune raison publiée par le serveur'}
      </p>
      {rejectedReasons.size > 0 ? (
        <div className="vx-cal-scroll" tabIndex={0} role="region" aria-label="Motifs de refus comptés par le worker">
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

// ---------------------------------------------------------------------------

export function ImportanceRuleModule({ served, state }: { readonly served: CalendarResponse | null; readonly state: ModuleState }) {
  const module = calendarModule('importance-rule');
  const view = served === null ? null : importanceRuleOf(served.importance_rule);
  return (
    <Widget
      id="importance-rule"
      size={module.size}
      kicker="Règle versionnée"
      title={module.title}
      titleId="vx-cal-rule-title"
      state={state}
      {...(view === null ? {} : { action: <code>{view.version ?? 'non publiée'}</code> })}
      footer={<>l’interface n’attribue aucune importance : elle affiche le rang et le code que le worker a appliqués</>}
    >
      {view === null ? (
        <AgendaAbsence state={state} />
      ) : (
        <div className="vx-cal-rule" data-testid="cal-importance-rule">
          <p className="vx-module-sentence">
            Règle d’importance versionnée : <code>{view.version ?? 'non publiée'}</code>
          </p>
          <div className="vx-cal-scroll" tabIndex={0} role="region" aria-label="Rangs de la règle d’importance publiée">
            <table className="vx-matrix-table">
              <caption>Rangs documentés de la règle publiée.</caption>
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
                      {entry.rank ?? <span className="vx-cell-absent">non publié</span>}
                    </th>
                    <td>
                      <code>{entry.code ?? 'non publié'}</code>
                    </td>
                    <td>
                      {entry.description ?? (
                        <span className="vx-cell-absent">description non publiée</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function CountersModule({ served, state }: { readonly served: CalendarResponse | null; readonly state: ModuleState }) {
  const module = calendarModule('counters');
  return (
    <Widget
      id="counters"
      size={module.size}
      kicker="Deux comptages publiés"
      title={module.title}
      titleId="vx-cal-counters-title"
      state={state}
      footer={<>la liste réellement servie (après fenêtre) et les totaux du snapshot entier ne se remplacent jamais</>}
    >
      {served === null ? <AgendaAbsence state={state} /> : <CountersTable served={served} />}
    </Widget>
  );
}

function CountersTable({ served }: { readonly served: CalendarResponse }) {
  const windowEcho = served.window;
  const servedCategories = counterMapOf(windowEcho.categories);
  const servedStatuses = counterMapOf(windowEcho.statuses);
  const totalCategories = counterMapOf(served.categories);
  const totalStatuses = counterMapOf(served.statuses);
  return (
    <div className="vx-cal-counters" data-testid="cal-counters">
      <div className="vx-cal-scroll" tabIndex={0} role="region" aria-label="Compteurs de la liste servie et totaux du snapshot">
        <table className="vx-matrix-table">
          <caption>Deux comptages DISTINCTS publiés par le serveur : liste servie (fenêtre appliquée) et totaux du snapshot.</caption>
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
            {[...new Set([...servedCategories.keys(), ...totalCategories.keys()])].sort().map((category) => (
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

// ---------------------------------------------------------------------------

export function ProvenanceModule({ served, state }: { readonly served: CalendarResponse | null; readonly state: ModuleState }) {
  const module = calendarModule('provenance');
  const coverage = (served?.coverage ?? {}) as Record<string, unknown>;
  const superseded = coverage['events_superseded'];
  const considered = coverage['observations_considered'];
  const stale = coverage['events_stale'];
  return (
    <Widget
      id="provenance"
      size={module.size}
      kicker="Snapshot publié"
      title={module.title}
      titleId="vx-cal-provenance-title"
      state={state}
      footer={<>fenêtre bornée par le serveur ; observations, supplantés et périmés comptés par le worker</>}
    >
      {served === null ? (
        <AgendaAbsence state={state} />
      ) : (
        <>
          <dl className="vx-inspector-facts">
            <div>
              <dt>Snapshot</dt>
              <dd>
                v{served.snapshot_version ?? 'non publiée'} · {served.as_of !== null ? <time dateTime={served.as_of}>{served.as_of}</time> : 'as_of non publié'}
              </dd>
            </div>
            <div>
              <dt>Population</dt>
              <dd>
                <code>{served.population ?? 'non publiée'}</code>
              </dd>
            </div>
            <div>
              <dt>État servi</dt>
              <dd>
                <code>{served.state}</code>
              </dd>
            </div>
          </dl>
          <p className="vx-cal-provenance" data-testid="cal-provenance">
            Snapshot version <code>{served.snapshot_version ?? 'non publiée'}</code> — publié{' '}
            {served.as_of === null ? (
              <span className="vx-cell-absent">instant non publié</span>
            ) : (
              <time dateTime={served.as_of}>{served.as_of}</time>
            )}{' '}
            — population <code>{served.population ?? 'non publiée'}</code> — fenêtre bornée à{' '}
            <span className="vx-num">{served.window.max_days}</span> jours — observations
            considérées{' '}
            {typeof considered === 'number' ? (
              <span className="vx-num">{considered}</span>
            ) : (
              <span className="vx-cell-absent">nombre non publié</span>
            )}{' '}
            — enregistrements supplantés{' '}
            {typeof superseded === 'number' ? (
              <span className="vx-num">{superseded}</span>
            ) : (
              <span className="vx-cell-absent">nombre non publié</span>
            )}{' '}
            — événements périmés{' '}
            {typeof stale === 'number' ? (
              <span className="vx-num">{stale}</span>
            ) : (
              <span className="vx-cell-absent">nombre non publié</span>
            )}
          </p>
        </>
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

/** Fuseaux proposés : ceux PUBLIÉS par les événements servis, UTC, et le fuseau du navigateur s'il est résolu. */
export function timeZoneChoicesOf(events: readonly CalendarEventView[], viewerTimeZone: string | null): readonly string[] {
  const zones = new Set<string>([UTC]);
  if (viewerTimeZone !== null) {
    zones.add(viewerTimeZone);
  }
  for (const event of events) {
    if (event.exchangeTimezone !== null) {
      zones.add(event.exchangeTimezone);
    }
  }
  return [...zones].sort((left, right) => (left === UTC ? -1 : right === UTC ? 1 : left.localeCompare(right)));
}

export function TimezoneModule({
  events,
  viewerTimeZone,
  displayTimeZone,
  onChange,
  state,
}: {
  readonly events: readonly CalendarEventView[] | null;
  readonly viewerTimeZone: string | null;
  readonly displayTimeZone: string;
  readonly onChange: (timeZone: string) => void;
  readonly state: ModuleState;
}) {
  const module = calendarModule('timezone');
  const choices = timeZoneChoicesOf(events ?? [], viewerTimeZone);
  return (
    <Widget
      id="timezone"
      size={module.size}
      kicker="Conversion explicite"
      title={module.title}
      titleId="vx-cal-tz-title"
      /*
       * MODULE DE CONTRÔLE — `state="ready"` littéral, comme la fenêtre servie.
       * Le fuseau d'affichage est un choix DE L'UTILISATEUR : le masquer parce
       * que l'agenda est hors ligne ou périmé retirerait le réglage au moment
       * où la page en a le plus besoin, et `Widget` ne rend aucun enfant hors
       * des états qui montrent du contenu. L'état de l'agenda reste DIT dans
       * le corps (`AgendaAbsence`), et la liste des fuseaux proposés se
       * dégrade seule : sans événement servi, il ne reste qu'UTC et le fuseau
       * du navigateur.
       */
      state="ready"
      footer={<>l’instant UTC publié reste affiché ; la conversion se fait dans un fuseau IANA nommé, jamais deviné</>}
    >
      {events === null ? <AgendaAbsence state={state} /> : null}
      <label className="vx-cal-tz-label">
        Fuseau d’affichage
        <select
          name="tz"
          value={choices.includes(displayTimeZone) ? displayTimeZone : UTC}
          data-testid="cal-tz-select"
          onChange={(bubble) => {
            onChange(bubble.target.value);
          }}
        >
          {choices.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
              {zone === viewerTimeZone ? ' (navigateur)' : ''}
            </option>
          ))}
        </select>
      </label>
      <p className="vx-module-sentence" data-testid="cal-tz-note">
        {events === null || events.length === 0
          ? 'Fuseaux proposés : UTC et le fuseau du navigateur.'
          : `${choices.length} fuseau(x) proposé(s) : UTC, le fuseau du navigateur et les fuseaux de place publiés par les événements servis.`}
      </p>
    </Widget>
  );
}

// ---------------------------------------------------------------------------

/**
 * Dénombrement d'événements SERVIS par journée UTC, en entrées de `DayBars`
 * (forme « rail derrière les barres », ADR-017).
 *
 * Ce n'est pas un calcul financier : c'est un DÉNOMBREMENT de la liste servie,
 * la même opération que la table équivalente rend visible ligne à ligne. Aucun
 * pourcentage n'est écrit — il n'est pas publié, et l'écrire serait le
 * calculer. Les journées sans événement servi n'entrent pas dans la figure :
 * une barre nulle affirmerait un zéro que le serveur n'a pas publié.
 *
 * `shortLabel` rend l'abscisse `MM-JJ` ; le jour complet reste dans l'infobulle
 * ET dans la table équivalente. ADR-017 interdit d'abréger une VALEUR, pas une
 * date d'axe.
 */
function dayBarsOf(events: readonly CalendarEventView[]): readonly DayBarEntry[] {
  const counts = new Map<string, number>();
  for (const event of events) {
    const day = groupKeyOf(event.eventTimeUtc, 'day');
    counts.set(day, (counts.get(day) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((left, right) => left[0].localeCompare(right[0]))
    .map(([key, count]) => ({ key, label: key, value: String(count), shortLabel: key.slice(5) }));
}

export function DensityModule({ events, state }: { readonly events: readonly CalendarEventView[] | null; readonly state: ModuleState }) {
  const module = calendarModule('density');
  return (
    <Widget
      id="density"
      size={module.size}
      kicker="Dénombrement par journée UTC"
      title={module.title}
      titleId="vx-cal-density-title"
      state={state}
      footer={<>événements servis par journée UTC ; les journées sans événement ne sont pas inventées</>}
    >
      {events === null ? (
        <AgendaAbsence state={state} />
      ) : (
        <DayBars
          entries={dayBarsOf(events)}
          unit="événements servis"
          ariaLabel="Événements servis par journée UTC"
          emptyLabel="Aucun événement servi."
        />
      )}
    </Widget>
  );
}

export function DailyExposureModule({ events, state }: { readonly events: readonly CalendarEventView[] | null; readonly state: ModuleState }) {
  const module = calendarModule('daily-exposure');
  const exposed = events === null ? null : events.filter((event) => event.context.positions.length > 0);
  return (
    <Widget
      id="daily-exposure"
      size={module.size}
      kicker="Registre manuel"
      title={module.title}
      titleId="vx-cal-exposure-title"
      state={state}
      footer={<>événements dont le contexte croisé nomme une position déclarée par vous ; aucun montant, aucun poids</>}
    >
      {exposed === null ? (
        <AgendaAbsence state={state} />
      ) : (
        <DayBars
          entries={dayBarsOf(exposed)}
          unit="événements servis"
          ariaLabel="Événements liés à une position déclarée, par journée UTC"
          emptyLabel="Aucun événement servi ne touche une position déclarée."
        />
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function NextEventModule({
  events,
  displayTimeZone,
  state,
}: {
  readonly events: readonly CalendarEventView[] | null;
  readonly displayTimeZone: string;
  readonly state: ModuleState;
}) {
  const module = calendarModule('next-event');
  const first = events === null ? null : (events[0] ?? null);
  const reading = first === null ? null : formatInTimeZone(first.eventTimeUtc, displayTimeZone);
  return (
    <Widget
      id="next-event"
      size={module.size}
      kicker="Premier de l’ordre publié"
      title={module.title}
      titleId="vx-cal-next-title"
      state={state}
      footer={<>aucun compte à rebours : une horloge vivante n’est pas une donnée servie</>}
    >
      {events === null ? (
        <AgendaAbsence state={state} />
      ) : first === null ? (
        <p className="vx-module-sentence" role="status" data-testid="cal-next-empty">
          Aucun événement servi dans la sélection.
        </p>
      ) : (
        <div data-testid="cal-next">
          <p className="vx-cal-next-title">
            {first.title ?? first.eventId} <EventStatusBadge status={first.status} />
          </p>
          <ul className="vx-agenda-mini" aria-label="Prochain événement">
            <AgendaLine event={first} />
          </ul>
          <p className="vx-module-sentence">
            Dans le fuseau <code>{displayTimeZone}</code> : {reading !== null ? <span className="vx-num">{reading}</span> : <span className="vx-cell-absent">conversion impossible</span>}
            {' · '}importance rang {first.importance.rank ?? 'non publié'} (
            <code>{first.importance.code ?? 'non publié'}</code>)
          </p>
        </div>
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function RevisionsModule({ events, state }: { readonly events: readonly CalendarEventView[] | null; readonly state: ModuleState }) {
  const module = calendarModule('revisions');
  const revised = events === null ? [] : events.filter((event) => event.revised);
  return (
    <Widget
      id="revisions"
      size={module.size}
      kicker="Publiées par la source"
      title={module.title}
      titleId="vx-cal-revisions-title"
      state={state}
      footer={<>drapeau et détail sont deux champs distincts du snapshot ; les valeurs antérieures restent lisibles dans l’agenda</>}
    >
      {events === null ? (
        <AgendaAbsence state={state} />
      ) : (
        <>
          <Metric label="Événements révisés" value={String(revised.length)} note={`sur ${events.length} servi(s)`} testId="cal-revisions-count" />
          {revised.length > 0 ? (
            <ul className="vx-inspector-list" data-testid="cal-revisions">
              {revised.map((event) => (
                <li key={event.eventId}>
                  <code>{event.ticker ?? event.eventId}</code> {event.title ?? ''}
                  <span className="vx-inspector-unit"> — {event.revisions.length > 0 ? `${event.revisions.length} révision(s) publiée(s)` : 'détail non publié'}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </Widget>
  );
}

export function ConflictsModule({ events, state }: { readonly events: readonly CalendarEventView[] | null; readonly state: ModuleState }) {
  const module = calendarModule('conflicts');
  const conflicting = events === null ? [] : events.filter((event) => event.versionState === VERSION_STATE_CONFLICTING);
  const rejected = events === null ? [] : events.filter((event) => event.rejectedRevisions.length > 0);
  return (
    <Widget
      id="conflicts"
      size={module.size}
      kicker="Publiés par le worker"
      title={module.title}
      titleId="vx-cal-conflicts-title"
      state={state}
      footer={<>un conflit n’est jamais résolu ici ; la version affichée suit l’ordre stable publié</>}
    >
      {events === null ? (
        <AgendaAbsence state={state} />
      ) : (
        <div className="vx-metrics-row" data-testid="cal-conflicts">
          <Metric label="Versions en conflit" value={String(conflicting.length)} size="compact" testId="cal-conflicts-versions" />
          <Metric label="Révisions rejetées" value={String(rejected.length)} size="compact" testId="cal-conflicts-rejected" />
        </div>
      )}
    </Widget>
  );
}
