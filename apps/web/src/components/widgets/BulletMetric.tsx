/**
 * BULLETMETRIC — la mesure quantitative précise, préférée à une jauge.
 *
 * POURQUOI PAS UNE JAUGE. Une jauge en arc occupe beaucoup de surface pour une
 * seule valeur, et sa lecture angulaire est approximative : l'œil compare mal
 * deux angles. Le bullet chart met la valeur, sa cible et ses paliers sur UN
 * axe linéaire, dans la hauteur d'une ligne de texte — donc plusieurs mesures
 * se comparent verticalement, ce qu'une rangée de cadrans ne permet pas. La
 * jauge reste pertinente pour une valeur unique et dominante ; partout
 * ailleurs, c'est cette forme qu'il faut.
 *
 * TOUT EST SERVI. La position de la valeur, celle de la cible et les bornes de
 * chaque palier arrivent en pourcentages SERVIS (`*_pct`, chaînes). Ce
 * composant ne divise rien, ne normalise rien et ne compare rien : il place ce
 * que le serveur a déjà situé. Si un pourcentage manque, la forme n'est pas
 * dessinée — une barre placée au jugé serait un chiffre inventé.
 *
 * LA COULEUR NE DIT RIEN SEULE. La valeur est écrite en toutes lettres à côté
 * de la barre, les paliers sont nommés dans la légende accessible, et la cible
 * porte son libellé. Quelqu'un qui ne distingue pas les teintes lit la même
 * chose.
 */

export interface BulletBand {
  /** Borne basse en pourcentage SERVI de l'axe. `null` = début de l'axe. */
  readonly fromPct: string | null;
  /** Borne haute en pourcentage SERVI. `null` = fin de l'axe. */
  readonly toPct: string | null;
  /** Nom du palier, tel que publié (« insuffisant », « correct », « bon »). */
  readonly name: string;
}

export interface BulletTarget {
  /** Position en pourcentage SERVI. */
  readonly pct: string;
  /** Libellé de la cible (« objectif 70 », « seuil minimal »). */
  readonly label: string;
}

export interface BulletMetricProps {
  readonly label: string;
  /** Position de la valeur en pourcentage SERVI. `null` ⇒ rien n'est dessiné. */
  readonly valuePct: string | null;
  /** Valeur en toutes lettres, verbatim. `null` = non publiée. */
  readonly valueText: string | null;
  readonly unit: string;
  /** Bornes de l'axe, verbatim, pour que l'échelle ne soit jamais implicite. */
  readonly boundsText: { readonly min: string; readonly max: string };
  readonly bands?: readonly BulletBand[];
  readonly target?: BulletTarget | null;
  /** Teinte de la valeur. `neutral` par défaut : la couleur se mérite. */
  readonly tone?: 'neutral' | 'positive' | 'negative' | 'warning';
  /** Raison publiée quand la valeur ne l'est pas. */
  readonly absentReason?: string | null;
}

/**
 * Un pourcentage SERVI n'est accepté que s'il est lisible ET dans [0, 100].
 * Hors bornes, on refuse : dessiner à 130 % sortirait la marque de son axe et
 * ferait croire à une valeur que personne n'a publiée.
 */
function positionServie(pct: string | null): number | null {
  if (pct === null) {
    return null;
  }
  const valeur = Number.parseFloat(pct.trim().replace('%', '').replace(',', '.'));
  if (Number.isNaN(valeur) || valeur < 0 || valeur > 100) {
    return null;
  }
  return valeur;
}

export function BulletMetric({
  label,
  valuePct,
  valueText,
  unit,
  boundsText,
  bands = [],
  target = null,
  tone = 'neutral',
  absentReason = null,
}: BulletMetricProps) {
  const position = positionServie(valuePct);
  const cible = target === null ? null : positionServie(target.pct);

  if (position === null || valueText === null) {
    // Pas de barre vide, pas de barre à zéro : une phrase qui dit pourquoi.
    return (
      <div className="vx-bullet" data-absent="true">
        <span className="vx-bullet-label">{label}</span>
        <p className="vx-bullet-reason" role="status">
          {absentReason ?? 'position non publiée par le serveur — aucune barre tracée'}
        </p>
      </div>
    );
  }

  const paliers = bands
    .map((bande) => {
      const debut = positionServie(bande.fromPct) ?? 0;
      const fin = positionServie(bande.toPct) ?? 100;
      return { ...bande, debut, largeur: Math.max(0, fin - debut) };
    })
    .filter((bande) => bande.largeur > 0);

  // Le nom accessible porte TOUT : valeur, unité, bornes, paliers, cible.
  // Il ne dépend d'aucun survol et se lit intégralement au clavier.
  const nomAccessible = [
    `${label} : ${valueText} ${unit}`,
    `axe de ${boundsText.min} à ${boundsText.max}`,
    paliers.length === 0 ? null : `paliers : ${paliers.map((b) => b.name).join(', ')}`,
    target === null ? null : target.label,
  ]
    .filter((part) => part !== null)
    .join(' — ');

  return (
    <div className="vx-bullet" data-tone={tone}>
      <span className="vx-bullet-label">{label}</span>
      <div className="vx-bullet-track" role="img" aria-label={nomAccessible}>
        {paliers.map((bande) => (
          <span
            key={`${bande.name}-${bande.debut}`}
            className="vx-bullet-band"
            style={{ left: `${bande.debut}%`, width: `${bande.largeur}%` }}
          />
        ))}
        <span className="vx-bullet-fill" style={{ width: `${position}%` }} />
        {cible === null || target === null ? null : (
          <span className="vx-bullet-target" style={{ left: `${cible}%` }} data-label={target.label} />
        )}
      </div>
      <span className="vx-bullet-value">
        <span className="vx-bullet-number">{valueText}</span>
        <span className="vx-bullet-unit">{unit}</span>
      </span>
      {/* Les bornes sont ÉCRITES : une échelle implicite n'est pas une échelle. */}
      <span className="vx-bullet-bounds">
        <span>{boundsText.min}</span>
        <span>{boundsText.max}</span>
      </span>
    </div>
  );
}
