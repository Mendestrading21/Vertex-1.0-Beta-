/**
 * Lecture DÉFENSIVE de l'agenda `calendar/global`, relayé verbatim par l'API.
 *
 * Rien n'est calculé ici : chaque statut, instant, rang d'importance et
 * valeur antérieure est la chaîne serveur exacte. Les deux statuts
 * canoniques `ESTIMATED` et `CONFIRMED` ne partagent JAMAIS le même libellé
 * (`ESTIMATED_STATUS_LABEL` ≠ `CONFIRMED_STATUS_LABEL`), et une valeur
 * antérieure n'est jamais effacée : elle reste lisible telle que publiée.
 *
 * Un champ illisible devient `null` (absence explicite) : il n'est jamais
 * remplacé par un zéro, une moyenne ni une valeur théorique.
 */

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function asArray(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

function str(record: UnknownRecord | null, key: string): string | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function int(record: UnknownRecord | null, key: string): number | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'number' && Number.isInteger(value) ? value : null;
}

function bool(record: UnknownRecord | null, key: string): boolean | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'boolean' ? value : null;
}

/** Compteurs publiés par le serveur — jamais recalculés côté interface. */
export function counterMapOf(value: unknown): ReadonlyMap<string, number> {
  const record = asRecord(value);
  const entries = new Map<string, number>();
  if (record === null) {
    return entries;
  }
  for (const [key, raw] of Object.entries(record)) {
    if (typeof raw === 'number' && Number.isInteger(raw)) {
      entries.set(key, raw);
    }
  }
  return entries;
}

// -- statuts canoniques -----------------------------------------------------

export const ESTIMATED_STATUS = 'ESTIMATED';
export const CONFIRMED_STATUS = 'CONFIRMED';

/**
 * Libellés STRICTEMENT distincts : une date estimée et une date confirmée ne
 * peuvent jamais se lire pareil (règle produit de la page 02).
 */
export const ESTIMATED_STATUS_LABEL = 'Estimé';
export const CONFIRMED_STATUS_LABEL = 'Confirmé';

/** État de version publié quand plusieurs versions se contredisent à égalité. */
export const VERSION_STATE_CONFLICTING = 'CONFLICTING_VERSIONS';

export function statusLabelOf(status: string): string {
  if (status === ESTIMATED_STATUS) {
    return ESTIMATED_STATUS_LABEL;
  }
  if (status === CONFIRMED_STATUS) {
    return CONFIRMED_STATUS_LABEL;
  }
  // Statut hors contrat : relayé tel quel, jamais assimilé à l'un des deux.
  return status;
}

/**
 * Marqueur textuel (jamais la couleur seule) accolé au libellé de statut.
 *
 * LOT T4-4 — UN STATUT HORS CONTRAT N'A PAS DE MARQUEUR, et c'est juste. Il
 * renvoyait `'?'`, qui ne disait rien de plus que le libellé posé JUSTE À CÔTÉ :
 * `statusLabelOf` relaie le statut servi verbatim, et c'est lui le signal. Le
 * point d'interrogation ajoutait un glyphe ambigu à une information déjà
 * complète — et sur `AgendaLine`, où le marqueur est `aria-hidden`, il
 * n'atteignait même pas le lecteur d'écran.
 */
export function statusMarkOf(status: string): string {
  if (status === ESTIMATED_STATUS) {
    return '≈';
  }
  if (status === CONFIRMED_STATUS) {
    return '✓';
  }
  return '';
}

export const CATEGORY_LABELS: Readonly<Record<string, string>> = {
  EARNINGS: 'Résultats',
  DIVIDEND: 'Dividende',
  OPTION_EXPIRATION: 'Expiration d’options',
  MACRO: 'Macro',
};

