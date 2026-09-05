import { useEffect, useRef, useState } from 'react';

import type { MarketsSector } from '../../api/client.ts';
import type { EChartsInstance } from '../../charts/echartsLoader.ts';
import type { SignGroup } from '../../components/markets/marketsView.ts';
import { flattenTickers, frDecimal, geometryNumber } from '../../components/markets/marketsView.ts';
import { SIGNED_SCALES, signedStep } from '../../design/signedScale.ts';

/**
 * MarketMap — treemap ECharts secteurs → tickers (dominante de /markets).
 *
 * - taille de tuile = poids global serveur (`weight_global_pct`) ;
 * - couleur = CRAN de l'échelle divergente à bornes déclarées
 *   (`design/signedScale.ts`), jamais la couleur seule : chaque tuile affiche
 *   en texte le ticker ET le rendement signé (« +1,23 % ») ;
 *
 *   La carte peignait auparavant la teinte PLEINE selon le seul signe : un
 *   +0,09 % et un +2,42 % recevaient exactement le même vert. La couleur
 *   couvrait donc toute la surface sans rien mesurer, et une planche de blocs
 *   saturés relève de l'esthétique que l'identité proscrit. Les bornes de
 *   l'échelle sont FIXES et publiées dans la légende : la même valeur donne
 *   toujours la même couleur, d'un instantané à l'autre ;
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
  // Une tuile sans rendement lisible n'est PAS peinte en gris neutre : elle
  // prend la surface d'absence, qui ne ressemble à aucun cran de l'échelle.
  // Peindre une absence comme un zéro les rendrait indiscernables.
  const absente = cssToken('--vx-surface-2');
  return sectors
    .map((sector) => ({
      name: sector.label,
      children: flattenTickers([sector])
        .filter((entry) => visibleGroups.has(entry.group))
        .map((entry) => {
          const rendement = geometryNumber(entry.ticker.return_1d_pct);
          const cran = signedStep(Number.isFinite(rendement) ? rendement : null, SIGNED_SCALES.quotidien);
          return {
          name: entry.ticker.ticker,
          value: geometryNumber(entry.ticker.weight_global_pct),
          itemStyle: {
            color: cran === null ? absente : cssToken(`--vx-${cran.token}`),
          },
          label: {
            formatter: `${entry.ticker.ticker}\n${frDecimal(entry.ticker.return_1d_pct)} %`,
          },
          };
        }),
    }))
    .filter((node) => node.children.length > 0);
}

export interface MarketMapProps {
  readonly sectors: readonly MarketsSector[];
  readonly visibleGroups: ReadonlySet<SignGroup>;
  /** Description courte lue par les lecteurs d'écran (résumé serveur). */
  readonly description: string;
  /**
   * LOT-A3 : un clic sur une TUILE ouvre l'instrument dans l'inspecteur. La
   * souris seule ne suffit pas à l'accessibilité — la même sélection existe
   * au clavier dans la table équivalente et la carte sectorielle.
   */
  readonly onSelect?: (ticker: string) => void;
}

export function MarketMap({ sectors, visibleGroups, description, onSelect }: MarketMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsInstance | null>(null);
  const [engineFailed, setEngineFailed] = useState(false);
  // La dernière fonction de sélection, lue par l'écouteur sans le réabonner.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

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
            textStyle: {
              fontFamily: cssToken('--vx-font-mono'),
              fontSize: 11,
              color: cssToken('--vx-text-muted'),
            },
            tooltip: {
              backgroundColor: cssToken('--vx-surface-2'),
              borderColor: cssToken('--vx-border'),
              borderWidth: 1,
              padding: [6, 10],
              textStyle: {
                color: cssToken('--vx-text'),
                fontFamily: cssToken('--vx-font-mono'),
                fontSize: 11,
              },
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
                  // Texte CLAIR : les crans sont translucides sur fond
                  // obsidienne, donc sombres. Un texte noir y était lisible
                  // tant que la teinte était pleine ; il ne l'est plus.
                  // `contrast.test.ts` mesure le texte clair sur chaque cran
                  // et sur chaque fond de lecture.
                  color: cssToken('--vx-text'),
                  // Ticker et rendement : « mono/tabular pour prix, dates,
                  // unités et codes ». Une tuile porte les deux.
                  fontFamily: cssToken('--vx-font-mono'),
                  fontSize: 11,
                  lineHeight: 15,
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
        // Seule une FEUILLE (un ticker servi) est sélectionnable : le nom d'un
        // nœud de secteur n'ouvre rien. La liste des tickers vient du snapshot.
        const tickers = new Set(flattenTickers(sectors).map((entry) => entry.ticker.ticker));
        chart.off('click');
        chart.on('click', (params: { readonly name?: string }) => {
          const name = params.name;
          if (typeof name === 'string' && tickers.has(name)) {
            onSelectRef.current?.(name);
          }
        });
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
      {/*
        LA LÉGENDE PUBLIE LES BORNES, et c'est ce qui rend l'échelle honnête.
        Sans elle, une teinte plus soutenue signifierait « plus » sans dire
        combien — une gradation décorative. Avec elle, un lecteur sait qu'un
        bloc soutenu est au-dessus de deux pour cent, et il peut le vérifier
        sur la tuile, qui porte le chiffre.
      */}
      <ul
        className="vx-marketmap-scale"
        aria-label={`Échelle de couleur — ${SIGNED_SCALES.quotidien.mesure}`}
      >
        {SIGNED_SCALES.quotidien.steps.map((cran) => (
          <li key={cran.key}>
            <span className="vx-marketmap-swatch" data-step={cran.key} aria-hidden="true" />
            {cran.label}
          </li>
        ))}
      </ul>
      <figcaption className="vx-marketmap-caption">
        Taille de tuile = poids global (%) ; couleur = cran de rendement 1 j à
        bornes fixes, identiques d'un instantané à l'autre ; texte de tuile =
        ticker et rendement 1 j signé. La table ci-dessous contient exactement
        les mêmes valeurs.
      </figcaption>
    </figure>
  );
}
