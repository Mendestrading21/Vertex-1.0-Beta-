// @vitest-environment node
/**
 * Porte du canon Titanium Ledger v2 (ADR-017).
 *
 * POURQUOI CETTE PORTE EXISTE. Le 2026-09-03, la décision de l'utilisateur a
 * levé plusieurs interdictions de forme (anneaux à chiffre central, jauges en
 * arc, aires à dégradé, rails, matrices de bandes, teinte secondaire par page)
 * — UNIQUEMENT sur des données servies. Ces interdictions vivaient dans une
 * douzaine de documents ; une seule formulation oubliée, et deux textes
 * normatifs se contredisent, ce qui revient à n'avoir aucune règle.
 *
 * CE QUE LA PORTE MESURE.
 * 1. L'ADR existe, est Acceptée, et écrit chaque forme admise ET chaque
 *    interdit maintenu — lever une règle ne doit jamais en effacer une autre.
 * 2. Les formulations levées ne reviennent dans aucun document du canon.
 * 3. Chaque document du canon cite ADR-017 : une règle v2 sans sa décision est
 *    une règle sans autorité.
 * 4. Les invariants NON levés sont toujours écrits là où ils l'étaient.
 *
 * CE QU'ELLE NE PROUVE PAS. Qu'un widget respecte la règle : c'est le rôle des
 * portes `no-authoritative-calculation`, `no-fabricated-values` et
 * `no-raw-colors`, et des tests des primitives du socle L0.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const REPO_ROOT = fileURLToPath(new URL('../../../../', import.meta.url));
const ADR_PATH = 'docs/09-adr/017-titanium-ledger-v2-formes-widgets.md';

function read(relativePath: string): string {
  return readFileSync(join(REPO_ROOT, relativePath), 'utf8');
}

/** Espaces et retours à la ligne repliés : un reflow de paragraphe n'est pas un changement de règle. */
function flat(text: string): string {
  return text.replace(/\s+/g, ' ');
}

/** Documents du canon mis en cohérence par le lot C0. Chacun cite ADR-017. */
const CANON_DOCS = [
  'docs/05-design/DESIGN_SYSTEM.md',
  'docs/05-design/CHART_STANDARD.md',
  'docs/05-design/WIDGET_LIBRARY.md',
  'docs/05-design/TOKENS.md',
  'docs/05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md',
  'docs/05-design/VERTEX_ONE_VISUAL_DIRECTION.md',
  'docs/05-design/DASHBOARD_COMPOSITION.md',
  'docs/05-design/MOTION_AND_MICROINTERACTIONS.md',
  'docs/05-design/WIDGETS_V2_PLAN.md',
  '.claude/skills/vertex-titanium-ledger/references/canonical-visual.md',
  '.claude/skills/vertex-titanium-ledger/references/visual-identity.md',
  '.claude/skills/vertex-titanium-ledger/references/component-system.md',
  '.claude/skills/vertex-titanium-ledger/references/charts.md',
  'manifests/widget-catalog.yaml',
] as const;

/**
 * Formulations LEVÉES par ADR-017, telles qu'elles étaient écrites (relevées
 * sur `main@4fc901a`). Chacune a été remplacée par la règle v2 avec sa
 * condition « donnée servie ». Leur retour serait une contradiction.
 */
