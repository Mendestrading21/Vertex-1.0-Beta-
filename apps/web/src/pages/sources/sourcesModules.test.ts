// @vitest-environment node
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { SOURCES_MODULES, absentSourcesModules, sourcesModule } from './sourcesModules.ts';

describe('catalogue de la planche §12 (Sources & Rapports)', () => {
  it('compte dix-sept modules aux identifiants uniques, huit servis et neuf absents', () => {
    expect(SOURCES_MODULES).toHaveLength(17);
    expect(new Set(SOURCES_MODULES.map((module) => module.id)).size).toBe(17);
    expect(SOURCES_MODULES.filter((module) => module.status.kind === 'served')).toHaveLength(8);
    expect(absentSourcesModules()).toHaveLength(9);
  });

  it('chaque module servi nomme un contrat API existant', () => {
    for (const module of SOURCES_MODULES) {
      if (module.status.kind === 'served') {
        expect(module.status.contract, module.id).toMatch(/^GET \/api\/v1\//);
      }
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentSourcesModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note, module.id).not.toMatch(/\d/);
      expect(module.status.note.length, module.id).toBeGreaterThan(20);
    }
  });

  it('aucune santé globale : le contrat interdit un vert rassurant sans couverture complète', () => {
    expect(sourcesModule('global-health').status).toMatchObject({ kind: 'absent', reason: 'NO_SOURCE' });
    for (const id of ['incidents', 'lineage', 'audit-log', 'reports', 'backups']) {
      expect(sourcesModule(id).status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
    }
    expect(sourcesModule('registry').status.kind).toBe('served');
  });

  it('un identifiant inconnu lève', () => {
    expect(() => sourcesModule('sla')).toThrow(/Unknown sources module/);
  });
});
