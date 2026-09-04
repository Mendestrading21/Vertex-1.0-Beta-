import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { BulletMetric } from './BulletMetric.tsx';

const BASE = {
  label: 'Liquidité',
  valuePct: '78',
  valueText: '78',
  unit: 'score /100',
  boundsText: { min: '0', max: '100' },
} as const;

describe('BulletMetric — la mesure préférée à la jauge', () => {
  it('place la valeur à la position SERVIE, sans rien calculer', () => {
    render(<BulletMetric {...BASE} />);
    const remplissage = document.querySelector('.vx-bullet-fill') as HTMLElement | null;
    // 78 % servi ⇒ 78 % de largeur. Aucune division, aucune normalisation.
    expect(remplissage?.style.width).toBe('78%');
  });

  it('REFUSE de dessiner quand la position n’est pas publiée', () => {
    render(<BulletMetric {...BASE} valuePct={null} absentReason="score non calculé : couverture insuffisante" />);
    // Ni barre vide, ni barre à zéro : une barre placée au jugé serait un
    // chiffre inventé.
    expect(document.querySelector('.vx-bullet-fill')).toBeNull();
    expect(screen.getByRole('status').textContent).toContain('couverture insuffisante');
  });

  it('REFUSE une position hors de l’axe plutôt que de la tronquer', () => {
    for (const hors of ['130', '-4', 'n/a']) {
      const { unmount } = render(<BulletMetric {...BASE} valuePct={hors} />);
      // Tronquer à 100 % afficherait une valeur que personne n'a publiée.
      expect(document.querySelector('.vx-bullet-fill')).toBeNull();
      unmount();
    }
  });

  it('écrit la valeur ET les bornes : aucune échelle implicite', () => {
    render(<BulletMetric {...BASE} />);
    expect(screen.getByText('78')).toBeTruthy();
    expect(screen.getByText('score /100')).toBeTruthy();
    expect(screen.getByText('0')).toBeTruthy();
    expect(screen.getByText('100')).toBeTruthy();
  });

  it('porte paliers et cible dans le nom accessible, pas dans un survol', () => {
    render(
      <BulletMetric
        {...BASE}
        bands={[
          { fromPct: '0', toPct: '40', name: 'insuffisant' },
          { fromPct: '40', toPct: '65', name: 'correct' },
          { fromPct: '65', toPct: null, name: 'bon' },
        ]}
        target={{ pct: '70', label: 'objectif 70' }}
      />,
    );
    const nom = screen.getByRole('img').getAttribute('aria-label') ?? '';
    expect(nom).toContain('Liquidité : 78 score /100');
    expect(nom).toContain('axe de 0 à 100');
    expect(nom).toContain('insuffisant, correct, bon');
    expect(nom).toContain('objectif 70');
  });

  it('ignore un palier de largeur nulle au lieu d’empiler des traits invisibles', () => {
    render(
      <BulletMetric
        {...BASE}
        bands={[
          { fromPct: '40', toPct: '40', name: 'vide' },
          { fromPct: '0', toPct: '40', name: 'insuffisant' },
        ]}
      />,
    );
    expect(document.querySelectorAll('.vx-bullet-band')).toHaveLength(1);
  });

  it('ne dessine pas la cible si sa position n’est pas exploitable', () => {
    render(<BulletMetric {...BASE} target={{ pct: 'inconnu', label: 'objectif' }} />);
    expect(document.querySelector('.vx-bullet-target')).toBeNull();
  });

  it('reste NEUTRE par défaut : la couleur se mérite', () => {
    const { unmount } = render(<BulletMetric {...BASE} />);
    expect(document.querySelector('.vx-bullet')?.getAttribute('data-tone')).toBe('neutral');
    unmount();
    render(<BulletMetric {...BASE} tone="positive" />);
    expect(document.querySelector('.vx-bullet')?.getAttribute('data-tone')).toBe('positive');
  });
});
