/**
 * Catalogue de la planche §3 (Opportunités) —
 * `pages-03-04-opportunities-analysis.png`, moitié gauche. Chaque module est
 * SERVI par un contrat existant ou DÉCLARÉ absent avec le motif mesuré ;
 * aucun n'est simulé (article 17).
 *
 * Ce que la planche montre et que ce dépôt refuse par contrat : un « score
 * moyen », un « biais global », un « rendement attendu » et un nuage
 * score/rendement. Le snapshot `opportunities/global` ne publie AUCUN score
 * (son ordre est lexicographique et le dit : « aucun score opaque ») et
 * aucune espérance de rendement ; l'interface ne peut pas en fabriquer un.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';

export type OpportunitiesModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface OpportunitiesModule {
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: OpportunitiesModuleStatus;
}

const SNAPSHOT = 'GET /api/v1/opportunities — content';

export const OPPORTUNITIES_MODULES: readonly OpportunitiesModule[] = [
  {
    id: 'active-ideas',
    title: 'Candidats évalués',
    question: 'Combien de candidats le moteur a-t-il admis, exclus, considérés ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.coverage` },
  },
  {
    id: 'mean-score',
    title: 'Score moyen',
    question: 'Quel est le score moyen des candidats retenus ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Le moteur ne publie aucun score : l’ordre est lexicographique et déclaré « aucun score opaque ». Une moyenne de scores absents serait une valeur inventée.',
    },
  },
  {
    id: 'global-bias',
    title: 'Biais global',
    question: 'La sélection penche-t-elle dans un sens ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun biais agrégé n’est publié ; la direction de chaque candidat est relayée telle quelle, et une direction UNKNOWN ne se compte pas comme neutre.',
    },
  },
  {
    id: 'expected-return',
    title: 'Rendement attendu',
    question: 'Quel rendement les candidats laissent-ils espérer ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune espérance de rendement n’est publiée, et aucune probabilité calibrée ne l’autoriserait ; rien ne remplace ce chiffre.',
    },
  },
  {
    id: 'ranking',
    title: 'Classement publié',
    question: 'Quels candidats admissibles méritent une analyse approfondie ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.qualified / excluded / ordering` },
  },
  {
    id: 'bias-split',
    title: 'Répartition des directions',
    question: 'Quelles directions le moteur a-t-il publiées, candidat par candidat ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.qualified[].advice.direction / excluded[].advice.direction` },
  },
  {
    id: 'score-return-scatter',
    title: 'Score contre rendement',
    question: 'Les meilleurs scores portent-ils les meilleurs rendements ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Ni score ni rendement ne sont publiés : aucun point à placer.',
    },
  },
  {
    id: 'factor-contribution',
    title: 'Contribution des facteurs',
    question: 'Quels facteurs expliquent la sélection ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Le moteur publie des gates et des preuves requises, pas des facteurs pondérés ; les gates sont lisibles dans le classement et l’inspecteur.',
    },
  },
  {
    id: 'recent-activity',
    title: 'Activité récente',
    question: 'Qu’est-ce qui a changé depuis le snapshot précédent ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'L’API ne relaie que le dernier snapshot ; aucun contrat ne publie l’écart avec le précédent. Le comparer dans le navigateur créerait une seconde vérité.',
    },
  },
  {
    id: 'opportunity-health',
    title: 'Statuts sur l’univers',
    question: 'Quel statut fail-closed porte chaque candidat de l’univers ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.coverage.status_counts` },
  },
  {
    id: 'profile',
    title: 'Profil de stratégie référencé',
    question: 'Quel profil a été appliqué, et quelles parts ne l’ont pas été ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.profile_ref` },
  },
  {
    id: 'exclusions',
    title: 'Raisons d’exclusion',
    question: 'Pourquoi les candidats exclus le sont-ils ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.exclusion_reasons` },
  },
  {
    id: 'catalysts-provenance',
    title: 'Provenance des catalyseurs',
    question: 'Sur quel snapshot calendrier les catalyseurs ont-ils été comptés ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.calendar_ref` },
  },
  {
    id: 'quality',
    title: 'Limites publiées',
    question: 'Quelles limites le moteur déclare-t-il sur ce snapshot ?',
    status: { kind: 'served', contract: `${SNAPSHOT}.limitations` },
  },
];

export function absentOpportunitiesModules(): readonly (OpportunitiesModule & {
  readonly status: Extract<OpportunitiesModuleStatus, { kind: 'absent' }>;
})[] {
  return OPPORTUNITIES_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function opportunitiesModule(id: string): OpportunitiesModule {
  const module = OPPORTUNITIES_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown opportunities module: ${id}`);
  }
  return module;
}
