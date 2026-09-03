/**
 * Catalogue de la planche §10 (Catalyseurs) —
 * `pages-09-10-risks-catalysts.png`, moitié droite. Chaque module est SERVI
 * par un contrat existant ou DÉCLARÉ absent avec le motif mesuré ; aucun
 * n'est simulé (article 17).
 *
 * Ce que la planche montre et que ce dépôt ne publie pas : un impact moyen
 * pondéré, une confiance, des surprises et leur historique, un consensus,
 * des alertes d'événement. Le snapshot d'agenda publie des événements avec
 * statut, importance (rang, code, version de règle), révisions, versions en
 * conflit, fraîcheur, source, contexte croisé (positions, thèses, liens) ;
 * la file de revue publie des thèses. La page CROISE ces deux snapshots ;
 * elle ne pondère rien et ne prédit rien.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';

export type CatalystsModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface CatalystsModule {
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: CatalystsModuleStatus;
}

const AGENDA = 'GET /api/v1/calendar — agenda[]';
const QUEUE = 'GET /api/v1/review-queue — content';

export const CATALYSTS_MODULES: readonly CatalystsModule[] = [
  {
    id: 'upcoming-count',
    title: 'Événements reliés',
    question: 'Combien d’événements servis touchent une thèse ou une position ?',
    status: { kind: 'served', contract: `${AGENDA}.event_context × ${QUEUE}.theses` },
  },
  {
    id: 'mean-impact',
    title: 'Impact moyen',
    question: 'Quel impact pondéré ces événements portent-ils ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun impact n’est publié par événement : l’importance servie est un rang et un code de règle, pas une mesure pondérable. Une moyenne de rangs serait un score inventé.',
    },
  },
  {
    id: 'confidence',
    title: 'Confiance moyenne',
    question: 'À quel point ces événements sont-ils certains ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune confiance n’est publiée ; le statut de date (estimé ou confirmé) est un fait par événement, jamais une probabilité, et ne se moyenne pas.',
    },
  },
  {
    id: 'revisions',
    title: 'Révisions',
    question: 'Combien d’événements reliés ont été révisés par leur source ?',
    status: { kind: 'served', contract: `${AGENDA}.revised / revisions[]` },
  },
  {
    id: 'surprises',
    title: 'Surprises récentes',
    question: 'Quels résultats ont dépassé ou manqué les attentes ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune valeur publiée ni attendue n’est servie pour un événement ; sans ces deux chiffres, aucune surprise n’existe.',
    },
  },
  {
    id: 'filters',
    title: 'Filtres d’affichage',
    question: 'Quels événements reliés afficher, par catégorie et par lien ?',
    status: { kind: 'served', contract: `${AGENDA}.category / event_context (filtre local, jamais un reclassement)` },
  },
  {
    id: 'consensus',
    title: 'Consensus fourni',
    question: 'Quel consensus la source publie-t-elle pour l’événement ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Le contrat d’agenda ne porte aucun champ de consensus ; le dessiner supposerait de l’inventer.',
    },
  },
  {
    id: 'timeline',
    title: 'Chronologie des catalyseurs',
    question: 'Quels événements vérifiés peuvent modifier la thèse et quand ?',
    status: { kind: 'served', contract: `${AGENDA} — ordre publié, relié par event_context` },
  },
  {
    id: 'category-split',
    title: 'Répartition par catégorie',
    question: 'Quelles catégories d’événements composent les catalyseurs ?',
    status: { kind: 'served', contract: `${AGENDA}.category (dénombrement)` },
  },
  {
    id: 'surprise-history',
    title: 'Historique des surprises',
    question: 'Comment les surprises ont-elles évolué ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Sans surprise publiée, aucun historique n’existe ; rien n’est rejoué depuis d’anciens snapshots.',
    },
  },
  {
    id: 'portfolio-exposure',
    title: 'Exposition du registre aux événements',
    question: 'Quels événements touchent une position déclarée du registre manuel ?',
    status: { kind: 'served', contract: `${AGENDA}.event_context.positions[]` },
  },
  {
    id: 'event-alerts',
    title: 'Alertes d’événement',
    question: 'De quels événements souhaite-t-on être averti ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucun contrat d’alerte n’existe ; une préférence enregistrée dans le navigateur ne serait ni servie ni notifiée.',
    },
  },
  {
    id: 'sources-freshness',
    title: 'Sources et fraîcheur',
    question: 'D’où viennent les catalyseurs et sont-ils frais ?',
    status: { kind: 'served', contract: `${AGENDA}.source / fresh / delay_status (dénombrement)` },
  },
  {
    id: 'window',
    title: 'Fenêtre et snapshot',
    question: 'Sur quelle fenêtre et quel snapshot ces catalyseurs sont-ils lus ?',
    status: { kind: 'served', contract: 'GET /api/v1/calendar — window / as_of / snapshot_version / population' },
  },
  {
    id: 'conflicts',
    title: 'Conflits de version',
    question: 'Quels événements reliés portent des versions contradictoires ou des révisions refusées ?',
    status: { kind: 'served', contract: `${AGENDA}.version_state / rejected_revisions[]` },
  },
  {
    id: 'orphan-theses',
    title: 'Thèses sans catalyseur servi',
    question: 'Quelles thèses déclarées ne sont touchées par aucun événement servi ?',
    status: { kind: 'served', contract: `${QUEUE}.theses[] × ${AGENDA}.event_context.theses[]` },
  },
  {
    id: 'review',
    title: 'Revue des thèses',
    question: 'Quelles thèses, alertes et informations doivent être revues ?',
    status: { kind: 'served', contract: `${QUEUE}.due / theses ; POST /api/v1/theses` },
  },
];

export function absentCatalystsModules(): readonly (CatalystsModule & {
  readonly status: Extract<CatalystsModuleStatus, { kind: 'absent' }>;
})[] {
  return CATALYSTS_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function catalystsModule(id: string): CatalystsModule {
  const module = CATALYSTS_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown catalysts module: ${id}`);
  }
  return module;
}
