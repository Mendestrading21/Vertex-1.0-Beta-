/**
 * MICROBARS — une distribution SERVIE, dans la hauteur d'une ligne.
 *
 * CE QU'ELLE EST. Un histogramme minuscule : pas d'axe, pas de légende, pas de
 * tooltip. Elle transmet UNE forme — croissant, décroissant, creusé, plat — en
 * moins d'une seconde, à côté du chiffre qu'elle contextualise. Dès qu'une
 * valeur précise doit être lue, ce n'est plus cette forme qu'il faut : c'est
 * une table.
 *
 * HAUTEURS SERVIES. Chaque barre reçoit sa hauteur en pourcentage SERVI
 * (`*_pct`). Ce composant ne cherche pas le maximum de la série pour
 * normaliser : normaliser, c'est calculer, et le rapport entre deux barres
 * deviendrait une affirmation du navigateur. Le serveur situe, le composant
 * dessine.
 *
 * UNE ABSENCE N'EST PAS UN ZÉRO. Une barre dont la hauteur n'est pas publiée
 * est rendue en creux, avec son motif nommé dans la légende accessible — pas
 * une barre à hauteur nulle, qui dirait « mesuré, et vaut zéro ».
 */

export interface MicroBar {
  readonly key: string;
  /** Hauteur en pourcentage SERVI. `null` = non publiée, rendue en creux. */
  readonly heightPct: string | null;
  /** Libellé de la barre, pour la légende accessible. */
  readonly label: string;
  /** Signe SERVI. Sans lui, la barre reste neutre. */
  readonly sign?: 'up' | 'down' | 'flat' | null;
}

export interface MicroBarsProps {
  readonly bars: readonly MicroBar[];
  /** Ce que la série représente, en une phrase. */
  readonly caption: string;
  readonly unit: string;
  /** Période nommée. Une série sans période n'est pas une mesure. */
  readonly windowLabel: string;
}

function hauteurServie(pct: string | null): number | null {
  if (pct === null) {
    return null;
  }
  const valeur = Number.parseFloat(pct.trim().replace('%', '').replace(',', '.'));
  if (Number.isNaN(valeur) || valeur < 0 || valeur > 100) {
    return null;
  }
  return valeur;
}

export function MicroBars({ bars, caption, unit, windowLabel }: MicroBarsProps) {
  if (windowLabel.trim() === '') {
    return (
      <p className="vx-micro-absent" role="status">
        Refus : période non publiée — la distribution n’est pas tracée.
      </p>
    );
  }
  if (bars.length === 0) {
    return (
      <p className="vx-micro-absent" role="status">
        Refus : aucune barre servie — rien à représenter.
      </p>
    );
  }

  const manquantes = bars.filter((barre) => hauteurServie(barre.heightPct) === null);
  const nom = [
    `${caption} — ${windowLabel}, ${unit}`,
    `${bars.length} barres servies`,
    manquantes.length === 0 ? null : `${manquantes.length} hauteur(s) non publiée(s) : ${manquantes.map((b) => b.label).join(', ')}`,
  ]
    .filter((part) => part !== null)
    .join(' — ');

  return (
    <div className="vx-micro-bars" role="img" aria-label={nom}>
      {bars.map((barre) => {
        const hauteur = hauteurServie(barre.heightPct);
        return (
          <span
            key={barre.key}
            className="vx-micro-bar"
            data-absent={hauteur === null ? 'true' : 'false'}
            {...(barre.sign === null || barre.sign === undefined ? {} : { 'data-sign': barre.sign })}
            // Une hauteur non publiée occupe toute la piste EN CREUX : elle se
            // voit comme un trou, jamais comme une mesure basse.
            style={{ height: `${hauteur ?? 100}%` }}
          />
        );
      })}
    </div>
  );
}
