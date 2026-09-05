import { useMemo, useState } from 'react';

import { saveTextAsFile } from '../../app/downloadFile.ts';

import type { FlatTicker } from '../../components/markets/marketsView.ts';
import {
  GROUP_LABELS_FR,
  frDecimal,
  geometryNumber,
  signSymbolOf,
} from '../../components/markets/marketsView.ts';

/**
 * Table accessible ÉQUIVALENTE de la MarketMap : mêmes valeurs exactes
 * (chaînes serveur verbatim, seulement formatées), tri par colonne activable
 * au clavier (bouton dans chaque en-tête, `aria-sort` reflété). Le tri est un
 * réarrangement local de la vue — aucune valeur n'est recalculée.
 */

type ColumnKey =
  | 'ticker'
  | 'sector'
  | 'last_close'
  | 'return_1d_pct'
  | 'weight_in_sector_pct'
  | 'weight_global_pct'
  | 'quality';

interface Column {
  readonly key: ColumnKey;
  readonly label: string;
  readonly numeric: boolean;
}

const COLUMNS: readonly Column[] = [
  { key: 'ticker', label: 'Ticker', numeric: false },
  { key: 'sector', label: 'Secteur', numeric: false },
  { key: 'last_close', label: 'Dernière clôture', numeric: true },
  { key: 'return_1d_pct', label: 'Rendement 1 j (%)', numeric: true },
  { key: 'weight_in_sector_pct', label: 'Poids secteur (%)', numeric: true },
  { key: 'weight_global_pct', label: 'Poids global (%)', numeric: true },
  { key: 'quality', label: 'Qualité', numeric: false },
];

const CSV_HEADER = [
  'ticker',
  'sector',
  'trading_day',
  'last_close',
  'currency',
  'return_1d',
  'return_1d_pct',
  'weight_in_sector',
  'weight_global',
  'quality',
  'synthetic',
] as const;
const CSV_FORMULA_PREFIXES: ReadonlySet<string> = new Set(['=', '+', '-', '@']);

/**
 * Cellule CSV au délimiteur `;` : neutralisation tableur identique à
 * `vertex_api.portfolio.neutralize_csv_cell`, puis échappement des
 * délimiteurs, guillemets et retours ligne.
 */
