/**
 * Vue PURE de la page Aujourd'hui (LOT-A3) — le catalogue de la planche §1 et
 * les dérivations de présentation. Aucun calcul financier : on compte des
 * drapeaux, on lit des chaînes serveur, on prend le premier élément d'un
 * ordre PUBLIÉ. Rien n'est classé, noté ni estimé ici.
 */
import type { CapabilityEntry } from '../api/client.ts';
import type { AbsenceReason } from '../components/AbsentModule.tsx';
import type { CalendarEventView } from './calendar/calendarView.ts';
import { calendarEventsOf } from './calendar/calendarView.ts';
import type { CandidateView, OpportunitiesContentView } from './opportunities/opportunitiesView.ts';
import type { CurrencyBlockView, ValuationContentView } from './portfolio/portfolioView.ts';
import type { WidgetSize, WidgetVariant } from '../components/widgets/Widget.tsx';

export type TodayModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface TodayModule {
  readonly id: string;
  /** Span de composition sur la planche — jamais une apparence (ADR-017). */
  readonly size: WidgetSize;
  /** Variante visuelle du vocabulaire fermé de WIDGET_LIBRARY.md. */
  readonly variant: WidgetVariant;
  readonly title: string;
  readonly question: string;
  readonly status: TodayModuleStatus;
}

/**
 * Les onze modules de la planche `pages-01-02-today-markets.png` (moitié
 * gauche), dans l'ordre de lecture — plus « Instruments suivis », demandé
 * explicitement au-delà de la planche et servi par les dossiers d'analyse. Un module « servi » nomme son contrat ;
 * un module « absent » porte le motif MESURÉ de son absence.
 */
export const TODAY_MODULES: readonly TodayModule[] = [
  {
    id: 'regime',
    size: 'S',
    variant: 'support',
    title: 'Régime de marché',
    question: 'Dans quel régime le marché évolue-t-il, et avec quelle participation ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note:
        'Le moteur publie lui-même cette absence : la preuve « regime » manque à chaque candidat d’Opportunités (« no regime assessment exists for this population »). Aucun calcul de régime n’existe au registre.',
    },
  },
  {
    id: 'global-market',
    size: 'S',
    variant: 'support',
    title: 'Marché global',
    question: 'Le marché suivi progresse-t-il, et sur quelle largeur ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview' },
  },
  {
    id: 'volatility',
    size: 'S',
    variant: 'support',
    title: 'Volatilité',
    question: 'La volatilité réalisée et implicite sont-elles élevées ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note:
        'Aucun snapshot ne publie de volatilité réalisée ni d’indice de volatilité ; la volatilité implicite par contrat vit sur Options, elle n’est pas un indice.',
    },
  },
  {
    id: 'next-catalyst',
    size: 'S',
    variant: 'support',
    title: 'Catalyseur suivant',
    question: 'Quel est le prochain événement publié à l’agenda ?',
    status: { kind: 'served', contract: 'GET /api/v1/calendar' },
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
    id: 'source-health',
    size: 'S',
    variant: 'support',
    title: 'Santé des sources',
    question: 'Les sources sont-elles disponibles, fraîches et autorisées ?',
    status: { kind: 'served', contract: 'GET /api/v1/system/capabilities' },
  },
  {
    id: 'attention',
    size: 'XL',
    variant: 'dominant',
    title: 'File d’attention',
    question: 'Qu’est-ce qui mérite réellement mon attention maintenant ?',
    status: { kind: 'served', contract: 'GET /api/v1/today/attention' },
  },
  {
    id: 'opportunities',
    size: 'S',
    variant: 'support',
    title: 'Opportunités',
    question: 'Combien de candidats passent les gates, et lesquels ?',
    status: { kind: 'served', contract: 'GET /api/v1/opportunities' },
  },
  {
    id: 'active-risks',
    size: 'S',
    variant: 'support',
    title: 'Risques actifs',
    question: 'Quels risques nommés pèsent sur le contexte, et à quelle intensité ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note:
        'Aucune source ne nomme un risque actif ni son intensité. La matrice de corrélation de Risques est un autre objet : elle ne désigne aucun risque.',
    },
  },
  {
    id: 'sectors',
    size: 'L',
    variant: 'support',
    title: 'Carte sectorielle',
    question: 'Quels secteurs portent la séance, instrument par instrument ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview' },
  },
  {
    id: 'manual-portfolio',
    size: 'S',
    variant: 'support',
    title: 'Portefeuille manuel',
    question: 'Que vaut le portefeuille déclaré, aux marques publiées ?',
    status: { kind: 'served', contract: 'GET /api/v1/portfolio' },
  },
  {
    id: 'calendar',
    size: 'M',
    variant: 'support',
    title: 'Calendrier',
    question: 'Quels événements publiés arrivent ensuite ?',
    status: { kind: 'served', contract: 'GET /api/v1/calendar' },
  },
];

export function todayModule(id: string): TodayModule {
  const module = TODAY_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown today module: ${id}`);
  }
  return module;
}

export function absentTodayModules(): readonly (TodayModule & {
  readonly status: Extract<TodayModuleStatus, { kind: 'absent' }>;
})[] {
  return TODAY_MODULES.flatMap((module) =>
    module.status.kind === 'absent'
      ? [{ ...module, status: module.status }]
      : [],
  );
}

/**
 * Les premiers événements de l'agenda, DANS L'ORDRE PUBLIÉ. Le worker ordonne
 * l'agenda ; l'interface ne le retrie pas et ne choisit pas « le plus
 * important » — elle montre les premiers, et dit combien il y en a.
 */
export function leadingAgenda(agenda: readonly unknown[], count: number): readonly CalendarEventView[] {
  return calendarEventsOf(agenda).slice(0, count);
}

/** Recensement des statuts testés des capacités : un dénombrement, pas un score. */
export function capabilityStatusCensus(
  entries: readonly CapabilityEntry[],
): ReadonlyMap<CapabilityEntry['tested_status'], number> {
  const census = new Map<CapabilityEntry['tested_status'], number>();
  for (const entry of entries) {
    census.set(entry.tested_status, (census.get(entry.tested_status) ?? 0) + 1);
  }
  return census;
}

export interface OpportunitiesSummary {
  readonly universeSize: number | null;
  readonly qualifiedCount: number | null;
  readonly excludedCount: number | null;
  /** Candidats qualifiés dans l'ORDRE PUBLIÉ (méthode d'ordre serveur). */
  readonly qualified: readonly CandidateView[];
  readonly orderingMethod: string | null;
  readonly statusCounts: ReadonlyMap<string, number>;
}

export function opportunitiesSummaryOf(view: OpportunitiesContentView): OpportunitiesSummary {
  return {
    universeSize: view.coverage.universeSize,
    qualifiedCount: view.coverage.qualifiedCount,
    excludedCount: view.coverage.excludedCount,
    qualified: view.candidates.qualified,
    orderingMethod: view.ordering.method,
    statusCounts: view.coverage.statusCounts,
  };
}

export interface PortfolioSummary {
  readonly markPopulation: string | null;
  readonly asOf: string | null;
  readonly lotsValued: number | null;
  readonly lotsExcluded: number | null;
  readonly blocks: readonly CurrencyBlockView[];
}

export function portfolioSummaryOf(content: ValuationContentView): PortfolioSummary {
  return {
    markPopulation: content.markPopulation,
    asOf: content.asOf,
    lotsValued: content.coverage.lotsValued,
    lotsExcluded: content.coverage.lotsExcluded,
    blocks: content.blocks,
  };
}
