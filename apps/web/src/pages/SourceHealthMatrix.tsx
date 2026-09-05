import { useSearchParams } from 'react-router-dom';

import type { CapabilityEntry, SourceCapabilityStatus } from '../api/client.ts';
import { StatusBadge } from '../components/StatusBadge.tsx';
import { AbsentCell } from '../components/absence.tsx';

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

      {/* Région défilante focusable au clavier (WCAG 2.1.1 — axe
          scrollable-region-focusable) : la table large défile dans SON
          conteneur, jamais la page entière. */}
      <div className="vx-matrix-scroll" role="region" aria-label="Table des capacités (défilement horizontal possible)" tabIndex={0}>
        <table className="vx-matrix-table">
          <caption>
            Capacités IBKR market-data déclarées ({total}) croisées avec les sondes réellement persistées — un statut jamais sondé
            reste ERROR / NEVER_TESTED, jamais une disponibilité supposée.
          </caption>
          <thead>
            <tr>
              <th scope="col">capability_id</th>
              <th scope="col">Famille</th>
              <th scope="col">Mode déclaré</th>
              <th scope="col">Statut testé</th>
              <th scope="col">Raison</th>
              <th scope="col">tested_at (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((entry) => (
              <tr key={entry.capability_id} {...(selected === entry.capability_id ? { 'data-selected': 'true' } : {})}>
                <th scope="row">
                  <code>{entry.capability_id}</code>
                  {onInspect !== undefined ? (
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
                  ) : null}
                </th>
                <td>{entry.family}</td>
                <td>{entry.declared_mode}</td>
                <td>
                  <StatusBadge status={entry.tested_status} />
                </td>
                <td>{entry.reason === null ? <AbsentCell quoi="raison" nature="not_published" reason={null} accord="f" /> : entry.reason}</td>
                {/* LOT T4-7 — « JAMAIS SONDÉ » N'EST PAS UNE ABSENCE, c'est un FAIT :
                    `tested_at === null` signifie qu'aucune sonde n'a jamais tourné sur
                    cette source. Le passer en `AbsentCell` aurait écrit « sonde sans
                    objet », ce qui est faux — et c'est exactement la limite n° 3 de la
                    porte : elle ne juge pas si la NATURE choisie est la bonne. Le test
                    existant l'a rattrapée. */}
                <td>
                  {entry.tested_at === null ? (
                    <span className="vx-cell-absent">jamais sondé</span>
                  ) : (
                    <time dateTime={entry.tested_at}>{entry.tested_at}</time>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 ? (
        <p className="vx-matrix-empty" role="status">
          Aucune capacité ne correspond aux filtres actifs — les {entries.length} entrées reçues restent comptées ci-dessus.
        </p>
      ) : null}
    </div>
  );
}
