/**
 * Tokens Black Glass — Obsidian Signal. SOURCE TYPÉE UNIQUE.
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
  'black': '#020304',
  'app': '#06080d',
  'surface-0': '#090c12',
  'surface-1': '#0e1219',
  'surface-2': '#141923',
  'surface-3': '#1a202b',
  'hover': '#202835',
  'border-soft': 'rgba(232, 239, 249, 0.07)',
  'border': 'rgba(232, 239, 249, 0.11)',
  'border-strong': 'rgba(232, 239, 249, 0.18)',
  'text': '#f5f7fb',
  'text-secondary': '#a8b0bf',
  'text-muted': '#747e8e',
  'silver': '#d4dae3',
  'signal': '#d4ff45',
  'signal-soft': 'rgba(212, 255, 69, 0.13)',
  'signal-faint': 'rgba(212, 255, 69, 0.055)',
  'positive': '#2bd99b',
  'positive-soft': 'rgba(43, 217, 155, 0.12)',
  'negative': '#ff6070',
  'negative-soft': 'rgba(255, 96, 112, 0.12)',
  'warning': '#f2b94b',
  'warning-soft': 'rgba(242, 185, 75, 0.12)',
  'option': '#a87cf7',
  'option-soft': 'rgba(168, 124, 247, 0.12)',
  'macro': '#5bd2c2',
  'macro-soft': 'rgba(91, 210, 194, 0.12)',
  'overlay': 'rgba(2, 3, 4, 0.82)',
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
  18: '18px',
  22: '22px',
  pill: '999px',
} as const satisfies Record<string | number, string>;

/** Ombres sobres : profondeur, jamais halo lumineux. */
export const shadow = {
  panel: '0 18px 48px rgba(0, 0, 0, 0.2)',
  floating: '0 28px 72px rgba(0, 0, 0, 0.38)',
  inset: 'inset 0 1px 0 rgba(255, 255, 255, 0.035)',
} as const satisfies Record<string, string>;

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
  headline: '28px',
  metric: '34px',
} as const satisfies Record<string, string>;

export type ColorToken = keyof typeof color;
export type SpaceToken = keyof typeof space;
export type RadiusToken = keyof typeof radius;
export type ShadowToken = keyof typeof shadow;
export type MotionDurationToken = keyof typeof motionDuration;
export type ZIndexToken = keyof typeof zIndex;
