// @vitest-environment node
/**
 * PORTE — AUCUNE MISE EN FORME NE DÉLÈGUE SA LANGUE AU NAVIGATEUR.
 *
 * CE QU'ELLE ATTRAPE. Vertex est un produit ENTIÈREMENT FRANÇAIS : `index.html`
 * déclare `lang="fr"` et chaque libellé est écrit en français. Mais `lang` ne
 * gouverne PAS le formatage des dates et des nombres en JavaScript. Un
 * `toLocaleString()` sans argument, un `Intl.DateTimeFormat()` sans locale,
 * lisent la locale du NAVIGATEUR : sur un poste configuré en anglais, la même
 * page rend `9/5/2026, 2:30:00 PM` là où elle devait rendre `05/09/2026 14:30`.
 *
 * Ce n'est pas une coquetterie de présentation. Une date financière ambiguë
 * ment : `05/09/2026` et `09/05/2026` désignent deux jours différents, et rien
 * à l'écran ne dit lequel a été rendu. Une échéance d'option, une date de
 * résultats, un instant de fraîcheur lus à l'envers, c'est une décision prise
 * sur un fait faux — exactement ce que `.claude/rules/financial-safety.md`
 * interdit quand il exige que « unité, devise, multiplicateur, convention de
 * signe et timezone » soient explicites aux frontières.
 *
 * COMMENT LE DÉFAUT A ÉTÉ VU. Pas par un test : par une CAPTURE. Le champ
 * `<input type="datetime-local">` de Catalyseurs affichait `mm/dd/yyyy,
 * --:-- --` dans une page française. L'enquête a innocenté le produit — ses
 * deux seuls formateurs épinglent déjà `fr-CH` et `fr-CA` — et accusé
 * l'environnement de capture, dont Chromium démarrait en `en-US`. Le remède
 * tient en une ligne de `playwright.config.ts` (`locale: 'fr-FR'`). Cette
 * porte garde l'autre moitié : que le PRODUIT, lui, n'acquière jamais cette
 * dépendance.
 *
 * CE QU'ELLE N'INTERDIT PAS. Lire la locale ou le fuseau du lecteur pour les
 * NOMMER reste légitime — `resolveViewerTimeZone()` le fait, et la colonne
 * qu'il alimente porte le nom du fuseau appliqué. Ce qui est interdit, c'est
 * de FORMATER sans dire dans quelle langue.
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
 * Les quatre écritures qui délèguent la langue au navigateur.
 *
 * `toLocaleString()`, `toLocaleDateString()`, `toLocaleTimeString()` sans
 * premier argument, et les constructeurs `Intl` sans locale. Le premier
 * argument peut être une chaîne ou un tableau ; l'absence d'argument est le
 * seul cas visé, et `undefined` écrit explicitement en est un aussi — il dit
 * « prends la locale du poste ».
 */
const DELEGATIONS: readonly (readonly [RegExp, string])[] = [
  [/\.toLocale(?:Date|Time)?String\(\s*(?:\)|undefined\b)/, 'toLocale…String() sans locale'],
  [/new\s+Intl\.(?:DateTimeFormat|NumberFormat)\(\s*(?:\)|undefined\b|\{)/, 'Intl sans locale'],
];

/**
 * `resolveViewerTimeZone()` interroge `Intl.DateTimeFormat().resolvedOptions()`
 * pour LIRE le fuseau du lecteur, jamais pour rendre une valeur. La colonne
 * qu'il alimente est étiquetée avec le nom du fuseau obtenu. C'est la seule
 * dérogation, et elle est nominative : un second usage devra se justifier ici.
 */
const DEROGATIONS: readonly string[] = ['pages/calendar/calendarView.ts'];

describe('Toute mise en forme épingle sa locale', () => {
  const sources = fichiers(SRC, []);

  it('lit un corpus non vide — sinon la porte serait vide de sens', () => {
    expect(sources.length).toBeGreaterThan(100);
  });

  it('aucune source ne délègue sa langue au navigateur', () => {
    const fautes: string[] = [];
    for (const source of sources) {
      const chemin = relative(SRC, source).replaceAll('\\', '/');
      const lignes = readFileSync(source, 'utf8').split('\n');
      lignes.forEach((ligne, index) => {
        // Un commentaire qui EXPLIQUE le piège ne le commet pas.
        if (/^\s*(?:\*|\/\/)/.test(ligne)) {
          return;
        }
        for (const [motif, nom] of DELEGATIONS) {
          if (!motif.test(ligne)) {
            continue;
          }
          if (DEROGATIONS.includes(chemin) && /resolvedOptions\(\)/.test(ligne)) {
            return;
          }
          fautes.push(`${chemin}:${index + 1} — ${nom}`);
        }
      });
    }
    expect(fautes).toEqual([]);
  });
});
