// @vitest-environment node
/**
 * PORTE DOCUMENTAIRE DES JETONS — LOT V2.
 *
 * `docs/05-design/TOKENS.md` est le document que lit un humain avant d'écrire
 * une règle CSS. Au lot V2 il annonçait encore, pour les ESPACES, deux crans
 * `40` et `48` retirés au lot V1 ; pour les RAYONS, des clés `18` et `22` qui
 * n'existent plus et dont on avait justement prouvé qu'elles mentaient sur
 * leur valeur ; une ombre « flottant » supprimée ; une taille de texte
 * `mono-number` qui n'a JAMAIS existé dans la source ; un alias `label` ; et il
 * taisait `headline` et `metric`, deux tailles bien réelles.
 *
 * POURQUOI CELA COMPTE PLUS QU'UNE COQUILLE. `tokens-css.test.ts` prouve que le
 * CSS généré correspond à la source typée. Rien ne reliait la source au
 * DOCUMENT. Le lot V1 a donc pu retirer trois jetons, en écrire la raison dans
 * le code, et laisser le document affirmer le contraire pendant tout ce temps.
 * Un développeur qui lisait la documentation écrivait `var(--vx-space-40)` — une
 * variable qui n'existe plus, donc une déclaration silencieusement invalide.
 *
 * CE QUE CETTE PORTE NE FAIT PAS. Elle ne relit pas la prose : elle vérifie les
 * ÉNUMÉRATIONS, là où le document prétend lister ce que la source contient. Le
 * reste du document est du jugement, et un test n'a rien à en dire.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { fontSize, radius, shadow, space } from './tokens.ts';

const doc = readFileSync(
  fileURLToPath(new URL('../../../../docs/05-design/TOKENS.md', import.meta.url)),
  'utf8',
);

/** La ligne de puce qui commence par ce libellé, sans le libellé. */
function puce(libelle: string): string {
  const trouve = new RegExp(`^- ${libelle} : ([\\s\\S]*?)(?=\\n- |\\n\\n)`, 'm').exec(doc);
  if (trouve === null || trouve[1] === undefined) {
    throw new Error(`TOKENS.md ne décrit plus « ${libelle} »`);
  }
  return trouve[1];
}

describe('TOKENS.md décrit la source typée, et rien d’autre', () => {
  /**
   * La suite `n/n/n` la plus longue de la ligne, DÉCOUPÉE en crans.
   *
   * `toContain` ne suffit pas ici, et c'est une leçon payée en écrivant cette
   * porte : le document périmé annonçait `4/8/12/16/20/24/32/40/48`, qui
   * CONTIENT la suite correcte `4/8/12/16/20/24/32`. Un sur-ensemble satisfait
   * l'inclusion — donc la première version de ce test passait au vert sur le
   * document faux. Une énumération se compare par ÉGALITÉ, jamais par
   * inclusion : sinon un document peut annoncer des jetons morts sans jamais
   * échouer.
   */
  function crans(ligne: string): number[] {
    const suite = /\d+(?:\/\d+)+/.exec(ligne);
    if (suite === null) {
      throw new Error(`aucune énumération numérique dans « ${ligne} »`);
    }
    return suite[0].split('/').map(Number);
  }

  it('énumère exactement les espaces qui existent', () => {
    expect(crans(puce('espace'))).toEqual(Object.keys(space).map(Number));
  });

  it('énumère exactement les rayons qui existent', () => {
    const numeriques = Object.keys(radius).filter((cle) => /^\d+$/.test(cle));
    expect(crans(puce('rayon'))).toEqual(numeriques.map(Number));
    // `pill` est un rôle, pas un cran d'échelle : le document doit le nommer
    // pour qu'on ne le confonde pas avec un rayon ordinaire.
    expect(puce('rayon')).toContain('pill');
  });

  it('nomme les ombres par leur clé réelle, aucune de plus', () => {
    for (const cle of Object.keys(shadow)) {
      expect(puce('ombre'), `ombre non documentée : ${cle}`).toContain(`\`${cle}\``);
    }
    // Anti-fantôme : une ombre citée par le document et absente de la source
    // enverrait un développeur écrire une variable qui n'existe pas.
    for (const fantome of ['floating', 'flottant']) {
      expect(puce('ombre'), `ombre fantôme documentée : ${fantome}`).not.toContain(fantome);
    }
  });

  it('énumère exactement les tailles de texte qui existent', () => {
    const ligne = puce('typographie');
    for (const cle of Object.keys(fontSize)) {
      expect(ligne, `taille non documentée : ${cle}`).toContain(`\`${cle}\``);
    }
    // Le document ne peut pas inventer une taille : on relit ce qu'il cite
    // entre accents graves et on exige que la source la connaisse.
    for (const cite of ligne.matchAll(/`([a-z-]+)`/g)) {
      expect(Object.keys(fontSize), `taille documentée inexistante : ${cite[1]}`).toContain(cite[1]);
    }
  });
});
