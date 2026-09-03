import { geometryValue, servedWidth } from './geometry.ts';

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

export interface SharePart {
  readonly key: string;
  readonly label: string;
  /** Pourcentage SERVI. `null` = non publié. */
  readonly pct: string | null;
  readonly tone?: ShareTone;
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
  const drawn = parts.filter((part) => geometryValue(part.pct) !== null);

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
            style={{ width: servedWidth(part.pct as string) }}
          />
        ))}
      </div>
      <ul className="vx-w2-shares-legend">
        {parts.map((part) => (
          <li key={part.key}>
            <span>{part.label}</span>{' '}
            <span>{part.pct === null ? 'non publié' : `${part.pct} ${unit}`}</span>
          </li>
        ))}
      </ul>
      {totalText === undefined ? null : <p className="vx-w2-absent">{totalText}</p>}
    </div>
  );
}