export function categoryLabelOf(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

// -- vues -------------------------------------------------------------------

export interface ImportanceView {
  readonly rank: number | null;
  readonly code: string | null;
  readonly ruleVersion: string | null;
}

/** Une révision DÉCLARÉE PAR LA SOURCE (valeur antérieure conservée). */
export interface RevisionView {
  readonly revisedAt: string | null;
  readonly previousStatus: string | null;
  readonly previousEventTimeUtc: string | null;
  readonly reason: string | null;
}

/** Une révision REFUSÉE par le worker, avec sa raison publiée. */
export interface RejectedRevisionView {
  readonly reason: string | null;
  readonly revisedAt: string | null;
  readonly previousStatus: string | null;
  readonly previousEventTimeUtc: string | null;
}

/** Un enregistrement SUPPLANTÉ, resté lisible (statut et instant antérieurs). */
export interface PreviousValueView {
  readonly sourceEventId: string | null;
  readonly source: string | null;
  readonly asOf: string | null;
  readonly status: string | null;
  readonly eventTimeUtc: string | null;
}

export interface EventContextView {
  readonly positions: readonly number[];
  readonly theses: readonly {
    readonly thesisId: number | null;
    readonly title: string | null;
    readonly status: string | null;
  }[];
  readonly links: readonly { readonly rel: string; readonly resource: string }[];
}

export interface CalendarEventView {
  readonly eventId: string;
  readonly category: string;
  readonly status: string;
  readonly title: string | null;
  readonly ticker: string | null;
  readonly scope: string | null;
  readonly eventTimeUtc: string;
  readonly eventTimeLocal: string | null;
  readonly exchangeTimezone: string | null;
  readonly importance: ImportanceView;
  readonly revised: boolean;
  readonly revisions: readonly RevisionView[];
  readonly rejectedRevisions: readonly RejectedRevisionView[];
  readonly previousValues: readonly PreviousValueView[];
  /**
   * État de version publié par le worker quand il existe (`RESOLVED` ou
   * `CONFLICTING_VERSIONS`). `null` quand le snapshot ne le publie pas :
   * l'interface n'en déduit alors AUCUN état — l'absence reste une absence.
   */
  readonly versionState: string | null;
  readonly conflictingVersions: readonly PreviousValueView[];
  readonly context: EventContextView;
  readonly fresh: boolean | null;
  readonly staleAfter: string | null;
  readonly delayStatus: string | null;
  readonly quality: string | null;
  readonly source: string | null;
  readonly rights: string | null;
  readonly sourceEventId: string | null;
  readonly synthetic: boolean;
  /** Champs facultatifs relayés verbatim (montant, devise, expiration). */
  readonly amount: string | null;
  readonly currency: string | null;
  readonly expiration: string | null;
}

function importanceOf(value: unknown): ImportanceView {
  const record = asRecord(value);
  return {
    rank: int(record, 'rank'),
    code: str(record, 'code'),
    ruleVersion: str(record, 'rule_version'),
  };
}

function revisionsOf(value: unknown): readonly RevisionView[] {
  return asArray(value).map((raw) => {
    const record = asRecord(raw);
    return {
      revisedAt: str(record, 'revised_at'),
      previousStatus: str(record, 'previous_status'),
      previousEventTimeUtc: str(record, 'previous_event_time_utc'),
      reason: str(record, 'reason'),
    };
  });
}

function rejectedRevisionsOf(value: unknown): readonly RejectedRevisionView[] {
  return asArray(value).map((raw) => {
    const record = asRecord(raw);
    const revision = asRecord(record?.['revision']) ?? record;
    return {
      reason: str(record, 'reason'),
      revisedAt: str(revision, 'revised_at'),
      previousStatus: str(revision, 'previous_status'),
      previousEventTimeUtc: str(revision, 'previous_event_time_utc'),
    };
  });
}

function previousValuesOf(value: unknown): readonly PreviousValueView[] {
  return asArray(value).map((raw) => {
    const record = asRecord(raw);
    return {
      sourceEventId: str(record, 'source_event_id'),
      source: str(record, 'source'),
      asOf: str(record, 'as_of'),
      status: str(record, 'status'),
      eventTimeUtc: str(record, 'event_time_utc'),
    };
  });
}

function contextOf(value: unknown): EventContextView {
  const record = asRecord(value);
  const positions: number[] = [];
  for (const raw of asArray(record?.['positions'])) {
    const identifier = int(asRecord(raw), 'portfolio_id');
    if (identifier !== null) {
      positions.push(identifier);
    }
  }
  const theses = asArray(record?.['theses']).map((raw) => {
    const entry = asRecord(raw);
    return {
      thesisId: int(entry, 'thesis_id'),
      title: str(entry, 'title'),
      status: str(entry, 'status'),
    };
  });
  const links: { rel: string; resource: string }[] = [];
  for (const raw of asArray(record?.['links'])) {
    const entry = asRecord(raw);
    const rel = str(entry, 'rel');
    const resource = str(entry, 'resource');
    if (rel !== null && resource !== null) {
      links.push({ rel, resource });
    }
  }
  return { positions, theses, links };
}

/**
 * Convertit un événement publié en vue d'affichage. `null` si l'identité, la
 * catégorie, le statut ou l'instant UTC manquent : un événement non lisible
 * n'est jamais affiché à moitié.
 */
export function calendarEventOf(raw: unknown): CalendarEventView | null {
  const record = asRecord(raw);
  const eventId = str(record, 'event_id');
  const category = str(record, 'category');
  const status = str(record, 'status');
  const eventTimeUtc = str(record, 'event_time_utc');
  if (eventId === null || category === null || status === null || eventTimeUtc === null) {
    return null;
  }
  const amountValue = record?.['amount'];
  const expirationValue = record?.['expiration'];
  return {
    eventId,
    category,
    status,
    title: str(record, 'title'),
    ticker: str(record, 'ticker'),
    scope: str(record, 'scope'),
    eventTimeUtc,
    eventTimeLocal: str(record, 'event_time_local'),
    exchangeTimezone: str(record, 'exchange_timezone'),
    importance: importanceOf(record?.['importance']),
    revised: bool(record, 'revised') === true,
    revisions: revisionsOf(record?.['revisions']),
    rejectedRevisions: rejectedRevisionsOf(record?.['rejected_revisions']),
    previousValues: previousValuesOf(record?.['previous_values']),
    versionState: str(record, 'version_state'),
    conflictingVersions: previousValuesOf(record?.['conflicting_versions']),
    context: contextOf(record?.['event_context']),
    fresh: bool(record, 'fresh'),
    staleAfter: str(record, 'stale_after'),
    delayStatus: str(record, 'delay_status'),
    quality: str(record, 'quality'),
    source: str(record, 'source'),
    rights: str(record, 'rights'),
    sourceEventId: str(record, 'source_event_id'),
    synthetic: bool(record, 'synthetic') === true,
    amount: typeof amountValue === 'string' && amountValue !== '' ? amountValue : null,
    currency: str(record, 'currency'),
    expiration: typeof expirationValue === 'string' && expirationValue !== '' ? expirationValue : null,
  };
}

export function calendarEventsOf(agenda: readonly unknown[]): readonly CalendarEventView[] {
  const events: CalendarEventView[] = [];
  for (const raw of agenda) {
    const event = calendarEventOf(raw);
    if (event !== null) {
      events.push(event);
    }
  }
  return events;
}

// -- règle d'importance versionnée ------------------------------------------

export interface ImportanceRuleView {
  readonly version: string | null;
  readonly ranks: readonly {
    readonly rank: number | null;
    readonly code: string | null;
    readonly description: string | null;
  }[];
}

export function importanceRuleOf(value: unknown): ImportanceRuleView {
  const record = asRecord(value);
  return {
    version: str(record, 'version'),
    ranks: asArray(record?.['ranks']).map((raw) => {
      const entry = asRecord(raw);
      return {
        rank: int(entry, 'rank'),
        code: str(entry, 'code'),
        description: str(entry, 'description'),
      };
    }),
  };
}

// -- regroupement jour / semaine --------------------------------------------

export type AgendaGrouping = 'day' | 'week';

/**
 * Clé de regroupement d'un instant UTC : le PRÉFIXE de la chaîne serveur pour
 * le jour (`YYYY-MM-DD`), et le jour du lundi ISO de la même chaîne pour la
 * semaine. Aucune conversion de fuseau n'intervient ici : le regroupement se
 * fait sur l'instant UTC publié, ce que l'en-tête de groupe affiche.
 */
export function groupKeyOf(eventTimeUtc: string, grouping: AgendaGrouping): string {
  const day = eventTimeUtc.slice(0, 10);
  if (grouping === 'day') {
    return day;
  }
  const parsed = new Date(`${day}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return day;
  }
  // Lundi ISO de la semaine contenant ce jour (UTC, jamais l'heure locale).
  const weekday = (parsed.getUTCDay() + 6) % 7;
  parsed.setUTCDate(parsed.getUTCDate() - weekday);
  return parsed.toISOString().slice(0, 10);
}

export interface AgendaGroupView {
  readonly key: string;
  readonly events: readonly CalendarEventView[];
}

/** Regroupe la liste SERVIE dans son ordre serveur (jamais retriée). */
export function groupAgenda(
  events: readonly CalendarEventView[],
  grouping: AgendaGrouping,
): readonly AgendaGroupView[] {
  const groups: AgendaGroupView[] = [];
  const index = new Map<string, CalendarEventView[]>();
  for (const event of events) {
    const key = groupKeyOf(event.eventTimeUtc, grouping);
    let bucket = index.get(key);
    if (bucket === undefined) {
      bucket = [];
      index.set(key, bucket);
      groups.push({ key, events: bucket });
    }
    bucket.push(event);
  }
  return groups;
}

// -- affichage des fuseaux ---------------------------------------------------

/**
 * Rend un instant UTC dans une timezone IANA EXPLICITE. Utilisé uniquement
 * pour la colonne « votre fuseau », toujours étiquetée avec le nom du fuseau
 * appliqué : jamais une conversion implicite d'une des deux chaînes serveur,
 * qui restent affichées telles quelles.
 */
export function formatInTimeZone(instantUtc: string, timeZone: string): string | null {
  const parsed = new Date(instantUtc);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  try {
    return new Intl.DateTimeFormat('fr-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(parsed);
  } catch {
    return null;
  }
}

/** Fuseau IANA du navigateur, ou `null` s'il n'est pas résoluble. */
export function resolveViewerTimeZone(): string | null {
  try {
    const zone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
    return typeof zone === 'string' && zone !== '' ? zone : null;
  } catch {
    return null;
  }
}
