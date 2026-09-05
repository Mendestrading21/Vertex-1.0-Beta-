/**
 * Lecture DÉFENSIVE du snapshot `opportunities/global`, relayé verbatim par
 * l'API. Rien n'est classé, noté ni recalculé ici : le statut, les gates, les
 * preuves manquantes et les raisons d'exclusion sont les valeurs publiées.
 *
 * Une seule discipline structurelle est appliquée côté interface, et elle est
 * DÉFENSIVE : un candidat publié dans le groupe qualifié mais contredit par
 * ses propres faits (statut fermé, gate BLOCK, exclusion publiée ou preuve
 * requise manquante) n'est JAMAIS rendu parmi les qualifiés. Il tombe dans un
 * troisième seau `contradictory`, affiché avec les exclus et signalé comme
 * incohérence du snapshot — l'interface ne le « répare » pas et ne lui
 * fabrique aucun verdict.
 */

import type { OpportunitiesResponse } from '../../api/client.ts';
import type { PageDataState } from '../../api/hooks.ts';
import type { DataState } from '../../components/DataStateBoundary.tsx';

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

function strList(value: unknown): readonly string[] {
  return asArray(value).filter((entry): entry is string => typeof entry === 'string' && entry !== '');
}

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

// -- contrat de statut ------------------------------------------------------

/** Les SEULS statuts admis dans le groupe qualifié (miroir du contrat API). */
export const QUALIFIED_STATUSES: readonly string[] = ['OBSERVE', 'REVIEW', 'QUALIFIED'];
export const GATE_STATUS_BLOCK = 'BLOCK';

export const EXCLUSION_KIND_LABELS: Readonly<Record<string, string>> = {
  CLOSED_STATUS: 'Statut fermé par une gate bloquante',
  MISSING_REQUIRED_EVIDENCE: 'Preuve requise du profil absente',
};

// -- vues -------------------------------------------------------------------

export interface GateView {
  readonly gateId: string;
  readonly status: string;
  readonly reasonCode: string | null;
}

export interface AdviceView {
  readonly adviceId: string | null;
  readonly status: string;
  readonly direction: string | null;
  readonly horizon: string | null;
  readonly asOf: string | null;
  readonly validUntil: string | null;
  readonly engineVersion: string | null;
}

interface EvidenceCheckView {
  readonly name: string;
  readonly present: boolean;
  readonly detail: string | null;
}

export interface ExclusionView {
  readonly kind: string | null;
  readonly gateId: string | null;
  readonly reasonCode: string | null;
  readonly detail: string | null;
  readonly missingEvidence: readonly string[];
}

export interface CandidateView {
  readonly ticker: string;
  readonly sector: string | null;
  readonly rank: number | null;
  readonly advice: AdviceView;
  readonly gates: readonly GateView[];
  readonly degradedGates: readonly string[];
  readonly missingEvidence: readonly string[];
  readonly requiredEvidence: readonly EvidenceCheckView[];
  readonly evidenceClusterIds: readonly string[];
  readonly scenarioIds: readonly string[];
  readonly barsStatus: string | null;
  readonly scenariosStatus: string | null;
  readonly population: string | null;
  readonly synthetic: boolean;
  readonly exclusion: ExclusionView | null;
  readonly primaryExclusionReason: { readonly gateId: string; readonly reasonCode: string } | null;
}

function adviceOf(value: unknown): AdviceView {
  const record = asRecord(value);
  return {
    adviceId: str(record, 'advice_id'),
    status: str(record, 'status') ?? 'INCONNU',
    direction: str(record, 'direction'),
    horizon: str(record, 'horizon'),
    asOf: str(record, 'as_of'),
    validUntil: str(record, 'valid_until'),
    engineVersion: str(record, 'engine_version'),
  };
}

function gatesOf(value: unknown): readonly GateView[] {
  const gates: GateView[] = [];
  for (const raw of asArray(value)) {
    const record = asRecord(raw);
    const gateId = str(record, 'gate_id');
    const status = str(record, 'status');
    if (gateId === null || status === null) {
      continue;
    }
    gates.push({ gateId, status, reasonCode: str(record, 'reason_code') });
  }
  return gates;
}

function evidenceChecksOf(value: unknown): readonly EvidenceCheckView[] {
  const record = asRecord(value);
  if (record === null) {
    return [];
  }
  return Object.keys(record)
    .sort()
    .map((name) => {
      const entry = asRecord(record[name]);
      return {
        name,
        present: entry !== null && entry['present'] === true,
        detail: str(entry, 'detail'),
      };
    });
}

function exclusionOf(value: unknown): ExclusionView | null {
  const record = asRecord(value);
  if (record === null) {
    return null;
  }
  return {
    kind: str(record, 'kind'),
    gateId: str(record, 'gate_id'),
    reasonCode: str(record, 'reason_code'),
    detail: str(record, 'detail'),
    missingEvidence: strList(record['missing_evidence']),
  };
}

