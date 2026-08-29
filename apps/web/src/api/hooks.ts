/**
 * Hooks TanStack Query des snapshots API + dérivation d'état d'affichage.
 *
 * Les clés de requête sont indexées par la ressource SSE (`<kind>/<key>`) :
 * l'abonnement `events.ts` invalide EXACTEMENT la clé de la ressource
 * signalée, jamais tout le cache. Aucune donnée n'est transformée ici : les
 * DTO de l'API arrivent tels quels jusqu'aux composants.
 */
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import type { DataState } from '../components/DataStateBoundary.tsx';
import {
  getAnalysis,
  getAttention,
  getCapabilities,
  getMarketsOverview,
  getOptionChain,
  isApiError,
} from './client.ts';
import type {
  AnalysisResponse,
  AttentionSnapshot,
  MarketsOverview,
  OptionChainResponse,
  SystemCapabilities,
} from './client.ts';

/** Ressources signalées par le flux SSE signal-only (têtes fixes). */
export const SSE_RESOURCES = [
  'attention/global',
  'capabilities/global',
  'markets_overview/global',
] as const;

/**
 * Familles de ressources signalées PAR PRÉFIXE : le serveur publie une clé
 * par instrument (`option_chain/SYN-…`, `analysis/SYN-…`). Le suivi par
 * préfixe reflète la sémantique serveur (`WATCHED_SNAPSHOT_KINDS`) : une clé
 * jamais interrogée localement n'a simplement aucun cache à invalider.
 */
export const SSE_RESOURCE_PREFIXES = ['option_chain/', 'analysis/'] as const;

export type SseResource = string;

export function queryKeyForResource(resource: SseResource): readonly [string, string] {
  return ['snapshot', resource] as const;
}

export function isKnownResource(resource: string): resource is SseResource {
  return (
    (SSE_RESOURCES as readonly string[]).includes(resource) ||
    SSE_RESOURCE_PREFIXES.some(
      (prefix) => resource.startsWith(prefix) && resource.length > prefix.length,
    )
  );
}

export function useAttention(): UseQueryResult<AttentionSnapshot> {
  return useQuery({
    queryKey: queryKeyForResource('attention/global'),
    queryFn: getAttention,
    retry: false,
    staleTime: Infinity, // l'invalidation vient du signal SSE, pas d'un timer local
  });
}

export function useCapabilities(): UseQueryResult<SystemCapabilities> {
  return useQuery({
    queryKey: queryKeyForResource('capabilities/global'),
    queryFn: getCapabilities,
    retry: false,
    staleTime: Infinity,
  });
}

export function useMarketsOverview(): UseQueryResult<MarketsOverview> {
  return useQuery({
    queryKey: queryKeyForResource('markets_overview/global'),
    queryFn: getMarketsOverview,
    retry: false,
    staleTime: Infinity,
  });
}

export function useOptionChain(underlying: string): UseQueryResult<OptionChainResponse> {
  return useQuery({
    queryKey: queryKeyForResource(`option_chain/${underlying}`),
    queryFn: () => getOptionChain(underlying),
    retry: false,
    staleTime: Infinity,
  });
}

export function useAnalysis(instrument: string): UseQueryResult<AnalysisResponse> {
  return useQuery({
    queryKey: queryKeyForResource(`analysis/${instrument}`),
    queryFn: () => getAnalysis(instrument),
    retry: false,
    staleTime: Infinity,
  });
}

/**
 * État de page dérivé du résultat de requête — 8 états canoniques + l'état
 * dédié « session requise ». Uniquement des faits observés : statut de la
 * requête et nature de l'erreur ; jamais l'horloge du navigateur.
 */
export type PageDataState = DataState | 'auth-required';

export function pageStateOf(query: UseQueryResult<unknown>): PageDataState {
  if (query.isPending) {
    return 'loading';
  }
  if (query.isError) {
    const error = query.error;
    if (isApiError(error)) {
      if (error.kind === 'AUTH_REQUIRED') {
        return 'auth-required';
      }
      if (error.kind === 'NETWORK') {
        return 'offline';
      }
    }
    return 'error';
  }
  if (query.isFetching) {
    return 'refreshing';
  }
  return 'ready';
}
