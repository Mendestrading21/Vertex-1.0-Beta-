import type { AbsenceReason } from '../../components/AbsentModule.tsx';

/**
 * Graphiques — vue pure : le CATALOGUE des modules de la planche canonique
 * (`pages-07-08-portfolio-charts.png`, moitié droite ; `references/pages.md`
 * §8) et, pour chacun, ce que le serveur publie aujourd'hui.
 *
 * POURQUOI UN CATALOGUE. La consigne produit est « affichage d'abord,
 * branchements ensuite ». Cet ordre n'est honnête qu'à une condition : chaque
 * module de la planche est PRÉSENT, à sa place, soit servi par un contrat,
 * soit déclaré absent avec un motif du vocabulaire fermé d'`AbsentModule`.
 * Un test lit ce catalogue et exige que la page rende les douze — servis ou
 * déclarés —, ce qu'une capture seule ne prouverait pas.
 *
 * Aucun chiffre ici, aucune donnée : des titres, des questions et des motifs.
 * Les valeurs viennent uniquement d'`AnalysisResponse`, dans la page.
 */

export type ChartsModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface ChartsModule {
  /** Identifiant stable, utilisé par les tests et les `data-module`. */
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: ChartsModuleStatus;
}

const ANALYSIS_CONTRACT = 'GET /api/v1/analysis/{instrument}';

/**
 * Les douze modules de la planche, dans son ordre de lecture.
 *
 * Les trois premiers sont servis par le contrat Analyse — même DTO, même
 * client, même composant de rendu que `/analysis`. Ce n'est pas un second
 * propriétaire de donnée : le propriétaire est le contrat, et cette page ne
 * fait que l'afficher sous SA question (« quelles relations puis-je explorer
 * sans perdre méthode et contexte ? »).
 *
 * Les neuf autres portent le motif EXACT de leur absence, mesuré dans le
 * dépôt le 2026-09-02 — jamais une promesse de livraison.
 */
export const CHARTS_MODULES: readonly ChartsModule[] = [
  {
    id: 'main-chart',
    title: 'Espace graphique',
    question: 'Que publie le serveur de la série de cet instrument ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'volume',
    title: 'Volume',
    question: 'Quel volume accompagne chaque barre publiée ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'served-indicators',
    title: 'Indicateurs servis',
    question: 'Quelles mesures le moteur serveur publie-t-il sur cette série ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'overlays',
    title: 'Overlays (moyennes mobiles)',
    question: 'Quelles moyennes mobiles superposer à la série ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun calcul de moyenne mobile n’est déclaré au registre des calculs ni publié par un snapshot.',
    },
  },
  {
    id: 'rsi',
    title: 'RSI',
    question: 'Où se situe la force relative de la série sur sa fenêtre ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun calcul RSI n’est déclaré au registre des calculs ni publié par un snapshot.',
    },
  },
  {
    id: 'macd',
    title: 'MACD',
    question: 'Comment évoluent les moyennes mobiles convergentes et divergentes ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun calcul MACD n’est déclaré au registre des calculs ni publié par un snapshot.',
    },
  },
  {
    id: 'comparison',
    title: 'Comparaison base 100',
    question: 'Comment cette série se compare-t-elle à d’autres, ramenées à une base commune ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Le calcul `market.rebased_series` est approuvé au registre et implémenté dans vertex_core, mais aucun snapshot ni aucune route ne le relaie. Le rebaser ici créerait une seconde autorité.',
    },
  },
  {
    id: 'synchronized',
    title: 'Graphiques synchronisés',
    question: 'Quelles séries lire côte à côte sur le même calendrier ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Plusieurs séries alignées sur un calendrier commun exigent un contrat d’alignement que rien ne publie.',
    },
  },
  {
    id: 'selected-object',
    title: 'Objet sélectionné',
    question: 'Quels niveaux ou annotations ai-je posés sur cette série ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Un objet dessiné est une donnée utilisateur persistée : le propriétaire n’a pas tranché où elle vit ni sous quel contrat.',
    },
  },
  {
    id: 'linked-alerts',
    title: 'Alertes liées',
    question: 'Quelles alertes surveillent cette série ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: '« Alertes » est une capacité globale de la barre supérieure, pas un module de page ; son contrat n’existe pas.',
    },
  },
  {
    id: 'layouts',
    title: 'Agencement',
    question: 'Comment disposer plusieurs vues de cette série ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Un agencement enregistré est une préférence utilisateur persistée, sans propriétaire ni contrat décidés.',
    },
  },
  {
    id: 'saved-studies',
    title: 'Études sauvegardées',
    question: 'Quelles études ai-je enregistrées pour y revenir ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Une étude sauvegardée est une donnée utilisateur persistée, sans propriétaire ni contrat décidés.',
    },
  },
];

export function servedModules(): readonly ChartsModule[] {
  return CHARTS_MODULES.filter((module) => module.status.kind === 'served');
}

export function absentModules(): readonly (ChartsModule & {
  readonly status: Extract<ChartsModuleStatus, { kind: 'absent' }>;
})[] {
  return CHARTS_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}
