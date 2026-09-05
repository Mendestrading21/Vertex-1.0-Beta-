import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MicroBars } from './MicroBars.tsx';

const BASE = {
  caption: 'Volume par séance',
  unit: 'titres',
  windowLabel: '10 dernières séances',
} as const;

const BARRES = [
  { key: 'j1', heightPct: '20', label: 'lundi', sign: 'up' as const },
  { key: 'j2', heightPct: '80', label: 'mardi', sign: 'down' as const },
  { key: 'j3', heightPct: null, label: 'mercredi' },
];

describe('MicroBars — une distribution servie, sans axe', () => {
  it('dessine chaque barre à la hauteur SERVIE, sans normaliser', () => {
    render(<MicroBars {...BASE} bars={BARRES} />);
    const barres = document.querySelectorAll('.vx-micro-bar');
    // Chercher le maximum pour normaliser aurait été un calcul : le rapport
    // entre deux barres deviendrait une affirmation du navigateur.
    expect((barres[0] as HTMLElement).style.height).toBe('20%');
    expect((barres[1] as HTMLElement).style.height).toBe('80%');
  });

  it('rend une hauteur non publiée en CREUX, jamais à zéro', () => {
    render(<MicroBars {...BASE} bars={BARRES} />);
    const troisieme = document.querySelectorAll('.vx-micro-bar')[2] as HTMLElement;
    expect(troisieme.getAttribute('data-absent')).toBe('true');
    // Une barre à hauteur nulle dirait « mesuré, et vaut zéro ».
    expect(troisieme.style.height).toBe('100%');
  });

  it('nomme les périodes dont la hauteur manque', () => {
    render(<MicroBars {...BASE} bars={BARRES} />);
    const nom = screen.getByRole('img').getAttribute('aria-label') ?? '';
    expect(nom).toContain('1 hauteur(s) non publiée(s) : mercredi');
  });

  it('REFUSE une hauteur hors de [0, 100] au lieu de la tronquer', () => {
    render(<MicroBars {...BASE} bars={[{ key: 'x', heightPct: '150', label: 'x' }]} />);
    expect(document.querySelector('.vx-micro-bar')?.getAttribute('data-absent')).toBe('true');
  });

  it('REFUSE de tracer sans période servie', () => {
    render(<MicroBars {...BASE} windowLabel="" bars={BARRES} />);
    expect(screen.getByRole('status').textContent).toContain('période non publiée');
    expect(document.querySelector('.vx-micro-bars')).toBeNull();
  });

  it('REFUSE de tracer une série vide', () => {
    render(<MicroBars {...BASE} bars={[]} />);
    expect(screen.getByRole('status').textContent).toContain('aucune barre servie');
  });

  it('ne porte de signe que là où il est SERVI', () => {
    render(<MicroBars {...BASE} bars={BARRES} />);
    const barres = [...document.querySelectorAll('.vx-micro-bar')];
    expect(barres.map((b) => b.getAttribute('data-sign'))).toEqual(['up', 'down', null]);
  });
});
