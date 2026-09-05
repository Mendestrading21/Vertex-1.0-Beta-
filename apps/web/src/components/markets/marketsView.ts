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
import { geometryValue } from '../widgets/geometry.ts';

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
/**
 * Valeur numérique d'une chaîne servie, POUR LA GÉOMÉTRIE SEULE — ou `null`.
 *
 * ELLE RENDAIT `0`. Une chaîne illisible devenait donc un point tracé à zéro :
 * une bougie qui plonge sur l'axe, une étincelle qui touche le fond, un P&L
 * posé sur la ligne des zéros. Une absence peinte comme une valeur est un FAIT
 * FAUX, et `.claude/rules/frontend.md` l'interdit nommément — « ne jamais
 * remplacer une donnée absente par 0 ». Le module de géométrie du socle avait
 * déjà nommé ce piège et écrit le remède ; les copies ne l'avaient jamais
 * adopté.
 *
 * L'appelant DOIT désormais traiter `null` : ne rien dessiner, écarter le
 * point, ou refuser la figure — jamais lui substituer une valeur.
 */
export function geometryNumber(value: string | null | undefined): number | null {
  return geometryValue(value);
}

/** Glyphe de sens, TOUJOURS accompagné du texte signé — jamais la couleur seule. */
export function signSymbolOf(group: SignGroup): string {
  return group === 'up' ? '▲' : group === 'down' ? '▼' : '=';
}

export const GROUP_LABELS_FR: Readonly<Record<SignGroup, string>> = {
  up: 'En hausse',
  down: 'En baisse',
  flat: 'Stables',
};

/**
 * Recensement de la nature DÉCLARÉE des instruments servis.
 *
 * POURQUOI CE RECENSEMENT EXISTE. `docs/08-runbooks/REPRENDRE_ICI.md` §4.1 :
 * la page Marchés écrivait « Carte des marchés synthétiques », source
 * `synthetic-dev`, « poids … (synthétiques) » et « données SYNTHÉTIQUES de
 * développement » — le tout EN DUR, au-dessus de 161 instruments IBKR réels.
 *
 * La correction n'est pas de remplacer « synthétique » par « réel » : ce
 * serait déplacer le mensonge. Sur une machine de développement la donnée EST
 * synthétique. Le texte doit DÉCOULER de ce que le serveur déclare.
 *
 * Deux champs le déclarent, et ils sont distincts :
 *   - `population`, la nature de l'INSTANTANÉ, propriété du bandeau
 *     (`SyntheticBanner`), seul propriétaire de ce vocabulaire ;
 *   - `synthetic`, un drapeau PAR INSTRUMENT, que seule cette page peut
 *     recenser.
 *
 * Compter des drapeaux booléens n'est pas un calcul financier : aucun prix,
 * rendement, score ni classement n'en sort. C'est un dénombrement de ce qui a
 * été servi.
 */
export interface NatureCensus {
  readonly total: number;
  readonly synthetic: number;
  /** `true` seulement si TOUS les instruments servis se déclarent synthétiques. */
  readonly allSynthetic: boolean;
  /** `true` seulement si AUCUN ne se déclare synthétique. */
  readonly noneSynthetic: boolean;
}

export function censusOfNature(sectors: readonly MarketsSector[]): NatureCensus {
  const entries = flattenTickers(sectors);
  const synthetic = entries.filter((entry) => entry.ticker.synthetic).length;
  return {
    total: entries.length,
    synthetic,
    // Un univers VIDE n'est ni « tout synthétique » ni « rien de synthétique » :
    // il n'a rien déclaré. Les deux drapeaux sont donc faux, et la phrase
    // affichée le dit au lieu de choisir.
    allSynthetic: entries.length > 0 && synthetic === entries.length,
    noneSynthetic: entries.length > 0 && synthetic === 0,
  };
}

/** Phrase de provenance, DÉRIVÉE du recensement — jamais écrite en dur. */
export function provenanceSentence(census: NatureCensus): string {
  if (census.total === 0) {
    return 'Aucun instrument servi : la nature des données n’est pas déclarée.';
  }
  if (census.allSynthetic) {
    return `${census.total} instruments servis, tous déclarés synthétiques par le worker.`;
  }
  if (census.noneSynthetic) {
    return `${census.total} instruments servis, aucun déclaré synthétique.`;
  }
  // Le cas MIXTE ne se fond pas dans l'un des deux : il se nomme.
  return `${census.total} instruments servis, dont ${census.synthetic} déclarés synthétiques — deux natures, jamais confondues.`;
}
