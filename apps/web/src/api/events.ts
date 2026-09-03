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
 * connecté / reconnexion / silence / arrêté », jamais un état simulé).
 *
 * SILENCE ET REPLI (lot L0). Le serveur émet un `ping` toutes les 15 s : un
 * `EventSource` peut rester « ouvert » alors que plus rien n'arrive. Trois
 * pings manqués (45 s sans AUCUNE trame, `ping` compris) valent SILENCE, et le
 * client bascule en repli par SONDAGE : une invalidation des requêtes ACTIVES
 * toutes les 30 s, arrêtée dès qu'une trame revient. Le temps mesuré ici est
 * celui du TRANSPORT (`performance.now()`), jamais une horloge de donnée : la
 * fraîcheur affichée reste l'`age_seconds` SERVI par l'API.
 */
import type { QueryClient } from '@tanstack/react-query';

import { isKnownResource, queryKeyForResource } from './hooks.ts';
import { sessionStore } from './client.ts';

/** État du LIEN de signalement. `silent` : ouvert mais muet depuis 45 s. */
export type SseLinkState = 'connecting' | 'open' | 'retrying' | 'silent' | 'stopped';

/** Alias historique — les consommateurs installés l'utilisent déjà. */
export type SseConnectionState = SseLinkState;

/** Comment les invalidations arrivent RÉELLEMENT au cache. */
export type SseLinkMode = 'signal' | 'sondage' | 'aucun';

/** Trois pings manqués (15 s chacun). */
export const SILENCE_MS = 45_000;
/** Cadence du repli par sondage, requêtes ACTIVES seulement. */
export const POLL_INTERVAL_MS = 30_000;

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
  readonly silenceMs?: number;
  readonly pollIntervalMs?: number;
  /** Horloge de TRANSPORT injectable (jamais une horloge de donnée). */
  readonly now?: () => number;
}

export interface SnapshotEventsHandle {
  readonly getState: () => SseLinkState;
  readonly getMode: () => SseLinkMode;
  /** Millisecondes de transport depuis la dernière trame reçue. */
  readonly getSilenceMs: () => number;
  readonly subscribe: (listener: () => void) => () => void;
  readonly stop: () => void;
}

export const EVENTS_STREAM_URL = '/api/v1/events/stream';

function defaultCreateEventSource(url: string): EventSourceLike {
  return new EventSource(url, { withCredentials: true });
}

function defaultNow(): number {
  return typeof performance === 'undefined' ? 0 : performance.now();
}

export function startSnapshotEvents(
  queryClient: QueryClient,
  options: SnapshotEventsOptions = {},
): SnapshotEventsHandle {
  const createEventSource = options.createEventSource ?? defaultCreateEventSource;
  const baseDelayMs = options.baseDelayMs ?? 1000;
  const maxDelayMs = options.maxDelayMs ?? 30000;
  const silenceMs = options.silenceMs ?? SILENCE_MS;
  const pollIntervalMs = options.pollIntervalMs ?? POLL_INTERVAL_MS;
  const now = options.now ?? defaultNow;

  let state: SseLinkState = 'connecting';
  let attempts = 0;
  let source: EventSourceLike | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let silenceTimer: ReturnType<typeof setTimeout> | null = null;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let lastFrameAt = now();
  let stopped = false;
  const listeners = new Set<() => void>();

  function notify(): void {
    for (const listener of listeners) {
      listener();
    }
  }

  function modeOf(): SseLinkMode {
    if (stopped || state === 'stopped') {
      return 'aucun';
    }
    return pollTimer === null ? 'signal' : 'sondage';
  }

  function stopPolling(): void {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function startPolling(): void {
    if (pollTimer !== null || stopped) {
      return;
    }
    pollTimer = setInterval(() => {
      // Requêtes ACTIVES seulement : un cache que personne ne regarde n'a pas
      // besoin d'être rafraîchi, et un refetch global masquerait le silence.
      void queryClient.invalidateQueries({ queryKey: ['snapshot'], refetchType: 'active' });
    }, pollIntervalMs);
  }

  function setState(next: SseLinkState): void {
    if (next === state) {
      return;
    }
    state = next;
    if (state === 'retrying' || state === 'silent') {
      startPolling();
    } else {
      stopPolling();
    }
    notify();
  }

  function armSilenceTimer(): void {
    if (silenceTimer !== null) {
      clearTimeout(silenceTimer);
      silenceTimer = null;
    }
    if (stopped) {
      return;
    }
    silenceTimer = setTimeout(() => {
      // Le lien est peut-être « ouvert » : il est surtout MUET.
      setState('silent');
    }, silenceMs);
  }

  /** Toute trame — `snapshot` comme `ping` — prouve que le lien vit. */
  function onFrame(): void {
    lastFrameAt = now();
    if (state === 'silent') {
      setState('open');
    }
    armSilenceTimer();
  }

  function onSnapshotEvent(event: MessageEvent<string>): void {
    onFrame();
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
    // Le `ping` du serveur (15 s) ne porte rien : il PROUVE le lien.
    next.addEventListener('ping', onFrame);
    next.onopen = () => {
      attempts = 0;
      onFrame();
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

  armSilenceTimer();
  connect();

  return {
    getState: () => state,
    getMode: modeOf,
    getSilenceMs: () => now() - lastFrameAt,
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
      if (silenceTimer !== null) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
      }
      stopPolling();
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
  getState(): SseLinkState {
    return activeHandle === null ? 'stopped' : activeHandle.getState();
  },
  subscribe(listener: () => void): () => void {
    stateListeners.add(listener);
    return () => {
      stateListeners.delete(listener);
    };
  },
};

export interface SseLink {
  readonly link: SseLinkState;
  readonly mode: SseLinkMode;
}

const NO_LINK: SseLink = { link: 'stopped', mode: 'aucun' };
let lastLink: SseLink = NO_LINK;

/**
 * Store `{link, mode}` — l'état du lien ET la façon dont les invalidations
 * arrivent réellement (signal ou sondage). L'instantané est STABLE tant que
 * rien ne change : `useSyncExternalStore` compare par identité et boucle
 * sinon.
 */
export const sseLinkStore = {
  getState(): SseLink {
    if (activeHandle === null) {
      if (lastLink.link !== 'stopped' || lastLink.mode !== 'aucun') {
        lastLink = NO_LINK;
      }
      return lastLink;
    }
    const link = activeHandle.getState();
    const mode = activeHandle.getMode();
    if (lastLink.link !== link || lastLink.mode !== mode) {
      lastLink = { link, mode };
    }
    return lastLink;
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
