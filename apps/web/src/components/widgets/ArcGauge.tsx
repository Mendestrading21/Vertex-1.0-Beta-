import { geometryValue, textDensityOf } from './geometry.ts';

/**
 * Jauge en ARC graduée — forme admise par ADR-017 UNIQUEMENT lorsque la valeur
 * est bornée et servie AVEC ses seuils et sa POSITION en pourcentage
 * (coordonnées serveur).
 *
 * CE QUE L'ARC N'EST PAS. Ni un compteur automobile, ni un score opaque : le
 * chiffre est SERVI et écrit au centre, les graduations sont EXACTEMENT les
 * bornes et les seuils servis (aucune graduation décorative inventée), et le
 * repère de position est STATIQUE — aucune aiguille animée, aucune pulsation.
 *
 * REFUS. Position absente ou statut `INVALID` : « non calculable » + la raison
 * servie, aucun arc de remplissage, aucun repère. Le rail subsiste : il dit la
 * forme, jamais la valeur.
 */
const RADIUS = 70;
const CENTER_X = 80;
const CENTER_Y = 80;
const LEFT_X = CENTER_X - RADIUS;
const RIGHT_X = CENTER_X + RADIUS;

/** Longueur du demi-cercle : la seule constante de géométrie de la forme. */
export const ARC_LENGTH = Math.PI * RADIUS;

/**
 * Cadre de dessin DÉRIVÉ des constantes ci-dessus — jamais écrit à la main.
 * Un `viewBox` littéral (« 0 0 160 96 ») a la forme d'un séparateur de
 * milliers et serait signalé, à juste titre, par `no-fabricated-values` : la
 * porte ne distingue pas une géométrie SVG d'une valeur. La dériver ferme le
 * doute au lieu de l'exempter.
 */
const VIEW_WIDTH = CENTER_X * 2;
const VIEW_HEIGHT = CENTER_Y + 16;

const ARC_PATH = `M${LEFT_X},${CENTER_Y} A${RADIUS},${RADIUS} 0 0 1 ${RIGHT_X},${CENTER_Y}`;

export const ARC_TONES = ['silver', 'macro', 'option', 'warning', 'positive', 'negative'] as const;
export type ArcTone = (typeof ARC_TONES)[number];

export interface ArcThreshold {
  /** Position SERVIE en pourcentage. */
  readonly pct: string;
  readonly label: string;
}

export interface ArcGaugeProps {
  readonly label: string;
  /** POSITION SERVIE en pourcentage (coordonnée serveur). `null` = refus. */
  readonly valuePct: string | null;
  /** Texte SERVI de la valeur. `null` = refus. */
  readonly valueText: string | null;
  readonly unit: string;
  readonly boundsText: { readonly min: string; readonly max: string };
  readonly thresholds: readonly ArcThreshold[];
  readonly tone?: ArcTone;
  /** Statut SERVI ; `INVALID` refuse la forme même si une position existe. */
  readonly status?: string;
  readonly reason?: string;
  readonly method?: string;
}

/** Point du demi-cercle à une part (0–1) de l'arc. GÉOMÉTRIE seule. */
function pointAt(share: number, radius: number): readonly [number, number] {
  const angle = Math.PI * (1 - share);
  return [CENTER_X + radius * Math.cos(angle), CENTER_Y - radius * Math.sin(angle)];
}

export function ArcGauge({
  label,
  valuePct,
  valueText,
  unit,
  boundsText,
  thresholds,
  tone = 'silver',
  status,
  reason,
  method,
}: ArcGaugeProps) {
  const position = status === 'INVALID' ? null : geometryValue(valuePct);
  const refused = position === null || valueText === null;

  // Graduations = bornes servies + seuils servis. Rien d'autre.
  const ticks: ReadonlyArray<{ readonly key: string; readonly share: number }> = [
    { key: 'min', share: 0 },
    { key: 'max', share: 1 },
    ...thresholds.flatMap((threshold) => {
      const value = geometryValue(threshold.pct);
      return value === null ? [] : [{ key: threshold.label, share: value / 100 }];
    }),
  ];

  const filled = position === null ? 0 : (ARC_LENGTH * position) / 100;

  return (
    <div className="vx-w2-arc" data-tone={tone} data-state={refused ? 'invalid' : 'served'}>
      <span className="vx-w2-arc-label">{label}</span>
      <svg
        className="vx-w2-arc-svg"
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        role={refused ? 'img' : 'meter'}
        aria-label={refused ? `${label} — non calculable` : undefined}
        {...(refused
          ? {}
          : {
              'aria-valuemin': 0,
              'aria-valuemax': 100,
              'aria-valuenow': position,
              'aria-valuetext': `${valueText} ${unit}`.trim(),
            })}
      >
        <path className="vx-w2-arc-rail" d={ARC_PATH} />
        {refused ? null : (
          <path
            className="vx-w2-arc-fill"
            d={ARC_PATH}
            strokeDasharray={`${filled} ${ARC_LENGTH - filled}`}
          />
        )}
        {ticks.map((tick) => {
          const [x1, y1] = pointAt(tick.share, RADIUS - 8);
          const [x2, y2] = pointAt(tick.share, RADIUS + 4);
          return (
            <line className="vx-w2-arc-tick" key={tick.key} x1={x1} y1={y1} x2={x2} y2={y2} />
          );
        })}
        {refused ? null : (
          <line
            className="vx-w2-arc-needle"
            x1={CENTER_X}
            y1={CENTER_Y}
            x2={pointAt(position / 100, RADIUS - 12)[0]}
            y2={pointAt(position / 100, RADIUS - 12)[1]}
          />
        )}
      </svg>
      {refused ? (
        <p className="vx-w2-absent" role="status">
          Valeur non calculable. Aucun arc de remplissage.
          {reason === undefined ? null : (
            <>
              {' '}
              Raison serveur : <code>{reason}</code>.
            </>
          )}
        </p>
      ) : (
        <p
          className="vx-w2-arc-figure"
          // Même défaut que le chiffre central de l'anneau, même remède : un
          // RSI servi fait quatorze caractères (`57.584431426615`) et
          // débordait de l'arc. Ni arrondi, ni tronqué — un cran de moins.
          data-density={textDensityOf(valueText ?? '')}
          data-testid="arc-figure"
        >
          {valueText}
          <span className="vx-w2-arc-unit"> {unit}</span>
        </p>
      )}
      <p className="vx-w2-gauge-bounds">
        <span>{boundsText.min}</span>
        <span>{boundsText.max}</span>
      </p>
      {thresholds.length === 0 ? null : (
        <p className="vx-w2-absent">
          {thresholds.map((threshold) => `${threshold.label} : ${threshold.pct}`).join(' · ')}
        </p>
      )}
      {method === undefined ? null : (
        <p className="vx-w2-absent">
          méthode <code>{method}</code>
        </p>
      )}
    </div>
  );
}
