import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { makeAnalysis, makeEmptyAnalysis, makeMarketsTicker } from '../../test/fixtures.ts';
import { signGroupOf } from '../markets/marketsView.ts';
import { InstrumentTile } from './InstrumentTile.tsx';

/**
 * Tuile d'instrument — déplacée depuis `pages/InstrumentWidget.tsx` dans le
 * socle (lot L0). Les faits ajoutés sont ceux que le contrat publiait déjà
 * sans être affichés : `previous_close` / `previous_trading_day` et `quality`.
 */
function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function wrap(children: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
}

const TICKER = makeMarketsTicker({
  ticker: 'AEHL',
  last_close: '12.55',
  previous_close: '12.10',
  previous_trading_day: '2026-09-02',
  quality: 'OK',
  currency: 'USD',
  return_1d_pct: '+3.72',
});

const ENTRY = { ticker: TICKER, sectorLabel: 'Technologie', group: signGroupOf(TICKER) };

describe('InstrumentTile', () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('affiche la clôture PRÉCÉDENTE servie et son jour de séance', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeAnalysis()));
    wrap(<InstrumentTile entry={ENTRY} />);
    await waitFor(() => {
      expect(screen.getByTestId('instrument-widget')).toBeDefined();
    });
    const faits = screen.getByTestId('instrument-tile-facts');
    // Chaîne SERVIE, virgule française comme le reste de la tuile — jamais un
    // arrondi ni une conversion : seul le séparateur décimal est adapté.
    expect(faits.textContent).toContain('12,10');
    expect(faits.textContent).toContain('2026-09-02');
  });

  it('la qualité servie est une pastille à TEXTE', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeAnalysis()));
    wrap(<InstrumentTile entry={ENTRY} />);
    await waitFor(() => {
      expect(screen.getByTestId('instrument-widget')).toBeDefined();
    });
    expect(screen.getByTestId('status-chip').textContent).toContain('OK');
  });

  it('une clôture précédente non publiée est DITE, jamais remplacée', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeAnalysis()));
    const sansPrecedent = {
      ...ENTRY,
      ticker: { ...TICKER, previous_close: '', previous_trading_day: '' },
    };
    wrap(<InstrumentTile entry={sansPrecedent} />);
    await waitFor(() => {
      expect(screen.getByTestId('instrument-widget')).toBeDefined();
    });
    expect(screen.getByTestId('instrument-tile-facts').textContent).toContain('non publié');
  });

  it('sans dossier publié, le cadre DIT ce qui manque : aucune courbe plate', async () => {
    fetchMock.mockResolvedValue(jsonResponse(makeEmptyAnalysis()));
    const { container } = wrap(<InstrumentTile entry={ENTRY} />);
    await waitFor(() => {
      expect(screen.getByTestId('instrument-widget-chart').textContent).toContain(
        'Aucun dossier',
      );
    });
    expect(container.querySelector('polyline')).toBeNull();
  });
});
