// @vitest-environment node
/**
 * PORTE TYPOGRAPHIQUE — LOT V2.
 *
 * UN SEUL point, mais il vaut pour tout le produit : les chiffres alignent
 * leurs colonnes.
 *
 * CE QUI EST DÉJÀ VRAI, ET QUE RIEN NE PROTÉGEAIT. `global.css` pose
 * `font-variant-numeric: tabular-nums` sur `body`. La propriété s'HÉRITE : tout
 * nombre du produit a donc déjà des chiffres de largeur fixe, et les ~19
 * redéclarations qu'on trouve plus bas dans le même fichier ne font que répéter
 * cet héritage. Le lot V2 n'avait rien à ajouter — mais rien n'empêchait non
 * plus qu'une refonte de `body` l'emporte au passage, et personne ne l'aurait
 * vu : un tableau de prix dont les colonnes dansent ne casse aucun test, il
 * devient simplement plus difficile à lire, ce qui est pire.
 *
 * CE QUE CETTE PORTE NE MESURE PAS. Le rendu réel : elle lit la feuille de
 * style, pas le navigateur. Une règle plus spécifique qui remettrait
 * `normal` sur une carte lui échapperait. C'est l'e2e qui verrait cela ; ici on
 * tient la BASE, celle dont tout le reste hérite.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { fontFamily } from './tokens.ts';

const globalCss = readFileSync(fileURLToPath(new URL('../styles/global.css', import.meta.url)), 'utf8');

/** Le bloc `body { ... }` de premier niveau, celui dont tout le produit hérite. */
function blocBody(): string {
  const debut = globalCss.indexOf('\nbody {');
  if (debut === -1) {
    throw new Error('aucune règle `body` de premier niveau dans global.css');
  }
  const fin = globalCss.indexOf('\n}', debut);
  if (fin === -1) {
    throw new Error('règle `body` non refermée');
  }
  return globalCss.slice(debut, fin);
}

describe('Typographie — chiffres tabulaires', () => {
  it('la racine du produit impose les chiffres de largeur fixe', () => {
    // Un nombre se lit en colonne : dans une table de prix, une chaîne
    // d'options ou une série de variations, des chiffres de largeurs
    // différentes déplacent la virgule d'une ligne à l'autre.
    expect(
      blocBody(),
      '`body` ne pose plus `tabular-nums` : tous les nombres du produit perdent leur alignement',
    ).toContain('font-variant-numeric: tabular-nums');
  });

  it('aucune règle ne REVIENT aux chiffres proportionnels', () => {
    // L'héritage ne protège que de l'absence, pas de l'annulation. Une seule
    // règle `font-variant-numeric: normal` suffirait à défaire la base sur sa
    // sous-arborescence, sans qu'aucun autre test ne bronche.
    const annulations = globalCss
      .split('\n')
      .map((ligne, index) => ({ ligne: ligne.trim(), numero: index + 1 }))
      .filter(({ ligne }) => /^font-variant-numeric:\s*(normal|proportional-nums)/.test(ligne));
    expect(
      annulations.map(({ numero, ligne }) => `global.css:${numero} → ${ligne}`),
      'retour aux chiffres proportionnels',
    ).toEqual([]);
  });

  it('la pile monospace nomme une police, jamais le seul mot-clé générique', () => {
    // `monospace` seul laisse le navigateur choisir, et le choix diffère d'une
    // machine à l'autre : la largeur d'un ticker cesse d'être une constante du
    // produit. La pile doit donc commencer par une police NOMMÉE et ne garder
    // le générique qu'en dernier recours.
    expect(fontFamily.mono.startsWith("'Geist Mono'")).toBe(true);
    expect(fontFamily.mono.endsWith('monospace')).toBe(true);
    expect(fontFamily.sans.startsWith("'Geist'")).toBe(true);
  });
});
