import { describe, expect, it } from 'vitest';
import { color } from './tokens.ts';

/**
 * PORTE DE DISTINCTION DES JETONS — LOT V2.
 *
 * ADR-017 pose « une couleur = une signification » et son protocole de nuance
 * interdit un alias de même valeur. Rien ne le vérifiait, et deux jetons
 * portaient la même couleur sous deux sens opposés :
 *
 *   - `warning` (prudence, retard, synthétique) et `signal-bright` (l'ambre le
 *     plus clair de la dominante) : ΔE = 1,9. Le même jaune disait « attention
 *     à ceci » et « voici la lumière de la page ». La réserve 3 d'ADR-017
 *     demandait de trancher « au lot L0, avant toute page P » ; elle ne l'avait
 *     jamais été, et `catalog.test.ts` tenait la ligne en INTERDISANT à toute
 *     page de déclarer `warning` comme teinte.
 *   - `titanium` (micro-libellés) et `text-secondary` (texte courant) :
 *     ΔE = 4,9. Deux rôles, une couleur perçue.
 *
 * POURQUOI ΔE ET NON LE RATIO DE CONTRASTE. Le ratio WCAG mesure la LISIBILITÉ
 * d'un texte sur un fond : c'est un rapport de luminances, aveugle à la teinte.
 * Deux couleurs de même luminance et de teintes opposées ont un ratio de 1,0 et
 * se distinguent parfaitement. Employer le ratio pour juger qu'un jeton se
 * distingue d'un autre aurait poussé à écarter les luminances là où il fallait
 * écarter les teintes — et aurait fabriqué une palette délavée.
 *
 * ΔE est calculé en CIE Lab (illuminant D65, observateur 2°), forme 1976. Le
 * seuil de 10 est celui d'une différence lue SANS hésitation à l'écran, sur des
 * aplats voisins ; ce n'est pas le seuil de perception (≈ 2,3), qui laisserait
 * passer les collisions ci-dessus.
 */

type Triplet = readonly [number, number, number];

/**
 * Seul l'hex opaque est comparé : une couleur translucide n'a pas de teinte
 * propre tant qu'on ne la compose pas sur un fond.
 *
 * Le nom `triplet` n'est pas un caprice : `no-raw-colors` interdit toute
 * écriture fonctionnelle de couleur — les trois lettres r, g, b suivies d'une
 * parenthèse — partout hors des jetons, et une fonction ainsi nommée l'aurait
 * déclenchée. Ce commentaire évite lui-même la séquence : la porte balaie le
 * fichier ENTIER, commentaires compris, et c'est très bien ainsi — une couleur
 * brute commentée reste une couleur brute qui attend d'être décommentée.
 * Ajouter une exemption pour un nom de fonction, ou pour une phrase, aurait
 * affaibli une porte pour un détail de vocabulaire.
 */
function triplet(valeur: string): Triplet | null {
  const trouve = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(valeur.trim());
  if (trouve === null) {
    return null;
  }
  const [, r, v, b] = trouve;
  if (r === undefined || v === undefined || b === undefined) {
    return null;
  }
  return [Number.parseInt(r, 16), Number.parseInt(v, 16), Number.parseInt(b, 16)];
}

