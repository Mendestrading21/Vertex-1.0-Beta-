/**
 * L'ABSENCE DE VALEUR, dite une seule fois pour tout le produit.
 *
 * POURQUOI CE FICHIER EXISTE (LOT T4). L'interface écrivait `?? '—'` à
 * 163 endroits, sur 33 fichiers. Un tiret nu ne dit rien : dans une liste de
 * dénombrements, il est indiscernable d'un zéro SERVI, et
 * `.claude/rules/frontend.md` l'interdit textuellement — « ne jamais remplacer
 * une donnée absente par `0`, `—` ambigu, une fixture ou une ancienne valeur
 * non datée ».
 *
 * CE FICHIER EST LE SEUL DU DÉPÔT QUI A LE DROIT D'ÉCRIRE CE GLYPHE. La porte
 * `src/design/no-ambiguous-dash.test.ts` refuse partout ailleurs. La tolérance
 * n'est donc pas une liste d'attributs qu'on peut satisfaire à vide : c'est un
 * composant NOMMÉ dont la signature oblige à regarder ce qui manque avant de
 * poser quoi que ce soit.
 *
 * DEUX RÈGLES D'ACCESSIBILITÉ, apprises en chemin.
 *
 *   1. `role="img"` est ce qui donne le NOM ACCESSIBLE. `aria-label` posé sur
 *      le rôle implicite `generic` d'un `<span>` est ignoré par plusieurs
 *      technologies d'assistance, et `title` seul n'est pas fiable. Une garde
 *      qui n'aurait exigé qu'`aria-label` + `title` aurait BÉNI une régression.
 *   2. Le code SERVEUR reste verbatim dans le libellé, même quand une
 *      traduction française existe. Deux assertions le cherchent tel quel
 *      (`getAllByLabelText(/crossed_quote/)`), et surtout : c'est le code qui
 *      est la preuve, la traduction n'est qu'un confort de lecture.
 */

/**
 * Vocabulaire FERMÉ des natures d'absence. Chacune répond à une question
 * différente, et les confondre change le sens :
 *
 *   - `not_published`  : le serveur n'a pas envoyé le champ. Cas par défaut.
 *   - `not_computed`   : le champ existe au contrat, mais le moteur a REFUSÉ
 *                        de le produire, avec une raison typée. Ce n'est pas
 *                        « rien n'a été collecté » : c'est « le moteur a dit
 *                        non », et les deux appellent des actions différentes.
 *   - `not_applicable` : la question ne se pose pas pour cette ligne. Le
 *                        serveur n'a RIEN omis — écrire « non publié » ici lui
 *                        adresserait un reproche injustifié.
 *   - `not_entered`    : l'humain n'a pas renseigné le champ (journal manuel,
 *                        import CSV). L'absence vient de la saisie, pas du
 *                        serveur.
 *   - `not_recognised` : la valeur servie est hors du vocabulaire fermé.
 */
export const ABSENCE_NATURES = {
  not_published: { m: 'non publié', f: 'non publiée' },
  not_computed: { m: 'non calculé', f: 'non calculée' },
  not_applicable: { m: 'sans objet', f: 'sans objet' },
  not_entered: { m: 'non renseigné', f: 'non renseignée' },
  not_recognised: { m: 'non reconnu', f: 'non reconnue' },
} as const satisfies Record<string, { readonly m: string; readonly f: string }>;

export type AbsenceNature = keyof typeof ABSENCE_NATURES;

/** Genre grammatical de `quoi`. Le français l'exige ; le deviner serait faux. */
export type Accord = 'm' | 'f';

/**
 * Le libellé français d'une absence : CE QUI manque, sa nature, et — s'il est
 * servi — le motif exact, code serveur compris.
 *
 * `quoi` nomme le champ. Jamais un « non publié » orphelin dont le lecteur ne
 * saurait pas à quoi il se rapporte.
 */
export function absenceLabel(
  quoi: string,
  nature: AbsenceNature,
  reason: string | null,
  explained?: string,
  accord: Accord = 'm',
): string {
  const forme = ABSENCE_NATURES[nature][accord];
  const base = `${quoi} ${forme}`;
  if (reason === null || reason.trim() === '') {
    return base;
  }
  // Le code brut est TOUJOURS présent : il est la preuve. La traduction, quand
  // elle existe, le précède — elle ne le remplace jamais.
  return explained === undefined || explained.trim() === ''
    ? `${base} (${reason})`
    : `${base} (${explained} : ${reason})`;
}

export interface AbsentCellProps {
  /** Le champ qui manque, nommé. */
  readonly quoi: string;
  readonly nature: AbsenceNature;
  /**
   * Motif SERVI par le serveur, verbatim. `null` = aucun motif publié — et
   * alors aucun attribut de motif n'est inventé. Obligatoire mais nullable :
   * on ne peut pas l'oublier, on doit décider.
   */
  readonly reason: string | null;
  /** Traduction française du motif, quand le produit en connaît une. */
  readonly explained?: string;
  readonly accord?: Accord;
}

/**
 * Rendu DENSE d'une absence : le glyphe, avec son sens porté par le nom
 * accessible et par des attributs de donnée.
 *
 * RÉSERVÉ AUX TABLES DENSES — au moins cinq colonnes de valeurs ou vingt
 * lignes attendues, ET un motif servi par cellule. Partout ailleurs, l'absence
 * s'écrit en toutes lettres : dans une carte à trois champs, « non publié » se
 * lit, et un tiret ne se lit pas.
 */
export function AbsentCell({ quoi, nature, reason, explained, accord = 'm' }: AbsentCellProps) {
  const label = absenceLabel(quoi, nature, reason, explained, accord);
  return (
    <span
      className="vx-cell-absent"
      data-absent="true"
      {...(reason === null || reason.trim() === '' ? {} : { 'data-reason': reason })}
      role="img"
      aria-label={label}
      title={label}
    >
      —
    </span>
  );
}
