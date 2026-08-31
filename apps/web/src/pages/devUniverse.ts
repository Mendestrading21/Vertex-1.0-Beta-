/**
 * Instruments RÉELLEMENT publiés, lus depuis la page Marchés.
 *
 * POURQUOI CE MODULE A CHANGÉ. Il exportait une liste FIGÉE de quatre tickers
 * synthétiques (`SYN-ENER-01`…), miroir manuel de `SYNTHETIC_FOCUS_TICKERS`.
 * Sur une installation réelle, les trois pages qui s'en servaient proposaient
 * donc quatre instruments qui n'existent pas, et aucun de ceux qui existent —
 * mesuré le 2026-08-31 avec 153 titres IBKR en base.
 *
 * CE N'EST TOUJOURS PAS UNE DONNÉE DE MARCHÉ : juste la liste des instruments
 * pour lesquels une cotation a été publiée, donc les seuls dont une page peut
 * dire quelque chose. Tout autre identifiant saisi dans l'URL reçoit l'état
 * vide honnête de l'API, exactement comme avant.
 *
 * La source est la vue Marchés parce que c'est la seule qui publie l'univers
 * COUVERT. S'en remettre à une constante locale, c'était affirmer sans lire.
 */

import { useMarketsOverview } from '../api/hooks.ts';

/**
 * Tickers publiés, triés, dédoublonnés. Liste vide tant que Marchés n'a rien
 * couvert — l'absence reste une absence, jamais un instrument inventé.
 */
export function useDeclaredInstruments(): readonly string[] {
  const query = useMarketsOverview();
  const secteurs = query.data?.sectors ?? [];
  const tickers = new Set<string>();
  for (const secteur of secteurs) {
    for (const ligne of secteur.tickers) {
      tickers.add(ligne.ticker);
    }
  }
  return [...tickers].sort((a, b) => a.localeCompare(b));
}
