// @vitest-environment node
/**
 * Garde-fou de la phase « affichage d'abord » : AUCUNE valeur de planche
 * recopiée dans une page.
 *
 * POURQUOI CE FICHIER EXISTE. Les douze planches canoniques sont étiquetées
 * `DONNÉES FICTIVES` et portent des centaines de chiffres — « 286 420 CHF »,
 * « 97,42 USD », « +2,35 % », « 94 % ». La consigne produit est de livrer la
 * composition AVANT les branchements. Le risque de cet ordre est évident et
 * unique : qu'un chiffre de maquette finisse collé dans un composant pour
 * « remplir » un module, et qu'il devienne indiscernable d'une donnée servie.
 *
 * `.claude/rules/financial-safety.md` l'interdit sans ambiguïté — « aucun mock,
 * fixture, placeholder ou résultat synthétique ne peut être montré comme réel »
 * — mais l'interdiction reposait jusqu'ici sur la discipline. Ce fichier la
 * transforme en porte.
 *
 * CE QUE LA GARDE REFUSE : un littéral de chaîne, dans le rendu d'une PAGE, qui
 * a la forme d'une valeur financière formatée — un décimal à virgule française,
 * un nombre à séparateur de milliers, ou un nombre immédiatement suivi d'une
 * unité monétaire ou d'un pourcentage.
 *
 * CE QU'ELLE N'EST PAS. Elle ne juge pas les nombres NUMÉRIQUES (index,
 * longueurs, largeurs de viewport) : un `slice(0, 5)` n'est pas une valeur
 * financière, et les traquer produirait des faux positifs qu'on finirait par
 * désactiver. Elle vise la forme RENDUE, celle qu'un lecteur prendrait pour une
 * donnée.
 *
 * CE QU'ELLE NE PROUVE PAS. Une valeur assemblée à l'exécution
 * (`${a},${b} %`) lui échappe, comme lui échappe une valeur lue depuis une
 * constante d'un autre fichier. C'est la même limite assumée que
 * `no-authoritative-calculation.test.ts` : elle relève le plancher, elle ne
 * ferme pas le sujet.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const APP_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const PAGES_ROOT = join(APP_ROOT, 'src', 'pages');
/**
 * LOT L0 — EXTENSION DU PÉRIMÈTRE. Les primitives du socle v2 vivent dans
 * `src/components/widgets` et certaines viennent de `src/pages`
 * (`InstrumentTile`, déplacée depuis `pages/InstrumentWidget.tsx`). Un
 * déplacement ne doit JAMAIS sortir un fichier du périmètre d'une porte : le
 * balayage couvre les deux racines, et un test ci-dessous refuse qu'une racine
 * devienne vide.
 */
const WIDGETS_ROOT = join(APP_ROOT, 'src', 'components', 'widgets');
const SCANNED_ROOTS: readonly string[] = [PAGES_ROOT, WIDGETS_ROOT];

/**
 * Formes REFUSÉES. Chacune est celle d'une valeur qu'un lecteur lirait comme
 * une donnée de marché.
 */
const FABRICATED_SHAPES: ReadonlyArray<{ readonly name: string; readonly pattern: RegExp }> = [
  // « 97,42 » « 12 184,20 » — décimal à virgule française.
  { name: 'décimal à virgule', pattern: /\d,\d/ },
  // « 286 420 » — séparateur de milliers par espace (fine ou normale).
  { name: 'séparateur de milliers', pattern: /\d[   ]\d{3}\b/ },
  // « 94 % » — nombre suivi d'un pourcentage, À LA FRANÇAISE.
  //
  // L'ESPACE EST OBLIGATOIRE, et ce n'est pas un détail : `'100%'` sans
  // espace est une DIMENSION CSS (`width: '100%'`, `height: '52%'` dans une
  // configuration ECharts), pas une valeur financière. La typographie
  // française met une espace avant `%` ; la géométrie CSS n'en met jamais.
  // La distinction sépare exactement les deux usages — mesurée sur les neuf
  // premiers signalements de cette porte, dont six étaient des dimensions.
  { name: 'pourcentage littéral', pattern: /\d[   ]%/ },
  // « 250 000 USD » « 97.42 CHF » — nombre suivi d'une devise.
  { name: 'montant en devise', pattern: /\d[   ]?(CHF|EUR|USD|GBP|JPY)\b/ },
];

/**
 * Exemptions NOMMÉES, avec motif écrit. Une entrée doit dire POURQUOI la chaîne
 * n'est pas une valeur fabriquée — jamais qu'elle est pratique.
 */
