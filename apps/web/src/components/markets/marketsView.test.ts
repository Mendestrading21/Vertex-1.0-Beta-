import { describe, expect, it } from 'vitest';

import { makeMarketsSectors, makeMarketsTicker } from '../../test/fixtures.ts';
import {
  censusOfNature,
  flattenTickers,
  frDecimal,
  geometryNumber,
  provenanceSentence,
  signGroupOf,
} from './marketsView.ts';

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
  /**
   * CE TEST GELAIT UN DÉFAUT, et il faut le dire.
   *
   * Il exigeait « 0 sinon » — donc qu'une chaîne illisible devienne un zéro.
   * L'intention était honorable : ne jamais laisser un `NaN` atteindre le
   * rendu. Mais la conséquence était pire que le mal évité : une clôture
   * illisible devenait une clôture À ZÉRO, la courbe plongeait sur l'axe, et
   * ce creux se lisait comme un effondrement du cours. Une absence peinte
   * comme une valeur est un fait FAUX, et `.claude/rules/frontend.md`
   * l'interdit nommément — « ne jamais remplacer une donnée absente par 0 ».
   *
   * L'assertion est donc RESSERRÉE, pas desserrée : `null` dit strictement
   * plus que `0`, et il oblige chaque appelant à décider quoi ne pas dessiner.
   * Le `NaN` reste banni — c'était le vrai objet du test d'origine.
   */
  it('parse une chaîne serveur finie, et REFUSE le reste — jamais 0, jamais NaN', () => {
    expect(geometryNumber('35.48')).toBeCloseTo(35.48);
    expect(geometryNumber('pas-un-nombre')).toBeNull();
    expect(geometryNumber('')).toBeNull();
    expect(geometryNumber(null)).toBeNull();
    // Un zéro SERVI reste un zéro : c'est une observation, pas une absence.
    expect(geometryNumber('0')).toBe(0);
    expect(geometryNumber('-0.00')).toBe(-0);
  });
});

describe('censusOfNature / provenanceSentence — §4.1 : la phrase DÉCOULE des données', () => {
  it('tout synthétique : la phrase le dit, avec le compte', () => {
    const census = censusOfNature(makeMarketsSectors());
    expect(census.total).toBe(4);
    expect(census.synthetic).toBe(4);
    expect(census.allSynthetic).toBe(true);
    expect(provenanceSentence(census)).toBe(
      '4 instruments servis, tous déclarés synthétiques par le worker.',
    );
  });

  it('AUCUN synthétique : la phrase ne dit plus « synthétique »', () => {
    // Le cas du poste de travail : 161 instruments IBKR, 0 synthétique. La
    // page écrivait « Carte des marchés synthétiques » par-dessus.
    const reels = makeMarketsSectors().map((sector) => ({
      ...sector,
      tickers: sector.tickers.map((ticker) => ({ ...ticker, synthetic: false })),
    }));
    const census = censusOfNature(reels);
    expect(census.noneSynthetic).toBe(true);
    expect(provenanceSentence(census)).toBe('4 instruments servis, aucun déclaré synthétique.');
    expect(provenanceSentence(census)).not.toContain('synthétiques par le worker');
  });

  it('MIXTE : les deux natures se nomment, elles ne se fondent pas', () => {
    const sectors = makeMarketsSectors();
    const mixtes = sectors.map((sector, index) => ({
      ...sector,
      tickers: sector.tickers.map((ticker) => ({ ...ticker, synthetic: index === 0 })),
    }));
    const census = censusOfNature(mixtes);
    expect(census.allSynthetic).toBe(false);
    expect(census.noneSynthetic).toBe(false);
    expect(provenanceSentence(census)).toContain('deux natures, jamais confondues');
  });

  it('univers VIDE : ni l’un ni l’autre, et la phrase l’avoue', () => {
    const census = censusOfNature([]);
    expect(census.allSynthetic).toBe(false);
    expect(census.noneSynthetic).toBe(false);
    expect(provenanceSentence(census)).toBe(
      'Aucun instrument servi : la nature des données n’est pas déclarée.',
    );
  });
});
