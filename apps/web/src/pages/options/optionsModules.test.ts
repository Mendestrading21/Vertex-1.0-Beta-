// @vitest-environment node
/**
 * Catalogue de la planche §5 : quinze modules, servis par un contrat nommé
 * ou absents avec un motif fermé et une note sans chiffre (article 17).
 */
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { OPTIONS_MODULES, absentOptionsModules, optionsModule } from './optionsModules.ts';

describe('OPTIONS_MODULES — la planche §5', () => {
  it('compte quinze modules aux identifiants uniques', () => {
    expect(OPTIONS_MODULES).toHaveLength(15);
    expect(new Set(OPTIONS_MODULES.map((module) => module.id)).size).toBe(15);
  });

  it('neuf servis, six absents ; chaque servi nomme son contrat', () => {
    const served = OPTIONS_MODULES.filter((module) => module.status.kind === 'served');
    expect(served).toHaveLength(9);
    expect(absentOptionsModules()).toHaveLength(6);
    for (const module of served) {
      expect(module.status.kind === 'served' && module.status.contract).toMatch(/GET \/api\/v1\//);
    }
  });

  it('composeur et payoff vivent sur Simulateur : DÉCISION EN ATTENTE, pas une seconde saisie', () => {
    for (const id of ['strategy-builder', 'payoff-profile']) {
      const module = optionsModule(id);
      expect(module.status.kind === 'absent' && module.status.reason).toBe('DECISION_PENDING');
    }
    for (const id of ['expected-move', 'iv-reference']) {
      expect(optionsModule(id).status.kind === 'absent' && optionsModule(id).status).toMatchObject({ reason: 'SERVER_CONTRACT_MISSING' });
    }
    for (const id of ['iv-rank', 'strategy-metrics']) {
      expect(optionsModule(id).status.kind === 'absent' && optionsModule(id).status).toMatchObject({ reason: 'NO_SOURCE' });
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentOptionsModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note).not.toMatch(/\d/);
    }
  });

  it('refuse un identifiant inconnu', () => {
    expect(() => optionsModule('inconnu')).toThrow(/Unknown options module/);
  });
});
