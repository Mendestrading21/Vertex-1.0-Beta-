import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MultiSeriesArea } from './MultiSeriesArea.tsx';

const X = ['2026-08-31', '2026-09-01', '2026-09-02'];
const SERIES = [
  { key: 'gross', label: 'Valeur brute servie', points: ['100.00', '101.20', '99.80'], tone: 'silver' as const },
  { key: 'net', label: 'Valeur nette servie', points: ['100.00', '100.90', '99.10'], tone: 'macro' as const },
];

describe('MultiSeriesArea — deux ou trois séries SERVIES et alignées', () => {
  it('trace une aire à dégradé par série, de la teinte vers SA transparence', () => {
    const { container } = render(
      <MultiSeriesArea
        series={SERIES}
        xLabels={X}
        ariaLabel="Comparaison"
        caption="Comparaison brute / nette"
        unit="base 100"
        windowLabel="3 points servis"
      />,
    );
    const gradients = container.querySelectorAll('linearGradient');
    expect(gradients).toHaveLength(2);
    expect(gradients[0]?.querySelector('stop')?.getAttribute('stop-color')).toBe(
      'var(--vx-silver-gradient-start)',
    );
    expect(gradients[1]?.querySelector('stop')?.getAttribute('stop-color')).toBe(
      'var(--vx-macro-gradient-start)',
    );
  });

  it('chaque série a un TRAIT distinct : la surface ne porte jamais seule le sens', () => {
    const { container } = render(
      <MultiSeriesArea
        series={SERIES}
        xLabels={X}
        ariaLabel="A"
        caption="C"
        unit="u"
        windowLabel="3 points servis"
      />,
    );
    const traits = [...container.querySelectorAll('.vx-w2-multi-line')].map((line) =>
      line.getAttribute('stroke-dasharray'),
    );
    expect(new Set(traits).size).toBe(2);
  });

  it('la légende nomme chaque série servie', () => {
    render(
      <MultiSeriesArea
        series={SERIES}
        xLabels={X}
        ariaLabel="A"
        caption="C"
        unit="u"
        windowLabel="3 points servis"
      />,
    );
    const legende = screen.getByRole('list');
    expect(legende.textContent).toContain('Valeur brute servie');
    expect(legende.textContent).toContain('Valeur nette servie');
  });

  it('table équivalente : une ligne par abscisse servie, une colonne par série', () => {
    render(
      <MultiSeriesArea
        series={SERIES}
        xLabels={X}
        ariaLabel="A"
        caption="C"
        unit="u"
        windowLabel="3 points servis"
      />,
    );
    const table = screen.getByRole('table');
    expect(table.querySelectorAll('tbody tr')).toHaveLength(3);
    expect(table.querySelectorAll('thead th')).toHaveLength(3);
    expect(table.textContent).toContain('101.20');
  });

  it('séries non alignées : REFUS chiffré, aucune interpolation', () => {
    const { container } = render(
      <MultiSeriesArea
        series={[SERIES[0]!, { ...SERIES[1]!, points: ['100.00', '100.90'] }]}
        xLabels={X}
        ariaLabel="A"
        caption="C"
        unit="u"
        windowLabel="3 points servis"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('séries non alignées');
    expect(container.querySelector('svg')).toBeNull();
  });

  it('moins de deux séries, ou plus de trois : refus', () => {
    const { rerender } = render(
      <MultiSeriesArea
        series={[SERIES[0]!]}
        xLabels={X}
        ariaLabel="A"
        caption="C"
        unit="u"
        windowLabel="w"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('deux séries');
    rerender(
      <MultiSeriesArea
        series={[SERIES[0]!, SERIES[1]!, SERIES[0]!, SERIES[1]!]}
        xLabels={X}
        ariaLabel="A"
        caption="C"
        unit="u"
        windowLabel="w"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('trois séries');
  });

  it('aucun point : l’absence est DITE, jamais un axe vide', () => {
    const { container } = render(
      <MultiSeriesArea
        series={[
          { ...SERIES[0]!, points: [] },
          { ...SERIES[1]!, points: [] },
        ]}
        xLabels={[]}
        ariaLabel="A"
        caption="C"
        unit="u"
        windowLabel="w"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('série insuffisante');
    expect(container.querySelector('svg')).toBeNull();
  });
});
