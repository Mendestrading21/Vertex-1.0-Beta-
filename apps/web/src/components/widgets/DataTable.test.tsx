import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AbsentCell } from '../absence.tsx';
import { DataTable } from './DataTable.tsx';
import type { DataColumn } from './DataTable.tsx';

/**
 * Ce que ces tests exigent, et pourquoi.
 *
 * Une primitive de table peut être « verte » tout en étant illisible : les
 * assertions ci-dessous portent donc sur ce qu'un humain et un lecteur d'écran
 * obtiennent réellement — la légende, les unités, l'ordre publié, l'absence
 * typée, le clavier — et sur les REFUS, qui sont la moitié du contrat.
 */

interface Ligne {
  readonly id: string;
  readonly nom: string;
  readonly prix: string | null;
  readonly variation: string | null;
}

const LIGNES: readonly Ligne[] = [
  { id: 'SYN-A', nom: 'Synthétique A', prix: '111.23', variation: '+1.74 %' },
  { id: 'SYN-B', nom: 'Synthétique B', prix: '53.20', variation: '-0.45 %' },
  { id: 'SYN-C', nom: 'Synthétique C', prix: null, variation: null },
];

const COLONNES: ReadonlyArray<DataColumn<Ligne>> = [
  {
    key: 'nom',
    header: 'Instrument',
    align: 'text',
    rowHeader: true,
    cell: (l) => l.nom,
  },
  {
    key: 'prix',
    header: 'Dernier',
    align: 'num',
    unit: 'CHF',
    cell: (l) =>
      l.prix === null ? <AbsentCell quoi="dernier" nature="not_published" reason={null} /> : <code>{l.prix}</code>,
  },
  {
    key: 'variation',
    header: 'Variation',
    align: 'num',
    unit: '% 1 j',
    cell: (l) =>
      l.variation === null ? (
        <AbsentCell quoi="variation" nature="not_published" reason={null} accord="f" />
      ) : (
        <code>{l.variation}</code>
      ),
    sign: (l) => (l.variation === null ? null : l.variation.startsWith('+') ? 'up' : 'down'),
  },
];

function rendre(surcharge: Partial<Parameters<typeof DataTable<Ligne>>[0]> = {}) {
  return render(
    <DataTable<Ligne>
      id="vx-essai"
      caption="Instruments suivis"
      captionDetail="population SYNTHETIC, 3 instruments"
      columns={COLONNES}
      rows={LIGNES}
      rowKey={(l) => l.id}
      density="standard"
      overflow="none"
      emptyLabel="aucun instrument publié"
      servedOrder={{ by: 'prix', direction: 'desc' }}
      {...surcharge}
    />,
  );
}

