/**
 * Barres horizontales de DÉNOMBREMENTS — le remplacement, sur toutes les
 * planches, des « donuts » de répartition.
 *
 * POURQUOI PAS UN ANNEAU. `references/charts.md` : pas de jauge circulaire,
 * pas d'anneau — une part se lit sur une longueur, pas sur un angle. Et une
 * barre porte son compte À CÔTÉ d'elle, ce qu'un anneau ne fait jamais.
 *
 * CE QUE CE COMPOSANT REÇOIT. Des comptes ENTIERS publiés par le serveur
 * (statuts, directions, catégories, sources), jamais une grandeur financière.
 * La seule opération est la GÉOMÉTRIE : la longueur de chaque barre est la
 * part du plus grand compte. Le pourcentage n'est pas écrit — il n'est pas
 * publié, et l'écrire serait le calculer.
 */
export interface CensusEntry {
  readonly key: string;
  /** Libellé lisible ; `key` est montré en chasse fixe quand il en diffère. */
  readonly label?: string;
  readonly count: number;
}

export interface CensusBarsProps {
  readonly entries: readonly CensusEntry[];
  readonly ariaLabel: string;
  /** Préfixe des `data-testid` par ligne : `${prefix}-${key}`. */
  readonly testIdPrefix?: string;
  readonly emptyLabel?: string;
}

/** Largeur (0–100) de chaque barre : part du plus grand compte. Géométrie seule. */
export function censusWidths(counts: readonly number[]): readonly number[] {
  const max = Math.max(0, ...counts);
  if (max === 0) {
    return counts.map(() => 0);
  }
  return counts.map((count) => Number(((count / max) * 100).toFixed(1)));
}

export function CensusBars({ entries, ariaLabel, testIdPrefix, emptyLabel }: CensusBarsProps) {
  if (entries.length === 0) {
    return (
      <p className="vx-module-sentence" role="status">
        {emptyLabel ?? 'Aucun compte publié.'}
      </p>
    );
  }
  const widths = censusWidths(entries.map((entry) => entry.count));
  return (
    <ul className="vx-census" aria-label={ariaLabel}>
      {entries.map((entry, index) => (
        <li
          key={entry.key}
          className="vx-census-row"
          {...(testIdPrefix === undefined ? {} : { 'data-testid': `${testIdPrefix}-${entry.key}` })}
        >
          <span className="vx-census-label">
            {entry.label ?? <code>{entry.key}</code>}
            {entry.label !== undefined && entry.label !== entry.key ? (
              <code className="vx-census-code"> {entry.key}</code>
            ) : null}
          </span>
          <span className="vx-census-track" aria-hidden="true">
            <span className="vx-census-fill" style={{ width: `${widths[index] ?? 0}%` }} />
          </span>
          <span className="vx-census-count">{entry.count}</span>
        </li>
      ))}
    </ul>
  );
}
