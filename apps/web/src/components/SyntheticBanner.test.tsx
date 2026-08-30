/**
 * Reproducteur du 5e audit adversarial — le bandeau de population est
 * fail-OPEN.
 *
 * `population` est le SEUL champ qui sépare une donnée réelle d'une donnée
 * générée. Le composant rendait `null` dès que l'étiquette n'était pas
 * exactement `SYNTHETIC` : une étiquette FORGÉE (`REAL`, `LIVE`,
 * `IBKR_REALTIME`) ou ABSENTE supprimait donc l'avertissement au lieu de
 * fermer. C'est l'inverse exact du fail-closed exigé par
 * `.claude/rules/financial-safety.md`.
 *
 * Ce fichier vérifie trois invariants :
 *
 * 1. le bandeau ne disparaît JAMAIS — quelle que soit l'étiquette reçue,
 *    l'utilisateur voit ce qu'il regarde ;
 * 2. chaque nature déclarée a un rendu DISTINCT (réel, retardé, théorique,
 *    simulé, synthétique, démonstration, déclaré par l'utilisateur ne
 *    partagent ni le même libellé ni le même statut visuel) ;
 * 3. une étiquette inconnue ou absente est signalée en RISQUE, pas en
 *    silence.
 *
 * Tout est SYNTHETIC : le composant est pur, il ne lit ni réseau ni horloge.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import {
  POPULATION_NATURES,
  SyntheticBanner,
  resolvePopulationNature,
} from './SyntheticBanner.tsx';

afterEach(() => {
  cleanup();
});

/** Le bandeau, quel qu'il soit. Absent ⇒ l'assertion échoue explicitement. */
function banner(): HTMLElement {
  const found = document.querySelector('[data-vx-population-banner]');
  expect(found, 'le bandeau de population ne doit jamais disparaître').not.toBeNull();
  return found as HTMLElement;
}

// ---------------------------------------------------------------------------
// 1. Fail-closed : une étiquette forgée ou absente AVERTIT
// ---------------------------------------------------------------------------

/**
 * Étiquettes hors vocabulaire. `REAL`/`DELAYED` appartiennent au vocabulaire
 * du relais, mais tout le reste est ce qu'un contenu persisté forgé peut
 * porter — et ce que l'ancien composant traduisait par « aucun bandeau ».
 */
const FORGED_LABELS = [
  'LIVE',
  'REEL',
  'IBKR_REALTIME_ENTITLED',
  'PRODUCTION',
  'synthetic',
  'SYNTHETIC ',
  'SYNTHETIC/REAL',
];

/** Étiquettes qui ne déclarent RIEN : champ absent ou vide. */
const UNDECLARED_LABELS: readonly (string | null)[] = [null, ''];

describe('étiquette hors vocabulaire — le bandeau ferme, il ne disparaît pas', () => {
  it.each(FORGED_LABELS)('« %s » reste signalé comme non reconnu', (forged) => {
    render(<SyntheticBanner population={forged} />);
    const element = banner();
    expect(element.dataset.vxNature).toBe('UNRECOGNISED');
    expect(element.dataset.vxTone).toBe('risk');
    expect(element.textContent).toContain('NATURE NON RECONNUE');
  });

  it.each(UNDECLARED_LABELS)(
    'une étiquette non déclarée (%s) avertit au lieu de se taire',
    (absent) => {
      render(<SyntheticBanner population={absent} />);
      const element = banner();
      expect(element.dataset.vxNature).toBe('UNDECLARED');
      expect(element.dataset.vxTone).toBe('risk');
      expect(element.textContent).toContain('NATURE NON DÉCLARÉE');
    },
  );

  it("une étiquette non reconnue est citée, bornée, jamais interprétée", () => {
    const hostile = `ACHETEZ${'Z'.repeat(5000)}`;
    render(<SyntheticBanner population={hostile} />);
    const element = banner();
    // Citée pour le diagnostic, mais bornée : le DOM ne relaie pas 5000 car.
    expect(element.textContent!.length).toBeLessThan(400);
    expect(element.textContent).not.toContain('ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ');
  });
});

// ---------------------------------------------------------------------------
// 2. Chaque nature déclarée a un rendu DISTINCT
// ---------------------------------------------------------------------------

