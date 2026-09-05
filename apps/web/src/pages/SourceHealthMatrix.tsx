import { useSearchParams } from 'react-router-dom';

import type { CapabilityEntry, SourceCapabilityStatus } from '../api/client.ts';
import { StatusBadge } from '../components/StatusBadge.tsx';
import { AbsentCell } from '../components/absence.tsx';
import { DataTable } from '../components/widgets/DataTable.tsx';
import type { DataColumn } from '../components/widgets/DataTable.tsx';

/**
 * Visuel dominant de la page Sources & Rapports : matrice de santé des sources.
 *
 * Table accessible (caption, th scope) des capacités déclarées croisées avec
 * les sondes réellement persistées. Les lignes affichées sont EXACTEMENT les
 * entrées reçues de l'API (filtrées côté affichage uniquement) ; aucune
 * cellule vide : une valeur absente est rendue « — » avec un aria-label
 * explicite (« jamais sondé » pour un tested_at nul), jamais un zéro ni un
 * texte inventé. Les filtres famille/statut persistent dans l'URL.
 *
 * LOT-A8 : la matrice est le CORPS de la carte dominante portée par la page
 * (planche §12) ; chaque ligne peut ouvrir la capacité dans l'inspecteur
 * (« Détail »).
 */

const FAMILY_PARAM = 'famille';
const STATUS_PARAM = 'statut';
const ALL = 'toutes';

const STATUS_VALUES: readonly SourceCapabilityStatus[] = [
  'AVAILABLE',
  'DELAYED',
  'NOT_ENTITLED',
  'UNSUPPORTED',
  'ERROR',
  'MANUAL_EXPORT',
];

