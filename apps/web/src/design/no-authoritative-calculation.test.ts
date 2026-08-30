// @vitest-environment node
/**
 * Garde-fou automatisé : aucun calcul financier faisant autorité en TypeScript.
 *
 * `.claude/rules/frontend.md` l'interdit depuis le premier jour — « ne calculer
 * en TypeScript aucun prix, IV, Greek, rendement, risque, ratio, score,
 * probabilité, gate, classement financier ou verdict faisant autorité » — et
 * `manifests/traceability.yaml` marquait cette interdiction PROUVÉE en
 * s'appuyant sur trois tests de vue. Ces trois tests couvrent les vues qu'ils
 * testent, pas le dépôt : un calcul ajouté dans une vue non couverte passait.
 * La matrice l'avouait ; ce fichier ferme l'aveu.
 *
 * RÈGLE. Est une violation toute opération arithmétique (`+ - * / % **` et
 * leurs affectations composées) dont une opérande LIT une grandeur financière
 * relayée par l'API — directement (`row.premium`, `row['pnl']`) ou après
 * coercition numérique (`Number(row.premium)`, `parseFloat(o.delta)`), qui est
 * le chemin de blanchiment évident.
 *
 * CE QUI N'EST PAS UNE VIOLATION, et pourquoi :
 * - la concaténation de chaînes. Interpoler `${row.pnl}` dans une phrase
 *   affiche la valeur du serveur telle quelle — c'est le comportement EXIGÉ,
 *   pas une infraction. Sans cette exclusion, la garde signalait le libellé
 *   accessible de `PayoffChart.tsx`, qui est précisément du relais verbatim ;
 * - l'arithmétique sur des grandeurs non financières : index de tableau,
 *   `length - 1`, décalages de dates. Le vocabulaire fermé ci-dessous les
 *   laisse passer par construction.
 *
 * CE QUE CETTE GARDE NE PROUVE PAS. Elle est SYNTAXIQUE et repose sur les NOMS.
 * Un calcul sur une variable intermédiaire dont le nom sort du vocabulaire
 * (`const b = row.bid; const c = b * 2;`) lui échappe, comme lui échappent une
 * valeur passée à une fonction qui calcule ailleurs, ou un nom assemblé à
 * l'exécution. C'est la même limite, assumée et écrite, que
 * `tools/check_financial_boundary.py` côté Python. Elle relève le plancher ;
 * elle ne ferme pas le sujet.
 *
 * Ce fichier est le vérificateur : il est le seul exclu de son propre balayage.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const APP_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const SELF = fileURLToPath(import.meta.url);

/**
 * Vocabulaire FERMÉ des grandeurs financières relayées. Une propriété portant
 * l'un de ces noms est une valeur d'autorité : l'interface l'affiche, elle ne
 * la recalcule pas. La liste est explicite plutôt qu'heuristique — une
 * heuristique produirait des faux positifs qu'on finirait par désactiver.
 */
const FINANCIAL_PROPERTIES: ReadonlySet<string> = new Set([
  // prix et cotations
  'price', 'bid', 'ask', 'mid', 'last', 'close', 'open', 'high', 'low',
  // options
  'premium', 'strike', 'multiplier',
  'delta', 'gamma', 'theta', 'vega', 'rho', 'iv', 'implied_volatility',
  'volume', 'open_interest',
  // portefeuille et performance
  'pnl', 'realized_pnl', 'unrealized_pnl', 'cost_basis', 'market_value',
  'quantity', 'notional', 'weight', 'exposure', 'concentration',
  'drawdown', 'twr', 'xirr', 'change', 'change_percent',
  // décision
  'score', 'probability', 'ratio', 'risk_reward', 'rr',
]);

const ARITHMETIC: ReadonlySet<ts.SyntaxKind> = new Set([
  ts.SyntaxKind.PlusToken,
  ts.SyntaxKind.MinusToken,
  ts.SyntaxKind.AsteriskToken,
  ts.SyntaxKind.SlashToken,
  ts.SyntaxKind.PercentToken,
  ts.SyntaxKind.AsteriskAsteriskToken,
  ts.SyntaxKind.PlusEqualsToken,
  ts.SyntaxKind.MinusEqualsToken,
  ts.SyntaxKind.AsteriskEqualsToken,
  ts.SyntaxKind.SlashEqualsToken,
]);

