import { Link } from 'react-router-dom';

import type { CalendarResponse } from '../../api/client.ts';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { EventStatusBadge } from './EventAgenda.tsx';
import { VERSION_STATE_CONFLICTING, categoryLabelOf, formatInTimeZone } from './calendarView.ts';
import type { CalendarEventView } from './calendarView.ts';

/**
 * Inspecteur de la page Calendrier (planche §11 : « événement, source,
 * fuseau, statut et instruments concernés »).
 *
 * Deux contenus, un panneau à la fois : l'ÉVÉNEMENT ouvert depuis l'agenda —
 * statut, importance publiée, trois lectures du temps (UTC publié, place,
 * fuseau d'affichage), fraîcheur, source et droits, instruments et positions
 * déclarées, thèses et liens, versions et révisions — sinon la vérité du
 * snapshot. Les « chiffres » de la planche (actuel, consensus, précédent,
 * surprise) ne sont pas publiés : ils sont dits non publiés, jamais
 * inventés.
 */

export function EventInspector({
  event,
  displayTimeZone,
  onClose,
}: {
  readonly event: CalendarEventView;
  readonly displayTimeZone: string;
  readonly onClose: () => void;
}) {
  const reading = formatInTimeZone(event.eventTimeUtc, displayTimeZone);
  return (
    <InspectorPanel subject={event.ticker ?? event.eventId}>
      <div className="vx-sheet-head">
        <p className="vx-inspector-note">
          {event.title ?? event.eventId} <EventStatusBadge status={event.status} />
          {event.synthetic ? <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span> : null}
        </p>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>

      <SnapshotFacts
        testId="cal-event-facts"
        facts={[
          { label: 'Catégorie', value: `${categoryLabelOf(event.category)} (${event.category})` },
          { label: 'Statut de date', value: <code>{event.status}</code> },
          {
            label: 'Importance',
            value: `rang ${publishedOr(event.importance.rank)} · code ${publishedOr(event.importance.code)} · règle ${publishedOr(event.importance.ruleVersion)}`,
          },
          {
            label: 'Instant UTC publié',
            value: (
              <time dateTime={event.eventTimeUtc} className="vx-num">
                {event.eventTimeUtc}
              </time>
            ),
          },
          {
            label: 'Heure de place',
            value:
              event.eventTimeLocal === null ? (
                'non publiée'
              ) : (
                <>
                  <span className="vx-num">{event.eventTimeLocal}</span> <code>{publishedOr(event.exchangeTimezone)}</code>
                </>
              ),
          },
          {
            label: `Fuseau d’affichage (${displayTimeZone})`,
            value: reading === null ? 'conversion impossible' : <span className="vx-num">{reading}</span>,
          },
          {
            label: 'Fraîcheur',
            value: (
              <>
                <FreshnessBadge ageSeconds={null} sourceLabel={event.source ?? 'source non publiée'} />{' '}
                {event.fresh === true ? 'fraîche' : event.fresh === false ? 'périmée' : 'non publiée'} · péremption {publishedOr(event.staleAfter)} · retard{' '}
                <code>{publishedOr(event.delayStatus)}</code>
              </>
            ),
          },
          {
            label: 'Source et droits',
            value: (
              <>
                <code>{publishedOr(event.source)}</code> · droit <code>{publishedOr(event.rights)}</code> · qualité <code>{publishedOr(event.quality)}</code>
                {event.sourceEventId !== null ? <span className="vx-inspector-unit"> · {event.sourceEventId}</span> : null}
              </>
            ),
          },
          { label: 'Chiffres publiés', value: 'actuel, consensus, précédent et surprise non publiés' },
          {
            label: 'Instrument',
            value: event.ticker !== null ? <code>{event.ticker}</code> : `portée ${publishedOr(event.scope)}`,
          },
          {
            label: 'Positions déclarées',
            value: event.context.positions.length === 0 ? 'aucune' : event.context.positions.map((identifier) => `#${identifier}`).join(', '),
          },
          {
            label: 'Thèses',
            value:
              event.context.theses.length === 0
                ? 'aucune'
                : event.context.theses.map(
                    (thesis) =>
                      `#${thesis.thesisId ?? 'identifiant non publié'} ${
                        thesis.title ?? 'sans titre'
                      } (${thesis.status ?? 'statut non publié'})`,
                  ).join(' ; '),
          },
          {
            label: 'Versions et révisions',
            value: `${event.versionState === VERSION_STATE_CONFLICTING ? `${event.conflictingVersions.length} version(s) en conflit` : 'aucun conflit publié'} · ${event.revised ? `révisé (${event.revisions.length} détail(s))` : 'non révisé'} · ${event.rejectedRevisions.length} révision(s) rejetée(s)`,
          },
          ...(event.amount !== null ? [{ label: 'Montant publié', value: `${event.amount} ${event.currency ?? ''}` }] : []),
          ...(event.expiration !== null ? [{ label: 'Expiration publiée', value: <code>{event.expiration}</code> }] : []),
        ]}
      />

      {event.context.links.length > 0 ? (
        <ul className="vx-inspector-list" data-testid="cal-event-links">
          {event.context.links.map((link) => (
            <li key={`${link.rel}-${link.resource}`}>
              <code>{link.rel}</code> → <code>{link.resource}</code>
            </li>
          ))}
        </ul>
      ) : null}
      {event.ticker !== null ? (
        <p className="vx-inspector-note">
          <Link to={`/analysis/${encodeURIComponent(event.ticker)}`}>Ouvrir le dossier d’analyse</Link>
        </p>
      ) : null}
    </InspectorPanel>
  );
}

export function CalendarSnapshotInspector({
  served,
  shown,
  total,
}: {
  readonly served: CalendarResponse | null;
  readonly shown: number;
  readonly total: number;
}) {
  return (
    <InspectorPanel subject="Snapshot publié">
      <SnapshotFacts
        testId="cal-snapshot-facts"
        facts={
          served === null
            ? [{ label: 'Agenda', value: 'aucun agenda servi' }]
            : [
                { label: 'État servi', value: <code>{served.state}</code> },
                { label: 'Snapshot', value: `v${publishedOr(served.snapshot_version)}` },
                {
                  label: 'as_of',
                  value: served.as_of === null ? 'non publié' : <time dateTime={served.as_of}>{served.as_of}</time>,
                },
                { label: 'Population', value: <code>{publishedOr(served.population)}</code> },
                {
                  label: 'Fenêtre',
                  value: `${publishedOr(served.window.from_utc)} → ${publishedOr(served.window.to_utc)} · bornée à ${served.window.max_days} jours`,
                },
                {
                  label: 'Événements',
                  value: `${served.window.events_in_window} servi(s) · ${served.window.events_total} au snapshot · ${shown} affiché(s) sur ${total} après filtres`,
                },
                ...(served.reason === null ? [] : [{ label: 'Raison serveur', value: <code>{served.reason}</code> }]),
              ]
        }
      />
      <p className="vx-inspector-note">
        Sélectionner un événement (bouton « Inspecter » dans l’agenda) pour lire sa source, ses trois lectures du temps,
        son statut et les instruments concernés.
      </p>
    </InspectorPanel>
  );
}
