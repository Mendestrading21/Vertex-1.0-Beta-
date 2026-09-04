// @vitest-environment node
/**
 * LE TIRET AMBIGU : aucune valeur absente n'est remplacée par un glyphe muet.
 *
 * POURQUOI CETTE PORTE EXISTE. `.claude/rules/frontend.md` l'écrit
 * textuellement — « ne jamais remplacer une donnée absente par `0`, `—`
 * ambigu, une fixture ou une ancienne valeur non datée » — et l'interface le
 * violait 163 fois, sur 33 fichiers. Le pire cas mesuré :
 * `<dd className="vx-num">{reference.eventsUpcoming ?? '—'}</dd>`, dans une
 * liste où les voisins affichent de VRAIS comptes. Un lecteur ne peut pas
 * distinguer « zéro événement servi » de « compteur non publié ». Ce n'est pas
 * de la cosmétique : c'est exactement le fait financier que l'invariant
 * protège.
 *
 * Un défaut réel s'y cachait, au-delà de l'ambiguïté :
 * `portfolioView.ts` typait `lotId: string` avec `?? '—'` en repli, et cette
 * valeur servait de CLÉ REACT. Deux lots exclus sans `lot_id`, même ticker,
 * même raison, donnaient deux fois la même clé.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * CE QU'ELLE REFUSE — trois règles, chacune vérifiée par un test plus bas.
 *
 *   A. ÉGALITÉ EXACTE, SANS `trim`, sur un littéral de chaîne.
 *      L'absence de `trim` n'est pas un oubli : c'est le cœur de la règle.
 *      Le dépôt contient des séparateurs de prose écrits `{' — '}` — avec
 *      leurs espaces. Un substitut n'en a pas. LES ESPACES PORTENT
 *      L'INTENTION.
 *
 *   B. POSITION DE REPLI, avec `trim` — l'anti-contournement de A.
 *      Même jeu de glyphes, espaces ignorés, mais seulement quand le nœud
 *      occupe une position de repli : opérande droit de `??` ou `||`, branche
 *      d'un ternaire, argument d'un `return`, valeur d'une propriété. Un
 *      séparateur de prose n'apparaît JAMAIS dans ces quatre positions.
 *
 *   C. TEXTE JSX ENFANT UNIQUE.
 *      Un `<td>—</td>` est un substitut ; un `{' '}— <code>{x}</code>` est de
 *      la ponctuation. La condition d'enfant unique sépare les deux.
 *
 * EXCLUSION TRANSVERSE : un littéral COMPARÉ n'est pas un rendu.
 * `if (signe === '-')` lit le SIGNE SERVI d'une chaîne financière
 * (`KpiDelta.tsx`). C'est cette exclusion qui permet en retour d'ajouter le
 * trait d'union au jeu de glyphes.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * CE QU'ELLE NE PROUVE PAS — et le dire est une condition de sa survie.
 *
 *   1. Elle voit des LITTÉRAUX, pas des rendus. `const TIRET = '—'` dans
 *      un module tiers puis `{x ?? TIRET}` lui échappe, comme
 *      `String.fromCharCode(8212)`. La règle B ferme les positions de repli,
 *      pas l'indirection.
 *   2. Elle ne juge pas la VÉRITÉ du remplacement : remplacer `?? '—'` par
 *      `?? '0'` la passe. C'est `no-fabricated-values.test.ts` et les tests de
 *      page qui couvrent cela.
 *   3. Elle ne sait pas si la `reason` d'un `AbsentCell` vient du serveur.
 *      `reason="crossed_quote"` en dur passerait. Seuls `absence.test.tsx` et
 *      la revue le voient.
 *   4. Elle ne couvre pas les fichiers de test, délibérément : un test a le
 *      droit d'asserter `toBe('—')` sur la cellule dense légitime.
 *   5. Elle ne prouve rien sur la lisibilité. Un `AbsentCell` posé dans une
 *      carte à trois champs est laid et légal.
 *
 * Même limite assumée que `no-authoritative-calculation.test.ts` : elle relève
 * le plancher, elle ne ferme pas le sujet.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const APP_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const PAGES_ROOT = join(APP_ROOT, 'src', 'pages');
/**
 * PÉRIMÈTRE PLUS LARGE que `no-fabricated-values.test.ts`, qui ne balaie que
 * `src/components/widgets`. Il doit l'être : `components/ai/AiAnswerView.tsx`,
 * `components/inspector/SnapshotFacts.tsx`, `components/markets/SectorGrid.tsx`
 * et `components/calendar/AgendaLine.tsx` rendent tous des valeurs servies.
 */
