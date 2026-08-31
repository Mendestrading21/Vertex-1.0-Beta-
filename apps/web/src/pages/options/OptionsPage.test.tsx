/**
 * Page Options — sélecteur de groupes jamais fusionnés, table Calls | Strike
 * | Puts, IV absente rendue « — » avec sa raison, inspecteur avec lignée
 * CalculationRecord, transfert typé vers le Simulateur, états dégradés.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  makeEmptyOptionChain,
  makeMarketsOverview,
  makeOptionChain,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Sert une Response FRAÎCHE par appel, routée par URL.
 *
 * Le sélecteur d'instruments lit la vue Marchés en plus de la ressource de la
 * page. Un `mockResolvedValue` unique rendrait le même objet `Response` aux
 * deux appels, et un corps de réponse ne se lit qu'une fois.
 */
function repondre(reponse: Response): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/markets/overview')) {
      return Promise.resolve(jsonResponse(makeMarketsOverview()));
    }
    return Promise.resolve(reponse.clone());
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderOptions(path = '/options/SYN-TECH-01'): Promise<void> {
  renderApp(path);
  await screen.findByRole('heading', { level: 1, name: 'Options' });
}

describe('Page Options — état nominal', () => {
  it('sélecteur : deux trading classes d’une même date = deux entrées distinctes', async () => {
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    const groups = await screen.findAllByTestId('chain-group');
    expect(groups).toHaveLength(3);
    const labels = groups.map((group) => group.textContent ?? '');
    expect(labels.some((label) => label.includes('2026-09-26 · SYN-TECH-01 (SYNTH)'))).toBe(true);
    expect(labels.some((label) => label.includes('2026-09-26 · SYN-TECH-01W (SYNTH)'))).toBe(true);
    // Couverture et budget de lignes publiés, affichés.
    expect(labels[0]).toContain('3 contrats attendus');
    expect(labels[0]).toContain('2 IV résolues');
    expect(screen.getByTestId('chain-row-budget').textContent).toContain(
      '5 publiée(s) / 5 construite(s), plafond 240, 0 tronquée(s)',
    );
  });

  it('bascule de groupe : la table rend le groupe sélectionné uniquement', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    const table = await screen.findByRole('table', { name: /Chaîne d'options 2026-09-26 SYN-TECH-01$/ });
    expect(table).toBeDefined();
    const weekly = screen
      .getAllByTestId('chain-group')
      .find((group) => (group.textContent ?? '').includes('SYN-TECH-01W'));
    await user.click(weekly!);
    expect(
      screen.getByRole('table', { name: "Chaîne d'options 2026-09-26 SYN-TECH-01W" }),
    ).toBeDefined();
  });

  it('IV absente : cellule « — » avec la raison typée, jamais 0', async () => {
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    const table = await screen.findByRole('table', { name: /SYN-TECH-01$/ });
    // Le contrat croisé (strike 105.00) n'a pas d'IV : « — » + raison.
    const absent = within(table).getAllByLabelText(/crossed_quote/);
    expect(absent.length).toBeGreaterThan(0);
    expect(absent[0]?.textContent).toBe('—');
    expect(absent[0]?.getAttribute('title')).toContain('quote croisée');
    // Aucun zéro fabriqué à la place d'une IV absente.
    const row = absent[0]!.closest('tr');
    expect(row?.textContent).not.toContain('0.00000');
    // Statut de quote affiché en texte (jamais la couleur seule).
    expect(within(row as HTMLElement).getAllByText('CROSSED').length).toBeGreaterThan(0);
  });

  it('inspecteur : identité complète, quote, IV THÉORIQUE et CalculationRecord id', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    await screen.findByRole('table', { name: /SYN-TECH-01$/ });
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    const inspector = await screen.findByTestId('option-inspector');
    expect(inspector.getAttribute('role')).toBe('dialog');
    const scoped = within(inspector);
    expect(scoped.getByText('900000101')).toBeDefined(); // con_id
    // sous-jacent ET trading class affichés (deux <code> distincts).
    expect(scoped.getAllByText('SYN-TECH-01', { selector: 'code' }).length).toBeGreaterThanOrEqual(2);
    expect(scoped.getByText('EUROPEAN / CASH')).toBeDefined();
    expect(scoped.getByText('0.24500000000000001')).toBeDefined(); // IV verbatim
    expect(scoped.getAllByText('THÉORIQUE').length).toBeGreaterThanOrEqual(2); // IV + Greeks
    expect(scoped.getAllByText('options.implied_volatility').length).toBeGreaterThan(0);
    expect(scoped.getAllByText('options.greeks').length).toBeGreaterThan(0);
    // Fermeture par Échap : focus restitué (dialog démonté).
    await user.keyboard('{Escape}');
    expect(screen.queryByTestId('option-inspector')).toBeNull();
  });

  it('« Envoyer au Simulateur » : navigation avec préremplissage typé (transfert d’analyse)', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    await screen.findByRole('table', { name: /SYN-TECH-01$/ });
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    await screen.findByTestId('option-inspector');
    await user.click(screen.getByRole('button', { name: 'Envoyer au Simulateur' }));
    // La page Simulateur (paresseuse) se monte avec la note de préremplissage.
    await screen.findByRole('heading', { level: 1, name: 'Simulateur' });
    const note = await screen.findByTestId('sim-transfer-note');
    expect(note.textContent).toContain('CALL');
    expect(note.textContent).toContain('100.00');
    expect(note.textContent).toContain('SYN-TECH-01');
    expect(note.textContent).toContain('SYNTHÉTIQUE');
    // Champs préremplis avec les chaînes serveur verbatim (éditables).
    expect((screen.getByLabelText('Strike (décimal)') as HTMLInputElement).value).toBe('100.00');
    expect(
      (screen.getByLabelText('Prime unitaire déclarée (décimal)') as HTMLInputElement).value,
    ).toBe('4.30'); // ask
    expect((screen.getByLabelText('Spot déclaré (décimal)') as HTMLInputElement).value).toBe(
      '102.50',
    );
  });
});

