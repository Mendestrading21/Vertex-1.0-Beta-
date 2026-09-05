/**
 * Page Options — sélecteur de groupes jamais fusionnés, table Calls | Strike
 * | Puts, IV absente rendue « — » avec sa raison, inspecteur avec lignée
 * CalculationRecord, transfert typé vers le Simulateur, états dégradés.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { queryKeyForResource } from '../../api/hooks.ts';
import {
  makeAnalysis,
  makeCalendarResponse,
  makeEmptyOptionChain,
  makeMarketsOverview,
  makeOptionChain,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { OPTIONS_MODULES } from './optionsModules.ts';

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
    // LOT-A5 : la planche §5 lit aussi le dossier d'analyse du sous-jacent
    // (série) et, après transfert, l'agenda publié (catalyseurs). Servis
    // explicitement : le repli leur donnerait un corps de CHAÎNE.
    if (url.includes('/v1/analysis/')) {
      return Promise.resolve(jsonResponse(makeAnalysis()));
    }
    if (url.includes('/v1/calendar')) {
      return Promise.resolve(jsonResponse(makeCalendarResponse()));
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

async function renderOptions(path = '/options/SYN-TECH-01') {
  const view = renderApp(path);
  await screen.findByRole('heading', { level: 1, name: 'Options' });
  return view;
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
    await user.click(within(table).getByRole('button', { name: /Inspecter CALL strike 100\.00/ }));
    expect(await screen.findByTestId('option-inspector')).toBeDefined();
    const weekly = screen
      .getAllByTestId('chain-group')
      .find((group) => (group.textContent ?? '').includes('SYN-TECH-01W'));
    await user.click(weekly!);
    expect(
      screen.getByRole('table', { name: "Chaîne d'options 2026-09-26 SYN-TECH-01W" }),
    ).toBeDefined();
    expect(screen.queryByTestId('option-inspector')).toBeNull();
  });

  it('IV absente : cellule « — » avec la raison typée, jamais 0', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    const table = await screen.findByRole('table', { name: /SYN-TECH-01$/ });
    // Le contrat croisé (strike 105.00) n'a pas d'IV : « — » + raison.
    const absent = within(table).getAllByLabelText(/crossed_quote/);
    expect(absent.length).toBeGreaterThan(0);
    expect(absent[0]?.textContent).toBe('—');
    expect(absent[0]?.getAttribute('title')).toContain('quote croisée');
    // LOT T4 — assertions AJOUTÉES, aucune retirée. La cellule dense reste le
    // seul endroit du produit qui a le droit d'écrire « — », et elle le paie
    // en preuve : un nom accessible RÉEL (`role="img"` — sur un <span> nu,
    // ARIA ignore `aria-label`), le motif SERVI exposé en donnée, et le code
    // serveur verbatim dans le libellé.
    expect(absent[0]?.getAttribute('role')).toBe('img');
    expect(absent[0]?.getAttribute('data-absent')).toBe('true');
    expect(absent[0]?.getAttribute('data-reason')).toBe('crossed_quote');
    expect(absent[0]?.getAttribute('aria-label')).toContain('crossed_quote');
    // « non calculée » et non « absente » : le moteur a refusé, il n'a pas
    // manqué de données. Les deux appellent des actions différentes.
    expect(absent[0]?.getAttribute('aria-label')).toContain('non calculée');
    // Aucun zéro fabriqué à la place d'une IV absente.
    const row = absent[0]!.closest('tr');
    expect(row?.textContent).not.toContain('0.00000');
    // Statut de quote affiché en texte (jamais la couleur seule).
    expect(within(row as HTMLElement).getAllByText('CROSSED').length).toBeGreaterThan(0);

    // Le contrat reste consultable, mais une quote CROSSED ne fournit jamais
    // une prime au Simulateur.
    await user.click(
      screen.getByRole('button', { name: /Inspecter CALL strike 105\.00/ }),
    );
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Transfert bloqué : statut de quote CROSSED/)).toBeDefined();
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
    // LOT-13 : ce n'est plus un dialogue modal mais un panneau de
    // l'inspecteur du shell. Le contenu asséré ci-dessous est inchangé.
    expect(inspector.closest('.vx-inspector-panel')).not.toBeNull();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(document.querySelector('[aria-modal]')).toBeNull();
    const scoped = within(inspector);
    expect(scoped.getByText('900000101')).toBeDefined(); // con_id
    // sous-jacent ET trading class affichés (deux <code> distincts).
    expect(scoped.getAllByText('SYN-TECH-01', { selector: 'code' }).length).toBeGreaterThanOrEqual(2);
    expect(scoped.getByText('EUROPEAN / CASH')).toBeDefined();
    expect(scoped.getByText('0.24500000000000001')).toBeDefined(); // IV verbatim
    expect(scoped.getAllByText('THÉORIQUE').length).toBeGreaterThanOrEqual(2); // IV + Greeks
    expect(scoped.getAllByText('options.implied_volatility').length).toBeGreaterThan(0);
    expect(scoped.getAllByText('options.greeks').length).toBeGreaterThan(0);
    // CONSERVÉ : fermeture par Échap, panneau démonté.
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

  it('refetch SSE : un ancien contrat inspecté ne survit pas au nouveau snapshot', async () => {
    const user = userEvent.setup();
    const initial = makeOptionChain();
    let current = initial;
    fetchMock.mockImplementation((entree: unknown) => {
      const url = typeof entree === 'string' ? entree : String((entree as Request).url);
      return Promise.resolve(
        jsonResponse(
          url.includes('/markets/overview')
            ? makeMarketsOverview()
            : url.includes('/v1/analysis/')
              ? makeAnalysis()
              : current,
        ),
      );
    });

    const { queryClient } = await renderOptions();
    await screen.findByRole('table', { name: /Chaîne d'options 2026-09-26 SYN-TECH-01$/ });
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    expect(await screen.findByTestId('option-inspector')).toBeDefined();
    expect(
      (screen.getByRole('button', { name: 'Envoyer au Simulateur' }) as HTMLButtonElement).disabled,
    ).toBe(false);

    // Même groupe toujours VALID, mais la quote du contrat ouvert est
    // remplacée : l'ancien ask ne doit jamais être réutilisé après le refetch.
    current = makeOptionChain({
      snapshot_version: 13,
      as_of: '2026-08-25T12:05:00+00:00',
      expirations: initial.expirations.map((group, groupIndex) =>
        groupIndex === 0
          ? {
              ...group,
              contracts: group.contracts.map((contract) =>
                contract.con_id === 900000101
                  ? {
                      ...contract,
                      quote: { ...contract.quote, status: 'CROSSED', ask: null },
                      iv: { status: 'ABSENT', reason: 'crossed_quote' },
                      greeks: { status: 'ABSENT', reason: 'iv_unresolved' },
                    }
                  : contract,
              ),
            }
          : group,
      ),
    });
    await queryClient.invalidateQueries({
      queryKey: queryKeyForResource('option_chain/SYN-TECH-01'),
    });

    await waitFor(() => {
      expect(screen.queryByTestId('option-inspector')).toBeNull();
    });
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Transfert bloqué : statut de quote CROSSED/)).toBeDefined();
  });
});

describe('Page Options — états', () => {
  it('sans sous-jacent : la PLANCHE ENTIÈRE tient sa place, chaque carte dit pourquoi elle est vide', async () => {
    await renderOptions('/options');
    // LOT P3b — RESSERRÉ, PAS ASSOUPLI. La page rendait une carte isolée dans
    // un écran aux deux tiers vide ; elle rend maintenant les quinze modules
    // du catalogue. L'assertion passe donc d'« une carte vide existe » à « la
    // planche est complète et chaque module dit sa propre cause ».
    const planche = screen.getByTestId('options-grid');
    expect(planche.querySelectorAll(':scope > [data-module]')).toHaveLength(15);

    // LA DISTINCTION QUI COMPTE, et que ce lot ne doit surtout pas brouiller :
    // un module SANS SOURCE garde le motif de son absence permanente ; un
    // module SERVI dit qu'aucun sous-jacent n'est choisi. Confondre les deux
    // ferait croire qu'une source manquante n'est qu'une sélection oubliée.
    for (const module of OPTIONS_MODULES) {
      const carte = planche.querySelector(`:scope > [data-module="${module.id}"]`);
      expect(carte, module.id).not.toBeNull();
      const texte = carte?.textContent ?? '';
      if (module.status.kind === 'absent') {
        expect(texte, module.id).toContain(module.status.note.slice(0, 30));
        expect(texte, module.id).not.toContain('Aucun sous-jacent sélectionné');
      } else {
        expect(texte, module.id).toContain('Aucun sous-jacent sélectionné');
      }
    }

    expect(
      screen.getByRole('navigation', { name: 'Sous-jacents disponibles' }),
    ).toBeDefined();
    // AUCUN DÉFAUT IMPLICITE — l'exigence d'origine, conservée telle quelle.
    // Le sélecteur lit la vue Marchés ; ce qui ne doit PAS être demandé, c'est
    // la ressource d'instrument elle-même.
    const demandes = fetchMock.mock.calls.map(([entree]) => String(entree));
    expect(demandes.some((url) => url.includes('/v1/options/'))).toBe(false);
    // Et rien n'est inventé pour remplir : aucune table, aucun chiffre.
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('empty honnête : aucun snapshot publié, raison serveur affichée', async () => {
    repondre(jsonResponse(makeEmptyOptionChain()));
    await renderOptions();
    await screen.findByText('Aucune donnée');
    expect(screen.getByText(/no snapshot published/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('partial : seul le groupe sélectionné décide du transfert, sans masquer le cadre global', async () => {
    const user = userEvent.setup();
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
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(true);
    expect(
      screen.getByText(/qualité publiée du groupe sélectionné est PARTIAL, pas VALID/),
    ).toBeDefined();

    // Le groupe hebdomadaire est explicitement VALID : l'autre groupe reste
    // PARTIAL et le cadre global le signale toujours, mais ce contrat sain est
    // transférable sans lui attribuer la dégradation d'un voisin.
    await user.keyboard('{Escape}');
    const weekly = screen
      .getAllByTestId('chain-group')
      .find((group) => (group.textContent ?? '').includes('SYN-TECH-01W'));
    await user.click(weekly!);
    expect(screen.getByText('Données partielles')).toBeDefined();
    const weeklyTable = screen.getByRole('table', {
      name: "Chaîne d'options 2026-09-26 SYN-TECH-01W",
    });
    await user.click(within(weeklyTable).getByRole('button', { name: /Inspecter CALL strike/ }));
    const validTransfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((validTransfer as HTMLButtonElement).disabled).toBe(false);
  });

  it('stale serveur : bandeau « Données périmées » + contenu daté conservé', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain({ state: 'stale', reason: 'snapshot too old' })));
    await renderOptions();
    await screen.findByText('Données périmées');
    expect(screen.getByText('snapshot too old')).toBeDefined();
    expect(screen.getByText(/as_of 2026-08-25T12:00:00\+00:00/)).toBeDefined();
    const table = screen.getByRole('table', { name: /SYN-TECH-01$/ });
    expect(table.closest('[data-state]')?.getAttribute('data-state')).toBe('stale');
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Transfert bloqué : le snapshot d'options est périmé/)).toBeDefined();
  });

  it('population DELAYED : bandeau et état différés, sans promotion ready', async () => {
    const user = userEvent.setup();
    const base = makeOptionChain();
    const delayed = makeOptionChain({
      population: 'DELAYED',
      spot:
        base.spot === null
          ? null
          : { ...base.spot, source_event_id: 'ibkr.option-chain:delayed:spot' },
      expirations: base.expirations.map((group, index) => ({
        ...group,
        source_event_id: `ibkr.option-chain:delayed:${index}`,
        contracts: group.contracts.map((contract) => ({ ...contract, synthetic: false })),
      })),
    });
    repondre(jsonResponse(delayed));
    await renderOptions();

    await screen.findByText('DONNÉES RETARDÉES');
    await screen.findByText('Données différées');
    const table = screen.getByRole('table', { name: /SYN-TECH-01$/ });
    expect(table.closest('[data-state]')?.getAttribute('data-state')).toBe('delayed');
    expect(screen.getByTestId('chain-source-references').textContent).toContain(
      'ibkr.option-chain:delayed:spot',
    );
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(true);
    expect(
      screen.getByText(/Transfert bloqué : la population d'options est DELAYED/),
    ).toBeDefined();
  });

  it('population REAL : aucune source ni limite synthétique inventée', async () => {
    const user = userEvent.setup();
    const base = makeOptionChain();
    const real = makeOptionChain({
      population: 'REAL',
      spot:
        base.spot === null
          ? null
          : { ...base.spot, source_event_id: 'ibkr.option-chain:real:spot' },
      expirations: base.expirations.map((group, index) => ({
        ...group,
        source_event_id: `ibkr.option-chain:real:${index}`,
        contracts: group.contracts.map((contract) => ({ ...contract, synthetic: false })),
      })),
    });
    repondre(jsonResponse(real));
    await renderOptions();

    await screen.findByText('DONNÉES RÉELLES');
    const references = screen.getByTestId('chain-source-references');
    expect(references.textContent).toContain('ibkr.option-chain:real:spot');
    expect(references.textContent).toContain('ibkr.option-chain:real:0');
    expect(document.body.textContent).not.toContain('synthetic-dev');
    expect(document.body.textContent).not.toContain('données SYNTHÉTIQUES de développement');
    expect(screen.getByTestId('chain-population-limit').textContent).toContain('REAL');
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(false);
  });

  it('population inconnue : consultation conservée, transfert bloqué', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain({ population: 'UNKNOWN_SOURCE' })));
    await renderOptions();

    await screen.findByText('NATURE NON RECONNUE');
    expect(screen.getByRole('table', { name: /SYN-TECH-01$/ })).toBeDefined();
    await user.click(
      screen.getAllByRole('button', { name: /Inspecter CALL strike 100\.00/ })[0]!,
    );
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(true);
    expect(
      screen.getByText(/Transfert bloqué : la population publiée n'est ni REAL ni SYNTHETIC/),
    ).toBeDefined();
  });

  it('quote OK sans ask : consultation conservée, aucune prime suggérée au Simulateur', async () => {
    const user = userEvent.setup();
    const base = makeOptionChain();
    const firstGroup = base.expirations[0]!;
    const firstContract = firstGroup.contracts[0]!;
    const withoutAsk = makeOptionChain({
      expirations: [
        {
          ...firstGroup,
          contracts: [
            {
              ...firstContract,
              quote: { ...firstContract.quote, ask: null, status: 'OK' },
            },
          ],
        },
      ],
    });
    repondre(jsonResponse(withoutAsk));
    await renderOptions();

    expect(await screen.findByRole('table', { name: /SYN-TECH-01$/ })).toBeDefined();
    await user.click(screen.getByRole('button', { name: /Inspecter CALL strike 100\.00/ }));
    const transfer = await screen.findByRole('button', { name: 'Envoyer au Simulateur' });
    expect((transfer as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Transfert bloqué : ask non publié/)).toBeDefined();
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

  it('affiche le SPOT SERVI à sa place, et ne classe aucun strike « à la monnaie »', async () => {
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    const repere = await screen.findByText('spot servi');
    expect(repere).toBeTruthy();
    // Aucun champ ne classe un strike ATM : ce rangement est un jugement du
    // moteur. La table place une valeur PUBLIÉE sur un axe publié, elle
    // n'invente pas une catégorie.
    const table = screen.getByRole('table', { name: /Chaîne d’options|Chaîne d'options/ });
    expect(table.textContent).not.toMatch(/\bATM\b/);
    expect(table.textContent).not.toMatch(/à la monnaie/i);
  });

  it('propose les DOUZE colonnes servies, et en affiche six par défaut', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    const selecteur = await screen.findByText(/Colonnes affichées : 4 sur 12 servies/);
    await user.click(selecteur);
    // `volume` et `open_interest` étaient servis et jetés jusqu'ici.
    expect(screen.getByRole('checkbox', { name: /Volume/ })).toBeTruthy();
    expect(screen.getByRole('checkbox', { name: /Open interest/ })).toBeTruthy();
    expect(screen.getByRole('checkbox', { name: /Gamma/ })).toBeTruthy();
  });

  it('DIT ce que le contrat ne publie pas, au lieu de laisser croire à un oubli', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    await user.click(await screen.findByText(/Colonnes affichées/));
    expect(screen.getByText('Non publiées par le contrat')).toBeTruthy();
    expect(screen.getByText('Spread')).toBeTruthy();
    // Le motif nomme la règle, pas seulement l'absence.
    expect(screen.getByText(/calcul financier dans le navigateur/)).toBeTruthy();
  });

  it('plafonne les colonnes sans jamais bloquer le RETRAIT', async () => {
    const user = userEvent.setup();
    repondre(jsonResponse(makeOptionChain()));
    await renderOptions();
    await user.click(await screen.findByText(/Colonnes affichées/));

    // On ajoute jusqu'au plafond. Le test ne suppose PAS la taille du défaut :
    // il coche des colonnes tant qu'il en reste à cocher, ce qui le rend
    // insensible à un changement de sélection par défaut — c'est justement ce
    // qui l'avait cassé la première fois.
    const aAjouter = ['Volume', 'Open interest', 'Gamma', 'Vega', 'Rho / bp'];
    const ajoutees: string[] = [];
    for (const nom of aAjouter) {
      const cocher = screen.getByRole('checkbox', { name: new RegExp(nom) }) as HTMLInputElement;
      if (cocher.disabled) {
        break;
      }
      await user.click(cocher);
      ajoutees.push(nom);
    }
    expect(screen.getByText(/Colonnes affichées : 7 sur 12 servies/)).toBeTruthy();
    expect(screen.getByText(/Sept colonnes par côté au maximum/)).toBeTruthy();

    // Au plafond, on ne peut plus AJOUTER…
    const restante = aAjouter.find((nom) => !ajoutees.includes(nom));
    expect(restante, 'le plafond doit laisser au moins une colonne non cochée').toBeDefined();
    expect(
      (screen.getByRole('checkbox', { name: new RegExp(restante!) }) as HTMLInputElement).disabled,
    ).toBe(true);

    // …mais on peut toujours RETIRER : on ne piège pas l'utilisateur dans une
    // sélection saturée.
    const derniere = ajoutees[ajoutees.length - 1]!;
    const cochee = screen.getByRole('checkbox', { name: new RegExp(derniere) }) as HTMLInputElement;
    expect(cochee.disabled).toBe(false);
    await user.click(cochee);
    expect(screen.getByText(/Colonnes affichées : 6 sur 12 servies/)).toBeTruthy();
  });

});
