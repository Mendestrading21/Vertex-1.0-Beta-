/**
 * Catalogue de la planche §11 (Calendrier) —
 * `pages-11-12-calendar-sources-reports.png`, moitié gauche. Chaque module
 * est SERVI par un contrat existant ou DÉCLARÉ absent avec le motif mesuré ;
 * aucun n'est simulé (article 17).
 *
 * Ce que la planche montre et que ce dépôt ne publie pas : des rappels et
 * un « depuis ma dernière visite » (aucun contrat ne mémorise une visite ni
 * n'émet de rappel), un compte à rebours (une horloge vivante n'est pas une
 * donnée servie). Le snapshot `calendar/global` publie l'agenda, sa
 * fenêtre, ses compteurs, sa règle d'importance, ses révisions et ses
 * conflits ; l'interface sélectionne, regroupe et convertit l'instant UTC
 * publié dans un fuseau IANA EXPLICITE — jamais un fuseau deviné.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';

export type CalendarModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface CalendarModule {
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: CalendarModuleStatus;
}

const SNAPSHOT = 'GET /api/v1/calendar';

export const CALENDAR_MODULES: readonly CalendarModule[] = [
  {
    id: 'view-controls',
    title: 'Fenêtre servie et filtres',
    question: 'Quelle fenêtre demander au serveur, et quels événements servis afficher ?',
    status: { kind: 'served', contract: `${SNAPSHOT}?from&to — window.categories / statuses` },
  },
  {
    id: 'timezone',
    title: 'Fuseau d’affichage',
    question: 'Dans quel fuseau lire les instants publiés ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — agenda[].event_time_utc / exchange_timezone (conversion IANA explicite)` },
  },
  {
    id: 'agenda',
    title: 'Agenda',
    question: 'Quels événements peuvent affecter mes instruments et mon portefeuille ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — agenda[] (ordre publié, regroupé par jour ou semaine)` },
  },
  {
    id: 'daily-exposure',
    title: 'Exposition du registre par jour',
    question: 'Quels jours portent des événements liés à une position déclarée ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — agenda[].event_context.positions (dénombrement par jour)` },
  },
  {
    id: 'density',
    title: 'Densité des événements',
    question: 'Quels jours de la fenêtre sont les plus chargés ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — agenda[].event_time_utc (dénombrement par jour)` },
  },
  {
    id: 'next-event',
    title: 'Prochain événement',
    question: 'Quel est le premier événement de l’ordre publié ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — agenda[0] (ordre publié, aucun compte à rebours)` },
  },
  {
    id: 'counters',
    title: 'Compteurs',
    question: 'Combien d’événements la liste servie et le snapshot entier comptent-ils ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — window.events_in_window / events_total / categories / statuses` },
  },
  {
    id: 'importance-rule',
    title: 'Règle d’importance',
    question: 'Quelle règle versionnée a attribué les rangs d’importance ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — importance_rule` },
  },
  {
    id: 'provenance',
    title: 'Provenance',
    question: 'Quel snapshot, quelle population et quelle couverture servent cet agenda ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — snapshot_version / as_of / population / coverage` },
  },
  {
    id: 'revisions',
    title: 'Révisions',
    question: 'Quels événements servis ont été révisés par leur source ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — agenda[].revised / revisions[]` },
  },
  {
    id: 'conflicts',
    title: 'Conflits de version',
    question: 'Quels événements servis portent des versions contradictoires ou des révisions refusées ?',
    status: { kind: 'served', contract: `${SNAPSHOT} — agenda[].version_state / rejected_revisions[]` },
  },
  {
    id: 'reminders',
    title: 'Rappels',
    question: 'De quels événements souhaite-t-on être rappelé ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucun contrat de rappel n’existe ; une préférence enregistrée dans le navigateur ne serait ni servie ni notifiée.',
    },
  },
  {
    id: 'changes-since-visit',
    title: 'Changements depuis la dernière visite',
    question: 'Qu’est-ce qui a été ajouté, modifié ou annulé depuis ma dernière lecture ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucun contrat ne mémorise une visite ni ne publie l’écart entre deux snapshots ; le comparer dans le navigateur créerait une seconde vérité.',
    },
  },
];

export function absentCalendarModules(): readonly (CalendarModule & {
  readonly status: Extract<CalendarModuleStatus, { kind: 'absent' }>;
})[] {
  return CALENDAR_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function calendarModule(id: string): CalendarModule {
  const module = CALENDAR_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown calendar module: ${id}`);
  }
  return module;
}
