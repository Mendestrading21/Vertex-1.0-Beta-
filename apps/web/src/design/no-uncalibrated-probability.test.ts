// @vitest-environment node
/**
 * Garde-fou automatisé : aucune probabilité prédictive lue par l'interface.
 *
 * `CLAUDE.md` et `.claude/rules/financial-safety.md` l'interdisent tous deux :
 * « une probabilité prédictive n'est affichée que si sa calibration, son
 * horizon, sa population, sa validation hors échantillon et sa version sont
 * présents et valides ».
 *
 * CE QUI EST DÉJÀ PROUVÉ AILLEURS, et n'a pas besoin de cette garde :
 * - la gate 8 (`probability_calibrated_if_used`) bloque une probabilité non
 *   calibrée, non validée hors échantillon, ou dont les faits manquent
 *   (`packages/python/vertex_core/tests/decision/test_gates.py`) ;
 * - `AdviceEngine` ne propage `probability_evidence` QUE si cette gate passe
 *   avec `PROBABILITY_CALIBRATED`, et inscrit sinon une limitation écrite
 *   (`packages/python/vertex_core/tests/decision/test_advice.py`, classe
 *   dédiée, quatre cas dont le cas positif) ;
 * - la règle d'abstention côté recherche
 *   (`research/tests/test_calibration.py`).
 *
 * CE QUI NE L'ÉTAIT PAS : le point d'AFFICHAGE. Rien n'empêchait une page
 * future de lire `probability_evidence` et de le rendre sans vérifier les cinq
 * champs. Le champ vaut `null` partout aujourd'hui — la règle tient donc par
 * absence de chemin, ce qui n'est pas une garantie mais un hasard d'étape.
 *
 * RÈGLE. Aucun module web ne LIT `probability_evidence`. La capacité est
 * réservée : l'activer exige une entrée d'exemption nommée ci-dessous, donc
 * une décision écrite, donc une revue des cinq champs obligatoires.
 *
 * Une DÉCLARATION du champ (dans une fixture, un type, un objet littéral)
 * n'est pas une lecture et reste permise : c'est un `PropertyAssignment`, pas
 * un `PropertyAccessExpression`, et l'AST distingue les deux exactement.
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

/** Le champ réservé, et ses variantes d'accès. */
const RESERVED_FIELD = 'probability_evidence';

/**
 * Exemptions NOMMÉES, avec motif écrit. Vide : aucune page ne lit ce champ.
 * Une entrée ajoutée ici doit citer le test qui prouve que les cinq champs
 * obligatoires (calibration, horizon, population, validation hors échantillon,
 * version) sont vérifiés AVANT tout rendu.
 */
const ALLOWLIST: ReadonlyArray<{ path: string; reason: string; provenBy: string }> = [];

