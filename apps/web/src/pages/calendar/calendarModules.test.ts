// @vitest-environment node
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { CALENDAR_MODULES, absentCalendarModules, calendarModule } from './calendarModules.ts';

describe('catalogue de la planche §11 (Calendrier)', () => {
  it('compte treize modules aux identifiants uniques, onze servis et deux absents', () => {
    expect(CALENDAR_MODULES).toHaveLength(13);
    expect(new Set(CALENDAR_MODULES.map((module) => module.id)).size).toBe(13);
    expect(CALENDAR_MODULES.filter((module) => module.status.kind === 'served')).toHaveLength(11);
    expect(absentCalendarModules()).toHaveLength(2);
  });

  it('chaque module servi nomme un contrat API existant', () => {
    for (const module of CALENDAR_MODULES) {
      if (module.status.kind === 'served') {
        expect(module.status.contract, module.id).toMatch(/^GET \/api\/v1\//);
      }
    }
  });

  it('chaque absence porte un motif du vocabulaire fermé et une note sans chiffre', () => {
    for (const module of absentCalendarModules()) {
      expect(Object.keys(ABSENCE_REASONS)).toContain(module.status.reason);
      expect(module.status.note, module.id).not.toMatch(/\d/);
      expect(module.status.note.length, module.id).toBeGreaterThan(20);
    }
  });

  it('rappels et changements depuis la visite attendent un contrat serveur ; le prochain événement n’a pas de compte à rebours', () => {
    expect(calendarModule('reminders').status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
    expect(calendarModule('changes-since-visit').status).toMatchObject({ kind: 'absent', reason: 'SERVER_CONTRACT_MISSING' });
    const next = calendarModule('next-event');
    expect(next.status.kind).toBe('served');
    expect(next.status.kind === 'served' ? next.status.contract : '').toContain('aucun compte à rebours');
  });

  it('un identifiant inconnu lève', () => {
    expect(() => calendarModule('countdown')).toThrow(/Unknown calendar module/);
  });
});
