import { useEffect, useRef, useState } from 'react';

import type { LightweightChartApi } from '../../charts/lightweightChartsLoader.ts';
import type { OhlcvBar } from './analysisView.ts';
import { geometryNumber } from './analysisView.ts';

/**
 * CandleChart — chandeliers + volume (dominante de /analysis).
 *
 * Moteur : Lightweight Charts™ (TradingView, Inc., Apache-2.0, version
 * épinglée exacte), importé DYNAMIQUEMENT via
 * `charts/lightweightChartsLoader.ts` — chunk séparé, jamais dans le bundle
 * initial. ATTRIBUTION OBLIGATOIRE : la mention TradingView du pied de cadre
 * (lien https://www.tradingview.com/) reste visible en permanence.
 *
 * Aucune donnée n'est calculée ici : les 60 barres serveur (chaînes
 * décimales verbatim) sont seulement parsées pour la géométrie du rendu.
 * Aucun overlay (0 sur les 2 admis par CHART_STANDARD pour ce socle).
 * L'équivalence d'accès complète est la table OHLCV rendue par la page.
 */

function cssToken(name: string): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export interface CandleChartProps {
  readonly bars: readonly OhlcvBar[];
  /** Description courte lue par les lecteurs d'écran. */
  readonly description: string;
}

export function CandleChart({ bars, description }: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<LightweightChartApi | null>(null);
  const [engineFailed, setEngineFailed] = useState(false);

  useEffect(() => {
    let disposed = false;

    async function mount(): Promise<void> {
      const container = containerRef.current;
      if (container === null) {
        return;
      }
      try {
        // Import dynamique : lightweight-charts vit dans son propre chunk.
        const { CandlestickSeries, HistogramSeries, createChart } = await import(
          '../../charts/lightweightChartsLoader.ts'
        );
        if (disposed || containerRef.current === null) {
          return;
        }
        chartRef.current?.remove();
        const chart = createChart(containerRef.current, {
          autoSize: true,
          layout: {
            background: { color: cssToken('--vx-surface-0') },
            textColor: cssToken('--vx-text-secondary'),
            attributionLogo: true, // logo TradingView du moteur, jamais retiré
          },
          grid: {
            vertLines: { color: cssToken('--vx-border') },
            horzLines: { color: cssToken('--vx-border') },
          },
          timeScale: { borderColor: cssToken('--vx-border') },
          rightPriceScale: { borderColor: cssToken('--vx-border') },
        });
        chartRef.current = chart;

        const candles = chart.addSeries(CandlestickSeries, {
          upColor: cssToken('--vx-positive'),
          downColor: cssToken('--vx-negative'),
          borderUpColor: cssToken('--vx-positive'),
          borderDownColor: cssToken('--vx-negative'),
          wickUpColor: cssToken('--vx-positive'),
          wickDownColor: cssToken('--vx-negative'),
        });
        candles.setData(
          bars.map((bar) => ({
            time: bar.tradingDay,
            open: geometryNumber(bar.open),
            high: geometryNumber(bar.high),
            low: geometryNumber(bar.low),
            close: geometryNumber(bar.close),
          })),
        );

        const volume = chart.addSeries(HistogramSeries, {
          priceScaleId: 'volume',
          priceFormat: { type: 'volume' },
          color: cssToken('--vx-text-muted'),
        });
        chart.priceScale('volume').applyOptions({
          scaleMargins: { top: 0.8, bottom: 0 },
        });
        volume.setData(
          bars.map((bar) => ({
            time: bar.tradingDay,
            value: bar.volume,
          })),
        );

        chart.timeScale().fitContent();
      } catch {
        if (!disposed) {
          setEngineFailed(true);
        }
      }
    }

    void mount();
    return () => {
      disposed = true;
      chartRef.current?.remove();
      chartRef.current = null;
    };
  }, [bars]);

  if (engineFailed) {
    return (
      <p className="vx-candles-fallback" role="status">
        Le moteur de chandeliers n'a pas pu être chargé — la table OHLCV ci-dessous reste la
        référence complète des mêmes valeurs.
      </p>
    );
  }

  return (
    <figure className="vx-candles" aria-label="Chandeliers et volume">
      {/* Pas de role="img" ici : le moteur insère son propre lien
          d'attribution (interactif) dans le conteneur — la description
          accessible est portée par le texte masqué ci-dessous et la table
          OHLCV équivalente. */}
      <p className="vx-visually-hidden">{description}</p>
      <div ref={containerRef} className="vx-candles-canvas" data-testid="candles-canvas" />
      <figcaption className="vx-candles-caption">
        Chandeliers OHLC + volume (60 barres serveur, aucun overlay). La table OHLCV ci-dessous
        contient exactement les mêmes valeurs.{' '}
        <span className="vx-candles-attribution">
          Graphique rendu avec Lightweight Charts™ —{' '}
          <a href="https://www.tradingview.com/" rel="noopener noreferrer" target="_blank">
            TradingView
          </a>{' '}
          (Apache-2.0).
        </span>
      </figcaption>
    </figure>
  );
}