interface Read {
  readonly path: string;
  readonly line: number;
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

/** Lectures du champ réservé dans une source, et nombre de mentions vues. */
function scanSource(path: string, text: string): { reads: Read[]; mentions: number } {
  const source = ts.createSourceFile(path, text, ts.ScriptTarget.ES2022, true);
  const reads: Read[] = [];
  let mentions = 0;

  const record = (node: ts.Node): void => {
    reads.push({
      path,
      line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1,
      snippet: node.getText(source).replace(/\s+/g, ' ').slice(0, 100),
    });
  };

  const visit = (node: ts.Node): void => {
    // `x.probability_evidence` — accès en lecture.
    if (ts.isPropertyAccessExpression(node) && node.name.text === RESERVED_FIELD) {
      mentions += 1;
      record(node);
    }
    // `x['probability_evidence']` — même lecture, autre écriture.
    else if (
      ts.isElementAccessExpression(node) &&
      ts.isStringLiteral(node.argumentExpression) &&
      node.argumentExpression.text === RESERVED_FIELD
    ) {
      mentions += 1;
      record(node);
    }
    // `const { probability_evidence } = advice;` — déstructuration : c'est
    // une lecture, même si elle ne ressemble pas à un accès.
    else if (
      ts.isBindingElement(node) &&
      ts.isObjectBindingPattern(node.parent) &&
      ((node.propertyName !== undefined && node.propertyName.getText(source) === RESERVED_FIELD) ||
        (node.propertyName === undefined && node.name.getText(source) === RESERVED_FIELD))
    ) {
      mentions += 1;
      record(node);
    }
    // Une DÉCLARATION (`probability_evidence: null` dans une fixture ou un
    // type) est comptée comme mention mais n'est PAS une lecture.
    else if (
      (ts.isPropertyAssignment(node) || ts.isPropertySignature(node)) &&
      node.name.getText(source).replace(/['"]/g, '') === RESERVED_FIELD
    ) {
      mentions += 1;
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return { reads, mentions };
}

describe('probabilité prédictive : capacité réservée côté interface', () => {
  const scanned = collectFiles(join(APP_ROOT, 'src'), []).map((file) => ({
    ...scanSource(relative(APP_ROOT, file), readFileSync(file, 'utf8')),
  }));

  it('aucun module web ne lit `probability_evidence`', () => {
    const reads = scanned
      .flatMap((entry) => entry.reads)
      .filter((read) => !ALLOWLIST.some((exempt) => exempt.path === read.path));
    expect(
      reads.map((r) => `${r.path}:${r.line} ${r.snippet}`),
      "afficher une probabilité exige d'abord de prouver ses cinq champs obligatoires",
    ).toEqual([]);
  });

  // Anti-vacuité : si le champ disparaissait du contrat, la garde deviendrait
  // verte pour la mauvaise raison. Ce test échoue le jour où plus rien ne le
  // mentionne — il faudra alors décider si la garde a encore un objet.
  it('le champ réservé existe toujours dans le contrat web', () => {
    const mentions = scanned.reduce((total, entry) => total + entry.mentions, 0);
    expect(
      mentions,
      '`probability_evidence` ne figure plus nulle part : la garde surveille un champ disparu',
    ).toBeGreaterThan(0);
  });

  it('aucune exemption morte', () => {
    const paths = new Set(scanned.flatMap((entry) => entry.reads).map((r) => r.path));
    expect(
      ALLOWLIST.filter((exempt) => !paths.has(exempt.path)).map((e) => e.path),
      "une exemption qui n'exempte plus rien doit être retirée",
    ).toEqual([]);
  });
});

// Preuve par injection : le dépôt est propre, donc le balayage ci-dessus ne
// prouve rien à lui seul sur la capacité à détecter.
describe('le détecteur détecte — preuve par injection', () => {
  const DOIT_DETECTER: ReadonlyArray<readonly [string, string]> = [
    ['accès direct', 'const p = advice.probability_evidence;'],
    ['accès par index', "const p = advice['probability_evidence'];"],
    ['déstructuration', 'const { probability_evidence } = advice;'],
    ['déstructuration renommée', 'const { probability_evidence: proba } = advice;'],
    ['rendu conditionnel', 'const node = advice.probability_evidence ? <span /> : null;'],
    ['chaînage optionnel', 'const v = advice?.probability_evidence?.value;'],
  ];

  const NE_DOIT_PAS_DETECTER: ReadonlyArray<readonly [string, string]> = [
    ['déclaration de fixture', 'const fixture = { probability_evidence: null };'],
    ['signature de type', 'interface A { probability_evidence: unknown }'],
    ['champ voisin', 'const x = advice.probability_used;'],
    ['chaîne de caractères seule', "const s = 'probability_evidence';"],
  ];

  it.each(DOIT_DETECTER)('détecte : %s', (_nom, code) => {
    expect(scanSource('injection.tsx', code).reads).not.toEqual([]);
  });

  it.each(NE_DOIT_PAS_DETECTER)('ne signale pas : %s', (_nom, code) => {
    expect(scanSource('injection.tsx', code).reads).toEqual([]);
  });
});
