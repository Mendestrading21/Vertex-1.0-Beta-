// @vitest-environment node
/**
 * Catalogue de la planche §6 : quatorze modules, servis par un contrat nommé
 * ou absents avec un motif fermé et une note sans chiffre (article 17).
 */
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { SIMULATOR_MODULES, absentSimulatorModules, simulatorModule } from './simulatorModules.ts';

describe('SIMULATOR_MODULES — la planche §6', () => {
  it('compte quatorze modules aux identifiants uniques', () => {
    expect(SIMULATOR_MODULES).toHaveLength(14);
    expect(new Set(SIMULATOR_MODULES.map((module) => module.id)).size).toBe(14);
  });

  it('neuf servis, cinq absents', () => {
    expect(SIMULATOR_MODULES.filter((module) => module.status.kind === 'served')).toHaveLength(9);
    expect(absentSimulatorModules()).toHaveLength(5);
  });

  it('rien de probabiliste n’est servi : Monte-Carlo, probabilité, chocs sont AUCUNE SOURCE', () => {
    for (const id of ['monte-carlo', 'kpi-probabilistic', 'stress-tests']) {
      expect(simulatorModule(id).status.kind === 'absent' && simulatorModule(id).status).toMatchObject({ reason: 'NO_SOURCE' });
    }
    for (const id of ['sensitivity', 'portfolio-impact']) {
      expect(simulatorModule(id).status.kind === 'absent' && simulatorModule(id).status).toMatchObject({ reason: 'SERVER_CONTRACT_MISSING' });
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentSimulatorModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note).not.toMatch(/\d/);
    }
  });

  it('refuse un identifiant inconnu', () => {
    expect(() => simulatorModule('inconnu')).toThrow(/Unknown simulator module/);
  });
});
