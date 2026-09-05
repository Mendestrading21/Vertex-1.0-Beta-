import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MiniHeatStrip } from './MiniHeatStrip.tsx';

const LIBELLES = {
  none: 'aucune',
  low: 'faible',
  medium: 'moyenne',
  high: 'forte',
  extreme: 'extrême',
  unknown: 'aucune donnée publiée',
};

const CELLULES = [
  { key: 'd1', band: 'low' as const, label: '2026-09-01', valueText: '0.4' },
  { key: 'd2', band: 'extreme' as const, label: '2026-09-02', valueText: '3.9' },
  { key: 'd3', band: null, label: '2026-09-03' },
];

describe('MiniHeatStrip — bandes NOMMÉES, jamais un dégradé calculé', () => {
  it('rend chaque cellule dans sa bande servie', () => {
    render(<MiniHeatStrip cells={CELLULES} caption="Volatilité quotidienne" unit="%" bandLabels={LIBELLES} />);
    const cellules = [...document.querySelectorAll('.vx-heatstrip-cell')];
    expect(cellules.map((c) => c.getAttribute('data-band'))).toEqual(['low', 'extreme', 'unknown']);
  });

  it('traite l’absence comme UNKNOWN, pas comme la bande la plus basse', () => {
    render(<MiniHeatStrip cells={CELLULES} caption="c" unit="%" bandLabels={LIBELLES} />);
    const troisieme = document.querySelectorAll('.vx-heatstrip-cell')[2] as Element;
    expect(troisieme.getAttribute('data-band')).toBe('unknown');
    expect(troisieme.getAttribute('data-band')).not.toBe('none');
    // Et elle se NOMME : une cellule vide traitée comme « faible » inventerait
    // une mesure.
    expect(troisieme.getAttribute('aria-label')).toContain('aucune donnée publiée');
  });

  it('donne à chaque cellule un nom complet, jamais la couleur seule', () => {
    render(<MiniHeatStrip cells={CELLULES} caption="c" unit="%" bandLabels={LIBELLES} />);
    const premiere = document.querySelectorAll('.vx-heatstrip-cell')[0] as Element;
    expect(premiere.getAttribute('aria-label')).toBe('2026-09-01 : faible — 0.4 %');
  });

  it('compte les périodes sans donnée dans la légende', () => {
    render(<MiniHeatStrip cells={CELLULES} caption="Volatilité" unit="%" bandLabels={LIBELLES} />);
    const nom = (screen.getAllByRole('img')[0] as HTMLElement).getAttribute('aria-label') ?? '';
    expect(nom).toContain('1 période(s) sans donnée publiée');
  });

  it('REFUSE de tracer une bande vide', () => {
    render(<MiniHeatStrip cells={[]} caption="c" unit="%" bandLabels={LIBELLES} />);
    expect(screen.getByRole('status').textContent).toContain('aucune période servie');
  });
});
