import { sparklinePoints } from '../markets/Sparkline.tsx';
import type { SignGroup } from '../markets/marketsView.ts';

/**
 * Figure d'une série SERVIE : tracé + légende de période + TABLE ÉQUIVALENTE.
 *
 * Deux variantes, toutes deux admises par ADR-017 :
 *   - `line` : le canon v1, aucun dégradé ;
 *   - `area` : l'aire à dégradé VERTICAL, de la teinte sémantique de la série
 *     vers SA transparence (`--vx-<famille>-gradient-start` → `-end`). Jamais
 *     entre deux teintes, jamais sur un fond de carte.
 *
 * CE QUI EST REFUSÉ. Une série de moins de deux points ne donne pas une
 * courbe plate : elle donne une phrase. Une figure sans période SERVIE est
 * refusée — « valeur, unité, période » est le minimum d'une mesure
 * (`references/visual-identity.md`).
 *
 * Les volumes restent la propriété de `Sparkline` (tuile d'instrument) : cette
 * figure ne trace qu'UNE représentation, comme l'exige l'anatomie v2.
 */
export const SPARK_TONES = [
  'silver',
  'macro',
  'option',
  'warning',
  'positive',
  'negative',
] as const;
export type SparkTone = (typeof SPARK_TONES)[number];

const WIDTH = 120;
const HEIGHT = 40;
const BASELINE = 37;

export interface SparkFigureProps {
  /** Série SERVIE, chaînes verbatim, dans l'ordre publié. */
  readonly closes: readonly string[];
  /** Étiquettes SERVIES (jours de séance) pour la table équivalente. */
  readonly labels?: readonly string[];
  readonly sign: SignGroup;
  readonly caption: string;
  readonly unit: string;
  /** Période SERVIE, obligatoire (« 30 dernières barres servies sur 252 »). */
  readonly windowLabel: string;
  readonly variant?: 'line' | 'area';
  readonly tone?: SparkTone;
}

export function SparkFigure({
  closes,
  labels,
  sign,
  caption,
  unit,
  windowLabel,
  variant = 'line',
  tone = 'silver',
}: SparkFigureProps) {
  if (windowLabel.trim() === '') {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : période non publiée — la série n’est pas tracée. Une mesure sans période n’en
        est pas une.
      </p>
    );
  }

  if (closes.length < 2) {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : série insuffisante ({closes.length} barre servie) — aucun tracé.
      </p>
    );
  }

  const points = sparklinePoints(closes);
  const path = points.map(([x, y]) => `${x},${y}`).join(' ');
  const first = points[0] as readonly [number, number];
  const last = points[points.length - 1] as readonly [number, number];
  const area = `M${first[0]},${BASELINE} L${path.replaceAll(' ', ' L')} L${last[0]},${BASELINE} Z`;
  const gradientId = `vx-w2-spark-${tone}-${closes.length}`;

  return (
    <figure className="vx-w2-spark" data-sign={sign} data-tone={tone} data-variant={variant}>
      <svg
        className="vx-w2-spark-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${caption} — ${windowLabel}`}
      >
        {variant === 'area' ? (
          <defs>
            {/* Dégradé VERTICAL (x1 = x2) : la teinte descend vers sa propre
                transparence. `stop-color` ne porte que des tokens. */}
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={`var(--vx-${tone}-gradient-start)`} />
              <stop offset="100%" stopColor={`var(--vx-${tone}-gradient-end)`} />
            </linearGradient>
          </defs>
        ) : null}
        {/* Base pointillée = PREMIÈRE clôture servie : un repère de lecture,
            jamais une moyenne ni un seuil. */}
        <line
          className="vx-w2-spark-base"
          x1={0}
          x2={WIDTH}
          y1={first[1]}
          y2={first[1]}
          strokeDasharray="2 2"
        />
        {variant === 'area' ? <path d={area} fill={`url(#${gradientId})`} /> : null}
        <polyline className="vx-w2-spark-line" points={path} data-testid="spark-figure-line" />
      </svg>
      <figcaption className="vx-w2-spark-caption">
        {caption} · {unit} · {windowLabel}
      </figcaption>
      <details>
        <summary>Table équivalente</summary>
        <table className="vx-w2-spark-table">
          <thead>
            <tr>
              <th scope="col">Séance servie</th>
              <th scope="col">Valeur servie ({unit})</th>
            </tr>
          </thead>
          <tbody>
            {closes.map((close, index) => (
              <tr key={labels?.[index] ?? `${index}-${close}`}>
                <th scope="row">{labels?.[index] ?? `rang ${index + 1}`}</th>
                <td>{close}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