const NUMERIC_COERCIONS: ReadonlySet<string> = new Set(['Number', 'parseFloat', 'parseInt']);

/**
 * Exemptions NOMMÉES, avec motif écrit. Vide aujourd'hui : le dépôt ne contient
 * aucun calcul autoritaire en TypeScript. Une entrée ajoutée ici doit dire
 * POURQUOI le calcul n'est pas autoritaire — pas qu'il est pratique.
 */
const ALLOWLIST: ReadonlyArray<{ path: string; line: number; reason: string }> = [];

interface Finding {
  readonly path: string;
  readonly line: number;
  readonly property: string;
  readonly snippet: string;
}

function collectFiles(directory: string, accumulator: string[]): string[] {
  for (const entry of readdirSync(directory)) {
    const full = join(directory, entry);
    if (statSync(full).isDirectory()) {
      collectFiles(full, accumulator);
    } else if (/\.tsx?$/.test(full) && !full.endsWith('.d.ts') && full !== SELF) {
      accumulator.push(full);
    }
  }
  return accumulator;
}

/** Nom de propriété lu par une expression, s'il y en a un. */
function accessedName(node: ts.Node): string | null {
  if (ts.isPropertyAccessExpression(node)) {
    return node.name.text;
  }
  if (ts.isElementAccessExpression(node) && ts.isStringLiteral(node.argumentExpression)) {
    return node.argumentExpression.text;
  }
  return null;
}

/** L'expression lit-elle une grandeur financière, directement ou par coercition ? */
function readsFinancialValue(node: ts.Node): string | null {
  let found: string | null = null;
  const visit = (current: ts.Node): void => {
    if (found !== null) {
      return;
    }
    const name = accessedName(current);
    if (name !== null && FINANCIAL_PROPERTIES.has(name)) {
      found = name;
      return;
    }
    if (ts.isCallExpression(current)) {
      const callee = current.expression;
      const calleeName = ts.isIdentifier(callee)
        ? callee.text
        : ts.isPropertyAccessExpression(callee)
          ? callee.name.text
          : null;
      if (calleeName !== null && NUMERIC_COERCIONS.has(calleeName)) {
        for (const argument of current.arguments) {
          visit(argument);
        }
      }
    }
    ts.forEachChild(current, visit);
  };
  visit(node);
  return found;
}

/** `+` dont une opérande est textuelle : concaténation, jamais un calcul. */
function isStringConcatenation(node: ts.BinaryExpression): boolean {
  if (node.operatorToken.kind !== ts.SyntaxKind.PlusToken) {
    return false;
  }
  const isTextual = (side: ts.Expression): boolean =>
    ts.isStringLiteral(side) ||
    ts.isTemplateExpression(side) ||
    ts.isNoSubstitutionTemplateLiteral(side) ||
    (ts.isBinaryExpression(side) && isStringConcatenation(side));
  return isTextual(node.left) || isTextual(node.right);
}

