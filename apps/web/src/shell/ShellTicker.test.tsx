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
import { servedClockOf, tickerFrameOf } from './ShellTicker.tsx';

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

/**
 * LOT-A1 — points 4 et 5 de l'anatomie : l'heure SERVIE, à droite.
 *
 * Les planches canoniques posent une heure UTC à l'extrémité droite de la
 * bande. Le piège est nommé d'avance : une horloge murale qui AVANCE à côté
 * d'un instantané FIGÉ fabrique une impression de courant, et
 * `.claude/rules/financial-safety.md` interdit de présenter un cache comme du
 * live. L'heure affichée est donc celle de l'`as_of` servi, jamais
 * `Date.now()` — et quand aucun instantané n'est servi, il n'y a AUCUNE heure
 * à afficher, parce qu'il n'y a pas d'instant dont elle serait l'heure.
 */
describe('servedClockOf — l’heure vient de l’instantané, jamais du navigateur', () => {
  it('formate l’instant SERVI en UTC, sans dépendre du fuseau du navigateur', () => {
    // `SYNTHETIC_AS_OF` vaut `2026-08-25T12:00:00+00:00`. Le rendu doit être le
    // MÊME à Zurich, à Tokyo ou à New York : c'est un instant de marché, pas
    // une heure locale de lecture.
    expect(servedClockOf('2026-08-25T12:00:00+00:00')).toBe('25/08/2026 12:00 UTC');
    // Un décalage de fuseau dans la chaîne servie est CONVERTI, pas tronqué.
    expect(servedClockOf('2026-08-25T14:00:00+02:00')).toBe('25/08/2026 12:00 UTC');
    // Passage de jour : convertir puis lire, jamais lire puis convertir.
    expect(servedClockOf('2026-08-25T23:30:00-05:00')).toBe('26/08/2026 04:30 UTC');
  });

  it('AUCUNE heure de repli : absence et illisible sortent `null`', () => {
    // Le cœur du lot. Une heure de repli — `Date.now()`, minuit, une chaîne
    // brute — serait une valeur que personne n'a servie.
    expect(servedClockOf(null)).toBeNull();
    expect(servedClockOf(undefined)).toBeNull();
    expect(servedClockOf('')).toBeNull();
    expect(servedClockOf('pas une date')).toBeNull();
    expect(servedClockOf('2026-13-45T99:99:99Z')).toBeNull();
  });

  it('ne bouge pas entre deux lectures — un instantané n’a qu’une heure', () => {
    const premier = servedClockOf('2026-08-25T12:00:00+00:00');
    const second = servedClockOf('2026-08-25T12:00:00+00:00');
    expect(premier).toBe(second);
  });
});

describe('Ticker — l’heure servie et le bloc de droite', () => {
  it('affiche l’heure de l’instantané, et c’est bien CELLE-LÀ', async () => {
    fetchMock.mockImplementation(async () => jsonResponse(makeMarketsOverview()));
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(found.getAttribute('data-mode')).toBe('values');
      return found;
    });
    const horloge = within(bande).getByTestId('ticker-clock');
    expect(horloge.textContent).toBe('25/08/2026 12:00 UTC');
    // L'heure porte son `datetime` machine : la même vérité, lisible par un
    // outil, et impossible à confondre avec une heure de lecture.
    expect(horloge.getAttribute('datetime')).toBe('2026-08-25T12:00:00+00:00');
  });

  it('un instantané SANS `as_of` n’affiche aucune heure', async () => {
    fetchMock.mockImplementation(async () =>
      jsonResponse(makeMarketsOverview({ as_of: null })),
    );
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(found.getAttribute('data-mode')).toBe('values');
      return found;
    });
    // Les cours restent — le serveur les sert. L'heure, elle, n'existe pas.
    expect(within(bande).getByTestId('ticker-SYN-ENER-01')).toBeDefined();
    expect(within(bande).queryByTestId('ticker-clock')).toBeNull();
  });

  it('hors ligne : aucune heure non plus — il n’y a pas d’instantané', async () => {
    fetchMock.mockImplementation(async () => {
      throw new TypeError('Failed to fetch');
    });
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(found.getAttribute('data-mode')).toBe('notice');
      return found;
    });
    expect(within(bande).queryByTestId('ticker-clock')).toBeNull();
  });

  it('la DÉGRADATION reste avant les valeurs, la métadonnée passe après', async () => {
    fetchMock.mockImplementation(async () =>
      jsonResponse(makeMarketsOverview({ data_state: 'stale' })),
    );
    renderApp('/today');

    const bande = await waitFor(() => {
      const found = ticker();
      expect(found.getAttribute('data-mode')).toBe('values');
      return found;
    });
    // L'ordre du DOM est l'ordre de LECTURE, y compris au lecteur d'écran.
    // `PÉRIMÉ` qualifie les cours : il doit être lu AVANT eux. Nature,
    // fraîcheur et heure identifient l'instantané : elles peuvent suivre.
    // Le placement à droite des planches est obtenu par la grille CSS, pas
    // en déplaçant le DOM — sinon on perdrait exactement ce que le LOT-14 a
    // établi : « un cours lu avant son étiquette est un cours lu sans elle ».
    const textes = Array.from(bande.querySelectorAll('[data-ticker-slot]')).map((noeud) =>
      noeud.getAttribute('data-ticker-slot'),
    );
    expect(textes).toEqual(['caveat', 'meta', 'list']);
  });
});
