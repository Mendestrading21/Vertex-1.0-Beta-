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

  it('DOUZE servis, sept absents ; chaque servi nomme son contrat', () => {
    // LOT P2 — UNE ABSENCE QUI A CESSÉ D'ÊTRE VRAIE. Le module `oscillators`
    // affirmait « le registre des calculs ne publie aucun oscillateur ».
    // C'était exact avant le LOT-S6 ; depuis, le worker publie
    // `indicators.oscillators = {rsi, macd}` avec leurs séries rendues, leur
    // méthode, leurs paramètres et leur lignée. Une absence qui a cessé d'être
    // vraie n'est plus une prudence : c'est un mensonge.
    const served = ANALYSIS_MODULES.filter((module) => module.status.kind === 'served');
    expect(served).toHaveLength(12);
    expect(absentAnalysisModules()).toHaveLength(7);
    for (const module of served) {
      expect(module.status.kind === 'served' && module.status.contract).toMatch(/GET \/api\/v1\//);
    }
  });

  it('la dominante est le graphique ; les faits SEC sont servis par leur propre route', () => {
    expect(analysisModule('chart').status.kind).toBe('served');
    // Les oscillateurs sont servis par le MÊME dossier que les indicateurs.
    expect(analysisModule('oscillators').status.kind).toBe('served');
    const financials = analysisModule('financials');
    expect(financials.status.kind === 'served' && financials.status.contract).toContain('/sources/sec/');
  });

  it('ni régime, ni confiance, ni valorisation : aucune source ne les publie', () => {
    // LOT P2 — `oscillators` a QUITTÉ cette liste : le worker les publie
    // depuis le LOT-S6. Les cinq autres restent réellement sans source.
    for (const id of ['regime', 'model-confidence', 'valuation', 'fundamental-quality', 'analyst-revisions']) {
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