const ALLOWLIST: ReadonlyArray<{
  readonly path: string;
  readonly text: string;
  readonly reason: string;
}> = [
  // Ces trois chaînes EXPLIQUENT une convention d'unité au lecteur ; elles ne
  // rapportent aucune observation. Retirer le « = 25 % » rendrait la légende
  // incompréhensible : le lecteur ne saurait pas si `0.25` vaut 25 % ou 0,25 %.
  // Elles sont exemptées UNE PAR UNE, par leur texte exact — jamais par
  // fichier, piège déjà payé une fois dans `check_secrets.py`.
  {
    path: 'src/pages/options/optionsView.ts',
    text: 'par point de volatilité (1.00 = 100 %)',
    reason: 'légende d’unité : explique la convention, ne rapporte aucune mesure',
  },
  {
    path: 'src/pages/options/optionsView.ts',
    text: 'par unité de taux (1.00 = 100 %)',
    reason: 'légende d’unité : explique la convention, ne rapporte aucune mesure',
  },
  {
    // LOT-A5 : le composeur vit dans son propre fichier ; même libellé, même motif.
    path: 'src/pages/simulator/SimComposer.tsx',
    text: 'Volatilité annualisée (décimal, 0.25 = 25 %/an)',
    reason: 'libellé de champ de saisie : explique l’unité attendue, ne rapporte rien',
  },
  {
    path: 'src/pages/options/OptionInspector.tsx',
    text: 'volatilité annualisée (décimal, 0.25 = 25 %/an), côté',
    reason: 'légende d’unité de l’inspecteur : la valeur, elle, vient du DTO juste avant',
  },
];

interface Finding {
  readonly path: string;
  readonly line: number;
  readonly shape: string;
  readonly text: string;
}

function collectPageFiles(directory: string, accumulator: string[]): string[] {
  for (const entry of readdirSync(directory)) {
    const full = join(directory, entry);
    if (statSync(full).isDirectory()) {
      collectPageFiles(full, accumulator);
    } else if (
      /\.tsx?$/.test(full) &&
      !full.endsWith('.d.ts') &&
      !/\.test\.tsx?$/.test(full)
    ) {
      accumulator.push(full);
    }
  }
  return accumulator;
}

function scan(path: string): Finding[] {
  const source = ts.createSourceFile(
    path,
    readFileSync(path, 'utf8'),
    ts.ScriptTarget.ES2022,
    true,
    ts.ScriptKind.TSX,
  );
  const findings: Finding[] = [];

  const inspect = (text: string, node: ts.Node): void => {
    for (const shape of FABRICATED_SHAPES) {
      if (!shape.pattern.test(text)) {
        continue;
      }
      const relativePath = relative(APP_ROOT, path);
      // Comparaison sur le texte NORMALISÉ : un nœud JSX porte son indentation
      // et ses retours à la ligne, qui n'ont rien à voir avec ce que le lecteur
      // voit. Comparer brut obligerait à coller une chaîne indentée dans
      // l'exemption, illisible et fragile au moindre reformatage.
      const normalise = (value: string): string => value.replace(/\s+/g, ' ').trim();
      const exempted = ALLOWLIST.some(
        (entry) => entry.path === relativePath && normalise(entry.text) === normalise(text),
      );
      if (exempted) {
        return;
      }
      findings.push({
        path: relativePath,
        line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1,
        shape: shape.name,
        text: text.length > 60 ? `${text.slice(0, 60)}…` : text,
      });
      return;
    }
  };

  const visit = (node: ts.Node): void => {
    // Les littéraux de chaîne ET le texte JSX : les deux atteignent l'écran.
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      inspect(node.text, node);
    } else if (ts.isJsxText(node)) {
      inspect(node.text, node);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return findings;
}

describe('Aucune valeur de planche recopiée dans une page', () => {
  it('aucun littéral n’a la forme d’une donnée financière servie', () => {
    const findings = SCANNED_ROOTS.flatMap((root) => collectPageFiles(root, [])).flatMap(scan);
    expect(
      findings,
      `Valeurs fabriquées trouvées :\n${findings
        .map((f) => `  ${f.path}:${f.line} — ${f.shape} — « ${f.text} »`)
        .join('\n')}`,
    ).toEqual([]);
  });

  it('les deux racines sont réellement balayées (aucune ne devient vide)', () => {
    for (const root of SCANNED_ROOTS) {
      expect(collectPageFiles(root, []).length, `racine vide : ${root}`).toBeGreaterThan(0);
    }
    const balayes = SCANNED_ROOTS.flatMap((root) => collectPageFiles(root, [])).map((file) =>
      relative(APP_ROOT, file),
    );
    // La primitive déplacée au lot L0 reste couverte, à sa nouvelle place.
    expect(balayes).toContain(join('src', 'components', 'widgets', 'InstrumentTile.tsx'));
  });

  it('la garde voit réellement les formes qu’elle annonce', () => {
    // Sans cette vérification, une expression régulière cassée rendrait la
    // porte silencieusement aveugle — le défaut le plus fréquent de ce dépôt.
    const echantillons = ['97,42', '286 420', '94 %', '250 000 USD'];
    for (const echantillon of echantillons) {
      expect(
        FABRICATED_SHAPES.some((shape) => shape.pattern.test(echantillon)),
        `la garde ne voit pas « ${echantillon} »`,
      ).toBe(true);
    }
  });

  it('elle laisse passer ce qui n’est pas une valeur financière', () => {
    const innocents = [
      '2026-08-24',
      'RSI (14)',
      'Aller au contenu principal',
      'v1',
      // Géométrie CSS : sans espace avant `%`, ce n'est pas une valeur.
      '100%',
      '52%',
    ];
    for (const innocent of innocents) {
      expect(
        FABRICATED_SHAPES.some((shape) => shape.pattern.test(innocent)),
        `faux positif sur « ${innocent} »`,
      ).toBe(false);
    }
  });
});