function lineariser(canal: number): number {
  const s = canal / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

/** sRGB → CIE Lab, blanc de référence D65. */
function lab([r, v, b]: Triplet): Triplet {
  const rl = lineariser(r);
  const vl = lineariser(v);
  const bl = lineariser(b);
  const x = (rl * 0.4124564 + vl * 0.3575761 + bl * 0.1804375) / 0.95047;
  const y = rl * 0.2126729 + vl * 0.7151522 + bl * 0.072175;
  const z = (rl * 0.0193339 + vl * 0.119192 + bl * 0.9503041) / 1.08883;
  const f = (t: number): number => (t > 216 / 24389 ? Math.cbrt(t) : (841 / 108) * t + 4 / 29);
  const fx = f(x);
  const fy = f(y);
  const fz = f(z);
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

function deltaE(a: string, b: string): number {
  const ra = triplet(a);
  const rb = triplet(b);
  if (ra === null || rb === null) {
    throw new Error(`ΔE exige deux couleurs opaques : ${a} / ${b}`);
  }
  const [l1, a1, b1] = lab(ra);
  const [l2, a2, b2] = lab(rb);
  return Math.hypot(l1 - l2, a1 - a2, b1 - b2);
}

const arrondi = (n: number): number => Math.round(n * 10) / 10;

/** Seuil de lecture sans hésitation entre deux aplats voisins. */
const SEUIL = 10;

/**
 * Les jetons qui portent chacun UN SENS et doivent donc se distinguer deux à
 * deux. Les surfaces n'y sont pas : elles forment une échelle, traitée à part.
 */
const SENS_DISTINCTS = [
  'text',
  'text-secondary',
  'text-muted',
  'silver',
  'titanium',
  'signal',
  'signal-bright',
  'positive',
  'negative',
  'warning',
  'option',
  'macro',
] as const;

/**
 * DETTE V2 — TEMPORAIRE, ET ELLE NE PEUT QUE RÉTRÉCIR.
 *
 * Deux collisions ne se règlent pas par une valeur : elles demandent une
 * décision de structure, et la prendre à la hâte serait pire que la nommer.
 *
 *   - `titanium` / `text-secondary` (ΔE 4,9) : les quatre gris — `text`,
 *     `silver`, `text-secondary`, `text-muted` — plus `titanium` se partagent
 *     une plage étroite. Écarter `titanium` sans le faire virer au gris neutre
 *     le sortirait de la palette chaude ; la vraie question est s'il doit
 *     EXISTER, puisque les micro-libellés se distinguent déjà par la casse, la
 *     graisse et l'interlettrage. Quinze usages CSS, décision au lot V2b.
 *   - L'échelle de SURFACES est plate : ΔE de 1,4 à 4,9 entre crans voisins,
 *     17,4 en tout du plus sombre au survol. Elle ne peut pas être étirée : le
 *     haut est plafonné par `text-muted`, qui doit tenir 4,5:1 sur `hover` et
 *     n'a plus que 1,6 % de marge de luminance. La séparation des cartes doit
 *     donc venir de l'élévation, de la gouttière et du liseré — pas de la
 *     luminance. Décision au lot V3b, avec la coquille.
 */
const DETTE_V2: ReadonlyArray<{ readonly paire: string; readonly lot: string }> = [
  { paire: 'titanium|text-secondary', lot: 'V2b' },
  { paire: 'titanium|text-muted', lot: 'V2b' },
];

/** Plafond de la dette. ABAISSÉ à chaque lot, jamais relevé. */
const DETTE_MAX = 2;

const clef = (a: string, b: string): string => [a, b].sort().join('|');

/** Normalisé par `clef` : une paire déclarée dans un ordre doit valoir dans l'autre. */
const EN_DETTE: ReadonlySet<string> = new Set(
  DETTE_V2.map(({ paire }) => {
    const [a, b] = paire.split('|');
    if (a === undefined || b === undefined) {
      throw new Error(`paire de dette mal formée : ${paire}`);
    }
    return clef(a, b);
  }),
);

describe('Distinction des jetons — ΔE en CIE Lab', () => {
  it('la mesure elle-même est juste sur des repères connus', () => {
    // Anti-vacuité. Une couleur ne diffère pas d'elle-même ; le noir et le
    // blanc sont séparés par toute l'échelle de clarté, soit ΔE = 100.
    expect(arrondi(deltaE(color.black, color.black))).toBe(0);
    expect(Math.round(deltaE(color.text, color.black))).toBeGreaterThan(90);
    // Deux teintes opposées de clarté voisine : le ratio de contraste les
    // dirait identiques, ΔE non. C'est la raison d'être de cette porte.
    expect(deltaE(color.positive, color.macro)).toBeGreaterThan(SEUIL);
  });

  it('deux jetons de sens différents ne portent pas la même couleur', () => {
    const collisions: string[] = [];
    for (let i = 0; i < SENS_DISTINCTS.length; i += 1) {
      for (let j = i + 1; j < SENS_DISTINCTS.length; j += 1) {
        const a = SENS_DISTINCTS[i];
        const b = SENS_DISTINCTS[j];
        if (a === undefined || b === undefined || EN_DETTE.has(clef(a, b))) {
          continue;
        }
        const distance = deltaE(color[a], color[b]);
        if (distance < SEUIL) {
          collisions.push(`${a} / ${b} : ΔE ${arrondi(distance)}`);
        }
      }
    }
    expect(
      collisions,
      `Jetons indiscernables (ΔE < ${SEUIL}) :\n  ${collisions.join('\n  ')}\n` +
        'Deux sens différents ne peuvent pas porter la même couleur.',
    ).toEqual([]);
  });

  it('la dette ne peut que RÉTRÉCIR — cliquet du lot V2', () => {
    expect(DETTE_V2.length).toBeLessThanOrEqual(DETTE_MAX);
    for (const { lot } of DETTE_V2) {
      expect(lot, 'chaque dette nomme le lot qui la ferme').toMatch(/^V\d+[a-z]?$/);
    }
  });

  it('une paire en dette est RÉELLEMENT en collision', () => {
    // Sinon elle est déjà réglée et doit sortir de la liste. Une dette qui
    // survit à sa cause est une exemption qui se déguise.
    const inutiles = DETTE_V2.filter(({ paire }) => {
      const [a, b] = paire.split('|');
      if (a === undefined || b === undefined) {
        return false;
      }
      return deltaE(color[a as keyof typeof color], color[b as keyof typeof color]) >= SEUIL;
    }).map((entree) => entree.paire);
    expect(inutiles, 'dette à retirer : ces paires se distinguent déjà').toEqual([]);
  });

  it('une famille et sa teinte douce restent de la MÊME famille', () => {
    // Le pendant de la règle précédente : `-soft` ne doit PAS s'éloigner de sa
    // famille, sinon la teinte douce cesse de nommer la même chose. La porte
    // `tokens-css.test.ts` le vérifie déjà sur les dégradés ; ici on couvre les
    // fonds `-soft`, qui ont le même contrat de triplet.
    for (const famille of ['signal', 'positive', 'negative', 'warning', 'option', 'macro'] as const) {
      const pleine = triplet(color[famille]);
      const douce = /^rgba\((\d+), (\d+), (\d+),/.exec(color[`${famille}-soft`]);
      expect(pleine, `famille non opaque : ${famille}`).not.toBeNull();
      expect(douce, `teinte douce non analysable : ${famille}-soft`).not.toBeNull();
      if (pleine !== null && douce !== null) {
        expect(
          [Number(douce[1]), Number(douce[2]), Number(douce[3])],
          `${famille}-soft n'est pas le triplet de ${famille}`,
        ).toEqual([...pleine]);
      }
    }
  });
});