const COMPONENTS_ROOT = join(APP_ROOT, 'src', 'components');
const SCANNED_ROOTS: readonly string[] = [PAGES_ROOT, COMPONENTS_ROOT];

/**
 * Les glyphes qui se substituent à une valeur. Les variantes de tiret ferment
 * le contournement par homoglyphe ; `?` et `N/A` sont le MÊME défaut avec un
 * autre caractère, et le dépôt en portait dix.
 */
const GLYPHS: ReadonlySet<string> = new Set([
  '—', // — cadratin
  '–', // – demi-cadratin
  '―', // ― barre horizontale
  '‒', // ‒ tiret numéral
  '−', // − signe moins
  '-',
  '--',
  '?',
  'N/A',
  'n/a',
  's.o.',
]);

/**
 * LES POINTS DE SUSPENSION N'Y SONT PAS, et c'est mesuré. Le seul site du
 * dépôt qui en écrit (`SyntheticBanner.tsx`) les AJOUTE après un libellé servi
 * tronqué : ils marquent une troncature, pas une absence. Les inclure aurait
 * produit un faux positif et zéro défaut réel.
 */

/**
 * Exemptions PERMANENTES. Une entrée dit POURQUOI ce n'est pas un défaut —
 * jamais qu'elle est pratique. Exemption par FICHIER ici, et c'est délibéré :
 * le fichier exempté est la source unique du glyphe, il fait soixante lignes,
 * et il est relu une fois pour toutes.
 */
const ALLOWLIST: ReadonlyArray<{ readonly path: string; readonly reason: string }> = [
  {
    path: 'src/components/absence.tsx',
    reason:
      'Source UNIQUE du glyphe dans tout le dépôt. `AbsentCell` ne peut être posé ' +
      'sans `quoi`, `nature` ET `reason` : le tiret n’y est pas un repli, c’est le ' +
      'rendu dense d’une absence DÉJÀ qualifiée, avec son nom accessible et son ' +
      'motif servi en attribut. Sa légitimité est vérifiée par absence.test.tsx, ' +
      'pas par cette porte.',
  },
];

/**
 * DETTE T4 — TEMPORAIRE, et elle ne peut que RÉTRÉCIR.
 *
 * Fichiers non encore convertis, avec le lot qui les clôt. La séparation
 * d'avec `ALLOWLIST` est le point de conception : une dette qui se déguise en
 * exemption ne se rembourse jamais — piège déjà payé dans `check_secrets.py`.
 * Le test « la dette ne peut que rétrécir » plus bas est le cliquet : dès ce
 * lot, aucun NOUVEAU fichier ne peut entrer.
 *
 * Cette liste, et le mécanisme qui la porte, disparaissent au dernier lot T4.
 */
const DETTE_T4: ReadonlyArray<{ readonly path: string; readonly lot: string }> = [
  { path: 'src/pages/AttentionQueue.tsx', lot: 'T4-7' },
  { path: 'src/pages/SnapshotRail.tsx', lot: 'T4-7' },
  { path: 'src/pages/SourceHealthMatrix.tsx', lot: 'T4-7' },
  { path: 'src/pages/markets/MarketsPage.tsx', lot: 'T4-6' },
  { path: 'src/pages/options/OptionInspector.tsx', lot: 'T4-6' },
  { path: 'src/pages/options/OptionsModules.tsx', lot: 'T4-6' },
  { path: 'src/pages/options/OptionsPage.tsx', lot: 'T4-6' },
  { path: 'src/pages/simulator/SimResult.tsx', lot: 'T4-7' },
  { path: 'src/pages/simulator/SimulatorModules.tsx', lot: 'T4-7' },
  { path: 'src/pages/simulator/SimulatorPage.tsx', lot: 'T4-7' },
  { path: 'src/pages/sources/SourcesModules.tsx', lot: 'T4-7' },
];

/** Plafond de la dette. Il est ABAISSÉ à chaque lot, jamais relevé. */
const DETTE_MAX = 11;

interface Finding {
  readonly path: string;
  readonly line: number;
  readonly rule: string;
  readonly text: string;
}

function collectFiles(directory: string, accumulator: string[]): string[] {
  for (const entry of readdirSync(directory)) {
    const full = join(directory, entry);
    if (statSync(full).isDirectory()) {
      collectFiles(full, accumulator);
    } else if (/\.tsx?$/.test(full) && !full.endsWith('.d.ts') && !/\.test\.tsx?$/.test(full)) {
      accumulator.push(full);
    }
  }
  return accumulator;
}

