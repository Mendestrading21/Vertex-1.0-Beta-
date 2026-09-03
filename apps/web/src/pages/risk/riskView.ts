import type { RiskMatrixResponse } from '../../api/client.ts';

/**
 * Lecture du contrat Risques — SÉLECTION et LIBELLÉS, jamais de calcul.
 *
 * Ce module transforme la réponse de l'API en une vue prête à afficher. Il ne
 * fait que trois choses : lire des champs, traduire des codes serveur en
 * français, et trier ce qui doit être stable à l'écran.
 *
 * IL NE FAIT AUCUN CALCUL FINANCIER. Les coefficients restent les chaînes
 * publiées, les bandes restent les noms publiés, les seuils restent les
 * chaînes publiées. Rien n'est arrondi, comparé ni reclassé ici :
 * `.claude/rules/frontend.md` l'interdit, et un arrondi refait côté client
 * pourrait afficher un nombre différent de celui que le serveur a certifié.
 *
 * LOT-A6 : la vue relaie aussi ce que le contrat publiait sans être lu —
 * population, état des données, moteur, schéma, unité, périmètre déclaré et
 * retenu, enregistrements rejetés, séances par instrument, observations,
 * fenêtre de retour. Aucun champ nouveau côté serveur.
 */

/** Libellés français des motifs de refus publiés par le worker. */
export const REFUSAL_LABELS: Readonly<Record<string, string>> = {
  perimeter_too_small:
    'moins de deux instruments du périmètre ont des barres — une matrice compare, elle ne décrit pas',
  insufficient_common_days:
    'trop peu de séances communes aux instruments retenus, sous le seuil déclaré',
  calculation_refused: 'le calcul a refusé la matrice',
};

/** Libellés français des motifs d'écartement d'un instrument. */
export const DISCARD_LABELS: Readonly<Record<string, string>> = {
  no_bars: 'aucune barre quotidienne collectée',
  source_not_allowed: 'source non déclarée',
  rights_not_usable: 'droits inutilisables',
};

export interface RiskExtremePair {
  readonly pair: string;
  readonly value: string;
}

export interface RiskView {
  readonly serverState: string;
  readonly population: string;
  readonly dataState: string | null;
  readonly asOf: string | null;
  readonly engineVersion: string | null;
  readonly schemaVersion: string | null;
  readonly unit: string | null;
  readonly conclusion: string;
  readonly refusalReason: string | null;
  readonly synchronicityWarning: string | null;
  readonly instruments: ReadonlyArray<{ readonly ticker: string; readonly label: string }>;
  /** Cellule NON servie ou illisible = `null`, jamais `''` : une chaîne vide
   *  se lit comme une absence là où la donnée est cassée. */
  readonly matrix: ReadonlyArray<ReadonlyArray<string | null>>;
  readonly bands: ReadonlyArray<ReadonlyArray<string | null>>;
  /** `null` = aucun bloc `extremes` publié. Une paire servie SEULE est
   *  conservée : l'absence de l'autre ne l'efface pas. */
  readonly extremes: {
    readonly mostCorrelated: RiskExtremePair | null;
    readonly mostOpposed: RiskExtremePair | null;
  } | null;
  readonly coverage: {
    readonly perimeter: readonly string[];
    readonly retainedTickers: readonly string[];
    readonly perimeterSize: number;
    readonly retained: number;
    readonly commonDays: number;
    readonly minimumDays: number;
    /** Seuils PUBLIÉS. `null` = non publié — la page le dit, aucun tiret. */
    readonly moderateThreshold: string | null;
    readonly strongThreshold: string | null;
    readonly window: string | null;
    readonly observationsConsidered: number | null;
    readonly lookbackSeconds: number | null;
    /** `days`/`lost` à `null` = compte NON publié pour cet instrument. Ces
     *  deux mappings ne sont PAS validés par le relais (`vertex_api/risk.py`) :
     *  un repli à 0 y transformerait un contrat rompu en fait mesuré. */
    readonly tradingDaysPerInstrument: ReadonlyArray<{ readonly ticker: string; readonly days: number | null }>;
    /** TOUTES les entrées servies, y compris une perte NULLE : « n'a rien
     *  perdu » est un fait publié, distinct de « n'est pas dans la matrice ». */
    readonly alignmentLoss: ReadonlyArray<{ readonly ticker: string; readonly lost: number | null }>;
    readonly discarded: ReadonlyArray<{
      readonly instrument: string;
      readonly reason: string;
    }>;
    /** Entrées RENDABLES. Le compte servi vit à côté : rendre moins que ce
     *  que le serveur a rejeté sous-déclarerait ses refus. */
    readonly rejectedRecords: readonly string[];
    readonly rejectedServedCount: number;
  };
}

