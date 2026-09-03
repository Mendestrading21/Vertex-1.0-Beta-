import { QueryClient } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { startSnapshotEvents } from './events.ts';
import type { EventSourceLike } from './events.ts';

/** EventSource factice, piloté par les tests (aucun réseau). */
class FakeEventSource implements EventSourceLike {
  static instances: FakeEventSource[] = [];
  readonly url: string;
  readonly listeners = new Map<string, Array<(event: MessageEvent<string>) => void>>();
  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void {
    const existing = this.listeners.get(type) ?? [];
    existing.push(listener);
    this.listeners.set(type, existing);
  }

  close(): void {
    this.closed = true;
  }

  emitOpen(): void {
    this.onopen?.(new Event('open'));
  }

  emitError(): void {
    this.onerror?.(new Event('error'));
  }

  emitSnapshot(data: string): void {
    for (const listener of this.listeners.get('snapshot') ?? []) {
      listener(new MessageEvent('snapshot', { data }));
    }
  }

  /** Le `ping` du serveur (15 s) : aucune donnée, la preuve du lien. */
  emitPing(): void {
    for (const listener of this.listeners.get('ping') ?? []) {
      listener(new MessageEvent('ping', { data: '' }));
    }
  }
}

describe('abonnement SSE signal-only', () => {
  let queryClient: QueryClient;
  let invalidateSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.useFakeTimers();
    FakeEventSource.instances = [];
    queryClient = new QueryClient();
    invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function start() {
    return startSnapshotEvents(queryClient, {
      createEventSource: (url) => new FakeEventSource(url),
      baseDelayMs: 100,
      maxDelayMs: 1000,
    });
  }

  it("invalide UNIQUEMENT la clé de la ressource signalée", () => {
    const handle = start();
    const source = FakeEventSource.instances[0]!;
    source.emitOpen();
    expect(handle.getState()).toBe('open');

    source.emitSnapshot(JSON.stringify({ resource: 'attention/global', version: 4 }));
    expect(invalidateSpy).toHaveBeenCalledTimes(1);
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['snapshot', 'attention/global'],
    });

    source.emitSnapshot(JSON.stringify({ resource: 'capabilities/global', version: 2 }));
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
    expect(invalidateSpy).toHaveBeenLastCalledWith({
      queryKey: ['snapshot', 'capabilities/global'],
    });
    handle.stop();
  });

  it('ignore une ressource inconnue ou une trame invalide (aucune invalidation globale)', () => {
    const handle = start();
    const source = FakeEventSource.instances[0]!;
    source.emitOpen();
    source.emitSnapshot(JSON.stringify({ resource: 'autre/ressource', version: 9 }));
    source.emitSnapshot('pas-du-json');
    source.emitSnapshot(JSON.stringify({ version: 9 }));
    expect(invalidateSpy).not.toHaveBeenCalled();
    handle.stop();
  });

  it('reconnexion avec backoff exponentiel et état exposé', () => {
    const handle = start();
    const states: string[] = [];
    handle.subscribe(() => {
      states.push(handle.getState());
    });

    const first = FakeEventSource.instances[0]!;
    first.emitError();
    expect(handle.getState()).toBe('retrying');
    expect(first.closed).toBe(true);
    expect(FakeEventSource.instances).toHaveLength(1);

    vi.advanceTimersByTime(100); // 100 ms × 2^0
    expect(FakeEventSource.instances).toHaveLength(2);
    const second = FakeEventSource.instances[1]!;
    second.emitError();
    vi.advanceTimersByTime(199);
    expect(FakeEventSource.instances).toHaveLength(2);
    vi.advanceTimersByTime(1); // 100 ms × 2^1
    expect(FakeEventSource.instances).toHaveLength(3);

    const third = FakeEventSource.instances[2]!;
    third.emitOpen();
    expect(handle.getState()).toBe('open');
    expect(states).toContain('retrying');
    expect(states).toContain('open');
    handle.stop();
    expect(handle.getState()).toBe('stopped');
    expect(third.closed).toBe(true);
  });

  it("après stop(), plus aucune reconnexion n'est programmée", () => {
    const handle = start();
    const source = FakeEventSource.instances[0]!;
    source.emitError();
    handle.stop();
    vi.advanceTimersByTime(10_000);
    expect(FakeEventSource.instances).toHaveLength(1);
  });
});

