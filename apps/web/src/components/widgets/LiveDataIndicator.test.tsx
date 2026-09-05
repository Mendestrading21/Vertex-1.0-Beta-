import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LiveDataIndicator } from './LiveDataIndicator.tsx';
import type { LiveDataState } from './LiveDataIndicator.tsx';

const TOUS: readonly LiveDataState[] = [
  'live',
  'delayed',
  'stale',
  'closed',
  'manual',
  'simulated',
  'unavailable',
  'degraded',
];

describe('LiveDataIndicator — le statut canonique des données', () => {
  it('nomme chacun des huit états, sans jamais coder par la couleur seule', () => {
    for (const etat of TOUS) {
      const { unmount } = render(<LiveDataIndicator state={etat} ageSeconds={12} />);
      const pastille = screen.getByRole('status');
      // Le mot est TOUJOURS là : quelqu'un qui ne distingue pas les teintes
      // obtient exactement la même information.
      expect(pastille.textContent?.trim().length ?? 0).toBeGreaterThan(0);
      expect(pastille.getAttribute('data-state')).toBe(etat);
      unmount();
    }
  });

  it('donne à chaque état une DÉFINITION dans son nom accessible', () => {
    for (const etat of TOUS) {
      const { unmount } = render(<LiveDataIndicator state={etat} ageSeconds={null} />);
      const nom = screen.getByRole('status').getAttribute('aria-label') ?? '';
      // Une définition réservée au survol serait inatteignable au clavier.
      expect(nom).toContain('—');
      expect(nom.length).toBeGreaterThan(25);
      unmount();
    }
  });

  it('distingue « décrit l’instant » de « ne le décrit plus » PAR LA FORME', () => {
    // Seconde vecteur, indépendant de la couleur : pastille pleine ou creuse.
    const pleins: readonly LiveDataState[] = ['live', 'delayed', 'manual', 'simulated'];
    const creux: readonly LiveDataState[] = ['stale', 'closed', 'unavailable', 'degraded'];
    for (const etat of pleins) {
      const { unmount } = render(<LiveDataIndicator state={etat} ageSeconds={1} />);
      expect(document.querySelector('.vx-live-dot')?.getAttribute('data-filled')).toBe('true');
      unmount();
    }
    for (const etat of creux) {
      const { unmount } = render(<LiveDataIndicator state={etat} ageSeconds={1} />);
      expect(document.querySelector('.vx-live-dot')?.getAttribute('data-filled')).toBe('false');
      unmount();
    }
  });

  it('DIT que l’âge n’est pas publié, au lieu de le masquer', () => {
    render(<LiveDataIndicator state="delayed" ageSeconds={null} />);
    expect(screen.getByText('âge inconnu')).toBeTruthy();
  });

  it('n’affiche AUCUNE latence — le serveur n’en publie pas', () => {
    render(<LiveDataIndicator state="live" ageSeconds={3} source="IBKR" asOf="2026-09-04T20:18:52Z" />);
    const texte = screen.getByRole('status').textContent ?? '';
    // La maquette montrait « 124 ms ». Le contrat ne publie pas de latence :
    // l'afficher aurait voulu dire la fabriquer. Ce test gèle cette absence.
    expect(texte).not.toMatch(/\bms\b/);
    expect(texte).not.toMatch(/latence/i);
  });

  it('n’affiche le droit manquant QUE là où il est la cause', () => {
    const { unmount } = render(
      <LiveDataIndicator state="unavailable" ageSeconds={null} missingEntitlement="US-OPRA-TOP" />,
    );
    expect(screen.getByText(/droit requis : US-OPRA-TOP/)).toBeTruthy();
    unmount();

    // Sur un état retardé, le droit ne serait qu'un mot de plus sans rapport
    // avec ce que l'utilisateur lit.
    render(<LiveDataIndicator state="delayed" ageSeconds={900} missingEntitlement="US-OPRA-TOP" />);
    expect(screen.queryByText(/droit requis/)).toBeNull();
  });

  it('rend l’instant servi en <time>, jamais une date recalculée', () => {
    render(<LiveDataIndicator state="closed" ageSeconds={7200} asOf="2026-09-04T17:30:00Z" />);
    const instant = document.querySelector('time');
    expect(instant?.getAttribute('datetime')).toBe('2026-09-04T17:30:00Z');
    // Verbatim : aucune reformulation locale d'une date serveur.
    expect(instant?.textContent).toBe('2026-09-04T17:30:00Z');
  });

  it('la variante compacte tait le contexte, pas l’état', () => {
    render(<LiveDataIndicator state="stale" ageSeconds={5000} source="IBKR" variant="compact" />);
    expect(screen.getByText('PÉRIMÉ')).toBeTruthy();
    expect(screen.queryByText('IBKR')).toBeNull();
  });

  it('« SYNTHÉTIQUE » n’emprunte aucun mot d’activité de marché', () => {
    render(<LiveDataIndicator state="simulated" ageSeconds={4} />);
    const nom = screen.getByRole('status').getAttribute('aria-label') ?? '';
    expect(nom).toMatch(/jamais une donnée de marché/);
    expect(nom).not.toMatch(/direct|temps réel/i);
  });
});
