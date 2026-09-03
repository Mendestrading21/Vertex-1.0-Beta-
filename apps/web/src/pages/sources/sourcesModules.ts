/**
 * Catalogue de la planche §12 (Sources & Rapports) —
 * `pages-11-12-calendar-sources-reports.png`, moitié droite. Chaque module
 * est SERVI par un contrat existant ou DÉCLARÉ absent avec le motif mesuré ;
 * aucun n'est simulé (article 17).
 *
 * Ce que la planche montre et que ce dépôt ne publie pas : une santé
 * globale en pourcentage, une couverture et une qualité des champs, un taux
 * d'erreur, des incidents, une lignée de données, un journal d'audit, des
 * rapports générés, des sauvegardes. Le contrat `system/capabilities`
 * publie les capacités déclarées croisées avec les sondes persistées, la
 * santé des composants, les versions de snapshots ; les seuls exports servis
 * sont ceux du registre manuel et de sa performance. Rien n'est simulé —
 * une santé rassurante sans couverture complète est interdite par le contrat.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';

export type SourcesModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface SourcesModule {
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: SourcesModuleStatus;
}

const CAPABILITIES = 'GET /api/v1/system/capabilities';

export const SOURCES_MODULES: readonly SourcesModule[] = [
  {
    id: 'global-health',
    title: 'Santé globale',
    question: 'Quel pourcentage de sources est en bonne santé ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune santé agrégée n’est publiée, et le contrat interdit une santé rassurante sans couverture complète : un pourcentage calculé sur des sondes partielles serait un faux vert.',
    },
  },
  {
    id: 'status-census',
    title: 'Statuts testés',
    question: 'Combien de capacités portent chaque statut réellement sondé ?',
    status: { kind: 'served', contract: `${CAPABILITIES} — capabilities[].tested_status (dénombrement)` },
  },
  {
    id: 'freshness',
    title: 'Fraîcheur',
    question: 'Quel âge ont les snapshots publiés et la dernière observation du worker ?',
    status: { kind: 'served', contract: `${CAPABILITIES} — health.attention_snapshot / capabilities_snapshot / worker` },
  },
  {
    id: 'field-coverage',
    title: 'Couverture des champs',
    question: 'Quelle part des champs attendus est réellement servie ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun inventaire de champs par source n’est publié ; compter des champs dans le navigateur inventerait la liste attendue.',
    },
  },
  {
    id: 'error-rate',
    title: 'Taux d’erreur',
    question: 'Quelle part des appels aux sources échoue ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun compteur d’appels ni d’échecs n’est publié par l’API ; le statut d’une sonde est un fait, pas un taux.',
    },
  },
  {
    id: 'incidents',
    title: 'Incidents',
    question: 'Quels incidents sont ouverts ou récemment clos ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucun contrat d’incident n’existe ; une sonde en erreur est relayée telle quelle dans le registre, elle n’est pas requalifiée en incident.',
    },
  },
  {
    id: 'last-sync',
    title: 'Dernière vérification',
    question: 'Quand l’état des capacités a-t-il été vérifié et publié ?',
    status: { kind: 'served', contract: `${CAPABILITIES} — checked_at / as_of / age_seconds / snapshot_version` },
  },
  {
    id: 'versions',
    title: 'Versions publiées',
    question: 'Quelles versions de snapshots et quel état de flux la page lit-elle ?',
    status: { kind: 'served', contract: `${CAPABILITIES} — health.*.version ; flux SSE du client` },
  },
  {
    id: 'registry',
    title: 'Registre des sources',
    question: 'Puis-je faire confiance aux sources, traitements et sauvegardes maintenant ?',
    status: { kind: 'served', contract: `${CAPABILITIES} — capabilities[] × sondes persistées` },
  },
  {
    id: 'lineage',
    title: 'Lignée de données',
    question: 'Par quels traitements une valeur affichée est-elle passée ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Chaque calcul publie son identifiant, sa version et son hash d’entrées dans son propre snapshot ; aucun contrat ne relie ces lignées entre sources.',
    },
  },
  {
    id: 'field-quality',
    title: 'Qualité des champs',
    question: 'Quels champs sont excellents, bons, dégradés ou mauvais ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune note de qualité par champ n’est publiée ; la qualité servie est un statut par observation, jamais une note.',
    },
  },
  {
    id: 'audit-log',
    title: 'Journal d’audit',
    question: 'Qui a modifié quoi, et quand ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Le journal du registre manuel est append-only et lisible sur Portefeuille ; aucun journal d’audit transversal n’est publié.',
    },
  },
  {
    id: 'reports',
    title: 'Rapports',
    question: 'Quels rapports ont été générés, et lesquels sont planifiés ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucun rapport n’est généré ni planifié par le serveur ; en simuler une liste présenterait une automatisation qui n’existe pas.',
    },
  },
  {
    id: 'exports',
    title: 'Exports servis',
    question: 'Quels exports l’API sert-elle réellement, avec leur provenance ?',
    status: { kind: 'served', contract: 'GET /api/v1/portfolio/export ; GET /api/v1/performance/{portfolio_id}/export' },
  },
  {
    id: 'backups',
    title: 'Sauvegardes',
    question: 'Quand la dernière sauvegarde a-t-elle été faite et restaurée ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucun contrat de sauvegarde n’est exposé par l’API ; la politique vit dans l’exploitation, pas dans l’interface.',
    },
  },
  {
    id: 'components-health',
    title: 'Santé des composants',
    question: 'La base, les snapshots, le worker et le flux répondent-ils ?',
    status: { kind: 'served', contract: `${CAPABILITIES} — health.db / attention_snapshot / capabilities_snapshot / worker` },
  },
  {
    id: 'unknown-probes',
    title: 'Sondes hors manifeste',
    question: 'Quelles sondes persistées ne correspondent à aucune capacité déclarée ?',
    status: { kind: 'served', contract: `${CAPABILITIES} — unknown_probed_capability_ids[]` },
  },
];

export function absentSourcesModules(): readonly (SourcesModule & {
  readonly status: Extract<SourcesModuleStatus, { kind: 'absent' }>;
})[] {
  return SOURCES_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function sourcesModule(id: string): SourcesModule {
  const module = SOURCES_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown sources module: ${id}`);
  }
  return module;
}
