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

  // `schema.d.ts` est GÉNÉRÉ verbatim depuis apps/api/openapi.json : sa seule
  // occurrence du vocabulaire est la phrase d'interdiction du backend
  // (« nothing here is, or ever becomes, an ... ») recopiée en JSDoc. Le
  // contrat lui-même est la source de vérité, gardée côté API ; on vérifie
  // ci-dessous que l'exclusion reste bien limitée à ce cas de négation.
  function isGeneratedSchema(file: string): boolean {
    return file.endsWith(join('src', 'api', 'schema.d.ts'));
  }

  it("aucun terme d'ordre (achat/vente/transmission) dans le code ou l'interface", () => {
    const offenders: string[] = [];
    for (const file of scannedFiles()) {
      if (isGeneratedSchema(file)) {
        continue;
      }
      const content = readFileSync(file, 'utf8');
      const match = termPattern.exec(content);
      if (match !== null) {
        offenders.push(`${relative(APP_ROOT, file)} → ${match[0]}`);
      }
    }
    expect(offenders, `Vocabulaire d'ordre détecté : ${offenders.join(', ')}`).toEqual([]);
  });

  it('schema.d.ts généré : le vocabulaire n’apparaît que dans une négation du contrat', () => {
    const generated = scannedFiles().find((file) => isGeneratedSchema(file));
    expect(generated).toBeDefined();
    const lines = readFileSync(generated!, 'utf8').split('\n');
    const matchingLines = lines.filter((line) => termPattern.test(line));
    for (const line of matchingLines) {
      expect(
        /nothing here is, or ever becomes/i.test(line),
        `Occurrence non couverte par la négation du contrat : ${line.trim()}`,
      ).toBe(true);
    }
  });

  it('les nouveaux fichiers V3 (options, analyse, simulateur) sont bien balayés', () => {
    const files = scannedFiles().map((file) => relative(APP_ROOT, file));
    for (const expected of [
      join('src', 'pages', 'options', 'OptionsPage.tsx'),
      join('src', 'pages', 'options', 'OptionChainTable.tsx'),
      join('src', 'pages', 'options', 'OptionInspector.tsx'),
      join('src', 'pages', 'analysis', 'AnalysisPage.tsx'),
      join('src', 'pages', 'analysis', 'CandleChart.tsx'),
      join('src', 'pages', 'simulator', 'SimulatorPage.tsx'),
      join('src', 'pages', 'simulator', 'PayoffChart.tsx'),
      join('src', 'charts', 'lightweightChartsLoader.ts'),
    ]) {
      expect(files, `${expected} doit être couvert par les gardes`).toContain(expected);
    }
  });
});
