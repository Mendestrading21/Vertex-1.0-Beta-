import { Link } from 'react-router-dom';

import {
  CONFIRMED_STATUS,
  ESTIMATED_STATUS,
  VERSION_STATE_CONFLICTING,
  categoryLabelOf,
  formatInTimeZone,
  groupAgenda,
  statusLabelOf,
  statusMarkOf,
} from './calendarView.ts';
import type { AgendaGrouping, CalendarEventView } from './calendarView.ts';

/**
 * Composant dominant de la page Calendrier : l'agenda jour/semaine. LOT-A7 :
 * il est le CORPS de la carte dominante portée par la page (planche §11) ;
 * chaque carte d'événement peut ouvrir l'inspecteur (« Inspecter »).
 *
 * Invariants d'affichage :
 * - « Estimé » et « Confirmé » ne partagent JAMAIS le même libellé : badge,
 *   marqueur textuel et phrase de statut sont distincts, et la couleur n'est
 *   jamais le seul porteur de la distinction ;
 * - un événement révisé ouvre un détail dépliable où les valeurs
 *   ANTÉRIEURES (statut et instant) restent lisibles — rien n'est effacé ;
 * - les trois lectures du temps sont montrées séparément et étiquetées :
 *   instant UTC publié, heure locale de la place avec son fuseau IANA, puis
 *   la même instant rendu dans le fuseau du lecteur (étiqueté avec ce
 *   fuseau) — aucune conversion implicite ;
 * - fraîcheur, importance (rang + code + version de règle) et contexte croisé
 *   (position, thèse, liens) proviennent du snapshot, jamais d'un calcul.
 */

export const STATUS_DESCRIPTIONS: Readonly<Record<string, string>> = {
  [ESTIMATED_STATUS]: 'date estimée par la source, non confirmée',
  [CONFIRMED_STATUS]: 'date confirmée par la source',
};

export function EventStatusBadge({ status }: { readonly status: string }) {
  return (
    <span className="vx-cal-status" data-status={status}>
      <span aria-hidden="true" className="vx-cal-status-mark">
        {statusMarkOf(status)}
      </span>
      <span className="vx-cal-status-label">{statusLabelOf(status)}</span>
    </span>
  );
}

function TimeReadings({
  event,
  viewerTimeZone,
}: {
  readonly event: CalendarEventView;
  readonly viewerTimeZone: string | null;
}) {
  const viewerReading =
    viewerTimeZone === null ? null : formatInTimeZone(event.eventTimeUtc, viewerTimeZone);
  return (
    <dl className="vx-cal-times" data-testid={`cal-times-${event.eventId}`}>
      <div>
        <dt>Instant UTC (publié)</dt>
        <dd>
          <time dateTime={event.eventTimeUtc}>{event.eventTimeUtc}</time>
        </dd>
      </div>
      <div>
        <dt>Heure locale de la place</dt>
        <dd>
          {event.eventTimeLocal !== null ? (
            <time dateTime={event.eventTimeLocal}>{event.eventTimeLocal}</time>
          ) : (
            <span className="vx-cell-absent">non publiée</span>
          )}{' '}
          <span className="vx-cal-tz">
            fuseau de place :{' '}
            {event.exchangeTimezone !== null ? (
              <code>{event.exchangeTimezone}</code>
            ) : (
              <span className="vx-cell-absent">non publié</span>
            )}
          </span>
        </dd>
      </div>
      <div>
        <dt>Votre fuseau{viewerTimeZone !== null ? <> (<code>{viewerTimeZone}</code>)</> : null}</dt>
        <dd>
          {viewerReading !== null ? (
            <span className="vx-num">{viewerReading}</span>
          ) : (
            <span className="vx-cell-absent">fuseau du navigateur non résolu</span>
          )}
        </dd>
      </div>
    </dl>
  );
}

