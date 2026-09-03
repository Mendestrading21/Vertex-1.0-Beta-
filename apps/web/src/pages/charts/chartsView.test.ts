import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { CHARTS_MODULES, absentModules, servedModules } from './chartsView.ts';

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

  it('la comparaison base 100 est ABSENTE pour contrat serveur manquant, pas pour absence de source', () => {
    // `market.rebased_series` existe et est approuvé ; c'est le RELAIS qui manque.
    // Dire « aucune source » serait faux et orienterait vers le mauvais chantier.
    const comparison = CHARTS_MODULES.find((module) => module.id === 'comparison');
    expect(comparison?.status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
  });

  it('aucun module absent ne porte de chiffre dans sa note (article 17)', () => {
    for (const module of absentModules()) {
      expect(module.status.note).not.toMatch(/\d/);
    }
  });
});
