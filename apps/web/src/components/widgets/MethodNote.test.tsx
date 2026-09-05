import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MethodNote } from './MethodNote.tsx';

/**
 * Ce que ces tests gèlent : la divulgation ne doit jamais devenir une
 * suppression. Le texte replié reste dans le document, et le déclencheur est
 * un contrôle nommé — pas une zone cliquable muette.
 */
describe('MethodNote — repliée, jamais supprimée', () => {
  it('garde méthode ET limites dans le document', () => {
    render(
      <MethodNote
        methode="rendement 1 j calculé par le worker"
        limites="deux clôtures par instrument au minimum"
      />,
    );
    expect(screen.getByText(/rendement 1 j calculé par le worker/)).toBeDefined();
    expect(screen.getByText(/deux clôtures par instrument au minimum/)).toBeDefined();
  });

  it('range les deux derrière UN SEUL contrôle nommé', () => {
    const { container } = render(<MethodNote methode="m" limites="l" />);
    const details = container.querySelectorAll('details');
    expect(details.length, 'un seul repli, pas deux à ouvrir séparément').toBe(1);
    expect(details[0]!.querySelector('summary')?.textContent).toBe('Méthode et limites');
    // Le repli est FERMÉ par défaut : c'est tout l'objet du composant.
    expect(details[0]!.hasAttribute('open')).toBe(false);
  });

  it('garde l’ATTRIBUTION de licence hors du repli', () => {
    // Apache-2.0 exige que la mention accompagne l'œuvre. Derrière un bouton,
    // elle n'accompagne rien : elle attend. La première version de ce
    // composant l'avait repliée, et un test e2e l'a rattrapée.
    const { container } = render(
      <MethodNote
        methode="m"
        limites="l"
        attribution={<a href="https://www.tradingview.com/">TradingView</a>}
      />,
    );
    const lien = screen.getByRole('link', { name: 'TradingView' });
    expect(container.querySelector('details')!.contains(lien)).toBe(false);
  });

  it('nomme laquelle des deux on lit — sans quoi elles se confondent', () => {
    render(<MethodNote methode="m" limites="l" />);
    const etiquettes = screen.getAllByText(/^(Méthode|Limites)$/).map((n) => n.textContent);
    expect(etiquettes).toEqual(['Méthode', 'Limites']);
  });
});