/**
 * UN LITTÉRAL QUI N'ATTEINT PAS L'ÉCRAN COMME VALEUR.
 *
 * Quatre classes, chacune découverte par un faux positif de la première
 * version de cette porte — elles sont donc mesurées, pas supposées :
 *
 *   - COMPARÉ : `if (pct.startsWith('-'))` LIT le signe servi d'une chaîne
 *     financière (`marketsView.ts`, `RiskModules.tsx`, `PortfolioInspector`).
 *     C'est une lecture, l'exact contraire d'un substitut.
 *   - ARGUMENT D'APPEL : `evidenceId.replace(/[^a-z]/g, '-')` fabrique une
 *     ancre HTML. Le tiret y est une syntaxe, pas une valeur.
 *   - ÉLÉMENT DE TABLEAU : `new Set(['=', '+', '-', '@'])` déclare un
 *     vocabulaire de préfixes de formule CSV.
 *   - IMPORT / EXPORT / `case`.
 *
 * Sans ces quatre exclusions, le trait d'union serait inutilisable dans le jeu
 * de glyphes — et il faut l'y garder, sinon `?? '-'` contourne la porte.
 */
function isNotRendered(node: ts.Node): boolean {
  const parent = node.parent;
  if (parent === undefined) {
    return false;
  }
  if (ts.isBinaryExpression(parent)) {
    const kind = parent.operatorToken.kind;
    return (
      kind === ts.SyntaxKind.EqualsEqualsEqualsToken ||
      kind === ts.SyntaxKind.ExclamationEqualsEqualsToken ||
      kind === ts.SyntaxKind.EqualsEqualsToken ||
      kind === ts.SyntaxKind.ExclamationEqualsToken
    );
  }
  return (
    ts.isCallExpression(parent) ||
    ts.isNewExpression(parent) ||
    ts.isArrayLiteralExpression(parent) ||
    ts.isCaseClause(parent) ||
    ts.isImportDeclaration(parent) ||
    ts.isExportDeclaration(parent)
  );
}

/** Position de REPLI : là où un glyphe remplace une valeur qui manque. */
function isFallbackPosition(node: ts.Node): boolean {
  const parent = node.parent;
  if (parent === undefined) {
    return false;
  }
  if (ts.isBinaryExpression(parent) && parent.right === node) {
    const kind = parent.operatorToken.kind;
    return (
      kind === ts.SyntaxKind.QuestionQuestionToken || kind === ts.SyntaxKind.BarBarToken
    );
  }
  if (ts.isConditionalExpression(parent)) {
    return parent.whenTrue === node || parent.whenFalse === node;
  }
  if (ts.isReturnStatement(parent)) {
    return true;
  }
  return ts.isPropertyAssignment(parent) && parent.initializer === node;
}

/** Enfant JSX unique : `<td>—</td>` est un substitut, `— <code>x</code>` non. */
function isOnlyJsxChild(node: ts.JsxText): boolean {
  const parent = node.parent;
  if (parent === undefined || !('children' in parent)) {
    return false;
  }
  const children = (parent as ts.JsxElement | ts.JsxFragment).children;
  const meaningful = children.filter(
    (child) => !(ts.isJsxText(child) && child.text.trim() === '') || child === node,
  );
  return meaningful.length === 1;
}

