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

  it('une figure SANS vocabulaire de bande ne déclare aucune bande', () => {
    // Défaut mesuré sur la planche §8 : le volume n'a pas de bandes — le
    // serveur n'en publie pas et personne n'en attend. Les barres tombaient
    // pourtant sur « unknown », dont la teinte fantôme dit « bande NON
    // publiée » : elles étaient invisibles, et le motif d'absence portait sur
    // une donnée que rien ne devait publier.
    const { container } = render(
      <DayBars
        entries={[
          { key: 'a', label: '2026-08-24', value: '5294000' },
          { key: 'b', label: '2026-08-25', value: '82230' },
        ]}
        unit="titres"
        ariaLabel="Volume par séance"
      />,
    );
    const barres = [...container.querySelectorAll('.vx-w2-daybar')];
    expect(barres).toHaveLength(2);
    for (const barre of barres) {
      expect(barre.getAttribute('data-band')).toBeNull();
    }
  });

  it('un mapping DÉCLARÉ mais une bande non servie reste « unknown », visible', () => {
    const { container } = render(
      <DayBars
        entries={[{ key: 'a', label: 'lun', value: '3' }]}
        unit="jours"
        ariaLabel="x"
        bands={{ served: 'macro' }}
      />,
    );
    expect(
      container.querySelector('.vx-w2-daybar')?.getAttribute('data-band'),
    ).toBe('unknown');
  });
});