describe('Page Options — états', () => {
  it('sans sous-jacent : état vide explicite + sélecteur, aucun défaut implicite', async () => {
    await renderOptions('/options');
    expect(screen.getByText('Aucune donnée')).toBeDefined();
    expect(screen.getByText(/Aucun sous-jacent sélectionné/)).toBeDefined();
    expect(
      screen.getByRole('navigation', { name: 'Sous-jacents disponibles' }),
    ).toBeDefined();
    // Le sélecteur lit la vue Marchés ; ce qui ne doit PAS être
    // demandé, c'est la ressource d'instrument elle-même.
    const demandes = fetchMock.mock.calls.map(([entree]) => String(entree));
    expect(demandes.some((url) => url.includes('/v1/options/'))).toBe(false);
  });

  it('empty honnête : aucun snapshot publié, raison serveur affichée', async () => {
    repondre(jsonResponse(makeEmptyOptionChain()));
    await renderOptions();
    await screen.findByText('Aucune donnée');
    expect(screen.getByText(/no snapshot published/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('partial : qualité de groupe dégradée publiée → bandeau + contenu conservé', async () => {
    const chain = makeOptionChain();
    const degraded = {
      ...chain,
      expirations: chain.expirations.map((group, index) =>
        index === 0 ? { ...group, quality: 'PARTIAL' } : group,
      ),
    };
    repondre(jsonResponse(degraded));
    await renderOptions();
    await screen.findByText('Données partielles');
    expect(screen.getByText(/qualité dégradée/)).toBeDefined();
    expect(screen.getByRole('table', { name: /SYN-TECH-01$/ })).toBeDefined();
  });

  it('offline honnête quand l’API est injoignable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    await renderOptions();
    await screen.findByText('Hors ligne');
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('loading au premier chargement', async () => {
    fetchMock.mockReturnValue(new Promise<Response>(() => {}));
    await renderOptions();
    expect(await screen.findByText('Chargement')).toBeDefined();
  });

  it('session requise sur 401', async () => {
    repondre(jsonResponse({ detail: { code: 'AUTH_REQUIRED' } }, 401));
    await renderOptions();
    await screen.findByText('Session requise');
  });

  it('erreur de données sur réponse inattendue (500)', async () => {
    repondre(jsonResponse({ detail: 'boom' }, 500));
    await renderOptions();
    await screen.findByText('Erreur de données');
  });
});
