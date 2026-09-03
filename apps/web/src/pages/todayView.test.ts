import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../components/AbsentModule.tsx';
import { makeCapabilityEntries, makeCalendarResponse, makeOpportunities, makeValuationContent } from '../test/fixtures.ts';
import { opportunitiesContentOf } from './opportunities/opportunitiesView.ts';
import { valuationContentOf } from './portfolio/portfolioView.ts';
import {
  TODAY_MODULES,
  absentTodayModules,
  capabilityStatusCensus,
  leadingAgenda,
  opportunitiesSummaryOf,
  portfolioSummaryOf,
  todayModule,
} from './todayView.ts';

describe('catalogue de la planche §1 — Aujourd’hui', () => {
  it('porte les onze modules de la planche plus les instruments suivis, identifiants uniques', () => {
    expect(TODAY_MODULES).toHaveLength(12);
    expect(new Set(TODAY_MODULES.map((module) => module.id)).size).toBe(12);
  });

  it('trois modules sont absents, avec un motif du vocabulaire fermé et une note sans chiffre', () => {
    const absents = absentTodayModules();
    expect(absents.map((module) => module.id)).toEqual(['regime', 'volatility', 'active-risks']);
    for (const module of absents) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      // Article 17 : le corps d'un module absent ne porte aucun chiffre.
      expect(module.status.note, module.id).not.toMatch(/\d/);
    }
  });

  it('les neuf autres nomment leur contrat serveur', () => {
    const served = TODAY_MODULES.filter((module) => module.status.kind === 'served');
    expect(served).toHaveLength(9);
    for (const module of served) {
      expect(module.status.kind === 'served' ? module.status.contract : '').toMatch(/^GET \/api\/v1\//);
    }
  });

  it('un identifiant inconnu est refusé, jamais un module inventé', () => {
    expect(() => todayModule('regime')).not.toThrow();
    expect(() => todayModule('made-up')).toThrow(/Unknown today module/);
  });
});

describe('dérivations pures — ordre publié, comptes publiés', () => {
  it('leadingAgenda prend les premiers événements DANS L’ORDRE PUBLIÉ, sans retri', () => {
    const response = makeCalendarResponse();
    const premiers = leadingAgenda(response.agenda, 1);
    expect(premiers).toHaveLength(1);
    // Le fixture publie l'événement révisé (SYN-ENER-01) en premier : il reste premier.
    expect(premiers[0]?.ticker).toBe('SYN-ENER-01');
    expect(leadingAgenda(response.agenda, 5)).toHaveLength(2);
    expect(leadingAgenda([], 3)).toHaveLength(0);
  });

  it('capabilityStatusCensus compte les statuts testés, sans en inventer', () => {
    const census = capabilityStatusCensus(makeCapabilityEntries());
    let total = 0;
    for (const count of census.values()) {
      total += count;
    }
    expect(total).toBe(14);
    expect(census.get('AVAILABLE')).toBe(3);
    expect(capabilityStatusCensus([]).size).toBe(0);
  });

  it('opportunitiesSummaryOf relaie les comptes de couverture et la méthode d’ordre', () => {
    const view = opportunitiesContentOf(makeOpportunities().content);
    expect(view).not.toBeNull();
    const summary = opportunitiesSummaryOf(view!);
    expect(summary.universeSize).toBe(24);
    expect(summary.qualifiedCount).toBe(0);
    expect(summary.excludedCount).toBe(1);
    expect(summary.qualified).toHaveLength(0);
    expect(summary.orderingMethod).toBe('lexicographic');
    expect(summary.statusCounts.get('INSUFFICIENT_DATA')).toBe(1);
  });

  it('portfolioSummaryOf relaie la population des marques et les comptes de lots', () => {
    const content = valuationContentOf({
      state: 'ok',
      snapshot_version: 3,
      as_of: '2026-08-25T12:00:00+00:00',
      age_seconds: 60,
      reason: null,
      content: makeValuationContent(),
    });
    expect(content).not.toBeNull();
    const summary = portfolioSummaryOf(content!);
    expect(summary.markPopulation).toBe('SYNTHETIC');
    expect(summary.lotsValued).toBe(1);
    expect(summary.lotsExcluded).toBe(1);
    expect(summary.blocks).toHaveLength(1);
    expect(summary.blocks[0]?.totalValue).toBe('555');
  });
});
