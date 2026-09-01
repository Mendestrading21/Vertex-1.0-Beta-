import { useEffect, useRef, useState } from 'react';

import type { EChartsInstance } from '../../../charts/echartsLoader.ts';
import { geometryNumber } from './performanceView.ts';
import type { HeatmapView } from './performanceView.ts';

/**
 * Heatmap mensuelle ECharts (années × mois) + table équivalente rendue par
 * la page. Les mois INCOMPLETS sont marqués (◐ sur la tuile, raisons dans la
 * table) — un mois partiel ne se présente jamais comme un mois plein.
 *
 * Statut non-OK : la page affiche le statut + raison à la place du visuel.
 */

function cssToken(name: string): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function MonthlyHeatmap({ heatmap }: { readonly heatmap: HeatmapView }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsInstance | null>(null);
  const [engineFailed, setEngineFailed] = useState(false);

  useEffect(() => {
    let disposed = false;
    let resizeObserver: ResizeObserver | null = null;

    async function mount(): Promise<void> {
      const container = containerRef.current;
      if (container === null || heatmap.status !== 'OK') {
        return;
      }
      try {
        const { echarts } = await import('../../../charts/echartsLoader.ts');
        if (disposed || containerRef.current === null) {
          return;
        }
        const years = [...new Set(heatmap.months.map((month) => month.month.slice(0, 4)))].sort();
        const monthLabels = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
        const byMonth = new Map(heatmap.months.map((month) => [month.month, month]));
        const cells: [number, number, number][] = [];
        let maxAbs = 0;
        for (const month of heatmap.months) {
          const value = geometryNumber(month.ret);
          if (value === null) {
            continue;
          }
          const yearIndex = years.indexOf(month.month.slice(0, 4));
          const monthIndex = Number(month.month.slice(5, 7)) - 1;
          cells.push([monthIndex, yearIndex, value]);
          maxAbs = Math.max(maxAbs, Math.abs(value));
        }
        const chart = chartRef.current ?? echarts.init(containerRef.current);
        chartRef.current = chart;
        chart.setOption(
          {
            animation: false,
            aria: { enabled: true },
            tooltip: {
              backgroundColor: cssToken('--vx-surface-2'),
              borderColor: cssToken('--vx-border'),
              textStyle: { color: cssToken('--vx-text'), fontSize: 12 },
              formatter: (params: unknown): string => {
                const item = params as { value?: unknown } | undefined;
                const value = Array.isArray(item?.value) ? item.value : [];
                const monthIndex = typeof value[0] === 'number' ? value[0] : 0;
                const yearIndex = typeof value[1] === 'number' ? value[1] : 0;
                const key = `${years[yearIndex] ?? ''}-${monthLabels[monthIndex] ?? ''}`;
                const month = byMonth.get(key);
                if (month === undefined) {
                  return key;
                }
                return [
                  key,
                  `rendement du mois : ${month.retPct} %`,
                  month.complete
                    ? 'mois complet'
                    : `mois INCOMPLET : ${month.incompleteReasons.join(', ')}`,
                ].join('<br/>');
              },
            },
            grid: { left: 64, right: 88, top: 16, bottom: 32 },
            xAxis: {
              type: 'category',
              data: monthLabels,
              axisLabel: { color: cssToken('--vx-text-muted'), fontSize: 11 },
            },
            yAxis: {
              type: 'category',
              data: years,
              axisLabel: { color: cssToken('--vx-text-muted'), fontSize: 11 },
            },
            visualMap: {
              min: -maxAbs || -1,
              max: maxAbs || 1,
              calculable: false,
              orient: 'vertical',
              right: 8,
              top: 'center',
              textStyle: { color: cssToken('--vx-text-muted'), fontSize: 11 },
              inRange: {
                color: [
                  cssToken('--vx-negative'),
                  cssToken('--vx-surface-3'),
                  cssToken('--vx-positive'),
                ],
              },
            },
            series: [
              {
                type: 'heatmap',
                data: cells,
                label: {
                  show: true,
                  fontSize: 11,
                  color: cssToken('--vx-black'),
                  formatter: (params: unknown): string => {
                    const item = params as { value?: unknown } | undefined;
                    const value = Array.isArray(item?.value) ? item.value : [];
                    const monthIndex = typeof value[0] === 'number' ? value[0] : 0;
                    const yearIndex = typeof value[1] === 'number' ? value[1] : 0;
                    const key = `${years[yearIndex] ?? ''}-${monthLabels[monthIndex] ?? ''}`;
                    const month = byMonth.get(key);
                    if (month === undefined) {
                      return '';
                    }
                    return month.complete ? `${month.retPct} %` : `◐ ${month.retPct} %`;
                  },
                },
                itemStyle: {
                  borderColor: cssToken('--vx-surface-0'),
                  borderWidth: 1,
                },
              },
            ],
          },
          true,
        );
        resizeObserver = new ResizeObserver(() => {
          chartRef.current?.resize();
        });
        resizeObserver.observe(container);
      } catch {
        if (!disposed) {
          setEngineFailed(true);
        }
      }
    }

    void mount();
    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, [heatmap]);

  if (heatmap.status !== 'OK') {
    return (
      <p className="vx-cell-absent" role="status" data-testid="perf-heatmap-absent">
        Heatmap non disponible — statut serveur <code>{heatmap.status}</code>
        {heatmap.reason !== null ? ` (raison : ${heatmap.reason})` : null} : aucun mois n'est affiché
        à la place.
      </p>
    );
  }

  if (engineFailed) {
    return (
      <p className="vx-perf-chart-fallback" role="status">
        Le moteur de heatmap n'a pas pu être chargé — la table mensuelle ci-dessous reste la
        référence complète des mêmes valeurs.
      </p>
    );
  }

  return (
    <figure className="vx-perf-heatmap" aria-label="Heatmap des rendements mensuels">
      <div
        ref={containerRef}
        className="vx-perf-heatmap-canvas"
        role="img"
        aria-label={`Rendements mensuels TWR (chaînage des périodes) sur ${heatmap.months.length} mois — les valeurs exactes et les mois incomplets sont listés dans la table mensuelle ci-dessous.`}
        data-testid="perf-heatmap-canvas"
      />
      <figcaption className="vx-perf-chart-caption">
        ◐ marque un mois incomplet (début/fin de série ou jour exclu). Méthode serveur :{' '}
        {heatmap.method ?? '—'}.
      </figcaption>
    </figure>
  );
}
