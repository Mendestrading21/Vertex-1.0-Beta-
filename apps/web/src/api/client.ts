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

const API_BASE = '/api';

export const CSRF_COOKIE_NAME = 'vertex_csrf';
export const CSRF_HEADER_NAME = 'X-Vertex-CSRF';

/** Codes d'erreur du client — jamais un détail serveur inventé. */
export type ApiErrorKind = 'AUTH_REQUIRED' | 'HTTP' | 'NETWORK' | 'INVALID_BODY';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;

  constructor(kind: ApiErrorKind, message: string, status: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
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

interface RequestSpec {
  readonly method: 'GET' | 'POST';
  readonly path: string;
  readonly body?: unknown;
  /** Route derrière la session : son succès prouve une session active. */
  readonly protectedRoute: boolean;
}

async function request<T>(spec: RequestSpec): Promise<T> {
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
    throw new ApiError('HTTP', `unexpected status ${response.status}`, response.status);
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
