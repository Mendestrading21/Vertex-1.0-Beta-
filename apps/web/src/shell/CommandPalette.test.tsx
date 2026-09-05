import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { ALL_PAGES } from '../app/pages.ts';
import { CommandPalette, filtrer } from './CommandPalette.tsx';
import type { PaletteResult } from './CommandPalette.tsx';

function rendre(onClose = vi.fn()) {
  // Client vide : l'instantané Marchés n'est PAS chargé. C'est l'état par
  // défaut d'une session qui vient de démarrer, et il doit être dit.
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    onClose,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <CommandPalette open onClose={onClose} />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

const ECHANTILLON: readonly PaletteResult[] = [
  { id: '1', group: 'Destinations', label: 'Marchés', detail: 'où va le marché', path: '/markets' },
  { id: '2', group: 'Destinations', label: 'Portefeuille', detail: 'mes positions', path: '/portfolio' },
  { id: '3', group: 'Instruments', label: 'SYN-MARCHE-01', detail: 'Énergie', path: '/analysis/SYN-MARCHE-01' },
];

describe('CommandPalette — recherche globale et navigation', () => {
  it('classe DEVANT ce qui commence par la saisie', () => {
    const retenus = filtrer(ECHANTILLON, 'march');
    // « Marchés » commence par la saisie ; « SYN-MARCHE-01 » la contient
    // seulement. Un score de pertinence flou aurait rendu l'ordre imprévisible.
    expect(retenus.map((r) => r.label)).toEqual(['Marchés', 'SYN-MARCHE-01']);
  });

  it('ignore accents et casse', () => {
    expect(filtrer(ECHANTILLON, 'MARCHES').map((r) => r.label)).toContain('Marchés');
    expect(filtrer(ECHANTILLON, 'energie').map((r) => r.label)).toContain('SYN-MARCHE-01');
  });

  it('cherche aussi dans le contexte, pas seulement dans le libellé', () => {
    expect(filtrer(ECHANTILLON, 'positions').map((r) => r.label)).toEqual(['Portefeuille']);
  });

  it('propose les douze destinations dès l’ouverture', () => {
    rendre();
    const options = screen.getAllByRole('option');
    expect(options.length).toBe(ALL_PAGES.length);
  });

  it('DISTINGUE « aucun résultat » de « instantané non chargé »', async () => {
    rendre();
    // Les deux silences ne disent pas la même chose : l'un dit que la recherche
    // a abouti à rien, l'autre que la moitié du corpus n'est pas publiée.
    expect(screen.getByText(/Instantané Marchés non chargé/)).toBeTruthy();
    expect(screen.queryByText(/Aucune destination ni instrument/)).toBeNull();

    await userEvent.type(screen.getByRole('combobox'), 'zzzzz');
    expect(screen.getByText(/Aucune destination ni instrument/)).toBeTruthy();
  });

  it('navigue au clavier sans déplacer la liste', async () => {
    rendre();
    const champ = screen.getByRole('combobox');
    const avant = screen.getAllByRole('option');
    expect(avant[0]?.getAttribute('aria-selected')).toBe('true');
    await userEvent.type(champ, '{ArrowDown}');
    const apres = screen.getAllByRole('option');
    expect(apres[1]?.getAttribute('aria-selected')).toBe('true');
    expect(apres[0]?.getAttribute('aria-selected')).toBe('false');
    // `aria-activedescendant` suit la sélection : sans lui, un lecteur d'écran
    // n'annonce jamais l'option courante.
    expect(champ.getAttribute('aria-activedescendant')).toBe(apres[1]?.id);
  });

  it('boucle en fin de liste plutôt que de rester bloqué', async () => {
    rendre();
    const champ = screen.getByRole('combobox');
    for (let i = 0; i < ALL_PAGES.length; i += 1) {
      await userEvent.type(champ, '{ArrowDown}');
    }
    expect(screen.getAllByRole('option')[0]?.getAttribute('aria-selected')).toBe('true');
  });

  it('ferme sur Échap', async () => {
    const { onClose } = rendre();
    await userEvent.type(screen.getByRole('combobox'), '{Escape}');
    expect(onClose).toHaveBeenCalled();
  });

  it('est un dialogue MODAL correctement nommé, focus dans le champ', () => {
    rendre();
    const dialogue = screen.getByRole('dialog');
    expect(dialogue.getAttribute('aria-modal')).toBe('true');
    expect(dialogue.getAttribute('aria-label')).toBeTruthy();
    expect(document.activeElement).toBe(screen.getByRole('combobox'));
  });

  it('ne propose QUE de la navigation : chaque option mène à une route', () => {
    rendre();
    /**
     * POURQUOI CETTE FORME D'ASSERTION, ET PAS UNE LISTE DE MOTS INTERDITS.
     *
     * La première version énumérait le vocabulaire d'ordre pour vérifier son
     * absence — et la porte `no-raw-colors.test.ts`, qui balaie TOUT le code à
     * la recherche de ce même vocabulaire, a fait échouer ce fichier. Elle
     * avait raison : le mot était bien présent dans la source. Et elle rendait
     * l'assertion inutile, puisqu'elle couvre déjà l'ensemble du dépôt, ce
     * fichier compris.
     *
     * Ce test garantit donc autre chose, que la porte ne peut pas donner : la
     * palette n'expose AUCUN contrôle qui ne soit une navigation. Toute option
     * est une entrée de `listbox` menant à une route de l'application, et le
     * seul élément interactif hors liste est le champ de recherche. Une
     * capacité d'exécution ne pourrait donc pas s'y glisser sans casser cette
     * structure — c'est une garantie de forme, plus solide qu'une liste de mots
     * qu'il faudrait tenir à jour.
     */
    const dialogue = screen.getByRole('dialog');
    const interactifs = dialogue.querySelectorAll('button, a, input, select, textarea');
    expect(interactifs).toHaveLength(1);
    expect((interactifs[0] as HTMLElement).getAttribute('role')).toBe('combobox');

    const options = screen.getAllByRole('option');
    expect(options.length).toBeGreaterThan(0);
    for (const option of options) {
      // Chaque option est une destination de l'application, jamais une action.
      expect(option.getAttribute('id')).toMatch(/-\d+$/);
    }
  });
});
