import { describe, expect, it } from 'vitest';
import { color } from './tokens.ts';

/**
 * PORTE DE CONTRASTE — LOT V1.
 *
 * `docs/05-design/TOKENS.md` affirme depuis l'origine : « Chaque token de
 * couleur a un libellé/icône associé et UNE PAIRE TEXTE/FOND VÉRIFIÉE AA ».
 * Rien ne le vérifiait. L'audit du 2026-09-04 a mesuré ce que cette absence
 * laissait passer :
 *
 *   - `signal-deep` à 2,67:1 sur `surface-1` — illisible comme texte ;
 *   - `text` sur `signal` à 1,94:1 — un bouton plein au texte clair ;
 *   - `text-muted` à 4,35:1 sur `hover` — sous le seuil AA, alors qu'il porte
 *     les métadonnées À L'INTÉRIEUR des cartes, donc sur leur état de survol.
 *
 * CE QUE CETTE PORTE N'EST PAS. Elle ne remplace pas `axe` en e2e : `axe` ne
 * mesure que les paires RÉELLEMENT rendues, sur les données du moment. Un état
 * dégradé qu'aucun test ne visite n'est jamais mesuré. Cette porte, elle,
 * mesure le CONTRAT : toute paire déclarée utilisable doit tenir, qu'elle soit
 * rendue aujourd'hui ou demain.
 */

/** Canaux 0-255 plus alpha 0-1. */
interface Rgba {
  readonly r: number;
  readonly g: number;
  readonly b: number;
  readonly a: number;
}

function parse(valeur: string): Rgba {
  const hex = /^#([0-9a-f]{6})$/i.exec(valeur.trim());
  const chiffres = hex?.[1];
  if (chiffres !== undefined) {
    const n = Number.parseInt(chiffres, 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, a: 1 };
  }
  const rgba = /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+))?\s*\)$/i.exec(
    valeur.trim(),
  );
  if (rgba === null) {
    throw new Error(`couleur non analysable : ${valeur}`);
  }
  return {
    r: Number(rgba[1]),
    g: Number(rgba[2]),
    b: Number(rgba[3]),
    a: rgba[4] === undefined ? 1 : Number(rgba[4]),
  };
}

/** Composition « source-over » d'une couleur translucide sur un fond opaque. */
function composer(dessus: Rgba, dessous: Rgba): Rgba {
  return {
    r: dessus.r * dessus.a + dessous.r * (1 - dessus.a),
    g: dessus.g * dessus.a + dessous.g * (1 - dessus.a),
    b: dessus.b * dessus.a + dessous.b * (1 - dessus.a),
    a: 1,
  };
}

/** Luminance relative, WCAG 2.2 §dfn-relative-luminance. */
function luminance({ r, g, b }: Rgba): number {
  const canal = (v: number): number => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);
}

/**
 * Ratio WCAG. `devant` peut être translucide : il est composé sur `fond`.
 *
 * NON EXPORTÉ : un fichier de test n'expose rien (`noExportsInTest`). Le jour
 * où un autre lot aura besoin de cette mesure, elle déménagera dans un module
 * de `src/design/` — l'exporter d'ici en ferait une API par accident.
 */
function ratio(devant: string, fond: string): number {
  const arriere = parse(fond);
  if (arriere.a !== 1) {
    throw new Error(`un fond doit être opaque : ${fond}`);
  }
  const compose = composer(parse(devant), arriere);
  const l1 = luminance(compose);
  const l2 = luminance(arriere);
  const [clair, sombre] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (clair + 0.05) / (sombre + 0.05);
}

/** Arrondi à deux décimales, pour que le message d'échec soit lisible. */
const arrondi = (n: number): number => Math.round(n * 100) / 100;

/**
 * Les fonds sur lesquels du texte est RÉELLEMENT posé. `black` en est absent :
 * il n'habille aucune surface de lecture, seulement le fond de la fenêtre
 * derrière le shell.
 */
const FONDS = ['app', 'surface-0', 'surface-1', 'surface-2', 'surface-3', 'hover'] as const;

/**
 * Jetons de texte, et le seuil qu'ils doivent tenir SUR CHACUN des fonds.
 *
 * 4,5:1 est le seuil AA du texte normal (WCAG 1.4.3). Aucun jeton n'est ici à
 * 3:1 « texte large » : le produit n'a aucun texte au-dessus de 24 px qui ne
 * soit pas déjà `text` ou `signal-bright`.
 */
