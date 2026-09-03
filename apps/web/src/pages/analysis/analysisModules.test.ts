// @vitest-environment node
/**
 * Catalogue de la planche §4 : dix-neuf modules, chacun servi par un contrat
 * nommé ou absent avec un motif du vocabulaire fermé et une note SANS
 * chiffre (article 17).
 */
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { ANALYSIS_MODULES, absentAnalysisModules, analysisModule } from './analysisModules.ts';

describe('ANALYSIS_MODULES — la planche §4', () => {
  it('compte dix-neuf modules aux identifiants uniques', () => {
    expect(ANALYSIS_MODULES).toHaveLength(19);
    expect(new Set(ANALYSIS_MODULES.map((module) => module.id)).size).toBe(19);
  });

  it('onze servis, huit absents ; chaque servi nomme son contrat', () => {
    const served = ANALYSIS_MODULES.filter((module) => module.status.kind === 'served');
    expect(served).toHaveLength(11);
    expect(absentAnalysisModules()).toHaveLength(8);
    for (const module of served) {
      expect(module.status.kind === 'served' && module.status.contract).toMatch(/GET \/api\/v1\//);
    }
  });

  it('la dominante est le graphique ; les faits SEC sont servis par leur propre route', () => {
    expect(analysisModule('chart').status.kind).toBe('served');
    const financials = analysisModule('financials');
    expect(financials.status.kind === 'served' && financials.status.contract).toContain('/sources/sec/');
  });

  it('aucun oscillateur, régime, confiance ni valorisation : aucune source ne les publie', () => {
    for (const id of ['oscillators', 'regime', 'model-confidence', 'valuation', 'fundamental-quality', 'analyst-revisions']) {
      const module = analysisModule(id);
      expect(module.status.kind === 'absent' && module.status.reason).toBe('NO_SOURCE');
    }
    for (const id of ['levels', 'contradictions']) {
      const module = analysisModule(id);
      expect(module.status.kind === 'absent' && module.status.reason).toBe('SERVER_CONTRACT_MISSING');
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentAnalysisModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note).not.toMatch(/\d/);
    }
  });

  it('refuse un identifiant inconnu', () => {
    expect(() => analysisModule('inconnu')).toThrow(/Unknown analysis module/);
  });
});
