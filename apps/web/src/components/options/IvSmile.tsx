import type { OptionChainExpiration } from '../../api/client.ts';
import { geometryNumber, ivViewOf } from '../../pages/options/optionsView.ts';

/**
 * Sourire d'IV d'UN groupe (expiration, trading_class) : les IV THÉORIQUES
 * publiées par le worker, placées par strike, calls et puts séparés.
 *
 * Ce composant ne calcule aucune volatilité : il ne fait que la GÉOMÉTRIE
 * du tracé (position des points publiés), comme `Sparkline` pour les
 * clôtures. Un contrat sans IV résolue n'a pas de point — jamais un zéro —
 * et le compte des absents est écrit. Aucun point « ATM » n'est choisi :
 * choisir un strike de référence serait une décision de calcul.
 */
export interface IvPoint {
  readonly strike: string;
  readonly iv: string;
  readonly right: 'CALL' | 'PUT';
}

export interface IvSmileSeries {
  readonly calls: readonly IvPoint[];
  readonly puts: readonly IvPoint[];
  readonly absentCount: number;
  readonly strikeMin: string | null;
  readonly strikeMax: string | null;
  readonly ivMin: string | null;
  readonly ivMax: string | null;
}

/** Points publiés du groupe, triés par strike (tri de vue). Exportée pour être testée sans DOM. */
export function ivSmileSeriesOf(group: OptionChainExpiration): IvSmileSeries {
  const calls: IvPoint[] = [];
  const puts: IvPoint[] = [];
  let absentCount = 0;
  for (const contract of group.contracts) {
    const iv = ivViewOf(contract);
    if (contract.strike === null || contract.right === null || iv.status !== 'OK' || iv.value === null) {
      absentCount += 1;
      continue;
    }
    const point: IvPoint = { strike: contract.strike, iv: iv.value, right: contract.right };
    if (contract.right === 'CALL') {
      calls.push(point);
    } else {
      puts.push(point);
    }
  }
  // Tri de VUE : les strikes publiés deviennent des nombres AVANT toute
  // comparaison, comme `Sparkline` pour les clôtures — aucune arithmétique
  // sur une propriété financière relayée.
  const orderOf = (points: IvPoint[]): IvPoint[] => {
    const keys: number[] = points.map((point) => geometryNumber(point.strike));
    return points
      .map((point, index) => ({ point, key: keys[index] ?? 0 }))
      .sort((left, right) => left.key - right.key)
      .map((entry) => entry.point);
  };
  const sortedCalls = orderOf(calls);
  const sortedPuts = orderOf(puts);
  const all = [...sortedCalls, ...sortedPuts];
  const extreme = (pick: (values: number[]) => number, key: 'strike' | 'iv'): string | null => {
    if (all.length === 0) {
      return null;
    }
    const target = pick(all.map((point) => geometryNumber(point[key])));
    return all.find((point) => geometryNumber(point[key]) === target)?.[key] ?? null;
  };
  return {
    calls: sortedCalls,
    puts: sortedPuts,
    absentCount,
    strikeMin: extreme((values) => Math.min(...values), 'strike'),
    strikeMax: extreme((values) => Math.max(...values), 'strike'),
    ivMin: extreme((values) => Math.min(...values), 'iv'),
    ivMax: extreme((values) => Math.max(...values), 'iv'),
  };
}

const WIDTH = 160;
const HEIGHT = 72;
const PAD_X = 6;
const PAD_Y = 6;

function scale(values: readonly number[], size: number, pad: number, invert: boolean): (value: number) => number {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;
  const drawable = size - 2 * pad;
  if (span === 0) {
    return () => pad + drawable / 2;
  }
  return (value) => {
    const ratio = (value - min) / span;
    return invert ? size - pad - ratio * drawable : pad + ratio * drawable;
  };
}

export interface IvSmileProps {
  readonly group: OptionChainExpiration;
  readonly label: string;
  readonly compact?: boolean;
}

export function IvSmile({ group, label, compact = false }: IvSmileProps) {
  const series = ivSmileSeriesOf(group);
  const all = [...series.calls, ...series.puts];
  if (all.length === 0) {
    return (
      <p className="vx-iw-absent" role="status" data-testid="iv-smile-absent">
        Aucune IV résolue dans ce groupe ({series.absentCount} contrat{series.absentCount > 1 ? 's' : ''} sans IV) :
        rien n’est tracé.
      </p>
    );
  }
  const x = scale(all.map((point) => geometryNumber(point.strike)), WIDTH, PAD_X, false);
  const y = scale(all.map((point) => geometryNumber(point.iv)), HEIGHT, PAD_Y, true);
  const path = (points: readonly IvPoint[]): string =>
    points.map((point) => `${x(geometryNumber(point.strike)).toFixed(2)},${y(geometryNumber(point.iv)).toFixed(2)}`).join(' ');
  return (
    <figure className="vx-smile" data-compact={compact ? 'true' : 'false'} data-testid="iv-smile">
      <svg
        className="vx-smile-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        {series.calls.length > 1 ? <polyline className="vx-smile-line" data-right="CALL" points={path(series.calls)} /> : null}
        {series.puts.length > 1 ? <polyline className="vx-smile-line" data-right="PUT" points={path(series.puts)} /> : null}
        {all.map((point) => (
          <circle
            key={`${point.right}-${point.strike}`}
            className="vx-smile-dot"
            data-right={point.right}
            cx={x(geometryNumber(point.strike))}
            cy={y(geometryNumber(point.iv))}
            r={compact ? 1.4 : 2}
          />
        ))}
      </svg>
      <figcaption className="vx-smile-caption">
        <span>
          strikes <code>{series.strikeMin}</code> → <code>{series.strikeMax}</code>
        </span>
        <span>
          IV <code>{series.ivMin}</code> → <code>{series.ivMax}</code>
        </span>
        <span>
          <span className="vx-smile-key" data-right="CALL" aria-hidden="true">●</span> calls {series.calls.length} ·{' '}
          <span className="vx-smile-key" data-right="PUT" aria-hidden="true">●</span> puts {series.puts.length}
          {series.absentCount > 0 ? ` · ${series.absentCount} sans IV` : ''}
        </span>
      </figcaption>
    </figure>
  );
}
