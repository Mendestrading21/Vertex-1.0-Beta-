import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SnapshotRail } from './SnapshotRail.tsx';

const AS_OF = '2026-08-30T22:04:05+00:00';

function field(name: string): HTMLElement {
  const element = document.querySelector<HTMLElement>(`[data-vx-snapshot-field="${name}"]`);
  expect(element, `champ snapshot absent : ${name}`).not.toBeNull();
  return element as HTMLElement;
}

function coverageField(name: string): HTMLElement {
  const element = document.querySelector<HTMLElement>(`[data-vx-coverage-field="${name}"]`);
  expect(element, `champ couverture absent : ${name}`).not.toBeNull();
  return element as HTMLElement;
}

describe('SnapshotRail', () => {
  it('affiche les valeurs reçues, y compris les zéros publiés', () => {
    render(
      <SnapshotRail
        snapshotVersion={7}
        asOf={AS_OF}
        population="SYNTHETIC"
        itemCount={0}
        rejectedCount={0}
        coverage={{
          observations_considered: 12,
          clusters: 0,
          ranked: 8,
          published_items: 8,
          truncated_ranked: 0,
        }}
      />,
    );

    expect(within(field('version')).getByText('7')).toBeDefined();
    expect(within(field('population')).getByText('SYNTHETIC')).toBeDefined();
    expect(within(field('item-count')).getByText('0')).toBeDefined();
    expect(within(field('rejected-count')).getByText('0')).toBeDefined();
    expect(within(coverageField('clusters')).getByText('0')).toBeDefined();
    expect(within(coverageField('truncated_ranked')).getByText('0')).toBeDefined();
  });

  it("rend l'horodatage lisible tout en conservant la valeur brute", () => {
    render(
      <SnapshotRail
        snapshotVersion={1}
        asOf={AS_OF}
        population="REAL"
        itemCount={4}
        rejectedCount={1}
        coverage={null}
      />,
    );

    const time = within(field('as-of')).getByRole('time') as HTMLTimeElement;
    expect(time.getAttribute('datetime')).toBe(AS_OF);
    expect(time.getAttribute('title')).toBe(AS_OF);
    expect(time.textContent).toContain('UTC');
    expect(time.textContent).not.toContain(AS_OF);
  });

  it("ne remplace jamais une absence par zéro", () => {
    render(
      <SnapshotRail
        snapshotVersion={null}
        asOf={null}
        population={null}
        itemCount={4}
        rejectedCount={null}
        coverage={null}
      />,
    );

    expect(within(field('version')).getByText('Non publié')).toBeDefined();
    expect(within(field('as-of')).getByText('Non publié')).toBeDefined();
    expect(within(field('population')).getByText('Non publié')).toBeDefined();
    expect(within(field('rejected-count')).getByText('Non publié')).toBeDefined();
    expect(screen.getByText('Couverture non publiée.')).toBeDefined();
    expect(screen.queryByText('0')).toBeNull();

    for (const element of document.querySelectorAll('[data-vx-coverage-field]')) {
      // LOT T4-7 — le nom accessible NOMME désormais la mesure absente :
      // « Non publié » seul ne disait pas de quoi il parlait. Assertion
      // RESSERRÉE sur un libellé plus précis, jamais relâchée.
      expect(
        within(element as HTMLElement).getByRole('img', {
          name: 'dénombrement de couverture non publié',
        }),
      ).toBeDefined();
    }
  });

  it('limite la couverture aux clés fermées et refuse les valeurs non numériques', () => {
    render(
      <SnapshotRail
        snapshotVersion={2}
        asOf={AS_OF}
        population="DELAYED"
        itemCount={3}
        rejectedCount={1}
        coverage={{
          observations_considered: 21,
          clusters: 3,
          ranked: '999',
          published_items: { value: 3 },
          truncated_ranked: null,
          private_unknown_metric: 123_456,
        }}
      />,
    );

    expect(document.querySelectorAll('[data-vx-coverage-field]')).toHaveLength(5);
    expect(within(coverageField('observations_considered')).getByText('21')).toBeDefined();
    expect(within(coverageField('clusters')).getByText('3')).toBeDefined();
    const nomAbsence = 'dénombrement de couverture non publié';
    expect(within(coverageField('ranked')).getByRole('img', { name: nomAbsence })).toBeDefined();
    expect(
      within(coverageField('published_items')).getByRole('img', { name: nomAbsence }),
    ).toBeDefined();
    expect(screen.queryByText('999')).toBeNull();
    expect(screen.queryByText('123456')).toBeNull();
    expect(screen.queryByText('private_unknown_metric')).toBeNull();
  });

  it('conserve un horodatage reçu mais illisible au lieu de le remplacer', () => {
    const malformed = 'horodatage-non-interprété';
    render(
      <SnapshotRail
        snapshotVersion={3}
        asOf={malformed}
        population="DEMO"
        itemCount={1}
        rejectedCount={null}
        coverage={{}}
      />,
    );

    const time = within(field('as-of')).getByRole('time');
    expect(time.getAttribute('datetime')).toBe(malformed);
    expect(time.textContent).toBe(malformed);
  });
});
