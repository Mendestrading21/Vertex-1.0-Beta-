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

  it('lot S4 : un signal risk_matrix/global invalide la clé de la page Risques', () => {
    const handle = start();
    const source = FakeEventSource.instances[0]!;
    source.emitOpen();
    source.emitSnapshot(JSON.stringify({ resource: 'risk_matrix/global', version: 3 }));
    expect(invalidateSpy).toHaveBeenCalledTimes(1);
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['snapshot', 'risk_matrix/global'],
    });
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
