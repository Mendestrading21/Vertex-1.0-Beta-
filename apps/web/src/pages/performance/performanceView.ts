/**
 * Lecture défensive du snapshot `performance/<portfolio_id>`, relayé
 * verbatim par l'API (`PerformanceSnapshotResponse.content`).
 *
 * Aucun rendement, drawdown ni ratio n'est calculé ici : chaque chiffre est
 * la chaîne serveur exacte. Un statut INSUFFICIENT_DATA ou INVALID est
 * affiché AVEC SA RAISON à la place de toute valeur — jamais un zéro.
 */
import { calculationMetaOf } from '../portfolio/portfolioView.ts';
import type { CalculationMetaView } from '../portfolio/portfolioView.ts';

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function asArray(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

function str(record: UnknownRecord | null, key: string): string | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function num(record: UnknownRecord | null, key: string): number | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

// -- vues -------------------------------------------------------------------

export interface SeriesPointView {
  readonly tradingDay: string;
  readonly at: string | null;
  readonly grossValue: string;
  readonly netValue: string;
  readonly cash: string | null;
  readonly positionValue: string | null;
  readonly feesCumulative: string | null;
  readonly lotsValued: number | null;
}

export interface ExcludedDayView {
  readonly tradingDay: string;
  readonly reason: string;
}

/** Un bloc métrique — soit OK avec ses valeurs, soit un statut + raison. */
export interface MetricBlockView {
  readonly status: string;
  readonly reason: string | null;
  readonly calculation: CalculationMetaView | null;
  /** TWR : rendement total (chaîne). */
  readonly totalReturn: string | null;
  readonly totalReturnPct: string | null;
  /** XIRR : taux annualisé (chaîne). */
  readonly rate: string | null;
  readonly ratePct: string | null;
  /** Drawdown : perte maximale (chaîne) + bornes. */
  readonly maxDrawdown: string | null;
  readonly maxDrawdownPct: string | null;
  readonly peakAt: string | null;
  readonly troughAt: string | null;
  readonly drawdownPoints: readonly { readonly tradingDay: string; readonly drawdown: string }[];
}

export interface HeatmapMonthView {
  readonly month: string;
  readonly ret: string;
  readonly retPct: string;
  readonly periods: number | null;
  readonly complete: boolean;
  readonly incompleteReasons: readonly string[];
}

export interface HeatmapView {
  readonly status: string;
  readonly reason: string | null;
  readonly method: string | null;
  readonly months: readonly HeatmapMonthView[];
}

export interface PerformanceContentView {
  readonly asOf: string | null;
  readonly engineVersion: string | null;
  readonly population: string | null;
  readonly populationMarks: string | null;
  readonly populationLedger: string | null;
  readonly currency: string | null;
  readonly lotMethod: string | null;
  readonly conventions: Readonly<Record<string, string>>;
  readonly seriesStatus: string;
  readonly seriesReason: string | null;
  readonly points: readonly SeriesPointView[];
  readonly excludedDays: readonly ExcludedDayView[];
  readonly metrics: Readonly<Record<MetricKey, MetricBlockView>>;
  readonly heatmap: HeatmapView;
  readonly coverage: {
    readonly daysWithClose: number | null;
    readonly daysValued: number | null;
    readonly daysExcluded: number | null;
    readonly coverageRatio: string | null;
    readonly externalCashflows: number | null;
  };
}

export const METRIC_KEYS = [
  'twr_gross',
  'twr_net',
  'xirr_gross',
  'xirr_net',
  'drawdown_gross',
  'drawdown_net',
] as const;
export type MetricKey = (typeof METRIC_KEYS)[number];

export const METRIC_LABELS: Readonly<Record<MetricKey, string>> = {
  twr_gross: 'TWR brut',
  twr_net: 'TWR net',
  xirr_gross: 'XIRR brut',
  xirr_net: 'XIRR net',
  drawdown_gross: 'Drawdown max brut',
  drawdown_net: 'Drawdown max net',
};

/** Définition d'une ligne (métrique, base brut/net) — affichée avec elle. */
export const METRIC_DEFINITIONS: Readonly<Record<MetricKey, string>> = {
  twr_gross:
    'Rendement pondéré par le temps (chaînage des périodes entre valorisations, flux externes au début de période), sur la valeur brute.',
  twr_net:
    'Même chaînage TWR sur la valeur nette (valeur brute moins frais déclarés cumulés du journal).',
  xirr_gross:
    'Taux de rendement interne annualisé des flux datés (dépôts négatifs, retraits positifs, valeur terminale positive), sur la valeur brute.',
  xirr_net: 'Même XIRR sur la valeur nette de frais déclarés.',
  drawdown_gross: 'Perte maximale depuis un sommet de la courbe de valeur brute.',
  drawdown_net: 'Perte maximale depuis un sommet de la courbe de valeur nette.',
};

const EMPTY_METRIC: MetricBlockView = {
  status: 'ABSENT',
  reason: 'metric_block_missing',
  calculation: null,
  totalReturn: null,
  totalReturnPct: null,
  rate: null,
  ratePct: null,
  maxDrawdown: null,
  maxDrawdownPct: null,
  peakAt: null,
  troughAt: null,
  drawdownPoints: [],
};

function metricBlockOf(value: unknown): MetricBlockView {
  const record = asRecord(value);
  if (record === null) {
    return EMPTY_METRIC;
  }
  const drawdownPoints = asArray(record['points'])
    .map((entry) => {
      const point = asRecord(entry);
      const tradingDay = str(point, 'trading_day');
      const drawdown = str(point, 'drawdown');
      if (tradingDay === null || drawdown === null) {
        return null;
      }
      return { tradingDay, drawdown };
    })
    .filter((entry): entry is { tradingDay: string; drawdown: string } => entry !== null);
  return {
    status: str(record, 'status') ?? 'ABSENT',
    reason: str(record, 'reason'),
    calculation: calculationMetaOf(record['calculation']),
    totalReturn: str(record, 'total_return'),
    totalReturnPct: str(record, 'total_return_pct'),
    rate: str(record, 'rate'),
    ratePct: str(record, 'rate_pct'),
    maxDrawdown: str(record, 'max_drawdown'),
    maxDrawdownPct: str(record, 'max_drawdown_pct'),
    peakAt: str(record, 'peak_at'),
    troughAt: str(record, 'trough_at'),
    drawdownPoints,
  };
}

function pointOf(value: unknown): SeriesPointView | null {
  const record = asRecord(value);
  const tradingDay = str(record, 'trading_day');
  const grossValue = str(record, 'gross_value');
  const netValue = str(record, 'net_value');
  if (record === null || tradingDay === null || grossValue === null || netValue === null) {
    return null;
  }
  return {
    tradingDay,
    at: str(record, 'at'),
    grossValue,
    netValue,
    cash: str(record, 'cash'),
    positionValue: str(record, 'position_value'),
    feesCumulative: str(record, 'fees_cumulative'),
    lotsValued: num(record, 'lots_valued'),
  };
}

/** Lit le contenu du snapshot. `null` si absent ou de version inattendue. */
export function performanceContentOf(content: unknown): PerformanceContentView | null {
  const record = asRecord(content);
  if (record === null || str(record, 'schema_version') !== 'vertex.performance/1.0') {
    return null;
  }
  const populationComponents = asRecord(record['population_components']);
  const conventionsRecord = asRecord(record['conventions']);
  const conventions: Record<string, string> = {};
  if (conventionsRecord !== null) {
    for (const key of Object.keys(conventionsRecord).sort()) {
      const value = conventionsRecord[key];
      if (typeof value === 'string') {
        conventions[key] = value;
      } else if (Array.isArray(value)) {
        conventions[key] = value.filter((entry): entry is string => typeof entry === 'string').join(', ');
      }
    }
  }
  const series = asRecord(record['series']);
  const metricsRecord = asRecord(record['metrics']);
  const metrics = Object.fromEntries(
    METRIC_KEYS.map((key) => [key, metricBlockOf(metricsRecord?.[key])]),
  ) as Record<MetricKey, MetricBlockView>;
  const heatmapRecord = asRecord(record['heatmap']);
  const months = asArray(heatmapRecord?.['months'])
    .map((entry): HeatmapMonthView | null => {
      const month = asRecord(entry);
      const label = str(month, 'month');
      const ret = str(month, 'return');
      const retPct = str(month, 'return_pct');
      if (month === null || label === null || ret === null || retPct === null) {
        return null;
      }
      return {
        month: label,
        ret,
        retPct,
        periods: num(month, 'periods'),
        complete: month['complete'] === true,
        incompleteReasons: asArray(month['incomplete_reasons']).filter(
          (reason): reason is string => typeof reason === 'string',
        ),
      };
    })
    .filter((month): month is HeatmapMonthView => month !== null);
  const coverage = asRecord(record['coverage']);
  return {
    asOf: str(record, 'as_of'),
    engineVersion: str(record, 'engine_version'),
    population: str(record, 'population'),
    populationMarks: str(populationComponents, 'marks'),
    populationLedger: str(populationComponents, 'ledger'),
    currency: str(record, 'currency'),
    lotMethod: str(record, 'lot_method'),
    conventions,
    seriesStatus: str(series, 'status') ?? 'ABSENT',
    seriesReason: str(series, 'reason'),
    points: asArray(series?.['points'])
      .map(pointOf)
      .filter((point): point is SeriesPointView => point !== null),
    excludedDays: asArray(series?.['excluded_days'])
      .map((entry) => {
        const day = asRecord(entry);
        const tradingDay = str(day, 'trading_day');
        const reason = str(day, 'reason');
        if (tradingDay === null || reason === null) {
          return null;
        }
        return { tradingDay, reason } satisfies ExcludedDayView;
      })
      .filter((day): day is ExcludedDayView => day !== null),
    metrics,
    heatmap: {
      status: str(heatmapRecord, 'status') ?? 'ABSENT',
      reason: str(heatmapRecord, 'reason'),
      method: str(heatmapRecord, 'method'),
      months,
    },
    coverage: {
      daysWithClose: num(coverage, 'days_with_close'),
      daysValued: num(coverage, 'days_valued'),
      daysExcluded: num(coverage, 'days_excluded'),
      coverageRatio: str(coverage, 'coverage_ratio'),
      externalCashflows: num(coverage, 'external_cashflows'),
    },
  };
}

/** Nombre pour la GÉOMÉTRIE de rendu (jamais réaffiché) ; null si illisible. */
export function geometryNumber(value: string | null): number | null {
  if (value === null) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
