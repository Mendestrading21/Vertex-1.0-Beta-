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
  /**
   * Version de SCHÉMA servie (LOT T4). Obligatoire et nullable comme les
   * autres : Opportunités la publiait et la rendait en tiret muet. En faire
   * une prop optionnelle aurait permis à un futur consommateur de la laisser
   * tomber en silence — ce que la primitive existe précisément pour empêcher.
   */
  readonly schemaVersion: number | string | null;
  readonly engineVersion: string | null;
  readonly sources: readonly string[];
  readonly method?: string | null;
  readonly population?: string | null;
}

/**
 * LOT T4 — L'ACCORD EN GENRE ET EN NOMBRE. « sources non publié » se lisait
 * comme une faute de frappe, et une faute de frappe fait douter du reste de la
 * ligne. Le français l'exige ; le deviner depuis le mot serait faux.
 */
function Absent({ what, accord = 'm' }: { readonly what: string; readonly accord?: 'm' | 'f' | 'fp' }) {
  const forme = accord === 'f' ? 'non publiée' : accord === 'fp' ? 'non publiées' : 'non publié';
  return (
    <span data-absent="true">
      {what} {forme}
    </span>
  );
}

export function ProvenanceLine({
  asOf,
  snapshotVersion,
  schemaVersion,
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
      {snapshotVersion === null ? <Absent what="version" accord="f" /> : <span>v{snapshotVersion}</span>}
      {' · '}
      {schemaVersion === null ? (
        <Absent what="schéma" />
      ) : (
        <span>
          schéma <code>{schemaVersion}</code>
        </span>
      )}
      {' · '}
      {schemaVersion === null ? (
        <Absent what="schéma" />
      ) : (
        <span>
          schéma <code>{schemaVersion}</code>
        </span>
      )}
      {' · '}
      {engineVersion === null || engineVersion === '' ? (
        <Absent what="moteur" />
      ) : (
        <span>{engineVersion}</span>
      )}
      {' · '}
      {sources.length === 0 ? (
        <Absent what="sources" accord="fp" />
      ) : (
        <span>sources : {sources.join(', ')}</span>
      )}
      {method === undefined || method === null || method === '' ? (
        <>
          {' · '}
          <Absent what="méthode" accord="f" />
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
          <Absent what="nature" accord="f" />
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
