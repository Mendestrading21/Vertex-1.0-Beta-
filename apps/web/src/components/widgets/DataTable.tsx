import type { ReactNode } from 'react';

import type { SignGroup } from '../markets/marketsView.ts';

/**
 * DATATABLE — la primitive unique des tableaux Vertex.
 *
 * POURQUOI ELLE EXISTE. Le frontend rendait **24 fichiers `<table>` pour 21
 * familles de classes CSS distinctes**, mesurées et listées dans
 * `docs/05-design/refonte/00-systeme-visuel.md` §3. Douze d'entre elles
 * déclaraient exactement les mêmes trois propriétés dans deux blocs séparés ;
 * `vx-w2-spark-table` et `vx-w2-figure-table` étaient strictement identiques ;
 * `vx-opp-table` était posée dans le JSX sans qu'aucune règle CSS ne la
 * décrive. Vingt-et-une grammaires pour un seul besoin, c'est vingt-et-une
 * occasions de diverger.
 *
 * CE QUE LE TYPE GARANTIT, ET QUE LA REVUE NE GARANTISSAIT PAS.
 *
 *   - Une colonne numérique DOIT porter une unité (`unit: string`, non
 *     nullable) : un nombre financier sans unité n'est pas une donnée, c'est
 *     un chiffre.
 *   - `rowKey` n'a AUCUNE valeur par défaut. La clé vient de la donnée servie ;
 *     un index de tableau change quand l'ordre change, et fait alors mentir la
 *     sélection et le focus.
 *   - `emptyLabel` est obligatoire : une table sans ligne se NOMME, elle ne se
 *     rend pas vide ni ne se remplit d'un tiret.
 *   - `servedOrder` est explicitement `null` quand le serveur ne publie pas
 *     d'ordre. Le client ne trie pas : il DÉCLARE l'ordre reçu. Rendre ce champ
 *     obligatoire empêche d'inventer un tri en le faisant passer pour servi.
 *   - `sign` lit un signe SERVI et ne le déduit jamais d'un nombre — la couleur
 *     financière suit la donnée, pas une comparaison faite ici.
 *
 * CE QU'ELLE NE FAIT PAS, ET NE FERA PAS. Aucun calcul : ni total, ni moyenne,
 * ni pourcentage, ni conversion d'unité, ni arrondi. `cell` rend une valeur
 * servie verbatim, ou une absence typée. La porte
 * `no-authoritative-calculation` reste la loi, et cette primitive ne lui ouvre
 * aucune brèche.
 *
 * ACCESSIBILITÉ. `<caption>` VISIBLE et obligatoire — il remplace les 18
 * `aria-label` posés sur `<table>`, sémantiquement plus faibles et invisibles à
 * l'écran. Exactement une colonne porte `rowHeader`, rendue en
 * `<th scope="row">`. En mode `panel`, l'enveloppe défilante est une région
 * focalisable au clavier (`tabIndex={0}`, `role="region"`), sans quoi son
 * contenu est inatteignable sans souris.
 */

/** Densités du desk. `standard` est le défaut. */
export type Density = 'comfortable' | 'standard' | 'dense';

/** Alignement dérivé du TYPE de valeur, jamais d'une préférence esthétique. */
export type ColumnAlign = 'text' | 'num' | 'status';

/** Largeurs de composition. Jamais un pixel libre dans une page. */
export type ColumnWidth = 'auto' | 'min' | 'ch8' | 'ch12' | 'ch16';

interface ColonneBase<Row> {
  readonly key: string;
  /** Nom de colonne, rendu en micro-libellé. */
  readonly header: string;
  /**
   * `true` ⇒ `<th scope="row">`. C'est la colonne d'IDENTITÉ de la ligne.
   * Exactement une par table, vérifié à l'exécution.
   */
  readonly rowHeader?: boolean;
  readonly width?: ColumnWidth;
  /** Rend une valeur servie verbatim, ou une absence typée (`AbsentCell`). */
  readonly cell: (row: Row) => ReactNode;
  /**
   * Signe SERVI de la ligne pour cette colonne. `null` = aucune couleur.
   * Il n'est JAMAIS déduit ici d'une comparaison numérique.
   */
  readonly sign?: (row: Row) => SignGroup | null;
}

/**
 * Une colonne numérique EXIGE son unité. Ce n'est pas une convention de revue :
 * c'est le type qui refuse la colonne sans elle.
 */
interface ColonneNumerique<Row> extends ColonneBase<Row> {
  readonly align: 'num';
  readonly unit: string;
}

