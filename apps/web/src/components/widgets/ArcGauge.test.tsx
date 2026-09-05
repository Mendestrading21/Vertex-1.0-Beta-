import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ARC_LENGTH, ArcGauge } from './ArcGauge.tsx';

/**
 * Forme admise par ADR-017 UNIQUEMENT sur une valeur bornée servie dont la
 * POSITION en pourcentage est une coordonnée serveur. Aucun cadran décoratif,
 * aucune aiguille animée : le repère est statique et le chiffre est servi.
 */
describe('ArcGauge — arc gradué sur position servie', () => {
  const base = {
    label: 'Couverture de la fenêtre',
    valuePct: '63.40',
    valueText: '63,40',
    unit: '%',
    boundsText: { min: '0 %', max: '100 %' },
    thresholds: [{ pct: '80.00', label: 'seuil requis' }],
  } as const;

  it('la longueur remplie est la part SERVIE de l’arc', () => {
    const { container } = render(<ArcGauge {...base} />);
    const fill = container.querySelector('.vx-w2-arc-fill') as SVGPathElement;
    const [rempli, reste] = (fill.getAttribute('stroke-dasharray') ?? '').split(' ');
    expect(Number(rempli)).toBeCloseTo(ARC_LENGTH * 0.634, 3);
    expect(Number(reste)).toBeCloseTo(ARC_LENGTH - ARC_LENGTH * 0.634, 3);
  });

  it('role=meter, aria-valuetext servi, chiffre et unité écrits', () => {
    render(<ArcGauge {...base} />);
    const meter = screen.getByRole('meter');
    expect(meter.getAttribute('aria-valuetext')).toBe('63,40 %');
    expect(meter.getAttribute('aria-valuemin')).toBe('0');
    expect(meter.getAttribute('aria-valuemax')).toBe('100');
    expect(screen.getByTestId('arc-figure').textContent).toContain('63,40');
    expect(screen.getByTestId('arc-figure').textContent).toContain('%');
  });

  it('les graduations sont EXACTEMENT les bornes et les seuils servis', () => {
    const { container } = render(<ArcGauge {...base} />);
    // Deux bornes (0 et 100) + un seuil servi.
    expect(container.querySelectorAll('.vx-w2-arc-tick')).toHaveLength(3);
    expect(screen.getByText(/seuil requis/)).toBeDefined();
  });

  it('un repère STATIQUE marque la position servie ; aucune animation', () => {
    const { container } = render(<ArcGauge {...base} />);
    const aiguille = container.querySelector('.vx-w2-arc-needle');
    expect(aiguille).not.toBeNull();
    expect(container.querySelector('animate')).toBeNull();
    expect(container.querySelector('animateTransform')).toBeNull();
  });

  it('position absente : « non calculable » + raison servie, AUCUN arc de remplissage', () => {
    const { container } = render(
      <ArcGauge
        {...base}
        valuePct={null}
        valueText={null}
        reason="coverage_below_threshold"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('non calculable');
    expect(screen.getByText('coverage_below_threshold').tagName).toBe('CODE');
    expect(container.querySelector('.vx-w2-arc-fill')).toBeNull();
    expect(container.querySelector('.vx-w2-arc-needle')).toBeNull();
    // Le rail reste : il dit la forme, pas la valeur.
    expect(container.querySelector('.vx-w2-arc-rail')).not.toBeNull();
  });

  it('statut INVALID servi : même refus, même si une position est publiée', () => {
    const { container } = render(<ArcGauge {...base} status="INVALID" reason="stale_inputs" />);
    expect(container.querySelector('.vx-w2-arc-fill')).toBeNull();
    expect(screen.getByRole('status').textContent).toContain('non calculable');
  });

  it('la teinte est une famille sémantique déclarée, jamais un hex', () => {
    const { container } = render(<ArcGauge {...base} tone="macro" />);
    expect(container.querySelector('.vx-w2-arc')?.getAttribute('data-tone')).toBe('macro');
  });
});
