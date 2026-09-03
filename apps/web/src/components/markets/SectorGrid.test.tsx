import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { makeMarketsSectors } from '../../test/fixtures.ts';
import { SectorGrid } from './SectorGrid.tsx';

describe('SectorGrid — la carte sectorielle, chaînes serveur verbatim', () => {
  it('une tuile par secteur, comptes couverts/déclarés, une puce signée par instrument', () => {
    const sectors = makeMarketsSectors();
    render(<SectorGrid sectors={sectors} />);
    for (const sector of sectors) {
      const tuile = screen.getByRole('region', { name: sector.label });
      expect(within(tuile).getByText(`${sector.covered_count}/${sector.declared_count} couverts`)).toBeDefined();
      for (const ticker of sector.tickers) {
        const puce = within(tuile).getByText(ticker.ticker).closest('li') as HTMLElement;
        // Le rendement est la chaîne serveur, virgule française, signe conservé.
        expect(puce.textContent).toContain(`${ticker.return_1d_pct.replace('.', ',')} %`);
        expect(puce.getAttribute('data-sign')).toMatch(/^(up|down|flat)$/);
      }
    }
    // Sans `onSelect`, aucune puce n'est un bouton mort.
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });

  it('aucun rendement de SECTEUR n’est affiché : le contrat n’en publie pas', () => {
    render(<SectorGrid sectors={makeMarketsSectors()} />);
    for (const tuile of screen.getAllByRole('region')) {
      const tete = tuile.querySelector('.vx-sector-head') as HTMLElement;
      expect(tete.textContent).not.toMatch(/[+-]\d/);
    }
  });

  it('avec `onSelect`, chaque puce est un bouton pressable qui nomme l’instrument', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const sectors = makeMarketsSectors();
    const premier = sectors[0]!.tickers[0]!.ticker;
    render(<SectorGrid sectors={sectors} selected={premier} onSelect={onSelect} />);
    const boutons = screen.getAllByRole('button');
    expect(boutons.length).toBeGreaterThan(0);
    const presse = boutons.find((bouton) => bouton.getAttribute('aria-pressed') === 'true');
    expect(presse?.textContent).toContain(premier);
    const autre = boutons.find((bouton) => bouton.getAttribute('aria-pressed') === 'false')!;
    await user.click(autre);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('univers vide : un état explicite, rien de dessiné', () => {
    render(<SectorGrid sectors={[]} />);
    expect(screen.getByRole('status').textContent).toContain('Aucun secteur publié');
  });
});
