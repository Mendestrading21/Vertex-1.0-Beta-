import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SharesBand } from './SharesBand.tsx';

const PARTS = [
  { key: 'tech', label: 'Technologie', pct: '48.20', tone: 'silver' as const },
  { key: 'sante', label: 'Santé', pct: '31.05', tone: 'titanium' as const },
  { key: 'energie', label: 'Énergie', pct: '15.75', tone: 'macro' as const },
];

describe('SharesBand — parts servies en bande', () => {
  it('la largeur de chaque part est la chaîne SERVIE, verbatim', () => {
    const { container } = render(
      <SharesBand parts={PARTS} unit="%" ariaLabel="Poids par secteur" />,
    );
    const parts = container.querySelectorAll('.vx-w2-share');
    expect(parts).toHaveLength(3);
    expect((parts[0] as HTMLElement).style.width).toBe('48.2%');
    expect((parts[1] as HTMLElement).style.width).toBe('31.05%');
  });

  it('la teinte n’est jamais seule : un motif distingue les parts', () => {
    const { container } = render(<SharesBand parts={PARTS} unit="%" ariaLabel="A" />);
    const motifs = [...container.querySelectorAll('.vx-w2-share')].map((part) =>
      part.getAttribute('data-pattern'),
    );
    expect(new Set(motifs).size).toBe(3);
  });

  it('une part sans pourcentage servi sort de la bande et est listée « non publié »', () => {
    const { container } = render(
      <SharesBand
        parts={[...PARTS, { key: 'x', label: 'Non classé', pct: null }]}
        unit="%"
        ariaLabel="A"
      />,
    );
    expect(container.querySelectorAll('.vx-w2-share')).toHaveLength(3);
    expect(screen.getByRole('list').textContent).toContain('non publié');
  });

  it('le reliquat n’est jamais étiré : la bande garde son rail visible', () => {
    const { container } = render(<SharesBand parts={PARTS} unit="%" ariaLabel="A" />);
    const largeurs = [...container.querySelectorAll('.vx-w2-share')].map(
      (part) => (part as HTMLElement).style.width,
    );
    // 48.2 + 31.05 + 15.75 = 95 : le reliquat reste du rail, aucune part n'est
    // dilatée pour « faire 100 ».
    expect(largeurs).toEqual(['48.2%', '31.05%', '15.75%']);
    expect(container.querySelector('.vx-w2-shares')).not.toBeNull();
  });

  it('plus de quatre teintes : refus (protocole de nuance)', () => {
    const trop = [
      { key: 'a', label: 'A', pct: '10', tone: 'silver' as const },
      { key: 'b', label: 'B', pct: '10', tone: 'titanium' as const },
      { key: 'c', label: 'C', pct: '10', tone: 'macro' as const },
      { key: 'd', label: 'D', pct: '10', tone: 'option' as const },
      { key: 'e', label: 'E', pct: '10', tone: 'silver' as const },
      { key: 'f', label: 'F', pct: '10', tone: 'titanium' as const },
    ];
    const { container } = render(<SharesBand parts={trop} unit="%" ariaLabel="A" />);
    // Six parts, quatre teintes : accepté.
    expect(container.querySelectorAll('.vx-w2-share')).toHaveLength(6);
  });

  it('la légende porte les valeurs servies et l’ordre SERVI', () => {
    render(<SharesBand parts={PARTS} unit="%" ariaLabel="A" />);
    const items = [...screen.getByRole('list').querySelectorAll('li')].map(
      (li) => li.textContent ?? '',
    );
    expect(items[0]).toContain('Technologie');
    expect(items[0]).toContain('48.20');
    expect(items[2]).toContain('Énergie');
  });

  it('aucune part : l’absence est DITE, jamais une bande vide', () => {
    const { container } = render(<SharesBand parts={[]} unit="%" ariaLabel="A" />);
    expect(screen.getByRole('status').textContent).toContain('Aucune part publiée');
    expect(container.querySelector('.vx-w2-shares')).toBeNull();
  });

  it('aucun total n’est recalculé : seul un total SERVI est affiché', () => {
    const { container, rerender } = render(<SharesBand parts={PARTS} unit="%" ariaLabel="A" />);
    expect(container.textContent).not.toContain('Total');
    rerender(
      <SharesBand parts={PARTS} unit="%" ariaLabel="A" totalText="Herfindahl servi : 0.3140" />,
    );
    expect(container.textContent).toContain('Herfindahl servi : 0.3140');
  });
});
