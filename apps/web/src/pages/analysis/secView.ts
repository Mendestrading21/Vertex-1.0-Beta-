/**
 * Lecture DÉFENSIVE de la réponse `sources/sec/{instrument}/fundamentals`.
 *
 * Les dépôts et faits arrivent comme des tableaux d'objets non typés
 * (`FrozenStrMapping`) : on ne garde que les champs lisibles, verbatim, et on
 * ignore une entrée illisible plutôt que de la compléter. Aucun ratio, aucune
 * somme, aucune comparaison — la route le dit elle-même : « no ratio, score
 * or advice is computed ».
 */
import type { SecFundamentalsResponse } from '../../api/client.ts';

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function str(record: UnknownRecord, key: string): string | null {
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

export interface SecFilingView {
  readonly accession: string;
  readonly form: string | null;
  readonly availableAt: string | null;
  /** URL officielle publiée par la source ; relayée, jamais construite ici. */
  readonly primaryDocumentUrl: string | null;
}

export interface SecFactView {
  readonly key: string;
  readonly taxonomy: string | null;
  readonly concept: string;
  /** Chaîne décimale publiée, jamais parsée. */
  readonly value: string | null;
  readonly unit: string | null;
  readonly periodEnd: string | null;
  readonly availableAt: string | null;
  readonly accession: string | null;
}

export interface SecCoverageView {
  readonly observationsConsidered: number | null;
  readonly publishedFilings: number | null;
  readonly publishedFacts: number | null;
  readonly truncatedFacts: number | null;
  readonly conflictingFactKeys: number | null;
  readonly correctionsObserved: number | null;
}

export interface SecFundamentalsView {
  readonly filings: readonly SecFilingView[];
  readonly facts: readonly SecFactView[];
  readonly conflictCount: number;
  readonly coverage: SecCoverageView;
}

const SEC_HOST = 'https://www.sec.gov/';

/** Seule une URL du domaine officiel est relayée comme lien. */
export function officialSecUrl(value: string | null): string | null {
  return value?.startsWith(SEC_HOST) ? value : null;
}

export function secFundamentalsViewOf(data: SecFundamentalsResponse): SecFundamentalsView {
  const filings: SecFilingView[] = [];
  for (const raw of data.filings) {
    const record = asRecord(raw);
    if (record === null) {
      continue;
    }
    const accession = str(record, 'accession');
    if (accession === null) {
      continue;
    }
    filings.push({
      accession,
      form: str(record, 'form'),
      availableAt: str(record, 'available_at'),
      primaryDocumentUrl: officialSecUrl(str(record, 'primary_document_url')),
    });
  }
  const facts: SecFactView[] = [];
  for (const raw of data.facts) {
    const record = asRecord(raw);
    if (record === null) {
      continue;
    }
    const concept = str(record, 'concept');
    if (concept === null) {
      continue;
    }
    const taxonomy = str(record, 'taxonomy');
    const unit = str(record, 'unit');
    const periodEnd = str(record, 'period_end');
    facts.push({
      key: [taxonomy ?? '', concept, unit ?? '', periodEnd ?? ''].join('|'),
      taxonomy,
      concept,
      value: str(record, 'value'),
      unit,
      periodEnd,
      availableAt: str(record, 'available_at'),
      accession: str(record, 'accession'),
    });
  }
  const coverage = asRecord(data.coverage);
  return {
    filings,
    facts,
    conflictCount: data.conflicts.length,
    coverage: {
      observationsConsidered: int(coverage, 'observations_considered'),
      publishedFilings: int(coverage, 'published_filings'),
      publishedFacts: int(coverage, 'published_facts'),
      truncatedFacts: int(coverage, 'truncated_facts'),
      conflictingFactKeys: int(coverage, 'conflicting_fact_keys'),
      correctionsObserved: int(coverage, 'corrections_observed'),
    },
  };
}

export const IDENTITY_STATE_FR: Readonly<Record<string, string>> = {
  RESOLVED: 'identité résolue',
  CONFLICTING_IDENTITY: 'identité contradictoire — aucun fait attribué',
  ABSENT: 'identité absente — aucun fait attribué',
};
