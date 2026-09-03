/**
 * Catalogue de la planche §9 (Risques) — `pages-09-10-risks-catalysts.png`,
 * moitié gauche. Chaque module est SERVI par un contrat existant ou DÉCLARÉ
 * absent avec le motif mesuré ; aucun n'est simulé (article 17).
 *
 * Ce que la planche montre et que ce dépôt ne publie pas : un score de
 * risque, une VaR, une volatilité du registre, une liquidité, des chocs, des
 * facteurs, un budget de risque, un radar, un registre de risques à sévérité
 * et horizon (`docs/05-design/PAGE_ARBITRATION.md` : aucune source ne publie
 * sévérité ni horizon par risque). Ce qui EST publié : la matrice de
 * corrélation et sa couverture (`risk_matrix/global`), la concentration du
 * registre (`portfolio_valuation`), le drawdown (`performance`). La page
 * refuse tout score global dérivé de mesures partielles.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';

export type RiskModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface RiskModule {
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: RiskModuleStatus;
}

const MATRIX = 'GET /api/v1/risk/matrix — content';
const VALUATION = 'GET /api/v1/portfolio — valuation.content';
const PERFORMANCE = 'GET /api/v1/performance/{portfolio_id} — content';

export const RISK_MODULES: readonly RiskModule[] = [
  {
    id: 'risk-score',
    title: 'Score de risque',
    question: 'Quel niveau de risque global le portefeuille porte-t-il ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun score n’est publié, et le contrat interdit un score global dérivé de mesures partielles : une jauge verte sur des risques non mesurés serait un faux rassurant.',
    },
  },
  {
    id: 'var-cvar',
    title: 'VaR et CVaR',
    question: 'Quelle perte le registre peut-il subir à un horizon et un niveau donnés ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune distribution de pertes n’est publiée ; une VaR exige une probabilité calibrée et validée hors échantillon, qu’aucun contrat ne fournit.',
    },
  },
  {
    id: 'max-drawdown',
    title: 'Drawdown maximal',
    question: 'Quelle baisse maximale la série valorisée a-t-elle subie depuis son sommet ?',
    status: { kind: 'served', contract: `${PERFORMANCE}.metrics.drawdown_gross / drawdown_net` },
  },
  {
    id: 'benchmark-relative',
    title: 'Risque relatif au benchmark',
    question: 'Comment le risque se compare-t-il à celui d’un indice ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun indice de référence n’est collecté ni déclaré.',
    },
  },
  {
    id: 'volatility',
    title: 'Volatilité du registre',
    question: 'Quelle dispersion des rendements quotidiens le registre montre-t-il ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'La série quotidienne de valorisation est publiée, mais aucun contrat n’en publie la dispersion ; la calculer dans le navigateur serait un calcul de risque hors de son propriétaire.',
    },
  },
  {
    id: 'concentration',
    title: 'Concentration du registre',
    question: 'Quels poids par ticker et quel indice de Herfindahl la valorisation publie-t-elle ?',
    status: { kind: 'served', contract: `${VALUATION}.positions_by_currency[].concentration` },
  },
  {
    id: 'liquidity',
    title: 'Liquidité',
    question: 'En combien de séances chaque ligne se réduirait-elle sans peser sur le prix ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun volume moyen ni profondeur de carnet n’est rapporté à une taille de ligne.',
    },
  },
  {
    id: 'correlations',
    title: 'Corrélations',
    question: 'Qu’est-ce qui bouge ensemble dans mon périmètre, et qu’est-ce qui protège de quoi ?',
    status: { kind: 'served', contract: `${MATRIX}.matrix / matrix_bands / instruments` },
  },
  {
    id: 'turnover',
    title: 'Rotation',
    question: 'À quel rythme le registre se renouvelle-t-il ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Le journal est publié ligne à ligne, mais aucun contrat n’en publie une rotation ; la dériver ici serait un ratio financier calculé dans le navigateur.',
    },
  },
  {
    id: 'extremes',
    title: 'Paires extrêmes',
    question: 'Quelle paire est la plus liée, laquelle la plus opposée ?',
    status: { kind: 'served', contract: `${MATRIX}.extremes / synchronicity_warning` },
  },
  {
    id: 'stress-loss',
    title: 'Chocs',
    question: 'Que perdrait le registre sous un choc de marché déclaré ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun scénario de choc n’est déclaré ni repricé ; rien de probabiliste ni de contrefactuel n’est publié pour le registre.',
    },
  },
  {
    id: 'factor-exposures',
    title: 'Expositions aux facteurs',
    question: 'À quels facteurs le registre est-il exposé ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun modèle de facteurs n’est publié.',
    },
  },
  {
    id: 'risk-budget',
    title: 'Budget de risque',
    question: 'Quelle part du risque total chaque ligne consomme-t-elle ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Sans volatilité ni VaR publiées, aucune contribution au risque n’existe.',
    },
  },
  {
    id: 'radar',
    title: 'Radar des risques',
    question: 'Comment les familles de risque se comparent-elles d’un coup d’œil ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Un radar suppose une note par famille de risque ; aucune n’est publiée, et une note choisie ici serait un score.',
    },
  },
  {
    id: 'coverage',
    title: 'Couverture de la matrice',
    question: 'Sur quoi cette matrice est-elle bâtie ?',
    status: { kind: 'served', contract: `${MATRIX}.coverage` },
  },
  {
    id: 'alignment',
    title: "Ce que l'alignement a coûté",
    question: 'Combien de séances chaque instrument a-t-il perdues à l’alignement ?',
    status: { kind: 'served', contract: `${MATRIX}.coverage.trading_days_lost_to_alignment / trading_days_per_instrument` },
  },
  {
    id: 'discards',
    title: 'Instruments écartés',
    question: 'Quels instruments du périmètre n’ont pas pu entrer dans la matrice ?',
    status: { kind: 'served', contract: `${MATRIX}.coverage.discarded / rejected_records` },
  },
  {
    id: 'risk-register',
    title: 'Registre des risques',
    question: 'Quels risques sont actifs, mesurés, inconnus ou bloquants, avec quelle sévérité ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucune source ne publie sévérité, horizon ni preuve par risque ; un registre saisi dans l’interface serait une matrice sans propriétaire de mesure.',
    },
  },
  {
    id: 'alert-log',
    title: 'Journal des alertes de risque',
    question: 'Quelles alertes de risque ont été émises, et quand ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune alerte de risque n’est émise ni journalisée.',
    },
  },
];

export function absentRiskModules(): readonly (RiskModule & {
  readonly status: Extract<RiskModuleStatus, { kind: 'absent' }>;
})[] {
  return RISK_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function riskModule(id: string): RiskModule {
  const module = RISK_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown risk module: ${id}`);
  }
  return module;
}
