import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DayBars } from './DayBars.tsx';

const ENTRIES = [
  { key: '2026-09-01', label: 'lun.', value: '4', band: 'positive' },
  { key: '2026-09-02', label: 'mar.', value: '8', band: 'positive' },
  { key: '2026-09-03', label: 'mer.', value: null, band: 'positive' },
  { key: '2026-09-04', label: 'jeu.', value: '2', band: 'inconnue' },
];

describe('DayBars — comptes servis sur rail', () => {
  it('chaque barre a son RAIL, et la barre remplie est proportionnelle', () => {
    const { container } = render(
      <DayBars entries={ENTRIES} unit="événements" ariaLabel="Événements par jour" />,
    );
    expect(container.querySelectorAll('.vx-w2-daybar')).toHaveLength(4);
    const fills = container.querySelectorAll('.vx-w2-daybar-fill');
    // Une absence n'a AUCUNE barre : trois valeurs servies → trois remplissages.
    expect(fills).toHaveLength(3);
    // Le maximum servi occupe toute la hauteur ; le reste en est la part.
    expect((fills[1] as HTMLElement).style.height).toBe('100%');
    expect((fills[0] as HTMLElement).style.height).toBe('50%');
  });

  it('une absence n’est JAMAIS une barre de hauteur zéro', () => {
    const { container } = render(<DayBars entries={ENTRIES} unit="u" ariaLabel="A" />);
    const barres = container.querySelectorAll('.vx-w2-daybar');
    const absente = barres[2] as HTMLElement;
    expect(absente.querySelector('.vx-w2-daybar-fill')).toBeNull();
    expect(absente.getAttribute('data-absent')).toBe('true');
  });

  it('une bande hors du mapping déclaré retombe sur « unknown », visible', () => {
    const { container } = render(
      <DayBars
        entries={ENTRIES}
        unit="u"
        ariaLabel="A"
        bands={{ positive: 'positive' }}
      />,
    );
    const barres = container.querySelectorAll('.vx-w2-daybar');
    expect(barres[0]?.getAttribute('data-band')).toBe('positive');
    expect(barres[3]?.getAttribute('data-band')).toBe('unknown');
  });

  it('aria-current marque le jour courant SERVI', () => {
    const { container } = render(
      <DayBars entries={ENTRIES} unit="u" ariaLabel="A" currentKey="2026-09-02" />,
    );
    const barres = container.querySelectorAll('.vx-w2-daybar');
    expect(barres[1]?.getAttribute('aria-current')).toBe('true');
    expect(barres[0]?.hasAttribute('aria-current')).toBe(false);
  });

  it('table équivalente : une ligne par entrée, « non publié » pour l’absence', () => {
    render(<DayBars entries={ENTRIES} unit="u" ariaLabel="A" />);
    const lignes = screen.getByRole('table').querySelectorAll('tbody tr');
    expect(lignes).toHaveLength(4);
    expect(lignes[2]?.textContent).toContain('non publié');
  });

  it('aucun pourcentage n’est écrit : la proportion se voit, elle ne se chiffre pas', () => {
    const { container } = render(<DayBars entries={ENTRIES} unit="u" ariaLabel="A" />);
    expect(container.textContent).not.toContain('%');
  });

  it('toutes les valeurs absentes : une phrase d’absence, aucune barre', () => {
    const { container } = render(
      <DayBars
        entries={[{ key: 'a', label: 'a', value: null }]}
        unit="u"
        ariaLabel="A"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('Aucune valeur publiée');
    expect(container.querySelectorAll('.vx-w2-daybar-fill')).toHaveLength(0);
  });
});
