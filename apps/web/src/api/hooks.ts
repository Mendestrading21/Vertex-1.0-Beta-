/**
 * Hooks TanStack Query des snapshots API + dérivation d'état d'affichage.
 *
 * Les clés de requête sont indexées par la ressource SSE (`<kind>/<key>`) :
 * l'abonnement `events.ts` invalide EXACTEMENT la clé de la ressource
 * signalée, jamais tout le cache. Aucune donnée n'est transformée ici : les
 * DTO de l'API arrivent tels quels jusqu'aux composants.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import { useCallback, useRef, useSyncExternalStore } from 'react';

import type { DataState } from '../components/DataStateBoundary.tsx';
import {
  getAnalysis,
  getAttention,
  getCapabilities,
  getMarketsOverview,
  getOptionChain,
  getSecFundamentals,
  isApiError,
} from './client.ts';
import type {
  AnalysisResponse,
  AttentionSnapshot,
  MarketsOverview,
  OptionChainResponse,
  SecFundamentalsResponse,
  SystemCapabilities,
} from './client.ts';

/** Ressources signalées par le flux SSE signal-only (têtes fixes). */
export const SSE_RESOURCES = [
  'attention/global',
  'calendar/global',
  'capabilities/global',
  'markets_overview/global',
  'opportunities/global',
  'review_queue/global',
] as const;

/**
 * Familles de ressources signalées PAR PRÉFIXE : le serveur publie une clé
 * par instrument (`option_chain/SYN-…`, `analysis/SYN-…`) ou par portefeuille
 * (`portfolio_valuation/1`, `performance/1`). Le suivi par préfixe reflète la
 * sémantique serveur (`WATCHED_SNAPSHOT_KINDS`) : une clé jamais interrogée
 * localement n'a simplement aucun cache à invalider.
 */
export const SSE_RESOURCE_PREFIXES = [
  'option_chain/',
  'analysis/',
  'portfolio_valuation/',
  'performance/',
  // LOT-A4 : la route SEC est relayée par Analyse ; le serveur signale
  // `sec_fundamentals/<instrument>` (`WATCHED_SNAPSHOT_KINDS`).
  'sec_fundamentals/',
] as const;

export type SseResource = string;

export function queryKeyForResource(resource: SseResource): readonly [string, string] {
  // La valorisation vit DANS la réponse GET /portfolio — route sans identifiant
  // côté client) : tout signal `portfolio_valuation/<id>` invalide donc la
  // clé unique du portefeuille. Aucune autre traduction n'existe.
  if (resource.startsWith('portfolio_valuation/')) {
    return ['snapshot', 'portfolio'] as const;
  }
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

export function useSecFundamentals(instrument: string): UseQueryResult<SecFundamentalsResponse> {
  return useQuery({
    queryKey: queryKeyForResource(`sec_fundamentals/${instrument}`),
    queryFn: () => getSecFundamentals(instrument),
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

// ---------------------------------------------------------------------------
// Métadonnées SERVIES d'un snapshot, lues dans le cache — lot L0.
// ---------------------------------------------------------------------------

export type SnapshotMetaError = 'AUTH_REQUIRED' | 'NETWORK' | 'OTHER';

/**
 * Ce que le SERVEUR a publié avec la réponse, plus l'état de la requête.
 *
 * AUCUNE EXTRAPOLATION. `ageSeconds` est l'âge calculé par le backend au
 * moment de la réponse ; il ne vieillit pas entre deux réponses et n'est
 * jamais corrigé par l'horloge du navigateur (`FreshnessBadge` fige déjà cet
 * âge, `docs/05-design/UI_STATES.md`). Un champ que l'API ne publie pas vaut
 * `null` — jamais zéro.
 */
export interface SnapshotMeta {
  readonly ageSeconds: number | null;
  readonly asOf: string | null;
  readonly state: string | null;
  readonly population: string | null;
  readonly snapshotVersion: number | null;
  readonly fetchStatus: 'idle' | 'fetching' | 'paused';
  readonly error: SnapshotMetaError | null;
  /** Une réponse a-t-elle été vue pour cette clé ? */
  readonly present: boolean;
}

export const ABSENT_SNAPSHOT_META: SnapshotMeta = {
  ageSeconds: null,
  asOf: null,
  state: null,
  population: null,
  snapshotVersion: null,
  fetchStatus: 'idle',
  error: null,
  present: false,
};

function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function readNumber(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** Traduit un état de requête en métadonnées SERVIES. Fonction pure, testable. */
export function snapshotMetaOf(
  data: unknown,
  status: { readonly fetchStatus: 'idle' | 'fetching' | 'paused'; readonly error: unknown },
): SnapshotMeta {
  const error = isApiError(status.error)
    ? status.error.kind === 'AUTH_REQUIRED'
      ? 'AUTH_REQUIRED'
      : status.error.kind === 'NETWORK'
        ? 'NETWORK'
        : 'OTHER'
    : status.error === null || status.error === undefined
      ? null
      : 'OTHER';

  if (typeof data !== 'object' || data === null) {
    return { ...ABSENT_SNAPSHOT_META, fetchStatus: status.fetchStatus, error };
  }
  const source = data as Record<string, unknown>;
  return {
    ageSeconds: readNumber(source, 'age_seconds'),
    asOf: readString(source, 'as_of'),
    state: readString(source, 'state'),
    population: readString(source, 'population'),
    snapshotVersion: readNumber(source, 'snapshot_version'),
    fetchStatus: status.fetchStatus,
    error,
    present: true,
  };
}

/**
 * Métadonnées servies d'une clé de cache, SANS requête supplémentaire.
 *
 * Aucun `queryFn` : ce hook OBSERVE le cache (`useSyncExternalStore` sur
 * `QueryCache.subscribe`). Il ne déclenche donc jamais de fetch et ne peut pas
 * faire diverger deux lecteurs de la même donnée. L'instantané rendu est
 * mémorisé : `useSyncExternalStore` compare par identité et bouclerait sur un
 * objet neuf à chaque appel.
 */
export function useSnapshotMeta(queryKey: readonly [string, string]): SnapshotMeta {
  const queryClient = useQueryClient();
  const cacheKey = queryKey.join(' ');
  const memo = useRef<{ signature: string; meta: SnapshotMeta } | null>(null);

  const subscribe = useCallback(
    (listener: () => void) => queryClient.getQueryCache().subscribe(listener),
    [queryClient],
  );

  const getSnapshot = useCallback((): SnapshotMeta => {
    const state = queryClient.getQueryState(cacheKey.split(' '));
    const meta =
      state === undefined
        ? ABSENT_SNAPSHOT_META
        : snapshotMetaOf(state.data, { fetchStatus: state.fetchStatus, error: state.error });
    const signature = JSON.stringify(meta);
    if (memo.current === null || memo.current.signature !== signature) {
      memo.current = { signature, meta };
    }
    return memo.current.meta;
  }, [queryClient, cacheKey]);

  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
