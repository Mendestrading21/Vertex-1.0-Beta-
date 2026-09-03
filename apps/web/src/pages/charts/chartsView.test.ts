import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { CHARTS_MODULES, absentModules, comparisonViewOf, servedModules } from './chartsView.ts';

/**
 * Le catalogue est le CONTRAT de composition de la page : la planche §8 est
 * complète, chaque absence porte un motif du vocabulaire fermé, et aucun
 * module servi ne prétend l'être sans nommer son contrat.
 */
describe('chartsView — catalogue des modules de la planche Graphiques', () => {
  it('porte les douze modules de la planche, sans doublon', () => {
    const ids = CHARTS_MODULES.map((module) => module.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toEqual([
      'main-chart',
      'volume',
      'served-indicators',
      'overlays',
      'rsi',
      'macd',
      'comparison',
      'synchronized',
      'selected-object',
      'linked-alerts',
      'layouts',
      'saved-studies',
    ]);
  });

  it('chaque module a un titre et une question non vides', () => {
    for (const module of CHARTS_MODULES) {
      expect(module.title.trim()).not.toBe('');
      expect(module.question.trim()).not.toBe('');
    }
  });

  it('les modules servis nomment leur contrat ; les absents, un motif fermé et une note', () => {
    for (const module of servedModules()) {
      expect(module.status.kind).toBe('served');
      if (module.status.kind === 'served') {
        expect(module.status.contract).toContain('/api/v1/');
      }
    }
    for (const module of absentModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note.trim()).not.toBe('');
    }
    expect(servedModules().length + absentModules().length).toBe(CHARTS_MODULES.length);
  });

  it('la comparaison base 100 est SERVIE par le contrat Analyse (LOT-S2)', () => {
    // `market.rebased_series` était approuvé, implémenté et sans appelant : le
    // relais existe désormais, la page n'a plus rien à rebaser elle-même.
    const comparison = CHARTS_MODULES.find((module) => module.id === 'comparison');
    expect(comparison?.status).toMatchObject({
      kind: 'served',
      contract: 'GET /api/v1/analysis/{instrument}',
    });
  });

  it('aucun module absent ne porte de chiffre dans sa note (article 17)', () => {
    for (const module of absentModules()) {
      expect(module.status.note).not.toMatch(/\d/);
    }
  });
});


/**
 * `comparisonViewOf` — LECTURE seule du bloc servi. Aucun rebasage, aucun
 * alignement, aucune moyenne : le serveur a déjà tout fait, cette fonction
 * ne fait que nommer ce qu'il publie.
 */
describe('comparisonViewOf — la comparaison base 100 servie, lue sans être recalculée', () => {
  const servie = {
    status: 'OK',
    benchmark: 'SPX',
    unit: 'index',
    base_value: '100',
    currency: 'USD',
    adjustment_basis: 'split_adjusted',
    common_sessions: 2,
    first_trading_day: '2026-08-21',
    last_trading_day: '2026-08-22',
    series: [
      { trading_day: '2026-08-21', instrument: '100.0', benchmark: '100.0' },
      { trading_day: '2026-08-22', instrument: '110.0', benchmark: '120.0' },
    ],
    calculation: { calculation_id: 'market.rebased_series', method: 'base 100' },
    benchmark_calculation: { calculation_id: 'market.rebased_series', method: 'base 100' },
  };

  it('sans indicateurs publiés, il n’y a rien à afficher', () => {
    expect(comparisonViewOf(null).kind).toBe('none');
    expect(comparisonViewOf(undefined).kind).toBe('none');
    expect(comparisonViewOf({}).kind).toBe('none');
  });

  it('un refus serveur est repris TEL QUEL, avec son motif nommé', () => {
    const vue = comparisonViewOf({
      rebased_comparison: {
        status: 'BENCHMARK_NOT_OBSERVED',
        benchmark: 'SPX',
        detail: 'aucune série exploitable admise pour SPX',
      },
    });
    expect(vue).toMatchObject({
      kind: 'absent',
      status: 'BENCHMARK_NOT_OBSERVED',
      benchmark: 'SPX',
      detail: 'aucune série exploitable admise pour SPX',
    });
  });

  it('les enregistrements que le serveur a ÉCARTÉS sont repris, jamais tus', () => {
    const vue = comparisonViewOf({
      rebased_comparison: {
        status: 'BENCHMARK_NOT_OBSERVED',
        benchmark: 'SPX',
        rejected_records: [{ event_id: 'evt-1', reason: 'rights_not_usable' }],
      },
    });
    expect(vue.kind).toBe('absent');
    if (vue.kind === 'absent') {
      expect(vue.rejected).toEqual(['evt-1 — rights_not_usable']);
    }
  });

  it('une comparaison servie porte sa base, ses unités et ses séances', () => {
    const vue = comparisonViewOf({ rebased_comparison: servie });
    expect(vue).toMatchObject({
      kind: 'served',
      benchmark: 'SPX',
      baseValue: '100',
      unit: 'index',
      currency: 'USD',
      adjustmentBasis: 'split_adjusted',
      commonSessions: 2,
      firstTradingDay: '2026-08-21',
      lastTradingDay: '2026-08-22',
    });
  });

  it('chaque point porte SON jour et les DEUX valeurs de ce jour', () => {
    // La page ne peut donc pas apparier deux listes : la structure l'interdit.
    const vue = comparisonViewOf({ rebased_comparison: servie });
    expect(vue.kind).toBe('served');
    if (vue.kind === 'served') {
      expect(vue.points).toEqual([
        { tradingDay: '2026-08-21', instrument: '100.0', benchmark: '100.0' },
        { tradingDay: '2026-08-22', instrument: '110.0', benchmark: '120.0' },
      ]);
    }
  });

  it('une comparaison servie SANS sa base est déclarée illisible, jamais complétée', () => {
    const { base_value: _base, ...ampute } = servie;
    const vue = comparisonViewOf({ rebased_comparison: ampute });
    expect(vue.kind).toBe('unreadable');
  });
});
