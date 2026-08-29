import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { FreshnessBadge, formatAge } from './FreshnessBadge.tsx';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('formatAge — formatage déterministe depuis les props', () => {
  it('distingue âge inconnu (null) et âge invalide (négatif, NaN, infini)', () => {
    expect(formatAge(null)).toBe('âge inconnu');
    expect(formatAge(-1)).toBe('âge invalide');
    expect(formatAge(Number.NaN)).toBe('âge invalide');
    expect(formatAge(Number.POSITIVE_INFINITY)).toBe('âge invalide');
  });

  it('formate secondes, minutes, heures et jours', () => {
    expect(formatAge(0)).toBe('il y a 0 s');
    expect(formatAge(59)).toBe('il y a 59 s');
    expect(formatAge(60)).toBe('il y a 1 min');
    expect(formatAge(3599)).toBe('il y a 59 min');
    expect(formatAge(3600)).toBe('il y a 1 h');
    expect(formatAge(86399)).toBe('il y a 23 h');
    expect(formatAge(86400)).toBe('il y a 1 j');
    expect(formatAge(172800)).toBe('il y a 2 j');
  });
});

describe('FreshnessBadge', () => {
  it("affiche l'âge fourni par props avec la source", () => {
    render(<FreshnessBadge ageSeconds={125} sourceLabel="IBKR différé" />);
    expect(screen.getByText('il y a 2 min')).toBeDefined();
    expect(screen.getByText(/IBKR différé/)).toBeDefined();
  });

  it("affiche « âge inconnu » quand l'âge est null", () => {
    render(<FreshnessBadge ageSeconds={null} />);
    expect(screen.getByText('âge inconnu')).toBeDefined();
  });

  it("ne lit jamais l'horloge du navigateur", () => {
    const nowSpy = vi.spyOn(Date, 'now');
    render(<FreshnessBadge ageSeconds={42} sourceLabel="test" />);
    expect(nowSpy).not.toHaveBeenCalled();
  });
});