/**
 * Deux faits que le worker publie QUAND il les a : des versions en conflit à
 * égalité de chronologie, et des révisions déclarées refusées avec leur
 * raison. Aucun des deux n'est masqué ; leur ABSENCE du snapshot n'invente
 * aucun état (rien n'est affiché plutôt qu'un « RESOLVED » supposé).
 */
export function VersionState({ event }: { readonly event: CalendarEventView }) {
  if (event.versionState === null && event.rejectedRevisions.length === 0) {
    return null;
  }
  const conflicting = event.versionState === VERSION_STATE_CONFLICTING;
  return (
    <div className="vx-cal-version" data-testid={`cal-version-${event.eventId}`}>
      {event.versionState !== null ? (
        <p
          className="vx-cal-version-state"
          data-version-state={event.versionState}
          role={conflicting ? 'status' : undefined}
        >
          <span aria-hidden="true">{conflicting ? '⚠' : '●'}</span> État de version :{' '}
          <code>{event.versionState}</code>
          {conflicting
            ? ' — plusieurs versions se contredisent à égalité de chronologie ; la version affichée est choisie par un ordre stable dérivé des valeurs, jamais par un identifiant.'
            : null}
        </p>
      ) : null}
      {event.conflictingVersions.length > 0 ? (
        <ul className="vx-cal-version-list">
          {event.conflictingVersions.map((version) => (
            <li key={version.sourceEventId ?? `${version.asOf}-${version.eventTimeUtc}`}>
              Version en conflit — statut{' '}
              {version.status !== null ? statusLabelOf(version.status) : 'non publié'} — instant{' '}
              <code>{version.eventTimeUtc ?? 'non publié'}</code> — reçue{' '}
              <code>{version.asOf ?? 'non publiée'}</code>
            </li>
          ))}
        </ul>
      ) : null}
      {event.rejectedRevisions.length > 0 ? (
        <ul className="vx-cal-version-list" data-testid={`cal-rejected-revisions-${event.eventId}`}>
          {event.rejectedRevisions.map((rejected, position) => (
            <li
              // La liste arrive entière dans un DTO, est remplacée en bloc et n'est jamais triée, filtrée ni insérée côté client : aucun
              // réordonnancement local n'est possible. L'index seul serait insuffisant ; le contenu seul pourrait se répéter.
              // biome-ignore lint/suspicious/noArrayIndexKey: la clé n'est PAS l'index seul, elle concatène l'index ET le contenu publié par le serveur.
              key={`${position}-${rejected.reason ?? ''}`}
            >
              <span aria-hidden="true">⊘</span> Révision déclarée REFUSÉE —{' '}
              <code>{rejected.reason ?? 'raison non publiée'}</code>
              {rejected.revisedAt !== null ? (
                <>
                  {' '}
                  (datée <code>{rejected.revisedAt}</code>)
                </>
              ) : null}{' '}
              — l’événement reste affiché, seule la révision est écartée.
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function RevisionDetails({ event }: { readonly event: CalendarEventView }) {
  if (!event.revised) {
    return (
      <p className="vx-cal-norevision" data-testid={`cal-norevision-${event.eventId}`}>
        Aucune révision publiée pour cet événement.
      </p>
    );
  }
  return (
    <details className="vx-cal-revision" data-testid={`cal-revision-${event.eventId}`}>
      <summary>
        Révisé — voir les valeurs antérieures ({event.previousValues.length} enregistrement
        {event.previousValues.length > 1 ? 's' : ''} supplanté
        {event.previousValues.length > 1 ? 's' : ''}, {event.revisions.length} révision
        {event.revisions.length > 1 ? 's' : ''} déclarée{event.revisions.length > 1 ? 's' : ''})
      </summary>
      {event.previousValues.length > 0 ? (
        <div
          className="vx-cal-scroll"
          tabIndex={0}
          role="region"
          aria-label="Enregistrements supplantés, valeurs antérieures conservées"
        >
        <table className="vx-matrix-table vx-cal-revision-table">
          <caption>
            Enregistrements supplantés, conservés lisibles : leur statut et leur instant
            antérieurs ne sont jamais effacés.
          </caption>
          <thead>
            <tr>
              <th scope="col">Statut antérieur</th>
              <th scope="col">Instant antérieur (UTC)</th>
              <th scope="col">Reçu le (as_of)</th>
              <th scope="col">Source</th>
            </tr>
          </thead>
          <tbody>
            {event.previousValues.map((previous) => (
              <tr key={previous.sourceEventId ?? `${previous.asOf}-${previous.eventTimeUtc}`}>
                <td data-testid={`cal-previous-status-${event.eventId}`}>
                  {previous.status !== null ? (
                    <EventStatusBadge status={previous.status} />
                  ) : (
                    <span className="vx-cell-absent">non publié</span>
                  )}
                </td>
                <td data-testid={`cal-previous-time-${event.eventId}`}>
                  {previous.eventTimeUtc !== null ? (
                    <time dateTime={previous.eventTimeUtc}>{previous.eventTimeUtc}</time>
                  ) : (
                    <span className="vx-cell-absent">non publié</span>
                  )}
                </td>
                <td>
                  {previous.asOf !== null ? (
                    <time dateTime={previous.asOf}>{previous.asOf}</time>
                  ) : (
                    <span className="vx-cell-absent">non publié</span>
                  )}
                </td>
                <td>
                  <code>{previous.source ?? 'source non publiée'}</code>
                  {previous.sourceEventId !== null ? (
                    <>
                      {' '}
                      <code>{previous.sourceEventId}</code>
                    </>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      ) : (
        <p className="vx-cal-norevision">
          Aucun enregistrement supplanté : la révision est déclarée par la source elle-même.
        </p>
      )}
      {event.revisions.length > 0 ? (
        <div
          className="vx-cal-scroll"
          tabIndex={0}
          role="region"
          aria-label="Révisions déclarées par la source"
        >
        <table className="vx-matrix-table vx-cal-revision-table">
          <caption>Révisions déclarées par la source, valeurs antérieures conservées.</caption>
          <thead>
            <tr>
              <th scope="col">Révisé le</th>
              <th scope="col">Statut antérieur</th>
              <th scope="col">Instant antérieur (UTC)</th>
              <th scope="col">Motif déclaré</th>
            </tr>
          </thead>
          <tbody>
            {event.revisions.map((revision) => (
              <tr key={`${revision.revisedAt}-${revision.previousEventTimeUtc}`}>
                <td>
                  {revision.revisedAt !== null ? (
                    <time dateTime={revision.revisedAt}>{revision.revisedAt}</time>
                  ) : (
                    <span className="vx-cell-absent">non publié</span>
                  )}
                </td>
                <td data-testid={`cal-declared-previous-status-${event.eventId}`}>
                  {revision.previousStatus !== null ? (
                    <EventStatusBadge status={revision.previousStatus} />
                  ) : (
                    <span className="vx-cell-absent">non publié</span>
                  )}
                </td>
                <td data-testid={`cal-declared-previous-time-${event.eventId}`}>
                  {revision.previousEventTimeUtc !== null ? (
                    <time dateTime={revision.previousEventTimeUtc}>
                      {revision.previousEventTimeUtc}
                    </time>
                  ) : (
                    <span className="vx-cell-absent">non publié</span>
                  )}
                </td>
                <td>{revision.reason ?? <span className="vx-cell-absent">non publié</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      ) : null}
    </details>
  );
}

export function EventContext({ event }: { readonly event: CalendarEventView }) {
  const { positions, theses, links } = event.context;
  if (positions.length === 0 && theses.length === 0 && links.length === 0) {
    return (
      <p className="vx-cal-context" data-testid={`cal-context-${event.eventId}`}>
        Contexte croisé : aucune position déclarée, aucune thèse, aucun lien publié.
      </p>
    );
  }
  return (
    <div className="vx-cal-context" data-testid={`cal-context-${event.eventId}`}>
      <p className="vx-cal-context-title">Contexte croisé publié</p>
      <ul>
        {positions.length > 0 ? (
          <li>
            Position manuelle déclarée dans le portefeuille{' '}
            {positions.map((identifier) => (
              <code key={identifier}>#{identifier}</code>
            ))}{' '}
            — <Link to="/portfolio">ouvrir le portefeuille</Link>
          </li>
        ) : (
          <li>Aucune position manuelle déclarée sur cet instrument.</li>
        )}
        {theses.length > 0 ? (
          theses.map((thesis) => (
            <li key={thesis.thesisId ?? thesis.title}>
              Thèse <code>#{thesis.thesisId ?? 'identifiant non publié'}</code> «{' '}
              {thesis.title ?? 'sans titre'} » — statut{' '}
              <code>{thesis.status ?? 'non publié'}</code>{' '}
              <Link to="/follow-up">ouvrir le suivi</Link>
            </li>
          ))
        ) : (
          <li>Aucune thèse utilisateur rattachée.</li>
        )}
        {links.map((link) => (
          <li key={`${link.rel}-${link.resource}`}>
            Lien <code>{link.rel}</code> → <code>{link.resource}</code>
            {link.rel === 'analysis' && event.ticker !== null ? (
              <>
                {' '}
                <Link to={`/analysis/${encodeURIComponent(event.ticker)}`}>ouvrir l’analyse</Link>
              </>
            ) : null}
            {link.rel === 'option_chain' && event.ticker !== null ? (
              <>
                {' '}
                <Link to={`/options/${encodeURIComponent(event.ticker)}`}>ouvrir les options</Link>
              </>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function EventCard({
  event,
  viewerTimeZone,
  selected = false,
  onInspect,
}: {
  readonly event: CalendarEventView;
  readonly viewerTimeZone: string | null;
  readonly selected?: boolean;
  readonly onInspect?: (eventId: string) => void;
}) {
  return (
    <li
      className="vx-cal-event"
      data-testid={`cal-event-${event.eventId}`}
      data-status={event.status}
      {...(selected ? { 'data-selected': 'true' } : {})}
    >
      <div className="vx-cal-event-head" data-testid={`cal-head-${event.eventId}`}>
        <h4 className="vx-cal-event-title">{event.title ?? event.eventId}</h4>
        <EventStatusBadge status={event.status} />
        {onInspect !== undefined ? (
          <button
            type="button"
            className="vx-opp-inspect"
            aria-pressed={selected}
            aria-label={`Inspecter ${event.title ?? event.eventId}`}
            onClick={() => {
              onInspect(event.eventId);
            }}
          >
            Inspecter
          </button>
        ) : null}
      </div>
      <p className="vx-cal-event-meta">
        <span className="vx-cal-category" data-category={event.category}>
          {categoryLabelOf(event.category)}
        </span>
        {' · '}
        {event.ticker !== null ? (
          <code>{event.ticker}</code>
        ) : (
          <span>portée {event.scope ?? 'non publiée'}</span>
        )}
        {' · '}
        <span data-testid={`cal-importance-${event.eventId}`}>
          Importance rang {event.importance.rank ?? 'non publié'} — code{' '}
          <code>{event.importance.code ?? 'non publié'}</code> (règle{' '}
          <code>{event.importance.ruleVersion ?? 'non publiée'}</code>)
        </span>
      </p>
      {/* LOT P6a — CE QUI RESTE DANS LA LIGNE, ET POURQUOI. Les TROIS LECTURES
          DU TEMPS restent : elles sont l'essence d'un calendrier, et les
          déplacer obligerait à ouvrir chaque événement pour savoir QUAND il a
          lieu. Tout le reste — la description du statut, la fraîcheur, les
          droits, l'archive des révisions, le contexte croisé — vit désormais
          dans l'inspecteur, qui le portait DÉJÀ : la ligne le répétait. */}
      <TimeReadings event={event} viewerTimeZone={viewerTimeZone} />
      {event.versionState === VERSION_STATE_CONFLICTING ? (
        // UNE EXCEPTION, ET UNE SEULE. Des versions qui se contredisent ne
        // peuvent pas attendre l'ouverture d'un panneau : le lecteur doit
        // savoir, en parcourant la liste, que cet événement est en conflit.
        // Le DÉTAIL du conflit, lui, est dans l'inspecteur.
        <p
          className="vx-cal-version-state"
          data-version-state={event.versionState}
          role="status"
          data-testid={`cal-conflict-flag-${event.eventId}`}
        >
          <span aria-hidden="true">⚠</span> Versions en conflit —{' '}
          <code>{event.versionState}</code>
        </p>
      ) : null}
    </li>
  );
}

export interface EventAgendaProps {
  readonly events: readonly CalendarEventView[];
  readonly grouping: AgendaGrouping;
  /** Fuseau IANA d'affichage (troisième lecture du temps) — explicite, jamais deviné. */
  readonly viewerTimeZone: string | null;
  readonly selectedEventId?: string | null;
  readonly onInspect?: (eventId: string) => void;
}

export function EventAgenda({ events, grouping, viewerTimeZone, selectedEventId = null, onInspect }: EventAgendaProps) {
  const groups = groupAgenda(events, grouping);
  if (groups.length === 0) {
    return (
      <p className="vx-matrix-empty" data-testid="cal-agenda-empty">
        Aucun événement ne correspond aux filtres appliqués côté interface. Le snapshot servi
        n’est pas modifié : retirez un filtre pour revoir la liste servie.
      </p>
    );
  }
  return (
    /*
      RÉGION DÉFILANTE BORNÉE (refonte V3). Mesuré sur la capture 1600×1000 :
      la page Calendrier faisait 6 928 px de haut — sept écrans — parce que
      l'agenda déroulait tous ses groupes et tous leurs détails imbriqués. Une
      « zone de travail dense » qui exige sept défilements n'est plus dense :
      plus rien n'y est comparable d'un coup d'œil.

      RIEN N'EST MASQUÉ : la région défile, elle ne tronque pas. Le nombre
      d'événements servis reste le nombre d'événements présents, et chaque
      groupe garde son compte affiché.

      `tabIndex` et `role="region"` sont OBLIGATOIRES ici, pas décoratifs : une
      région défilante inatteignable au clavier est la violation axe
      `scrollable-region-focusable`, impact « serious », sur un seuil déclaré à
      zéro. C'est le défaut exact trouvé sur l'inspecteur au LOT-A1.
    */
    <div
      className="vx-cal-agenda"
      data-testid="cal-agenda"
      data-grouping={grouping}
      tabIndex={0}
      role="region"
      aria-label="Agenda des événements, région défilante"
    >
      {groups.map((group) => (
        <section key={group.key} className="vx-cal-group" aria-labelledby={`vx-cal-group-${group.key}`}>
          <h3 id={`vx-cal-group-${group.key}`} className="vx-cal-group-title">
            {grouping === 'day' ? 'Journée UTC ' : 'Semaine UTC du '}
            <time dateTime={group.key}>{group.key}</time>
            <span className="vx-cal-group-count">
              {' '}
              — {group.events.length} événement{group.events.length > 1 ? 's' : ''}
            </span>
          </h3>
          <ul className="vx-cal-event-list">
            {group.events.map((event) => (
              <EventCard
                key={event.eventId}
                event={event}
                viewerTimeZone={viewerTimeZone}
                selected={event.eventId === selectedEventId}
                {...(onInspect === undefined ? {} : { onInspect })}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
