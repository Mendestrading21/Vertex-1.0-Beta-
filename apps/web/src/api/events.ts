/**
 * Abonnement au flux SSE signal-only `/api/v1/events/stream`.
 *
 * Chaque événement `snapshot` vaut exactement `{resource, version}` : aucun
 * contenu métier ne transite. À réception, la clé de requête de la ressource
 * signalée est invalidée de façon CIBLÉE (`['snapshot', resource]`) et le
 * client refait son GET REST — le flux ne porte jamais la donnée.
 *
 * Reconnexion : backoff exponentiel borné (1 s → 30 s). L'état de connexion
 * est exposé via un petit store à abonnement (affichage honnête « flux
 * connecté / reconnexion / arrêté », jamais un état simulé).
 */
import type { QueryClient } from '@tanstack/react-query';

import { isKnownResource, queryKeyForResource } from './hooks.ts';
import { sessionStore } from './client.ts';

export type SseConnectionState = 'connecting' | 'open' | 'retrying' | 'stopped';

/** Sous-ensemble d'EventSource utilisé (injectable en test). */
export interface EventSourceLike {
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void;
  close(): void;
  onopen: ((event: Event) => void) | null;
  onerror: ((event: Event) => void) | null;
}

export interface SnapshotEventsOptions {
  readonly createEventSource?: (url: string) => EventSourceLike;
  readonly baseDelayMs?: number;
  readonly maxDelayMs?: number;
}

export interface SnapshotEventsHandle {
  readonly getState: () => SseConnectionState;
  readonly subscribe: (listener: () => void) => () => void;
  readonly stop: () => void;
}

export const EVENTS_STREAM_URL = '/api/v1/events/stream';

function defaultCreateEventSource(url: string): EventSourceLike {
  return new EventSource(url, { withCredentials: true });
}

export function startSnapshotEvents(
  queryClient: QueryClient,
  options: SnapshotEventsOptions = {},
): SnapshotEventsHandle {
  const createEventSource = options.createEventSource ?? defaultCreateEventSource;
  const baseDelayMs = options.baseDelayMs ?? 1000;
  const maxDelayMs = options.maxDelayMs ?? 30000;

  let state: SseConnectionState = 'connecting';
  let attempts = 0;
  let source: EventSourceLike | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;
  const listeners = new Set<() => void>();

  function setState(next: SseConnectionState): void {
    if (next === state) {
      return;
    }
    state = next;
    for (const listener of listeners) {
      listener();
    }
  }

  function onSnapshotEvent(event: MessageEvent<string>): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(event.data);
    } catch {
      return; // trame inconnue : ignorée, jamais interprétée
    }
    if (typeof parsed !== 'object' || parsed === null) {
      return;
    }
    const resource = (parsed as { resource?: unknown }).resource;
    if (typeof resource !== 'string' || !isKnownResource(resource)) {
      return; // ressource non suivie : aucune invalidation globale
    }
    void queryClient.invalidateQueries({ queryKey: queryKeyForResource(resource) });
  }

  function connect(): void {
    if (stopped) {
      return;
    }
    setState(attempts === 0 ? 'connecting' : 'retrying');
    const next = createEventSource(EVENTS_STREAM_URL);
    source = next;
    next.addEventListener('snapshot', onSnapshotEvent);
    next.onopen = () => {
      attempts = 0;
      setState('open');
    };
    next.onerror = () => {
      next.close();
      if (source === next) {
        source = null;
      }
      if (stopped) {
        return;
      }
      const delay = Math.min(baseDelayMs * 2 ** attempts, maxDelayMs);
      attempts += 1;
      setState('retrying');
      retryTimer = setTimeout(connect, delay);
    };
  }

  connect();

  return {
    getState: () => state,
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    stop: () => {
      stopped = true;
      if (retryTimer !== null) {
        clearTimeout(retryTimer);
        retryTimer = null;
      }
      source?.close();
      source = null;
      setState('stopped');
    },
  };
}

// ---------------------------------------------------------------------------
// Câblage applicatif : le flux ne vit que pendant une session authentifiée
// (sans session, le serveur répond 401 ; boucler dessus serait malhonnête).
// ---------------------------------------------------------------------------

let activeHandle: SnapshotEventsHandle | null = null;
const stateListeners = new Set<() => void>();
let detachHandleListener: (() => void) | null = null;

function notifyStateListeners(): void {
  for (const listener of stateListeners) {
    listener();
  }
}

/** Store de l'état du flux pour l'interface (useSyncExternalStore). */
export const sseStateStore = {
  getState(): SseConnectionState {
    return activeHandle === null ? 'stopped' : activeHandle.getState();
  },
  subscribe(listener: () => void): () => void {
    stateListeners.add(listener);
    return () => {
      stateListeners.delete(listener);
    };
  },
};

/**
 * Démarre/arrête l'abonnement SSE selon l'état de session observé.
 * Retourne une fonction d'arrêt globale (tests, démontage).
 */
export function installSnapshotEvents(
  queryClient: QueryClient,
  options: SnapshotEventsOptions = {},
): () => void {
  function sync(): void {
    const authenticated = sessionStore.getState() === 'authenticated';
    if (authenticated && activeHandle === null) {
      activeHandle = startSnapshotEvents(queryClient, options);
      detachHandleListener = activeHandle.subscribe(notifyStateListeners);
    } else if (!authenticated && activeHandle !== null) {
      detachHandleListener?.();
      detachHandleListener = null;
      activeHandle.stop();
      activeHandle = null;
    }
    notifyStateListeners();
  }

  const unsubscribe = sessionStore.subscribe(sync);
  sync();
  return () => {
    unsubscribe();
    detachHandleListener?.();
    detachHandleListener = null;
    activeHandle?.stop();
    activeHandle = null;
    notifyStateListeners();
  };
}
