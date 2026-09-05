// @vitest-environment node
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { PORTFOLIO_MODULES, absentPortfolioModules, portfolioModule } from './portfolioModules.ts';

describe('catalogue de la planche §7 (Portefeuille)', () => {
  it('compte dix-huit modules aux identifiants uniques, dix servis et huit absents', () => {
    expect(PORTFOLIO_MODULES).toHaveLength(18);
    expect(new Set(PORTFOLIO_MODULES.map((module) => module.id)).size).toBe(18);
    expect(PORTFOLIO_MODULES.filter((module) => module.status.kind === 'served')).toHaveLength(10);
    expect(absentPortfolioModules()).toHaveLength(8);
  });

  it('chaque module servi nomme un contrat API existant', () => {
    for (const module of PORTFOLIO_MODULES) {
      if (module.status.kind === 'served') {
        expect(module.status.contract, module.id).toMatch(/^(GET|POST) \/api\/v1\//);
      }
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentPortfolioModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note, module.id).not.toMatch(/\d/);
      expect(module.status.note.length, module.id).toBeGreaterThan(20);
    }
  });

  it('les dividendes sont SERVIS depuis le journal, jamais sommés ; espèces et allocation restent absents', () => {
    expect(portfolioModule('dividends').status.kind).toBe('served');
    expect(portfolioModule('cash').status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
    expect(portfolioModule('allocation').status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
    expect(portfolioModule('concentration-alerts').status).toMatchObject({ kind: 'absent', reason: 'DECISION_PENDING' });
  });

  it('un identifiant inconnu lève', () => {
    expect(() => portfolioModule('nav')).toThrow(/Unknown portfolio module/);
  });
});