export function candidateOf(raw: unknown): CandidateView | null {
  const record = asRecord(raw);
  const ticker = str(record, 'ticker');
  if (ticker === null) {
    return null;
  }
  const primary = asRecord(record?.['primary_exclusion_reason']);
  const primaryGate = str(primary, 'gate_id');
  const primaryReason = str(primary, 'reason_code');
  return {
    ticker,
    sector: str(record, 'sector'),
    rank: int(record, 'rank'),
    advice: adviceOf(record?.['advice']),
    gates: gatesOf(record?.['gates']),
    degradedGates: strList(record?.['degraded_gates']),
    missingEvidence: strList(record?.['missing_evidence']),
    requiredEvidence: evidenceChecksOf(record?.['required_evidence']),
    evidenceClusterIds: strList(record?.['evidence_cluster_ids']),
    scenarioIds: strList(record?.['scenario_ids']),
    barsStatus: str(record, 'bars_status'),
    scenariosStatus: str(record, 'scenarios_status'),
    population: str(record, 'population'),
    synthetic: record?.['synthetic'] === true,
    exclusion: exclusionOf(record?.['exclusion']),
    primaryExclusionReason:
      primaryGate !== null && primaryReason !== null
        ? { gateId: primaryGate, reasonCode: primaryReason }
        : null,
  };
}

/**
 * Les faits qui INTERDISENT le groupe qualifié. Un seul suffit : ce sont
 * exactement les trois faits croisés par le contrat serveur, plus l'exclusion
 * publiée elle-même.
 */
export function disqualifyingFacts(candidate: CandidateView): readonly string[] {
  const facts: string[] = [];
  if (!QUALIFIED_STATUSES.includes(candidate.advice.status)) {
    facts.push(`statut ${candidate.advice.status} hors du groupe qualifié`);
  }
  const blocking = candidate.gates.filter((gate) => gate.status === GATE_STATUS_BLOCK);
  if (blocking.length > 0) {
    facts.push(`gate bloquante : ${blocking.map((gate) => gate.gateId).join(', ')}`);
  }
  if (candidate.missingEvidence.length > 0) {
    facts.push(`preuve requise absente : ${candidate.missingEvidence.join(', ')}`);
  }
  if (candidate.exclusion !== null || candidate.primaryExclusionReason !== null) {
    facts.push('exclusion publiée par le serveur');
  }
  return facts;
}

export interface PartitionedCandidates {
  readonly qualified: readonly CandidateView[];
  readonly excluded: readonly CandidateView[];
  /** Publiés qualifiés mais contredits par leurs propres faits publiés. */
  readonly contradictory: readonly CandidateView[];
}

/**
 * Sépare les deux groupes. GARANTIE testée : aucun candidat portant un fait
 * disqualifiant ne peut se retrouver dans `qualified`, quel que soit le
 * groupe dans lequel le serveur l'a publié.
 */
export function partitionCandidates(content: unknown): PartitionedCandidates {
  const record = asRecord(content);
  const qualified: CandidateView[] = [];
  const contradictory: CandidateView[] = [];
  for (const raw of asArray(record?.['qualified'])) {
    const candidate = candidateOf(raw);
    if (candidate === null) {
      continue;
    }
    if (disqualifyingFacts(candidate).length > 0) {
      contradictory.push(candidate);
    } else {
      qualified.push(candidate);
    }
  }
  const excluded: CandidateView[] = [];
  for (const raw of asArray(record?.['excluded'])) {
    const candidate = candidateOf(raw);
    if (candidate !== null) {
      excluded.push(candidate);
    }
  }
  return { qualified, excluded, contradictory };
}

// -- références de provenance ------------------------------------------------

interface ProfileRefView {
  readonly id: string | null;
  readonly version: string | null;
  readonly source: string | null;
  readonly applied: readonly string[];
  readonly notApplied: readonly { readonly field: string; readonly reason: string | null }[];
}

function profileRefOf(value: unknown): ProfileRefView {
  const record = asRecord(value);
  const notApplied: { field: string; reason: string | null }[] = [];
  for (const raw of asArray(record?.['not_applied'])) {
    const entry = asRecord(raw);
    const field = str(entry, 'field');
    if (field !== null) {
      notApplied.push({ field, reason: str(entry, 'reason') });
    }
  }
  return {
    id: str(record, 'id'),
    version: str(record, 'version'),
    source: str(record, 'source'),
    applied: strList(record?.['applied']),
    notApplied,
  };
}

export const CALENDAR_REF_STATUS_LABELS: Readonly<Record<string, string>> = {
  USED: 'Utilisé — catalyseurs comptés sur ce snapshot',
  ABSENT: 'Absent — aucun snapshot calendrier fourni, aucun catalyseur prouvé',
  STALE: 'Périmé — snapshot plus vieux que la fenêtre admise, aucun catalyseur prouvé',
  REJECTED_FUTURE_AS_OF: 'Refusé — snapshot daté dans le futur, aucun catalyseur prouvé',
};