function scanFile(path: string, contents?: string): Finding[] {
  const source = ts.createSourceFile(
    path,
    contents ?? readFileSync(path, 'utf8'),
    ts.ScriptTarget.ES2022,
    true,
    ts.ScriptKind.TSX,
  );
  const findings: Finding[] = [];
  const relativePath = contents === undefined ? relative(APP_ROOT, path) : path;

  const report = (rule: string, text: string, node: ts.Node): void => {
    findings.push({
      path: relativePath,
      line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1,
      rule,
      text,
    });
  };

  const visit = (node: ts.Node): void => {
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      // L'ORDRE COMPTE. Le repli est jugé D'ABORD : `f(x ?? '—')` est un
      // argument d'appel ET un repli — c'est un défaut, et l'exclusion des
      // arguments ne doit pas l'absoudre.
      if (isFallbackPosition(node) && GLYPHS.has(node.text.trim())) {
        report(
          GLYPHS.has(node.text) ? 'A — littéral substitutif' : 'B — repli espacé',
          node.text,
          node,
        );
      } else if (GLYPHS.has(node.text) && !isNotRendered(node)) {
        report('A — littéral substitutif', node.text, node);
      }
    } else if (ts.isJsxText(node) && GLYPHS.has(node.text.trim()) && isOnlyJsxChild(node)) {
      report('C — texte JSX seul', node.text.trim(), node);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return findings;
}

const EXEMPTED: ReadonlySet<string> = new Set([
  ...ALLOWLIST.map((entry) => entry.path),
  ...DETTE_T4.map((entry) => entry.path),
]);

describe('Aucune valeur absente remplacée par un glyphe muet', () => {
  it('aucun fichier converti n’écrit un glyphe substitutif', () => {
    const findings = SCANNED_ROOTS.flatMap((root) => collectFiles(root, []))
      .flatMap((file) => scanFile(file))
      .filter((finding) => !EXEMPTED.has(finding.path));
    expect(
      findings,
      `Glyphes substitutifs trouvés :\n${findings
        .map((f) => `  ${f.path}:${f.line} — ${f.rule} — « ${f.text} »`)
        .join('\n')}`,
    ).toEqual([]);
  });

  it('les deux racines sont réellement balayées (aucune ne devient vide)', () => {
    for (const root of SCANNED_ROOTS) {
      expect(collectFiles(root, []).length, `racine vide : ${root}`).toBeGreaterThan(0);
    }
  });
});

describe('Gouvernance des exemptions', () => {
  it('chaque exemption permanente porte un motif écrit et un fichier réel', () => {
    for (const entry of ALLOWLIST) {
      expect(entry.reason.length, `motif trop court : ${entry.path}`).toBeGreaterThan(80);
      expect(() => statSync(join(APP_ROOT, entry.path)), `fichier absent : ${entry.path}`).not.toThrow();
    }
  });

  it('aucune exemption permanente n’est inutile', () => {
    // Une exemption qui ne couvre plus rien est une exemption morte : elle
    // laisserait passer un défaut futur sans que personne le sache.
    for (const entry of ALLOWLIST) {
      expect(
        scanFile(join(APP_ROOT, entry.path)).length,
        `exemption sans objet, à supprimer : ${entry.path}`,
      ).toBeGreaterThan(0);
    }
  });

  it('la dette ne peut que RÉTRÉCIR — cliquet du lot T4', () => {
    expect(DETTE_T4.length).toBeLessThanOrEqual(DETTE_MAX);
    expect(new Set(DETTE_T4.map((e) => e.path)).size).toBe(DETTE_T4.length);
    for (const entry of DETTE_T4) {
      expect(() => statSync(join(APP_ROOT, entry.path)), `dette fantôme : ${entry.path}`).not.toThrow();
      expect(entry.lot, `lot manquant : ${entry.path}`).toMatch(/^T4-\d$/);
    }
  });

  it('un fichier en dette porte RÉELLEMENT au moins un glyphe', () => {
    // Sinon il est déjà converti et doit sortir de la liste — c'est ce qui
    // fait avancer le cliquet à chaque lot.
    const inutiles = DETTE_T4.filter((entry) => scanFile(join(APP_ROOT, entry.path)).length === 0);
    expect(inutiles.map((e) => e.path), 'dette à retirer : ces fichiers sont propres').toEqual([]);
  });
});

describe('La garde voit ce qu’elle annonce', () => {
  const scan = (code: string): readonly string[] =>
    scanFile('probe.tsx', code).map((f) => f.rule);

  it('règle A — chaque glyphe substitutif est vu', () => {
    for (const glyphe of ['—', '?', '--', 'N/A', '–']) {
      expect(scan(`const x = a ?? '${glyphe}';`), glyphe).toContain('A — littéral substitutif');
    }
  });

  it('règle B — le repli ESPACÉ est vu malgré l’espace', () => {
    expect(scan("const x = a ?? '— ';")).toContain('B — repli espacé');
    expect(scan("function f() { return '—'; }")).not.toEqual([]);
  });

  it('règle C — un texte JSX SEUL est vu, la ponctuation non', () => {
    expect(scan('const x = <td>—</td>;')).toContain('C — texte JSX seul');
    expect(scan('const x = <p>{a} — <code>{b}</code></p>;')).toEqual([]);
  });

  it('la ponctuation française passe : les espaces portent l’intention', () => {
    expect(scan("const x = <p>{' — '}</p>;")).toEqual([]);
    expect(scan("const t = 'Inspecteur — Dossier SYN-TECH-01';")).toEqual([]);
    expect(scan("const t = 'NON — mois incomplet';")).toEqual([]);
  });

  it('un littéral COMPARÉ n’est pas un rendu', () => {
    // `KpiDelta.tsx` lit le SIGNE servi d'une chaîne : c'est une lecture, pas
    // un substitut. Sans cette exclusion, le trait d'union serait inutilisable
    // dans le jeu de glyphes.
    expect(scan("if (signe === '-') { return 'down'; }")).toEqual([]);
    expect(scan("switch (s) { case '?': break; }")).toEqual([]);
  });
});