/** Balaie une source et rend les violations, avec le nombre d'opérations vues. */
function scanSource(
  path: string,
  text: string,
): { findings: Finding[]; arithmeticSeen: number } {
  const source = ts.createSourceFile(path, text, ts.ScriptTarget.ES2022, true);
  const findings: Finding[] = [];
  let arithmeticSeen = 0;

  const visit = (node: ts.Node): void => {
    if (ts.isBinaryExpression(node) && ARITHMETIC.has(node.operatorToken.kind)) {
      arithmeticSeen += 1;
      if (!isStringConcatenation(node)) {
        const property = readsFinancialValue(node.left) ?? readsFinancialValue(node.right);
        if (property !== null) {
          findings.push({
            path,
            line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1,
            property,
            snippet: node.getText(source).replace(/\s+/g, ' ').slice(0, 120),
          });
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return { findings, arithmeticSeen };
}

describe('interdiction du calcul financier autoritaire en TypeScript', () => {
  const files = collectFiles(join(APP_ROOT, 'src'), []);
  const scanned = files.map((file) => ({
    file,
    ...scanSource(relative(APP_ROOT, file), readFileSync(file, 'utf8')),
  }));

  it('aucune arithmétique sur une grandeur financière relayée', () => {
    const violations = scanned
      .flatMap((entry) => entry.findings)
      .filter(
        (finding) =>
          !ALLOWLIST.some(
            (exempt) => exempt.path === finding.path && exempt.line === finding.line,
          ),
      );
    expect(
      violations.map((v) => `${v.path}:${v.line} [${v.property}] ${v.snippet}`),
      'le verdict financier appartient à vertex_core, jamais au navigateur',
    ).toEqual([]);
  });

  // Anti-vacuité du balayage lui-même : un « zéro violation » obtenu parce que
  // rien n'a été lu ne vaut rien. Ces deux bornes sont volontairement basses ;
  // elles détectent un balayage cassé, pas une variation de taille du dépôt.
  it('le balayage a réellement lu le dépôt web', () => {
    expect(scanned.length).toBeGreaterThan(50);
    const arithmetic = scanned.reduce((total, entry) => total + entry.arithmeticSeen, 0);
    expect(arithmetic).toBeGreaterThan(20);
  });

  it('aucune exemption morte', () => {
    const positions = new Set(
      scanned.flatMap((entry) => entry.findings).map((f) => `${f.path}:${f.line}`),
    );
    const dead = ALLOWLIST.filter((exempt) => !positions.has(`${exempt.path}:${exempt.line}`));
    expect(
      dead.map((exempt) => `${exempt.path}:${exempt.line}`),
      "une exemption qui n'exempte plus rien doit être retirée",
    ).toEqual([]);
  });
});

// Preuve par injection. Une garde qui ne signale jamais rien est une porte
// fermée à clé sur une pièce vide : le dépôt est propre aujourd'hui, donc le
// balayage ci-dessus ne prouve, à lui seul, RIEN sur la capacité à détecter.
describe('le détecteur détecte — preuve par injection', () => {
  const DOIT_DETECTER: ReadonlyArray<readonly [string, string]> = [
    ['mid recalculé côté client', 'const mid = (quote.bid + quote.ask) / 2;'],
    ['P&L recalculé', 'const gain = row.quantity * (row.last - row.cost_basis);'],
    ['notional recalculé', 'const n = leg.strike * leg.multiplier;'],
    ['coercition puis calcul', 'const x = Number(row.premium) * 100;'],
    ['blanchiment par parseFloat', 'const y = parseFloat(o.delta) + parseFloat(o.gamma);'],
    ['accès par index littéral', "const z = row['pnl'] - row['cost_basis'];"],
    ['affectation composée', 'let total = 0; total += position.market_value;'],
    ['score repondéré', 'const s = item.score * 0.5;'],
    ['probabilité rééchelonnée', 'const p = candidate.probability / 100;'],
  ];

  const NE_DOIT_PAS_DETECTER: ReadonlyArray<readonly [string, string]> = [
    // Le `$` est séparé de son accolade pour que le littéral de CE fichier ne
    // contienne aucun marqueur de gabarit : Biome le prendrait pour un gabarit
    // oublié, et désactiver la règle pour un test serait pire que l'écrire
    // ainsi. Le code injecté, lui, est bien `const t = `gain ${row.pnl}` + " fin";`.
    ['concaténation affichant la valeur serveur', 'const t = `gain ' + '$' + '{row.pnl}` + " fin";'],
    ['index de tableau', 'const p = points[i + 1];'],
    ['longueur de liste', 'const n = rows.length - 1;'],
    ['champ non financier', 'const d = event.day_offset + 1;'],
    ['valeur relayée sans calcul', 'const label = String(row.pnl);'],
    ['comparaison, pas arithmétique', 'const ok = row.pnl === other.pnl;'],
  ];

  it.each(DOIT_DETECTER)('détecte : %s', (_nom, code) => {
    expect(scanSource('injection.ts', code).findings).not.toEqual([]);
  });

  it.each(NE_DOIT_PAS_DETECTER)('ne signale pas : %s', (_nom, code) => {
    expect(scanSource('injection.ts', code).findings).toEqual([]);
  });
});
