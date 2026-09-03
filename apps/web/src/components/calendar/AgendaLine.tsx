import {
  formatInTimeZone,
  statusLabelOf,
  statusMarkOf,
} from '../../pages/calendar/calendarView.ts';
import type { CalendarEventView } from '../../pages/calendar/calendarView.ts';

/**
 * Heure d'un événement dans le fuseau de SA place, lisible. La chaîne brute
 * reste dans `dateTime` ; sans fuseau publié, la chaîne locale serveur est
 * montrée telle quelle — jamais convertie dans un fuseau deviné.
 */
export function readableEventTime(event: CalendarEventView): string {
  if (event.exchangeTimezone !== null) {
    const rendu = formatInTimeZone(event.eventTimeUtc, event.exchangeTimezone);
    if (rendu !== null) {
      return rendu;
    }
  }
  return event.eventTimeLocal ?? event.eventTimeUtc;
}

/**
 * Une ligne d'agenda compacte : heure de place, instrument, titre, statut.
 * Chaînes serveur verbatim ; le badge SYNTHÉTIQUE suit l'événement.
 *
 * Extraite de `TodayModules.tsx` au LOT-A4 (Analyse et, plus tard,
 * Simulateur et Portefeuille listent des événements de la même façon).
 */
export function AgendaLine({ event }: { readonly event: CalendarEventView }) {
  return (
    <li className="vx-agenda-line" data-status={event.status}>
      <span className="vx-agenda-time">
        <time dateTime={event.eventTimeUtc}>{readableEventTime(event)}</time>
        {event.exchangeTimezone === null ? null : (
          <span className="vx-agenda-tz"> {event.exchangeTimezone}</span>
        )}
      </span>
      <span className="vx-agenda-ticker">
        {event.ticker === null ? (
          <span className="vx-cell-absent">sans instrument</span>
        ) : (
          <code>{event.ticker}</code>
        )}
      </span>
      <span className="vx-agenda-title">{event.title ?? 'titre non publié'}</span>
      <span className="vx-agenda-status">
        <span aria-hidden="true">{statusMarkOf(event.status)}</span> {statusLabelOf(event.status)}
        {event.synthetic ? <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span> : null}
      </span>
    </li>
  );
}
