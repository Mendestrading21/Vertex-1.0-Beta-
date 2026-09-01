/**
 * La grille de corrélation, telle que le serveur la publie.
 *
 * CE COMPOSANT NE CALCULE RIEN. Les coefficients arrivent en CHAÎNES déjà
 * rendues et les bandes arrivent sous forme de NOMS (`strong_positive`,
 * `weak`, …). Il n'y a donc ni arrondi, ni comparaison à un seuil, ni
 * reclassement ici — `.claude/rules/frontend.md` l'interdit, et le seuil qui
 * sépare « fort » de « modéré » est un jugement de domaine qui doit rester
 * lisible côté serveur, pas enfoui dans une feuille de style.
 *
 * Une bande INCONNUE ne serait jamais servie : le relais API la refuse
 * (deny-by-default). Le composant s'aligne sur ce contrat plutôt que de
 * peindre une couleur par défaut, qui ferait passer une case inclassable pour
 * une case faiblement corrélée.
 */

export interface CorrelationMatrixProps {
  readonly instruments: ReadonlyArray<{ readonly ticker: string; readonly label: string }>;
  readonly matrix: ReadonlyArray<readonly string[]>;
  readonly bands: ReadonlyArray<readonly string[]>;
}

/** Libellés français des bandes, pour la légende et les infobulles. */
export const BAND_LABELS: Readonly<Record<string, string>> = {
  self: 'Le même actif',
  strong_positive: 'Fortement liés, même sens',
  moderate_positive: 'Modérément liés, même sens',
  weak: 'Peu liés',
  moderate_negative: 'Modérément liés, sens contraire',
  strong_negative: 'Fortement liés, sens contraire',
};

/** Ordre de lecture de la légende : du plus lié positivement au plus opposé. */
const LEGEND_ORDER: readonly string[] = [
  'strong_positive',
  'moderate_positive',
  'weak',
  'moderate_negative',
  'strong_negative',
];

export function correlationRowsOf(
  props: CorrelationMatrixProps,
): ReadonlyArray<{
  readonly ticker: string;
  readonly label: string;
  readonly cells: ReadonlyArray<{ readonly value: string; readonly band: string }>;
}> {
  return props.instruments.map((instrument, index) => ({
    ticker: instrument.ticker,
    label: instrument.label,
    cells: (props.matrix[index] ?? []).map((value, column) => ({
      value,
      band: props.bands[index]?.[column] ?? 'weak',
    })),
  }));
}

export function CorrelationMatrix({ instruments, matrix, bands }: CorrelationMatrixProps) {
  const rows = correlationRowsOf({ instruments, matrix, bands });

  return (
    <div className="vx-riskmatrix" data-rank="dominant">
      <div className="vx-riskmatrix-scroll" role="region" aria-labelledby="vx-riskmatrix-title" tabIndex={0}>
        <table className="vx-riskmatrix-table">
          <caption id="vx-riskmatrix-title" className="vx-riskmatrix-caption">
            Corrélation des rendements quotidiens, sur les séances communes à tous les
            instruments du périmètre.
          </caption>
          <thead>
            <tr>
              <th scope="col" className="vx-riskmatrix-corner">
                <span className="vx-visually-hidden">Instrument</span>
              </th>
              {instruments.map((instrument) => (
                <th key={instrument.ticker} scope="col" className="vx-riskmatrix-colhead">
                  <abbr title={instrument.label}>{instrument.ticker}</abbr>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.ticker}>
                <th scope="row" className="vx-riskmatrix-rowhead">
                  <abbr title={row.label}>{row.ticker}</abbr>
                </th>
                {row.cells.map((cell, column) => {
                  const other = instruments[column];
                  const bandLabel = BAND_LABELS[cell.band] ?? cell.band;
                  return (
                    <td
                      // La paire (ligne, colonne) est unique et stable : deux
                      // instruments ne portent jamais le même ticker (le
                      // périmètre refuse les doublons côté serveur).
                      key={`${row.ticker}-${other?.ticker ?? String(column)}`}
                      className="vx-riskmatrix-cell"
                      data-band={cell.band}
                      title={`${row.label} et ${other?.label ?? ''} — ${bandLabel} (${cell.value})`}
                    >
                      {cell.value}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="vx-riskmatrix-legend" aria-label="Légende des bandes">
        {LEGEND_ORDER.map((band) => (
          <li key={band} className="vx-riskmatrix-legend-item">
            <span className="vx-riskmatrix-swatch" data-band={band} aria-hidden="true" />
            {BAND_LABELS[band]}
          </li>
        ))}
      </ul>
    </div>
  );
}
