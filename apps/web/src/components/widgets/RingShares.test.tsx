import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RING_CIRCUMFERENCE, RingQuartet, RingShares } from './RingShares.tsx';

const PARTS = [
  { key: 'AVAILABLE', label: 'Disponible', pct: '42.90', tone: 'silver' as const },
  { key: 'ERROR', label: 'En erreur', pct: '57.10', tone: 'warning' as const },
];

describe('RingShares — anneau de parts servies à chiffre central', () => {
  it('chaque arc a la longueur de sa part SERVIE ; rien n’est additionné', () => {
    const { container } = render(
      <RingShares
        parts={PARTS}
        centerValue="14"
        centerLabel="capacités testées"
        ariaLabel="Répartition des capacités"
      />,
    );
    const arcs = container.querySelectorAll('.vx-w2-ring-arc');
    expect(arcs).toHaveLength(2);
    const premier = (arcs[0]?.getAttribute('stroke-dasharray') ?? '').split(' ');
    expect(Number(premier[0])).toBeCloseTo(RING_CIRCUMFERENCE * 0.429, 3);
    // Le chiffre central est SERVI verbatim, jamais une somme recalculée.
    expect(screen.getByTestId('ring-center').textContent).toContain('14');
    expect(container.textContent).not.toContain('100');
  });

  it('la légende est OBLIGATOIRE et porte les valeurs servies', () => {
    render(
      <RingShares parts={PARTS} centerValue="14" centerLabel="capacités" ariaLabel="A" />,
    );
    const legende = screen.getByRole('list');
    expect(legende.querySelectorAll('li')).toHaveLength(2);
    expect(legende.textContent).toContain('42.90');
    expect(legende.textContent).toContain('57.10');
    expect(legende.textContent).toContain('Disponible');
  });

  it('une part sans pourcentage servi n’est pas dessinée et est DITE « non publié »', () => {
    const { container } = render(
      <RingShares
        parts={[...PARTS, { key: 'X', label: 'Inconnue', pct: null }]}
        centerValue="14"
        centerLabel="capacités"
        ariaLabel="A"
      />,
    );
    expect(container.querySelectorAll('.vx-w2-ring-arc')).toHaveLength(2);
    expect(screen.getByRole('list').textContent).toContain('non publié');
  });

  it('plus de cinq parts : refus explicite (protocole de nuance)', () => {
    const trop = Array.from({ length: 6 }, (_, index) => ({
      key: `k${index}`,
      label: `L${index}`,
      pct: '10.00',
    }));
    const { container } = render(
      <RingShares parts={trop} centerValue="1" centerLabel="x" ariaLabel="A" />,
    );
    expect(screen.getByRole('status').textContent).toContain('trop de parts');
    expect(container.querySelector('svg')).toBeNull();
  });

  it('aucune part servie : l’absence est DITE, aucun anneau vide décoratif', () => {
    const { container } = render(
      <RingShares parts={[]} centerValue={null} centerLabel="x" ariaLabel="A" />,
    );
    expect(screen.getByRole('status').textContent).toContain('Aucune part publiée');
    expect(container.querySelector('svg')).toBeNull();
  });

  it('chiffre central absent : « non publié », jamais un zéro', () => {
    render(
      <RingShares parts={PARTS} centerValue={null} centerLabel="capacités" ariaLabel="A" />,
    );
    const centre = screen.getByTestId('ring-center');
    expect(centre.textContent).toContain('non publié');
    expect(centre.textContent).not.toMatch(/(^|\s)0(\s|$)/);
  });

  it('table équivalente disponible pour la figure', () => {
    render(<RingShares parts={PARTS} centerValue="14" centerLabel="x" ariaLabel="A" />);
    expect(screen.getByRole('table').querySelectorAll('tbody tr')).toHaveLength(2);
  });
});

describe('RingShares — le chiffre central tient DANS le creux de l’anneau', () => {
  // Défaut mesuré sur capture (planche §7) : le Herfindahl servi fait 29
  // caractères. Écrit à la taille d'affichage, il traversait l'anneau de part
  // et d'autre et devenait illisible. L'arrondir aurait produit une valeur que
  // le serveur n'a pas servie ; le tronquer aurait caché des décimales. La
  // primitive DIT donc la densité du chiffre servi, et la feuille de style lui
  // donne le cran typographique qui le fait tenir entier.
  const UNE_PART = [{ key: 'a', label: 'A', ratio: '1' }];

  it('un chiffre court garde la taille d’affichage', () => {
    render(<RingShares parts={UNE_PART} centerValue="14" centerLabel="capacités" ariaLabel="A" />);
    expect(screen.getByTestId('ring-center').getAttribute('data-density')).toBe('short');
  });

  it('un chiffre LONG est annoncé comme tel — et reste ENTIER', () => {
    const servi = '0.5020890861513105581980366928';
    render(
      <RingShares parts={UNE_PART} centerValue={servi} centerLabel="Herfindahl servi" ariaLabel="A" />,
    );
    const centre = screen.getByTestId('ring-center');
    expect(centre.getAttribute('data-density')).toBe('long');
    expect(centre.textContent).toContain(servi);
  });

  it('l’unité servie compte dans la densité — elle occupe la même place', () => {
    render(
      <RingShares
        parts={UNE_PART}
        centerValue="1933.05"
        centerUnit="SYN"
        centerLabel="valeur marquée"
        ariaLabel="A"
      />,
    );
    expect(screen.getByTestId('ring-center').getAttribute('data-density')).toBe('medium');
  });

  it('une absence n’est pas un chiffre long', () => {
    render(<RingShares parts={UNE_PART} centerValue={null} centerLabel="x" ariaLabel="A" />);
    const centre = screen.getByTestId('ring-center');
    expect(centre.getAttribute('data-density')).toBe('medium');
    expect(centre.textContent).toContain('non publié');
  });
});

describe('RingQuartet — quatre anneaux en rangée (référence 26)', () => {
  const anneau = {
    parts: PARTS,
    centerValue: '14',
    centerLabel: 'capacités',
    ariaLabel: 'A',
  };

  it('rend jusqu’à quatre anneaux', () => {
    const { container } = render(
      <RingQuartet rings={[anneau, anneau, anneau, anneau]} ariaLabel="Quatuor" />,
    );
    expect(container.querySelectorAll('.vx-w2-ring')).toHaveLength(4);
  });

  it('refuse un cinquième anneau plutôt que d’en masquer un', () => {
    render(
      <RingQuartet
        rings={[anneau, anneau, anneau, anneau, anneau]}
        ariaLabel="Quatuor"
      />,
    );
    expect(screen.getByRole('status').textContent).toContain('quatre anneaux');
  });
});
