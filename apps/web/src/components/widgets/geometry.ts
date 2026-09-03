/**
 * GÉOMÉTRIE SEULE — la seule arithmétique autorisée dans le socle.
 *
 * `apps/web/src/design/no-authoritative-calculation.test.ts` refuse toute
 * opération arithmétique dont une opérande lit une propriété du vocabulaire
 * financier (`close`, `weight`, `drawdown`, `pnl`, `volume`, `score`…). Les
 * primitives du socle reçoivent donc des propriétés à noms NEUTRES — `value`,
 * `pct`, `parts`, `points` — et ne produisent que des longueurs, des positions
 * et des angles. Aucun nombre dérivé n'est jamais ÉCRIT à l'écran.
 *
 * LE PIÈGE QUE CE MODULE FERME. `geometryNumber` (`marketsView.ts`) rend `0`
 * sur une chaîne non finie : une absence deviendrait une barre de hauteur
 * zéro, c'est-à-dire un fait faux (`.claude/rules/frontend.md` : absence ≠ 0).
 * `geometryValue` rend `null` ; l'appelant DOIT alors ne rien dessiner et dire
 * l'absence.
 */

/** Valeur numérique d'une chaîne servie pour la géométrie, ou `null`. */
export function geometryValue(raw: string | null | undefined): number | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  const trimmed = raw.trim();
  if (trimmed === '') {
    return null;
  }
  const parsed = Number.parseFloat(trimmed.replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Largeur CSS d'une part : la chaîne SERVIE, telle quelle, suivie de `%`.
 * Rien n'est arrondi, rien n'est normalisé — un reliquat reste un reliquat.
 */
export function servedWidth(pct: string): string {
  return `${pct.trim().replace(',', '.')}%`;
}

/**
 * Largeur CSS d'une part servie en RATIO (0–1) et non en pourcentage.
 *
 * Le contrat de concentration publie des ratios rendus
 * (`0.4295692665890570437233410943`) : posés tels quels comme largeur, ils
 * dessineraient une bande cent fois trop fine. La multiplication vit ICI, dans
 * le module de géométrie, sur une opérande au nom NEUTRE — elle produit une
 * longueur, jamais un nombre affiché. La chaîne servie reste seule à l'écran.
 */
export function ratioWidth(ratio: string): string | null {
  const parsed = geometryValue(ratio);
  if (parsed === null || parsed < 0) {
    return null;
  }
  return `${String(Math.min(100, parsed * 100))}%`;
}

/** Part (0–1) d'une valeur de géométrie sur un maximum de géométrie. */
export function geometryShare(value: number, max: number): number {
  if (max <= 0) {
    return 0;
  }
  return value / max;
}

/** Arrondi de RENDU (deux décimales) — appliqué à des coordonnées, jamais à une valeur. */
export function round2(value: number): number {
  return Number(value.toFixed(2));
}
