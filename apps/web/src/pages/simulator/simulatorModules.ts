/**
 * Catalogue de la planche §6 (Simulateur) — `pages-05-06-options-simulator.png`,
 * moitié droite. Chaque module est SERVI par un contrat existant ou DÉCLARÉ
 * absent avec le motif mesuré ; aucun n'est simulé (article 17).
 *
 * `POST /api/v1/simulations/preview` calcule TOUT côté serveur pour une
 * structure DÉCLARÉE : points de payoff, breakevens certifiés, extrêmes sur
 * la grille, grille de scénarios (spot × temps), vérification de risque
 * défini, écho des hypothèses, lignée des calculs et avertissements. Rien
 * n'est probabiliste : ni Monte-Carlo, ni probabilité de profit, ni stress
 * — aucune distribution n'est publiée, et l'afficher serait l'inventer.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';
import type { WidgetSize, WidgetVariant } from '../../components/widgets/Widget.tsx';

export type SimulatorModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface SimulatorModule {
  readonly id: string;
  /** Span de composition sur la planche — jamais une apparence (ADR-017). */
  readonly size: WidgetSize;
  /** Variante visuelle du vocabulaire fermé de WIDGET_LIBRARY.md. */
  readonly variant: WidgetVariant;
  readonly title: string;
  readonly question: string;
  readonly status: SimulatorModuleStatus;
}

const PREVIEW = 'POST /api/v1/simulations/preview';

export const SIMULATOR_MODULES: readonly SimulatorModule[] = [
  {
    id: 'base-parameters',
    size: 'M',
    variant: 'workflow-step',
    title: 'Hypothèses déclarées',
    question: 'Sous quel spot, quelle volatilité, quel taux et quelles grilles étudier ?',
    status: { kind: 'served', contract: `${PREVIEW} — assumptions (saisie, validée côté serveur)` },
  },
  {
    id: 'manual-entry',
    size: 'L',
    variant: 'workflow-step',
    title: 'Structure déclarée',
    question: 'Quelles jambes composent la structure étudiée ?',
    status: { kind: 'served', contract: `${PREVIEW} — legs (saisie bornée, validée côté serveur)` },
  },
  {
    id: 'scenarios',
    size: 'M',
    variant: 'support',
    title: 'Scénarios',
    question: 'Que vaut la structure selon le spot et le temps restant ?',
    status: { kind: 'served', contract: `${PREVIEW} — scenario_grid × scenario_spot_grid × scenario_time_grid_years` },
  },
  {
    id: 'payoff',
    size: 'XL',
    variant: 'dominant',
    title: 'Payoff à l’expiration',
    question: 'Que vaut la structure à l’expiration selon le spot ?',
    status: { kind: 'served', contract: `${PREVIEW} — payoff_points, breakevens` },
  },
  {
    id: 'monte-carlo',
    size: 'S',
    variant: 'support',
    title: 'Monte-Carlo',
    question: 'Quelle distribution de résultats une simulation donnerait-elle ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun calcul stochastique n’est au registre ; une distribution simulée sans modèle déclaré serait une probabilité non calibrée.',
    },
  },
  {
    id: 'kpi-served',
    size: 'S',
    variant: 'support',
    title: 'Résultats certifiés',
    question: 'Gain et perte maximaux sur la grille, breakevens, risque défini ?',
    status: { kind: 'served', contract: `${PREVIEW} — max_gain_on_grid, max_loss_on_grid, breakevens, defined_risk` },
  },
  {
    id: 'kpi-probabilistic',
    size: 'S',
    variant: 'support',
    title: 'Probabilité de profit',
    question: 'Quelle chance la structure a-t-elle de finir gagnante ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune probabilité calibrée, validée hors échantillon et versionnée n’est publiée ; sans elle, rien n’est affiché.',
    },
  },
  {
    id: 'stress-tests',
    size: 'S',
    variant: 'support',
    title: 'Chocs de marché',
    question: 'Que vaut la structure sous un choc de spot ou de volatilité ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun jeu de chocs n’est déclaré ni publié ; la grille de scénarios ne couvre que les spots et temps DÉCLARÉS par l’utilisateur.',
    },
  },
  {
    id: 'sensitivity',
    size: 'S',
    variant: 'support',
    title: 'Sensibilités',
    question: 'Comment la valeur réagit-elle à la volatilité, au temps, au taux ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Les Greeks par contrat existent sur Options ; aucun contrat n’agrège des sensibilités pour une structure déclarée.',
    },
  },
  {
    id: 'portfolio-impact',
    size: 'S',
    variant: 'support',
    title: 'Impact sur le portefeuille',
    question: 'Que changerait cette structure au portefeuille déclaré ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Le portefeuille est déclaré par l’utilisateur et valorisé par le worker ; aucun contrat ne combine une structure théorique avec cette valorisation.',
    },
  },
  {
    id: 'catalysts',
    size: 'S',
    variant: 'support',
    title: 'Catalyseurs du sous-jacent',
    question: 'Quels événements publiés concernent le sous-jacent transféré ?',
    status: { kind: 'served', contract: 'GET /api/v1/calendar — agenda filtré par ticker du transfert' },
  },
  {
    id: 'key-assumptions',
    size: 'S',
    variant: 'support',
    title: 'Hypothèses écho',
    question: 'Quelles hypothèses le serveur a-t-il réellement appliquées ?',
    status: { kind: 'served', contract: `${PREVIEW} — assumptions (écho serveur)` },
  },
  {
    id: 'sources',
    size: 'S',
    variant: 'support',
    title: 'Sources et provenance',
    question: 'D’où viennent les valeurs préremplies, et qu’est-ce qui est persisté ?',
    status: { kind: 'served', contract: 'transfert typé Options → Simulateur (état de navigation) ; sauvegarde NON_IMPLÉMENTÉ' },
  },
  {
    id: 'method',
    size: 'M',
    variant: 'support',
    title: 'Méthode et limites',
    question: 'Quels calculs, quelle nature de valeur, quels avertissements ?',
    status: { kind: 'served', contract: `${PREVIEW} — calculations, value_nature, warnings` },
  },
];

export function absentSimulatorModules(): readonly (SimulatorModule & {
  readonly status: Extract<SimulatorModuleStatus, { kind: 'absent' }>;
})[] {
  return SIMULATOR_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function simulatorModule(id: string): SimulatorModule {
  const module = SIMULATOR_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown simulator module: ${id}`);
  }
  return module;
}
