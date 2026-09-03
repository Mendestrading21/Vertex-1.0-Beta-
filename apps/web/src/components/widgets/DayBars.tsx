import { geometryShare, geometryValue, round2 } from './geometry.ts';

/**
 * Barres par jour, SUR RAIL — comptes ou valeurs SERVIS.
 *
 * LE RAIL (référence 25, admis par ADR-017) est la piste neutre qui rend la
 * proportion lisible ; il ne porte aucune valeur. La barre remplie est la part
 * du plus grand compte SERVI — la même géométrie que `CensusBars`, et comme
 * elle, AUCUN pourcentage n'est écrit : il n'est pas publié, et l'écrire
 * serait le calculer.
 *
 * ABSENCE ≠ ZÉRO. Une entrée sans valeur servie n'a PAS de barre : elle porte
 * `data-absent` et sa cellule de table dit « non publié ». Une barre de
 * hauteur zéro affirmerait un compte nul qui n'a pas été publié.
 *
 * BANDES. Le mapping bande → teinte est DÉCLARÉ par le widget appelant
 * (`bands`). Vert et rouge ne sont admis que si la bande EST un signe
 * financier (revue adverse du canon, point B4) ; sinon l'échelle reste
 * titane / macro / signal. Une bande hors mapping devient `unknown`, VISIBLE.
 */
export interface DayBarEntry {
  readonly key: string;
  readonly label: string;
  /** Valeur SERVIE (compte ou chaîne décimale). `null` = non publiée. */
  readonly value: string | null;
  /**
   * Libellé COURT de l'axe. Le libellé complet reste dans l'infobulle ET
   * dans la table équivalente : c'est un rendu d'abscisse, jamais une valeur
   * raccourcie (ADR-017 interdit d'abréger une VALEUR, pas une date).
   */
  readonly shortLabel?: string;
  /** Nom de bande SERVI. */
  readonly band?: string;
}

export interface DayBarsProps {
  readonly entries: readonly DayBarEntry[];
  readonly unit: string;
  readonly ariaLabel: string;
  /** Jour courant SERVI (jamais l'horloge du navigateur). */
  readonly currentKey?: string;
  /** Mapping DÉCLARÉ bande servie → teinte du widget. */
  readonly bands?: Readonly<Record<string, string>>;
  readonly emptyLabel?: string;
}

export function DayBars({
  entries,
  unit,
  ariaLabel,
  currentKey,
  bands,
  emptyLabel,
}: DayBarsProps) {
  // Les valeurs NULLES sont écartées AVANT la géométrie : sans ce filtre, une
  // absence entrerait dans le maximum et deviendrait une barre nulle.
  const values = entries
    .map((entry) => geometryValue(entry.value))
    .filter((value): value is number => value !== null);
  const max = values.length === 0 ? 0 : Math.max(...values);

  if (entries.length === 0 || values.length === 0) {
    return (
      <p className="vx-w2-absent" role="status">
        {emptyLabel ?? `Aucune valeur publiée (${unit}) : aucune barre tracée.`}
      </p>
    );
  }

  /**
   * Bande d'une entrée, ou `null` quand la figure n'a PAS de vocabulaire de
   * bandes.
   *
   * « Bande non publiée » (`unknown`, teinte fantôme) et « cette donnée n'a
   * pas de bandes » sont deux choses différentes. Le volume d'une séance n'en
   * a aucune : personne n'en publie, personne n'en attend. Le classer
   * `unknown` affichait un aveu d'absence sur une donnée complète — et le
   * rendait invisible (mesuré sur la planche §8). L'absence de bande n'est un
   * manque que si l'appelant a DÉCLARÉ un vocabulaire.
   */
  function bandOf(entry: DayBarEntry): string | null {
    const served = entry.band;
    if (served === undefined || served === '') {
      return bands === undefined ? null : 'unknown';
    }
    if (bands === undefined) {
      return served;
    }
    return bands[served] ?? 'unknown';
  }

  return (
    <div className="vx-w2-daybars-block">
      <div className="vx-w2-daybars" aria-label={ariaLabel} role="img">
        {entries.map((entry) => {
          const value = geometryValue(entry.value);
          const band = bandOf(entry);
          return (
            <span
              key={entry.key}
              className="vx-w2-daybar"
              {...(band === null ? {} : { 'data-band': band })}
              {...(value === null ? { 'data-absent': 'true' } : {})}
              {...(currentKey !== undefined && entry.key === currentKey
                ? { 'aria-current': 'true' }
                : {})}
            >
              {/* La valeur SERVIE est écrite au-dessus de sa barre et le
                  libellé en dessous : sans eux, une colonne grise ne dit ni
                  de qui elle parle ni combien elle vaut, et la table
                  équivalente restait le seul endroit lisible. */}
              <span className="vx-w2-daybar-value">{entry.value === null ? 'n. p.' : entry.value}</span>
              <span className="vx-w2-daybar-track">
                {value === null ? null : (
                  <span
                    className="vx-w2-daybar-fill"
                    style={{ height: `${round2(geometryShare(value, max) * 100)}%` }}
                  />
                )}
              </span>
              <span className="vx-w2-daybar-label" title={entry.label}>
                {entry.shortLabel ?? entry.label}
              </span>
            </span>
          );
        })}
      </div>
      <details>
        <summary>Table équivalente</summary>
        <table className="vx-w2-figure-table">
          <thead>
            <tr>
              <th scope="col">Jour servi</th>
              <th scope="col">Valeur servie ({unit})</th>
              <th scope="col">Bande servie</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.key}>
                <th scope="row">{entry.label}</th>
                <td>{entry.value === null ? 'non publié' : entry.value}</td>
                <td>{entry.band === undefined || entry.band === '' ? 'non publié' : entry.band}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
