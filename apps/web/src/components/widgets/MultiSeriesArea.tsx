import { geometryValue, round2 } from './geometry.ts';

/**
 * Deux ou trois séries SERVIES et ALIGNÉES PAR LE SERVEUR, en aires
 * translucides à dégradé — forme admise par ADR-017.
 *
 * ALIGNEMENT. Ce composant n'interpole rien et ne réaligne rien : si les
 * séries n'ont pas le même nombre de points que les abscisses servies, il
 * REFUSE avec le compte exact. Aligner des dates côté navigateur produirait
 * une comparaison que personne n'a publiée (`references/charts.md`).
 *
 * TRAIT DISTINCT. Chaque série porte un motif de trait propre en plus de sa
 * teinte : « une différence subtile de surface ne porte jamais seule une
 * information » (`references/visual-identity.md`, revue adverse point E5).
 *
 * MOTEUR. SVG interne plutôt qu'ECharts : la primitive doit rendre sa TABLE
 * ÉQUIVALENTE et ses états dans l'environnement de test (jsdom, `css: false`),
 * et ne trace que des coordonnées — aucune agrégation, aucun empilement (un
 * empilement d'aires additionnerait des grandeurs financières).
 */
const WIDTH = 320;
const HEIGHT = 180;
const TOP = 8;
const BOTTOM = 156;

export const MULTI_TONES = ['silver', 'macro', 'option', 'warning'] as const;
export type MultiTone = (typeof MULTI_TONES)[number];

/** Motifs de trait, un par série. Le premier est plein. */
const DASHES = ['none', '6 3', '2 3'] as const;

const MIN_SERIES = 2;
const MAX_SERIES = 3;

export interface MultiSeries {
  readonly key: string;
  readonly label: string;
  /** Points SERVIS, chaînes verbatim, alignés sur `xLabels`. */
  readonly points: readonly string[];
  readonly tone: MultiTone;
}

export interface MultiSeriesAreaProps {
  readonly series: readonly MultiSeries[];
  /** Abscisses SERVIES (jours de séance). */
  readonly xLabels: readonly string[];
  readonly ariaLabel: string;
  readonly caption: string;
  readonly unit: string;
  readonly windowLabel: string;
}

export function MultiSeriesArea({
  series,
  xLabels,
  ariaLabel,
  caption,
  unit,
  windowLabel,
}: MultiSeriesAreaProps) {
  if (series.length < MIN_SERIES) {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : une comparaison demande au moins deux séries servies ({series.length} fournie).
      </p>
    );
  }
  if (series.length > MAX_SERIES) {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : au plus trois séries servies se distinguent ({series.length} fournies).
      </p>
    );
  }

  const misaligned = series.filter((one) => one.points.length !== xLabels.length);
  if (misaligned.length > 0) {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : séries non alignées par le serveur —{' '}
        {misaligned
          .map((one) => `${one.label} : ${one.points.length} points contre ${xLabels.length}`)
          .join(' ; ')}
        . Aucune interpolation côté navigateur.
      </p>
    );
  }

  if (xLabels.length < MIN_SERIES) {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : série insuffisante ({xLabels.length} point servi) — aucun tracé.
      </p>
    );
  }

  // Échelle commune : géométrie seule, sur des propriétés à noms neutres.
  const allValues = series.flatMap((one) =>
    one.points.map((point) => geometryValue(point)).filter((one2): one2 is number => one2 !== null),
  );
  const min = allValues.length === 0 ? 0 : Math.min(...allValues);
  const max = allValues.length === 0 ? 0 : Math.max(...allValues);
  const span = max - min;
  const step = xLabels.length === 1 ? 0 : WIDTH / (xLabels.length - 1);

  function yOf(value: number): number {
    if (span === 0) {
      return round2(TOP + (BOTTOM - TOP) / 2);
    }
    return round2(BOTTOM - ((value - min) / span) * (BOTTOM - TOP));
  }

  return (
    <figure className="vx-w2-multi">
      <svg
        className="vx-w2-multi-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${ariaLabel} — ${windowLabel}`}
      >
        <defs>
          {series.map((one) => (
            <linearGradient
              key={one.key}
              id={`vx-w2-multi-${one.key}`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={`var(--vx-${one.tone}-gradient-start)`} />
              <stop offset="100%" stopColor={`var(--vx-${one.tone}-gradient-end)`} />
            </linearGradient>
          ))}
        </defs>
        <line className="vx-w2-multi-grid" x1={0} y1={BOTTOM} x2={WIDTH} y2={BOTTOM} />
        {series.map((one, index) => {
          const coords = one.points.map((point, position) => {
            const value = geometryValue(point);
            return [round2(position * step), value === null ? null : yOf(value)] as const;
          });
          const drawable = coords.filter(
            (coord): coord is readonly [number, number] => coord[1] !== null,
          );
          if (drawable.length === 0) {
            return null;
          }
          const path = drawable.map(([x, y]) => `${x},${y}`).join(' ');
          const firstX = drawable[0]?.[0] ?? 0;
          const lastX = drawable[drawable.length - 1]?.[0] ?? 0;
          return (
            <g key={one.key}>
              <path
                d={`M${firstX},${BOTTOM} L${path.replaceAll(' ', ' L')} L${lastX},${BOTTOM} Z`}
                fill={`url(#vx-w2-multi-${one.key})`}
              />
              <polyline
                className="vx-w2-multi-line"
                data-tone={one.tone}
                points={path}
                strokeDasharray={DASHES[index % DASHES.length]}
              />
            </g>
          );
        })}
      </svg>
      <figcaption className="vx-w2-spark-caption">
        {caption} · {unit} · {windowLabel}
      </figcaption>
      <ul className="vx-w2-multi-legend">
        {series.map((one, index) => (
          <li key={one.key}>
            <svg aria-hidden="true" viewBox="0 0 28 8">
              <line
                className="vx-w2-multi-line"
                data-tone={one.tone}
                x1={0}
                y1={4}
                x2={28}
                y2={4}
                strokeDasharray={DASHES[index % DASHES.length]}
              />
            </svg>
            {one.label}
          </li>
        ))}
      </ul>
      <details>
        <summary>Table équivalente</summary>
        <table className="vx-w2-figure-table">
          <thead>
            <tr>
              <th scope="col">Séance servie</th>
              {series.map((one) => (
                <th key={one.key} scope="col">
                  {one.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {xLabels.map((label, position) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                {series.map((one) => (
                  <td key={one.key}>{one.points[position] ?? 'non publié'}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