export function marketsCsvCell(value: string): string {
  const safe = CSV_FORMULA_PREFIXES.has(value.charAt(0)) ? `'${value}` : value;
  return /[;"\r\n]/u.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
}

function marketsCsvRow(cells: readonly string[]): string {
  return cells.map(marketsCsvCell).join(';');
}

export function renderMarketsCsv(entries: readonly FlatTicker[]): string {
  const lines = entries.map((entry) =>
    marketsCsvRow([
      entry.ticker.ticker,
      entry.ticker.sector,
      entry.ticker.trading_day,
      entry.ticker.last_close,
      entry.ticker.currency ?? '',
      entry.ticker.return_1d,
      entry.ticker.return_1d_pct,
      entry.ticker.weight_in_sector,
      entry.ticker.weight_global,
      entry.ticker.quality,
      entry.ticker.synthetic ? 'SYNTHETIC' : '',
    ]),
  );
  return `${marketsCsvRow(CSV_HEADER)}\n${lines.join('\n')}\n`;
}

function rawValue(entry: FlatTicker, key: ColumnKey): string {
  switch (key) {
    case 'ticker':
      return entry.ticker.ticker;
    case 'sector':
      return entry.sectorLabel;
    case 'last_close':
      return entry.ticker.last_close;
    case 'return_1d_pct':
      return entry.ticker.return_1d_pct;
    case 'weight_in_sector_pct':
      return entry.ticker.weight_in_sector_pct;
    case 'weight_global_pct':
      return entry.ticker.weight_global_pct;
    case 'quality':
      return entry.ticker.quality;
  }
}

export interface MarketsTableProps {
  readonly entries: readonly FlatTicker[];
  readonly population: string | null;
  /** LOT-A3 : instrument ouvert dans l'inspecteur, et son sélecteur. */
  readonly selected?: string | null;
  readonly onSelect?: (ticker: string) => void;
}

/**
 * Nom d'export dérivé de la population publiée, sans présumer de la nature
 * des cas absents, mixtes ou non synthétiques.
 */
function marketsCsvFilename(population: string | null): string {
  return population === 'SYNTHETIC' ? 'marches-synthetiques.csv' : 'marches.csv';
}

/**
 * Compare deux valeurs servies dont l'une peut être illisible.
 *
 * L'illisible va TOUJOURS au bout, quel que soit le sens du tri : l'inverser
 * avec le reste le ferait remonter en tête au premier clic, comme s'il était
 * l'extrême le plus élevé.
 */
function compareNumeriqueServi(gauche: number | null, droite: number | null): number {
  if (gauche === null && droite === null) {
    return 0;
  }
  if (gauche === null) {
    return 1;
  }
  if (droite === null) {
    return -1;
  }
  return gauche - droite;
}

export function MarketsTable({ entries, population, selected = null, onSelect }: MarketsTableProps) {
  const [sortKey, setSortKey] = useState<ColumnKey>('ticker');
  const [descending, setDescending] = useState(false);

  const sorted = useMemo(() => {
    const column = COLUMNS.find((candidate) => candidate.key === sortKey);
    const copy = [...entries];
    copy.sort((a, b) => {
      const left = rawValue(a, sortKey);
      const right = rawValue(b, sortKey);
      // UNE VALEUR ILLISIBLE NE VAUT PAS ZÉRO, MÊME POUR TRIER. La conversion
      // rendait `0` : une chaîne non analysable se rangeait alors AU MILIEU du
      // classement, entre les valeurs négatives et positives, comme si elle
      // avait été mesurée à zéro. Elle est désormais reléguée en fin de tri,
      // dans les deux sens : « on ne sait pas » n'est pas une position sur
      // l'échelle, c'est l'absence de position.
      const compared = column?.numeric
        ? compareNumeriqueServi(geometryNumber(left), geometryNumber(right))
        : left.localeCompare(right, 'fr');
      return descending ? -compared : compared;
    });
    return copy;
  }, [entries, sortKey, descending]);

  function activateSort(key: ColumnKey): void {
    if (key === sortKey) {
      setDescending((previous) => !previous);
    } else {
      setSortKey(key);
      setDescending(false);
    }
  }

  function exportCsv(): void {
    saveTextAsFile(
      renderMarketsCsv(sorted),
      marketsCsvFilename(population),
      'text/csv;charset=utf-8',
    );
  }

  return (
    <div className="vx-markets-table-wrap">
      <div className="vx-markets-table-actions">
        <button type="button" className="vx-markets-export" onClick={exportCsv}>
          Exporter (CSV)
        </button>
      </div>
      {/*
        LOT-A3 — bornée comme les autres tables longues (règle commune de
        `global.css`) : 22 lignes déroulées faisaient 1 100 px. `tabIndex` dans
        le même geste que la borne : une région défilante doit être atteignable
        au clavier (axe `scrollable-region-focusable`, seuil zéro).
      */}
      <div
        className="vx-markets-table-scroll"
        tabIndex={0}
        role="region"
        aria-label="Table équivalente, région défilante"
      >
        <table className="vx-markets-table" aria-label="Table équivalente de la carte des marchés">
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={
                    column.key === sortKey ? (descending ? 'descending' : 'ascending') : 'none'
                  }
                >
                  <button
                    type="button"
                    className="vx-markets-sort"
                    onClick={() => {
                      activateSort(column.key);
                    }}
                  >
                    {column.label}
                    <span aria-hidden="true" className="vx-markets-sort-mark">
                      {column.key === sortKey ? (descending ? '↓' : '↑') : ''}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((entry) => (
              <tr key={entry.ticker.ticker} data-group={entry.group}>
                <th scope="row">
                  {onSelect === undefined ? (
                    <code>{entry.ticker.ticker}</code>
                  ) : (
                    <button
                      type="button"
                      className="vx-markets-pick"
                      aria-pressed={selected === entry.ticker.ticker}
                      aria-label={`Inspecter ${entry.ticker.ticker}`}
                      onClick={() => {
                        onSelect(entry.ticker.ticker);
                      }}
                    >
                      <code>{entry.ticker.ticker}</code>
                    </button>
                  )}{' '}
                  {entry.ticker.synthetic ? (
                    <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
                  ) : null}
                </th>
                <td>{entry.sectorLabel}</td>
                <td className="vx-num">
                  {frDecimal(entry.ticker.last_close)}
                  {entry.ticker.currency !== null ? ` ${entry.ticker.currency}` : ''}
                </td>
                <td className="vx-num" data-sign={entry.group}>
                  <span aria-hidden="true">{signSymbolOf(entry.group)}</span>{' '}
                  {frDecimal(entry.ticker.return_1d_pct)} %{' '}
                  <span className="vx-visually-hidden">({GROUP_LABELS_FR[entry.group]})</span>
                </td>
                <td className="vx-num">{frDecimal(entry.ticker.weight_in_sector_pct)} %</td>
                <td className="vx-num">{frDecimal(entry.ticker.weight_global_pct)} %</td>
                <td>{entry.ticker.quality}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
