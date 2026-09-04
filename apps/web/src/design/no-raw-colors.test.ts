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

/**
 * EXEMPTIONS NOMMÉES — une seule, et elle porte sa raison.
 *
 * Le motif est celui déjà employé par `no-ambiguous-dash.test.ts` : une
 * exemption explicite, motivée, et surveillée par un test qui échoue si elle
 * devient inutile. Élargir `isTokenSource` aurait ouvert la porte à tout
 * fichier nommé `tokens.*` ; nommer un fichier ne coûte rien et se voit.
 */
const EXEMPTIONS: ReadonlyArray<{ readonly path: string; readonly reason: string }> = [
  {
    path: join('src', 'design', 'contrast.test.ts'),
    reason:
      "C'est la porte qui MESURE les couleurs. Ses seuls littéraux sont le noir pur et le blanc pur, les deux bornes par lesquelles WCAG 2.2 définit le ratio maximal de 21:1 : ils servent à prouver que la fonction de mesure est juste, sans quoi tout le reste passerait pour de mauvaises raisons. Ce fichier ne rend rien à l'écran et n'est donc pas une seconde source de couleur du produit.",
  },
];

const EXEMPTED: ReadonlySet<string> = new Set(EXEMPTIONS.map((entry) => entry.path));

describe('interdiction des couleurs brutes hors tokens.*', () => {
  const hexPattern = /#[0-9a-fA-F]{3,8}\b/;
  const functionalPattern = /\b(?:rgb|rgba|hsl|hsla)\(/;

  it('aucun hex ni rgb()/hsl() hors src/design/tokens.*', () => {
    const offenders: string[] = [];
    for (const file of scannedFiles()) {
      if (isTokenSource(file) || EXEMPTED.has(relative(APP_ROOT, file))) {
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

  it('chaque exemption porte un motif écrit, un fichier réel, et reste utile', () => {
    for (const { path, reason } of EXEMPTIONS) {
      expect(reason.length, `motif trop court : ${path}`).toBeGreaterThan(80);
      const absolu = join(APP_ROOT, path);
      expect(() => readFileSync(absolu, 'utf8'), `fichier exempté absent : ${path}`).not.toThrow();
      // Une exemption qui ne couvre plus rien est une exemption MORTE : elle
      // laisserait passer une vraie couleur brute sans que personne le sache.
      const contenu = readFileSync(absolu, 'utf8');
      const porteVraimentUneCouleur =
        hexPattern.exec(contenu) !== null || functionalPattern.exec(contenu) !== null;
      expect(porteVraimentUneCouleur, `exemption sans objet, à retirer : ${path}`).toBe(true);
    }
  });
});

describe("interdiction du vocabulaire d'ordre boursier", () => {
  // Termes assemblés par concaténation pour que ce vérificateur ne se signale
  // pas lui-même s'il venait à être balayé.
  //
  // Le titre de ce bloc annonçait « achat/vente/transmission » depuis toujours,
  // mais la liste ne contenait QUE de l'anglais alors que toute l'interface
  // Vertex est en français : `<button>Acheter</button>` passait la garde. Le
  // français est donc ajouté ici, et un cas d'injection le prouve plus bas.
  //
  // `exécuter` / `exécution` sont VOLONTAIREMENT absents comme mots isolés :
  // « preuve d'exécution », « exécution du test » sont partout dans ce dépôt.
  // Seule la locution complète, qui ne peut désigner qu'un ordre boursier, est
  // interdite — voir `phrasePatterns`.
  const forbiddenTerms = [
    'bu' + 'y',
    'se' + 'll',
    'exe' + 'cute',
    'ord' + 'er',
    'ache' + 'ter',
    'ach' + 'at',
    'ach' + 'ats',
    'vend' + 're',
    'reven' + 'dre',
    'ven' + 'te',
    'ven' + 'tes',
  ];
  const termPattern = new RegExp(`\\b(?:${forbiddenTerms.join('|')})\\b`, 'i');

  // Locutions : chacune ne peut désigner qu'une instruction d'ordre, même
  // lorsque ses mots pris isolément sont anodins.
  const phrasePatterns = [
    new RegExp(`(?:pass|envoy|transmett|exécut)\\w*\\s+(?:un|l['’])\\s*ord` + 're', 'i'),
    new RegExp(`ord` + `re\\s+d['’]\\s*(?:ach` + 'at|vente)', 'i'),
  ];

  /**
   * Exemptions NOMMÉES, avec motif écrit.
   *
   * L'interdiction porte sur une INSTRUCTION d'ordre émise par Vertex. Elle ne
   * porte pas sur la désignation d'une transaction que l'utilisateur déclare
   * avoir faite ailleurs : le portefeuille manuel est justement construit sur
   * ces déclarations, et le priver de son vocabulaire rendrait la garde
   * intenable — donc, tôt ou tard, désactivée.
   *
   * Chaque entrée dit pourquoi l'occurrence est un CONSTAT et non un ordre.
   */
  const declaredTransactionAllowlist: ReadonlyArray<{
    path: string;
    term: string;
    reason: string;
  }> = [
    {
      path: join('src', 'pages', 'portfolio', 'portfolioView.ts'),
      term: 'ventes',
      reason:
        "Message d'incohérence du journal manuel : « ventes déclarées supérieures " +
        'aux achats déclarés ». Il DÉCRIT une contradiction dans ce que ' +
        "l'utilisateur a saisi ; il n'invite à aucune action et Vertex n'exécute rien.",
    },
    {
      path: join('src', 'pages', 'portfolio', 'TransactionForm.tsx'),
      term: 'achat',
      reason:
        "Message de validation du journal manuel : « ticker obligatoire pour un fait " +
        "de position (achat/vente enregistré) ». Le formulaire est titré " +
        '« Enregistrer une transaction (déjà exécutée hors Vertex) » et son en-tête ' +
        'dit « journal comptable de FAITS PASSÉS uniquement » : il consigne, il ' +
        "n'émet pas. C'est le site le plus sensible du dépôt sur cette règle, et " +
        "c'est pourquoi son exemption est nommée plutôt que globale.",
    },
    {
      path: join('src', 'test', 'fixtures.ts'),
      term: 'achat',
      reason:
        "Note d'une fixture SYNTHETIC de lot déclaré (« achat enregistré le … »). " +
        "Elle nomme un fait passé saisi par l'utilisateur, jamais une instruction.",
    },
  ];

  function declaredTransactionExemption(
    file: string,
    term: string,
  ): (typeof declaredTransactionAllowlist)[number] | undefined {
    return declaredTransactionAllowlist.find(
      (exempt) => file.endsWith(exempt.path) && exempt.term.toLowerCase() === term.toLowerCase(),
    );
  }

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
      const match =
        termPattern.exec(content) ??
        phrasePatterns.reduce<RegExpExecArray | null>(
          (found, pattern) => found ?? pattern.exec(content),
          null,
        );
      if (match !== null && declaredTransactionExemption(file, match[0]) === undefined) {
        offenders.push(`${relative(APP_ROOT, file)} → ${match[0]}`);
      }
    }
    expect(offenders, `Vocabulaire d'ordre détecté : ${offenders.join(', ')}`).toEqual([]);
  });

  // Preuve par injection. La liste précédente était ANGLAISE alors que toute
  // l'interface est française : la garde passait au vert sur un bouton
  // « Acheter ». Un test qui ne signale jamais rien ne prouve rien ; ces cas
  // figent la capacité de détection dans les deux langues.
  const INSTRUCTIONS_INTERDITES: ReadonlyArray<readonly [string, string]> = [
    ['bouton français', '<button type="button">Ach' + 'eter</button>'],
    ['bouton français, vente', '<button>Ven' + 'dre 100 titres</button>'],
    ['libellé de revente', 'const label = "Reven' + 'dre la position";'],
    ['locution : passer un ordre', 'const t = "Pas' + 'ser un ordre au marché";'],
    ['locution : transmettre un ordre', 'const t = "Trans' + 'mettre un ordre";'],
    ["locution : ordre d'achat", 'const t = "Ord' + "re d'ach" + 'at immédiat";'],
    ['anglais, inchangé', 'const t = "Pla' + 'ce order";'],
  ];

  const TEXTES_LEGITIMES: ReadonlyArray<readonly [string, string]> = [
    ["preuve d'exécution", "// Preuve d'exé" + 'cution de la porte'],
    ['exécution du test', 'const t = "exé' + 'cution du scénario";'],
    ['aucune mention', 'const t = "Analyse du dossier";'],
  ];

  it.each(INSTRUCTIONS_INTERDITES)('détecte une instruction : %s', (_nom, code) => {
    const detecte =
      termPattern.test(code) || phrasePatterns.some((pattern) => pattern.test(code));
    expect(detecte, `non détecté : ${code}`).toBe(true);
  });

  it.each(TEXTES_LEGITIMES)('ne signale pas : %s', (_nom, code) => {
    const detecte =
      termPattern.test(code) || phrasePatterns.some((pattern) => pattern.test(code));
    expect(detecte, `faux positif : ${code}`).toBe(false);
  });

  it("aucune exemption de transaction déclarée n'est morte", () => {
    const dead = declaredTransactionAllowlist.filter((exempt) => {
      const file = scannedFiles().find((candidate) => candidate.endsWith(exempt.path));
      if (file === undefined) {
        return true;
      }
      const content = readFileSync(file, 'utf8');
      return !new RegExp(`\\b${exempt.term}\\b`, 'i').test(content);
    });
    expect(
      dead.map((exempt) => `${exempt.path} → ${exempt.term}`),
      "une exemption qui n'exempte plus rien doit être retirée",
    ).toEqual([]);
  });

  it('schema.d.ts généré : le vocabulaire n’apparaît que dans une négation du contrat', () => {
    // Chaque phrase autorisée est une NÉGATION écrite par le backend (le
    // contrat interdit la capacité) ; certaines s'étalent sur deux lignes de
    // JSDoc, d'où la fenêtre ligne courante + ligne précédente.
    const negationPatterns = [
      /nothing here is, or ever becomes/i,
      /none of these is\s+(?:\*\s*)?an instruction, an ord/i,
    ];
    const generated = scannedFiles().find((file) => isGeneratedSchema(file));
    expect(generated).toBeDefined();
    const lines = readFileSync(generated!, 'utf8').split('\n');
    for (const [index, line] of lines.entries()) {
      if (!termPattern.test(line)) {
        continue;
      }
      const window = `${lines[index - 1] ?? ''}\n${line}`;
      expect(
        negationPatterns.some((pattern) => pattern.test(window)),
        `Occurrence non couverte par une négation du contrat : ${line.trim()}`,
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

  it('les nouveaux fichiers V5 (calendrier, opportunités, Vertex IA) sont bien balayés', () => {
    const files = scannedFiles().map((file) => relative(APP_ROOT, file));
    for (const expected of [
      join('src', 'api', 'decisionApi.ts'),
      join('src', 'pages', 'calendar', 'CalendarPage.tsx'),
      join('src', 'pages', 'calendar', 'EventAgenda.tsx'),
      join('src', 'pages', 'calendar', 'calendarView.ts'),
      join('src', 'pages', 'opportunities', 'OpportunitiesPage.tsx'),
      join('src', 'pages', 'opportunities', 'OpportunityTable.tsx'),
      join('src', 'pages', 'opportunities', 'opportunitiesView.ts'),
      // LOT-12 : l'explication IA vit dans l'inspecteur. Les trois fichiers
      // restent balayés — un déplacement ne sort jamais un fichier du
      // périmètre des gardes.
      join('src', 'components', 'ai', 'AiExplanationPanel.tsx'),
      join('src', 'components', 'ai', 'AiAnswerView.tsx'),
      join('src', 'components', 'ai', 'aiView.ts'),
    ]) {
      expect(files, `${expected} doit être couvert par les gardes`).toContain(expected);
    }
  });

  it('les nouveaux fichiers V4 (portefeuille, suivi, performance) sont bien balayés', () => {
    const files = scannedFiles().map((file) => relative(APP_ROOT, file));
    for (const expected of [
      join('src', 'pages', 'portfolio', 'PortfolioPage.tsx'),
      join('src', 'pages', 'portfolio', 'PortfolioSummary.tsx'),
      join('src', 'pages', 'portfolio', 'PortfolioTable.tsx'),
      join('src', 'pages', 'portfolio', 'ConcentrationPanel.tsx'),
      join('src', 'pages', 'portfolio', 'LedgerPanel.tsx'),
      join('src', 'pages', 'portfolio', 'TransactionForm.tsx'),
      join('src', 'pages', 'portfolio', 'CsvImportPanel.tsx'),
      join('src', 'pages', 'portfolio', 'portfolioView.ts'),
      // LOT-10 : le module de revue vit sous Catalyseurs. Les quatre fichiers
      // restent balayés — un déplacement ne sort jamais un fichier du
      // périmètre des gardes. S'y ajoutent les deux fichiers créés.
      join('src', 'pages', 'catalysts', 'review', 'ReviewQueueSection.tsx'),
      join('src', 'pages', 'catalysts', 'review', 'ThesisSheet.tsx'),
      join('src', 'pages', 'catalysts', 'review', 'ThesisForm.tsx'),
      join('src', 'pages', 'catalysts', 'review', 'followUpView.ts'),
      join('src', 'pages', 'catalysts', 'CatalystsPage.tsx'),
      join('src', 'pages', 'catalysts', 'CatalystTimeline.tsx'),
      join('src', 'pages', 'catalysts', 'catalystsView.ts'),
      // LOT-08 : le module Performance vit sous Portefeuille. Les quatre
      // fichiers restent balayés — un déplacement ne doit jamais sortir un
      // fichier du périmètre des gardes.
      join('src', 'pages', 'portfolio', 'performance', 'PerformanceSection.tsx'),
      join('src', 'pages', 'portfolio', 'performance', 'PerformanceChart.tsx'),
      join('src', 'pages', 'portfolio', 'performance', 'MonthlyHeatmap.tsx'),
      join('src', 'pages', 'portfolio', 'performance', 'performanceView.ts'),
    ]) {
      expect(files, `${expected} doit être couvert par les gardes`).toContain(expected);
    }
  });
});
