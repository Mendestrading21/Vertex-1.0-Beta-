/**
 * Routes et hooks de la vague 4 (portefeuille, suivi, performance).
 *
 * Module SÉPARÉ de `client.ts`/`hooks.ts` À DESSEIN : il n'est importé que
 * par les trois pages chargées paresseusement, donc il vit dans leurs chunks
 * et ne grossit pas le bundle initial (budget « bundle initial inchangé »).
 * Le transport reste UNIQUE (`request` de client.ts : CSRF double-submit,
 * erreurs typées, état de session observé) — aucun second client concurrent.
 *
 * Sémantique de JOURNAL : chaque écriture enregistre un FAIT PASSÉ déjà
 * survenu hors Vertex ; rien ici n'est une instruction ni un ticket
 * transmissible, et le serveur n'a aucune capacité de transmission.
 */
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { API_BASE, ApiError, request } from './client.ts';
import type {
  CompensateTransactionRequest,
  CompensateTransactionResponse,
  CreateThesisRequest,
  CreateThesisResponse,
  CsvImportPreviewRequest,
  FollowUpQueueResponse,
  ImportConfirmRequest,
  ImportConfirmResponse,
  ImportPreviewResponse,
  PerformanceExportResponse,
  PerformanceSnapshotResponse,
  PortfolioResponse,
  RecordTransactionRequest,
  RecordTransactionResponse,
  ThesisRevisionRequest,
  ThesisRevisionResponse,
} from './client.ts';
import { queryKeyForResource } from './hooks.ts';

export function getPortfolio(): Promise<PortfolioResponse> {
  return request({ method: 'GET', path: '/v1/portfolio', protectedRoute: true });
}

/**
 * Export CSV du journal — corps `text/csv` du serveur, relayé TEL QUEL
 * (l'en-tête de version et la neutralisation tableur viennent du serveur).
 * Chemin texte dédié : `request` ne transporte que du JSON.
 */
export async function getPortfolioExportCsv(): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/portfolio/export`, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'text/csv' },
    });
  } catch {
    throw new ApiError('NETWORK', 'network unreachable');
  }
  if (response.status === 401) {
    throw new ApiError('AUTH_REQUIRED', 'authentication required', 401);
  }
  if (!response.ok) {
    throw new ApiError('HTTP', `unexpected status ${response.status}`, response.status);
  }
  return response.text();
}

/** Enregistre UN fait passé déjà survenu hors Vertex (journal append-only). */
export function postTransaction(
  body: RecordTransactionRequest,
): Promise<RecordTransactionResponse> {
  return request({ method: 'POST', path: '/v1/portfolio/transactions', body, protectedRoute: true });
}

/** Ajoute la ligne compensatoire d'un fait enregistré (jamais une édition). */
export function postCompensation(
  transactionId: number,
  body: CompensateTransactionRequest,
): Promise<CompensateTransactionResponse> {
  return request({
    method: 'POST',
    path: `/v1/portfolio/transactions/${encodeURIComponent(String(transactionId))}/compensate`,
    body,
    protectedRoute: true,
  });
}

/** Prévisualisation typée d'un import CSV — AUCUNE écriture. */
export function postImportPreview(body: CsvImportPreviewRequest): Promise<ImportPreviewResponse> {
  return request({ method: 'POST', path: '/v1/portfolio/import/preview', body, protectedRoute: true });
}

/** Confirme l'import : écho INTACT de la prévisualisation, hash inclus. */
export function postImportConfirm(body: ImportConfirmRequest): Promise<ImportConfirmResponse> {
  return request({ method: 'POST', path: '/v1/portfolio/import/confirm', body, protectedRoute: true });
}

export function getFollowUpQueue(): Promise<FollowUpQueueResponse> {
  return request({ method: 'GET', path: '/v1/follow-up/queue', protectedRoute: true });
}

/** Nouvelle thèse (invalidation obligatoire, idempotency_key du client). */
export function postThesis(body: CreateThesisRequest): Promise<CreateThesisResponse> {
  return request({ method: 'POST', path: '/v1/theses', body, protectedRoute: true });
}

/** Révision append-only d'une thèse (rejouable via la même idempotency_key). */
export function postThesisRevision(
  thesisId: number,
  body: ThesisRevisionRequest,
): Promise<ThesisRevisionResponse> {
  return request({
    method: 'POST',
    path: `/v1/theses/${encodeURIComponent(String(thesisId))}/revisions`,
    body,
    protectedRoute: true,
  });
}

export function getPerformance(portfolioId: number): Promise<PerformanceSnapshotResponse> {
  return request({
    method: 'GET',
    path: `/v1/performance/${encodeURIComponent(String(portfolioId))}`,
    protectedRoute: true,
  });
}

/** Export reproductible : CSV des points + manifeste d'audit JSON. */
export function getPerformanceExport(portfolioId: number): Promise<PerformanceExportResponse> {
  return request({
    method: 'GET',
    path: `/v1/performance/${encodeURIComponent(String(portfolioId))}/export`,
    protectedRoute: true,
  });
}

// ---------------------------------------------------------------------------
// Hooks TanStack Query — clés alignées sur les ressources SSE (hooks.ts).
// ---------------------------------------------------------------------------

export function usePortfolio(): UseQueryResult<PortfolioResponse> {
  return useQuery({
    // Clé UNIQUE du portefeuille : tout signal `portfolio_valuation/<id>` du
    // flux SSE se traduit vers elle (voir queryKeyForResource).
    queryKey: queryKeyForResource('portfolio_valuation/any'),
    queryFn: getPortfolio,
    retry: false,
    staleTime: Infinity,
  });
}

export function useFollowUpQueue(): UseQueryResult<FollowUpQueueResponse> {
  return useQuery({
    queryKey: queryKeyForResource('review_queue/global'),
    queryFn: getFollowUpQueue,
    retry: false,
    staleTime: Infinity,
  });
}

export function usePerformance(
  portfolioId: number | null,
): UseQueryResult<PerformanceSnapshotResponse> {
  return useQuery({
    queryKey: queryKeyForResource(`performance/${portfolioId ?? 'unknown'}`),
    queryFn: () => {
      if (portfolioId === null) {
        throw new Error('portfolioId is null while the query is enabled');
      }
      return getPerformance(portfolioId);
    },
    enabled: portfolioId !== null,
    retry: false,
    staleTime: Infinity,
  });
}
