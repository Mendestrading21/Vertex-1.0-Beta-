/**
 * Ligne de provenance en pied de widget — « données au <as_of> · v<n> ·
 * <moteur> · sources : … · méthode · nature ».
 *
 * Chaque champ ABSENT est dit « non publié » À SA PLACE : une provenance
 * partielle reste lisible comme partielle, jamais comme complète.
 */
export interface ProvenanceLineProps {
  readonly asOf: string | null;
  readonly snapshotVersion: number | string | null;
  readonly engineVersion: string | null;
  readonly sources: readonly string[];
  readonly method?: string | null;
  readonly population?: string | null;
}

function Absent({ what }: { readonly what: string }) {
  return <span data-absent="true">{what} non publié</span>;
}

export function ProvenanceLine({
  asOf,
  snapshotVersion,
  engineVersion,
  sources,
  method,
  population,
}: ProvenanceLineProps) {
  return (
    <p className="vx-w2-provenance" data-testid="provenance-line">
      {asOf === null || asOf === '' ? (
        <Absent what="horodatage" />
      ) : (
        <>
          données au <time dateTime={asOf}>{asOf}</time>
        </>
      )}
      {' · '}
      {snapshotVersion === null ? <Absent what="version" /> : <span>v{snapshotVersion}</span>}
      {' · '}
      {engineVersion === null || engineVersion === '' ? (
        <Absent what="moteur" />
      ) : (
        <span>{engineVersion}</span>
      )}
      {' · '}
      {sources.length === 0 ? (
        <Absent what="sources" />
      ) : (
        <span>sources : {sources.join(', ')}</span>
      )}
      {method === undefined || method === null || method === '' ? (
        <>
          {' · '}
          <Absent what="méthode" />
        </>
      ) : (
        <>
          {' · méthode '}
          <code>{method}</code>
        </>
      )}
      {population === undefined || population === null || population === '' ? (
        <>
          {' · '}
          <Absent what="nature" />
        </>
      ) : (
        <>
          {' · nature '}
          <code>{population}</code>
        </>
      )}
    </p>
  );
}