function countBy<K extends string>(entries: readonly CapabilityEntry[], key: (entry: CapabilityEntry) => K): Map<K, number> {
  const counts = new Map<K, number>();
  for (const entry of entries) {
    const value = key(entry);
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return counts;
}

export interface SourceHealthMatrixProps {
  readonly entries: readonly CapabilityEntry[];
  /** `total` du DTO — le nombre exact d'entrées du manifeste déclaré. */
  readonly total: number;
  readonly selected?: string | null;
  readonly onInspect?: (capabilityId: string) => void;
}

/**
 * Colonnes de la matrice, typées par la NATURE de leur valeur.
 *
 * Aucune n'est `num` : un identifiant de capacité, une famille, un mode, un
 * statut, une raison et un horodatage ne sont pas des mesures. Le type refuse
 * d'ailleurs une colonne `num` sans unité servie — ce qui est exactement la
 * bonne contrainte, et ce qui aurait empêché d'inventer une unité ici.
 */
function colonnes(
  selected: string | null,
  onInspect?: (capabilityId: string) => void,
): ReadonlyArray<DataColumn<CapabilityEntry>> {
  return [
  {
    key: 'capability_id',
    header: 'capability_id',
    align: 'text',
    rowHeader: true,
    /*
      L'ACTION RESTE DANS LA CELLULE D'IDENTITÉ, comme avant la migration.
      `DataTable` sait poser une colonne d'action dédiée (`onOpenRow`), et c'est
      sa convention ; l'adopter ici ajouterait une SEPTIÈME colonne à une
      matrice dont la composition en compte six, figées par un test. Migrer une
      table ne doit pas changer ce qu'elle montre : le gain visé est la légende,
      l'ordre déclaré, l'état vide nommé et la région défilante — pas une
      colonne de plus.
    */
    cell: (entry) => (
      <>
        <code>{entry.capability_id}</code>
        {onInspect === undefined ? null : (
          <button
            type="button"
            className="vx-opp-inspect"
            aria-pressed={selected === entry.capability_id}
            aria-label={`Inspecter ${entry.capability_id}`}
            onClick={() => {
              onInspect(entry.capability_id);
            }}
          >
            Détail
          </button>
        )}
      </>
    ),
  },
  { key: 'family', header: 'Famille', align: 'text', cell: (entry) => entry.family },
  { key: 'declared_mode', header: 'Mode déclaré', align: 'text', cell: (entry) => entry.declared_mode },
  {
    key: 'tested_status',
    header: 'Statut testé',
    align: 'status',
    cell: (entry) => <StatusBadge status={entry.tested_status} />,
  },
  {
    key: 'reason',
    header: 'Raison',
    align: 'text',
    cell: (entry) =>
      entry.reason === null ? (
        <AbsentCell quoi="raison" nature="not_published" reason={null} accord="f" />
      ) : (
        entry.reason
      ),
  },
  {
    key: 'tested_at',
    header: 'tested_at',
    align: 'text',
    unit: 'UTC',
    /*
      « JAMAIS SONDÉ » N'EST PAS UNE ABSENCE, C'EST UN FAIT. `tested_at === null`
      signifie qu'aucune sonde n'a jamais tourné sur cette source. Le passer en
      `AbsentCell` écrirait « sonde sans objet », ce qui est faux — la porte
      anti-tiret ne juge pas si la NATURE choisie est la bonne, et c'est un test
      qui l'avait rattrapé. La distinction est conservée telle quelle.
    */
    cell: (entry) =>
      entry.tested_at === null ? (
        <span className="vx-cell-absent">jamais sondé</span>
      ) : (
        <time dateTime={entry.tested_at}>{entry.tested_at}</time>
      ),
    },
  ];
}

export function SourceHealthMatrix({ entries, total, selected = null, onInspect }: SourceHealthMatrixProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const familyFilter = searchParams.get(FAMILY_PARAM) ?? ALL;
  const statusFilter = searchParams.get(STATUS_PARAM) ?? ALL;

  const families = [...new Set(entries.map((entry) => entry.family))].sort();
  const familyCounts = countBy(entries, (entry) => entry.family);
  const statusCounts = countBy(entries, (entry) => entry.tested_status);

  const filtered = entries.filter(
    (entry) =>
      (familyFilter === ALL || entry.family === familyFilter) &&
      (statusFilter === ALL || entry.tested_status === statusFilter),
  );

  function updateParam(name: string, value: string): void {
    const next = new URLSearchParams(searchParams);
    if (value === ALL) {
      next.delete(name);
    } else {
      next.set(name, value);
    }
    setSearchParams(next, { replace: true });
  }

  return (
    <div className="vx-matrix">
      <div className="vx-matrix-filters">
        <label>
          Famille
          <select value={familyFilter} onChange={(event) => updateParam(FAMILY_PARAM, event.target.value)}>
            <option value={ALL}>Toutes ({entries.length})</option>
            {families.map((family) => (
              <option key={family} value={family}>
                {family} ({familyCounts.get(family) ?? 0})
              </option>
            ))}
          </select>
        </label>
        <label>
          Statut testé
          <select value={statusFilter} onChange={(event) => updateParam(STATUS_PARAM, event.target.value)}>
            <option value={ALL}>Tous ({entries.length})</option>
            {STATUS_VALUES.map((status) => (
              <option key={status} value={status}>
                {status} ({statusCounts.get(status) ?? 0})
              </option>
            ))}
          </select>
        </label>
        <p className="vx-matrix-count" role="status">
          {filtered.length} capacité{filtered.length > 1 ? 's' : ''} affichée
          {filtered.length > 1 ? 's' : ''} sur {total} déclarée{total > 1 ? 's' : ''}
        </p>
      </div>

      <DataTable<CapabilityEntry>
        id="vx-capabilities"
        caption={`Capacités IBKR market-data déclarées (${total}) croisées avec les sondes réellement persistées`}
        captionDetail="un statut jamais sondé reste ERROR / NEVER_TESTED, jamais une disponibilité supposée"
        columns={colonnes(selected, onInspect)}
        rows={filtered}
        rowKey={(entry) => entry.capability_id}
        overflow="panel"
        emptyLabel={`Aucune capacité ne correspond aux filtres actifs — les ${entries.length} entrées reçues restent comptées ci-dessus.`}
        servedOrder={null}
        selectedRowKey={selected}
      />
    </div>
  );
}
