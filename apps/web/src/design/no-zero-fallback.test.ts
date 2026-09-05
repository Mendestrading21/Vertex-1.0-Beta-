// @vitest-environment node
/**
 * PORTE — UNE VALEUR ILLISIBLE NE DEVIENT JAMAIS ZÉRO.
 *
 * CE QU'ELLE ATTRAPE. Quatre copies d'un même utilitaire de géométrie
 * convertissaient une chaîne servie en nombre et rendaient `0` dès que la
 * conversion échouait. L'intention était d'empêcher un `NaN` d'atteindre le
 * rendu ; la conséquence était pire que le mal évité :
 *
 *   - une clôture illisible devenait une clôture À ZÉRO, et la courbe
 *     plongeait sur l'axe — un effondrement de cours qui n'a pas eu lieu ;
 *   - une bougie OHLC illisible tombait sur l'axe des prix ;
 *   - un P&L illisible se posait à l'origine du repère, où il se lisait comme
 *     un point mort ;
 *   - un strike illisible se rangeait sous tous les autres, comme s'il valait
 *     le plus bas de l'échelle.
 *
 * `.claude/rules/frontend.md` l'interdit nommément : « ne jamais remplacer une
 * donnée absente par 0 ». Le module `components/widgets/geometry.ts` avait
 * même NOMMÉ ce piège dans son en-tête et écrit le remède — mais les copies ne
 * l'avaient jamais adopté. Cette porte empêche la prochaine copie.
 *
 * CE QU'ELLE N'INTERDIT PAS. Un zéro SERVI reste un zéro : c'est une
 * observation. La porte ne vise que le repli d'une conversion RATÉE.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SRC = fileURLToPath(new URL('..', import.meta.url));

function fichiers(dossier: string, acc: string[]): string[] {
  for (const entree of readdirSync(dossier)) {
    const complet = join(dossier, entree);
    if (statSync(complet).isDirectory()) {
      fichiers(complet, acc);
    } else if (/\.tsx?$/.test(complet) && !/\.test\.tsx?$/.test(complet)) {
      acc.push(complet);
    }
  }
  return acc;
}

/**
 * Le repli fautif, dans ses deux écritures courantes.
 *
 * `Number.isFinite(x) ? x : 0` et `Number.isNaN(x) ? 0 : x` disent la même
 * chose : « si je n'ai pas su lire, je poserai zéro ».
 */
const REPLIS = [
  /Number\.isFinite\([^)]*\)\s*\?[^:]*:\s*0\b/,
  /Number\.isNaN\([^)]*\)\s*\?\s*0\b/,
  /\?\?\s*0\s*\)?\s*;?\s*\/\/\s*g[ée]om/i,
];

describe('Aucune conversion ne se replie sur zéro', () => {
  const sources = fichiers(SRC, []);

  it('lit un corpus non vide — sinon la porte serait vide de sens', () => {
    expect(sources.length).toBeGreaterThan(100);
  });

  it('ne trouve aucun repli à zéro sur une conversion ratée', () => {
    const fautes: string[] = [];
    for (const fichier of sources) {
      const contenu = readFileSync(fichier, 'utf8');
      for (const ligne of contenu.split('\n')) {
        // Les commentaires expliquent le défaut ; ils ne le contiennent pas.
        const nue = ligne.trim();
        if (nue.startsWith('*') || nue.startsWith('//')) {
          continue;
        }
        for (const motif of REPLIS) {
          if (motif.test(ligne)) {
            fautes.push(`${relative(SRC, fichier)} : ${nue.slice(0, 90)}`);
          }
        }
      }
    }
    expect(
      fautes,
      `Une conversion ratée doit rendre \`null\`, jamais 0 :\n  ${fautes.join('\n  ')}`,
    ).toEqual([]);
  });
});