interface CalendarRefView {
  readonly kind: string | null;
  readonly key: string | null;
  readonly version: number | null;
  readonly status: string | null;
  readonly snapshotAsOf: string | null;
  readonly contentAsOf: string | null;
  readonly contentSchemaVersion: string | null;
  readonly maxAgeSeconds: number | null;
  readonly eventsUpcoming: number | null;
  readonly eventsIgnoredPast: number | null;
  readonly eventsWithoutTicker: number | null;
  readonly eventsRejected: number | null;
}

function calendarRefOf(value: unknown): CalendarRefView {
  const record = asRecord(value);
  return {
    kind: str(record, 'kind'),
    key: str(record, 'key'),
    version: int(record, 'version'),
    status: str(record, 'status'),
    snapshotAsOf: str(record, 'snapshot_as_of'),
    contentAsOf: str(record, 'content_as_of'),
    contentSchemaVersion: str(record, 'content_schema_version'),
    maxAgeSeconds: int(record, 'max_age_seconds'),
    eventsUpcoming: int(record, 'events_upcoming'),
    eventsIgnoredPast: int(record, 'events_ignored_past'),
    eventsWithoutTicker: int(record, 'events_without_ticker'),
    eventsRejected: int(record, 'events_rejected'),
  };
}

interface OrderingView {
  readonly method: string | null;
  readonly keys: readonly string[];
  readonly note: string | null;
}

function orderingOf(value: unknown): OrderingView {
  const record = asRecord(value);
  return {
    method: str(record, 'method'),
    keys: strList(record?.['keys']),
    note: str(record, 'note'),
  };
}

export interface OpportunitiesContentView {
  readonly asOf: string | null;
  readonly population: string | null;
  readonly engineVersion: string | null;
  readonly schemaVersion: string | null;
  readonly profileRef: ProfileRefView;
  readonly calendarRef: CalendarRefView;
  readonly ordering: OrderingView;
  readonly exclusionReasons: ReadonlyMap<string, number>;
  readonly limitations: readonly string[];
  readonly coverage: {
    readonly universeSize: number | null;
    readonly qualifiedCount: number | null;
    readonly excludedCount: number | null;
    readonly observationsConsidered: number | null;
    readonly statusCounts: ReadonlyMap<string, number>;
    readonly populationCounts: ReadonlyMap<string, number>;
  };
  readonly candidates: PartitionedCandidates;
}

/** `null` quand le contenu publié est illisible : rien n'est affiché à moitié. */
export function opportunitiesContentOf(content: unknown): OpportunitiesContentView | null {
  const record = asRecord(content);
  if (record === null) {
    return null;
  }
  const schemaVersion = str(record, 'schema_version');
  if (schemaVersion === null || !Array.isArray(record['excluded'])) {
    return null;
  }
  const coverage = asRecord(record['coverage']);
  return {
    asOf: str(record, 'as_of'),
    population: str(record, 'population'),
    engineVersion: str(record, 'engine_version'),
    schemaVersion,
    profileRef: profileRefOf(record['profile_ref']),
    calendarRef: calendarRefOf(record['calendar_ref']),
    ordering: orderingOf(record['ordering']),
    exclusionReasons: counterMapOf(record['exclusion_reasons']),
    limitations: strList(record['limitations']),
    coverage: {
      universeSize: int(coverage, 'universe_size'),
      qualifiedCount: int(coverage, 'qualified_count'),
      excludedCount: int(coverage, 'excluded_count'),
      observationsConsidered: int(coverage, 'observations_considered'),
      statusCounts: counterMapOf(coverage?.['status_counts']),
      populationCounts: counterMapOf(coverage?.['population_counts']),
    },
    candidates: partitionCandidates(record),
  };
}

/**
 * État du cadre Opportunités, dérivé des faits servis (déplacé de la page au
 * LOT-A3 : Aujourd'hui le réutilise sans tirer la page dans son chunk).
 */
export function opportunitiesFrameStateOf(
  queryState: PageDataState,
  data: OpportunitiesResponse | undefined,
): {
  readonly state: DataState | 'auth-required';
  readonly view: OpportunitiesContentView | null;
  readonly detail?: string;
} {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return { state: queryState, view: null };
  }
  if (data === undefined) {
    return { state: 'error', view: null };
  }
  const served: string = data.state;
  if (served === 'empty') {
    return { state: 'empty', view: null };
  }
  if (served === 'clock_inconsistent') {
    // Fermé comme tout état sans contenu servable, mais la cause vient du
    // serveur : dire « erreur » seul laisserait croire à un contenu invalide.
    return {
      state: 'error',
      view: null,
      detail:
        data.reason ??
        'Horloge incohérente entre le worker et l’API : aucun verdict n’est affiché.',
    };
  }
  if (served !== 'ok' && served !== 'stale') {
    // Fail-closed : un état hors contrat n'est jamais rendu comme un succès,
    // et aucune cause n'est inventée pour lui.
    return { state: 'error', view: null };
  }
  const view = opportunitiesContentOf(data.content);
  if (view === null) {
    return { state: 'error', view: null };
  }
  // Un verdict périmé garde son contenu SOUS un bandeau explicite : il n'est
  // ni masqué, ni présenté comme courant.
  return { state: served === 'stale' ? 'stale' : queryState, view };
}
