// @vitest-environment node
/**
 * Vérifie que `tokens.css` (commité) est exactement la sortie du générateur
 * depuis la source typée unique, et que les valeurs canoniques du design
 * system y figurent — y compris les tokens du canon v2 (ADR-017) : la
 * surbrillance 600 ms, les dégradés de série vers la transparence et la
 * teinte sémantique secondaire par page.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { GENERATED_HEADER, renderTokensCss } from './generate-css.ts';
import { color, motionDuration, pageAccent, radius, shadow, space, zIndex } from './tokens.ts';

const tokensCssPath = fileURLToPath(new URL('./tokens.css', import.meta.url));

/**
 * Familles de série qui possèdent un couple de dégradé (ADR-017). L'ambre
 * (`signal`) n'en a pas : il n'est jamais la teinte d'une série.
 */
const GRADIENT_FAMILIES = ['silver', 'positive', 'negative', 'warning', 'option', 'macro'] as const;

const RGBA_PATTERN = /^rgba\((\d+), (\d+), (\d+), (0|0?\.\d+|1)\)$/;

/** Décompose une écriture fonctionnelle rgba ; échoue visiblement sur toute autre écriture. */
function parseAlphaColor(value: string): { rgb: [number, number, number]; alpha: number } {
  const match = RGBA_PATTERN.exec(value);
  if (match === null) {
    throw new Error(`Écriture fonctionnelle rgba attendue, reçu « ${value} »`);
  }
  return {
    rgb: [Number(match[1]), Number(match[2]), Number(match[3])],
    alpha: Number(match[4]),
  };
}

/** `#rrggbb` → triplet décimal, pour comparer une famille à son dégradé. */
function hexToRgb(value: string): [number, number, number] {
  const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(value);
  if (match === null) {
    throw new Error(`Hex #rrggbb attendu, reçu « ${value} »`);
  }
  const [, red, green, blue] = match;
  if (red === undefined || green === undefined || blue === undefined) {
    throw new Error(`Hex #rrggbb incomplet : ${value}`);
  }
  return [Number.parseInt(red, 16), Number.parseInt(green, 16), Number.parseInt(blue, 16)];
}

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

  it('déclare les rayons 6/10/14/18/22', () => {
    expect(Object.keys(radius)).toEqual(['6', '10', '14', '18', '22', 'pill']);
    for (const [key, value] of Object.entries(radius)) {
      expect(committed).toContain(`--vx-radius-${key}: ${value};`);
    }
  });

  it('déclare les trois ombres sobres du système Titanium Ledger', () => {
    expect(Object.keys(shadow)).toEqual(['panel', 'floating', 'inset']);
    for (const [key, value] of Object.entries(shadow)) {
      expect(committed).toContain(`--vx-shadow-${key}: ${value};`);
    }
  });

  it('déclare les durées 90/140/180/220 ms, la surbrillance 600 ms (ADR-017) et les plans z nommés', () => {
    expect(Object.keys(motionDuration).map(Number)).toEqual([90, 140, 180, 220, 600]);
    for (const [key, value] of Object.entries(motionDuration)) {
      expect(committed).toContain(`--vx-motion-${key}: ${value};`);
    }
    // 600 ms est la surbrillance UNIQUE d'une valeur mise à jour, jamais une
    // transition d'interface : aucune durée intermédiaire n'est ajoutée.
    expect(motionDuration[600]).toBe('600ms');
    for (const name of ['base', 'sticky', 'popover', 'sheet', 'dialog', 'toast']) {
      expect(Object.keys(zIndex)).toContain(name);
      expect(committed).toContain(`--vx-z-${name}:`);
    }
  });

  it('ramène toutes les durées à 0 ms sous prefers-reduced-motion, 600 ms compris', () => {
    const reducedBlock = committed.split('@media (prefers-reduced-motion: reduce)')[1];
    expect(reducedBlock).toBeDefined();
    for (const key of Object.keys(motionDuration)) {
      expect(reducedBlock).toContain(`--vx-motion-${key}: 0ms;`);
    }
    expect(reducedBlock).toContain('--vx-motion-600: 0ms;');
  });

  it('déclare, pour chaque famille de série, un dégradé de la teinte vers SA transparence (ADR-017)', () => {
    for (const family of GRADIENT_FAMILIES) {
      const start = parseAlphaColor(color[`${family}-gradient-start`]);
      const end = parseAlphaColor(color[`${family}-gradient-end`]);
      // Le fondu reste dans la famille : même triplet que la teinte pleine,
      // jamais un fondu vers le noir ni vers une autre teinte.
      expect(start.rgb, `${family}-gradient-start`).toEqual(hexToRgb(color[family]));
      expect(end.rgb, `${family}-gradient-end`).toEqual(hexToRgb(color[family]));
      // Fin à la transparence totale ; départ discret — une aire sous une
      // série n'est pas un fond de carte.
      expect(end.alpha, `${family}-gradient-end`).toBe(0);
      expect(start.alpha, `${family}-gradient-start`).toBeGreaterThan(0);
      expect(start.alpha, `${family}-gradient-start`).toBeLessThan(0.5);
      expect(committed).toContain(`--vx-${family}-gradient-start: ${color[`${family}-gradient-start`]};`);
      expect(committed).toContain(`--vx-${family}-gradient-end: ${color[`${family}-gradient-end`]};`);
    }
    // L'ambre est la lumière de la dominante, jamais la teinte d'une série.
    expect(Object.keys(color)).not.toContain('signal-gradient-start');
  });

  it('expose la teinte secondaire de page par famille EXISTANTE — [data-page-accent], ADR-017', () => {
    expect(Object.keys(pageAccent)).toEqual(['macro', 'option', 'warning']);
    for (const [page, family] of Object.entries(pageAccent)) {
      // La clé NOMME la famille : aucun alias, « une couleur = une signification ».
      expect(page).toBe(family);
      expect(color).toHaveProperty(family);
      expect(color).toHaveProperty(`${family}-soft`);
      expect(color).toHaveProperty(`${family}-gradient-start`);
      expect(color).toHaveProperty(`${family}-gradient-end`);
      expect(committed).toContain(
        [
          `[data-page-accent="${page}"] {`,
          `  --vx-page-accent: var(--vx-${family});`,
          `  --vx-page-accent-soft: var(--vx-${family}-soft);`,
          `  --vx-page-accent-gradient-start: var(--vx-${family}-gradient-start);`,
          `  --vx-page-accent-gradient-end: var(--vx-${family}-gradient-end);`,
          '}',
        ].join('\n'),
      );
    }
    // L'ambre reste la seule lumière de la dominante : jamais une teinte de page.
    expect(Object.values(pageAccent)).not.toContain('signal');
    expect(committed).not.toContain('--vx-page-accent: var(--vx-signal)');
    // Vert/rouge restent au signe financier servi : une teinte de page ne
    // bascule pas selon le signe, elle ne peut donc pas en porter un (revue C0).
    for (const reserved of ['positive', 'negative'] as const) {
      expect(Object.keys(pageAccent)).not.toContain(reserved);
      expect(committed).not.toContain(`--vx-page-accent: var(--vx-${reserved})`);
    }
    // Aucune valeur par défaut silencieuse : sans déclaration de page, pas de teinte.
    expect(committed).not.toMatch(/:root\s*\{[^}]*--vx-page-accent/);
  });
});
