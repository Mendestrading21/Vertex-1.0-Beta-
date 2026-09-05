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

  // LOT P2b — LA PREUVE SERVIE D'UNE ÉTAPE.
  it('preuve servie : les couples clé → valeur sont relayés VERBATIM, dans l’ordre du serveur', () => {
    render(
      <StepList
        ariaLabel="A"
        steps={[
          {
            id: 'minimum_liquidity',
            label: 'minimum_liquidity',
            status: 'BLOCK',
            tone: 'negative',
            code: 'LIQUIDITY_BELOW_MINIMUM',
            evidence: [
              {
                title: 'Observé',
                facts: [
                  { key: 'asset_class', text: 'EQUITY' },
                  // Le moteur publie un `Decimal` ; `model_dump(mode="json")`
                  // le rend en CHAÎNE. La précision servie doit survivre
                  // telle quelle — ni arrondi, ni notation scientifique.
                  { key: 'observed_liquidity', text: '12345.678901234567890' },
                  { key: 'observation_delayed', text: 'false' },
                ],
              },
              { title: 'Seuils', facts: [{ key: 'required_minimum', text: '50000' }] },
            ],
          },
        ]}
      />,
    );
    expect(screen.getByText('Observé')).toBeDefined();
    expect(screen.getByText('Seuils')).toBeDefined();
    expect(screen.getByText('12345.678901234567890').tagName).toBe('CODE');
    expect(screen.getByText('50000').tagName).toBe('CODE');
    // L'ordre du serveur est conservé : aucun tri alphabétique.
    const cles = [...document.querySelectorAll('.vx-w2-step-fact dt')].map((n) => n.textContent);
    expect(cles).toEqual([
      'asset_class',
      'observed_liquidity',
      'observation_delayed',
      'required_minimum',
    ]);
  });

  it('groupe de preuve VIDE : aucun titre orphelin — le silence du serveur ne devient pas une rubrique', () => {
    const { container } = render(
      <StepList
        ariaLabel="A"
        steps={[
          {
            id: 'entitlements_sufficient',
            label: 'entitlements_sufficient',
            status: 'BLOCK',
            tone: 'negative',
            evidence: [
              { title: 'Observé', facts: [] },
              { title: 'Seuils', facts: [] },
            ],
          },
        ]}
      />,
    );
    expect(container.querySelectorAll('.vx-w2-step-evidence')).toHaveLength(0);
    expect(screen.queryByText('Observé')).toBeNull();
  });

  it('valeur servie NON RELAYABLE : « non reconnue », jamais un vide ni un [object Object]', () => {
    render(
      <StepList
        ariaLabel="A"
        steps={[
          {
            id: 'g',
            label: 'g',
            status: 'BLOCK',
            tone: 'negative',
            evidence: [{ title: 'Observé', facts: [{ key: 'nested', text: null }] }],
          },
        ]}
      />,
    );
    // La clé EST publiée : elle reste visible, et l'aveu porte sur la VALEUR.
    expect(screen.getByText('nested')).toBeDefined();
    const absent = screen.getByRole('img');
    expect(absent.getAttribute('aria-label')).toContain('valeur non reconnue');
    expect(document.body.textContent).not.toContain('[object Object]');
  });

  it('aucune étape : l’absence est DITE', () => {
    render(<StepList steps={[]} ariaLabel="A" />);
    expect(screen.getByRole('status').textContent).toContain('Aucune étape publiée');
  });
});