const LIFTED_FORMULATIONS: ReadonlyArray<{ file: string; formulation: string }> = [
  { file: 'docs/05-design/DESIGN_SYSTEM.md', formulation: 'gradients réservés à sélection/action principale ;' },
  {
    file: 'docs/05-design/DESIGN_SYSTEM.md',
    formulation: 'jauges uniquement linéaires/segmentées, nommées et sourcées ; aucun cadran décoratif ou score opaque ;',
  },
  { file: 'docs/05-design/CHART_STANDARD.md', formulation: 'SVG/CSS interne : sparklines et micro-barres simples seulement.' },
  { file: 'docs/05-design/CHART_STANDARD.md', formulation: 'Formes autorisées : barre linéaire, bullet chart et bande segmentée.' },
  { file: 'docs/05-design/CHART_STANDARD.md', formulation: 'Aucun speedometer, score opaque, aiguille animée ou 3D.' },
  {
    file: 'docs/05-design/WIDGET_LIBRARY.md',
    formulation:
      'Elles utilisent une barre linéaire, un bullet chart ou une bande segmentée ; aucun compteur automobile, aiguille animée, volume 3D ou score composite opaque.',
  },
  { file: 'docs/05-design/TOKENS.md', formulation: 'motion : 140/180/220 ms' },
  { file: 'docs/05-design/DASHBOARD_COMPOSITION.md', formulation: 'zéro cadran décoratif' },
  {
    file: 'docs/05-design/DASHBOARD_COMPOSITION.md',
    formulation:
      'SVG/CSS interne seulement pour sparklines, micro-barres et jauges factuelles du catalogue ; aucune 3D, aucun WebGL décoratif, aucun globe, cadran ou particule.',
  },
  {
    file: 'manifests/widget-catalog.yaml',
    formulation: 'allowed_forms: ["linear_bullet", "segmented_band", "progress_with_target"]\n',
  },
];

/** Formes admises par ADR-017 : chacune doit être nommée dans la table de décision. */
const ADMITTED_FORMS = [
  'Anneau / donut à chiffre central',
  "Quatuor d'anneaux",
  'Jauge en arc à graduations',
  'Aire à dégradé sous une série',
  'Sparkline en aire',
  'Rail derrière les barres',
  'Matrice de bandes',
  'Liste groupée par jour',
  'Teinte sémantique secondaire par page',
] as const;

/** Interdits MAINTENUS par ADR-017 : lever une règle n'en efface aucune autre. */
const STILL_FORBIDDEN = [
  'halos ou néons permanents',
  'noir pur',
  'cartes translucides floues',
  'couleur seule sans texte',
  'compte à rebours',
  'horloge client',
  'radar ou nuage de points sans dimension multiple servie',
  'dégradé de fond plein sur une carte',
  'pulsation',
  'aiguille animée',
  'valeur abrégée côté client',
  'score composite opaque',
  'toute forme sur une valeur non servie',
] as const;

/**
 * Invariants que la v2 ne touche pas, à l'endroit exact où ils étaient écrits.
 * Si l'un disparaît, la porte échoue : la mise en cohérence n'est pas un
 * affaiblissement.
 */
const KEPT_INVARIANTS: ReadonlyArray<{ file: string; text: string }> = [
  { file: 'docs/05-design/DESIGN_SYSTEM.md', text: 'une couleur = une signification' },
  { file: 'docs/05-design/DESIGN_SYSTEM.md', text: 'jamais couleur seule : texte, icône ou motif' },
  { file: 'docs/05-design/DESIGN_SYSTEM.md', text: "le signal ambre n'exprime jamais une hausse, un score ou une validation" },
  { file: 'docs/05-design/CHART_STANDARD.md', text: 'Fraîcheur et couverture restent deux jauges indépendantes.' },
  { file: 'docs/05-design/WIDGET_LIBRARY.md', text: 'aucune jauge hors contrat factuel' },
  { file: 'docs/05-design/WIDGET_LIBRARY.md', text: 'Le navigateur ne calcule ni pourcentage, ni seuil, ni position du marqueur' },
  { file: 'docs/05-design/MOTION_AND_MICROINTERACTIONS.md', text: 'aucune pulsation' },
  { file: 'docs/05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md', text: 'ambre utilisé pour signifier une performance positive' },
  { file: '.claude/skills/vertex-titanium-ledger/references/canonical-visual.md', text: 'aucun halo néon permanent' },
  { file: '.claude/skills/vertex-titanium-ledger/references/canonical-visual.md', text: 'noir pur uniforme' },
  { file: '.claude/skills/vertex-titanium-ledger/references/charts.md', text: 'Réserver vert/rouge au signe financier.' },
  { file: '.claude/skills/vertex-titanium-ledger/references/visual-identity.md', text: 'jamais un halo lumineux permanent' },
  { file: 'manifests/widget-catalog.yaml', text: '"decorative_speedometer"' },
  { file: 'manifests/widget-catalog.yaml', text: '"animated_needle"' },
  { file: 'manifests/widget-catalog.yaml', text: '"opaque_composite_score"' },
];

