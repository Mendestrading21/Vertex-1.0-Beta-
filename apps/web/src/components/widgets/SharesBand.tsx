import { geometryValue, ratioWidth, servedWidth } from './geometry.ts';

/**
 * Bande de parts SERVIES — largeur = chaîne servie, verbatim.
 *
 * TEINTES. Trois teintes non directionnelles (`silver`, `titanium`, `macro`)
 * plus `option` RÉSERVÉE au domaine des options (`references/ICON_SYSTEM.md` :
 * « option uniquement pour identifier la classe d'actif »). Un MOTIF distingue
 * chaque part : « une différence subtile de surface ne porte jamais seule une
 * information » (`references/visual-identity.md`).
 *
 * RELIQUAT. Si la somme des parts servies n'atteint pas 100 (arrondis
 * serveur), le rail reste visible. Aucune part n'est étirée, aucun « autres »
 * n'est fabriqué : additionner les parts serait produire une valeur.
 */
export const SHARE_TONES = ['silver', 'titanium', 'macro', 'option'] as const;
export type ShareTone = (typeof SHARE_TONES)[number];

const PATTERNS = ['a', 'b', 'c', 'd', 'e', 'f'] as const;

/**
 * Une part est servie SOIT en pourcentage (`pct`), SOIT en ratio 0–1
 * (`ratio`) — jamais les deux. L'identifiant DIT l'unité de la chaîne servie,
 * pour que la géométrie ne se trompe pas d'échelle et que la légende affiche
 * la chaîne verbatim, dans l'unité que l'appelant déclare.
 */
export type SharePart = {
  readonly key: string;
  readonly label: string;
  readonly tone?: ShareTone;
} & (
  | {
      /** Pourcentage SERVI. `null` = non publié. */
      readonly pct: string | null;
      readonly ratio?: undefined;
    }
  | {
      /** Ratio SERVI (0–1). `null` = non publié. */
      readonly ratio: string | null;
      readonly pct?: undefined;
    }
);

/** Chaîne servie de la part, quelle que soit son unité déclarée. */
function servedText(part: SharePart): string | null {
  return part.ratio === undefined ? part.pct : part.ratio;
}

/** Largeur de la part, ou `null` si rien n'est dessinable. */
function partWidth(part: SharePart): string | null {
  if (part.ratio !== undefined) {
    return part.ratio === null ? null : ratioWidth(part.ratio);
  }
  return part.pct === null || geometryValue(part.pct) === null ? null : servedWidth(part.pct);
}

export interface SharesBandProps {
  readonly parts: readonly SharePart[];
  readonly unit: string;
  readonly ariaLabel: string;
  /** Total SERVI (ex. un Herfindahl publié). Jamais un total recalculé. */
  readonly totalText?: string;
  readonly emptyLabel?: string;
}

const DEFAULT_TONES: readonly ShareTone[] = ['silver', 'titanium', 'macro', 'option'];

export function SharesBand({
  parts,
  unit,
  ariaLabel,
  totalText,
  emptyLabel,
}: SharesBandProps) {
  const drawn = parts.filter((part) => partWidth(part) !== null);

  if (drawn.length === 0) {
    return (
      <p className="vx-w2-absent" role="status">
        {emptyLabel ?? 'Aucune part publiée : aucune bande tracée.'}
      </p>
    );
  }

  return (
    <div className="vx-w2-shares-block">
      <div className="vx-w2-shares" role="img" aria-label={ariaLabel}>
        {drawn.map((part, index) => (
          <span
            key={part.key}
            className="vx-w2-share"
            data-tone={part.tone ?? DEFAULT_TONES[index % DEFAULT_TONES.length]}
            data-pattern={PATTERNS[index % PATTERNS.length]}
            style={{ width: partWidth(part) as string }}
          />
        ))}
      </div>
      <ul className="vx-w2-shares-legend">
        {parts.map((part) => (
          <li key={part.key}>
            <span>{part.label}</span>{' '}
            <span>{servedText(part) === null ? 'non publié' : `${servedText(part) as string} ${unit}`}</span>
          </li>
        ))}
      </ul>
      {totalText === undefined ? null : <p className="vx-w2-absent">{totalText}</p>}
    </div>
  );
}
