/**
 * Catalogue de la planche §7 (Portefeuille) —
 * `pages-07-08-portfolio-charts.png`, moitié gauche. Chaque module est SERVI
 * par un contrat existant ou DÉCLARÉ absent avec le motif mesuré ; aucun
 * n'est simulé (article 17).
 *
 * Ce que la planche montre et que ce dépôt refuse ou ne publie pas : une
 * performance « du jour », un solde d'espèces, un benchmark, une allocation
 * par classe, une exposition par secteur ou par pays, une attribution, des
 * alertes de concentration. Le snapshot de valorisation publie des totaux
 * PAR DEVISE, des poids PAR TICKER et un indice de Herfindahl ; le snapshot
 * de performance publie TWR, XIRR et drawdown. L'interface ne fabrique aucun
 * agrégat manquant — et là où la planche emploie un vocabulaire de
 * transaction, ce dépôt ne connaît que des FAITS PASSÉS enregistrés.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';

export type PortfolioModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface PortfolioModule {
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: PortfolioModuleStatus;
}

const VALUATION = 'GET /api/v1/portfolio — valuation.content';
const PERFORMANCE = 'GET /api/v1/performance/{portfolio_id} — content';

export const PORTFOLIO_MODULES: readonly PortfolioModule[] = [
  {
    id: 'value',
    title: 'Valorisation publiée',
    question: 'Que valent mes lots ouverts, devise par devise, selon le worker ?',
    status: { kind: 'served', contract: `${VALUATION}.positions_by_currency[].concentration.total_value / unrealized / realized` },
  },
  {
    id: 'day-performance',
    title: 'Performance du jour',
    question: 'Combien le registre a-t-il varié depuis la séance précédente ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune variation quotidienne du registre n’est publiée : la valorisation est un instantané unique, sans instantané précédent à comparer. La variation d’un ticker publiée par Marchés n’est pas une variation du portefeuille.',
    },
  },
  {
    id: 'total-performance',
    title: 'Performance totale',
    question: 'Quel rendement pondéré par le temps et quel taux interne le serveur publie-t-il ?',
    status: { kind: 'served', contract: `${PERFORMANCE}.metrics.twr_* / xirr_*` },
  },
  {
    id: 'cash',
    title: 'Espèces',
    question: 'Quel solde d’espèces résulte des dépôts, retraits et frais déclarés ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Le snapshot de valorisation ne publie aucun solde d’espèces — seulement le compte des événements de trésorerie considérés. L’interface n’additionne pas le journal : un solde calculé ici serait une seconde vérité.',
    },
  },
  {
    id: 'performance',
    title: 'Performance',
    question: 'Quelle performance ai-je réellement enregistrée, avec quels risques et contributions ?',
    status: { kind: 'served', contract: `${PERFORMANCE}.series / metrics / heatmap` },
  },
  {
    id: 'benchmark',
    title: 'Benchmark',
    question: 'Comment le registre se compare-t-il à un indice de référence ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun indice de référence n’est collecté ni déclaré ; comparer le registre à un indice absent produirait un écart inventé.',
    },
  },
  {
    id: 'allocation',
    title: 'Allocation',
    question: 'Comment la valeur se répartit-elle entre classes d’actifs ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Le worker publie des valeurs par groupe que le contrat de vue ne type ni ne relaie ; aucune classe d’actif n’est déclarée par lot. Rien n’est regroupé côté navigateur.',
    },
  },
  {
    id: 'concentration',
    title: 'Concentration par ticker',
    question: 'Quelles expositions et concentrations résultent de mon ledger manuel ?',
    status: { kind: 'served', contract: `${VALUATION}.positions_by_currency[].concentration.weights / herfindahl_index` },
  },
  {
    id: 'sector-exposure',
    title: 'Exposition par secteur',
    question: 'Quels secteurs portent la valeur marquée ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Le secteur existe par ticker dans le snapshot Marchés, pas par lot dans la valorisation ; sommer des poids par secteur dans le navigateur serait un calcul de concentration hors de son propriétaire.',
    },
  },
  {
    id: 'country-exposure',
    title: 'Exposition par pays',
    question: 'Quels pays portent la valeur marquée ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune source ne publie le pays d’un instrument ni d’un lot.',
    },
  },
  {
    id: 'currency-exposure',
    title: 'Exposition par devise',
    question: 'Quelle valeur marquée chaque devise porte-t-elle ?',
    status: { kind: 'served', contract: `${VALUATION}.positions_by_currency[].currency / concentration.total_value` },
  },
  {
    id: 'concentration-alerts',
    title: 'Alertes de concentration',
    question: 'Quel poids dépasse un seuil déclaré ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Aucun seuil de concentration n’est déclaré ni publié ; un seuil choisi dans l’interface serait une règle de risque sans propriétaire.',
    },
  },
  {
    id: 'positions',
    title: 'Lots ouverts valorisés',
    question: 'Quels lots sont valorisés, lesquels sont exclus, et pourquoi ?',
    status: { kind: 'served', contract: `${VALUATION}.positions_by_currency[].unrealized.lots / excluded_lots` },
  },
  {
    id: 'attribution',
    title: 'Attribution',
    question: 'Quelle part de la performance vient de chaque ligne ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune attribution n’est publiée par le moteur de performance ; la décomposer dans le navigateur serait un calcul financier faisant autorité.',
    },
  },
  {
    id: 'dividends',
    title: 'Dividendes enregistrés',
    question: 'Quels dividendes ai-je déclarés au journal ?',
    status: { kind: 'served', contract: 'GET /api/v1/portfolio — transactions[kind = DIVIDEND]' },
  },
  {
    id: 'ledger',
    title: 'Journal',
    question: 'Quels faits passés ai-je déclarés, et lesquels sont compensés ?',
    status: { kind: 'served', contract: 'GET /api/v1/portfolio — transactions' },
  },
  {
    id: 'record-transaction',
    title: 'Déclarer un fait passé',
    question: 'Comment enregistrer un fait déjà survenu hors Vertex ?',
    status: { kind: 'served', contract: 'POST /api/v1/portfolio/transactions' },
  },
  {
    id: 'csv-import',
    title: 'Import CSV contrôlé',
    question: 'Comment importer un journal en deux temps, aperçu puis confirmation ?',
    status: { kind: 'served', contract: 'POST /api/v1/portfolio/import/preview puis /confirm' },
  },
];

export function absentPortfolioModules(): readonly (PortfolioModule & {
  readonly status: Extract<PortfolioModuleStatus, { kind: 'absent' }>;
})[] {
  return PORTFOLIO_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function portfolioModule(id: string): PortfolioModule {
  const module = PORTFOLIO_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown portfolio module: ${id}`);
  }
  return module;
}
