import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../test/render.tsx';
import { ALL_PAGES } from './pages.ts';

/** Pages réellement installées (routes + données + états + tests). */
const INSTALLED_KEYS = new Set([
  'today',
  'markets',
  'sources-reports',
  'options',
  'analysis',
  'simulator',
  'portfolio',
  'risks',
  'catalysts',
  'calendar',
  'opportunities',
  'charts',
]);

describe('routes — couverture du blueprint', () => {
  // L'INVARIANT est « aucune façade » : toute entrée du rail est une page
  // réelle. Il est inchangé.
  it('toute entrée du rail est une page réelle : aucune façade « Lot non installé »', () => {
    const missing = ALL_PAGES.filter((entry) => !INSTALLED_KEYS.has(entry.key)).map(
      (entry) => entry.key,
    );
    expect(missing).toEqual([]);
  });

  // Le COMPTE, lui, dit la vérité du moment. La cible est douze
  // (`references/pages.md`) et le rail en porte douze depuis le LOT-A2
  // (2026-09-02) ; l'arbitrage est journalisé dans
  // docs/05-design/PAGE_ARBITRATION.md. Ce test échoue si une destination
  // apparaît ou disparaît sans que l'arbitrage soit mis à jour — il n'est pas
  // relâché, il est déplacé de « combien » vers « lesquelles ».
  it('le rail porte exactement les douze destinations réelles, dans l’ordre', () => {
    expect(ALL_PAGES.map((entry) => entry.key)).toEqual([
      'today',
      'opportunities',
      'analysis',
      'options',
      'simulator',
      'calendar',
      'markets',
      'charts',
      'portfolio',
      'risks',
      'catalysts',
      'sources-reports',
    ]);
  });

  // Risques est sorti de cette liste le 2026-09-01 : sa route, ses données et
  // ses tests existent, ce qui est EXACTEMENT la condition posée dans
  // app/pages.ts. Sa clé est `risks` au pluriel — celle du blueprint, que
  // `audit_titanium_ledger.py` cherche pour mesurer l'écart à la cible ;
  // un `risk` singulier aurait laissé l'audit annoncer la page manquante.
  // Graphiques a rejoint le rail le 2026-09-02 (LOT-A2) — pas en façade :
  // sa dominante est servie par le contrat Analyse et chaque module sans
  // source est DÉCLARÉ absent avec son motif (`AbsentModule`). La clé est
  // `charts`, celle que `audit_titanium_ledger.py` cherche pour la cible.
  it('la douzième destination, Graphiques, est présente sous sa clé cible', () => {
    const keys = new Set(ALL_PAGES.map((entry) => entry.key));
    expect(keys.has('charts')).toBe(true);
  });
});

describe('routes — pages installées : plus de façade « Lot non installé »', () => {
  for (const page of ALL_PAGES.filter((entry) => INSTALLED_KEYS.has(entry.key))) {
    it(`${page.navPath} → ${page.title} réelle`, async () => {
      renderApp(page.navPath);
      // /markets est chargée paresseusement (React.lazy) : attendre le rendu.
      expect(
        await screen.findByRole('heading', { level: 1, name: page.title }),
      ).toBeDefined();
      expect(screen.getByText(page.question)).toBeDefined();
      expect(screen.queryByText(`NON_IMPLÉMENTÉ — ${page.lot}`)).toBeNull();
    });
  }

  it("/auth rend la page Accès (hors rail, sans façade)", () => {
    renderApp('/auth');
    expect(screen.getByRole('heading', { level: 1, name: 'Accès' })).toBeDefined();
    expect(
      screen.getByRole('button', { name: 'Créer la passkey (premier démarrage)' }),
    ).toBeDefined();
  });

  it('la racine redirige vers /today', () => {
    const { router } = renderApp('/');
    expect(router.state.location.pathname).toBe('/today');
    expect(screen.getByRole('heading', { level: 1, name: "Aujourd'hui" })).toBeDefined();
  });
});

describe('routes — paramètres optionnels arbitrés', () => {
  // Les trois pages sont chargées paresseusement (React.lazy) : attendre.
  it('/analysis/:instrument? accepte un identifiant opaque', async () => {
    renderApp('/analysis/vx-instr-0000');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Analyse' }),
    ).toBeDefined();
  });

  it('/options/:underlying? accepte un identifiant opaque', async () => {
    renderApp('/options/vx-under-0000');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Options' }),
    ).toBeDefined();
  });

  it('/simulator/:id? accepte un identifiant de brouillon', async () => {
    renderApp('/simulator/vx-draft-0000');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Simulateur' }),
    ).toBeDefined();
  });
});

describe('routes — destinations absorbées (docs/05-design/PAGE_ARBITRATION.md)', () => {
  // Règle 5 de l'arbitrage : une route retirée est remplacée par une
  // redirection permanente, jamais par un 404. Sans ce test, la redirection
  // n'est pas prouvée et un signet existant casserait en silence.
  it('/system redirige durablement vers /sources-reports', () => {
    const { router } = renderApp('/system');
    expect(router.state.location.pathname).toBe('/sources-reports');
    expect(
      screen.getByRole('heading', { level: 1, name: 'Sources & Rapports' }),
    ).toBeDefined();
  });

  it("l'ancienne adresse ne laisse pas d'entrée dans l'historique (replace)", () => {
    const { router } = renderApp('/system');
    expect(router.state.historyAction).toBe('REPLACE');
  });
});

describe('routes — inconnues', () => {
  it('une adresse inconnue mène à un état explicite, pas à une autre page', () => {
    renderApp('/inconnue');
    expect(screen.getByRole('heading', { level: 1, name: 'Page introuvable' })).toBeDefined();
  });
});
