/**
 * Aides de PRÉSENTATION de la page Marchés — aucun calcul financier.
 *
 * Tout chiffre affiché provient du snapshot serveur (chaînes décimales déjà
 * calculées et formatées par le worker). Ici on ne fait que : aplatir les
 * secteurs, classer un rendement déjà calculé par son signe textuel, adapter
 * un point décimal en virgule française et parser une chaîne serveur en
 * nombre pour la GÉOMÉTRIE du rendu (taille de tuile, tri local) — jamais
 * pour produire une nouvelle valeur financière.
 */
import type { MarketsSector, MarketsTicker } from '../../api/client.ts';

/** Groupe de signe d'un ticker, dérivé du PREMIER caractère de la chaîne
 * serveur `return_1d_pct` (« + », « - » ou autre) — pas d'arithmétique. */
export type SignGroup = 'up' | 'down' | 'flat';

export function signGroupOf(ticker: MarketsTicker): SignGroup {
  const pct = ticker.return_1d_pct;
  if (pct.startsWith('+')) {
    return pct === '+0.00' ? 'flat' : 'up';
  }
  if (pct.startsWith('-')) {
    return pct === '-0.00' ? 'flat' : 'down';
  }
  return 'flat';
}

export interface FlatTicker {
  readonly ticker: MarketsTicker;
  readonly sectorLabel: string;
  readonly group: SignGroup;
}

export function flattenTickers(sectors: readonly MarketsSector[]): FlatTicker[] {
  return sectors.flatMap((sector) =>
    sector.tickers.map((ticker) => ({
      ticker,
      sectorLabel: sector.label,
      group: signGroupOf(ticker),
    })),
  );
}

/** Affichage français d'une chaîne décimale serveur (point → virgule). */
export function frDecimal(value: string): string {
  return value.replace('.', ',');
}

/** Valeur numérique d'une chaîne serveur pour la géométrie/tri UNIQUEMENT. */
export function geometryNumber(value: string): number {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export const GROUP_LABELS_FR: Readonly<Record<SignGroup, string>> = {
  up: 'En hausse',
  down: 'En baisse',
  flat: 'Stables',
};
