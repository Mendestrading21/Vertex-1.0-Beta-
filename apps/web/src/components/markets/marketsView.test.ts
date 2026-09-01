import { describe, expect, it } from 'vitest';

import { makeMarketsSectors, makeMarketsTicker } from '../../test/fixtures.ts';
import { flattenTickers, frDecimal, geometryNumber, signGroupOf } from './marketsView.ts';

describe('signGroupOf — signe TEXTUEL de la chaîne serveur, sans arithmétique', () => {
  it('classe par le signe de return_1d_pct', () => {
    expect(signGroupOf(makeMarketsTicker({ return_1d_pct: '+1.23' }))).toBe('up');
    expect(signGroupOf(makeMarketsTicker({ return_1d_pct: '-0.40' }))).toBe('down');
    expect(signGroupOf(makeMarketsTicker({ return_1d_pct: '+0.00' }))).toBe('flat');
    expect(signGroupOf(makeMarketsTicker({ return_1d_pct: '-0.00' }))).toBe('flat');
    expect(signGroupOf(makeMarketsTicker({ return_1d_pct: '0.00' }))).toBe('flat');
  });
});

describe('flattenTickers', () => {
  it('aplati secteurs → tickers en conservant le libellé de secteur', () => {
    const entries = flattenTickers(makeMarketsSectors());
    expect(entries).toHaveLength(4);
    expect(entries[0]?.sectorLabel).toBe('Énergie synthétique');
    expect(entries.map((entry) => entry.group)).toEqual(['down', 'flat', 'up', 'up']);
  });
});

describe('frDecimal — présentation française', () => {
  it('remplace le point décimal par une virgule sans toucher à la valeur', () => {
    expect(frDecimal('+10.00')).toBe('+10,00');
    expect(frDecimal('110.00')).toBe('110,00');
    expect(frDecimal('50')).toBe('50');
  });
});

describe('geometryNumber — géométrie de rendu uniquement', () => {
  it('parse une chaîne serveur finie, 0 sinon (jamais NaN dans le rendu)', () => {
    expect(geometryNumber('35.48')).toBeCloseTo(35.48);
    expect(geometryNumber('pas-un-nombre')).toBe(0);
  });
});
