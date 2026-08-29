// @vitest-environment node
/**
 * Vérifie que `tokens.css` (commité) est exactement la sortie du générateur
 * depuis la source typée unique, et que les valeurs canoniques du design
 * system y figurent.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { GENERATED_HEADER, renderTokensCss } from './generate-css.ts';
import { color, motionDuration, space, zIndex } from './tokens.ts';

const tokensCssPath = fileURLToPath(new URL('./tokens.css', import.meta.url));

describe('tokens.css généré', () => {
  const committed = readFileSync(tokensCssPath, 'utf8');

  it('est identique à la sortie du générateur (pnpm tokens:css)', () => {
    expect(committed).toBe(renderTokensCss());
  });

  it("commence par l'en-tête GÉNÉRÉ — ne pas éditer", () => {
    expect(committed.startsWith(GENERATED_HEADER)).toBe(true);
    expect(GENERATED_HEADER).toContain('GÉNÉRÉ — ne pas éditer');
  });

  it('déclare chaque couleur canonique sous son nom --vx-*', () => {
    for (const [key, value] of Object.entries(color)) {
      expect(committed).toContain(`--vx-${key}: ${value};`);
    }
  });

  it('déclare la grille 4 px complète (4..48)', () => {
    expect(Object.keys(space).map(Number)).toEqual([4, 8, 12, 16, 20, 24, 32, 40, 48]);
    for (const [key, value] of Object.entries(space)) {
      expect(committed).toContain(`--vx-space-${key}: ${value};`);
    }
  });

  it('déclare les rayons 6/10/14', () => {
    for (const key of [6, 10, 14]) {
      expect(committed).toContain(`--vx-radius-${key}: ${key}px;`);
    }
  });

  it('déclare les durées 90/140/180/220 ms et les plans z nommés', () => {
    expect(Object.keys(motionDuration).map(Number)).toEqual([90, 140, 180, 220]);
    for (const [key, value] of Object.entries(motionDuration)) {
      expect(committed).toContain(`--vx-motion-${key}: ${value};`);
    }
    for (const name of ['base', 'sticky', 'popover', 'sheet', 'dialog', 'toast']) {
      expect(Object.keys(zIndex)).toContain(name);
      expect(committed).toContain(`--vx-z-${name}:`);
    }
  });

  it('ramène toutes les durées à 0 ms sous prefers-reduced-motion', () => {
    const reducedBlock = committed.split('@media (prefers-reduced-motion: reduce)')[1];
    expect(reducedBlock).toBeDefined();
    for (const key of Object.keys(motionDuration)) {
      expect(reducedBlock).toContain(`--vx-motion-${key}: 0ms;`);
    }
  });
});
