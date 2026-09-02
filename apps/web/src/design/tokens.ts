/**
 * Tokens Black Glass — Titanium Ledger. SOURCE TYPÉE UNIQUE.
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
  'black': '#030302',
  'app': '#080806',
  'surface-0': '#0d0d0b',
  'surface-1': '#141310',
  'surface-2': '#1b1915',
  'surface-3': '#242119',
  'hover': '#2d2920',
  'border-soft': 'rgba(231, 224, 207, 0.07)',
  'border': 'rgba(231, 224, 207, 0.12)',
  'border-strong': 'rgba(231, 224, 207, 0.21)',
  'grid-line': 'rgba(231, 224, 207, 0.045)',
  'text': '#f6f2e8',
  'text-secondary': '#b8b0a0',
  'text-muted': '#948c7d',
  'silver': '#d8d3c7',
  'titanium': '#aaa497',
  'titanium-soft': 'rgba(216, 211, 199, 0.1)',
  // Filigrane de registre : DÉLIBÉRÉMENT sous le niveau de contraste du texte.
  // « Arrière-plan : décor presque invisible » (`canonical-visual.md`). À
  // `titanium-soft`, le code d'espace se lisait aussi bien que le titre de la
  // page : un second titre qui ne dit rien.
  'titanium-ghost': 'rgba(216, 211, 199, 0.045)',
  'signal': '#d7a94a',
  'signal-bright': '#f2c76b',
  'signal-deep': '#765319',
  'signal-soft': 'rgba(215, 169, 74, 0.15)',
  'signal-faint': 'rgba(215, 169, 74, 0.065)',
  'positive': '#50c992',
  'positive-soft': 'rgba(80, 201, 146, 0.12)',
  'negative': '#ef6f6c',
  'negative-soft': 'rgba(239, 111, 108, 0.12)',
  'warning': '#f0c36a',
  'warning-soft': 'rgba(240, 195, 106, 0.12)',
  'option': '#a88ae8',
  'option-soft': 'rgba(168, 138, 232, 0.12)',
  'macro': '#6bc5bc',
  'macro-soft': 'rgba(107, 197, 188, 0.12)',
  'overlay': 'rgba(3, 3, 2, 0.86)',
  'scrim': 'rgba(3, 3, 2, 0.56)',
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
  18: '16px',
  22: '20px',
  pill: '999px',
} as const satisfies Record<string | number, string>;

/** Ombres sobres : profondeur, jamais halo lumineux. */
export const shadow = {
  panel: '0 20px 52px rgba(0, 0, 0, 0.28)',
  floating: '0 32px 80px rgba(0, 0, 0, 0.48)',
  inset: 'inset 0 1px 0 rgba(255, 255, 255, 0.045)',
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
