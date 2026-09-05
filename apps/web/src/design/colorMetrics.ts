/**
 * MESURES DE COULEUR — une seule implémentation pour toutes les portes.
 *
 * POURQUOI CE MODULE. Trois fichiers de porte parsaient chacun leur couleur,
 * linéarisaient chacun leurs canaux et composaient chacun leur transparence.
 * Trois copies d'une même arithmétique, c'est trois occasions de diverger — et
 * une porte qui mesure faux est pire qu'une porte absente : elle rassure.
 *
 * DEUX MESURES, DEUX QUESTIONS. Elles ne sont pas interchangeables, et les
 * confondre a déjà produit un faux verdict pendant la refonte.
 *
 *   - `contraste` répond « ce texte est-il LISIBLE sur ce fond ? ». C'est un
 *     rapport de luminances, donc aveugle à la teinte : deux couleurs de même
 *     clarté et de teintes opposées valent 1,0 alors qu'elles se distinguent
 *     parfaitement. C'est la mesure de WCAG 1.4.3.
 *   - `deltaE` répond « ces deux aplats se DISTINGUENT-ils ? ». Il travaille en
 *     CIE Lab, où la distance approche la différence perçue, teinte comprise.
 *
 * Employer le contraste pour juger de la distinction pousse à écarter les
 * clartés là où il fallait écarter les teintes, et fabrique une palette
 * délavée. Employer ΔE pour juger de la lisibilité laisse passer un texte de
 * même clarté que son fond.
 */

/** Canaux 0-255 et opacité 0-1. */
export interface Canaux {
  readonly r: number;
  readonly v: number;
  readonly b: number;
  readonly a: number;
}

const HEX = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i;
const FONCTIONNELLE = /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+))?\s*\)$/i;

/**
 * Lit une couleur du système, hexadécimale ou fonctionnelle.
 *
 * Échoue BRUYAMMENT sur toute autre écriture : une porte qui accepterait
 * silencieusement une valeur qu'elle ne sait pas lire mesurerait du vide.
 */
export function analyser(valeur: string): Canaux {
  const brut = valeur.trim();
  const hex = HEX.exec(brut);
  if (hex !== null) {
    const [, r, v, b] = hex;
    if (r === undefined || v === undefined || b === undefined) {
      throw new Error(`hexadécimal incomplet : ${valeur}`);
    }
    return {
      r: Number.parseInt(r, 16),
      v: Number.parseInt(v, 16),
      b: Number.parseInt(b, 16),
      a: 1,
    };
  }
  const fonctionnelle = FONCTIONNELLE.exec(brut);
  if (fonctionnelle === null) {
    throw new Error(`couleur non analysable : ${valeur}`);
  }
  return {
    r: Number(fonctionnelle[1]),
    v: Number(fonctionnelle[2]),
    b: Number(fonctionnelle[3]),
    a: fonctionnelle[4] === undefined ? 1 : Number(fonctionnelle[4]),
  };
}

/** Composition « source-over » d'une couleur translucide sur un fond opaque. */
export function composer(dessus: Canaux, dessous: Canaux): Canaux {
  return {
    r: dessus.r * dessus.a + dessous.r * (1 - dessus.a),
    v: dessus.v * dessus.a + dessous.v * (1 - dessus.a),
    b: dessus.b * dessus.a + dessous.b * (1 - dessus.a),
    a: 1,
  };
}

function lineariser(canal: number): number {
  const s = canal / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

/** Luminance relative, WCAG 2.2 §dfn-relative-luminance. */
export function luminance({ r, v, b }: Canaux): number {
  return 0.2126 * lineariser(r) + 0.7152 * lineariser(v) + 0.0722 * lineariser(b);
}

/**
 * Ratio de contraste WCAG. `devant` peut être translucide : il est composé sur
 * `fond`, qui doit être opaque — un fond translucide n'a pas de couleur tant
 * qu'on ne sait pas ce qu'il y a dessous.
 */
export function contraste(devant: string | Canaux, fond: string | Canaux): number {
  const arriere = typeof fond === 'string' ? analyser(fond) : fond;
  if (arriere.a !== 1) {
    throw new Error('un fond doit être opaque pour mesurer un contraste');
  }
  const compose = composer(typeof devant === 'string' ? analyser(devant) : devant, arriere);
  const l1 = luminance(compose);
  const l2 = luminance(arriere);
  const [clair, sombre] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (clair + 0.05) / (sombre + 0.05);
}

/** sRGB → CIE Lab, blanc de référence D65, observateur 2°. */
function lab({ r, v, b }: Canaux): readonly [number, number, number] {
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

/**
 * ΔE 1976 entre deux couleurs OPAQUES.
 *
 * Une couleur translucide n'a pas de teinte propre : la composer sur son fond
 * est à la charge de l'appelant, parce que lui seul sait sur quoi elle est
 * posée.
 */
export function deltaE(a: string | Canaux, b: string | Canaux): number {
  const ca = typeof a === 'string' ? analyser(a) : a;
  const cb = typeof b === 'string' ? analyser(b) : b;
  if (ca.a !== 1 || cb.a !== 1) {
    throw new Error('ΔE exige deux couleurs opaques : composez-les d’abord sur leur fond');
  }
  const [l1, a1, b1] = lab(ca);
  const [l2, a2, b2] = lab(cb);
  return Math.hypot(l1 - l2, a1 - a2, b1 - b2);
}
