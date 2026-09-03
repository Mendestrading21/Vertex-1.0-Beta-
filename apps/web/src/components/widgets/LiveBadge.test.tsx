import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LiveBadge, liveBadgeDecision } from './LiveBadge.tsx';
import type { LiveBadgeInput } from './LiveBadge.tsx';

/**
 * Le badge dit l'état du LIEN DE SIGNALEMENT et la fraîcheur SERVIE — jamais
 * une promesse sur la donnée. Le mot « direct » n'y figure pas : le flux SSE
 * est signal-only (`{resource, version}`), il ne cote rien.
 */
const BASE: LiveBadgeInput = {
  session: 'authenticated',
  link: 'open',
  mode: 'signal',
  tracked: true,
  meta: {
    ageSeconds: 4,
    asOf: '2026-09-03T08:40:00Z',
    state: 'ok',
    population: 'REAL',
    snapshotVersion: 42290,
    fetchStatus: 'idle',
    error: null,
    present: true,
  },
};

describe('liveBadgeDecision — table de décision pure', () => {
  it('session absente : SESSION REQUISE, et rien d’autre n’est promis', () => {
    const decision = liveBadgeDecision({ ...BASE, session: 'unauthenticated' });
    expect(decision.label).toBe('SESSION REQUISE');
    expect(decision.live).toBe('session');
    expect(decision.tone).toBe('negative');
  });

  it('erreur réseau : HORS LIGNE avec le DERNIER instantané servi', () => {
    const decision = liveBadgeDecision({
      ...BASE,
      meta: { ...BASE.meta, error: 'NETWORK' },
    });
    expect(decision.label).toContain('HORS LIGNE');
    expect(decision.label).toContain('2026-09-03T08:40:00Z');
    expect(decision.live).toBe('offline');
  });

  it('état servi « stale » : PÉRIMÉ — jamais un mot de direct', () => {
    const decision = liveBadgeDecision({ ...BASE, meta: { ...BASE.meta, state: 'stale' } });
    expect(decision.label).toContain('PÉRIMÉ');
    expect(decision.tone).toBe('warning');
  });

  it('population DELAYED : DIFFÉRÉ', () => {
    const decision = liveBadgeDecision({
      ...BASE,
      meta: { ...BASE.meta, population: 'DELAYED' },
    });
    expect(decision.label).toContain('DIFFÉRÉ');
    expect(decision.tone).toBe('warning');
  });

  it('ressource non suivie : SANS SIGNAL, jamais « actif »', () => {
    const decision = liveBadgeDecision({ ...BASE, tracked: false });
    expect(decision.label).toContain('SANS SIGNAL');
    expect(decision.label).not.toContain('ACTIF');
    expect(decision.tone).toBe('muted');
  });

  it('lien ouvert : SIGNAL ACTIF • publié il y a N — la donnée est « publiée », pas « cotée »', () => {
    const decision = liveBadgeDecision(BASE);
    expect(decision.label).toBe('SIGNAL ACTIF • publié il y a 4 s');
    expect(decision.live).toBe('open');
    // Aucune teinte pour l'état du lien (revue C0, point B2).
    expect(decision.tone).toBe('neutral');
  });

  it('reconnexion et silence sont DITS, avec le mode de repli', () => {
    expect(liveBadgeDecision({ ...BASE, link: 'retrying' }).label).toContain('RECONNEXION');
    expect(
      liveBadgeDecision({ ...BASE, link: 'silent', mode: 'sondage' }).label,
    ).toContain('SONDAGE');
    expect(liveBadgeDecision({ ...BASE, link: 'silent', mode: 'signal' }).label).toContain(
      'SILENCE',
    );
  });

  it('actualisation en cours : suffixe explicite, sans changer l’état du lien', () => {
    const decision = liveBadgeDecision({
      ...BASE,
      meta: { ...BASE.meta, fetchStatus: 'fetching' },
    });
    expect(decision.label).toContain('actualisation');
    expect(decision.live).toBe('open');
  });

  it('âge non publié : DIT, jamais extrapolé depuis l’horloge du navigateur', () => {
    const decision = liveBadgeDecision({ ...BASE, meta: { ...BASE.meta, ageSeconds: null } });
    expect(decision.label).toContain('âge non publié');
  });

  it('aucune population SYNTHETIC ou DEMO ne peut porter un mot de direct', () => {
    for (const population of ['SYNTHETIC', 'DEMO']) {
      const decision = liveBadgeDecision({ ...BASE, meta: { ...BASE.meta, population } });
      expect(decision.label).not.toContain('ACTIF');
      expect(decision.label).toContain('SIGNAL');
      expect(decision.populationChip).toBe(population);
    }
  });

  it('aucun libellé de la table ne contient le mot « direct »', () => {
    const variantes: LiveBadgeInput[] = [
      BASE,
      { ...BASE, session: 'unauthenticated' },
      { ...BASE, tracked: false },
      { ...BASE, link: 'retrying' },
      { ...BASE, link: 'silent', mode: 'sondage' },
      { ...BASE, meta: { ...BASE.meta, state: 'stale' } },
      { ...BASE, meta: { ...BASE.meta, population: 'DELAYED' } },
      { ...BASE, meta: { ...BASE.meta, error: 'NETWORK' } },
    ];
    for (const variante of variantes) {
      expect(liveBadgeDecision(variante).label.toLowerCase()).not.toContain('direct');
    }
  });
});

describe('LiveBadge — rendu', () => {
  it('porte data-live et le texte de la décision', () => {
    render(<LiveBadge {...BASE} />);
    const badge = screen.getByTestId('live-badge');
    expect(badge.getAttribute('data-live')).toBe('open');
    expect(badge.textContent).toContain('SIGNAL ACTIF');
  });

  it('la nature de la population est un CHIP à texte, jamais une couleur seule', () => {
    render(<LiveBadge {...BASE} meta={{ ...BASE.meta, population: 'SYNTHETIC' }} />);
    expect(screen.getByTestId('status-chip').textContent).toContain('DONNÉES SYNTHÉTIQUES');
  });

  it('aucune pulsation : pas de classe d’animation, pas de rôle alerte', () => {
    const { container } = render(<LiveBadge {...BASE} />);
    expect(container.innerHTML).not.toContain('pulse');
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });
});
