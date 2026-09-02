import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Sparkline, sparklinePoints } from './Sparkline.tsx';

describe('sparklinePoints — géométrie des clôtures publiées, rien d’autre', () => {
  it('un point par clôture, abscisses régulières, ordonnées dans le cadre', () => {
    const points = sparklinePoints(['100.00', '101.50', '99.25', '103.00']);
    expect(points).toHaveLength(4);
    expect(points[0]?.[0]).toBe(0);
    expect(points[3]?.[0]).toBe(120);
    for (const [, y] of points) {
      expect(y).toBeGreaterThanOrEqual(3);
      expect(y).toBeLessThanOrEqual(37);
    }
    // Le maximum est en haut du cadre, le minimum en bas : le tracé lit la série.
    expect(points[3]?.[1]).toBe(3);
    expect(points[2]?.[1]).toBe(37);
  });

  it('série plate : une ligne à mi-hauteur, jamais NaN ; série vide : aucun point', () => {
    const flat = sparklinePoints(['50', '50', '50']);
    expect(new Set(flat.map(([, y]) => y)).size).toBe(1);
    expect(flat.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y))).toBe(true);
    expect(sparklinePoints([])).toHaveLength(0);
    expect(sparklinePoints(['42'])).toEqual([[0, 20]]);
  });
});

describe('Sparkline — un tracé servi, une description lisible, pas de couleur seule', () => {
  it('rend la ligne, la base pointillée, les barres de volume et le libellé', () => {
    const { container, getByRole } = render(
      <Sparkline
        closes={['10', '12', '11']}
        volumes={[100, 400, 200]}
        sign="up"
        label="3 clôtures publiées, première 10, dernière 11"
      />,
    );
    expect(getByRole('img', { name: /3 clôtures publiées/ })).toBeDefined();
    expect(container.querySelector('[data-testid="spark-line"]')?.getAttribute('points')).toContain(',');
    expect(container.querySelectorAll('.vx-spark-vol')).toHaveLength(3);
    expect(container.querySelector('.vx-spark-vol[data-last="true"]')).not.toBeNull();
    expect(container.querySelector('.vx-spark')?.getAttribute('data-sign')).toBe('up');
  });

  it('sans clôture : rien n’est dessiné', () => {
    const { container } = render(<Sparkline closes={[]} volumes={[]} sign="flat" label="vide" />);
    expect(container.querySelector('svg')).toBeNull();
  });
});
