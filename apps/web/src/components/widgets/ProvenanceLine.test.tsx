import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ProvenanceLine } from './ProvenanceLine.tsx';

describe('ProvenanceLine', () => {
  it('rend la provenance servie : horodatage daté, version, moteur, sources', () => {
    const { container } = render(
      <ProvenanceLine
        asOf="2026-09-03T08:40:00Z"
        snapshotVersion={42290}
        engineVersion="vertex_worker 0.9.1"
        sources={['ibkr', 'sec']}
        method="market.breadth"
        population="REAL"
      />,
    );
    const time = container.querySelector('time');
    expect(time?.getAttribute('dateTime')).toBe('2026-09-03T08:40:00Z');
    const texte = container.textContent ?? '';
    expect(texte).toContain('v42290');
    expect(texte).toContain('vertex_worker 0.9.1');
    expect(texte).toContain('ibkr');
    expect(texte).toContain('sec');
    expect(texte).toContain('market.breadth');
    expect(texte).toContain('REAL');
  });

  it('chaque champ absent est DIT « non publié » à sa place', () => {
    render(
      <ProvenanceLine
        asOf={null}
        snapshotVersion={null}
        engineVersion={null}
        sources={[]}
        method={null}
        population={null}
      />,
    );
    const ligne = screen.getByTestId('provenance-line');
    expect(ligne.querySelectorAll('[data-absent="true"]').length).toBeGreaterThanOrEqual(4);
    expect(ligne.textContent).toContain('non publié');
    expect(ligne.textContent).not.toContain('—');
    expect(ligne.querySelector('time')).toBeNull();
  });
});
