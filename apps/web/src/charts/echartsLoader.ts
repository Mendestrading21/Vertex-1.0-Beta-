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
import { TreemapChart } from 'echarts/charts';
import { AriaComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([TreemapChart, TooltipComponent, AriaComponent, CanvasRenderer]);

export { echarts };
export type EChartsInstance = ReturnType<typeof echarts.init>;
