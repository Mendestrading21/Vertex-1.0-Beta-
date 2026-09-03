/**
 * Barres de dénombrement : géométrie seule sur des comptes ENTIERS, compte
 * publié à côté de chaque barre, aucun pourcentage écrit, état vide dit.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CensusBars, censusWidths } from './CensusBars.tsx';

describe('censusWidths', () => {
  it('rapporte chaque compte au plus grand, sans dépasser cent', () => {
    expect(censusWidths([24, 12, 0])).toEqual([100, 50, 0]);
  });

  it('tout à zéro : aucune barre, jamais une division par zéro', () => {
    expect(censusWidths([0, 0])).toEqual([0, 0]);
    expect(censusWidths([])).toEqual([]);
  });
});

describe('CensusBars', () => {
  it('rend une ligne par compte, avec le compte publié et le code', () => {
    render(
      <CensusBars
        entries={[
          { key: 'INSUFFICIENT_DATA', count: 24 },
          { key: 'UNKNOWN', label: 'Inconnue', count: 3 },
        ]}
        ariaLabel="Statuts"
        testIdPrefix="census"
      />,
    );
    const first = screen.getByTestId('census-INSUFFICIENT_DATA');
    expect(within(first).getByText('24')).toBeDefined();
    expect(within(first).getByText('INSUFFICIENT_DATA')).toBeDefined();
    const second = screen.getByTestId('census-UNKNOWN');
    expect(within(second).getByText('Inconnue')).toBeDefined();
    expect(within(second).getByText('UNKNOWN')).toBeDefined();
    // Aucun pourcentage n'est écrit : il n'est pas publié.
    expect(screen.getByRole('list').textContent).not.toContain('%');
  });

  it('sans compte : un état vide nommé, pas une liste vide', () => {
    render(<CensusBars entries={[]} ariaLabel="Statuts" emptyLabel="Aucun statut compté." />);
    expect(screen.getByRole('status').textContent).toBe('Aucun statut compté.');
    expect(screen.queryByRole('list')).toBeNull();
  });
});
