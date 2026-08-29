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
import { getAttention, getCapabilities, isApiError } from './client.ts';
import type { AttentionSnapshot, SystemCapabilities } from './client.ts';

/** Ressources signalées par le flux SSE signal-only. */
export const SSE_RESOURCES = ['attention/global', 'capabilities/global'] as const;
export type SseResource = (typeof SSE_RESOURCES)[number];

export function queryKeyForResource(resource: SseResource): readonly [string, string] {
  return ['snapshot', resource] as const;
}

export function isKnownResource(resource: string): resource is SseResource {
  return (SSE_RESOURCES as readonly string[]).includes(resource);
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
