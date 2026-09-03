import { geometryValue } from './geometry.ts';

/**
 * Anneau de parts SERVIES à chiffre central — forme admise par ADR-017.
 *
 * CE QUI EST SERVI, ET RIEN D'AUTRE. Chaque part arrive en POURCENTAGE servi
 * (chaîne) ; le chiffre central est une valeur SERVIE affichée verbatim (un
 * total publié, un compte, une part principale) — jamais une somme recalculée
 * dans le navigateur. La légende est OBLIGATOIRE : un angle ne porte pas son
 * chiffre, une légende si.
 *
 * REFUS. Une part sans pourcentage servi n'est pas dessinée et apparaît « non
 * publié » dans la légende ; au-delà de cinq parts, la forme est refusée
 * (protocole de nuance : au-delà, les teintes ne se distinguent plus et la
 * couleur porterait seule l'information).
 *
 * RELIQUAT. Si les parts servies ne totalisent pas 100 (arrondis serveur), le
 * rail reste visible : aucune part n'est dilatée pour « faire un tour ».
 */
const RADIUS = 54;
const CENTER = 60;

export const RING_CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * Cadre de dessin DÉRIVÉ des constantes ci-dessus — jamais écrit à la main.
 * Un `viewBox` littéral (« 0 0 120 120 ») a la forme d'un séparateur de
 * milliers et serait signalé, à juste titre, par `no-fabricated-values`.
 */
const VIEW_SIZE = CENTER * 2;

export const RING_TONES = ['silver', 'titanium', 'macro', 'option', 'warning'] as const;
export type RingTone = (typeof RING_TONES)[number];

/** Au-delà, la teinte porterait seule l'information. */
const MAX_PARTS = 5;

export interface RingPart {
  readonly key: string;
  readonly label: string;
  /** Pourcentage SERVI. `null` = non publié. */
  readonly pct: string | null;
  readonly tone?: RingTone;
}

export interface RingSharesProps {
  readonly parts: readonly RingPart[];
  /** Valeur SERVIE affichée au centre. `null` = non publiée. */
  readonly centerValue: string | null;
  readonly centerLabel: string;
  readonly centerUnit?: string;
  readonly ariaLabel: string;
}

const DEFAULT_TONES: readonly RingTone[] = ['silver', 'macro', 'titanium', 'option', 'warning'];

export function RingShares({
  parts,
  centerValue,
  centerLabel,
  centerUnit,
  ariaLabel,
}: RingSharesProps) {
  if (parts.length === 0) {
    return (
      <p className="vx-w2-absent" role="status">
        Aucune part publiée : aucun anneau tracé.
      </p>
    );
  }

  if (parts.length > MAX_PARTS) {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : trop de parts ({parts.length}) pour un anneau lisible ; au-delà de {MAX_PARTS}, la
        teinte porterait seule l’information.
      </p>
    );
  }

  const drawn: Array<{ part: RingPart; length: number; offset: number; tone: RingTone }> = [];
  let cursor = 0;
  for (const [index, part] of parts.entries()) {
    const value = geometryValue(part.pct);
    if (value === null) {
      continue;
    }
    const length = (RING_CIRCUMFERENCE * value) / 100;
    drawn.push({
      part,
      length,
      offset: cursor,
      tone: part.tone ?? DEFAULT_TONES[index % DEFAULT_TONES.length] ?? 'silver',
    });
    cursor += length;
  }

  return (
    <div className="vx-w2-ring">
      <div className="vx-w2-ring-figure">
        <svg
          className="vx-w2-ring-svg"
          viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
          role="img"
          aria-label={ariaLabel}
        >
          <circle className="vx-w2-ring-rail" cx={CENTER} cy={CENTER} r={RADIUS} />
          {drawn.map((arc) => (
            <circle
              key={arc.part.key}
              className="vx-w2-ring-arc"
              data-tone={arc.tone}
              cx={CENTER}
              cy={CENTER}
              r={RADIUS}
              strokeDasharray={`${arc.length} ${RING_CIRCUMFERENCE - arc.length}`}
              strokeDashoffset={-arc.offset}
              transform={`rotate(-90 ${CENTER} ${CENTER})`}
            />
          ))}
        </svg>
        <span className="vx-w2-ring-center" data-testid="ring-center">
          <span className="vx-w2-ring-center-value">
            {centerValue === null ? (
              <span data-absent="true">non publié</span>
            ) : (
              <>
                {centerValue}
                {centerUnit === undefined ? null : <span> {centerUnit}</span>}
              </>
            )}
          </span>
          <span className="vx-w2-ring-center-label">{centerLabel}</span>
        </span>
      </div>
      <ul className="vx-w2-ring-legend">
        {parts.map((part, index) => (
          <li key={part.key}>
            <span
              className="vx-w2-ring-swatch"
              data-tone={part.tone ?? DEFAULT_TONES[index % DEFAULT_TONES.length]}
              aria-hidden="true"
            />
            <span>{part.label}</span>
            <span>{part.pct === null ? 'non publié' : part.pct}</span>
          </li>
        ))}
      </ul>
      <details>
        <summary>Table équivalente</summary>
        <table className="vx-w2-figure-table">
          <thead>
            <tr>
              <th scope="col">Part servie</th>
              <th scope="col">Pourcentage servi</th>
            </tr>
          </thead>
          <tbody>
            {parts.map((part) => (
              <tr key={part.key}>
                <th scope="row">{part.label}</th>
                <td>{part.pct === null ? 'non publié' : part.pct}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

/** Au-delà, ce n'est plus une rangée : c'est une grille bento. */
const MAX_RINGS = 4;

export interface RingQuartetProps {
  readonly rings: readonly RingSharesProps[];
  readonly ariaLabel: string;
}

/**
 * Quatuor d'anneaux (référence 26) — une RANGÉE de quatre anneaux au plus,
 * chacun sur ses propres parts servies. Un cinquième est refusé plutôt que
 * masqué : masquer un anneau serait cacher une donnée servie.
 */
export function RingQuartet({ rings, ariaLabel }: RingQuartetProps) {
  if (rings.length > MAX_RINGS) {
    return (
      <p className="vx-w2-absent" role="status">
        Refus : un quatuor porte quatre anneaux au plus ({rings.length} demandés).
      </p>
    );
  }
  return (
    <section className="vx-w2-ring-quartet" aria-label={ariaLabel}>
      {rings.map((ring, index) => (
        // Un anneau du quatuor n'a pas d'identité propre : sa position est sa
        // seule clé stable (même motif que les barres de `Sparkline`).
        // biome-ignore lint/suspicious/noArrayIndexKey: anneaux positionnels
        <RingShares key={index} {...ring} />
      ))}
    </section>
  );
}
