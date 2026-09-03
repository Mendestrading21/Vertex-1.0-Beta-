import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StepList } from './StepList.tsx';

const GATES = [
  { id: 'bars_available', label: 'Barres disponibles', status: 'PASS', tone: 'positive' as const },
  {
    id: 'entitlements_sufficient',
    label: 'Habilitations suffisantes',
    status: 'UNEVALUABLE',
    tone: 'warning' as const,
    detail: 'Aucune habilitation déclarée pour cette source.',
    code: 'entitlements_sufficient:UNEVALUABLE',
  },
];

describe('StepList', () => {
  it('chaque étape porte un texte ET une pastille de statut', () => {
    render(<StepList steps={GATES} ariaLabel="Portes du candidat" />);
    expect(screen.getByText('Barres disponibles')).toBeDefined();
    expect(screen.getAllByTestId('status-chip')).toHaveLength(2);
    expect(screen.getByText('entitlements_sufficient:UNEVALUABLE').tagName).toBe('CODE');
  });

  it('ordered : la liste est une <ol> ; sinon une <ul>', () => {
    const { container, rerender } = render(<StepList steps={GATES} ariaLabel="A" ordered />);
    expect(container.querySelector('ol')).not.toBeNull();
    rerender(<StepList steps={GATES} ariaLabel="A" />);
    expect(container.querySelector('ul')).not.toBeNull();
  });

  it('statut vide : « statut non publié », jamais une coche muette', () => {
    render(
      <StepList
        steps={[{ id: 'x', label: 'Porte sans statut', status: '', tone: 'neutral' }]}
        ariaLabel="A"
      />,
    );
    expect(screen.getByText(/statut non publié/)).toBeDefined();
  });

  it('aucune étape : l’absence est DITE', () => {
    render(<StepList steps={[]} ariaLabel="A" />);
    expect(screen.getByRole('status').textContent).toContain('Aucune étape publiée');
  });
});
