/**
 * Ticker du shell — point 4 de l'anatomie canonique.
 *
 * Ce que ces tests protègent, et rien d'autre : la bande n'affiche JAMAIS un
 * chiffre qu'elle ne peut pas qualifier. Un ticker qui garderait ses derniers
 * cours pendant une coupure présenterait un cache comme du courant.
 */
import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { makeEmptyMarketsOverview, makeMarketsOverview } from '../test/fixtures.ts';
import { renderApp } from '../test/render.tsx';
import { tickerFrameOf } from './ShellTicker.tsx';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function ticker(): HTMLElement {
  return screen.getByRole('region', { name: 'Ticker des marchés' });
}

describe('tickerFrameOf — la table de décision, sans navigateur', () => {
  it('aucun chiffre tant que la requête n’a pas abouti', () => {
    expect(tickerFrameOf('loading', undefined, undefined).mode).toBe('notice');
    expect(tickerFrameOf('auth-required', undefined, undefined).mode).toBe('notice');
    expect(tickerFrameOf('offline', undefined, undefined).mode).toBe('notice');
    expect(tickerFrameOf('error', undefined, undefined).mode).toBe('notice');
  });

  it('un succès SANS instantané n’est pas un succès', () => {
    // `ready` avec `state` absent = réponse hors contrat. La bande ne doit pas
    // rendre une liste vide qui ressemblerait à « aucun mouvement ».
    expect(tickerFrameOf('ready', 'ok', undefined).mode).toBe('notice');
    expect(tickerFrameOf('ready', null, 'empty').mode).toBe('notice');
  });

  it('les dégradations viennent du SERVEUR et accompagnent les valeurs', () => {
    expect(tickerFrameOf('ready', 'stale', 'ok')).toEqual({
      mode: 'values',
      notice: null,
      caveat: 'PÉRIMÉ',
    });
    // L'état canonique de l'instantané suffit, même si `data_state` dit « ok ».
    expect(tickerFrameOf('ready', 'ok', 'stale').caveat).toBe('PÉRIMÉ');
    expect(tickerFrameOf('ready', 'partial', 'ok').caveat).toBe('COUVERTURE PARTIELLE');
    expect(tickerFrameOf('ready', 'ok', 'ok')).toEqual({
      mode: 'values',
      notice: null,
      caveat: null,
    });
    expect(tickerFrameOf('refreshing', 'ok', 'ok').mode).toBe('values');
  });
});

describe('Ticker du shell — rendu', () => {
  it('nominal : nature, fraîcheur et cours du serveur, dans l’ordre du worker', async () => {
    fetchMock.mockImplementation(async () => jsonResponse(makeMarketsOverview()));
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(found.getAttribute('data-mode')).toBe('values');
      return found;
    });

    // La nature de la population est DANS la bande, jamais dans le coin
    // haut-droit : elle qualifie ce ticker, pas l'application.
    expect(within(bande).getByText('DONNÉES SYNTHÉTIQUES')).toBeDefined();
    expect(within(bande).getByText('il y a 1 min')).toBeDefined();

    // Ordre du worker, secteur par secteur : Énergie puis Technologie. Aucun
    // tri local — reclasser produirait un classement financier.
    const symboles = within(bande)
      .getAllByRole('listitem')
      .map((item) => item.getAttribute('data-testid'));
    expect(symboles).toEqual([
      'ticker-SYN-ENER-01',
      'ticker-SYN-ENER-02',
      'ticker-SYN-TECH-01',
      'ticker-SYN-TECH-02',
    ]);

    // Chaînes serveur verbatim, point décimal francisé, signe conservé.
    const premier = within(bande).getByTestId('ticker-SYN-ENER-01');
    expect(premier.textContent).toContain('45,00');
    expect(premier.textContent).toContain('SYN');
    expect(premier.textContent).toContain('-10,00 %');
    expect(premier.getAttribute('data-group')).toBe('down');
    expect(
      within(bande).getByTestId('ticker-SYN-ENER-02').getAttribute('data-group'),
    ).toBe('flat');
  });

  it('la région défilante est atteignable au clavier', async () => {
    fetchMock.mockImplementation(async () => jsonResponse(makeMarketsOverview()));
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(found.getAttribute('data-mode')).toBe('values');
      return found;
    });
    // Sans `tabindex`, axe signale `scrollable-region-focusable` en « serious »
    // et le contenu de la bande devient inatteignable au clavier.
    expect(within(bande).getByRole('list').getAttribute('tabindex')).toBe('0');
  });

  it('périmé : les valeurs restent, la marque PÉRIMÉ les accompagne', async () => {
    fetchMock.mockImplementation(async () => jsonResponse(makeMarketsOverview({ data_state: 'stale' })));
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(found.getAttribute('data-mode')).toBe('values');
      return found;
    });
    expect(within(bande).getByText('PÉRIMÉ')).toBeDefined();
    expect(within(bande).getByTestId('ticker-SYN-ENER-01')).toBeDefined();
  });

  it('aucun instantané publié : un message, AUCUN chiffre', async () => {
    fetchMock.mockImplementation(async () => jsonResponse(makeEmptyMarketsOverview()));
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(within(found).getByText('Ticker — aucun instantané publié.')).toBeDefined();
      return found;
    });
    expect(bande.getAttribute('data-mode')).toBe('notice');
    expect(within(bande).queryAllByRole('listitem')).toEqual([]);
  });

  it('hors ligne : aucun cours conservé — un cache n’est pas un cours', async () => {
    fetchMock.mockImplementation(async () => {
      throw new TypeError('Failed to fetch');
    });
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(within(found).getByText('Ticker — API locale injoignable.')).toBeDefined();
      return found;
    });
    expect(bande.getAttribute('data-mode')).toBe('notice');
    expect(within(bande).queryAllByRole('listitem')).toEqual([]);
  });

  it('sans session : la bande le dit, sans rien inventer', async () => {
    fetchMock.mockImplementation(async () =>
      jsonResponse({ error: { kind: 'AUTH_REQUIRED', message: 'session requise' } }, 401),
    );
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(within(found).getByText('Ticker — session requise.')).toBeDefined();
      return found;
    });
    expect(bande.getAttribute('data-mode')).toBe('notice');
  });

  it('le ticker est le MÊME sur toutes les destinations (shell identique)', async () => {
    fetchMock.mockImplementation(async () => jsonResponse(makeMarketsOverview()));
    for (const route of ['/today', '/portfolio', '/sources-reports']) {
      const { unmount } = renderApp(route);
      await waitFor(() => {
        expect(ticker().getAttribute('data-mode')).toBe('values');
      });
      unmount();
    }
  });
});