describe('DataTable — la primitive unique des tableaux', () => {
  it('rend une légende VISIBLE, pas un aria-label invisible', () => {
    rendre();
    // Les 18 tables héritées portaient un `aria-label` : invisible à l'écran et
    // absent des captures. La légende doit être lisible par les deux.
    const table = screen.getByRole('table');
    expect(within(table).getByText('Instruments suivis')).toBeTruthy();
    expect(table.querySelector('caption')).not.toBeNull();
  });

  it("déclare l'unité de chaque colonne numérique DANS l'en-tête", () => {
    rendre();
    // Une unité au survol seulement serait inatteignable au clavier.
    expect(screen.getByText('CHF')).toBeTruthy();
    expect(screen.getByText('% 1 j')).toBeTruthy();
  });

  it("dit l'ordre SERVI, et le dit aussi quand il n'y en a pas", () => {
    const { unmount } = rendre();
    expect(screen.getByText(/trié par le serveur sur « Dernier », ordre décroissant/)).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: /Dernier/ }).getAttribute('aria-sort')).toBe('descending');
    unmount();

    rendre({ servedOrder: null });
    // Le silence laisserait croire que l'ordre affiché a un sens.
    expect(screen.getByText(/aucun tri publié/)).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: /Dernier/ }).getAttribute('aria-sort')).toBeNull();
  });

  it("n'annonce PAS comme triée une colonne que le serveur n'a pas triée", () => {
    rendre();
    // Poser `aria-sort` partout dirait qu'on peut trier ; le client ne trie pas.
    expect(screen.getByRole('columnheader', { name: /Instrument/ }).getAttribute('aria-sort')).toBeNull();
    expect(screen.getByRole('columnheader', { name: /Variation/ }).getAttribute('aria-sort')).toBeNull();
  });

  it("rend l'identité de ligne en th scope=row", () => {
    rendre();
    const entetes = screen.getAllByRole('rowheader');
    expect(entetes.map((e) => e.textContent)).toEqual(['Synthétique A', 'Synthétique B', 'Synthétique C']);
  });

  it('rend une absence TYPÉE, jamais un zéro ni un tiret nu', () => {
    rendre();
    const absents = document.querySelectorAll('[data-absent="true"]');
    expect(absents.length).toBe(2);
    for (const cellule of absents) {
      // Un tiret sans nom accessible est un tiret ambigu : la porte
      // `no-ambiguous-dash` l'interdit ailleurs, la primitive le garantit ici.
      expect(cellule.getAttribute('aria-label')).toBeTruthy();
    }
    expect(screen.queryByText('0')).toBeNull();
  });

  it('porte le signe SERVI, et aucun signe quand il ne l’est pas', () => {
    rendre();
    const cellules = document.querySelectorAll('[data-sign]');
    expect([...cellules].map((c) => c.getAttribute('data-sign'))).toEqual(['up', 'down']);
  });

  it('nomme l’état vide au lieu de rendre une table sans ligne', () => {
    rendre({ rows: [] });
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.getByRole('status').textContent).toBe('aucun instrument publié');
  });

  it('ouvre une ligne au clavier par un vrai bouton nommé', async () => {
    const ouvrir = vi.fn();
    rendre({ onOpenRow: ouvrir, rowActionLabel: (l: Ligne) => `Ouvrir ${l.nom}` });
    const bouton = screen.getByRole('button', { name: 'Ouvrir Synthétique B' });
    await userEvent.click(bouton);
    expect(ouvrir).toHaveBeenCalledWith('SYN-B');
  });

  it('rend l’enveloppe défilante ATTEIGNABLE au clavier', () => {
    rendre({ overflow: 'panel' });
    // Sans `tabIndex`, une zone défilante est inatteignable sans souris et son
    // contenu devient invisible pour qui navigue au clavier.
    const region = screen.getByRole('region', { name: /Instruments suivis/ });
    expect(region.getAttribute('tabindex')).toBe('0');
  });

  it('REFUSE une table sans exactement un en-tête de ligne', () => {
    const sansIdentite = COLONNES.map((c) => ({ ...c, rowHeader: false })) as ReadonlyArray<DataColumn<Ligne>>;
    // Échouer bruyamment vaut mieux que rendre une table dont aucune ligne n'a
    // d'identité lisible.
    expect(() => rendre({ columns: sansIdentite })).toThrow(/exactement une colonne/);

    const deuxIdentites = COLONNES.map((c) => ({ ...c, rowHeader: true })) as ReadonlyArray<DataColumn<Ligne>>;
    expect(() => rendre({ columns: deuxIdentites })).toThrow(/exactement une colonne/);
  });

  it('REFUSE une ligne ouvrable dont le bouton n’aurait pas de nom', () => {
    expect(() => rendre({ onOpenRow: vi.fn() })).toThrow(/rowActionLabel/);
  });

  it('marque la ligne sélectionnée pour l’œil ET pour le lecteur d’écran', () => {
    rendre({ selectedRowKey: 'SYN-B' });
    const ligne = screen.getByRole('rowheader', { name: 'Synthétique B' }).closest('tr');
    expect(ligne?.getAttribute('data-selected')).toBe('true');
    expect(ligne?.getAttribute('aria-current')).toBe('true');
  });
});
