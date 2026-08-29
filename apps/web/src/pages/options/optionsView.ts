/**
 * Aides de PRÉSENTATION de la page Options — aucun calcul financier.
 *
 * Toute valeur affichée provient du snapshot serveur `option_chain/{u}`
 * (chaînes décimales verbatim, IV/Greeks calculés par le worker avec leur
 * `CalculationRecord`). Ici on ne fait que : lire défensivement les blocs
 * non typés (`quote`, `iv`, `greeks` — additionalProperties du contrat),
 * apparier CALL/PUT par strike D'UN MÊME groupe (jamais entre groupes),
 * trier par la valeur numérique du strike (géométrie du rendu uniquement)
 * et dériver l'état d'affichage depuis les statuts PUBLIÉS.
 */
import type {
  OptionChainContract,
  OptionChainExpiration,
  OptionChainResponse,
} from '../../api/client.ts';
import type { DataState } from '../../components/DataStateBoundary.tsx';

// ---------------------------------------------------------------------------
// Lecture défensive des blocs relayés verbatim (jamais un zéro fabriqué)
// ---------------------------------------------------------------------------

function blockString(block: Record<string, unknown>, key: string): string | null {
  const value = block[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function blockInt(block: Record<string, unknown>, key: string): number | null {
  const value = block[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** Quote verbatim + statut de qualité publié (`OK`/`CROSSED`/`STALE`/`MISSING`). */
export interface QuoteView {
  readonly bid: string | null;
  readonly ask: string | null;
  readonly bidSize: number | null;
  readonly askSize: number | null;
  readonly observedAt: string | null;
  readonly ageSeconds: number | null;
  readonly status: string | null;
}

export function quoteViewOf(contract: OptionChainContract): QuoteView {
  const quote = contract.quote;
  return {
    bid: blockString(quote, 'bid'),
    ask: blockString(quote, 'ask'),
    bidSize: blockInt(quote, 'bid_size'),
    askSize: blockInt(quote, 'ask_size'),
    observedAt: blockString(quote, 'observed_at'),
    ageSeconds: blockInt(quote, 'age_seconds'),
    status: blockString(quote, 'status'),
  };
}

/** Lignée `CalculationRecord` conservée par le worker (relayée verbatim). */
export interface CalculationMetaView {
  readonly calculationId: string | null;
  readonly engineVersion: string | null;
  readonly method: string | null;
  readonly inputHash: string | null;
  readonly resultHash: string | null;
  readonly status: string | null;
}

function calculationMetaOf(value: unknown): CalculationMetaView | null {
  if (typeof value !== 'object' || value === null) {
    return null;
  }
  const block = value as Record<string, unknown>;
  return {
    calculationId: blockString(block, 'calculation_id'),
    engineVersion: blockString(block, 'engine_version'),
    method: blockString(block, 'method'),
    inputHash: blockString(block, 'input_hash'),
    resultHash: blockString(block, 'result_hash'),
    status: blockString(block, 'status'),
  };
}

/**
 * IV Vertex : présente (`THEORETICAL`, avec lignée) OU absente avec sa
 * raison typée. L'absence n'est JAMAIS convertie en zéro.
 */
export interface IvView {
  readonly status: 'OK' | 'ABSENT' | 'UNREADABLE';
  readonly value: string | null;
  readonly quoteSide: string | null;
  readonly valueNature: string | null;
  readonly reason: string | null;
  readonly calculation: CalculationMetaView | null;
}

export function ivViewOf(contract: OptionChainContract): IvView {
  const iv = contract.iv;
  const status = blockString(iv, 'status');
  if (status === 'OK') {
    return {
      status: 'OK',
      value: blockString(iv, 'value'),
      quoteSide: blockString(iv, 'quote_side'),
      valueNature: blockString(iv, 'value_nature'),
      reason: null,
      calculation: calculationMetaOf(iv['calculation']),
    };
  }
  if (status === 'ABSENT') {
    return {
      status: 'ABSENT',
      value: null,
      quoteSide: null,
      valueNature: null,
      reason: blockString(iv, 'reason'),
      calculation: null,
    };
  }
  return {
    status: 'UNREADABLE',
    value: null,
    quoteSide: null,
    valueNature: null,
    reason: null,
    calculation: null,
  };
}

/** Une sensibilité nommée avec son unité d'affichage (contrat du worker). */
export interface GreekEntry {
  readonly key: string;
  readonly label: string;
  readonly unit: string;
  readonly value: string;
}

const GREEK_FIELDS: readonly { key: string; label: string; unit: string }[] = [
  { key: 'delta', label: 'Delta', unit: 'variation de prime par unité de spot' },
  { key: 'gamma', label: 'Gamma', unit: 'variation de delta par unité de spot' },
  { key: 'vega', label: 'Vega', unit: 'par point de volatilité (1.00 = 100 %)' },
  { key: 'vega_per_point', label: 'Vega / point', unit: 'par point de volatilité (%)' },
  { key: 'theta', label: 'Theta', unit: 'par année (ACT/365F)' },
  { key: 'theta_per_calendar_day', label: 'Theta / jour', unit: 'par jour calendaire' },
  { key: 'rho', label: 'Rho', unit: 'par unité de taux (1.00 = 100 %)' },
  { key: 'rho_per_bp', label: 'Rho / bp', unit: 'par point de base de taux' },
];

export interface GreeksView {
  readonly status: 'OK' | 'ABSENT' | 'UNREADABLE';
  readonly entries: readonly GreekEntry[];
  readonly valueNature: string | null;
  readonly reason: string | null;
  readonly calculation: CalculationMetaView | null;
}

export function greeksViewOf(contract: OptionChainContract): GreeksView {
  const greeks = contract.greeks;
  const status = blockString(greeks, 'status');
  if (status === 'OK') {
    const entries: GreekEntry[] = [];
    for (const field of GREEK_FIELDS) {
      const value = blockString(greeks, field.key);
      if (value !== null) {
        entries.push({ key: field.key, label: field.label, unit: field.unit, value });
      }
    }
    return {
      status: 'OK',
      entries,
      valueNature: blockString(greeks, 'value_nature'),
      reason: null,
      calculation: calculationMetaOf(greeks['calculation']),
    };
  }
  if (status === 'ABSENT') {
    return {
      status: 'ABSENT',
      entries: [],
      valueNature: null,
      reason: blockString(greeks, 'reason'),
      calculation: null,
    };
  }
  return { status: 'UNREADABLE', entries: [], valueNature: null, reason: null, calculation: null };
}

/** Delta seul (colonne de la table) — même lecture défensive. */
export function deltaOf(contract: OptionChainContract): string | null {
  return blockString(contract.greeks, 'delta');
}

// ---------------------------------------------------------------------------
// Groupes (expiration, trading_class) — JAMAIS fusionnés
// ---------------------------------------------------------------------------

/**
 * Identifiant stable d'un groupe : la PAIRE (expiration, trading_class).
 * Deux trading classes d'une même date restent deux entrées distinctes.
 */
export function groupKeyOf(group: OptionChainExpiration): string {
  return `${group.expiration}::${group.trading_class}`;
}

/** Libellé du sélecteur : date ET trading class toujours visibles ensemble. */
export function groupLabelOf(group: OptionChainExpiration): string {
  return `${group.expiration} · ${group.trading_class} (${group.exchange})`;
}

export interface GroupCoverageView {
  readonly expected: number | null;
  readonly quotesReceived: number | null;
  readonly quotesValid: number | null;
  readonly ivResolved: number | null;
  readonly discardedCount: number | null;
}

export function groupCoverageOf(group: OptionChainExpiration): GroupCoverageView {
  const coverage = group.coverage;
  const discarded = coverage['discarded'];
  return {
    expected: blockInt(coverage, 'expected'),
    quotesReceived: blockInt(coverage, 'quotes_received'),
    quotesValid: blockInt(coverage, 'quotes_valid'),
    ivResolved: blockInt(coverage, 'iv_resolved'),
    discardedCount: Array.isArray(discarded) ? discarded.length : null,
  };
}

// ---------------------------------------------------------------------------
// Lignes de strikes (Calls | Strike | Puts) au sein d'UN groupe
// ---------------------------------------------------------------------------

export interface StrikeRow {
  readonly strike: string;
  readonly call: OptionChainContract | null;
  readonly put: OptionChainContract | null;
}

/** Valeur numérique d'une chaîne serveur pour la géométrie/tri UNIQUEMENT. */
export function geometryNumber(value: string): number {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * Apparie CALL/PUT par strike du SEUL groupe fourni, trié par strike
 * croissant (tri de vue). Un contrat sans strike ou sans right lisible est
 * retourné à part (`unpairable`) avec sa ligne rendue telle quelle — il
 * n'est ni masqué, ni réparé.
 */
export function buildStrikeRows(group: OptionChainExpiration): {
  rows: StrikeRow[];
  unpairable: OptionChainContract[];
} {
  const byStrike = new Map<string, { call: OptionChainContract | null; put: OptionChainContract | null }>();
  const unpairable: OptionChainContract[] = [];
  for (const contract of group.contracts) {
    if (contract.strike === null || contract.right === null) {
      unpairable.push(contract);
      continue;
    }
    const slot = byStrike.get(contract.strike) ?? { call: null, put: null };
    if (contract.right === 'CALL') {
      slot.call = contract;
    } else {
      slot.put = contract;
    }
    byStrike.set(contract.strike, slot);
  }
  const rows = [...byStrike.entries()]
    .sort((a, b) => geometryNumber(a[0]) - geometryNumber(b[0]))
    .map(([strike, slot]) => ({ strike, call: slot.call, put: slot.put }));
  return { rows, unpairable };
}

// ---------------------------------------------------------------------------
// État d'affichage du cadre (dérivé des statuts PUBLIÉS, jamais deviné)
// ---------------------------------------------------------------------------

export function chainStateOf(
  queryState: DataState | 'auth-required',
  data: OptionChainResponse | undefined,
): DataState | 'auth-required' {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return queryState;
  }
  if (data === undefined) {
    return 'error';
  }
  if (data.state === 'empty') {
    return 'empty';
  }
  const truncated = data.row_budget !== null ? blockInt(data.row_budget, 'truncated_rows') : null;
  const degradedGroup = data.expirations.some((group) => group.quality !== 'VALID');
  if ((truncated !== null && truncated > 0) || degradedGroup) {
    return 'partial';
  }
  return queryState;
}

/** Budget de lignes publié (relayé verbatim depuis `row_budget`). */
export interface RowBudgetView {
  readonly maxRows: number | null;
  readonly totalRows: number | null;
  readonly publishedRows: number | null;
  readonly truncatedRows: number | null;
}

export function rowBudgetOf(data: OptionChainResponse): RowBudgetView | null {
  if (data.row_budget === null) {
    return null;
  }
  return {
    maxRows: blockInt(data.row_budget, 'max_rows'),
    totalRows: blockInt(data.row_budget, 'total_rows'),
    publishedRows: blockInt(data.row_budget, 'published_rows'),
    truncatedRows: blockInt(data.row_budget, 'truncated_rows'),
  };
}

/** Spot publié du snapshot (bloc verbatim). */
export interface SpotView {
  readonly value: string | null;
  readonly currency: string | null;
  readonly observedAt: string | null;
}

export function spotViewOf(data: OptionChainResponse): SpotView | null {
  if (data.spot === null) {
    return null;
  }
  return {
    value: blockString(data.spot, 'value'),
    currency: blockString(data.spot, 'currency'),
    observedAt: blockString(data.spot, 'observed_at'),
  };
}

// ---------------------------------------------------------------------------
// Raisons typées → phrase française (le code serveur reste affiché verbatim)
// ---------------------------------------------------------------------------

export const IV_ABSENT_REASONS_FR: Readonly<Record<string, string>> = {
  missing_quote: 'quote absente : aucune IV calculable',
  crossed_quote: 'quote croisée ou verrouillée : entrée IV refusée',
  stale_quote: 'quote plus vieille que l’âge maximal : entrée IV refusée',
  contract_expired: 'contrat expiré à l’instant du calcul',
  incomplete_identity: 'identité de contrat incomplète : aucun calcul lancé',
  iv_unresolved: 'IV non résolue : aucun Greek calculé',
  price_outside_no_arbitrage_bounds: 'prix hors des bornes de non-arbitrage',
};

/** Phrase française d'une raison d'absence + code verbatim (jamais 0). */
export function ivAbsentLabel(reason: string | null): string {
  if (reason === null) {
    return 'IV absente — raison non publiée';
  }
  const explained = IV_ABSENT_REASONS_FR[reason];
  return explained === undefined ? `IV absente — ${reason}` : `IV absente — ${explained} (${reason})`;
}
