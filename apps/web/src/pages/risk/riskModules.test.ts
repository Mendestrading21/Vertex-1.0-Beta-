// @vitest-environment node
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { RISK_MODULES, absentRiskModules, riskModule } from './riskModules.ts';

describe('catalogue de la planche §9 (Risques)', () => {
  it('compte dix-neuf modules aux identifiants uniques, sept servis et douze absents', () => {
    expect(RISK_MODULES).toHaveLength(19);
    expect(new Set(RISK_MODULES.map((module) => module.id)).size).toBe(19);
    expect(RISK_MODULES.filter((module) => module.status.kind === 'served')).toHaveLength(7);
    expect(absentRiskModules()).toHaveLength(12);
  });

  it('chaque module servi nomme un contrat API existant', () => {
    for (const module of RISK_MODULES) {
      if (module.status.kind === 'served') {
        expect(module.status.contract, module.id).toMatch(/^GET \/api\/v1\//);
      }
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentRiskModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note, module.id).not.toMatch(/\d/);
      expect(module.status.note.length, module.id).toBeGreaterThan(20);
    }
  });

  it('aucun score global : le score, la VaR et le radar sont absents faute de source', () => {
    for (const id of ['risk-score', 'var-cvar', 'radar']) {
      expect(riskModule(id).status).toMatchObject({ kind: 'absent', reason: 'NO_SOURCE' });
    }
    expect(riskModule('risk-register').status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
    expect(riskModule('correlations').status.kind).toBe('served');
  });

  it('un identifiant inconnu lève', () => {
    expect(() => riskModule('beta')).toThrow(/Unknown risk module/);
  });
});
