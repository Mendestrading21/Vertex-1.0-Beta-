/**
 * Routes et hooks de la vague finale (Calendrier, Opportunités, Vertex IA).
 *
 * Module SÉPARÉ de `client.ts`/`hooks.ts` À DESSEIN, comme `portfolioApi.ts` :
 * il n'est importé que par les trois pages chargées paresseusement, donc il
 * vit dans leurs chunks et ne grossit pas le bundle initial. Le transport
 * reste UNIQUE (`request` de client.ts : CSRF double-submit, erreurs typées,
 * état de session observé) — aucun second client concurrent.
 *
 * Aucune transformation ici : les DTO du contrat OpenAPI arrivent tels quels
 * jusqu'aux composants, y compris les états honnêtes `not_entitled`,
 * `rejected`, `empty` et le refus structuré de l'explication déterministe.
 */
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { request } from './client.ts';
import type {
  AiAnswer,
  AiExplainRequest,
  AiStatusResponse,
  CalendarResponse,
  OpportunitiesResponse,
} from './client.ts';
import { queryKeyForResource } from './hooks.ts';

/**
 * Fenêtre d'affichage `from`/`to` — chaînes RELAYÉES telles quelles.
 *
 * Une borne absente reste ABSENTE de la requête (elle n'est jamais complétée
 * ni remplacée par une chaîne vide) : c'est ainsi que le serveur peut rendre
 * son refus typé `WINDOW_INCOMPLETE` au lieu d'un refus de validation générique.
 */
export interface CalendarWindowQuery {
  readonly from: string;
  readonly to: string;
}

/** Chaîne de requête de la fenêtre : seules les bornes RÉELLEMENT saisies. */
export function calendarWindowQueryString(window: CalendarWindowQuery | null): string {
  if (window === null) {
    return '';
  }
  const params = new URLSearchParams();
  if (window.from !== '') {
    params.set('from', window.from);
  }
  if (window.to !== '') {
    params.set('to', window.to);
  }
  const query = params.toString();
  return query === '' ? '' : `?${query}`;
}

/**
 * Snapshot calendrier. La fenêtre est transmise VERBATIM : c'est le serveur
 * qui la valide (fenêtre incomplète, naïve, inversée ou trop large — 4 refus
 * typés 422) et l'interface n'en corrige aucune.
 */
export function getCalendar(window: CalendarWindowQuery | null): Promise<CalendarResponse> {
  return request({
    method: 'GET',
    path: `/v1/calendar${calendarWindowQueryString(window)}`,
    protectedRoute: true,
  });
}

export function getOpportunities(): Promise<OpportunitiesResponse> {
  return request({ method: 'GET', path: '/v1/opportunities', protectedRoute: true });
}

export function getAiStatus(): Promise<AiStatusResponse> {
  return request({ method: 'GET', path: '/v1/ai/status', protectedRoute: true });
}

/** Explication d'UN snapshot persisté par le gabarit déterministe. */
export function postAiExplain(body: AiExplainRequest): Promise<AiAnswer> {
  return request({ method: 'POST', path: '/v1/ai/explain', body, protectedRoute: true });
}

/**
 * La clé de requête PRÉFIXE toujours `['snapshot', 'calendar/global']` : le
 * signal SSE de la ressource invalide donc aussi les variantes fenêtrées
 * (invalidation par préfixe de TanStack Query), sans qu'aucune fenêtre ne
 * soit inventée côté client.
 */
export function useCalendar(window: CalendarWindowQuery | null): UseQueryResult<CalendarResponse> {
  return useQuery({
    queryKey: [
      ...queryKeyForResource('calendar/global'),
      window === null ? '' : window.from,
      window === null ? '' : window.to,
    ] as const,
    queryFn: () => getCalendar(window),
    retry: false,
    staleTime: Infinity,
  });
}

export function useOpportunities(): UseQueryResult<OpportunitiesResponse> {
  return useQuery({
    queryKey: queryKeyForResource('opportunities/global'),
    queryFn: getOpportunities,
    retry: false,
    staleTime: Infinity,
  });
}

export function useAiStatus(): UseQueryResult<AiStatusResponse> {
  return useQuery({
    queryKey: ['ai', 'status'] as const,
    queryFn: getAiStatus,
    retry: false,
    staleTime: Infinity,
  });
}
