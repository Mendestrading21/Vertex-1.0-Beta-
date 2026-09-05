import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Metric } from './Metric.tsx';

/**
 * Ce que ces tests gèlent : une mesure servie reste EXACTE dans le document,
 * son unité reste lisible, et une absence ne devient jamais une valeur.
 */
describe('Metric — la valeur est bornée au rendu, l’unité ne l’est jamais', () => {
  it('garde la chaîne SERVIE entière, et l’offre au survol', () => {
    // Le moteur publie ses flottants entiers : mesuré sur Risques, un
    // Herfindahl servi fait vingt-huit chiffres et écrasait sa carte. La
    // chaîne n'est PAS arrondie — seule sa largeur de rendu est bornée.
    const { container } = render(
      <Metric label="Herfindahl" value="0.5020890861513105581980366928" unit="SYN" />,
    );
    const nombre = container.querySelector('.vx-metric-number');
    expect(nombre?.textContent).toBe('0.5020890861513105581980366928');
    expect(nombre?.getAttribute('title')).toBe('0.5020890861513105581980366928');
  });

  it('laisse l’unité HORS de la boîte bornée', () => {
    // Un nombre sans son unité n'est pas une information abrégée, c'est une
    // information fausse — et l'ellipse la mangerait si elle entrait dans la
    // boîte.
    const { container } = render(<Metric label="Herfindahl" value="0.502" unit="SYN" />);
    const nombre = container.querySelector('.vx-metric-number');
    const unite = container.querySelector('.vx-metric-unit');
    expect(unite?.textContent?.trim()).toBe('SYN');
    expect(nombre?.contains(unite ?? null)).toBe(false);
  });

  it('nomme une absence au lieu de la peindre', () => {
    const { container } = render(<Metric label="Herfindahl" value={null} />);
    expect(container.textContent).toContain('non publié');
    expect(container.querySelector('.vx-metric-number')).toBeNull();
  });
});
