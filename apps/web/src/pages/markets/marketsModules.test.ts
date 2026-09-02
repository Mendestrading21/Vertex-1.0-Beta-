import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { MARKETS_MODULES, absentMarketsModules, marketsModule } from './marketsModules.ts';

describe('catalogue de la planche §2 — Marchés', () => {
  it('porte les douze modules de la planche, identifiants uniques', () => {
    expect(MARKETS_MODULES).toHaveLength(12);
    expect(new Set(MARKETS_MODULES.map((module) => module.id)).size).toBe(12);
  });

  it('cinq modules sont servis par le seul snapshot markets_overview', () => {
    const served = MARKETS_MODULES.filter((module) => module.status.kind === 'served');
    expect(served.map((module) => module.id)).toEqual([
      'breadth',
      'market-health',
      'market-map',
      'sectors',
      'discards',
    ]);
    for (const module of served) {
      expect(module.status.kind === 'served' ? module.status.contract : '').toContain(
        'GET /api/v1/markets/overview',
      );
    }
  });

  it('sept modules sont absents, motif fermé, note sans chiffre', () => {
    const absents = absentMarketsModules();
    expect(absents).toHaveLength(7);
    for (const module of absents) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note, module.id).not.toMatch(/\d/);
    }
    // La courbe des taux n'est PAS « sans source » : un adaptateur existe,
    // c'est le contrat qui manque. Le motif le dit, pas l'inverse.
    expect(marketsModule('rates-curve').status).toMatchObject({ reason: 'SERVER_CONTRACT_MISSING' });
    expect(marketsModule('fx').status).toMatchObject({ reason: 'NO_SOURCE' });
  });

  it('un identifiant inconnu est refusé', () => {
    expect(() => marketsModule('made-up')).toThrow(/Unknown markets module/);
  });
});
