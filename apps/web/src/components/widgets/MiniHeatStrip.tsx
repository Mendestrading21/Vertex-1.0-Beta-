/**
 * MINIHEATSTRIP — une bande de cellules servies, une par période.
 *
 * L'USAGE : trente jours de volatilité, quinze séances d'activité, une semaine
 * d'erreurs de collecte. Chaque cellule porte une BANDE NOMMÉE par le serveur
 * (« forte », « moyenne », « faible », « aucune donnée »), jamais un nombre que
 * le navigateur aurait classé lui-même. Ranger une valeur dans une bande est un
 * jugement ; il appartient au moteur Python.
 *
 * POURQUOI DES BANDES ET PAS UN DÉGRADÉ CONTINU. Un dégradé continu suppose une
 * échelle, donc une normalisation, donc un calcul. Il rend aussi la lecture
 * approximative : l'œil compare mal deux nuances voisines. Cinq bandes nommées
 * se distinguent, se comptent, et se disent à voix haute.
 *
 * L'ABSENCE EST UNE BANDE. `null` n'est pas la bande la plus basse : c'est
 * `unknown`, visuellement distincte (creuse, hachurée par la bordure) et
 * nommée. Une cellule vide traitée comme « faible » inventerait une mesure.
 */

/** Les cinq bandes admises. Aucune n'est un synonyme d'une autre. */
export const HEAT_BANDS = ['none', 'low', 'medium', 'high', 'extreme'] as const;
export type HeatBand = (typeof HEAT_BANDS)[number] | 'unknown';

export interface HeatCell {
  readonly key: string;
  /** Bande SERVIE. `null` ⇒ `unknown`, rendue en creux. */
  readonly band: HeatBand | null;
  /** Libellé de la période (date ISO servie, nom de séance). */
  readonly label: string;
  /** Valeur servie, verbatim, pour la table équivalente et le nom accessible. */
  readonly valueText?: string | null;
}

export interface MiniHeatStripProps {
  readonly cells: readonly HeatCell[];
  readonly caption: string;
  readonly unit: string;
  /** Nom lisible de chaque bande, SERVI ou déclaré par la page. */
  readonly bandLabels: Readonly<Record<string, string>>;
}

export function MiniHeatStrip({ cells, caption, unit, bandLabels }: MiniHeatStripProps) {
  if (cells.length === 0) {
    return (
      <p className="vx-micro-absent" role="status">
        Refus : aucune période servie — la bande n’est pas tracée.
      </p>
    );
  }

  const inconnues = cells.filter((cellule) => cellule.band === null || cellule.band === 'unknown');
  const nom = [
    `${caption} — ${cells.length} périodes, ${unit}`,
    inconnues.length === 0 ? null : `${inconnues.length} période(s) sans donnée publiée`,
  ]
    .filter((part) => part !== null)
    .join(' — ');

  return (
    <div className="vx-heatstrip" role="img" aria-label={nom}>
      {cells.map((cellule) => {
        const bande: HeatBand = cellule.band ?? 'unknown';
        // Chaque cellule porte son nom complet : la bande n'est jamais lisible
        // par la seule couleur, ni réservée à un survol de souris.
        const titre = `${cellule.label} : ${bandLabels[bande] ?? bande}${
          cellule.valueText === null || cellule.valueText === undefined ? '' : ` — ${cellule.valueText} ${unit}`
        }`;
        return (
          <span
            key={cellule.key}
            className="vx-heatstrip-cell"
            data-band={bande}
            title={titre}
            aria-label={titre}
            role="img"
          />
        );
      })}
    </div>
  );
}
