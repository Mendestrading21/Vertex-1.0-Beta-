/**
 * Lecture défensive du snapshot `review_queue/global`, relayé verbatim par
 * l'API (`FollowUpQueueResponse.content`).
 *
 * Ce module ne calcule ni urgence ni échéance : les flags, raisons, rangs et
 * instants viennent du worker. Les DEUX étiquettes de population (thèses
 * déclarées / contexte d'information) restent séparées — jamais fusionnées.
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

function num(record: UnknownRecord | null, key: string): number | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function bool(record: UnknownRecord | null, key: string): boolean {
  return record !== null && record[key] === true;
}

// -- vues -------------------------------------------------------------------

interface UrgencyReasonView {
  readonly code: string;
  readonly clusterId: string | null;
  readonly lastReceivedAt: string | null;
  readonly referenceInstant: string | null;
}

interface ClusterContextView {
  readonly clusterId: string;
  readonly title: string | null;
  readonly synthetic: boolean;
  readonly sources: readonly string[];
  readonly rights: readonly string[];
  readonly memberEventIds: readonly string[];
  readonly firstPublishedAt: string | null;
  readonly lastReceivedAt: string | null;
}

export interface ThesisEntryView {
  readonly id: number;
  readonly title: string;
  readonly hypotheses: string | null;
  readonly invalidation: string | null;
  readonly horizon: string | null;
  readonly instrumentTicker: string | null;
  readonly createdAt: string | null;
  readonly baseReviewDueAt: string | null;
  readonly status: string | null;
  readonly effectiveReviewDueAt: string | null;
  readonly isDue: boolean;
  readonly snoozeUntil: string | null;
  readonly lastReviewedAt: string | null;
  readonly lastAction: string | null;
  readonly lastRecordedAt: string | null;
  readonly revisionCount: number | null;
  readonly informationPopulation: string | null;
  readonly clusters: readonly ClusterContextView[];
  readonly hasNewInformation: boolean;
  readonly urgencyReasons: readonly UrgencyReasonView[];
}

export interface DueEntryView {
  readonly rank: number;
  readonly thesisId: number;
  readonly title: string;
  readonly reviewDueAt: string | null;
  readonly overdueSeconds: number | null;
  readonly lastRecordedAt: string | null;
  readonly hasNewInformation: boolean;
  readonly urgencyReasons: readonly UrgencyReasonView[];
}

export interface QueueContentView {
  readonly asOf: string | null;
  readonly populationTheses: string | null;
  readonly populationInformation: string | null;
  readonly orderingKeys: readonly string[];
  readonly orderingNote: string | null;
  readonly theses: readonly ThesisEntryView[];
  readonly due: readonly DueEntryView[];
  readonly thesesTotal: number | null;
  readonly dueCount: number | null;
  readonly thesesWithNewInformation: number | null;
}

function urgencyReasonOf(value: unknown): UrgencyReasonView | null {
  const record = asRecord(value);
  const code = str(record, 'code');
  if (record === null || code === null) {
    return null;
  }
  return {
    code,
    clusterId: str(record, 'cluster_id'),
    lastReceivedAt: str(record, 'last_received_at'),
    referenceInstant: str(record, 'reference_instant'),
  };
}

function strList(value: unknown): readonly string[] {
  return asArray(value).filter((entry): entry is string => typeof entry === 'string');
}

function clusterOf(value: unknown): ClusterContextView | null {
  const record = asRecord(value);
  const clusterId = str(record, 'cluster_id');
  if (record === null || clusterId === null) {
    return null;
  }
  const provenance = asRecord(record['provenance']);
  return {
    clusterId,
    title: str(record, 'title'),
    synthetic: bool(record, 'synthetic'),
    sources: strList(provenance?.['sources']),
    rights: strList(provenance?.['rights']),
    memberEventIds: strList(provenance?.['member_event_ids']),
    firstPublishedAt: str(provenance, 'first_published_at'),
    lastReceivedAt: str(provenance, 'last_received_at'),
  };
}

function thesisEntryOf(value: unknown): ThesisEntryView | null {
  const record = asRecord(value);
  if (record === null) {
    return null;
  }
  const thesis = asRecord(record['thesis']);
  const state = asRecord(record['state']);
  const id = num(thesis, 'id');
  const title = str(thesis, 'title');
  if (id === null || title === null) {
    return null;
  }
  const info = asRecord(record['information_context']);
  return {
    id,
    title,
    hypotheses: str(thesis, 'hypotheses'),
    invalidation: str(thesis, 'invalidation'),
    horizon: str(thesis, 'horizon'),
    instrumentTicker: str(record, 'instrument_ticker'),
    createdAt: str(thesis, 'created_at'),
    baseReviewDueAt: str(thesis, 'review_due_at'),
    status: str(state, 'status'),
    effectiveReviewDueAt: str(state, 'review_due_at'),
    isDue: bool(state, 'is_due'),
    snoozeUntil: str(state, 'snooze_until'),
    lastReviewedAt: str(state, 'last_reviewed_at'),
    lastAction: str(state, 'last_action'),
    lastRecordedAt: str(state, 'last_recorded_at'),
    revisionCount: num(state, 'revision_count'),
    informationPopulation: str(info, 'population'),
    clusters: asArray(info?.['clusters'])
      .map(clusterOf)
      .filter((cluster): cluster is ClusterContextView => cluster !== null),
    hasNewInformation: bool(record, 'has_new_information'),
    urgencyReasons: asArray(record['urgency_reasons'])
      .map(urgencyReasonOf)
      .filter((reason): reason is UrgencyReasonView => reason !== null),
  };
}

function dueEntryOf(value: unknown): DueEntryView | null {
  const record = asRecord(value);
  const rank = num(record, 'rank');
  const thesisId = num(record, 'thesis_id');
  const title = str(record, 'title');
  if (record === null || rank === null || thesisId === null || title === null) {
    return null;
  }
  const overdue = record['overdue_seconds'];
  return {
    rank,
    thesisId,
    title,
    reviewDueAt: str(record, 'review_due_at'),
    overdueSeconds: typeof overdue === 'number' && Number.isFinite(overdue) ? overdue : null,
    lastRecordedAt: str(record, 'last_recorded_at'),
    hasNewInformation: bool(record, 'has_new_information'),
    urgencyReasons: asArray(record['urgency_reasons'])
      .map(urgencyReasonOf)
      .filter((reason): reason is UrgencyReasonView => reason !== null),
  };
}

/** Lit le contenu du snapshot. `null` si absent ou de version inattendue. */
export function queueContentOf(content: unknown): QueueContentView | null {
  const record = asRecord(content);
  if (record === null || str(record, 'schema_version') !== 'vertex.review-queue/1.0') {
    return null;
  }
  const populations = asRecord(record['populations']);
  const ordering = asRecord(record['ordering']);
  const coverage = asRecord(record['coverage']);
  return {
    asOf: str(record, 'as_of'),
    populationTheses: str(populations, 'theses'),
    populationInformation: str(populations, 'information_context'),
    orderingKeys: strList(ordering?.['keys']),
    orderingNote: str(ordering, 'note'),
    theses: asArray(record['theses'])
      .map(thesisEntryOf)
      .filter((entry): entry is ThesisEntryView => entry !== null),
    due: asArray(record['due'])
      .map(dueEntryOf)
      .filter((entry): entry is DueEntryView => entry !== null),
    thesesTotal: num(coverage, 'theses_total'),
    dueCount: num(coverage, 'due_count'),
    thesesWithNewInformation: num(coverage, 'theses_with_new_information'),
  };
}

/** Statuts projetés → libellé français (le code machine reste affiché). */
const THESIS_STATUS_LABELS: Readonly<Record<string, string>> = {
  ACTIVE: 'active',
  SNOOZED: 'reportée',
  ARCHIVED: 'archivée',
};

export function thesisStatusLabel(status: string | null): string {
  if (status === null) {
    // LOT T4-3 — un statut non publié se DIT. Le tiret laissait le lecteur
    // deviner s'il s'agissait d'un statut vide, inconnu ou non servi.
    return 'statut non publié';
  }
  return THESIS_STATUS_LABELS[status] ?? status;
}