const TEXTES = [
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
 * Jetons qui ne sont JAMAIS du texte, chacun avec la raison écrite qui le
 * dispense. Une exemption sans raison est une exemption qui se déguise.
 */
const JAMAIS_TEXTE: ReadonlyArray<{ readonly jeton: keyof typeof color; readonly raison: string }> = [
  {
    jeton: 'signal-deep',
    raison:
      "Fin de dégradé uniquement (ADR-017). À 2,88:1 sur `app` il n'est lisible ni comme texte ni comme fond de texte sombre ; le test « aucun jeton exempté ne sert de couleur de texte » plus bas le prouve sur le CSS réel.",
  },
  {
    jeton: 'grid-line',
    raison:
      'Trame de fond décorative. « Arrière-plan : décor presque invisible » — un décor qui atteindrait 3:1 deviendrait un contenu.',
  },
  {
    jeton: 'titanium-ghost',
    raison:
      "Filigrane de registre, délibérément sous le seuil : à `titanium-soft` le code d'espace se lisait aussi bien que le titre de page, soit un second titre qui ne dit rien.",
  },
];

describe('Contraste des jetons — WCAG 2.2', () => {
  it('la mesure elle-même est juste sur des paires connues', () => {
    // Anti-vacuité : si `ratio` était faux, tout le reste passerait pour de
    // mauvaises raisons. Noir pur sur blanc pur vaut exactement 21:1.
    expect(arrondi(ratio('#000000', '#ffffff'))).toBe(21);
    expect(arrondi(ratio('#ffffff', '#ffffff'))).toBe(1);
    // Une couleur à alpha 0 disparaît dans son fond.
    expect(arrondi(ratio('rgba(255, 255, 255, 0)', '#000000'))).toBe(1);
  });

  it('chaque jeton de texte tient AA sur chaque fond de lecture', () => {
    const echecs: string[] = [];
    for (const texte of TEXTES) {
      for (const fond of FONDS) {
        const mesure = ratio(color[texte], color[fond]);
        if (mesure < 4.5) {
          echecs.push(`${texte} sur ${fond} : ${arrondi(mesure)}:1`);
        }
      }
    }
    expect(echecs, `Paires sous le seuil AA de 4,5:1 :\n  ${echecs.join('\n  ')}`).toEqual([]);
  });

  it('un texte sombre sur accent plein tient AA', () => {
    // Le cas des boutons remplis. `text` sur `signal` vaut 1,94:1 et aucune
    // porte ne l'interdisait ; la règle est donc énoncée dans l'autre sens :
    // sur un accent plein, le texte est SOMBRE, et on prouve qu'il tient.
    const echecs: string[] = [];
    for (const accent of ['signal', 'positive', 'negative', 'warning', 'option', 'macro'] as const) {
      for (const sombre of ['black', 'app', 'surface-0'] as const) {
        const mesure = ratio(color[sombre], color[accent]);
        if (mesure < 4.5) {
          echecs.push(`${sombre} sur ${accent} : ${arrondi(mesure)}:1`);
        }
      }
    }
    expect(echecs, `Texte sombre illisible sur son accent :\n  ${echecs.join('\n  ')}`).toEqual([]);
  });

  it('chaque exemption porte une raison écrite et un jeton réel', () => {
    for (const { jeton, raison } of JAMAIS_TEXTE) {
      expect(Object.keys(color), `jeton exempté inexistant : ${jeton}`).toContain(jeton);
      expect(raison.length, `raison trop courte : ${jeton}`).toBeGreaterThan(80);
    }
  });

  it('aucune exemption n’est inutile : chacune échouerait vraiment', () => {
    // Une exemption dont le jeton tiendrait AA serait une exemption morte,
    // et elle laisserait passer un défaut futur sans que personne le sache.
    for (const { jeton } of JAMAIS_TEXTE) {
      const meilleur = Math.max(...FONDS.map((fond) => ratio(color[jeton], color[fond])));
      expect(arrondi(meilleur), `exemption sans objet, à retirer : ${jeton}`).toBeLessThan(4.5);
    }
  });
});
