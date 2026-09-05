import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { KpiDelta } from './KpiDelta.tsx';
import { signGroupOfText } from './sign.ts';

/**
 * La pastille de variation. Le SIGNE se lit sur la chaîne servie — jamais par
 * une comparaison numérique, jamais par une soustraction.
 *
 * `signGroupOf` (`marketsView.ts`) prend un TICKER : elle ne peut pas servir
 * ici (revue « données », point 4). D'où une fonction de signe SUR CHAÎNE, qui
 * refuse de trancher quand la chaîne n'est pas signée : une chaîne positive
 * sans « + » n'est pas « stable », elle est de signe NON PUBLIÉ.
 */
describe('signGroupOfText — le signe est lu, jamais calculé', () => {
  it.each([
    ['+1,20 %', 'up'],
    ['+0.01', 'up'],
    ['-0,50', 'down'],
    ['-12.4', 'down'],
    ['+0.00', 'flat'],
    ['-0,00', 'flat'],
    ['0.00', 'flat'],
    ['0', 'flat'],
  ] as const)('« %s » → %s', (value, attendu) => {
    expect(signGroupOfText(value)).toBe(attendu);
  });

  it.each(['1,20', '12.4', 'INSUFFICIENT_DATA', ''])(
    'refuse de trancher sur « %s » (signe non publié)',
    (value) => {
      expect(signGroupOfText(value)).toBeNull();
    },
  );
});

describe('KpiDelta', () => {
  it('rend la chaîne servie VERBATIM avec son signe et sa période', () => {
    render(<KpiDelta value="+1,20 %" sign={signGroupOfText('+1,20 %')} period="1 j" />);
    const pastille = screen.getByTestId('kpi-delta');
    expect(pastille.getAttribute('data-sign')).toBe('up');
    expect(pastille.textContent).toContain('+1,20 %');
    expect(pastille.textContent).toContain('1 j');
  });

  it('négatif : data-sign=down et le signe reste dans le TEXTE', () => {
    render(<KpiDelta value="-0,50 %" sign="down" period="1 j" />);
    const pastille = screen.getByTestId('kpi-delta');
    expect(pastille.getAttribute('data-sign')).toBe('down');
    expect(pastille.textContent).toContain('-0,50 %');
  });

  it('valeur absente : « variation non publiée », jamais 0 ni tiret', () => {
    render(<KpiDelta value={null} sign="up" period="1 j" />);
    const pastille = screen.getByTestId('kpi-delta');
    expect(pastille.textContent).toContain('variation non publiée');
    expect(pastille.textContent).not.toMatch(/(^|\s)0(\s|$)/);
    expect(pastille.textContent).not.toContain('—');
    // Un signe SANS valeur est ignoré : il ne colore rien.
    expect(pastille.getAttribute('data-sign')).toBe('unknown');
  });

  it('signe non publié : la pastille le DIT et ne prend aucune couleur de sens', () => {
    render(<KpiDelta value="1,20 %" sign={null} period="1 j" />);
    const pastille = screen.getByTestId('kpi-delta');
    expect(pastille.getAttribute('data-sign')).toBe('unknown');
    expect(pastille.textContent).toContain('signe non publié');
  });

  it('jamais la couleur seule : un glyphe et un texte accompagnent toujours le sens', () => {
    render(<KpiDelta value="+1,20 %" sign="up" period="1 j" />);
    const pastille = screen.getByTestId('kpi-delta');
    expect(pastille.querySelector('[aria-hidden="true"]')?.textContent).toBe('▲');
    expect(pastille.textContent).toContain('En hausse');
  });
});
