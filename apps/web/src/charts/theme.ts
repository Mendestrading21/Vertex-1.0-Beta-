/**
 * Thème de graphique Titanium Ledger — UNE source pour les quatre moteurs.
 *
 * POURQUOI CE FICHIER EXISTE, et c'est la même histoire que la primitive de
 * carte. Quatre composants — `PayoffChart`, `PerformanceChart`,
 * `MonthlyHeatmap`, `MarketMap` — déclaraient CHACUN leur propre style d'axe,
 * de grille et d'infobulle, avec des jetons différents :
 *
 *     axisLine:  --vx-border-strong  |  --vx-border   |  (absent)
 *     axisLabel: --vx-text-secondary |  --vx-text-muted
 *     fontSize:  (défaut ECharts)    |  11
 *     splitLine: --vx-border         |  (absent)
 *
 * Quatre graphiques, quatre grammaires. Rien ne les tenait ensemble, et
 * chaque nouveau graphique en aurait inventé une cinquième.
 *
 * CE QUE LE THÈME IMPOSE, et pourquoi.
 *
 * - GRILLE À `--vx-grid-line` (0,045) et non `--vx-border` (0,12). Le contrat
 *   canonique veut un décor « sous le niveau de contraste du texte » : à 0,12,
 *   la grille se lisait aussi bien que la courbe qu'elle sert.
 * - ÉTIQUETTES EN MONO. « Mono/tabular pour prix, dates, unités et codes » :
 *   une graduation d'axe EST un prix ou une date, et en proportionnelle ses
 *   chiffres ne s'alignent pas d'un cran à l'autre.
 * - AUCUNE ANIMATION. « Aucun ticker animé faisant croire à une donnée live » —
 *   la règle vaut pour tout ce qui bouge sans que la donnée ait changé.
 *
 * CE QU'IL NE DÉCIDE PAS. Aucune couleur de SÉRIE : vert, rouge, violet et
 * cyan portent un sens financier ou de domaine, et ce sens appartient à la
 * page, jamais au thème.
 */

/** Lit un jeton CSS résolu. Le thème ne connaît aucune valeur littérale. */
export type TokenReader = (name: string) => string;

export interface ChartBaseOptions {
  /** Marges de la zone traçable. Chaque graphique a ses propres étiquettes. */
  readonly grid?: { left?: number; right?: number; top?: number; bottom?: number };
}

/**
 * Le socle commun : animation, accessibilité, infobulle et typographie.
 * À étaler dans l'option ECharts AVANT les axes et les séries.
 */
export function chartBase(token: TokenReader, options: ChartBaseOptions = {}) {
  return {
    animation: false,
    aria: { enabled: true },
    textStyle: {
      fontFamily: token('--vx-font-mono'),
      fontSize: 11,
      color: token('--vx-text-muted'),
    },
    grid: {
      left: options.grid?.left ?? 64,
      right: options.grid?.right ?? 20,
      top: options.grid?.top ?? 20,
      bottom: options.grid?.bottom ?? 32,
      containLabel: false,
    },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: token('--vx-surface-2'),
      borderColor: token('--vx-border'),
      borderWidth: 1,
      padding: [6, 10] as [number, number],
      textStyle: {
        color: token('--vx-text'),
        fontFamily: token('--vx-font-mono'),
        fontSize: 11,
      },
    },
  };
}

/**
 * Un axe. `name` reste à la charge de la page : c'est une unité, et une unité
 * non déclarée est une valeur non qualifiée.
 */
export function chartAxis(token: TokenReader) {
  return {
    axisLine: { lineStyle: { color: token('--vx-border-soft') } },
    axisTick: { show: false },
    axisLabel: {
      color: token('--vx-text-muted'),
      fontFamily: token('--vx-font-mono'),
      fontSize: 11,
    },
    nameTextStyle: {
      color: token('--vx-text-muted'),
      fontFamily: token('--vx-font-mono'),
      fontSize: 11,
    },
    splitLine: { lineStyle: { color: token('--vx-grid-line'), width: 1 } },
  };
}
