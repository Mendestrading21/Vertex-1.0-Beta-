/**
 * `OpportunityTable` — la NATURE d'un dossier, ligne par ligne.
 *
 * DÉFAUT REPRODUIT (7e audit, P1-8). La colonne « Population » imprimait la
 * nature BRUTE — `<code>{candidate.population ?? '—'}</code>` — aux deux
 * emplacements de lignes. Aucun vocabulaire fermé, aucun ton, aucun repli
 * fail-closed, et un mot anglais seul dans une interface française. Combiné à
 * la règle asymétrique du relais (elle, légitime et documentée : une tête
 * prudente au-dessus d'un dossier réel reste SERVIE), cela donnait une ligne
 * lisible « REAL » sous un bandeau « DONNÉES SYNTHÉTIQUES » — et surtout une
 * étiquette forgée (`LIVE`, `IBKR_REALTIME_ENTITLED`) ou absente rendue
 * SILENCIEUSEMENT, au lieu d'avertir.
 *
 * `SyntheticBanner` protège la TÊTE ; il ne protège pas les DOSSIERS. Les
 * tests ci-dessous exigent du composant le MÊME vocabulaire fermé
 * (`POPULATION_NATURES`) et le MÊME repli fail-closed
 * (`resolvePopulationNature`) que le bandeau, sans en dupliquer la table.
 *
 * Ce que ces tests n'affirment PAS : qu'une ligne « DONNÉES RÉELLES » sous un
 * bandeau « DONNÉES SYNTHÉTIQUES » soit une incohérence. C'est un état produit
 * légitime (dégradation vers le plus prudent). Ce qui était fautif est qu'elle
 * n'était ni nommée, ni distincte, ni fail-closed.
 */
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { POPULATION_NATURES } from '../../components/SyntheticBanner.tsx';
import { OpportunityTable } from './OpportunityTable.tsx';
import { candidateOf } from './opportunitiesView.ts';
import type { CandidateView } from './opportunitiesView.ts';

function candidate(overrides: Record<string, unknown> = {}): CandidateView {
  const view = candidateOf({
    ticker: 'SYN-TECH-01',
    sector: 'SYN-TECH',
    advice: { status: 'OBSERVE', direction: 'NEUTRAL' },
    gates: [],
    degraded_gates: [],
    missing_evidence: [],
    required_evidence: {},
    population: 'SYNTHETIC',
    synthetic: true,
    ...overrides,
  });
  if (view === null) {
    throw new Error('fixture SYNTHETIC invalide');
  }
  return view;
}

function renderTable(props: {
  readonly candidates?: readonly CandidateView[];
  readonly contradictory?: readonly CandidateView[];
}) {
  return render(
    <MemoryRouter>
      <OpportunityTable
        group="qualified"
        candidates={props.candidates ?? []}
        emptyMessage="Aucun candidat."
        {...(props.contradictory !== undefined ? { contradictory: props.contradictory } : {})}
      />
    </MemoryRouter>,
  );
}

/** La cellule de nature d'une ligne, repérée par son marqueur dédié. */
function natureCell(row: HTMLElement): HTMLElement {
  const cell = row.querySelector<HTMLElement>('[data-vx-population-cell]');
  if (cell === null) {
    throw new Error('la ligne ne publie aucune cellule de nature');
  }
  return cell;
}

