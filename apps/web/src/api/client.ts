/**
 * Client fetch typé de l'API locale Vertex One.
 *
 * - Base `/api` (proxy Vite en dev/preview vers 127.0.0.1:8000 ; jamais un
 *   hôte distant) ; `credentials: 'include'` sur chaque appel.
 * - Mutations (POST) : en-tête `X-Vertex-CSRF` recopié depuis le cookie
 *   lisible `vertex_csrf` (contrat double-submit du backend).
 * - Erreurs typées : un 401 devient `ApiError` de code `AUTH_REQUIRED`
 *   (réponse générique du serveur, aucune cause détaillée) ; un échec réseau
 *   devient `NETWORK` (état « hors ligne » côté interface, jamais un zéro).
 * - Ce module ne calcule rien : il transporte les DTO du contrat OpenAPI
 *   (types GÉNÉRÉS dans `schema.d.ts`) et expose l'état de session observé.
 */
import type { components } from './schema.d.ts';

export type AttentionSnapshot = components['schemas']['AttentionSnapshotResponse'];
export type AttentionItem = components['schemas']['AttentionItem'];
export type MarketsOverview = components['schemas']['MarketsOverviewResponse'];
export type MarketsSector = components['schemas']['MarketsSector'];
export type MarketsTicker = components['schemas']['MarketsTicker'];
export type MarketsBreadth = components['schemas']['MarketsBreadth'];
export type MarketsCoverage = components['schemas']['MarketsCoverage'];
export type SystemCapabilities = components['schemas']['SystemCapabilitiesResponse'];
export type CapabilityEntry = components['schemas']['CapabilityStatusEntry'];
export type SourceCapabilityStatus = components['schemas']['SourceCapabilityStatus'];
export type SystemHealth = components['schemas']['SystemHealth'];
export type CeremonyOptions = components['schemas']['CeremonyOptionsResponse'];
export type LoginVerifyRequest = components['schemas']['LoginVerifyRequest'];
export type LoginVerifyResponse = components['schemas']['LoginVerifyResponse'];
export type RegisterVerifyRequest = components['schemas']['RegisterVerifyRequest'];
export type RegisterVerifyResponse = components['schemas']['RegisterVerifyResponse'];
export type LogoutResponse = components['schemas']['LogoutResponse'];
export type OptionChainResponse = components['schemas']['OptionChainResponse'];
export type OptionChainExpiration = components['schemas']['OptionChainExpiration'];
export type OptionChainContract = components['schemas']['OptionChainContract'];
export type AnalysisResponse = components['schemas']['AnalysisResponse'];
export type SimulationPreviewRequest = components['schemas']['SimulationPreviewRequest'];
export type SimulationPreviewResponse = components['schemas']['SimulationPreviewResponse'];
export type SimulationOptionLeg = components['schemas']['OptionLeg'];
export type SimulationAssumptions = components['schemas']['SimulationAssumptions'];
export type SimulationBreakeven = components['schemas']['SimulationBreakeven'];
export type SimulationExtreme = components['schemas']['SimulationExtreme'];
export type SimulationPayoffPoint = components['schemas']['SimulationPayoffPoint'];
export type PortfolioResponse = components['schemas']['PortfolioResponse'];
export type PortfolioInfo = components['schemas']['PortfolioInfo'];
export type PortfolioLotEntry = components['schemas']['PortfolioLotEntry'];
export type PortfolioValuationView = components['schemas']['PortfolioValuationView'];
export type LedgerTransactionEntry = components['schemas']['LedgerTransactionEntry'];
export type LedgerEventKind = components['schemas']['LedgerEventKind'];
export type RecordTransactionRequest = components['schemas']['RecordTransactionRequest'];
export type RecordTransactionResponse = components['schemas']['RecordTransactionResponse'];
export type CompensateTransactionRequest = components['schemas']['CompensateTransactionRequest'];
export type CompensateTransactionResponse = components['schemas']['CompensateTransactionResponse'];
export type CsvImportPreviewRequest = components['schemas']['CsvImportPreviewRequest'];
export type ImportPreviewResponse = components['schemas']['ImportPreviewResponse'];
export type ImportRowEcho = components['schemas']['ImportRowEcho'];
export type ImportRowError = components['schemas']['ImportRowError'];
export type ImportRowDuplicate = components['schemas']['ImportRowDuplicate'];
export type ImportConfirmRequest = components['schemas']['ImportConfirmRequest'];
export type ImportConfirmResponse = components['schemas']['ImportConfirmResponse'];
export type FollowUpQueueResponse = components['schemas']['FollowUpQueueResponse'];
export type CreateThesisRequest = components['schemas']['CreateThesisRequest'];
export type CreateThesisResponse = components['schemas']['CreateThesisResponse'];
export type ThesisRevisionRequest = components['schemas']['ThesisRevisionRequest'];
export type ThesisRevisionResponse = components['schemas']['ThesisRevisionResponse'];
export type PerformanceSnapshotResponse = components['schemas']['PerformanceSnapshotResponse'];
export type CalendarResponse = components['schemas']['CalendarResponse'];
export type CalendarWindowEcho = components['schemas']['CalendarWindow'];
export type OpportunitiesResponse = components['schemas']['OpportunitiesResponse'];
export type RiskMatrixResponse = components['schemas']['RiskMatrixResponse'];
export type AiAnswer = components['schemas']['AiAnswer'];
export type AiClaim = components['schemas']['AiClaim'];
export type AiContradiction = components['schemas']['AiContradiction'];
export type AiEvidenceCatalogEntry = components['schemas']['AiEvidenceCatalogEntry'];
export type AiExternalExcerpt = components['schemas']['AiExternalExcerpt'];
export type AiExplainRequest = components['schemas']['AiExplainRequest'];
export type AiStatusResponse = components['schemas']['AiStatusResponse'];
export type AiSubject = components['schemas']['AiSubject'];
export type PerformanceExportResponse = components['schemas']['PerformanceExportResponse'];

