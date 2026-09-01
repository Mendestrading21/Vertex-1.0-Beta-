// @vitest-environment node
/**
 * « Une lumière dominante maximum par carte, deux par écran hors rouge/vert. »
 * — `references/canonical-visual.md`, comportements.
 *
 * POURQUOI CETTE PORTE EXISTE. Avant la primitive, la tranche métallique était
 * posée par une liste de noms :
 *
 *     .vx-chartframe::before,
 *     .vx-today-primary::before,
 *     .vx-snapshot-rail::before,
 *     .vx-pf-summary::before,
 *     .vx-sim-result::before { … }
 *
 * Rien n'arbitrait par PAGE. Sur Portefeuille, `.vx-pf-summary` et
 * `.vx-perf-chart` pouvaient briller ensemble ; sur Aujourd'hui,
 * `.vx-today-primary` et `.vx-snapshot-rail` le faisaient. Deux dominantes sur
 * un écran, c'est zéro dominante : le regard n'a plus de point d'entrée, et
 * c'est précisément la « dérive bento générique » que le contrat refuse.
 *
 * CE QUE LA PORTE MESURE. Le nombre de `rank="dominant"` par fichier de page.
 *
 * CE QU'ELLE NE PROUVE PAS. Un fichier n'est pas une page : un composant
 * enfant pourrait porter son propre dominant, et une page pourrait n'en avoir
 * aucun à l'exécution si sa dominante est conditionnelle. La porte relève le
 * plancher, elle ne ferme pas le sujet — même limite assumée que
 * `no-authoritative-calculation.test.ts`.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const APP_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const PAGES_ROOT = join(APP_ROOT, 'src', 'pages');

function collectPageFiles(directory: string, accumulator: string[]): string[] {
  for (const entry of readdirSync(directory)) {
    const full = join(directory, entry);
    if (statSync(full).isDirectory()) {
      collectPageFiles(full, accumulator);
    } else if (/\.tsx$/.test(full) && !/\.test\.tsx$/.test(full)) {
      accumulator.push(full);
    }
  }
  return accumulator;
}

/** Compte les `rank="dominant"` littéraux d'un fichier. */
function countDominant(source: string, fileName = 'page.tsx'): number {
  const file = ts.createSourceFile(fileName, source, ts.ScriptTarget.ES2022, true, ts.ScriptKind.TSX);
  let total = 0;
  const visit = (node: ts.Node): void => {
    if (ts.isJsxAttribute(node) && node.name.getText(file) === 'rank') {
      const valeur = node.initializer;
      if (valeur !== undefined && ts.isStringLiteral(valeur) && valeur.text === 'dominant') {
        total += 1;
      } else if (
        valeur !== undefined &&
        ts.isJsxExpression(valeur) &&
        valeur.expression !== undefined &&
        ts.isStringLiteral(valeur.expression) &&
        valeur.expression.text === 'dominant'
      ) {
        total += 1;
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return total;
}

describe('Une seule lumière dominante par page', () => {
  it('aucun fichier de page ne porte deux cartes dominantes', () => {
    const coupables = collectPageFiles(PAGES_ROOT, [])
      .map((path) => ({
        path: relative(APP_ROOT, path),
        total: countDominant(readFileSync(path, 'utf8'), path),
      }))
      .filter((entry) => entry.total > 1);
    expect(
      coupables,
      `Plusieurs dominantes :\n${coupables.map((c) => `  ${c.path} → ${c.total}`).join('\n')}`,
    ).toEqual([]);
  });

  it('la porte voit réellement ce qu’elle annonce', () => {
    // Sans cette vérification, une visite d'AST cassée rendrait la porte
    // silencieusement aveugle — le défaut le plus fréquent de ce dépôt.
    expect(countDominant('<Card rank="dominant" title="A" />')).toBe(1);
    expect(countDominant('<Card rank={"dominant"} title="A" />')).toBe(1);
    expect(countDominant('<><Card rank="dominant" /><Card rank="dominant" /></>')).toBe(2);
    expect(countDominant('<Card rank="quiet" /><Card title="B" />')).toBe(0);
  });
});
