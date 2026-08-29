/**
 * Tokens Black Glass — Signal Light. SOURCE TYPÉE UNIQUE.
 *
 * Références : docs/05-design/DESIGN_SYSTEM.md et docs/05-design/TOKENS.md.
 *
 * Règles :
 * - AUCUNE couleur hex/rgb/hsl ailleurs que dans ce fichier (et dans le
 *   `tokens.css` généré) ; le test `src/design/no-raw-colors.test.ts` échoue
 *   si une couleur brute apparaît hors `tokens.*`.
 * - `src/design/tokens.css` est GÉNÉRÉ depuis ce fichier via `pnpm tokens:css`
 *   (script `src/design/generate-css.ts`) et commité ; le test
 *   `src/design/tokens-css.test.ts` échoue si le fichier généré diverge.
 */

/** Couleurs canoniques. Clé → variable CSS `--vx-<clé>`. */
export const color = {
  'black': '#040504',
  'app': '#08090b',
  'surface-0': '#0b0c0f',
  'surface-1': '#101216',
  'surface-2': '#15171c',
  'surface-3': '#1b1e23',
  'hover': '#232830',
  'border-soft': 'rgba(222, 227, 237, 0.09)',
  'border': 'rgba(222, 227, 237, 0.14)',
  'border-strong': 'rgba(222, 227, 237, 0.22)',
  'text': '#f3f5f8',
  'text-secondary': '#b7bcc4',
  'text-muted': '#828892',
  'silver': '#c9cdd4',
  'positive': '#36c889',
  'negative': '#ed655c',
  'warning': '#dda23b',
  'option': '#9c79d0',
  'macro': '#53b9ad',
} as const satisfies Record<string, string>;

/** Espacements — grille 4 px. Clé (valeur px) → `--vx-space-<clé>`. */
export const space = {
  4: '4px',
  8: '8px',
  12: '12px',
  16: '16px',
  20: '20px',
  24: '24px',
  32: '32px',
  40: '40px',
  48: '48px',
} as const satisfies Record<number, string>;

/** Rayons. `pill` est réservé aux badges (docs/05-design/TOKENS.md). */
export const radius = {
  6: '6px',
  10: '10px',
  14: '14px',
  pill: '999px',
} as const satisfies Record<string | number, string>;

/**
 * Durées de mouvement. Clé (ms) → `--vx-motion-<clé>`.
 * Sous `prefers-reduced-motion: reduce`, le CSS généré ramène toutes ces
 * durées à 0 ms.
 */
export const motionDuration = {
  90: '90ms',
  140: '140ms',
  180: '180ms',
  220: '220ms',
} as const satisfies Record<number, string>;

/** Courbes documentées (docs/05-design/MOTION_AND_MICROINTERACTIONS.md). */
export const motionEase = {
  standard: 'cubic-bezier(0.2, 0, 0, 1)',
  decelerate: 'cubic-bezier(0, 0, 0.2, 1)',
} as const satisfies Record<string, string>;

/** Plans z nommés — aucune valeur locale arbitraire. */
export const zIndex = {
  base: '0',
  sticky: '100',
  popover: '200',
  sheet: '300',
  dialog: '400',
  toast: '500',
} as const satisfies Record<string, string>;

/**
 * Familles typographiques. Geist / Geist Mono (OFL-1.1) sont auto-hébergées
 * depuis le paquet npm `geist` (voir src/styles/fonts.css) ; les piles de
 * secours système couvrent l'échec de chargement.
 */
export const fontFamily = {
  sans: "'Geist', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  mono: "'Geist Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace",
} as const satisfies Record<string, string>;

/**
 * Corps de texte : 14 px par défaut, 13 px uniquement pour métadonnées
 * conformes AA (docs/05-design/DESIGN_SYSTEM.md).
 */
export const fontSize = {
  meta: '13px',
  body: '14px',
  label: '13px',
  title: '16px',
  display: '22px',
} as const satisfies Record<string, string>;

export type ColorToken = keyof typeof color;
export type SpaceToken = keyof typeof space;
export type RadiusToken = keyof typeof radius;
export type MotionDurationToken = keyof typeof motionDuration;
export type ZIndexToken = keyof typeof zIndex;
