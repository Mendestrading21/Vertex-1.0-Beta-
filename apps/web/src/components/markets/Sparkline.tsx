import { geometryNumber } from './marketsView.ts';
import type { SignGroup } from './marketsView.ts';

/**
 * Mini-série d'un instrument : clôtures en ligne, volumes en barres.
 *
 * « Mini-série : contexte seulement, valeur et période adjacentes ; pas de
 * sparkline décorative sans données » (`references/charts.md`). Ce composant
 * ne dessine que des chaînes SERVIES : les clôtures et volumes publiés par le
 * dossier d'analyse. Il ne calcule aucune valeur financière — seulement la
 * GÉOMÉTRIE du tracé (échelle du tracé, position des points), exactement
 * comme la treemap ne calcule que des tailles de tuiles.
 *
 * La ligne pointillée est la PREMIÈRE clôture de la fenêtre : un repère de
 * lecture (au-dessus / en dessous du début de fenêtre), pas une moyenne ni
 * un seuil. Le sens (couleur) vient du rendement 1 j publié par le worker,
 * jamais de la pente du tracé.
 */
export interface SparklineProps {
  /** Clôtures publiées, dans l'ordre chronologique servi. */
  readonly closes: readonly string[];
  /** Volumes publiés, même ordre. Vide : aucune barre. */
  readonly volumes: readonly number[];
  readonly sign: SignGroup;
  /** Description lue par les lecteurs d'écran : fenêtre, première et dernière valeur. */
  readonly label: string;
}

const WIDTH = 120;
const LINE_HEIGHT = 40;
const LINE_TOP = 3;
const LINE_BOTTOM = 37;
const VOLUME_HEIGHT = 18;

function scaleY(values: readonly number[]): (value: number) => number {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;
  const drawable = LINE_BOTTOM - LINE_TOP;
  if (span === 0) {
    const middle = LINE_TOP + drawable / 2;
    return () => middle;
  }
  return (value) => LINE_BOTTOM - ((value - min) / span) * drawable;
}

/**
 * Points « x,y » du tracé — exportée pour être testée sans DOM.
 *
 * UNE CLÔTURE ILLISIBLE N'EST PAS UNE CLÔTURE À ZÉRO. La conversion rendait
 * `0` sur une chaîne non finie : la courbe plongeait alors sur l'axe, et ce
 * creux se lisait comme un effondrement du cours. La série entière est refusée
 * dès qu'un point est illisible — mieux vaut ne rien tracer qu'une forme
 * fausse, et l'appelant affiche alors son état d'absence. Le pas de l'axe des
 * abscisses reste celui des clôtures SERVIES : écarter silencieusement un
 * point déformerait le temps.
 */
export function sparklinePoints(closes: readonly string[]): readonly (readonly [number, number])[] {
  const values: number[] = [];
  for (const raw of closes) {
    const valeur = geometryNumber(raw);
    if (valeur === null) {
      return [];
    }
    values.push(valeur);
  }
  if (values.length === 0) {
    return [];
  }
  const y = scaleY(values);
  const step = values.length === 1 ? 0 : WIDTH / (values.length - 1);
  return values.map((value, index) => [Number((index * step).toFixed(2)), Number(y(value).toFixed(2))]);
}

export function Sparkline({ closes, volumes, sign, label }: SparklineProps) {
  const points = sparklinePoints(closes);
  if (points.length === 0) {
    return null;
  }
  const first = points[0] as readonly [number, number];
  const last = points[points.length - 1] as readonly [number, number];
  const path = points.map(([x, y]) => `${x},${y}`).join(' ');
  const area = `M${first[0]},${LINE_BOTTOM} L${path.replaceAll(' ', ' L')} L${last[0]},${LINE_BOTTOM} Z`;
  const maxVolume = volumes.length === 0 ? 0 : Math.max(...volumes);
  const barSlot = volumes.length === 0 ? 0 : WIDTH / volumes.length;
  const barWidth = Math.max(1, barSlot * 0.55);

  return (
    <div className="vx-spark" data-sign={sign}>
      <svg
        className="vx-spark-line-svg"
        viewBox={`0 0 ${WIDTH} ${LINE_HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        <line
          className="vx-spark-base"
          x1={0}
          x2={WIDTH}
          y1={first[1]}
          y2={first[1]}
          strokeDasharray="2 2"
        />
        <path className="vx-spark-area" d={area} />
        <polyline className="vx-spark-line" points={path} data-testid="spark-line" />
        <circle className="vx-spark-dot" cx={last[0]} cy={last[1]} r={1.6} />
      </svg>
      {volumes.length === 0 ? null : (
        <svg
          className="vx-spark-vol-svg"
          viewBox={`0 0 ${WIDTH} ${VOLUME_HEIGHT}`}
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {volumes.map((volume, index) => {
            const height = maxVolume === 0 ? 0 : (volume / maxVolume) * (VOLUME_HEIGHT - 2);
            return (
              <rect
                // Un volume n'a pas d'identité propre : l'index est sa seule clé stable.
                // biome-ignore lint/suspicious/noArrayIndexKey: barres positionnelles
                key={index}
                className="vx-spark-vol"
                x={index * barSlot + (barSlot - barWidth) / 2}
                y={VOLUME_HEIGHT - height}
                width={barWidth}
                height={height}
                data-last={index === volumes.length - 1 ? 'true' : undefined}
              />
            );
          })}
        </svg>
      )}
    </div>
  );
}