function stringOf(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function numberOf(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function optionalNumberOf(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function stringListOf(value: unknown): readonly string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [];
}

/**
 * Grille de chaînes SERVIES. Une cellule qui n'est pas une chaîne non vide —
 * absente, nulle, ou publiée dans une autre forme — devient `null` et non
 * `''` : la page rend alors « non publié » au lieu d'une case vide que l'œil
 * lit comme une absence normale.
 */
function stringGridOf(value: unknown): ReadonlyArray<ReadonlyArray<string | null>> {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((row) => (Array.isArray(row) ? row.map((cell) => stringOf(cell)) : []));
}

function pairOf(value: unknown): RiskExtremePair | null {
  if (typeof value !== 'object' || value === null) {
    return null;
  }
  const record = value as Record<string, unknown>;
  const a = stringOf(record.a);
  const b = stringOf(record.b);
  const coefficient = stringOf(record.value);
  if (a === null || b === null || coefficient === null) {
    return null;
  }
  return { pair: `${a} et ${b}`, value: coefficient };
}

/** Un enregistrement rejeté, rendu lisible sans en inventer la forme. */
function rejectedRecordOf(value: unknown): string | null {
  if (typeof value === 'string') {
    return value.length > 0 ? value : null;
  }
  if (typeof value !== 'object' || value === null) {
    return null;
  }
  const record = value as Record<string, unknown>;
  const parts = Object.entries(record)
    .filter(([, entry]) => typeof entry === 'string' || typeof entry === 'number')
    .map(([key, entry]) => `${key}=${String(entry)}`);
  return parts.length === 0 ? null : parts.join(' · ');
}

/**
 * Traduit la réponse de l'API en vue affichable.
 *
 * Une clé absente ne devient JAMAIS zéro par commodité — les compteurs de
 * couverture sont publiés par le serveur, et un champ manquant signale un
 * contrat rompu que le relais aurait déjà refusé. Le repli à 0 n'existe ici
 * que pour satisfaire le typage d'une charge relayée en mapping libre.
 */
export function riskViewOf(response: RiskMatrixResponse): RiskView {
  const content = (response.content ?? {}) as Record<string, unknown>;
  const coverage = (content.coverage ?? {}) as Record<string, unknown>;
  const extremes = (content.extremes ?? null) as Record<string, unknown> | null;

  const refusalCode = stringOf(coverage.refusal_reason);
  const lost = (coverage.trading_days_lost_to_alignment ?? {}) as Record<string, unknown>;
  const perInstrument = (coverage.trading_days_per_instrument ?? {}) as Record<string, unknown>;
  const discarded = Array.isArray(coverage.discarded) ? coverage.discarded : [];
  const rejected = Array.isArray(coverage.rejected_records) ? coverage.rejected_records : [];

  const mostCorrelated = extremes === null ? null : pairOf(extremes.most_correlated);
  const mostOpposed = extremes === null ? null : pairOf(extremes.most_opposed);

  const windowStart = stringOf(coverage.window_start);
  const windowEnd = stringOf(coverage.window_end);

  return {
    serverState: response.state,
    population: stringOf(content.population) ?? 'EMPTY',
    dataState: stringOf(content.data_state),
    asOf: stringOf(content.as_of) ?? response.as_of,
    engineVersion: stringOf(content.engine_version),
    schemaVersion: stringOf(content.schema_version),
    unit: stringOf(content.unit),
    conclusion: stringOf(content.conclusion) ?? '',
    refusalReason: refusalCode === null ? null : (REFUSAL_LABELS[refusalCode] ?? refusalCode),
    synchronicityWarning: stringOf(content.synchronicity_warning),
    instruments: Array.isArray(content.instruments)
      ? content.instruments.map((entry) => {
          const record = (entry ?? {}) as Record<string, unknown>;
          const ticker = stringOf(record.ticker) ?? '';
          return { ticker, label: stringOf(record.label) ?? ticker };
        })
      : [],
    matrix: stringGridOf(content.matrix),
    bands: stringGridOf(content.matrix_bands),
    // Le bloc existe dès que le serveur le publie ; chaque paire y vaut
    // `null` si elle n'est pas servie. Exiger les DEUX effaçait une paire
    // pourtant publiée (`_checked_pair` accepte une paire nulle).
    extremes: extremes === null ? null : { mostCorrelated, mostOpposed },
    coverage: {
      perimeter: stringListOf(coverage.perimeter),
      retainedTickers: stringListOf(coverage.retained),
      perimeterSize: numberOf(coverage.perimeter_size),
      retained: numberOf(coverage.retained_count),
      commonDays: numberOf(coverage.common_trading_days),
      minimumDays: numberOf(coverage.minimum_common_days),
      moderateThreshold: stringOf(coverage.moderate_threshold),
      strongThreshold: stringOf(coverage.strong_threshold),
      window: windowStart !== null && windowEnd !== null ? `${windowStart} → ${windowEnd}` : null,
      observationsConsidered: optionalNumberOf(coverage.observations_considered),
      lookbackSeconds: optionalNumberOf(coverage.lookback_seconds),
      // Ordre alphabétique : un compte par instrument, stable d'un rendu à l'autre.
      tradingDaysPerInstrument: Object.entries(perInstrument)
        .map(([ticker, value]) => ({ ticker, days: optionalNumberOf(value) }))
        .sort((a, b) => a.ticker.localeCompare(b.ticker)),
      // Trié par perte DÉCROISSANTE : ce qui coûte le plus se lit d'abord.
      // À perte égale, l'ordre alphabétique garde l'affichage stable d'un
      // rendu à l'autre.
      alignmentLoss: Object.entries(lost)
        .map(([ticker, value]) => ({ ticker, lost: optionalNumberOf(value) }))
        // Aucune entrée n'est filtrée : une perte nulle SERVIE est un fait.
        // Les comptes non publiés passent en fin, après les pertes connues.
        .sort((a, b) => (b.lost ?? -1) - (a.lost ?? -1) || a.ticker.localeCompare(b.ticker)),
      discarded: discarded.map((entry) => {
        const record = (entry ?? {}) as Record<string, unknown>;
        const reason = stringOf(record.reason) ?? '';
        return {
          instrument: stringOf(record.instrument) ?? '',
          reason: DISCARD_LABELS[reason] ?? reason,
        };
      }),
      rejectedRecords: rejected.map(rejectedRecordOf).filter((entry): entry is string => entry !== null),
      rejectedServedCount: rejected.length,
    },
  };
}

/**
 * Libellés français des bandes SERVIES (`matrix_bands`), pour la légende et
 * les infobulles. Les clés sont les noms publiés par le worker, avec leurs
 * soulignés : aucune traduction de clé, aucune normalisation.
 */
export const BAND_LABELS: Readonly<Record<string, string>> = {
  self: 'Le même actif',
  strong_positive: 'Fortement liés, même sens',
  moderate_positive: 'Modérément liés, même sens',
  weak: 'Peu liés',
  moderate_negative: 'Modérément liés, sens contraire',
  strong_negative: 'Fortement liés, sens contraire',
  unknown: 'Bande non publiée par le serveur',
};

/**
 * Lignes de la matrice, pour l'inspecteur d'un instrument.
 *
 * LOT P4 : une bande absente vaut `null` et NON `'weak'`. Le repli précédent
 * affirmait « peu liés » sur une case dont le serveur n'avait rien publié —
 * un faux rassurant, exactement ce que l'article « absence ≠ valeur »
 * interdit. Le coefficient suit la même règle.
 */
export function correlationRowsOf(view: RiskView): ReadonlyArray<{
  readonly ticker: string;
  readonly label: string;
  readonly cells: ReadonlyArray<{ readonly value: string | null; readonly band: string | null }>;
}> {
  return view.instruments.map((instrument, index) => ({
    ticker: instrument.ticker,
    label: instrument.label,
    cells: view.instruments.map((_, column) => ({
      value: view.matrix[index]?.[column] ?? null,
      band: view.bands[index]?.[column] ?? null,
    })),
  }));
}
