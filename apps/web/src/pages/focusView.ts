/**
 * Instruments SUIVIS — ceux pour lesquels un dossier d'analyse est publié.
 *
 * D'où vient la liste. Le snapshot Opportunités énumère ses candidats à partir
 * des dossiers d'analyse publiés, et relaie pour chacun `bars_status`. Un
 * candidat dont les barres sont `OK` est donc un instrument dont une série de
 * clôtures EXISTE côté serveur. Aucune liste locale, aucun instrument deviné :
 * sur une installation sans dossier, la rangée est vide et le dit.
 *
 * Borne. Les widgets sont limités aux PREMIERS candidats de l'ordre publié
 * (méthode d'ordre servie par le worker, jamais retriée ici), pour ne jamais
 * ouvrir un nombre de requêtes qui dépendrait de la taille de l'univers.
 */
import type { MarketsSector } from '../api/client.ts';
import type { FlatTicker } from '../components/markets/marketsView.ts';
import { flattenTickers } from '../components/markets/marketsView.ts';
import type { OpportunitiesContentView } from './opportunities/opportunitiesView.ts';

export const FOCUS_LIMIT = 4;

export function focusInstrumentsOf(
  view: OpportunitiesContentView | null,
  sectors: readonly MarketsSector[],
  limit: number = FOCUS_LIMIT,
): readonly FlatTicker[] {
  if (view === null) {
    return [];
  }
  const byTicker = new Map(flattenTickers(sectors).map((entry) => [entry.ticker.ticker, entry]));
  const seen = new Set<string>();
  const result: FlatTicker[] = [];
  const candidates = [
    ...view.candidates.qualified,
    ...view.candidates.excluded,
    ...view.candidates.contradictory,
  ];
  for (const candidate of candidates) {
    if (result.length >= limit) {
      break;
    }
    if (candidate.barsStatus !== 'OK' || seen.has(candidate.ticker)) {
      continue;
    }
    const entry = byTicker.get(candidate.ticker);
    if (entry === undefined) {
      // Un dossier sans cotation dans le snapshot Marchés n'a ni clôture ni
      // rendement 1 j à afficher : il n'entre pas dans la rangée.
      continue;
    }
    seen.add(candidate.ticker);
    result.push(entry);
  }
  return result;
}
