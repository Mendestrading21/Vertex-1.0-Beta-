import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import {
  CHARTS_MODULES,
  absentModules,
  comparisonViewOf,
  indicatorBlockOf,
  indicatorFamilyOf,
  servedModules,
} from './chartsView.ts';

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

  it('overlays, RSI et MACD sont SERVIS par le contrat Analyse (LOT-S6)', () => {
    // DÉFAUT CORRIGÉ. Ces trois modules déclaraient « Aucun calcul … n'est
    // déclaré au registre des calculs ni publié par un snapshot ». C'était
    // vrai avant S6 ; ça ne l'est plus : le worker publie
    // `indicators.overlays.{sma, ema, bollinger_bands}` et
    // `indicators.oscillators.{rsi, macd}`, chacun avec sa série rendue, sa
    // méthode et sa lignée. Une absence qui a cessé d'être vraie est un
    // mensonge, pas une prudence.
    for (const id of ['overlays', 'rsi', 'macd']) {
      const module = CHARTS_MODULES.find((candidate) => candidate.id === id);
      expect(module?.status, id).toMatchObject({
        kind: 'served',
        contract: 'GET /api/v1/analysis/{instrument}',
      });
    }
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

/**
 * `indicatorBlockOf` — LECTURE seule des blocs S6. Trois formes servies, trois
 * refus honnêtes, et un FAIT constaté : les lignes partagent-elles les mêmes
 * séances ? La page choisit sa forme là-dessus, elle ne réaligne rien.
 */
describe('indicatorBlockOf — overlays et oscillateurs servis, lus sans être recalculés', () => {
  const sma = {
    status: 'OK',
    window: 20,
    unit: 'price',
    method: 'trailing arithmetic mean (fsum) over complete windows',
    points: [
      { trading_day: '2026-09-01', value: '101.5' },
      { trading_day: '2026-09-02', value: '102.25' },
    ],
    last: { trading_day: '2026-09-02', value: '102.25' },
    calculation: { calculation_id: 'market.sma', engine_version: 'vertex_core@0.1.0' },
  };

  it('une série simple : ses séances, ses valeurs verbatim, sa lignée', () => {
    const vue = indicatorBlockOf({ sma }, 'sma');
    expect(vue.kind).toBe('served');
    if (vue.kind !== 'served') {
      return;
    }
    expect(vue.unit).toBe('price');
    expect(vue.lines).toHaveLength(1);
    expect(vue.lines[0]?.values).toEqual(['101.5', '102.25']);
    expect(vue.lines[0]?.tradingDays).toEqual(['2026-09-01', '2026-09-02']);
    expect(vue.lines[0]?.last).toBe('102.25');
    expect(vue.lastTradingDay).toBe('2026-09-02');
    expect(vue.calculationId).toBe('market.sma');
    expect(vue.parameters).toEqual([{ label: 'fenêtre', value: '20' }]);
    expect(vue.aligned).toBe(true);
  });

  it('les bandes de Bollinger partagent leurs séances : elles sont ALIGNÉES', () => {
    const vue = indicatorBlockOf(
      {
        bollinger_bands: {
          status: 'OK',
          window: 20,
          num_std: '2',
          unit: 'price',
          bands: ['lower', 'middle', 'upper'],
          points: [
            { trading_day: '2026-09-01', lower: '98', middle: '100', upper: '102' },
            { trading_day: '2026-09-02', lower: '99', middle: '101', upper: '103' },
          ],
        },
      },
      'bollinger_bands',
    );
    expect(vue.kind).toBe('served');
    if (vue.kind !== 'served') {
      return;
    }
    expect(vue.lines.map((ligne) => ligne.label)).toEqual(['lower', 'middle', 'upper']);
    expect(vue.lines[2]?.values).toEqual(['102', '103']);
    expect(vue.aligned).toBe(true);
    expect(vue.parameters).toEqual([
      { label: 'fenêtre', value: '20' },
      { label: 'écarts-types', value: '2' },
    ]);
  });

  it('les trois lignes du MACD commencent à des séances DIFFÉRENTES : non alignées', () => {
    // Le serveur aligne chaque ligne sur la FIN des séances, avec sa propre
    // fenêtre : la ligne MACD commence avant son signal. Les superposer
    // exigerait de les réaligner ici — la vue le DIT au lieu de le faire.
    const vue = indicatorBlockOf(
      {
        macd: {
          status: 'OK',
          windows: { fast: 12, slow: 26, signal: 9 },
          unit: 'price',
          lines: ['macd', 'signal', 'histogram'],
          series: {
            macd: [
              { trading_day: '2026-09-01', value: '1.5' },
              { trading_day: '2026-09-02', value: '1.75' },
            ],
            signal: [{ trading_day: '2026-09-02', value: '1.6' }],
            histogram: [{ trading_day: '2026-09-02', value: '0.15' }],
          },
        },
      },
      'macd',
    );
    expect(vue.kind).toBe('served');
    if (vue.kind !== 'served') {
      return;
    }
    expect(vue.lines.map((ligne) => ligne.label)).toEqual(['macd', 'signal', 'histogram']);
    expect(vue.aligned).toBe(false);
    expect(vue.parameters).toEqual([
      { label: 'fenêtre fast', value: '12' },
      { label: 'fenêtre slow', value: '26' },
      { label: 'fenêtre signal', value: '9' },
    ]);
  });

  it('un échantillon insuffisant est RELAYÉ, jamais complété sur une fenêtre partielle', () => {
    const vue = indicatorBlockOf(
      {
        rsi: {
          status: 'INSUFFICIENT_SAMPLE',
          window: 14,
          available_bars: 4,
          detail: '15 clôtures requises ; 4 disponibles',
        },
      },
      'rsi',
    );
    expect(vue).toEqual({
      kind: 'refused',
      id: 'rsi',
      status: 'INSUFFICIENT_SAMPLE',
      detail: '15 clôtures requises ; 4 disponibles',
    });
  });

  it('un refus du moteur garde son code serveur', () => {
    const vue = indicatorBlockOf({ rsi: { status: 'REFUSED', reason: 'unordered_bars' } }, 'rsi');
    expect(vue).toMatchObject({ kind: 'refused', status: 'REFUSED', detail: 'unordered_bars' });
  });

  it('un bloc absent est absent ; un bloc amputé de son unité est illisible', () => {
    expect(indicatorBlockOf(null, 'sma')).toEqual({ kind: 'none', id: 'sma' });
    expect(indicatorBlockOf({}, 'sma')).toEqual({ kind: 'none', id: 'sma' });
    const { unit: _unit, ...ampute } = sma;
    expect(indicatorBlockOf({ sma: ampute }, 'sma')).toEqual({ kind: 'unreadable', id: 'sma' });
  });

  it('indicatorFamilyOf rend un bloc par identifiant demandé, dans l’ordre', () => {
    const blocs = indicatorFamilyOf({ overlays: { sma } }, 'overlays', ['sma', 'ema']);
    expect(blocs.map((bloc) => bloc.kind)).toEqual(['served', 'none']);
  });
});
