// @vitest-environment node
/**
 * PORTE — UNE SEULE RÈGLE DE SIGNE, UN SEUL VOCABULAIRE.
 *
 * CE QU'ELLE ATTRAPE. Cinq règles de signe coexistaient, et trois divergeaient
 * de la bonne :
 *
 *   - `startsWith('-') ? 'negative' : 'positive'` (table et inspecteur de
 *     Portefeuille) — BINAIRE, sans état neutre : un P&L latent servi `0.00`
 *     était peint EN VERT ;
 *   - `startsWith('-') ? 'down' : 'flat'` (drawdown de Risques) — même faute
 *     sur `-0.00` ;
 *   - `signOf` (Portefeuille et Simulateur, deux copies) — testait le tiret
 *     AVANT le zéro, donc `-0.00` valait « perte », et rendait `up` sur une
 *     chaîne positive NON signée, inventant un gain là où le signe n'était pas
 *     publié.
 *
 * Le signe n'est pas une décoration : peindre un chiffre en vert AFFIRME un
 * gain. L'affirmer d'un zéro servi fabrique une donnée financière, ce que
 * `.claude/rules/frontend.md` et `financial-safety.md` interdisent l'un et
 * l'autre.
 *
 * DEUX INTERDITS, PARCE QUE LA FAUTE AVAIT DEUX FACES. La règle elle-même
 * (première assertion) ; et le VOCABULAIRE (seconde), car
 * `positive`/`negative` était un dialecte que ne parlait aucune feuille de
 * style partagée — l'inspecteur de lot posait ainsi un `data-sign` que RIEN ne
 * coloriait, et la faute passait inaperçue.
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

/** L'autorité, seule autorisée à lire un signe dans une chaîne. */
const AUTORITE = 'components/widgets/sign.ts';

/**
 * Le vocabulaire canonique du produit. `unknown` nomme un signe NON publié ;
 * il n'est jamais une direction.
 */
const VOCABULAIRE = new Set(['up', 'down', 'flat', 'unknown']);

describe('Une seule règle de signe', () => {
  const sources = fichiers(SRC, []);

  it('lit un corpus non vide — sinon la porte serait vide de sens', () => {
    expect(sources.length).toBeGreaterThan(100);
  });

  it("seule l'autorité lit un signe dans une chaîne", () => {
    const fautes: string[] = [];
    for (const source of sources) {
      const chemin = relative(SRC, source).replaceAll('\\', '/');
      if (chemin === AUTORITE) {
        continue;
      }
      readFileSync(source, 'utf8')
        .split('\n')
        .forEach((ligne, index) => {
          if (/^\s*(?:\*|\/\/)/.test(ligne)) {
            return;
          }
          if (/\.startsWith\(\s*['"][+-]['"]\s*\)/.test(ligne)) {
            fautes.push(`${chemin}:${index + 1} — signe lu hors de ${AUTORITE}`);
          }
        });
    }
    expect(fautes).toEqual([]);
  });

  it('aucun `data-sign` littéral hors du vocabulaire canonique', () => {
    const fautes: string[] = [];
    for (const source of sources) {
      const chemin = relative(SRC, source).replaceAll('\\', '/');
      const contenu = readFileSync(source, 'utf8');
      for (const trouve of contenu.matchAll(/'data-sign':\s*'([^']+)'/g)) {
        const valeur = trouve[1];
        if (valeur !== undefined && !VOCABULAIRE.has(valeur)) {
          fautes.push(`${chemin} — « ${valeur} »`);
        }
      }
      for (const trouve of contenu.matchAll(/data-sign=(?:"([^"{]+)"|\{'([^']+)'\})/g)) {
        const valeur = trouve[1] ?? trouve[2];
        if (valeur !== undefined && !VOCABULAIRE.has(valeur)) {
          fautes.push(`${chemin} — « ${valeur} »`);
        }
      }
    }
    expect(fautes).toEqual([]);
  });

  it("aucune feuille de style ne cible un `data-sign` hors vocabulaire", () => {
    const styles = ['styles/global.css', 'styles/widgets.css', 'design/tokens.css'];
    const fautes: string[] = [];
    for (const feuille of styles) {
      /*
        LES COMMENTAIRES SONT RETIRÉS AVANT LA LECTURE. Sans cela la porte
        s'accusait elle-même : le commentaire qui EXPLIQUE l'ancien dialecte
        contient les mots `data-sign='positive'`. Une porte qui lit de la prose
        ne lit pas des règles — et symétriquement, une règle cachée dans un
        commentaire n'est pas une règle.
      */
      const contenu = readFileSync(join(SRC, feuille), 'utf8').replaceAll(
        /\/\*[\s\S]*?\*\//g,
        '',
      );
      for (const trouve of contenu.matchAll(/data-sign=['"]([^'"]+)['"]/g)) {
        const valeur = trouve[1];
        if (valeur !== undefined && !VOCABULAIRE.has(valeur)) {
          fautes.push(`${feuille} — « ${valeur} »`);
        }
      }
    }
    expect(fautes).toEqual([]);
  });
});