describe('ADR-017 — Titanium Ledger v2', () => {
  it('existe, est Acceptée et porte les sections du modèle ADR-000', () => {
    expect(existsSync(join(REPO_ROOT, ADR_PATH))).toBe(true);
    const adr = read(ADR_PATH);
    expect(adr).toContain('# ADR-017 — Titanium Ledger v2');
    expect(adr).toContain('- Statut : Accepté');
    for (const heading of [
      '## Contexte',
      '## Décision',
      "### Formes admises et donnée servie qu'elles exigent",
      '### Formes toujours interdites',
      '## Conséquences',
      '## Options rejetées',
      "## Preuves d'application",
      '## Critères de réexamen',
    ]) {
      expect(adr, heading).toContain(heading);
    }
  });

  it('subordonne chaque forme admise à une donnée servie', () => {
    const adr = read(ADR_PATH);
    expect(adr).toContain("chaque grandeur qu'elle dessine est servie");
    for (const form of ADMITTED_FORMS) {
      expect(adr, form).toContain(`| ${form} |`);
    }
    // Le chiffre central d'un anneau est servi : jamais une somme calculée.
    expect(adr).toContain('jamais une somme calculée');
    // La position d'un arc vient du serveur : aucun pourcentage client.
    expect(adr).toContain('position en pourcentage servie');
  });

  it("écrit chaque interdit maintenu — lever une règle n'en efface aucune autre", () => {
    const adr = read(ADR_PATH);
    const forbiddenSection = adr.split('### Formes toujours interdites')[1]?.split('## Conséquences')[0];
    expect(forbiddenSection).toBeDefined();
    for (const item of STILL_FORBIDDEN) {
      expect(forbiddenSection, item).toContain(item);
    }
  });

  it("ne change pas l'empreinte de la capture canonique", () => {
    // La capture reste l'autorité de style ; l'ADR le dit et le script d'audit le mesure.
    expect(read(ADR_PATH)).toContain('inchangée par cette décision');
    expect(read('.claude/skills/vertex-titanium-ledger/references/canonical-visual.md')).toContain(
      'eb2eb0fc2105a98203e571381aec7765775d80aacec3513def10e99c9fdc7ace',
    );
  });
});

describe('documents du canon — cohérence v2', () => {
  it('chaque document du canon cite ADR-017', () => {
    const silent = CANON_DOCS.filter((file) => !read(file).includes('ADR-017'));
    expect(silent, `Documents sans citation d'ADR-017 : ${silent.join(', ')}`).toEqual([]);
  });

  it('aucune formulation levée ne revient', () => {
    const offenders: string[] = [];
    for (const { file, formulation } of LIFTED_FORMULATIONS) {
      if (flat(read(file)).includes(flat(formulation))) {
        offenders.push(`${file} → « ${formulation.trim()} »`);
      }
    }
    expect(offenders, `Formulations v1 revenues : ${offenders.join(' ; ')}`).toEqual([]);
  });

  it('les invariants non levés restent écrits là où ils étaient', () => {
    const missing: string[] = [];
    for (const { file, text } of KEPT_INVARIANTS) {
      if (!flat(read(file)).includes(flat(text))) {
        missing.push(`${file} → « ${text} »`);
      }
    }
    expect(missing, `Invariants disparus : ${missing.join(' ; ')}`).toEqual([]);
  });

  it('le catalogue normatif admet les formes v2 sous condition de donnée servie', () => {
    const catalog = read('manifests/widget-catalog.yaml');
    expect(catalog).toContain('"arc_graduated_served_position"');
    expect(catalog).toContain('v2_forms:');
    expect(catalog).toContain('"ring_center_value"');
    expect(catalog).toContain('"gradient_area_under_served_series"');
    expect(catalog).toContain('secondary_accent_per_page:');
    expect(catalog).toContain('families: ["macro", "option", "positive", "warning"]');
    expect(catalog).toContain('"any_form_on_unserved_value"');
  });
});
