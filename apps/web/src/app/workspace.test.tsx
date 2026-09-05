import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { WorkspaceProvider, useWorkspace } from './workspace.tsx';

function Sonde() {
  const espace = useWorkspace();
  return (
    <div>
      <span data-testid="instrument">{espace.activeInstrument ?? 'aucun'}</span>
      <span data-testid="venue">{espace.venue ?? 'aucune'}</span>
      <span data-testid="devise">{espace.currency}</span>
      <span data-testid="fuseau">{espace.timezone}</span>
      <span data-testid="horizon">{espace.horizon ?? 'aucun'}</span>
      <button
        type="button"
        onClick={() => {
          espace.selectInstrument('SYN-TECH-01', 'SYNX');
        }}
      >
        choisir
      </button>
      <button
        type="button"
        onClick={() => {
          espace.setHorizon('6 mois');
        }}
      >
        horizon
      </button>
      <button
        type="button"
        onClick={() => {
          espace.setCurrency('EUR');
        }}
      >
        devise
      </button>
    </div>
  );
}

describe('WorkspaceProvider — le contexte de travail partagé', () => {
  it('n’INVENTE aucun instrument par défaut', () => {
    render(
      <WorkspaceProvider>
        <Sonde />
      </WorkspaceProvider>,
    );
    // Choisir « le premier de la liste » aurait fabriqué une sélection que
    // l'utilisateur n'a pas faite, indiscernable d'un vrai choix.
    expect(screen.getByTestId('instrument').textContent).toBe('aucun');
    expect(screen.getByTestId('venue').textContent).toBe('aucune');
    expect(screen.getByTestId('horizon').textContent).toBe('aucun');
  });

  it('porte les défauts du modèle de contexte : CHF et Europe/Zurich', () => {
    render(
      <WorkspaceProvider>
        <Sonde />
      </WorkspaceProvider>,
    );
    expect(screen.getByTestId('devise').textContent).toBe('CHF');
    expect(screen.getByTestId('fuseau').textContent).toBe('Europe/Zurich');
  });

  it('propage une sélection à TOUS les consommateurs', async () => {
    function Deux() {
      const espace = useWorkspace();
      return <span data-testid="miroir">{espace.activeInstrument ?? 'aucun'}</span>;
    }
    render(
      <WorkspaceProvider>
        <Sonde />
        <Deux />
      </WorkspaceProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'choisir' }));
    // C'est tout l'objet du contexte : huit `useState` locaux ne partageaient
    // rien, et cliquer un instrument sur une page ne disait rien à l'autre.
    expect(screen.getByTestId('instrument').textContent).toBe('SYN-TECH-01');
    expect(screen.getByTestId('miroir').textContent).toBe('SYN-TECH-01');
  });

  it('conserve horizon et devise indépendamment de l’instrument', async () => {
    render(
      <WorkspaceProvider>
        <Sonde />
      </WorkspaceProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'horizon' }));
    await userEvent.click(screen.getByRole('button', { name: 'devise' }));
    await userEvent.click(screen.getByRole('button', { name: 'choisir' }));
    // L'URL ne porte ni horizon ni devise : c'est le contexte qui les tient,
    // et changer d'instrument ne doit pas les effacer.
    expect(screen.getByTestId('horizon').textContent).toBe('6 mois');
    expect(screen.getByTestId('devise').textContent).toBe('EUR');
  });

  it('ne re-rend PAS quand on réécrit la même valeur', () => {
    let rendus = 0;
    function Compteur() {
      const espace = useWorkspace();
      rendus += 1;
      return (
        <button
          type="button"
          onClick={() => {
            espace.adopter('SYN-A', null);
          }}
        >
          adopter
        </button>
      );
    }
    render(
      <WorkspaceProvider>
        <Compteur />
      </WorkspaceProvider>,
    );
    const bouton = screen.getByRole('button');
    act(() => {
      bouton.click();
    });
    const apresPremier = rendus;
    act(() => {
      bouton.click();
    });
    // Adopter la même valeur à chaque rendu de page re-rendrait tous les
    // consommateurs pour rien.
    expect(rendus).toBe(apresPremier);
  });

  it('ÉCHOUE bruyamment hors du fournisseur', () => {
    const silence = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    // Un état par défaut aurait laissé un composant fonctionner en apparence
    // tout en ignorant chaque sélection — le défaut ne se voit qu'à l'usage.
    expect(() => render(<Sonde />)).toThrow(/hors de <WorkspaceProvider>/);
    silence.mockRestore();
  });
});
