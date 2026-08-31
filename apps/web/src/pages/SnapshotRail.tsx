/**
 * Rail de vérité du snapshot pour la page Aujourd'hui.
 *
 * Le composant est volontairement pur : il affiche uniquement les props
 * reçues. Il ne lit ni l'horloge, ni le réseau, ne complète aucun champ absent
 * et ne calcule aucun ratio à partir de la couverture.
 */

export interface SnapshotRailProps {
  readonly snapshotVersion: number | null;
  readonly asOf: string | null;
  readonly population: string | null;
  readonly itemCount: number;
  readonly rejectedCount: number | null;
  readonly coverage: Record<string, unknown> | null;
}

interface CoverageField {
  readonly key:
    | 'observations_considered'
    | 'clusters'
    | 'ranked'
    | 'published_items'
    | 'truncated_ranked';
  readonly label: string;
}

/** Liste fermée : une clé inconnue du dictionnaire n'entre jamais dans le DOM. */
const COVERAGE_FIELDS: readonly CoverageField[] = [
  { key: 'observations_considered', label: 'Observations considérées' },
  { key: 'clusters', label: 'Clusters' },
  { key: 'ranked', label: 'Éléments classés' },
  { key: 'published_items', label: 'Items publiés' },
  { key: 'truncated_ranked', label: 'Éléments classés tronqués' },
];

function AbsentCoverageValue() {
  return (
    <span className="vx-cell-absent" role="img" aria-label="Non publié">
      —
    </span>
  );
}

/**
 * La couverture reste un dictionnaire non typé dans le contrat OpenAPI.
 * Seuls les nombres finis sont affichés, sans conversion ni valeur par défaut.
 */
function coverageValue(coverage: Record<string, unknown> | null, key: CoverageField['key']) {
  const value = coverage?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? (
    <code>{String(value)}</code>
  ) : (
    <AbsentCoverageValue />
  );
}

/** Format lisible déterministe ; l'attribut `dateTime` conserve la valeur brute. */
function readableUtcTimestamp(value: string): string {
  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) {
    return value;
  }
  const formatted = new Intl.DateTimeFormat('fr-CH', {
    dateStyle: 'medium',
    timeStyle: 'medium',
    timeZone: 'UTC',
  }).format(instant);
  return `${formatted} UTC`;
}

export function SnapshotRail({
  snapshotVersion,
  asOf,
  population,
  itemCount,
  rejectedCount,
  coverage,
}: SnapshotRailProps) {
  return (
    <aside className="vx-snapshot-rail" aria-label="Vérité du snapshot">
      <section className="vx-snapshot-rail-section" aria-labelledby="vx-snapshot-rail-title">
        <h2 id="vx-snapshot-rail-title">Snapshot publié</h2>
        <dl className="vx-snapshot-rail-facts">
          <div data-vx-snapshot-field="version">
            <dt>Version</dt>
            <dd>{snapshotVersion === null ? 'Non publié' : <code>{snapshotVersion}</code>}</dd>
          </div>
          <div data-vx-snapshot-field="as-of">
            <dt>Horodatage</dt>
            <dd>
              {asOf === null || asOf === '' ? (
                'Non publié'
              ) : (
                <time dateTime={asOf} title={asOf}>
                  {readableUtcTimestamp(asOf)}
                </time>
              )}
            </dd>
          </div>
          <div data-vx-snapshot-field="population">
            <dt>Population</dt>
            <dd>{population === null || population === '' ? 'Non publié' : <code>{population}</code>}</dd>
          </div>
          <div data-vx-snapshot-field="item-count">
            <dt>Items reçus</dt>
            <dd>
              <code>{itemCount}</code>
            </dd>
          </div>
          <div data-vx-snapshot-field="rejected-count">
            <dt>Items rejetés</dt>
            <dd>{rejectedCount === null ? 'Non publié' : <code>{rejectedCount}</code>}</dd>
          </div>
        </dl>
      </section>

      <section className="vx-snapshot-rail-section" aria-labelledby="vx-snapshot-coverage-title">
        <h2 id="vx-snapshot-coverage-title">Couverture publiée</h2>
        {coverage === null ? (
          <p className="vx-snapshot-rail-note">Couverture non publiée.</p>
        ) : (
          <p className="vx-snapshot-rail-note">Champs relayés sans agrégat local.</p>
        )}
        <dl className="vx-snapshot-rail-facts">
          {COVERAGE_FIELDS.map((field) => (
            <div key={field.key} data-vx-coverage-field={field.key}>
              <dt>{field.label}</dt>
              <dd>{coverageValue(coverage, field.key)}</dd>
            </div>
          ))}
        </dl>
      </section>
    </aside>
  );
}
