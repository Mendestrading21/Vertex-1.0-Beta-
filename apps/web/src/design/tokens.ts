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
  // LOT V1 — relevé de `#948c7d`, qui donnait 4,35:1 sur `hover` : SOUS le
  // seuil AA, et précisément là où il compte. Ce jeton porte les métadonnées À
  // L'INTÉRIEUR des cartes, donc sur leur état de survol. +3 par canal suffit
  // (4,52:1), garde la teinte, et laisse 1,49 d'écart avec `text-secondary` :
  // les deux rôles restent distincts. Mesuré par `contrast.test.ts`.
  'text-muted': '#978f80',
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
  // Deux crans de tension SUPPLÉMENTAIRES, pour les échelles à bandes servies
  // (matrice de corrélation) : `-soft` et `-faint` ne se distinguaient pas à
  // l'œil sur une cellule de tableau (mesuré sur capture, planche §9), et une
  // bande invisible ne porte plus l'information qu'elle nomme.
  'signal-strong': 'rgba(215, 169, 74, 0.3)',
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
  'macro-strong': 'rgba(107, 197, 188, 0.28)',
  // Dégradés de série (ADR-017) : de la teinte sémantique vers SA transparence,
  // UNIQUEMENT sous une série servie (`SparkFigure`, `MultiSeriesArea`), jamais
  // un fond de carte. `-gradient-end` est le même triplet à alpha 0 : le fondu
  // reste dans la famille, il ne va ni vers le noir ni vers une autre teinte.
  // L'ambre (`signal`) n'a pas de dégradé : il n'est jamais la teinte d'une série.
  'silver-gradient-start': 'rgba(216, 211, 199, 0.22)',
  'silver-gradient-end': 'rgba(216, 211, 199, 0)',
  'positive-gradient-start': 'rgba(80, 201, 146, 0.22)',
  'positive-gradient-end': 'rgba(80, 201, 146, 0)',
  'negative-gradient-start': 'rgba(239, 111, 108, 0.22)',
  'negative-gradient-end': 'rgba(239, 111, 108, 0)',
  'warning-gradient-start': 'rgba(240, 195, 106, 0.22)',
  'warning-gradient-end': 'rgba(240, 195, 106, 0)',
  'option-gradient-start': 'rgba(168, 138, 232, 0.22)',
  'option-gradient-end': 'rgba(168, 138, 232, 0)',
  'macro-gradient-start': 'rgba(107, 197, 188, 0.22)',
  'macro-gradient-end': 'rgba(107, 197, 188, 0)',
  'overlay': 'rgba(3, 3, 2, 0.86)',
  'scrim': 'rgba(3, 3, 2, 0.56)',
} as const satisfies Record<string, string>;

/**
 * Teinte sémantique SECONDAIRE par page (ADR-017). Une page déclare UNE famille
 * dans son catalogue ; l'ambre (`signal`) reste la seule lumière de la
 * dominante et n'est pas éligible. Chaque clé renvoie à une famille EXISTANTE —
 * aucune couleur nouvelle : « une couleur = une signification » est préservé,
 * la teinte garde le sens de sa famille (macro = contexte, option = domaine
 * options, warning = prudence, retard, synthétique). `positive` et `negative`
 * restent réservés au signe financier servi : une teinte de page ne bascule
 * pas selon le signe, elle n'est donc jamais verte ni rouge (revue du lot C0).
 * Le CSS généré expose `[data-page-accent="<clé>"]` → `--vx-page-accent`,
 * `--vx-page-accent-soft`, `--vx-page-accent-gradient-start/-end`. Aucune
 * valeur par défaut : sans déclaration de page, il n'y a pas de teinte.
 */
export const pageAccent = {
  macro: 'macro',
  option: 'option',
  warning: 'warning',
} as const satisfies Record<string, ColorToken>;

/** Espacements — grille 4 px. Clé (valeur px) → `--vx-space-<clé>`. */
export const space = {
  4: '4px',
  8: '8px',
  12: '12px',
  16: '16px',
  20: '20px',
  24: '24px',
  32: '32px',
  // LOT V1 — `40` et `48` sont retirés : zéro lecture dans tout le produit,
  // et `tokens-css.test.ts` les EXIGEAIT, figeant deux jetons que personne
  // n'employait. Un cran s'ajoute le jour où il sert, pas avant.
} as const satisfies Record<number, string>;

/**
 * Rayons. `pill` est réservé aux badges (docs/05-design/TOKENS.md).
 *
 * LOT V1 — `18` valait `'16px'` et `22` valait `'20px'` : la clé mentait, et
 * l'assertion qui exigeait ces clés protégeait le mensonge. Deux documents
 * normatifs se contredisaient déjà — « 18 px pour les grandes surfaces »
 * contre « grande surface : rayon 16 px » — et le jeton donnait raison au
 * second en portant le nom du premier. Les clés valent maintenant leurs
 * valeurs ; les quatre consommateurs CSS ont suivi. AUCUN pixel ne change.
 */
export const radius = {
  6: '6px',
  10: '10px',
  14: '14px',
  16: '16px',
  20: '20px',
  pill: '999px',
} as const satisfies Record<string | number, string>;

/**
 * Ombres sobres : profondeur, jamais halo lumineux.
 *
 * `glass` est la profondeur de la CARTE ORDINAIRE (LOT T1) : plus courte et
 * plus proche que `panel`, qui reste la profondeur d'une planche entière.
 * Avec `inset` — le liseré clair d'un pixel en haut — elle donne au verre
 * noir son épaisseur sans aucun halo : une ombre portée et une arête, jamais
 * une lumière.
 */
export const shadow = {
  // LOT V1 — `floating` retiré : zéro lecture. Aucune surface flottante du
  // produit ne l'employait, et il était pourtant figé par une assertion.
  panel: '0 20px 52px rgba(0, 0, 0, 0.28)',
  glass: '0 10px 28px rgba(0, 0, 0, 0.34)',
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
  // ADR-017 : surbrillance UNIQUE d'une valeur dont `snapshot_version` a changé
  // (`docs/05-design/MOTION_AND_MICROINTERACTIONS.md`, « Valeur mise à jour »,
  // nom documentaire `--vx-motion-data`). Jamais une transition d'interface.
  600: '600ms',
} as const satisfies Record<number, string>;

/**
 * Courbes documentées (docs/05-design/MOTION_AND_MICROINTERACTIONS.md).
 *
 * LOT V1 — `decelerate` retiré : zéro lecture. La courbe reste documentée ;
 * elle reviendra dans le lot qui l'emploie réellement.
 */
export const motionEase = {
  standard: 'cubic-bezier(0.2, 0, 0, 1)',
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
export type PageAccentToken = keyof typeof pageAccent;
export type ZIndexToken = keyof typeof zIndex;
