import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  CalendarSkeleton,
  ChartSkeleton,
  HeatmapSkeleton,
  InspectorSkeleton,
  MetricSkeleton,
  TableSkeleton,
} from './Skeleton.tsx';

describe('Squelettes — un par forme, jamais un rectangle universel', () => {
  it('ANNONCE ce qui charge, au lieu de laisser une page apparemment vide', () => {
    render(<ChartSkeleton label="Chargement de la carte des marchés" />);
    const statut = screen.getByRole('status');
    expect(statut.getAttribute('aria-busy')).toBe('true');
    // « Chargement… » seul n'informe personne : le libellé dit QUOI.
    expect(statut.getAttribute('aria-label')).toBe('Chargement de la carte des marchés');
  });

  it('réserve une place PROPORTIONNÉE à ce qui arrive', () => {
    const { unmount } = render(<ChartSkeleton label="c" height="large" />);
    expect(document.querySelector('.vx-skel-chart')?.getAttribute('data-height')).toBe('large');
    unmount();
    render(<ChartSkeleton label="c" height="small" />);
    expect(document.querySelector('.vx-skel-chart')?.getAttribute('data-height')).toBe('small');
  });

  it('réserve le NOMBRE DE LIGNES que la page attend vraiment', () => {
    render(<TableSkeleton label="Chargement de la chaîne" rows={12} columns={7} />);
    // Réserver toujours trois lignes recréerait le sursaut qu'on supprime.
    expect(document.querySelectorAll('.vx-skel-row')).toHaveLength(12);
    expect(document.querySelectorAll('.vx-skel-row')[0]?.children).toHaveLength(7);
  });

  it('réserve une grille de sept jours par semaine', () => {
    render(<CalendarSkeleton label="Chargement du calendrier" weeks={6} />);
    expect(document.querySelectorAll('.vx-skel-day')).toHaveLength(42);
  });

  it('réserve une mosaïque pour une heatmap', () => {
    render(<HeatmapSkeleton label="Chargement de la treemap" cells={30} />);
    expect(document.querySelectorAll('.vx-skel-tile')).toHaveLength(30);
  });

  it('réserve un titre et des paires pour l’inspecteur', () => {
    render(<InspectorSkeleton label="Chargement du contrat" facts={4} />);
    expect(document.querySelectorAll('.vx-skel-fact')).toHaveLength(4);
    expect(document.querySelector('.vx-skel-line[data-width="title"]')).not.toBeNull();
  });

  it('rend une métrique en deux lignes : légende puis chiffre', () => {
    render(<MetricSkeleton label="Chargement du régime" />);
    expect(document.querySelectorAll('.vx-skel-metric .vx-skel-line')).toHaveLength(2);
  });

  it('cache la forme aux lecteurs d’écran : seule l’annonce compte', () => {
    render(<TableSkeleton label="Chargement" rows={3} />);
    // Les barres ne sont pas du contenu : les annoncer produirait du bruit.
    expect(document.querySelector('.vx-skel-table')?.getAttribute('aria-hidden')).toBe('true');
  });
});
