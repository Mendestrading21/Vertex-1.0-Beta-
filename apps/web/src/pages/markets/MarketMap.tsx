import { useEffect, useRef, useState } from 'react';

import type { MarketsSector } from '../../api/client.ts';
import type { EChartsInstance } from '../../charts/echartsLoader.ts';
import type { SignGroup } from '../../components/markets/marketsView.ts';
import { flattenTickers, frDecimal, geometryNumber } from '../../components/markets/marketsView.ts';

/**
 * MarketMap — treemap ECharts secteurs → tickers (dominante de /markets).
 *
 * - taille de tuile = poids global serveur (`weight_global_pct`) ;
 * - couleur = signe du rendement via les TOKENS (positif/négatif/texte
 *   atténué pour stable), jamais la couleur seule : chaque tuile affiche en
 *   texte le ticker ET le rendement signé (« +1,23 % ») ;
 * - moteur importé DYNAMIQUEMENT (chunk séparé, hors bundle initial) ;
 * - `AriaComponent` actif + description courte ; l'équivalence d'accès
 *   complète est la table triable rendue par la page sous la carte ;
 * - aucune donnée n'est calculée ici : les chaînes serveur sont seulement
 *   parsées pour la géométrie du rendu.
 */

function cssToken(name: string): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

interface TreemapLeaf {
  readonly name: string;
  readonly value: number;
  readonly itemStyle: { readonly color: string };
  readonly label: { readonly formatter: string };
}

interface TreemapNode {
  readonly name: string;
  readonly children: TreemapLeaf[];
}

function buildTreemapData(
  sectors: readonly MarketsSector[],
  visibleGroups: ReadonlySet<SignGroup>,
): TreemapNode[] {
  const positive = cssToken('--vx-positive');
  const negative = cssToken('--vx-negative');
  const neutral = cssToken('--vx-text-muted');
  return sectors
    .map((sector) => ({
      name: sector.label,
      children: flattenTickers([sector])
        .filter((entry) => visibleGroups.has(entry.group))
        .map((entry) => ({
          name: entry.ticker.ticker,
          value: geometryNumber(entry.ticker.weight_global_pct),
          itemStyle: {
            color:
              entry.group === 'up' ? positive : entry.group === 'down' ? negative : neutral,
          },
          label: {
            formatter: `${entry.ticker.ticker}\n${frDecimal(entry.ticker.return_1d_pct)} %`,
          },
        })),
    }))
    .filter((node) => node.children.length > 0);
}

export interface MarketMapProps {
  readonly sectors: readonly MarketsSector[];
  readonly visibleGroups: ReadonlySet<SignGroup>;
  /** Description courte lue par les lecteurs d'écran (résumé serveur). */
  readonly description: string;
}

export function MarketMap({ sectors, visibleGroups, description }: MarketMapProps) {
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
        // Import dynamique : echarts vit dans son propre chunk, chargé ici.
        const { echarts } = await import('../../charts/echartsLoader.ts');
        if (disposed || containerRef.current === null) {
          return;
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
            },
            series: [
              {
                type: 'treemap',
                roam: false,
                nodeClick: false,
                breadcrumb: { show: false },
                animation: false,
                /*
                  ANCRAGE AUX QUATRE BORDS, et non `width/height: '100%'`.
                  Mesuré : avec les pourcentages, la carte dépassait son
                  canevas — les tuiles du bas (« SYN-TECH-03 », les services
                  publics) étaient COUPÉES par `overflow: hidden` du cadre.
                  Une tuile tronquée, sur une carte dont la surface EST la
                  donnée, fausse la lecture : le lecteur ne voit pas qu'un
                  instrument manque. Les quatre bords se re-résolvent à chaque
                  `resize()`, donc la carte tient toujours dans son cadre.
                */
                left: 0,
                top: 0,
                right: 0,
                bottom: 0,
                itemStyle: {
                  borderColor: cssToken('--vx-surface-0'),
                  borderWidth: 1,
                  gapWidth: 1,
                },
                label: {
                  show: true,
                  color: cssToken('--vx-black'),
                  fontSize: 12,
                  lineHeight: 16,
                },
                upperLabel: {
                  show: true,
                  height: 22,
                  color: cssToken('--vx-text-secondary'),
                  backgroundColor: cssToken('--vx-surface-1'),
                  fontSize: 12,
                },
                levels: [
                  {},
                  { itemStyle: { gapWidth: 1, borderWidth: 2 } },
                ],
                data: buildTreemapData(sectors, visibleGroups),
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
    // Les données de rendu changent avec le snapshot ou le filtre local.
  }, [sectors, visibleGroups]);

  if (engineFailed) {
    return (
      <p className="vx-marketmap-fallback" role="status">
        Le moteur de carte n'a pas pu être chargé — la table équivalente
        ci-dessous reste la référence complète des mêmes valeurs.
      </p>
    );
  }

  return (
    <figure className="vx-marketmap" aria-label="Carte des marchés (treemap)">
      <div
        ref={containerRef}
        className="vx-marketmap-canvas"
        role="img"
        aria-label={description}
        data-testid="marketmap-canvas"
      />
      <figcaption className="vx-marketmap-caption">
        Taille de tuile = poids global (%) ; texte de tuile = ticker et
        rendement 1 j signé. La table ci-dessous contient exactement les mêmes
        valeurs.
      </figcaption>
    </figure>
  );
}