describe('natures déclarées — jamais le même statut visuel ni sémantique', () => {
  it('couvre exactement le vocabulaire fermé publié par le relais', () => {
    expect(Object.keys(POPULATION_NATURES).sort()).toEqual(
      [
        'DELAYED',
        'DEMO',
        'EMPTY',
        'REAL',
        'SIMULATED',
        'SYNTHETIC',
        'SYNTHETIC_MARKS_REAL_LEDGER',
        'THEORETICAL',
        'USER_DECLARED',
      ].sort(),
    );
  });

  it('réel, retardé, théorique, simulé et démonstration ont cinq libellés différents', () => {
    const labels = (['REAL', 'DELAYED', 'THEORETICAL', 'SIMULATED', 'DEMO'] as const).map(
      (nature) => POPULATION_NATURES[nature].label,
    );
    expect(new Set(labels).size).toBe(labels.length);
  });

  it('aucune nature ne partage son libellé avec une autre', () => {
    const labels = Object.values(POPULATION_NATURES).map((nature) => nature.label);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it.each(Object.keys(POPULATION_NATURES))('« %s » est rendu et nommé', (label) => {
    render(<SyntheticBanner population={label} />);
    const element = banner();
    expect(element.dataset.vxNature).toBe(label);
    expect(element.textContent).toContain(
      POPULATION_NATURES[label as keyof typeof POPULATION_NATURES].label,
    );
  });

  it('SYNTHETIC garde le libellé exact attendu par les parcours E2E', () => {
    render(<SyntheticBanner population="SYNTHETIC" />);
    expect(screen.getByText('DONNÉES SYNTHÉTIQUES')).toBeDefined();
  });

  it('une donnée observée n’est pas peinte comme une dégradation', () => {
    render(<SyntheticBanner population="REAL" />);
    expect(banner().dataset.vxTone).toBe('neutral');
  });

  it('retardé, théorique, simulé, synthétique et démonstration sont en prudence', () => {
    for (const label of ['DELAYED', 'THEORETICAL', 'SIMULATED', 'SYNTHETIC', 'DEMO']) {
      cleanup();
      render(<SyntheticBanner population={label} />);
      expect(banner().dataset.vxTone, label).toBe('caution');
    }
  });

  it('le bandeau dit que la nature est DÉCLARÉE, pas vérifiée', () => {
    render(<SyntheticBanner population="REAL" />);
    expect(banner().textContent).toMatch(/déclarée/i);
  });
});

// ---------------------------------------------------------------------------
// 3. Identité visuelle : aucune couleur hors tokens, aucun glow
// ---------------------------------------------------------------------------

describe('identité visuelle', () => {
  it.each([...FORGED_LABELS, '', ...Object.keys(POPULATION_NATURES)])(
    'la teinte de « %s » vient d’un token, jamais d’un hex',
    (label) => {
      render(<SyntheticBanner population={label} />);
      const style = banner().getAttribute('style') ?? '';
      expect(style).not.toMatch(/#[0-9a-f]{3,8}/i);
      expect(style).not.toMatch(/\b(?:rgb|rgba|hsl|hsla)\(/);
      expect(style).not.toMatch(/box-shadow|filter/i);
      expect(style).toMatch(/var\(--vx-/);
    },
  );

  it('n’utilise que prudence (ambre), risque (rouge) et neutre', () => {
    const tones = new Set<string>();
    for (const label of [...FORGED_LABELS, '', ...Object.keys(POPULATION_NATURES)]) {
      cleanup();
      render(<SyntheticBanner population={label} />);
      tones.add(banner().dataset.vxTone!);
    }
    expect([...tones].sort()).toEqual(['caution', 'neutral', 'risk']);
  });
});

describe('6e audit — coercition de type', () => {
  // `hasOwnProperty` et l'indexation coercent leur clé en chaîne. Un objet
  // portant `toString: () => 'REAL'` affichait « DONNÉES RÉELLES » en ton
  // neutre ; un nombre faisait planter le rendu sur `.slice`.
  const hostiles: ReadonlyArray<readonly [string, unknown]> = [
    ['objet avec toString', { toString: () => 'REAL' }],
    ['tableau', ['SYNTHETIC']],
    ['nombre', 0],
    ['nombre non nul', 42],
    ['booléen', true],
    ['fonction', () => 'REAL'],
    ['symbole-like', { valueOf: () => 'DELAYED' }],
  ];

  it.each(hostiles)('%s ne peut pas revendiquer une nature', (_label, value) => {
    const resolved = resolvePopulationNature(value as never);
    expect(resolved.key).toBe('UNRECOGNISED');
    expect(resolved.nature.tone).toBe('risk');
  });

  it('undefined est traité comme non déclaré, pas comme une erreur', () => {
    const resolved = resolvePopulationNature(undefined as never);
    expect(resolved.key).toBe('UNDECLARED');
  });

  it.each(hostiles)('%s ne fait pas planter le rendu', (_label, value) => {
    expect(() =>
      render(<SyntheticBanner population={value as never} />),
    ).not.toThrow();
  });

  it('une chaîne déclarée reste correctement reconnue', () => {
    // Anti-vacuité : la fermeture par type n'a pas cassé le cas nominal.
    expect(resolvePopulationNature('SYNTHETIC').key).toBe('SYNTHETIC');
    expect(resolvePopulationNature('REAL').key).toBe('REAL');
  });
});
