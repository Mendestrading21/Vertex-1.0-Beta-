import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeAttentionItem,
  makeAttentionSnapshot,
  makeCapabilities,
  makeEmptyAttentionSnapshot,
  makeMarketsOverview,
} from '../test/fixtures.ts';
import { renderApp } from '../test/render.tsx';
import { attentionFrameStateOf } from './TodayPage.tsx';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockToday(attention: unknown): void {
  fetchMock.mockImplementation((input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (url.includes('/today/attention')) {
      return Promise.resolve(jsonResponse(attention));
    }
    if (url.includes('/system/capabilities')) {
      return Promise.resolve(jsonResponse(makeCapabilities()));
    }
    return Promise.resolve(jsonResponse(makeMarketsOverview()));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("attentionFrameStateOf — l'état servi prime sur le succès HTTP", () => {
  it('relaie les états requête hors succès et refuse un succès sans réponse', () => {
    expect(attentionFrameStateOf('loading', undefined)).toBe('loading');
    expect(attentionFrameStateOf('offline', makeAttentionSnapshot({ state: 'stale' }))).toBe(
      'offline',
    );
    expect(attentionFrameStateOf('auth-required', undefined)).toBe('auth-required');
    expect(attentionFrameStateOf('ready', undefined)).toBe('error');
  });

  it('applique la priorité stale, DELAYED, empty, puis état de requête', () => {
    expect(
      attentionFrameStateOf(
        'refreshing',
        makeAttentionSnapshot({ state: 'stale', population: 'DELAYED' }),
      ),
    ).toBe('stale');
    expect(
      attentionFrameStateOf('refreshing', makeAttentionSnapshot({ population: 'DELAYED' })),
    ).toBe('delayed');
    expect(attentionFrameStateOf('ready', makeEmptyAttentionSnapshot())).toBe('empty');
    expect(attentionFrameStateOf('refreshing', makeAttentionSnapshot())).toBe('refreshing');
    expect(attentionFrameStateOf('ready', makeAttentionSnapshot())).toBe('ready');
  });
});

describe("Page Aujourd'hui — états dégradés du snapshot", () => {
  it('state=stale conserve la file sous un bandeau avec raison, âge et instant', async () => {
    const stale = makeAttentionSnapshot({
      state: 'stale',
      age_seconds: 300_000,
      reason: 'snapshot older than its freshness budget',
    });
    mockToday(stale);
    renderApp('/today');

    await screen.findByRole('heading', { level: 1, name: "Aujourd'hui" });
    const main = screen.getByRole('main');
    await waitFor(() => {
      expect(main.querySelector('[data-state="stale"]')).not.toBeNull();
    });
    const boundary = main.querySelector('[data-state="stale"]') as HTMLElement;
    expect(boundary.textContent).toContain('Données périmées');
    expect(boundary.textContent).toContain('snapshot older than its freshness budget');
    expect(boundary.textContent).toContain('300000 s');
    expect(boundary.textContent).toContain('as_of 2026-08-25T12:00:00+00:00');
    expect(within(boundary).getByText(stale.items[0]!.title)).toBeDefined();
  });

  it('population=DELAYED conserve la file sous un état différé explicite', async () => {
    const delayedItem = makeAttentionItem(0, {
      synthetic: false,
      sources: ['ibkr'],
      rights: ['IBKR_MARKET_DATA'],
      provenance: {
        ...makeAttentionItem(0).provenance,
        sources: ['ibkr'],
        rights: ['IBKR_MARKET_DATA'],
      },
    });
    const delayed = makeAttentionSnapshot({
      population: 'DELAYED',
      age_seconds: 90,
      items: [delayedItem],
    });
    mockToday(delayed);
    renderApp('/today');

    await screen.findByRole('heading', { level: 1, name: "Aujourd'hui" });
    const main = screen.getByRole('main');
    await waitFor(() => {
      expect(main.querySelector('[data-state="delayed"]')).not.toBeNull();
    });
    const boundary = main.querySelector('[data-state="delayed"]') as HTMLElement;
    expect(boundary.textContent).toContain('Données différées');
    expect(boundary.textContent).toContain('DONNÉES RETARDÉES');
    expect(boundary.textContent).toContain('90 s');
    expect(within(boundary).getByText(delayedItem.title)).toBeDefined();
  });
});
