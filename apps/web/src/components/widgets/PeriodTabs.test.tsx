import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { PeriodTabs } from './PeriodTabs.tsx';

const OPTIONS = [
  { key: '30', label: '30 barres', available: true },
  { key: '90', label: '90 barres', available: true },
  {
    key: '252',
    label: '252 barres',
    available: false,
    reason: 'Le dossier ne publie que 27 barres.',
  },
];

const LEGEND = 'fenêtres d’affichage des barres servies';

describe('PeriodTabs', () => {
  it('l’option active porte aria-pressed=true, les autres false', () => {
    render(<PeriodTabs options={OPTIONS} value="30" onChange={() => {}} legend={LEGEND} />);
    expect(screen.getByRole('button', { name: /30 barres/ }).getAttribute('aria-pressed')).toBe(
      'true',
    );
    expect(screen.getByRole('button', { name: /90 barres/ }).getAttribute('aria-pressed')).toBe(
      'false',
    );
  });

  it('une option indisponible est DÉSACTIVÉE et son motif reste visible', () => {
    render(<PeriodTabs options={OPTIONS} value="30" onChange={() => {}} legend={LEGEND} />);
    const bouton = screen.getByRole('button', { name: /252 barres/ });
    expect(bouton.hasAttribute('disabled')).toBe(true);
    expect(screen.getByText('Le dossier ne publie que 27 barres.')).toBeDefined();
  });

  it('la légende dit qu’il s’agit d’un choix de VUE, pas d’un fenêtrage de calcul', () => {
    render(<PeriodTabs options={OPTIONS} value="30" onChange={() => {}} legend={LEGEND} />);
    expect(screen.getByText(LEGEND)).toBeDefined();
  });

  it('le clic remonte la clé choisie ; une option indisponible ne remonte rien', () => {
    const onChange = vi.fn();
    render(<PeriodTabs options={OPTIONS} value="30" onChange={onChange} legend={LEGEND} />);
    fireEvent.click(screen.getByRole('button', { name: /90 barres/ }));
    expect(onChange).toHaveBeenCalledWith('90');
    fireEvent.click(screen.getByRole('button', { name: /252 barres/ }));
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('tabindex mobile : seule l’option active est atteignable au clavier', () => {
    render(<PeriodTabs options={OPTIONS} value="90" onChange={() => {}} legend={LEGEND} />);
    expect(screen.getByRole('button', { name: /90 barres/ }).getAttribute('tabindex')).toBe('0');
    expect(screen.getByRole('button', { name: /30 barres/ }).getAttribute('tabindex')).toBe('-1');
  });

  it('les flèches déplacent le choix vers l’option DISPONIBLE suivante', () => {
    // Composant CONTRÔLÉ : le parcours clavier se mesure sur la valeur
    // réellement remontée, pas sur une valeur figée par le test.
    const vues: string[] = [];
    function Controle() {
      const [value, setValue] = useState('30');
      return (
        <PeriodTabs
          options={OPTIONS}
          value={value}
          onChange={(key) => {
            vues.push(key);
            setValue(key);
          }}
          legend={LEGEND}
        />
      );
    }
    render(<Controle />);
    fireEvent.keyDown(screen.getByRole('button', { name: /30 barres/ }), { key: 'ArrowRight' });
    fireEvent.keyDown(screen.getByRole('button', { name: /90 barres/ }), { key: 'ArrowRight' });
    // 252 est INDISPONIBLE : le parcours ne s'y arrête pas, il revient au début.
    expect(vues).toEqual(['90', '30']);
    fireEvent.keyDown(screen.getByRole('button', { name: /30 barres/ }), { key: 'ArrowLeft' });
    expect(vues).toEqual(['90', '30', '90']);
  });

  it('aucune option : le composant est ABSENT (jamais un onglet vide)', () => {
    const { container } = render(
      <PeriodTabs options={[]} value="30" onChange={() => {}} legend={LEGEND} />,
    );
    expect(container.innerHTML).toBe('');
  });
});
