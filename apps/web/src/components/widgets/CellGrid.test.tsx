import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { CellGrid } from './CellGrid.tsx';

const ROWS = [
  { key: 'AAA', label: 'AAA' },
  { key: 'BBB', label: 'BBB' },
];
const COLS = [
  { key: 'AAA', label: 'AAA' },
  { key: 'BBB', label: 'BBB' },
];
const CELLS = [
  { row: 'AAA', col: 'AAA', band: 'self', text: '1.00' },
  { row: 'AAA', col: 'BBB', band: 'strong_positive', text: '0.82' },
  { row: 'BBB', col: 'AAA', band: 'strong_positive', text: '0.82' },
  { row: 'BBB', col: 'BBB', band: 'self', text: '1.00' },
];
const LEGEND = [
  { band: 'self', label: 'diagonale' },
  { band: 'strong_positive', label: 'forte, positive' },
];

describe('CellGrid — matrice de bandes servies', () => {
  it('rend une TABLE sémantique avec en-têtes de ligne et de colonne', () => {
    render(
      <CellGrid rows={ROWS} cols={COLS} cells={CELLS} legend={LEGEND} caption="Corrélations" />,
    );
    const table = screen.getByRole('table');
    expect(table.querySelector('caption')?.textContent).toContain('Corrélations');
    expect(table.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(table.querySelectorAll('thead th')).toHaveLength(3);
  });

  it('la bande servie est portée VERBATIM par data-band', () => {
    const { container } = render(
      <CellGrid rows={ROWS} cols={COLS} cells={CELLS} legend={LEGEND} caption="C" />,
    );
    const cellules = container.querySelectorAll('.vx-w2-cell');
    expect(cellules[0]?.getAttribute('data-band')).toBe('self');
    expect(cellules[1]?.getAttribute('data-band')).toBe('strong_positive');
  });

  it('une bande absente devient « unknown » VISIBLE, jamais un défaut silencieux', () => {
    const { container } = render(
      <CellGrid
        rows={ROWS}
        cols={COLS}
        cells={[{ row: 'AAA', col: 'BBB', band: '', text: '0.10' }]}
        legend={LEGEND}
        caption="C"
      />,
    );
    const sansBande = container.querySelector('[data-band="unknown"]');
    expect(sansBande).not.toBeNull();
    expect(sansBande?.getAttribute('title')).toContain('bande non publiée');
  });

  it('un texte absent est DIT « non publié »', () => {
    render(
      <CellGrid
        rows={ROWS}
        cols={COLS}
        cells={[{ row: 'AAA', col: 'AAA', band: 'self', text: null }]}
        legend={LEGEND}
        caption="C"
      />,
    );
    expect(screen.getAllByText('non publié').length).toBeGreaterThan(0);
  });

  it('la légende des bandes est présente', () => {
    render(<CellGrid rows={ROWS} cols={COLS} cells={CELLS} legend={LEGEND} caption="C" />);
    expect(screen.getByText('forte, positive')).toBeDefined();
  });

  it('onOpenRow : l’en-tête de ligne devient un bouton réel', () => {
    const onOpenRow = vi.fn();
    render(
      <CellGrid
        rows={ROWS}
        cols={COLS}
        cells={CELLS}
        legend={LEGEND}
        caption="C"
        onOpenRow={onOpenRow}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /AAA/ }));
    expect(onOpenRow).toHaveBeenCalledWith('AAA');
  });

  it('la matrice défile dans son propre conteneur, jamais la page', () => {
    const { container } = render(
      <CellGrid rows={ROWS} cols={COLS} cells={CELLS} legend={LEGEND} caption="C" />,
    );
    expect(container.querySelector('.vx-w2-grid-scroll')).not.toBeNull();
  });
});
