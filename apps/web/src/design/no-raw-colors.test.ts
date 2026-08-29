// @vitest-environment node
/**
 * Garde-fou automatisé : aucune couleur brute (hex, rgb/rgba, hsl) hors de la
 * source typée `src/design/tokens.ts` et du `tokens.css` généré, et aucun
 * vocabulaire d'ordre boursier dans le code ou l'interface.
 *
 * Ce fichier est le vérificateur : il est le seul exclu de son propre balayage.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { basename, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const APP_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const SELF = fileURLToPath(import.meta.url);

const SCANNED_EXTENSIONS = ['.ts', '.tsx', '.css', '.html'];

function collectFiles(directory: string, accumulator: string[]): string[] {
  for (const entry of readdirSync(directory)) {
    const fullPath = join(directory, entry);
    const info = statSync(fullPath);
    if (info.isDirectory()) {
      collectFiles(fullPath, accumulator);
    } else if (SCANNED_EXTENSIONS.some((extension) => fullPath.endsWith(extension))) {
      accumulator.push(fullPath);
    }
  }
  return accumulator;
}

function scannedFiles(): string[] {
  const files = collectFiles(join(APP_ROOT, 'src'), []);
  files.push(join(APP_ROOT, 'index.html'));
  files.push(join(APP_ROOT, 'vite.config.ts'));
  return files.filter((file) => file !== SELF);
}

function isTokenSource(file: string): boolean {
  // `tokens.ts` (source) et `tokens.css` (généré, vérifié par tokens-css.test.ts).
  return basename(file).startsWith('tokens.') && file.includes(join('src', 'design'));
}

describe('interdiction des couleurs brutes hors tokens.*', () => {
  const hexPattern = /#[0-9a-fA-F]{3,8}\b/;
  const functionalPattern = /\b(?:rgb|rgba|hsl|hsla)\(/;

  it('aucun hex ni rgb()/hsl() hors src/design/tokens.*', () => {
    const offenders: string[] = [];
    for (const file of scannedFiles()) {
      if (isTokenSource(file)) {
        continue;
      }
      const content = readFileSync(file, 'utf8');
      const hexMatch = hexPattern.exec(content);
      const functionalMatch = functionalPattern.exec(content);
      if (hexMatch !== null || functionalMatch !== null) {
        const sample = hexMatch?.[0] ?? functionalMatch?.[0] ?? '';
        offenders.push(`${relative(APP_ROOT, file)} → ${sample}`);
      }
    }
    expect(offenders, `Couleurs brutes hors tokens : ${offenders.join(', ')}`).toEqual([]);
  });
});

describe("interdiction du vocabulaire d'ordre boursier", () => {
  // Termes assemblés par concaténation pour que ce vérificateur ne se signale
  // pas lui-même s'il venait à être balayé.
  const forbiddenTerms = ['bu' + 'y', 'se' + 'll', 'exe' + 'cute', 'ord' + 'er'];
  const termPattern = new RegExp(`\\b(?:${forbiddenTerms.join('|')})\\b`, 'i');

  it("aucun terme d'ordre (achat/vente/transmission) dans le code ou l'interface", () => {
    const offenders: string[] = [];
    for (const file of scannedFiles()) {
      const content = readFileSync(file, 'utf8');
      const match = termPattern.exec(content);
      if (match !== null) {
        offenders.push(`${relative(APP_ROOT, file)} → ${match[0]}`);
      }
    }
    expect(offenders, `Vocabulaire d'ordre détecté : ${offenders.join(', ')}`).toEqual([]);
  });
});
