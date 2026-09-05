import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MicroRange } from './MicroRange.tsx';

const BASE = {
  label: 'Volatilité',
  positionPct: '13.7',
  valueText: '14.35',
  lowText: '12.11',
  highText: '28.43',
  unit: 'points',
  windowLabel: '30 jours',
} as const;

describe('MicroRange — situer une valeur dans son amplitude', () => {
  it('place le curseur à la position SERVIE, sans la recalculer', () => {
    render(<MicroRange {...BASE} />);
    // (14.35 − 12.11) / (28.43 − 12.11) = 13,7 %. Ce composant NE FAIT PAS ce
    // calcul : il le recevrait faux dès que l'échelle n'est pas linéaire.
    expect((document.querySelector('.vx-range-cursor') as HTMLElement).style.left).toBe('13.7%');
  });

  it('écrit les TROIS chiffres : la barre situe, elle ne chiffre pas', () => {
    render(<MicroRange {...BASE} />);
    expect(screen.getByText('12.11')).toBeTruthy();
    expect(screen.getByText('14.35')).toBeTruthy();
    expect(screen.getByText('28.43')).toBeTruthy();
  });

  it('REFUSE de placer un curseur sans position servie', () => {
    render(<MicroRange {...BASE} positionPct={null} absentReason="amplitude non publiée sur la période" />);
    expect(document.querySelector('.vx-range-cursor')).toBeNull();
    expect(screen.getByRole('status').textContent).toContain('amplitude non publiée');
  });

  it('REFUSE une position hors amplitude', () => {
    render(<MicroRange {...BASE} positionPct="112" />);
    expect(document.querySelector('.vx-range-cursor')).toBeNull();
  });

  it('nomme la période et l’unité dans le nom accessible', () => {
    render(<MicroRange {...BASE} />);
    const nom = screen.getByRole('img').getAttribute('aria-label') ?? '';
    expect(nom).toContain('sur 30 jours');
    expect(nom).toContain('amplitude de 12.11 à 28.43');
  });
});