describe('nature d’un DOSSIER : vocabulaire fermé, ton, repli fail-closed', () => {
  it.each(Object.keys(POPULATION_NATURES))(
    'rend la nature déclarée « %s » avec le libellé français du vocabulaire',
    (label) => {
      const nature = POPULATION_NATURES[label as keyof typeof POPULATION_NATURES];
      renderTable({ candidates: [candidate({ population: label, synthetic: false })] });
      const cell = natureCell(screen.getByTestId('opp-row-qualified-SYN-TECH-01'));

      expect(cell.textContent).toContain(nature.label);
      expect(cell.getAttribute('data-vx-nature')).toBe(label);
      expect(cell.getAttribute('data-vx-tone')).toBe(nature.tone);
    },
  );

  it('n’imprime jamais la nature en ANGLAIS SEUL (le défaut P1-8 exact)', () => {
    renderTable({ candidates: [candidate({ population: 'REAL', synthetic: false })] });
    const cell = natureCell(screen.getByTestId('opp-row-qualified-SYN-TECH-01'));

    // ABUSE 1 : la ligne REAL sous une tête prudente est SERVIE — mais elle
    // doit être NOMMÉE en français et portée par le vocabulaire fermé.
    expect(cell.textContent).toContain('DONNÉES RÉELLES');
    expect(cell.getAttribute('data-vx-nature')).toBe('REAL');
  });

  it('les natures déclarées ne partagent jamais un même rendu', () => {
    const labels = Object.keys(POPULATION_NATURES);
    const rendered = new Set<string>();
    for (const label of labels) {
      const view = renderTable({
        candidates: [candidate({ population: label, synthetic: false })],
      });
      const cell = natureCell(screen.getByTestId('opp-row-qualified-SYN-TECH-01'));
      rendered.add(`${cell.getAttribute('data-vx-nature')}|${cell.textContent}`);
      view.unmount();
    }
    expect(rendered.size).toBe(labels.length);
  });

  it('FAIL-CLOSED : une nature absente AVERTIT, elle ne se tait pas', () => {
    renderTable({ candidates: [candidate({ population: null, synthetic: false })] });
    const cell = natureCell(screen.getByTestId('opp-row-qualified-SYN-TECH-01'));

    expect(cell.textContent).toContain('NATURE NON DÉCLARÉE');
    expect(cell.getAttribute('data-vx-nature')).toBe('UNDECLARED');
    expect(cell.getAttribute('data-vx-tone')).toBe('risk');
    expect(cell.textContent).not.toBe('—');
  });

  it.each(['LIVE', 'IBKR_REALTIME_ENTITLED', 'real', 'SYNTHETIC ', 'PRODUCTION'])(
    'FAIL-CLOSED : l’étiquette forgée « %s » est NON RECONNUE, jamais rendue telle quelle',
    (forged) => {
      renderTable({ candidates: [candidate({ population: forged, synthetic: false })] });
      const cell = natureCell(screen.getByTestId('opp-row-qualified-SYN-TECH-01'));

      expect(cell.textContent).toContain('NATURE NON RECONNUE');
      expect(cell.getAttribute('data-vx-nature')).toBe('UNRECOGNISED');
      expect(cell.getAttribute('data-vx-tone')).toBe('risk');
    },
  );

  it('une étiquette hostile est BORNÉE avant d’atteindre le DOM', () => {
    const hostile = 'ACHETEZ MAINTENANT '.repeat(40);
    renderTable({ candidates: [candidate({ population: hostile, synthetic: false })] });
    const cell = natureCell(screen.getByTestId('opp-row-qualified-SYN-TECH-01'));

    expect(cell.getAttribute('data-vx-nature')).toBe('UNRECOGNISED');
    expect(cell.textContent ?? '').not.toContain(hostile);
    expect((cell.textContent ?? '').length).toBeLessThan(hostile.length);
  });

  it('la ligne CONTRADICTOIRE reçoit exactement le même traitement', () => {
    renderTable({
      contradictory: [
        candidate({ ticker: 'SYN-POISON-01', population: 'LIVE', synthetic: false }),
      ],
    });
    const cell = natureCell(screen.getByTestId('opp-contradictory-SYN-POISON-01'));

    expect(cell.textContent).toContain('NATURE NON RECONNUE');
    expect(cell.getAttribute('data-vx-tone')).toBe('risk');
  });

  it('la teinte de la cellule ne vient QUE de tokens Black Glass', () => {
    for (const label of Object.keys(POPULATION_NATURES)) {
      const view = renderTable({
        candidates: [candidate({ population: label, synthetic: false })],
      });
      const cell = natureCell(screen.getByTestId('opp-row-qualified-SYN-TECH-01'));
      const accent = within(cell).getByTestId('opp-population-label');
      expect(accent.style.color).toMatch(/^var\(--vx-[a-z-]+\)$/);
      view.unmount();
    }
  });
});
