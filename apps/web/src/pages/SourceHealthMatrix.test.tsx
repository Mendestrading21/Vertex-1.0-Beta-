import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { makeCapabilityEntries } from '../test/fixtures.ts';
import { SourceHealthMatrix } from './SourceHealthMatrix.tsx';

function renderMatrix(initialPath = '/sources-reports') {
  const entries = makeCapabilityEntries();
  const view = render(
    <MemoryRouter initialEntries={[initialPath]}>
      <SourceHealthMatrix entries={entries} total={entries.length} />
    </MemoryRouter>,
  );
  return { entries, ...view };
}

function bodyRows(): HTMLElement[] {
  const table = screen.getByRole('table');
  const [, tbody] = table.querySelectorAll('thead, tbody');
  return Array.from((tbody as HTMLElement).querySelectorAll('tr'));
}

describe('SourceHealthMatrix', () => {
  it('rend EXACTEMENT le nombre de lignes reçues (14) avec caption et th scope', () => {
    const { entries } = renderMatrix();
    expect(entries).toHaveLength(14);
    expect(bodyRows()).toHaveLength(14);
    const table = screen.getByRole('table');
    expect(table.querySelector('caption')?.textContent).toContain('14');
    const headers = Array.from(table.querySelectorAll('thead th'));
    expect(headers).toHaveLength(6);
    for (const header of headers) {
      expect(header.getAttribute('scope')).toBe('col');
    }
    expect(screen.getByText('14 capacités affichées sur 14 déclarées')).toBeDefined();
  });

  it('ZÉRO cellule vide : « — » porte un aria-label explicite', () => {
    renderMatrix();
    const table = screen.getByRole('table');
    for (const cell of table.querySelectorAll('tbody td, tbody th')) {
      expect(cell.textContent?.trim()).not.toBe('');
    }
    // LOT T4-7 — « jamais sondé » est un FAIT servi (`tested_at === null`
    // signifie qu'aucune sonde n'a tourné), pas une absence de publication :
    // il se lit en toutes lettres, sans glyphe à expliquer.
    expect(screen.getAllByText('jamais sondé').length).toBeGreaterThan(0);
    // La raison, elle, EST une absence de publication : glyphe dense + nom
    // accessible qui nomme le champ manquant.
    expect(screen.getAllByLabelText('raison non publiée').length).toBeGreaterThan(0);
  });

  it('badges de statut : icône aria-hidden + texte visible du contrat', () => {
    renderMatrix();
    const badge = screen.getAllByText('AVAILABLE')[0]!.closest('.vx-status-badge');
    expect(badge).not.toBeNull();
    const icon = badge!.querySelector('[aria-hidden="true"]');
    expect(icon).not.toBeNull();
    expect(icon!.textContent?.trim()).not.toBe('');
  });

  it('filtre famille : lignes et compteurs cohérents, persistance URL', async () => {
    const user = userEvent.setup();
    const { entries } = renderMatrix();
    const expected = entries.filter((entry) => entry.family === 'market_data').length;
    const familySelect = screen.getByLabelText('Famille');
    await user.selectOptions(familySelect, 'market_data');
    expect(bodyRows()).toHaveLength(expected);
    expect(
      screen.getByText(`${expected} capacités affichées sur ${entries.length} déclarées`),
    ).toBeDefined();
    // Le compteur de l'option reste calculé sur l'ensemble complet reçu.
    expect(
      within(familySelect as HTMLElement).getByText(`market_data (${expected})`),
    ).toBeDefined();
  });

  it('filtre statut initialisé depuis l’URL (persistance)', () => {
    const { entries } = renderMatrix('/sources-reports?statut=DELAYED');
    const expected = entries.filter((entry) => entry.tested_status === 'DELAYED').length;
    expect(expected).toBeGreaterThan(0);
    expect(bodyRows()).toHaveLength(expected);
    const statusSelect = screen.getByLabelText('Statut testé') as HTMLSelectElement;
    expect(statusSelect.value).toBe('DELAYED');
  });

  it('filtres sans résultat : message honnête, jamais une ligne inventée', async () => {
    const user = userEvent.setup();
    const { entries } = renderMatrix();
    const noMatchFamily = entries.find((entry) => entry.family === 'not_provided_by_source');
    expect(noMatchFamily).toBeDefined();
    await user.selectOptions(screen.getByLabelText('Famille'), 'not_provided_by_source');
    await user.selectOptions(screen.getByLabelText('Statut testé'), 'AVAILABLE');
    const combined = entries.filter(
      (entry) => entry.family === 'not_provided_by_source' && entry.tested_status === 'AVAILABLE',
    );
    if (combined.length === 0) {
      /*
        L'ASSERTION EST PLUS FORTE QU'AVANT, PAS PLUS FAIBLE. Elle exigeait une
        table à zéro ligne ; `DataTable` n'en rend AUCUNE et nomme l'absence à
        la place. Un en-tête seul au-dessus du vide laissait le lecteur devant
        une table sans lignes, sans lui dire pourquoi. On vérifie donc les deux
        choses : plus de table du tout, et le message honnête présent.
      */
      expect(screen.queryByRole('table')).toBeNull();
      expect(screen.getByText(/Aucune capacité ne correspond aux filtres actifs/)).toBeDefined();
    } else {
      expect(bodyRows()).toHaveLength(combined.length);
    }
  });
});
