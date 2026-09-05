// @vitest-environment node
/**
 * Catalogue de la planche §3 : quatorze modules, chacun servi par un contrat
 * nommé ou absent avec un motif du vocabulaire fermé et une note SANS
 * chiffre (article 17 : aucun placeholder numérique).
 */
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import {
  OPPORTUNITIES_MODULES,
  absentOpportunitiesModules,
  opportunitiesModule,
} from './opportunitiesModules.ts';

describe('OPPORTUNITIES_MODULES — la planche §3', () => {
  it('compte quatorze modules aux identifiants uniques', () => {
    expect(OPPORTUNITIES_MODULES).toHaveLength(14);
    expect(new Set(OPPORTUNITIES_MODULES.map((module) => module.id)).size).toBe(14);
  });

  it('huit servis, six absents ; chaque servi nomme son contrat', () => {
    const served = OPPORTUNITIES_MODULES.filter((module) => module.status.kind === 'served');
    expect(served).toHaveLength(8);
    expect(absentOpportunitiesModules()).toHaveLength(6);
    for (const module of served) {
      expect(module.status.kind === 'served' && module.status.contract).toMatch(/GET \/api\/v1\//);
    }
  });

  it('aucun score, biais global ni rendement attendu n’est servi : le moteur n’en publie pas', () => {
    for (const id of ['mean-score', 'global-bias', 'expected-return', 'score-return-scatter', 'factor-contribution']) {
      const module = opportunitiesModule(id);
      expect(module.status.kind).toBe('absent');
      expect(module.status.kind === 'absent' && module.status.reason).toBe('NO_SOURCE');
    }
    expect(opportunitiesModule('recent-activity').status.kind === 'absent' && opportunitiesModule('recent-activity').status).toMatchObject({ reason: 'SERVER_CONTRACT_MISSING' });
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentOpportunitiesModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note).not.toMatch(/\d/);
      expect(module.question).toMatch(/\?$/);
    }
  });

  it('refuse un identifiant inconnu', () => {
    expect(() => opportunitiesModule('inconnu')).toThrow(/Unknown opportunities module/);
  });
});
