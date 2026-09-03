import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { STATUS_CHIP_TONES, StatusChip } from './StatusChip.tsx';

describe('StatusChip', () => {
  it('porte toujours un TEXTE : la couleur ne dit jamais seule', () => {
    render(<StatusChip label="DIFFÉRÉ" tone="warning" icon="◐" />);
    const chip = screen.getByTestId('status-chip');
    expect(chip.textContent).toContain('DIFFÉRÉ');
    expect(chip.getAttribute('data-tone')).toBe('warning');
    expect(chip.querySelector('[aria-hidden="true"]')?.textContent).toBe('◐');
  });

  it('libellé vide : refus visible, jamais un badge muet', () => {
    render(<StatusChip label="" tone="warning" />);
    const chip = screen.getByTestId('status-chip');
    expect(chip.textContent).toContain('libellé non publié');
    expect(chip.getAttribute('data-tone')).toBe('neutral');
  });

  it('le code serveur est rendu en chasse fixe, verbatim', () => {
    render(<StatusChip label="Exclu" tone="negative" code="coverage_below_threshold" />);
    expect(screen.getByText('coverage_below_threshold').tagName).toBe('CODE');
  });

  it('le vocabulaire de teintes est FERMÉ et exclut toute teinte de lien', () => {
    expect([...STATUS_CHIP_TONES].sort()).toEqual(
      ['macro', 'negative', 'neutral', 'option', 'positive', 'warning'].sort(),
    );
  });
});
