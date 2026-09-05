/**
 * LE P&L LATENT NE PEUT PLUS ÊTRE PEINT EN GAIN QUAND IL VAUT ZÉRO.
 *
 * La règle qui vivait ici — `startsWith('-') ? 'negative' : 'positive'` —
 * n'avait pas d'état neutre. Sur un `0.00` servi, elle rendait « positive »,
 * et la feuille de style peignait la cellule EN VERT : un gain affirmé là où
 * le serveur n'en publie aucun.
 *
 * Ce fichier fige la ligne rendue, pas la fonction : c'est le SITE D'APPEL qui
 * avait divergé, et une autorité correcte ne protège rien si la table cesse de
 * l'appeler.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PortfolioTable } from './PortfolioTable.tsx';
import type { ValuedLotRow } from './portfolioView.ts';

function lot(pnl: string, lotId = 'L-1'): ValuedLotRow {
  return {
    lotId,
    ticker: 'SYN-TECH-01',
    currency: 'CHF',
    quantity: '10',
    unitCost: '100.00',
    mark: '100.00',
    marketValue: '1000.00',
    unrealizedPnl: pnl,
  };
}

function signeDuPnl(pnl: string): string | null {
  render(<PortfolioTable lots={[lot(pnl)]} excluded={[]} />);
  const cellule = screen.getByText(pnl);
  return cellule.getAttribute('data-sign');
}

describe('Signe du P&L latent dans la table des lots', () => {
  it('un zéro servi est neutre, jamais un gain', () => {
    expect(signeDuPnl('0.00')).toBe('flat');
  });

  it('un zéro servi SIGNÉ reste neutre', () => {
    expect(signeDuPnl('-0.00')).toBe('flat');
  });

  it('une perte servie est une perte', () => {
    expect(signeDuPnl('-12.40')).toBe('down');
  });

  it('un gain servi est un gain', () => {
    expect(signeDuPnl('+12.40')).toBe('up');
  });

  it("un signe NON publié ne prend aucune couleur de sens", () => {
    // Une chaîne positive sans « + » ne prouve pas un gain : elle prouve que le
    // serveur n'a pas publié de signe. L'attribut est alors absent.
    expect(signeDuPnl('12.40')).toBeNull();
  });

  it('le vocabulaire `positive`/`negative` a disparu du rendu', () => {
    render(<PortfolioTable lots={[lot('-12.40', 'L-9')]} excluded={[]} />);
    expect(document.querySelector("[data-sign='negative']")).toBeNull();
    expect(document.querySelector("[data-sign='positive']")).toBeNull();
  });
});
