// @vitest-environment node
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { CATALYSTS_MODULES, absentCatalystsModules, catalystsModule } from './catalystsModules.ts';

describe('catalogue de la planche §10 (Catalyseurs)', () => {
  it('compte dix-sept modules aux identifiants uniques, onze servis et six absents', () => {
    expect(CATALYSTS_MODULES).toHaveLength(17);
    expect(new Set(CATALYSTS_MODULES.map((module) => module.id)).size).toBe(17);
    expect(CATALYSTS_MODULES.filter((module) => module.status.kind === 'served')).toHaveLength(11);
    expect(absentCatalystsModules()).toHaveLength(6);
  });

  it('chaque module servi nomme un contrat API existant', () => {
    for (const module of CATALYSTS_MODULES) {
      if (module.status.kind === 'served') {
        expect(module.status.contract, module.id).toMatch(/^(GET|POST) \/api\/v1\//);
      }
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentCatalystsModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note, module.id).not.toMatch(/\d/);
      expect(module.status.note.length, module.id).toBeGreaterThan(20);
    }
  });

  it('impact, confiance, surprises et consensus restent absents faute de source', () => {
    for (const id of ['mean-impact', 'confidence', 'surprises', 'surprise-history', 'consensus']) {
      expect(catalystsModule(id).status).toMatchObject({ kind: 'absent', reason: 'NO_SOURCE' });
    }
    expect(catalystsModule('event-alerts').status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
    expect(catalystsModule('timeline').status.kind).toBe('served');
  });

  it('un identifiant inconnu lève', () => {
    expect(() => catalystsModule('impact')).toThrow(/Unknown catalysts module/);
  });
});