/**
 * LOT L0 — SILENCE ET REPLI PAR SONDAGE.
 *
 * Le serveur émet un `ping` toutes les 15 s. Un `EventSource` peut rester
 * « ouvert » alors que plus rien n'arrive : l'écran afficherait « connecté »
 * sur un lien mort. Trois pings manqués valent SILENCE, et les invalidations
 * repassent par un sondage borné aux requêtes ACTIVES.
 */
describe('flux SSE — silence, ping et repli par sondage', () => {
  let queryClient: QueryClient;
  let invalidateSpy: ReturnType<typeof vi.spyOn>;
  let clock = 0;

  beforeEach(() => {
    vi.useFakeTimers();
    FakeEventSource.instances = [];
    queryClient = new QueryClient();
    invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    clock = 0;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function start() {
    return startSnapshotEvents(queryClient, {
      createEventSource: (url) => new FakeEventSource(url),
      baseDelayMs: 100,
      maxDelayMs: 1000,
      // Horloge de TRANSPORT injectée : jamais une horloge de donnée.
      now: () => clock,
    });
  }

  function advance(ms: number): void {
    clock += ms;
    vi.advanceTimersByTime(ms);
  }

  it('un `ping` est écouté et REPOUSSE le silence', () => {
    const handle = start();
    const source = FakeEventSource.instances[0]!;
    source.emitOpen();
    expect(handle.getState()).toBe('open');

    advance(40_000);
    source.emitPing();
    expect(handle.getState()).toBe('open');
    expect(handle.getSilenceMs()).toBe(0);

    // 40 s de plus après le ping : toujours sous les 45 s.
    advance(40_000);
    expect(handle.getState()).toBe('open');
    handle.stop();
  });

  it('45 s sans aucune trame : SILENCE déclaré et mode « sondage »', () => {
    const handle = start();
    FakeEventSource.instances[0]!.emitOpen();
    expect(handle.getMode()).toBe('signal');

    advance(44_999);
    expect(handle.getState()).toBe('open');
    advance(1);
    expect(handle.getState()).toBe('silent');
    expect(handle.getMode()).toBe('sondage');
    handle.stop();
  });

  it('en silence, le sondage invalide les requêtes ACTIVES toutes les 30 s', () => {
    const handle = start();
    FakeEventSource.instances[0]!.emitOpen();
    advance(45_000);
    invalidateSpy.mockClear();

    advance(29_999);
    expect(invalidateSpy).not.toHaveBeenCalled();
    advance(1);
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['snapshot'],
      refetchType: 'active',
    });
    advance(30_000);
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
    handle.stop();
  });

  it('une trame reçue ARRÊTE le sondage et rouvre le lien', () => {
    const handle = start();
    const source = FakeEventSource.instances[0]!;
    source.emitOpen();
    advance(45_000);
    expect(handle.getState()).toBe('silent');

    source.emitPing();
    expect(handle.getState()).toBe('open');
    expect(handle.getMode()).toBe('signal');

    invalidateSpy.mockClear();
    advance(30_000);
    expect(invalidateSpy).not.toHaveBeenCalled();
    handle.stop();
  });

  it('en reconnexion, le sondage prend le relais puis s’arrête à la réouverture', () => {
    const handle = start();
    FakeEventSource.instances[0]!.emitError();
    expect(handle.getState()).toBe('retrying');
    expect(handle.getMode()).toBe('sondage');

    invalidateSpy.mockClear();
    advance(30_000);
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['snapshot'],
      refetchType: 'active',
    });

    // La reconnexion a recréé une source : elle s'ouvre, le sondage cesse.
    const reconnected = FakeEventSource.instances[FakeEventSource.instances.length - 1]!;
    reconnected.emitOpen();
    expect(handle.getState()).toBe('open');
    expect(handle.getMode()).toBe('signal');
    invalidateSpy.mockClear();
    advance(30_000);
    expect(invalidateSpy).not.toHaveBeenCalled();
    handle.stop();
  });

  it('stop() éteint tout : plus de sondage, plus de silence, mode « aucun »', () => {
    const handle = start();
    FakeEventSource.instances[0]!.emitError();
    handle.stop();
    expect(handle.getMode()).toBe('aucun');
    invalidateSpy.mockClear();
    advance(120_000);
    expect(invalidateSpy).not.toHaveBeenCalled();
    expect(handle.getState()).toBe('stopped');
  });
});
