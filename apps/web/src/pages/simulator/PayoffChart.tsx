import { useEffect, useRef, useState } from 'react';

import type {
  SimulationBreakeven,
  SimulationExtreme,
  SimulationPayoffPoint,
} from '../../api/client.ts';
import type { EChartsInstance } from '../../charts/echartsLoader.ts';
import { chartAxis, chartBase } from '../../charts/theme.ts';
import { geometryValue } from '../../components/widgets/geometry.ts';

/**
 * PayoffChart — courbe de P&L à l'expiration (dominante du résultat du
 * Simulateur).
 *
 * Chaque point est un couple (spot, pnl) CALCULÉ PAR LE SERVEUR
 * (`payoff_points`, chaînes décimales exactes) ; les breakevens certifiés
 * sont marqués par des lignes verticales avec leur résidu
 * (`payoff_at_spot`). ECharts (chunk paresseux partagé avec /markets) ne
 * fait que dessiner : les chaînes serveur sont parsées pour la géométrie du
 * rendu uniquement. La table des points sous le graphique est l'équivalent
 * accessible exact (mêmes chaînes).
 */

function cssToken(name: string): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/**
 * Valeur numérique d'une chaîne servie, POUR LA GÉOMÉTRIE SEULE — ou `null`.
 *
 * ELLE RENDAIT `0`. Une chaîne illisible devenait donc un point tracé à zéro :
 * une bougie qui plonge sur l'axe, une étincelle qui touche le fond, un P&L
 * posé sur la ligne des zéros. Une absence peinte comme une valeur est un FAIT
 * FAUX, et `.claude/rules/frontend.md` l'interdit nommément — « ne jamais
 * remplacer une donnée absente par 0 ». Le module de géométrie du socle avait
 * déjà nommé ce piège et écrit le remède ; les copies ne l'avaient jamais
 * adopté.
 *
 * L'appelant DOIT désormais traiter `null` : ne rien dessiner, écarter le
 * point, ou refuser la figure — jamais lui substituer une valeur.
 */
function geometryNumber(value: string | null | undefined): number | null {
  return geometryValue(value);
}

export interface PayoffChartProps {
  readonly points: readonly SimulationPayoffPoint[];
  readonly breakevens: readonly SimulationBreakeven[];
  readonly maxGain: SimulationExtreme;
  readonly maxLoss: SimulationExtreme;
}

export function PayoffChart({ points, breakevens, maxGain, maxLoss }: PayoffChartProps) {
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
        const { echarts } = await import('../../charts/echartsLoader.ts');
        if (disposed || containerRef.current === null) {
          return;
        }
        const chart = chartRef.current ?? echarts.init(containerRef.current);
        chartRef.current = chart;
        chart.setOption(
          {
            ...chartBase(cssToken, { grid: { left: 72, right: 24, top: 24, bottom: 40 } }),
            xAxis: {
              ...chartAxis(cssToken),
              type: 'value',
              name: 'spot terminal',
              nameLocation: 'middle',
              nameGap: 28,
              min: 'dataMin',
              max: 'dataMax',
            },
            yAxis: {
              ...chartAxis(cssToken),
              type: 'value',
              name: 'P&L théorique',
            },
            series: [
              {
                type: 'line',
                name: 'P&L à l’expiration (théorique)',
                showSymbol: true,
                symbolSize: 5,
                // Violet `--vx-option` : lumière du domaine options (identité).
                lineStyle: { color: cssToken('--vx-option'), width: 2 },
                itemStyle: { color: cssToken('--vx-option') },
                /*
                  UN POINT DONT LE SPOT OU LE P&L NE SE LIT PAS N'EST PAS UN
                  POINT À L'ORIGINE. La conversion rendait `0` : le tracé
                  passait alors par le coin du repère, et ce coude se lisait
                  comme un profil de gain réel. Le point est écarté ; la table
                  rendue sous la figure porte les chaînes servies telles
                  quelles et reste la référence complète.
                */
                data: points
                  .map((point) => [geometryNumber(point.spot), geometryNumber(point.pnl)])
                  .filter((couple): couple is [number, number] =>
                    couple[0] !== null && couple[1] !== null,
                  ),
                markLine: {
                  symbol: 'none',
                  animation: false,
                  lineStyle: { color: cssToken('--vx-warning'), type: 'dashed' },
                  label: {
                    color: cssToken('--vx-text-secondary'),
                    formatter: (params: { value?: unknown; name?: string }) =>
                      params.name ?? String(params.value ?? ''),
                  },
                  data: [
                    { yAxis: 0, name: 'P&L 0' },
                    // Un breakeven dont le spot ne se lit pas serait tracé
                    // sur l'axe des ordonnées : une ligne verticale à zéro,
                    // annoncée comme un point mort. Il n'est pas tracé.
                    ...breakevens
                      .map((breakeven) => ({
                        xAxis: geometryNumber(breakeven.spot),
                        name: `BE ${breakeven.spot} (résidu ${breakeven.payoff_at_spot})`,
                      }))
                      .filter((ligne): ligne is { xAxis: number; name: string } => ligne.xAxis !== null),
                  ],
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
  }, [points, breakevens]);

  const description =
    `Courbe de P&L théorique à l'expiration sur ${points.length} spots évalués par le serveur ; ` +
    `gain max ${maxGain.pnl} à ${maxGain.at_spot}, perte max ${maxLoss.pnl} à ${maxLoss.at_spot} ; ` +
    (breakevens.length === 0
      ? 'aucun breakeven certifié sur le domaine évalué.'
      : `breakevens certifiés : ${breakevens.map((entry) => entry.spot).join(', ')}.`);

  if (engineFailed) {
    return (
      <p className="vx-payoff-fallback" role="status">
        Le moteur de graphique n'a pas pu être chargé — la table des points ci-dessous reste la
        référence complète des mêmes valeurs.
      </p>
    );
  }

  return (
    <figure className="vx-payoff" aria-label="Courbe de P&L à l'expiration (théorique)">
      <div
        ref={containerRef}
        className="vx-payoff-canvas"
        role="img"
        aria-label={description}
        data-testid="payoff-canvas"
      />
      <figcaption className="vx-payoff-caption">
        Points serveur exacts (Decimal) reliés linéairement ; lignes pointillées = P&amp;L 0 et
        breakevens certifiés avec leur résidu. Rendu : Apache ECharts (Apache-2.0). La table
        ci-dessous contient exactement les mêmes valeurs.
      </figcaption>
    </figure>
  );
}
