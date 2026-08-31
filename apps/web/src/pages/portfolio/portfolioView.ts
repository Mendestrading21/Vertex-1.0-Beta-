/**
 * Lecture défensive du snapshot de valorisation (`portfolio_valuation/<id>`),
 * relayé verbatim par l'API dans `PortfolioResponse.valuation.content`.
 *
 * Ce module NE CALCULE RIEN : chaque chiffre affichable reste la chaîne
 * décimale exacte publiée par le worker (`vertex_core`), totaux inclus. Une
 * valeur absente ou illisible reste `null` — jamais un zéro, jamais une
 * moyenne, jamais une somme locale.
 */
import type { LedgerEventKind, PortfolioValuationView } from '../../api/client.ts';

// -- helpers de lecture (contenu non typé, relayé verbatim) -----------------

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function asArray(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

function str(record: UnknownRecord | null, key: string): string | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function num(record: UnknownRecord | null, key: string): number | null {
  if (record === null) {
    return null;
  }
  const value = record[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

// -- vues -------------------------------------------------------------------

export interface CalculationMetaView {
  readonly calculationId: string | null;
  readonly engineVersion: string | null;
  readonly method: string | null;
  readonly inputHash: string | null;
  readonly resultHash: string | null;
  readonly status: string | null;
}

export function calculationMetaOf(value: unknown): CalculationMetaView | null {
  const record = asRecord(value);
  if (record === null) {
    return null;
  }
  return {
    calculationId: str(record, 'calculation_id'),
    engineVersion: str(record, 'engine_version'),
    method: str(record, 'method'),
    inputHash: str(record, 'input_hash'),
    resultHash: str(record, 'result_hash'),
    status: str(record, 'status'),
  };
}

/** Un lot ouvert VALORISÉ (chaînes serveur verbatim). */
export interface ValuedLotRow {
  readonly lotId: string;
  readonly ticker: string;
  readonly currency: string;
  readonly quantity: string;
  readonly unitCost: string;
  readonly mark: string;
  readonly marketValue: string;
  readonly unrealizedPnl: string;
}

/** Un lot ouvert EXCLU de la valorisation, avec sa raison machine. */
export interface ExcludedLotRow {
  readonly lotId: string;
  readonly ticker: string | null;
  readonly currency: string | null;
  readonly reason: string;
}

export interface ConcentrationEntry {
  readonly ticker: string;
  readonly weight: string;
}

export interface CurrencyBlockView {
  readonly currency: string;
  readonly unrealizedStatus: string | null;
  readonly unrealizedReason: string | null;
  readonly totalUnrealized: string | null;
  readonly unrealizedCalculation: CalculationMetaView | null;
  readonly realizedStatus: string | null;
  readonly realizedReason: string | null;
  readonly totalRealized: string | null;
  readonly realizedFees: string | null;
  readonly realizedCalculation: CalculationMetaView | null;
  readonly concentrationStatus: string | null;
  readonly concentrationReason: string | null;
  readonly totalValue: string | null;
  readonly herfindahl: string | null;
  readonly weights: readonly ConcentrationEntry[];
  readonly concentrationCalculation: CalculationMetaView | null;
}

export interface MarksSourceView {
  readonly status: string | null;
  readonly reason: string | null;
  readonly snapshotVersion: number | null;
  readonly asOf: string | null;
  readonly tickersMarked: number | null;
}

export interface CoverageView {
  readonly eventsConsidered: number | null;
  readonly positionEvents: number | null;
  readonly cashEvents: number | null;
  readonly compensationPairs: number | null;
  readonly lotsOpen: number | null;
  readonly lotsValued: number | null;
  readonly lotsExcluded: number | null;
  readonly invalidPositions: readonly ExcludedLotRow[];
}

export interface ValuationContentView {
  readonly asOf: string | null;
  readonly engineVersion: string | null;
  readonly markPopulation: string | null;
  readonly lotMethod: string | null;
  readonly marks: MarksSourceView;
  readonly blocks: readonly CurrencyBlockView[];
  readonly valuedLots: readonly ValuedLotRow[];
  readonly excludedLots: readonly ExcludedLotRow[];
  readonly coverage: CoverageView;
}

function currencyBlockOf(value: unknown): CurrencyBlockView | null {
  const record = asRecord(value);
  const currency = str(record, 'currency');
  if (record === null || currency === null) {
    return null;
  }
  const unrealized = asRecord(record['unrealized']);
  const realized = asRecord(record['realized']);
  const concentration = asRecord(record['concentration']);
  const weightsRecord = asRecord(concentration?.['weights']);
  const weights: ConcentrationEntry[] = [];
  if (weightsRecord !== null) {
    for (const ticker of Object.keys(weightsRecord).sort()) {
      const weight = weightsRecord[ticker];
      if (typeof weight === 'string' && weight !== '') {
        weights.push({ ticker, weight });
      }
    }
  }
  return {
    currency,
    unrealizedStatus: str(unrealized, 'status'),
    unrealizedReason: str(unrealized, 'reason'),
    totalUnrealized: str(unrealized, 'total_unrealized'),
    unrealizedCalculation: calculationMetaOf(unrealized?.['calculation']),
    realizedStatus: str(realized, 'status'),
    realizedReason: str(realized, 'reason'),
    totalRealized: str(realized, 'total_pnl'),
    realizedFees: str(realized, 'total_fees'),
    realizedCalculation: calculationMetaOf(realized?.['calculation']),
    concentrationStatus: str(concentration, 'status'),
    concentrationReason: str(concentration, 'reason'),
    totalValue: str(concentration, 'total_value'),
    herfindahl: str(concentration, 'herfindahl_index'),
    weights,
    concentrationCalculation: calculationMetaOf(concentration?.['calculation']),
  };
}

function valuedLotsOf(record: UnknownRecord, currency: string): readonly ValuedLotRow[] {
  const unrealized = asRecord(record['unrealized']);
  const rows: ValuedLotRow[] = [];
  for (const entry of asArray(unrealized?.['lots'])) {
    const lot = asRecord(entry);
    const lotId = str(lot, 'lot_id');
    const ticker = str(lot, 'ticker');
    const quantity = str(lot, 'quantity');
    const unitCost = str(lot, 'unit_cost');
    const mark = str(lot, 'mark');
    const marketValue = str(lot, 'market_value');
    const unrealizedPnl = str(lot, 'unrealized_pnl');
    if (
      lotId !== null &&
      ticker !== null &&
      quantity !== null &&
      unitCost !== null &&
      mark !== null &&
      marketValue !== null &&
      unrealizedPnl !== null
    ) {
      rows.push({ lotId, ticker, currency, quantity, unitCost, mark, marketValue, unrealizedPnl });
    }
  }
  return rows;
}

function excludedLotOf(value: unknown): ExcludedLotRow | null {
  const record = asRecord(value);
  const reason = str(record, 'reason');
  if (record === null || reason === null) {
    return null;
  }
  return {
    lotId: str(record, 'lot_id') ?? '—',
    ticker: str(record, 'ticker'),
    currency: str(record, 'currency'),
    reason,
  };
}

/**
 * Lit le contenu du snapshot de valorisation. `null` si l'état est `empty`
 * ou si le contenu ne porte pas la version de schéma attendue — l'absence
 * reste une absence.
 */
export function valuationContentOf(valuation: PortfolioValuationView): ValuationContentView | null {
  // `ok` ET `stale` portent tous deux un contenu daté. Refuser `stale` ici
  // ferait disparaître la valorisation derrière un cadre « erreur » alors
  // que le serveur la sert avec son âge : ce serait cacher la donnée au
  // lieu de la dater, exactement l'inverse du correctif.
  if (valuation.state !== 'ok' && valuation.state !== 'stale') {
    return null;
  }
  const content = asRecord(valuation.content);
  if (content === null || str(content, 'schema_version') !== 'vertex.portfolio-valuation/1.0') {
    return null;
  }
  const marksRecord = asRecord(content['marks']);
  const marksSource = asRecord(marksRecord?.['source']);
  const blocks: CurrencyBlockView[] = [];
  const valuedLots: ValuedLotRow[] = [];
  for (const entry of asArray(content['positions_by_currency'])) {
    const block = currencyBlockOf(entry);
    const record = asRecord(entry);
    if (block !== null && record !== null) {
      blocks.push(block);
      valuedLots.push(...valuedLotsOf(record, block.currency));
    }
  }
  const excludedLots = asArray(content['excluded_lots'])
    .map(excludedLotOf)
    .filter((row): row is ExcludedLotRow => row !== null);
  const coverageRecord = asRecord(content['coverage']);
  const invalidPositions = asArray(coverageRecord?.['invalid_positions'])
    .map((entry) => {
      const record = asRecord(entry);
      const reason = str(record, 'reason');
      if (record === null || reason === null) {
        return null;
      }
      return {
        lotId: '—',
        ticker: str(record, 'ticker'),
        currency: str(record, 'currency'),
        reason,
      } satisfies ExcludedLotRow;
    })
    .filter((row): row is ExcludedLotRow => row !== null);
  return {
    asOf: str(content, 'as_of'),
    engineVersion: str(content, 'engine_version'),
    markPopulation: str(content, 'mark_population'),
    lotMethod: str(content, 'lot_method'),
    marks: {
      status: str(marksRecord, 'status'),
      reason: str(marksRecord, 'reason'),
      snapshotVersion: num(marksSource, 'snapshot_version'),
      asOf: str(marksSource, 'as_of'),
      tickersMarked: num(marksRecord, 'tickers_marked'),
    },
    blocks,
    valuedLots,
    excludedLots,
    coverage: {
      eventsConsidered: num(coverageRecord, 'events_considered'),
      positionEvents: num(coverageRecord, 'position_events'),
      cashEvents: num(coverageRecord, 'cash_events'),
      compensationPairs: num(coverageRecord, 'compensation_pairs'),
      lotsOpen: num(coverageRecord, 'lots_open'),
      lotsValued: num(coverageRecord, 'lots_valued'),
      lotsExcluded: num(coverageRecord, 'lots_excluded'),
      invalidPositions,
    },
  };
}

// -- libellés français ------------------------------------------------------

/**
 * Raisons machine d'exclusion → explication française. Une raison inconnue
 * est affichée telle quelle (code machine), jamais masquée.
 */
export const EXCLUSION_REASON_LABELS: Readonly<Record<string, string>> = {
  missing_mark: 'aucune clôture synthétique publiée pour ce ticker',
  invalid_mark: 'clôture publiée illisible ou non positive — refusée',
  mark_currency_mismatch: 'devise de la clôture différente de celle du lot',
  no_markets_snapshot: 'aucun snapshot de marchés publié — aucune marque disponible',
  oversold_position: 'ventes déclarées supérieures aux achats déclarés — position contradictoire',
};

export function exclusionReasonLabel(reason: string): string {
  return EXCLUSION_REASON_LABELS[reason] ?? reason;
}

/**
 * Les 13 kinds canoniques du journal, avec leur libellé français de FAIT
 * PASSÉ (sémantique de journal comptable : rien ici n'est une instruction).
 */
export const LEDGER_KIND_LABELS: Readonly<Record<LedgerEventKind, string>> = {
  BUY_RECORDED: 'Achat enregistré (déjà effectué hors Vertex)',
  SELL_RECORDED: 'Vente enregistrée (déjà effectuée hors Vertex)',
  OPTION_OPEN: 'Ouverture d’option enregistrée',
  OPTION_CLOSE: 'Clôture d’option enregistrée',
  DIVIDEND: 'Dividende perçu',
  INTEREST: 'Intérêts perçus',
  FEE: 'Frais constatés',
  TAX: 'Impôt ou taxe constaté',
  DEPOSIT: 'Dépôt d’espèces',
  WITHDRAWAL: 'Retrait d’espèces',
  FX_CONVERSION: 'Conversion de devises constatée',
  CORPORATE_ACTION: 'Opération sur titre constatée',
  ADJUSTMENT: 'Ajustement déclaré',
};

export const LEDGER_KINDS: readonly LedgerEventKind[] = Object.keys(
  LEDGER_KIND_LABELS,
) as LedgerEventKind[];

/** Kinds qui exigent un instrument, une quantité et un prix côté serveur. */
export const POSITION_KINDS: ReadonlySet<LedgerEventKind> = new Set([
  'BUY_RECORDED',
  'SELL_RECORDED',
]);

/**
 * Conversion d'un `datetime-local` (heure locale du poste) vers l'instant
 * UTC ISO attendu par l'API. `null` si le champ est vide ou illisible —
 * l'erreur de fond reste tranchée par le serveur (422 verbatim).
 */
export function localDateTimeToUtcIso(value: string): string | null {
  if (value === '') {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
}

// -- erreurs serveur (422/409) relayées verbatim ----------------------------

export interface ServerRejectionView {
  readonly code: string | null;
  readonly message: string | null;
  /** Défauts de validation Pydantic (`loc` + `msg`), relayés tels quels. */
  readonly wireIssues: readonly string[];
}

/** Lit `detail` d'une erreur API (objet code/message OU liste Pydantic). */
export function serverRejectionOf(detail: unknown): ServerRejectionView | null {
  const body = asRecord(detail);
  if (body === null) {
    return null;
  }
  const rawDetail = body['detail'];
  const detailRecord = asRecord(rawDetail);
  if (detailRecord !== null) {
    return {
      code: str(detailRecord, 'code'),
      message: str(detailRecord, 'message'),
      wireIssues: [],
    };
  }
  const issues: string[] = [];
  for (const entry of asArray(rawDetail)) {
    const issue = asRecord(entry);
    if (issue === null) {
      continue;
    }
    const loc = asArray(issue['loc'])
      .filter((part): part is string | number => typeof part === 'string' || typeof part === 'number')
      .join('.');
    const msg = str(issue, 'msg') ?? 'invalid';
    issues.push(loc === '' ? msg : `${loc} : ${msg}`);
  }
  if (issues.length === 0) {
    return null;
  }
  return { code: null, message: null, wireIssues: issues };
}
