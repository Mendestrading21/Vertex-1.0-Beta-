/**
 * MICRORANGE — où se situe une valeur dans son amplitude servie.
 *
 * L'USAGE CANONIQUE : « bas 30 jours 12,11 · haut 30 jours 28,43 · actuel
 * 14,35 ». Trois chiffres qui, écrits côte à côte, obligent le lecteur à faire
 * la position dans sa tête. La barre la donne d'un regard, et les trois chiffres
 * restent écrits — la forme ajoute, elle ne remplace pas.
 *
 * POSITION SERVIE. Le placement du curseur arrive en pourcentage SERVI. Ce
 * composant ne fait PAS `(valeur − bas) / (haut − bas)` : ce serait un calcul
 * financier dans le navigateur, et il serait faux dès que l'échelle n'est pas
 * linéaire. Sans position servie, rien n'est dessiné.
 */

export interface MicroRangeProps {
  readonly label: string;
  /** Position du curseur en pourcentage SERVI de l'amplitude. */
  readonly positionPct: string | null;
  /** Valeur courante, verbatim. */
  readonly valueText: string | null;
  /** Bornes de l'amplitude, verbatim. */
  readonly lowText: string;
  readonly highText: string;
  readonly unit: string;
  /** Période de l'amplitude (« 30 jours », « 52 semaines »). */
  readonly windowLabel: string;
  readonly absentReason?: string | null;
}

function positionServie(pct: string | null): number | null {
  if (pct === null) {
    return null;
  }
  const valeur = Number.parseFloat(pct.trim().replace('%', '').replace(',', '.'));
  return Number.isNaN(valeur) || valeur < 0 || valeur > 100 ? null : valeur;
}

export function MicroRange({
  label,
  positionPct,
  valueText,
  lowText,
  highText,
  unit,
  windowLabel,
  absentReason = null,
}: MicroRangeProps) {
  const position = positionServie(positionPct);

  if (position === null || valueText === null) {
    return (
      <div className="vx-range" data-absent="true">
        <span className="vx-range-label">{label}</span>
        <p className="vx-range-reason" role="status">
          {absentReason ?? 'position dans l’amplitude non publiée — aucun curseur placé'}
        </p>
      </div>
    );
  }

  const nom = `${label} sur ${windowLabel} : ${valueText} ${unit}, amplitude de ${lowText} à ${highText}`;

  return (
    <div className="vx-range">
      <span className="vx-range-label">{label}</span>
      <div className="vx-range-track" role="img" aria-label={nom}>
        <span className="vx-range-cursor" style={{ left: `${position}%` }} />
      </div>
      {/* Les trois chiffres restent ÉCRITS : la barre situe, elle ne chiffre pas. */}
      <span className="vx-range-bounds">
        <span className="vx-range-low">{lowText}</span>
        <span className="vx-range-current">{valueText}</span>
        <span className="vx-range-high">{highText}</span>
      </span>
      <span className="vx-range-window">
        {windowLabel} · {unit}
      </span>
    </div>
  );
}
