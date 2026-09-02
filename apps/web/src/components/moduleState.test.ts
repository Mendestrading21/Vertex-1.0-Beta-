import { describe, expect, it } from 'vitest';

import { MODULE_STATE_LABELS, moduleShowsContent, moduleStateOf } from './moduleState.ts';

describe('moduleStateOf — l’état d’un module vient des faits servis', () => {
  it('relaie les états de requête hors succès, et refuse un succès sans réponse', () => {
    expect(moduleStateOf('loading', undefined)).toBe('loading');
    expect(moduleStateOf('offline', { state: 'ok' })).toBe('offline');
    expect(moduleStateOf('auth-required', { state: 'ok' })).toBe('auth-required');
    expect(moduleStateOf('ready', undefined)).toBe('error');
  });

  it('applique la priorité empty, stale, état fermé, puis DELAYED, puis requête', () => {
    expect(moduleStateOf('ready', { state: 'empty', population: 'DELAYED' })).toBe('empty');
    expect(moduleStateOf('ready', { state: 'stale', population: 'DELAYED' })).toBe('stale');
    expect(moduleStateOf('ready', { state: 'not_entitled' })).toBe('closed');
    expect(moduleStateOf('ready', { state: 'clock_inconsistent' })).toBe('closed');
    expect(moduleStateOf('ready', { state: 'ok', population: 'DELAYED' })).toBe('delayed');
    expect(moduleStateOf('refreshing', { state: 'ok' })).toBe('refreshing');
    expect(moduleStateOf('ready', { state: 'ok' })).toBe('ready');
    // Un objet sans champ `state` (valorisation, capacités) suit la requête.
    expect(moduleStateOf('ready', {})).toBe('ready');
  });

  it('ne montre un contenu que daté ou différé — jamais fermé, vide ou en erreur', () => {
    expect(moduleShowsContent('ready')).toBe(true);
    expect(moduleShowsContent('stale')).toBe(true);
    expect(moduleShowsContent('delayed')).toBe(true);
    expect(moduleShowsContent('partial')).toBe(true);
    for (const state of ['loading', 'empty', 'offline', 'error', 'auth-required', 'closed'] as const) {
      expect(moduleShowsContent(state), state).toBe(false);
    }
  });

  it('chaque état non nominal porte un libellé stable, jamais rassurant', () => {
    expect(MODULE_STATE_LABELS.closed).toBe('État serveur fermé');
    expect(MODULE_STATE_LABELS.empty).toBe('Aucun snapshot publié');
    expect(Object.values(MODULE_STATE_LABELS).some((label) => /ok|succès/i.test(label))).toBe(false);
  });
});
