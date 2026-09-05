/**
 * Aides de PRÉSENTATION de la page Analyse — aucun calcul financier.
 *
 * Le dossier `analysis/{instrument}` arrive calculé et étiqueté par le
 * worker : barres OHLCV validées (chaînes décimales verbatim), rail evidence
 * de la fusion, bloc scénarios THÉORIQUE (ou son absence typée) et
 * `AdviceResult` canonique de l'unique AdviceEngine. Ici on ne fait que :
 * lire défensivement les blocs non typés du contrat, parser les chaînes
 * serveur en nombres POUR LA GÉOMÉTRIE du graphique uniquement, et dériver
 * l'état d'affichage depuis les statuts PUBLIÉS.
 */
import type { AnalysisResponse } from '../../api/client.ts';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { geometryValue } from '../../components/widgets/geometry.ts';

function blockString(block: Record<string, unknown>, key: string): string | null {
  const value = block[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function blockInt(block: Record<string, unknown>, key: string): number | null {
  const value = block[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function blockBool(block: Record<string, unknown>, key: string): boolean | null {
  const value = block[key];
  return typeof value === 'boolean' ? value : null;
}

// ---------------------------------------------------------------------------
// Barres OHLCV (chaînes serveur verbatim)
// ---------------------------------------------------------------------------

export interface OhlcvBar {
  readonly tradingDay: string;
  readonly open: string;
  readonly high: string;
  readonly low: string;
  readonly close: string;
  readonly volume: number;
}

export interface BarsView {
  readonly status: 'OK' | 'ABSENT';
  readonly count: number | null;
  readonly currency: string | null;
  readonly adjustmentBasis: string | null;
  readonly firstTradingDay: string | null;
  readonly lastTradingDay: string | null;
  readonly lastClose: string | null;
  readonly quality: string | null;
  readonly fresh: boolean | null;
  readonly sourceEventId: string | null;
  readonly observedAsOf: string | null;
  readonly discardedCount: number;
  readonly bars: readonly OhlcvBar[];
}

export function barsViewOf(data: AnalysisResponse): BarsView | null {
  const block = data.bars;
  // `undefined` n'est pas dans le contrat, mais un corps étranger reçu à la
  // place d'un dossier ne doit jamais faire tomber la page : absent = absent.
  if (block === null || block === undefined) {
    return null;
  }
  const rawBars = block['bars'];
  const bars: OhlcvBar[] = [];
  if (Array.isArray(rawBars)) {
    for (const raw of rawBars) {
      if (typeof raw !== 'object' || raw === null) {
        continue;
      }
      const bar = raw as Record<string, unknown>;
      const tradingDay = blockString(bar, 'trading_day');
      const open = blockString(bar, 'open');
      const high = blockString(bar, 'high');
      const low = blockString(bar, 'low');
      const close = blockString(bar, 'close');
      const volume = blockInt(bar, 'volume');
      if (
        tradingDay === null ||
        open === null ||
        high === null ||
        low === null ||
        close === null ||
        volume === null
      ) {
        continue; // barre illisible : ignorée à l'affichage, comptée côté serveur
      }
      bars.push({ tradingDay, open, high, low, close, volume });
    }
  }
  const discarded = block['discarded'];
  return {
    status: blockString(block, 'status') === 'OK' ? 'OK' : 'ABSENT',
    count: blockInt(block, 'count'),
    currency: blockString(block, 'currency'),
    adjustmentBasis: blockString(block, 'adjustment_basis'),
    firstTradingDay: blockString(block, 'first_trading_day'),
    lastTradingDay: blockString(block, 'last_trading_day'),
    lastClose: blockString(block, 'last_close'),
    quality: blockString(block, 'quality'),
    fresh: blockBool(block, 'fresh'),
    sourceEventId: blockString(block, 'source_event_id'),
    observedAsOf: blockString(block, 'observed_as_of'),
    discardedCount: Array.isArray(discarded) ? discarded.length : 0,
    bars,
  };
}

/** Valeur numérique d'une chaîne serveur pour la GÉOMÉTRIE du rendu. */
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

// ---------------------------------------------------------------------------
// AdviceResult (statut canonique — relayé, jamais recalculé)
// ---------------------------------------------------------------------------

/**
 * Un couple `clé → valeur` de la PREUVE servie par une gate
 * (`observed_values`, `thresholds`).
 *
 * `text === null` ne veut PAS dire « non publié » : la clé EST publiée, mais
 * sa valeur n'est pas un scalaire que l'affichage sache relayer verbatim
 * (objet, tableau, `null`). L'aveu correspondant est donc « non reconnu », pas
 * « non publié » — nommer la mauvaise nature serait mentir sur le serveur.
 */
export interface GateEvidenceEntry {
  readonly key: string;
  readonly text: string | null;
}

export interface GateView {
  readonly gateId: string;
  readonly version: string | null;
  readonly status: string;
  readonly reasonCode: string;
  readonly message: string;
  /** `observed_values` SERVI — ce que la gate a réellement vu. */
  readonly observedValues: readonly GateEvidenceEntry[];
  /** `thresholds` SERVI — la configuration que la gate a comparée. */
  readonly thresholds: readonly GateEvidenceEntry[];
}

/**
 * Relais VERBATIM d'un scalaire servi. Ce n'est pas un formatage : aucune
 * unité n'est ajoutée, aucun arrondi n'est appliqué, aucun séparateur n'est
 * inséré. Un nombre publié `60` s'écrit `60`, un booléen publié s'écrit
 * `true` — ce sont des codes serveur, pas des mots français.
 *
 * Tout le reste (objet, tableau, `null`, `undefined`) rend `null` : le lecteur
 * verra que la clé est publiée et que sa valeur n'entre pas dans le
 * vocabulaire relayable, plutôt qu'un `[object Object]`.
 */
function evidenceText(value: unknown): string | null {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === 'boolean') {
    return String(value);
  }
  return null;
}

/**
 * Lit un dictionnaire de preuve servi. L'ORDRE des clés est celui du serveur :
 * il n'est ni trié, ni filtré, ni complété — une clé absente du payload reste
 * absente de l'affichage, elle n'est jamais inventée avec une valeur vide.
 */
function gateEvidenceOf(gate: Record<string, unknown>, key: string): GateEvidenceEntry[] {
  const raw = gate[key];
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
    return [];
  }
  return Object.entries(raw as Record<string, unknown>).map(([name, value]) => ({
    key: name,
    text: evidenceText(value),
  }));
}

export interface AdviceView {
  readonly adviceId: string | null;
  readonly status: string;
  readonly direction: string;
  readonly horizon: string | null;
  readonly asOf: string | null;
  readonly validUntil: string | null;
  readonly engineVersion: string | null;
  readonly riskSummary: string | null;
  readonly gates: readonly GateView[];
  readonly limitations: readonly string[];
  readonly explanationFacts: readonly string[];
}

export function adviceViewOf(data: AnalysisResponse): AdviceView | null {
  const block = data.advice;
  if (block === null) {
    return null;
  }
  const status = blockString(block, 'status');
  const direction = blockString(block, 'direction');
  if (status === null || direction === null) {
    return null; // avis illisible : affiché comme absent, jamais reconstruit
  }
  const rawGates = block['gates'];
  const gates: GateView[] = [];
  if (Array.isArray(rawGates)) {
    for (const raw of rawGates) {
      if (typeof raw !== 'object' || raw === null) {
        continue;
      }
      const gate = raw as Record<string, unknown>;
      const gateId = blockString(gate, 'gate_id');
      const gateStatus = blockString(gate, 'status');
      const reasonCode = blockString(gate, 'reason_code');
      if (gateId === null || gateStatus === null || reasonCode === null) {
        continue;
      }
      gates.push({
        gateId,
        version: blockString(gate, 'version'),
        status: gateStatus,
        reasonCode,
        message: blockString(gate, 'message') ?? '',
        observedValues: gateEvidenceOf(gate, 'observed_values'),
        thresholds: gateEvidenceOf(gate, 'thresholds'),
      });
    }
  }
  const stringList = (key: string): string[] => {
    const value = block[key];
    return Array.isArray(value)
      ? value.filter((entry): entry is string => typeof entry === 'string')
      : [];
  };
  return {
    adviceId: blockString(block, 'advice_id'),
    status,
    direction,
    horizon: blockString(block, 'horizon'),
    asOf: blockString(block, 'as_of'),
    validUntil: blockString(block, 'valid_until'),
    engineVersion: blockString(block, 'engine_version'),
    riskSummary: blockString(block, 'risk_summary'),
    gates,
    limitations: stringList('limitations'),
    explanationFacts: stringList('explanation_facts'),
  };
}

/** Libellés français des statuts canoniques (le code reste affiché verbatim). */
export const ADVICE_STATUS_FR: Readonly<Record<string, string>> = {
  BLOCKED: 'bloqué par une gate fermée',
  INSUFFICIENT_DATA: 'données requises insuffisantes',
  OBSERVE: 'données valides, observation seulement',
  REVIEW: 'digne d’une étude analytique',
  QUALIFIED: 'toutes les gates passées',
};

export const DIRECTION_FR: Readonly<Record<string, string>> = {
  BULLISH: 'lecture haussière',
  BEARISH: 'lecture baissière',
  NEUTRAL: 'lecture neutre',
  MIXED: 'lecture contrastée',
  UNKNOWN: 'aucune lecture directionnelle',
};

// ---------------------------------------------------------------------------
// Evidence (clusters de fusion)
// ---------------------------------------------------------------------------

export interface EvidenceClusterView {
  readonly clusterId: string;
  readonly title: string;
  readonly sources: readonly string[];
  readonly memberCount: number | null;
  readonly lastReceivedAt: string | null;
  readonly synthetic: boolean;
}

export interface EvidenceView {
  readonly rulesetVersion: string | null;
  readonly considered: number | null;
  readonly clustersTotal: number | null;
  readonly clusters: readonly EvidenceClusterView[];
}

export function evidenceViewOf(data: AnalysisResponse): EvidenceView | null {
  const block = data.evidence;
  if (block === null) {
    return null;
  }
  const rawClusters = block['clusters'];
  const clusters: EvidenceClusterView[] = [];
  if (Array.isArray(rawClusters)) {
    for (const raw of rawClusters) {
      if (typeof raw !== 'object' || raw === null) {
        continue;
      }
      const cluster = raw as Record<string, unknown>;
      const clusterId = blockString(cluster, 'cluster_id');
      const title = blockString(cluster, 'title');
      if (clusterId === null || title === null) {
        continue;
      }
      const sources = cluster['sources'];
      clusters.push({
        clusterId,
        title,
        sources: Array.isArray(sources)
          ? sources.filter((entry): entry is string => typeof entry === 'string')
          : [],
        memberCount: blockInt(cluster, 'member_count'),
        lastReceivedAt: blockString(cluster, 'last_received_at'),
        synthetic: blockBool(cluster, 'synthetic') === true,
      });
    }
  }
  return {
    rulesetVersion: blockString(block, 'ruleset_version'),
    considered: blockInt(block, 'considered'),
    clustersTotal: blockInt(block, 'clusters_total'),
    clusters,
  };
}

// ---------------------------------------------------------------------------
// Scénarios (bloc THÉORIQUE ou absence typée)
// ---------------------------------------------------------------------------

export interface ScenariosView {
  readonly status: 'OK' | 'ABSENT';
  readonly reason: string | null;
  readonly valueNature: string | null;
  readonly basisLabel: string | null;
  readonly spotGrid: readonly string[];
  readonly timeGridYears: readonly string[];
  /** grid[scenario][temps][spot] — chaînes serveur verbatim. */
  readonly grid: readonly (readonly (readonly string[])[])[];
  readonly calculationId: string | null;
  readonly inputHash: string | null;
}

export function scenariosViewOf(data: AnalysisResponse): ScenariosView | null {
  const block = data.scenarios;
  if (block === null) {
    return null;
  }
  const status = blockString(block, 'status');
  if (status !== 'OK') {
    return {
      status: 'ABSENT',
      reason: blockString(block, 'reason'),
      valueNature: null,
      basisLabel: null,
      spotGrid: [],
      timeGridYears: [],
      grid: [],
      calculationId: null,
      inputHash: null,
    };
  }
  const stringGrid = (value: unknown): string[] =>
    Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [];
  const basis = block['basis'];
  let basisLabel: string | null = null;
  if (typeof basis === 'object' && basis !== null) {
    const record = basis as Record<string, unknown>;
    const right = blockString(record, 'right');
    const strike = blockString(record, 'strike');
    const expiration = blockString(record, 'expiration');
    const tradingClass = blockString(record, 'trading_class');
    const premium = blockString(record, 'premium');
    const premiumSide = blockString(record, 'premium_side');
    basisLabel = `jambe longue 1 x ${right ?? 'sens non publié'} ${
      strike ?? 'strike non publié'
    } · ${expiration ?? 'échéance non publiée'} · ${
      tradingClass ?? 'classe non publiée'
    } — prime déclarée ${premium ?? 'non publiée'} (côté ${premiumSide ?? 'non publié'})`;
  }
  const rawGrid = block['grid'];
  const grid: string[][][] = [];
  if (Array.isArray(rawGrid)) {
    for (const scenario of rawGrid) {
      if (Array.isArray(scenario)) {
        grid.push(scenario.map((row: unknown) => stringGrid(row)));
      }
    }
  }
  const calculation = block['calculation'];
  const calcRecord =
    typeof calculation === 'object' && calculation !== null
      ? (calculation as Record<string, unknown>)
      : null;
  return {
    status: 'OK',
    reason: null,
    valueNature: blockString(block, 'value_nature'),
    basisLabel,
    spotGrid: stringGrid(block['spot_grid']),
    timeGridYears: stringGrid(block['time_grid_years']),
    grid,
    calculationId: calcRecord !== null ? blockString(calcRecord, 'calculation_id') : null,
    inputHash: calcRecord !== null ? blockString(calcRecord, 'input_hash') : null,
  };
}

/** Raisons typées d'absence de scénarios → phrase française. */
export const SCENARIO_ABSENT_REASONS_FR: Readonly<Record<string, string>> = {
  no_option_chain: 'aucune chaîne d’options publiée pour cet instrument',
  no_healthy_contract: 'aucun contrat sain (quote saine ET IV résolue) dans la chaîne publiée',
};

export function scenarioAbsentLabel(reason: string | null): string {
  if (reason === null) {
    return 'Scénarios absents — raison non publiée';
  }
  const explained = SCENARIO_ABSENT_REASONS_FR[reason];
  return explained === undefined
    ? `Scénarios absents — ${reason}`
    : `Scénarios absents — ${explained} (${reason})`;
}

// ---------------------------------------------------------------------------
// État d'affichage du cadre
// ---------------------------------------------------------------------------

export function analysisStateOf(
  queryState: DataState | 'auth-required',
  data: AnalysisResponse | undefined,
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
  if (data.state === 'stale') {
    return 'stale'; // statut de fraîcheur du relais, propriétaire de l'âge servi
  }
  if (data.population === 'DELAYED') {
    return 'delayed'; // nature publiée par le relais, jamais ramenée à ready
  }
  const bars = barsViewOf(data);
  if (bars === null || bars.status !== 'OK') {
    return 'partial'; // dossier publié sans série de barres exploitable
  }
  if (bars.fresh === false) {
    return 'stale'; // fraîcheur PUBLIÉE par le worker, jamais l'horloge locale
  }
  if (bars.discardedCount > 0 || bars.quality !== 'VALID') {
    return 'partial';
  }
  return queryState;
}