export const API_BASE = '/api';

export const CSRF_COOKIE_NAME = 'vertex_csrf';
export const CSRF_HEADER_NAME = 'X-Vertex-CSRF';

/** Codes d'erreur du client — jamais un détail serveur inventé. */
export type ApiErrorKind = 'AUTH_REQUIRED' | 'HTTP' | 'NETWORK' | 'INVALID_BODY';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  /**
   * Corps JSON de la réponse d'erreur, RELAYÉ verbatim quand le serveur en a
   * fourni un (ex. 422 : `{"detail": {"code": ..., "message": ...}}` ou la
   * liste d'erreurs de validation). `undefined` si absent ou illisible —
   * jamais un détail fabriqué côté client.
   */
  readonly detail?: unknown;

  constructor(
    kind: ApiErrorKind,
    message: string,
    status: number | null = null,
    detail?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    if (detail !== undefined) {
      this.detail = detail;
    }
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

// ---------------------------------------------------------------------------
// État de session observé (jamais deviné) : il ne change qu'au vu d'une
// réponse réelle de l'API — succès d'une route protégée, 401, login, logout.
// ---------------------------------------------------------------------------

export type SessionState = 'unknown' | 'authenticated' | 'unauthenticated';

type Listener = () => void;

let sessionState: SessionState = 'unknown';
const sessionListeners = new Set<Listener>();

function setSessionState(next: SessionState): void {
  if (next === sessionState) {
    return;
  }
  sessionState = next;
  for (const listener of sessionListeners) {
    listener();
  }
}

export const sessionStore = {
  getState(): SessionState {
    return sessionState;
  },
  subscribe(listener: Listener): () => void {
    sessionListeners.add(listener);
    return () => {
      sessionListeners.delete(listener);
    };
  },
  /** Réinitialisation explicite (tests et logout). */
  reset(): void {
    setSessionState('unknown');
  },
};

// ---------------------------------------------------------------------------
// Transport
// ---------------------------------------------------------------------------

/** Lit le cookie CSRF lisible ; `null` s'il est absent (session inexistante). */
export function readCsrfCookie(): string | null {
  const cookies = typeof document === 'undefined' ? '' : document.cookie;
  for (const part of cookies.split(';')) {
    const [name, ...rest] = part.trim().split('=');
    if (name === CSRF_COOKIE_NAME) {
      const value = rest.join('=');
      return value === '' ? null : decodeURIComponent(value);
    }
  }
  return null;
}

export interface RequestSpec {
  readonly method: 'GET' | 'POST';
  readonly path: string;
  readonly body?: unknown;
  /** Route derrière la session : son succès prouve une session active. */
  readonly protectedRoute: boolean;
}

/**
 * Transport partagé, EXPORTÉ pour les modules de routes chargés paresseusement
 * (vague 4 : `portfolioApi.ts`, hors bundle initial). Un seul transport, une
 * seule discipline CSRF/session — jamais un second client concurrent.
 */
export async function request<T>(spec: RequestSpec): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const init: RequestInit = {
    method: spec.method,
    credentials: 'include',
    headers,
  };
  if (spec.method !== 'GET') {
    const csrf = readCsrfCookie();
    if (csrf !== null) {
      headers[CSRF_HEADER_NAME] = csrf;
    }
    if (spec.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(spec.body);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${spec.path}`, init);
  } catch {
    throw new ApiError('NETWORK', 'network unreachable');
  }

  if (response.status === 401) {
    setSessionState('unauthenticated');
    throw new ApiError('AUTH_REQUIRED', 'authentication required', 401);
  }
  if (!response.ok) {
    // Le corps d'erreur du serveur (s'il existe et se lit) est conservé
    // verbatim sur l'erreur : une page peut afficher la raison EXACTE d'un
    // 422 sans jamais l'inventer. Un corps illisible reste `undefined`.
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = undefined;
    }
    throw new ApiError('HTTP', `unexpected status ${response.status}`, response.status, detail);
  }
  if (spec.protectedRoute) {
    setSessionState('authenticated');
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError('INVALID_BODY', 'response body is not valid JSON', response.status);
  }
}

// ---------------------------------------------------------------------------
// Routes typées (contrat OpenAPI ; aucun second modèle manuel)
// ---------------------------------------------------------------------------

export function getAttention(): Promise<AttentionSnapshot> {
  return request({ method: 'GET', path: '/v1/today/attention', protectedRoute: true });
}

export function getCapabilities(): Promise<SystemCapabilities> {
  return request({ method: 'GET', path: '/v1/system/capabilities', protectedRoute: true });
}

export function getMarketsOverview(): Promise<MarketsOverview> {
  return request({ method: 'GET', path: '/v1/markets/overview', protectedRoute: true });
}

export function getOptionChain(underlying: string): Promise<OptionChainResponse> {
  return request({
    method: 'GET',
    path: `/v1/options/${encodeURIComponent(underlying)}/chain`,
    protectedRoute: true,
  });
}

export function getAnalysis(instrument: string): Promise<AnalysisResponse> {
  return request({
    method: 'GET',
    path: `/v1/analysis/${encodeURIComponent(instrument)}`,
    protectedRoute: true,
  });
}

/**
 * Prévisualisation THÉORIQUE d'une structure déclarée — analyse uniquement,
 * rien n'est persisté ni transmis à un courtier ; le serveur calcule tout.
 * L'en-tête CSRF double-submit est posé par `request` (mutation POST).
 */
export function postSimulationPreview(
  body: SimulationPreviewRequest,
): Promise<SimulationPreviewResponse> {
  return request({
    method: 'POST',
    path: '/v1/simulations/preview',
    body,
    protectedRoute: true,
  });
}

export function postRegisterOptions(): Promise<CeremonyOptions> {
  return request({ method: 'POST', path: '/v1/auth/register/options', protectedRoute: false });
}

export function postRegisterVerify(body: RegisterVerifyRequest): Promise<RegisterVerifyResponse> {
  return request({
    method: 'POST',
    path: '/v1/auth/register/verify',
    body,
    protectedRoute: false,
  });
}

export function postLoginOptions(): Promise<CeremonyOptions> {
  return request({ method: 'POST', path: '/v1/auth/login/options', protectedRoute: false });
}

export async function postLoginVerify(body: LoginVerifyRequest): Promise<LoginVerifyResponse> {
  const result = await request<LoginVerifyResponse>({
    method: 'POST',
    path: '/v1/auth/login/verify',
    body,
    protectedRoute: false,
  });
  // Réponse 200 avec cookies posés par le serveur : session réellement ouverte.
  setSessionState('authenticated');
  return result;
}

export async function postLogout(): Promise<LogoutResponse> {
  const result = await request<LogoutResponse>({
    method: 'POST',
    path: '/v1/auth/logout',
    protectedRoute: false,
  });
  setSessionState('unauthenticated');
  return result;
}