interface ColonneTextuelle<Row> extends ColonneBase<Row> {
  readonly align: 'text' | 'status';
  readonly unit?: string | null;
}

export type DataColumn<Row> = ColonneNumerique<Row> | ColonneTextuelle<Row>;

export interface ServedOrder {
  /** Clé de colonne sur laquelle le SERVEUR a trié. */
  readonly by: string;
  readonly direction: 'asc' | 'desc';
}

export interface DataTableProps<Row> {
  readonly id: string;
  /** `<caption>` visible et obligatoire. */
  readonly caption: string;
  /** Unité, période, population : la phrase qui qualifie la table. */
  readonly captionDetail?: string;
  readonly columns: ReadonlyArray<DataColumn<Row>>;
  readonly rows: readonly Row[];
  /** Clé stable SERVIE. Jamais un index. */
  readonly rowKey: (row: Row) => string;
  /**
   * Trois densités NOMMÉES, jamais configurables par l'utilisateur : chaque
   * composant choisit celle que son contenu exige. Une densité réglable serait
   * une quatrième chose à maintenir et à tester sur douze pages, pour un gain
   * que personne n'a demandé.
   *   - `comfortable` : grands résumés, peu de lignes ;
   *   - `standard` : défaut, panneaux d'analyse ;
   *   - `dense` : chaîne d'options, registres, tables longues.
   */
  readonly density?: Density;
  /** `panel` ⇒ enveloppe défilante bornée, en-tête collant, région au clavier. */
  readonly overflow: 'none' | 'panel';
  /** Nommé quand `rows` est vide. Jamais une table vide, jamais un tiret. */
  readonly emptyLabel: string;
  readonly selectedRowKey?: string | null;
  readonly onOpenRow?: (key: string) => void;
  /** Libellé accessible du bouton d'ouverture, quand `onOpenRow` est fourni. */
  readonly rowActionLabel?: (row: Row) => string;
  /** Ordre SERVI, ou `null` si le serveur n'en publie pas. */
  readonly servedOrder: ServedOrder | null;
  /** Méthode, version, source, `as_of`. */
  readonly footnote?: ReactNode;
}

const DIRECTION_FR: Readonly<Record<'asc' | 'desc', string>> = {
  asc: 'croissant',
  desc: 'décroissant',
};

/**
 * La phrase d'ordre, en toutes lettres.
 *
 * Quand le serveur ne publie pas d'ordre, on le DIT. Le silence laisserait
 * croire que l'ordre affiché a un sens, alors qu'il n'est que celui de la
 * réponse.
 */
function phraseOrdre<Row>(
  ordre: ServedOrder | null,
  colonnes: ReadonlyArray<DataColumn<Row>>,
): string {
  if (ordre === null) {
    return "ordre d'affichage : celui de la réponse, aucun tri publié";
  }
  const colonne = colonnes.find((c) => c.key === ordre.by);
  return `trié par le serveur sur « ${colonne?.header ?? ordre.by} », ordre ${DIRECTION_FR[ordre.direction]}`;
}

