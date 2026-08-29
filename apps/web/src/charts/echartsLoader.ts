/**
 * Chargeur ECharts — UNIQUE point d'entrée du moteur de graphique.
 *
 * Ce module n'est jamais importé statiquement par une route : les composants
 * l'importent via `import('./…/echartsLoader.ts')`, donc Vite le découpe (avec
 * echarts) dans un chunk séparé chargé uniquement sur les routes qui dessinent
 * (règle CHART_STANDARD : aucun moteur de graphique dans le bundle initial).
 *
 * Imports modulaires `echarts/core` uniquement (WIDGET_LIBRARY) : la série
 * treemap, le tooltip, `AriaComponent` (accessibilité déclarée) et le renderer
 * Canvas. ECharts est sous licence Apache-2.0 (NOTICE conservée dans le
 * paquet npm ; mention visible dans le pied du cadre graphique).
 */
import { HeatmapChart, LineChart, TreemapChart } from 'echarts/charts';
import {
  AriaComponent,
  AxisPointerComponent,
  GridComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';

// Treemap : MarketMap (/markets). Ligne + grille cartésienne + repères
// (markLine/markPoint) : PayoffChart (/simulator). Ligne double grille +
// axisPointer lié : PerformanceChart (/performance). Heatmap + visualMap :
// MonthlyHeatmap (/performance). Le chunk reste unique et paresseux — aucun
// de ces modules n'entre dans le bundle initial.
echarts.use([
  TreemapChart,
  LineChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  AxisPointerComponent,
  MarkLineComponent,
  MarkPointComponent,
  VisualMapComponent,
  AriaComponent,
  CanvasRenderer,
]);

export { echarts };
export type EChartsInstance = ReturnType<typeof echarts.init>;
