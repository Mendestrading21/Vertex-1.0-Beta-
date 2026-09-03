import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LinearGauge } from './LinearGauge.tsx';

describe('LinearGauge — coordonnées SERVIES', () => {
  it('la largeur est la chaîne servie, telle quelle : aucune arithmétique', () => {
    const { container } = render(
      <LinearGauge
        label="Couverture"
        valuePct="63.40"
        valueText="63,40 %"
        boundsText={{ min: '0 %', max: '100 %' }}
        markers={[{ pct: '80.00', label: 'seuil requis 80 %' }]}
      />,
    );
    const fill = container.querySelector('.vx-w2-gauge-fill') as HTMLElement;
    expect(fill.style.width).toBe('63.4%');
    const marqueur = container.querySelector('.vx-w2-gauge-marker') as HTMLElement;
    expect(marqueur.style.left).toBe('80%');
  });

  it('role=meter avec aria-valuetext servi et bornes affichées', () => {
    render(
      <LinearGauge
        label="Couverture"
        valuePct="63.40"
        valueText="63,40 %"
        boundsText={{ min: '0 %', max: '100 %' }}
        markers={[]}
      />,
    );
    const meter = screen.getByRole('meter');
    expect(meter.getAttribute('aria-valuetext')).toBe('63,40 %');
    expect(meter.getAttribute('aria-valuemin')).toBe('0');
    expect(meter.getAttribute('aria-valuemax')).toBe('100');
    expect(screen.getByText('0 %')).toBeDefined();
    expect(screen.getByText('100 %')).toBeDefined();
  });

  it('position absente : « non calculable » et RAISON servie, aucune barre', () => {
    const { container } = render(
      <LinearGauge
        label="Breadth"
        valuePct={null}
        valueText={null}
        boundsText={{ min: '0 %', max: '100 %' }}
        markers={[]}
        reason="coverage_below_threshold"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('non calculable');
    expect(screen.getByText('coverage_below_threshold').tagName).toBe('CODE');
    expect(container.querySelector('.vx-w2-gauge-fill')).toBeNull();
    expect(container.querySelector('[role="meter"]')).toBeNull();
  });

  it('un segment sans bornes servies n’est pas dessiné', () => {
    const { container } = render(
      <LinearGauge
        label="Couverture"
        valuePct="63.40"
        valueText="63,40 %"
        boundsText={{ min: '0 %', max: '100 %' }}
        markers={[]}
        segments={[
          { fromPct: '0', toPct: '30', name: 'faible' },
          { fromPct: null, toPct: '60', name: 'incomplet' },
        ]}
      />,
    );
    const segments = container.querySelectorAll('.vx-w2-gauge-seg');
    expect(segments).toHaveLength(1);
    expect(segments[0]?.getAttribute('data-name')).toBe('faible');
  });

  it('la méthode servie est nommée, jamais devinée', () => {
    render(
      <LinearGauge
        label="Couverture"
        valuePct="63.40"
        valueText="63,40 %"
        boundsText={{ min: '0 %', max: '100 %' }}
        markers={[]}
        method="market.breadth"
      />,
    );
    expect(screen.getByText('market.breadth').tagName).toBe('CODE');
  });
});
