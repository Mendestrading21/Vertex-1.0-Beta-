import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SparkFigure } from './SparkFigure.tsx';

const CLOSES = ['12.10', '12.40', '11.90', '12.55'];
const LABELS = ['2026-08-31', '2026-09-01', '2026-09-02', '2026-09-03'];
const WINDOW = '4 dernières barres servies sur 27';

describe('SparkFigure — figure de série servie', () => {
  it('rend une figure ET sa table équivalente, une ligne par clôture servie', () => {
    render(
      <SparkFigure
        closes={CLOSES}
        labels={LABELS}
        sign="up"
        caption="Clôtures publiées"
        unit="USD"
        windowLabel={WINDOW}
      />,
    );
    expect(screen.getByRole('figure')).toBeDefined();
    const lignes = screen.getByRole('table').querySelectorAll('tbody tr');
    expect(lignes).toHaveLength(CLOSES.length);
    expect(lignes[0]?.textContent).toContain('12.10');
    expect(lignes[3]?.textContent).toContain('12.55');
  });

  it('la légende porte la période SERVIE : une série sans période est refusée', () => {
    const { rerender } = render(
      <SparkFigure closes={CLOSES} sign="up" caption="Clôtures" unit="USD" windowLabel={WINDOW} />,
    );
    expect(screen.getByText(new RegExp(WINDOW))).toBeDefined();

    rerender(
      <SparkFigure closes={CLOSES} sign="up" caption="Clôtures" unit="USD" windowLabel="" />,
    );
    expect(screen.getByRole('status').textContent).toContain('période non publiée');
    expect(screen.queryByRole('figure')).toBeNull();
  });

  it('moins de deux points : « série insuffisante », aucune courbe plate', () => {
    const { container } = render(
      <SparkFigure closes={['12.10']} sign="flat" caption="C" unit="USD" windowLabel={WINDOW} />,
    );
    expect(screen.getByRole('status').textContent).toContain('série insuffisante');
    expect(container.querySelector('svg')).toBeNull();
  });

  it('série vide : l’absence est DITE, jamais un zéro', () => {
    render(<SparkFigure closes={[]} sign="flat" caption="C" unit="USD" windowLabel={WINDOW} />);
    const texte = screen.getByRole('status').textContent ?? '';
    expect(texte).toContain('série insuffisante');
    expect(texte).not.toMatch(/(^|\s)0(\s|$)/);
  });

  it('variante « ligne » : aucun dégradé (canon v1 conservé)', () => {
    const { container } = render(
      <SparkFigure closes={CLOSES} sign="up" caption="C" unit="USD" windowLabel={WINDOW} />,
    );
    expect(container.querySelector('linearGradient')).toBeNull();
  });

  it('variante « aire » (ADR-017) : un dégradé de la teinte vers SA transparence', () => {
    const { container } = render(
      <SparkFigure
        closes={CLOSES}
        sign="up"
        caption="C"
        unit="USD"
        windowLabel={WINDOW}
        variant="area"
        tone="macro"
      />,
    );
    const gradient = container.querySelector('linearGradient');
    expect(gradient).not.toBeNull();
    const stops = gradient?.querySelectorAll('stop') ?? [];
    expect(stops).toHaveLength(2);
    expect(stops[0]?.getAttribute('stop-color')).toBe('var(--vx-macro-gradient-start)');
    expect(stops[1]?.getAttribute('stop-color')).toBe('var(--vx-macro-gradient-end)');
    // Vertical : le fondu descend, il ne traverse pas la figure.
    expect(gradient?.getAttribute('x1')).toBe(gradient?.getAttribute('x2'));
  });

  it('aucun nombre dérivé n’est écrit : ni minimum, ni maximum, ni pourcentage', () => {
    const { container } = render(
      <SparkFigure
        closes={CLOSES}
        labels={LABELS}
        sign="up"
        caption="C"
        unit="USD"
        windowLabel={WINDOW}
      />,
    );
    const texte = container.textContent ?? '';
    for (const close of CLOSES) {
      expect(texte).toContain(close);
    }
    expect(texte).not.toMatch(/%/);
    expect(texte).not.toMatch(/min|max/i);
  });

  it('une série SANS signe financier ne porte aucun signe', () => {
    // Une moyenne mobile, un RSI, une bande de Bollinger n'ont pas de sens
    // financier « en hausse » ou « stable » : ce sont des mesures, pas des
    // variations. Écrire `data-sign="flat"` sur leur figure affirmerait une
    // stabilité que personne n'a publiée.
    const { container } = render(
      <SparkFigure
        closes={CLOSES}
        labels={LABELS}
        sign={null}
        caption="RSI"
        unit="index_0_100"
        windowLabel={WINDOW}
        tone="macro"
      />,
    );
    const figure = container.querySelector('.vx-w2-spark');
    expect(figure).not.toBeNull();
    expect(figure?.getAttribute('data-sign')).toBeNull();
    expect(figure?.getAttribute('data-tone')).toBe('macro');
  });
});
