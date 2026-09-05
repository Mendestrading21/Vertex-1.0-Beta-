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
            textColor: cssToken('--vx-text-muted'),
            // « Mono/tabular pour prix, dates, unités et codes »
            // (`canonical-visual.md`). Les étiquettes d'axe SONT des prix et
            // des dates : en sans-serif proportionnelle, leurs chiffres ne
            // s'alignent pas d'une graduation à l'autre.
            fontFamily: cssToken('--vx-font-mono'),
            fontSize: 11,
            attributionLogo: true, // logo TradingView du moteur, jamais retiré
          },
          grid: {
            // `--vx-grid-line` (0,045) et non `--vx-border` (0,12) : le contrat
            // veut un décor « sous le niveau de contraste du texte ». À 0,12,
            // la grille se lisait aussi bien que les chandeliers qu'elle est
            // censée servir.
            vertLines: { color: cssToken('--vx-grid-line') },
            horzLines: { color: cssToken('--vx-grid-line') },
          },
          crosshair: {
            vertLine: { color: cssToken('--vx-signal'), width: 1, style: 2, labelBackgroundColor: cssToken('--vx-surface-2') },
            horzLine: { color: cssToken('--vx-signal'), width: 1, style: 2, labelBackgroundColor: cssToken('--vx-surface-2') },
          },
          timeScale: { borderColor: cssToken('--vx-border-soft') },
          rightPriceScale: { borderColor: cssToken('--vx-border-soft') },
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
        /*
          UNE BARRE DONT UN PRIX NE SE LIT PAS N'EST PAS UNE BARRE À ZÉRO.
          La conversion rendait `0` sur une chaîne non finie : la bougie
          plongeait alors sur l'axe, et ce plongeon se lisait comme un
          effondrement du cours — une donnée FAUSSE, indiscernable d'une
          séance réelle. La barre est désormais ÉCARTÉE, jamais réparée ; la
          table OHLCV rendue sous le graphique porte les chaînes servies telles
          quelles et reste la référence complète.
        */
        const bougies: { time: string; open: number; high: number; low: number; close: number }[] = [];
        for (const bar of bars) {
          const open = geometryNumber(bar.open);
          const high = geometryNumber(bar.high);
          const low = geometryNumber(bar.low);
          const close = geometryNumber(bar.close);
          if (open === null || high === null || low === null || close === null) {
            continue;
          }
          bougies.push({ time: bar.tradingDay, open, high, low, close });
        }
        candles.setData(bougies);

        const volume = chart.addSeries(HistogramSeries, {
          priceScaleId: 'volume',
          priceFormat: { type: 'volume' },
          // Le volume ACCOMPAGNE le prix, il ne le concurrence pas : une teinte
          // sourde unique, et surtout pas vert/rouge. Le contrat réserve ces
          // deux couleurs au SENS FINANCIER, et un volume n'a pas de signe —
          // le colorer par la direction de la séance lui en inventerait un.
          color: cssToken('--vx-titanium-soft'),
        });
        chart.priceScale('volume').applyOptions({
          // 0,84 plutôt que 0,80 : la bande de volume prenait un cinquième de
          // la hauteur pour une information secondaire.
          scaleMargins: { top: 0.84, bottom: 0 },
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
