/**
 * Chargeur Lightweight Charts™ — UNIQUE point d'entrée du moteur de
 * chandeliers (page Analyse).
 *
 * Comme `echartsLoader.ts`, ce module n'est jamais importé statiquement par
 * une route : les composants l'importent via
 * `import('./…/lightweightChartsLoader.ts')`, donc Vite le découpe (avec
 * lightweight-charts) dans un chunk séparé chargé uniquement sur la route
 * /analysis (règle CHART_STANDARD : aucun moteur de graphique dans le bundle
 * initial).
 *
 * Dépendance épinglée exacte : lightweight-charts 5.2.1, licence Apache-2.0
 * (TradingView, Inc.). CONDITION D'ATTRIBUTION : la mention TradingView avec
 * lien vers https://www.tradingview.com/ reste VISIBLE dans le pied du cadre
 * graphique qui utilise ce moteur (voir CandleChart.tsx) — ne jamais la
 * retirer ni la masquer.
 */
import {
  CandlestickSeries,
  HistogramSeries,
  createChart,
} from 'lightweight-charts';
import type { IChartApi } from 'lightweight-charts';

export { CandlestickSeries, HistogramSeries, createChart };
export type LightweightChartApi = IChartApi;
