// @vitest-environment node
/**
 * PORTE — UN CHAMP DE VÉRITÉ SERVI DOIT ÊTRE LU.
 *
 * CE QU'ELLE ATTRAPE. `freshness_policy` traversait DOUZE routes, arrivait
 * jusqu'au client TypeScript généré… et n'était lu par AUCUN fichier
 * d'interface. Le contrat serveur avait pourtant écrit son intention mot pour
 * mot : « le client pose `age_seconds` sur cette échelle et n'invente ni TTL
 * ni ratio ; publier le budget évite un second registre recopié côté
 * interface ». La moitié cliente n'avait jamais été écrite.
 *
 * La conséquence n'était pas cosmétique. Un âge sans son échelle ne dit rien :
 * trois jours sur une barre quotidienne de séance fermée, c'est normal ; trois
 * jours sur une cotation, c'est une donnée morte. Le lecteur voyait « il y a
 * 3 j » sans savoir de quoi c'était l'âge.
 *
 * POURQUOI UNE LISTE NOMMÉE, ET PAS TOUS LES CHAMPS. Beaucoup de champs servis
 * n'ont légitimement pas de rendu (identifiants de corrélation, hashes de
 * lignée lus par l'inspecteur seul). La porte ne prétend pas les arbitrer :
 * elle garde une liste EXPLICITE de champs dont l'absence à l'écran fait
 * MENTIR ce qui est affiché. Un champ n'entre dans cette liste que sur constat.
 *
 * CE QU'ELLE NE PROUVE PAS. Qu'un champ lu est bien AFFICHÉ, ni qu'il l'est
 * correctement — ce sont les tests de composant et la relecture des captures
 * qui le disent. Elle prouve seulement que la moitié cliente du contrat existe.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SRC = fileURLToPath(new URL('..', import.meta.url));

/**
 * Champs dont l'absence à l'écran fait mentir ce qui est affiché, avec la
 * raison qui les a fait entrer ici.
 */
const CHAMPS: readonly (readonly [string, string])[] = [
  [
    'freshness_policy',
    "l'échelle qui juge `age_seconds` : sans elle, un âge ne dit pas de quoi il est l'âge",
  ],
];

/**
 * DEUX DOSSIERS SONT EXCLUS, ET LE SECOND A ÉTÉ TROUVÉ EN PROUVANT LA PORTE.
 *
 * `api/` d'abord : le client généré et les types nomment chaque champ du
 * contrat par construction. Les compter rendrait la porte toujours verte.
 *
 * `test/` ensuite. Écrite sans lui, la porte restait VERTE alors que le
 * câblage venait d'être retiré — parce que `test/fixtures.ts` POSE
 * `freshness_policy` pour satisfaire le type de la réponse. Poser un champ
 * n'est pas le lire : une fixture qui le remplit et une interface qui l'ignore
 * est exactement l'état que cette porte doit interdire. Sans cette exclusion,
 * elle aurait été verte pour toujours, sur rien.
 */
const HORS_INTERFACE = ['api', 'test'];

function fichiersInterface(dossier: string, acc: string[]): string[] {
  for (const entree of readdirSync(dossier)) {
    const complet = join(dossier, entree);
    const chemin = relative(SRC, complet).replaceAll('\\', '/');
    if (HORS_INTERFACE.some((exclu) => chemin === exclu || chemin.startsWith(`${exclu}/`))) {
      continue;
    }
    if (statSync(complet).isDirectory()) {
      fichiersInterface(complet, acc);
    } else if (/\.tsx?$/.test(complet) && !/\.test\.tsx?$/.test(complet)) {
      acc.push(complet);
    }
  }
  return acc;
}

describe('Les champs de vérité servis sont lus par l’interface', () => {
  const sources = fichiersInterface(SRC, []).map((chemin) => ({
    chemin: relative(SRC, chemin).replaceAll('\\', '/'),
    contenu: readFileSync(chemin, 'utf8'),
  }));

  it('lit un corpus non vide — sinon la porte serait vide de sens', () => {
    expect(sources.length).toBeGreaterThan(100);
  });

  it.each(CHAMPS)('« %s » a au moins un lecteur — %s', (champ) => {
    const lecteurs = sources
      .filter(({ contenu }) => {
        // Un COMMENTAIRE qui nomme le champ n'est pas un lecteur : c'est très
        // exactement ainsi que le défaut se cachait — `LiveDataIndicator`
        // documentait `freshness_policy` sans jamais la recevoir.
        const sansCommentaires = contenu
          .replaceAll(/\/\*[\s\S]*?\*\//g, '')
          .replaceAll(/^\s*\/\/.*$/gm, '');
        return sansCommentaires.includes(champ);
      })
      .map(({ chemin }) => chemin);
    expect(lecteurs).not.toEqual([]);
  });
});
