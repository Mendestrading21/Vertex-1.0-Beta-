/**
 * Catalogue de la planche §2 (Marchés) — `pages-01-02-today-markets.png`,
 * moitié droite. Chaque module est SERVI par un contrat existant ou DÉCLARÉ
 * absent avec le motif mesuré ; aucun n'est simulé (article 17).
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';
import type { WidgetSize, WidgetVariant } from '../../components/widgets/Widget.tsx';

export type MarketsModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface MarketsModule {
  readonly id: string;
  /** Span de composition sur la planche — jamais une apparence (ADR-017). */
  readonly size: WidgetSize;
  /** Variante visuelle du vocabulaire fermé de WIDGET_LIBRARY.md. */
  readonly variant: WidgetVariant;
  readonly title: string;
  readonly question: string;
  readonly status: MarketsModuleStatus;
}

export const MARKETS_MODULES: readonly MarketsModule[] = [
  {
    id: 'sessions',
    size: 'S',
    variant: 'support',
    title: 'Sessions mondiales',
    question: 'Quelles places sont ouvertes à cet instant ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun contrat d’horaires de place ni de calendrier de séance n’est publié ; l’heure servie est celle du snapshot, pas celle des marchés.',
    },
  },
  {
    id: 'volatility',
    size: 'S',
    variant: 'support',
    title: 'Volatilité (indice)',
    question: 'La volatilité implicite du marché est-elle élevée ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun indice de volatilité n’est collecté. La volatilité implicite par contrat vit sur Options ; ce n’est pas un indice de marché.',
    },
  },
  {
    id: 'breadth',
    size: 'S',
    variant: 'support',
    title: 'Largeur de marché',
    question: 'Quelle part des instruments couverts progresse ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview — market.breadth' },
  },
  {
    id: 'market-health',
    size: 'M',
    variant: 'support',
    title: 'Santé des marchés',
    question: 'La couverture est-elle complète, et qu’a-t-on écarté ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview — coverage' },
  },
  {
    id: 'focus',
    size: 'M',
    variant: 'rail',
    title: 'Instruments suivis',
    question: 'Que font les instruments dont un dossier est publié : prix, variation, série ?',
    status: { kind: 'served', contract: 'GET /api/v1/analysis/{instrument} (candidats publiés par GET /api/v1/opportunities)' },
  },
  {
    id: 'market-map',
    size: 'XL',
    variant: 'dominant',
    title: 'Carte des marchés',
    question: 'Comment les secteurs et instruments suivis ont-ils évolué sur la dernière séance ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview — market.simple_return' },
  },
  {
    id: 'indices',
    size: 'S',
    variant: 'support',
    title: 'Indices',
    question: 'Comment les grands indices ont-ils clôturé ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun indice n’est déclaré dans l’univers suivi ; les instruments servis sont des titres, jamais un indice reconstitué.',
    },
  },
  {
    id: 'sectors',
    size: 'L',
    variant: 'support',
    title: 'Carte sectorielle',
    question: 'Quels secteurs portent la séance, instrument par instrument ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview — sectors' },
  },
  {
    id: 'rates-curve',
    size: 'S',
    variant: 'support',
    title: 'Courbe des taux',
    question: 'Comment la courbe des taux s’est-elle déformée ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'L’adaptateur des sources officielles sait lire FRED, mais aucune route ni aucun snapshot ne relaie une courbe de taux : sans contrat, rien n’est dessiné.',
    },
  },
  {
    id: 'fx',
    size: 'S',
    variant: 'support',
    title: 'Devises',
    question: 'Comment les devises ont-elles bougé face à la devise de référence ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune cotation de change n’est collectée ; la devise de chaque instrument est relayée telle que publiée, sans conversion.',
    },
  },
  {
    id: 'correlation',
    size: 'S',
    variant: 'support',
    title: 'Corrélation',
    question: 'Les grands actifs évoluent-ils ensemble ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'La matrice de corrélation de l’univers suivi vit sur Risques ; aucun snapshot ne publie une corrélation entre indices ou classes d’actifs.',
    },
  },
  {
    id: 'vol-structure',
    size: 'S',
    variant: 'support',
    title: 'Structure de volatilité',
    question: 'La volatilité implicite est-elle plus chère à court ou à long terme ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune surface ni terme de volatilité de marché n’est publié ; les IV par contrat d’Options ne forment pas une structure par échéance.',
    },
  },
  {
    id: 'discards',
    size: 'M',
    variant: 'support',
    title: 'Instruments écartés et rejets',
    question: 'Qu’a-t-on refusé d’afficher, et pourquoi ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview — coverage.discarded_tickers' },
  },
];

export function absentMarketsModules(): readonly (MarketsModule & {
  readonly status: Extract<MarketsModuleStatus, { kind: 'absent' }>;
})[] {
  return MARKETS_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function marketsModule(id: string): MarketsModule {
  const module = MARKETS_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown markets module: ${id}`);
  }
  return module;
}
