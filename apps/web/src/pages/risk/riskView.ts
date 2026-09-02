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
  readonly conclusion: string;
  readonly refusalReason: string | null;
  readonly synchronicityWarning: string | null;
  readonly instruments: ReadonlyArray<{ readonly ticker: string; readonly label: string }>;
  readonly matrix: ReadonlyArray<readonly string[]>;
  readonly bands: ReadonlyArray<readonly string[]>;
  readonly extremes: {
    readonly mostCorrelated: RiskExtremePair;
    readonly mostOpposed: RiskExtremePair;
  } | null;
  readonly coverage: {
    readonly perimeterSize: number;
    readonly retained: number;
    readonly commonDays: number;
    readonly minimumDays: number;
    readonly moderateThreshold: string;
    readonly strongThreshold: string;
    readonly window: string | null;
    readonly alignmentLoss: ReadonlyArray<{ readonly ticker: string; readonly lost: number }>;
    readonly discarded: ReadonlyArray<{
      readonly instrument: string;
      readonly reason: string;
    }>;
  };
}

function stringOf(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function numberOf(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function stringGridOf(value: unknown): ReadonlyArray<readonly string[]> {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((row) =>
    Array.isArray(row) ? row.map((cell) => (typeof cell === 'string' ? cell : '')) : [],
  );
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
  const discarded = Array.isArray(coverage.discarded) ? coverage.discarded : [];

  const mostCorrelated = extremes === null ? null : pairOf(extremes.most_correlated);
  const mostOpposed = extremes === null ? null : pairOf(extremes.most_opposed);

  const windowStart = stringOf(coverage.window_start);
  const windowEnd = stringOf(coverage.window_end);

  return {
    serverState: response.state,
    population: stringOf(content.population) ?? 'EMPTY',
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
    extremes:
      mostCorrelated !== null && mostOpposed !== null ? { mostCorrelated, mostOpposed } : null,
    coverage: {
      perimeterSize: numberOf(coverage.perimeter_size),
      retained: numberOf(coverage.retained_count),
      commonDays: numberOf(coverage.common_trading_days),
      minimumDays: numberOf(coverage.minimum_common_days),
      moderateThreshold: stringOf(coverage.moderate_threshold) ?? '—',
      strongThreshold: stringOf(coverage.strong_threshold) ?? '—',
      window: windowStart !== null && windowEnd !== null ? `${windowStart} → ${windowEnd}` : null,
      // Trié par perte DÉCROISSANTE : ce qui coûte le plus se lit d'abord.
      // À perte égale, l'ordre alphabétique garde l'affichage stable d'un
      // rendu à l'autre.
      alignmentLoss: Object.entries(lost)
        .map(([ticker, value]) => ({ ticker, lost: numberOf(value) }))
        .filter((entry) => entry.lost > 0)
        .sort((a, b) => b.lost - a.lost || a.ticker.localeCompare(b.ticker)),
      discarded: discarded.map((entry) => {
        const record = (entry ?? {}) as Record<string, unknown>;
        const reason = stringOf(record.reason) ?? '';
        return {
          instrument: stringOf(record.instrument) ?? '',
          reason: DISCARD_LABELS[reason] ?? reason,
        };
      }),
    },
  };
}
