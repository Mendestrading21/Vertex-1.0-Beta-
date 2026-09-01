import { useEffect, useRef, useState } from 'react';

import type { EChartsInstance } from '../../../charts/echartsLoader.ts';
import { geometryNumber } from './performanceView.ts';
import type { MetricBlockView, SeriesPointView } from './performanceView.ts';

/**
 * Dominante de /performance — courbe de valeur (brute + nette) et courbe de
 * drawdown, deux grilles empilées avec CURSEUR PARTAGÉ (axisPointer lié sur
 * l'axe des jours).
 *
 * Moteur ECharts importé DYNAMIQUEMENT (chunk paresseux existant, jamais
 * dans le bundle initial). Les chaînes serveur ne sont parsées que pour la
 * GÉOMÉTRIE du tracé ; le tooltip et la table équivalente affichent les
 * chaînes exactes.
 */

function cssToken(name: string): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function PerformanceChart({
  points,
  drawdown,
  currency,
}: {
  readonly points: readonly SeriesPointView[];
  readonly drawdown: MetricBlockView;
  readonly currency: string | null;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsInstance | null>(null);
  const [engineFailed, setEngineFailed] = useState(false);

  useEffect(() => {
    let disposed = false;
    let resizeObserver: ResizeObserver | null = null;

    async function mount(): Promise<void> {
      const container = containerRef.current;
      if (container === null) {
        return;
      }
      try {
        const { echarts } = await import('../../../charts/echartsLoader.ts');
        if (disposed || containerRef.current === null) {
          return;
        }
        const days = points.map((point) => point.tradingDay);
        const gross = points.map((point) => geometryNumber(point.grossValue));
        const net = points.map((point) => geometryNumber(point.netValue));
        const drawdownByDay = new Map(
          drawdown.drawdownPoints.map((point) => [point.tradingDay, point.drawdown]),
        );
        const drawdownSeries = days.map((day) => geometryNumber(drawdownByDay.get(day) ?? null));
        const exactByDay = new Map(points.map((point) => [point.tradingDay, point]));

        const chart = chartRef.current ?? echarts.init(containerRef.current);
        chartRef.current = chart;
        chart.setOption(
          {
            animation: false,
            aria: { enabled: true },
            axisPointer: {
              // Curseur PARTAGÉ entre la grille valeur et la grille drawdown.
              link: [{ xAxisIndex: 'all' }],
              label: { backgroundColor: cssToken('--vx-surface-3') },
            },
            tooltip: {
              trigger: 'axis',
              backgroundColor: cssToken('--vx-surface-2'),
              borderColor: cssToken('--vx-border'),
              textStyle: { color: cssToken('--vx-text'), fontSize: 12 },
              // Les valeurs affichées sont les CHAÎNES SERVEUR exactes.
              formatter: (params: unknown): string => {
                const list = Array.isArray(params) ? params : [params];
                const first = list[0] as { axisValue?: unknown } | undefined;
                const day = typeof first?.axisValue === 'string' ? first.axisValue : '';
                const point = exactByDay.get(day);
                if (point === undefined) {
                  return day;
                }
                const dd = drawdownByDay.get(day);
                const unit = currency ?? '';
                return [
                  day,
                  `valeur brute : ${point.grossValue} ${unit}`,
                  `valeur nette : ${point.netValue} ${unit}`,
                  dd !== undefined ? `drawdown : ${dd}` : 'drawdown : —',
                ].join('<br/>');
              },
            },
            grid: [
              { left: 72, right: 24, top: 24, height: '52%' },
              { left: 72, right: 24, top: '68%', height: '22%' },
            ],
            xAxis: [
              {
                type: 'category',
                gridIndex: 0,
                data: [...days],
                axisLabel: { show: false },
                axisLine: { lineStyle: { color: cssToken('--vx-border-strong') } },
              },
              {
                type: 'category',
                gridIndex: 1,
                data: [...days],
                axisLabel: { color: cssToken('--vx-text-muted'), fontSize: 11 },
                axisLine: { lineStyle: { color: cssToken('--vx-border-strong') } },
              },
            ],
            yAxis: [
              {
                type: 'value',
                gridIndex: 0,
                scale: true,
                name: currency !== null ? `Valeur (${currency})` : 'Valeur',
                nameTextStyle: { color: cssToken('--vx-text-muted') },
                axisLabel: { color: cssToken('--vx-text-muted'), fontSize: 11 },
                splitLine: { lineStyle: { color: cssToken('--vx-border-soft') } },
              },
              {
                type: 'value',
                gridIndex: 1,
                name: 'Drawdown',
                nameTextStyle: { color: cssToken('--vx-text-muted') },
                axisLabel: { color: cssToken('--vx-text-muted'), fontSize: 11 },
                splitLine: { lineStyle: { color: cssToken('--vx-border-soft') } },
              },
            ],
            series: [
              {
                name: 'Valeur brute',
                type: 'line',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: [...gross],
                showSymbol: points.length <= 60,
                lineStyle: { color: cssToken('--vx-silver'), width: 2 },
                itemStyle: { color: cssToken('--vx-silver') },
              },
              {
                name: 'Valeur nette',
                type: 'line',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: [...net],
                showSymbol: false,
                lineStyle: { color: cssToken('--vx-macro'), width: 1, type: 'dashed' },
                itemStyle: { color: cssToken('--vx-macro') },
              },
              {
                name: 'Drawdown',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: [...drawdownSeries],
                showSymbol: false,
                areaStyle: { opacity: 0.25 },
                lineStyle: { color: cssToken('--vx-negative'), width: 1 },
                itemStyle: { color: cssToken('--vx-negative') },
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
  }, [points, drawdown, currency]);

  if (engineFailed) {
    return (
      <p className="vx-perf-chart-fallback" role="status">
        Le moteur de graphique n'a pas pu être chargé — la table des points quotidiens ci-dessous
        reste la référence complète des mêmes valeurs.
      </p>
    );
  }

  return (
    <figure className="vx-perf-chart" aria-label="Courbes de valeur et de drawdown">
      <div
        ref={containerRef}
        className="vx-perf-chart-canvas"
        role="img"
        aria-label={`Courbe de valeur (brute et nette${currency !== null ? `, en ${currency}` : ''}) et courbe de drawdown sur ${points.length} jour(s) ouvrable(s) valorisé(s) — les valeurs exactes sont dans la table quotidienne ci-dessous.`}
        data-testid="perf-chart-canvas"
      />
      <figcaption className="vx-perf-chart-caption">
        Haut : valeur brute (trait plein) et nette (pointillé). Bas : drawdown depuis le sommet.
        Curseur partagé entre les deux grilles ; valeurs exactes (chaînes serveur) au survol et dans
        la table quotidienne.
      </figcaption>
    </figure>
  );
}
