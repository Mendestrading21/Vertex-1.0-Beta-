/**
 * Aides d'affichage de la réponse déterministe `AiAnswer`.
 *
 * Aucune donnée n'est reformulée : les phrases, extraits, contradictions et
 * limites sont les chaînes exactes du serveur. Ce module ne fait que résoudre
 * une citation vers son entrée de catalogue et fabriquer des ancres HTML
 * stables — il ne complète, ne devine et ne traduit rien.
 */
import type { AiAnswer, AiEvidenceCatalogEntry, AiSubject } from '../../api/client.ts';

/** Les trois sujets explicables du contrat, avec leur libellé français. */
export const AI_SUBJECT_KINDS = ['analysis', 'portfolio_valuation', 'performance'] as const;

export type AiSubjectKind = (typeof AI_SUBJECT_KINDS)[number];

export const AI_SUBJECT_LABELS: Readonly<Record<AiSubjectKind, string>> = {
  analysis: 'Analyse d’un instrument',
  portfolio_valuation: 'Valorisation de portefeuille',
  performance: 'Performance de portefeuille',
};

export const AI_SUBJECT_RESOURCE_LABELS: Readonly<Record<AiSubjectKind, string>> = {
  analysis: 'analysis/<instrument>',
  portfolio_valuation: 'portfolio_valuation/<portefeuille>',
  performance: 'performance/<portefeuille>',
};

/** Bandeau permanent, non masquable, imposé par la décision B-05 en attente. */
export const AI_PERMANENT_NOTICE =
  'Explication par gabarit déterministe — fournisseur IA désactivé (décision B-05 en attente)';

/** L'enregistrement d'une note n'existe pas : capacité déclarée non implémentée. */
export const AI_NOTE_CAPABILITY_STATE = 'NON_IMPLÉMENTÉ';

export function isAiSubjectKind(value: string): value is AiSubjectKind {
  return (AI_SUBJECT_KINDS as readonly string[]).includes(value);
}

/** Ancre HTML stable d'une preuve — jamais l'identifiant brut (`:`, `/`). */
export function evidenceAnchorId(evidenceId: string): string {
  return `vx-ai-evidence-${evidenceId.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
}

export function evidenceIndexOf(
  catalog: readonly AiEvidenceCatalogEntry[],
): ReadonlyMap<string, AiEvidenceCatalogEntry> {
  const index = new Map<string, AiEvidenceCatalogEntry>();
  for (const entry of catalog) {
    index.set(entry.evidence_id, entry);
  }
  return index;
}

/** Étiquette courte et lisible d'une citation (jamais un texte inventé). */
export function evidenceLabelOf(
  evidenceId: string,
  index: ReadonlyMap<string, AiEvidenceCatalogEntry>,
): string {
  const entry = index.get(evidenceId);
  if (entry === undefined) {
    return `${evidenceId} — hors catalogue`;
  }
  return `${entry.evidence_type} · ${entry.path}`;
}

/** `true` quand la réponse est un REFUS structuré (jamais une explication vide). */
export function isRefusal(answer: AiAnswer): boolean {
  return answer.state === 'refused';
}

export function subjectOf(kind: AiSubjectKind, key: string): AiSubject {
  return { kind, key };
}