export function DataTable<Row>({
  id,
  caption,
  captionDetail,
  columns,
  rows,
  rowKey,
  density = 'standard',
  overflow,
  emptyLabel,
  selectedRowKey = null,
  onOpenRow,
  rowActionLabel,
  servedOrder,
  footnote,
}: DataTableProps<Row>) {
  // INVARIANT VÉRIFIÉ À L'EXÉCUTION, pas seulement documenté : une table sans
  // en-tête de ligne n'a pas d'identité lisible par un lecteur d'écran, et deux
  // en-têtes de ligne rendent la lecture ambiguë. Échouer ici est préférable à
  // rendre une table silencieusement inaccessible.
  const entetesDeLigne = columns.filter((colonne) => colonne.rowHeader === true);
  if (entetesDeLigne.length !== 1) {
    throw new Error(
      `DataTable « ${id} » : exactement une colonne doit porter rowHeader, ${entetesDeLigne.length} trouvée(s).`,
    );
  }
  if (onOpenRow !== undefined && rowActionLabel === undefined) {
    throw new Error(
      `DataTable « ${id} » : onOpenRow exige rowActionLabel — un bouton sans nom accessible n'est pas ouvrable au clavier.`,
    );
  }

  const legende = `${caption}${captionDetail === undefined ? '' : ` — ${captionDetail}`}`;
  const detail = `${captionDetail === undefined ? '' : `${captionDetail} · `}${phraseOrdre(servedOrder, columns)}`;

  if (rows.length === 0) {
    // Une table vide n'est pas une table : c'est un état, et il se nomme.
    return (
      <div className="vx-dt-empty" data-density={density}>
        <p className="vx-dt-empty-label">{caption}</p>
        <p className="vx-dt-empty-reason" role="status">
          {emptyLabel}
        </p>
        {footnote === undefined ? null : <div className="vx-dt-foot">{footnote}</div>}
      </div>
    );
  }

  const table = (
    <table className="vx-dt" id={id} data-density={density}>
      <caption className="vx-dt-caption">
        <span className="vx-dt-caption-main">{caption}</span>
        <span className="vx-dt-caption-detail">{detail}</span>
      </caption>
      <thead>
        <tr>
          {columns.map((colonne) => {
            // `aria-sort` n'est posé QUE sur la colonne réellement triée par le
            // serveur. Le poser partout dirait à un lecteur d'écran que chaque
            // colonne est triable, ce qui est faux : le client ne trie pas.
            const trie: 'ascending' | 'descending' | null =
              servedOrder === null || servedOrder.by !== colonne.key
                ? null
                : servedOrder.direction === 'asc'
                  ? 'ascending'
                  : 'descending';
            return (
              <th
                key={colonne.key}
                scope="col"
                data-align={colonne.align}
                data-width={colonne.width ?? 'auto'}
                {...(trie === null ? {} : { 'aria-sort': trie })}
              >
                <span className="vx-dt-head-label">{colonne.header}</span>
                {/* L'unité vit DANS l'en-tête, pas dans un tooltip : une colonne
                    dont l'unité n'est atteignable qu'au survol est illisible au
                    clavier et absente des captures. */}
                {/*
                  L'ESPACE N'EST PAS DÉCORATIF. Sans lui, le NOM ACCESSIBLE de
                  l'en-tête est la concaténation brute des deux segments :
                  « tested_atUTC ». C'est ce que lit un lecteur d'écran et ce
                  que produit toute extraction de texte — mesuré au deuxième
                  consommateur de cette primitive, pas au premier, parce que le
                  premier n'avait aucune colonne dont l'unité fût un mot.
                  Visuellement, l'unité est déjà sur sa propre ligne ; l'espace
                  ne change rien à l'œil et rétablit « tested_at UTC » à
                  l'oreille.
                */}
                {colonne.unit === undefined || colonne.unit === null ? null : (
                  <>
                    {' '}
                    <span className="vx-dt-head-unit">{colonne.unit}</span>
                  </>
                )}
              </th>
            );
          })}
          {onOpenRow === undefined ? null : (
            <th scope="col" data-align="status" data-width="min">
              <span className="vx-dt-head-label">détail</span>
            </th>
          )}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const cle = rowKey(row);
          return (
            <tr
              key={cle}
              {...(selectedRowKey === cle ? { 'data-selected': 'true', 'aria-current': 'true' as const } : {})}
            >
              {columns.map((colonne) => {
                const signe = colonne.sign?.(row) ?? null;
                const contenu = colonne.cell(row);
                const attributs: Record<string, string> = {
                  'data-align': colonne.align,
                  'data-width': colonne.width ?? 'auto',
                  ...(signe === null ? {} : { 'data-sign': signe }),
                };
                return colonne.rowHeader === true ? (
                  <th key={colonne.key} scope="row" {...attributs}>
                    {contenu}
                  </th>
                ) : (
                  <td key={colonne.key} {...attributs}>
                    {contenu}
                  </td>
                );
              })}
              {onOpenRow === undefined || rowActionLabel === undefined ? null : (
                <td data-align="status" data-width="min">
                  {/* Un vrai `button`, jamais un `div` cliquable : le clavier,
                      le focus et le lecteur d'écran en dépendent. */}
                  <button
                    type="button"
                    className="vx-dt-open"
                    onClick={() => {
                      onOpenRow(cle);
                    }}
                  >
                    {rowActionLabel(row)}
                  </button>
                </td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  return (
    <div className="vx-dt-wrap">
      {overflow === 'panel' ? (
        // Région focalisable : sans `tabIndex`, une zone défilante est
        // inatteignable au clavier et son contenu devient invisible.
        <div className="vx-dt-scroll" data-overflow="panel" role="region" aria-label={legende} tabIndex={0}>
          {table}
        </div>
      ) : (
        table
      )}
      {footnote === undefined ? null : <div className="vx-dt-foot">{footnote}</div>}
    </div>
  );
}
