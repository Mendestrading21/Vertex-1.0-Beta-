// @vitest-environment node
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { renderTokensCss } from './generate-css.ts';

/**
 * PORTE ANTI-JETON MORT — LOT V1.
 *
 * `tokens.ts` est la source typée unique, et `tokens-css.test.ts` prouve que le
 * CSS généré la reflète à l'octet près. Aucun des deux ne demande si un jeton
 * SERT. L'audit du 2026-09-04 a compté : `space[40]`, `space[48]` et
 * `shadow.floating` n'ont zéro lecture dans tout le produit — et les deux
 * premiers sont pourtant EXIGÉS par une assertion de `tokens-css.test.ts`, qui
 * fige donc trois jetons que personne n'emploie.
 *
 * Un jeton mort n'est pas neutre. Il fait croire à une échelle plus riche
 * qu'elle n'est, il se recopie dans les documents normatifs, et il rend
 * impossible de savoir ce que le produit utilise vraiment.
 *
 * LA RÈGLE : toute variable `--vx-*` émise doit être lue au moins une fois,
 * quelque part dans les feuilles ou les composants. Si un lot en a besoin plus
 * tard, il l'ajoute LE JOUR OÙ il l'emploie.
 */

const APP_ROOT = fileURLToPath(new URL('../..', import.meta.url));

function collecter(dossier: string, acc: string[]): string[] {
  for (const entree of readdirSync(dossier)) {
    const complet = join(dossier, entree);
    if (statSync(complet).isDirectory()) {
      collecter(complet, acc);
    } else if (/\.(?:css|tsx?)$/.test(complet) && !/\.test\.tsx?$/.test(complet)) {
      acc.push(complet);
    }
  }
  return acc;
}

/**
 * Les variables que le générateur émet, extraites de sa sortie plutôt que
 * reconstruites : reconstruire les noms ici créerait une seconde source de
 * vérité, exactement ce que la source typée unique existe pour empêcher.
 */
function variablesEmises(): readonly string[] {
  const css = renderTokensCss();
  const noms = new Set<string>();
  for (const trouve of css.matchAll(/^\s*(--vx-[a-z0-9-]+):/gm)) {
    const nom = trouve[1];
    if (nom !== undefined) {
      noms.add(nom);
    }
  }
  return [...noms].sort();
}

/** Toutes les lectures `var(--vx-…)` du produit, hors le fichier généré. */
function variablesLues(): ReadonlySet<string> {
  const lues = new Set<string>();
  for (const fichier of collecter(join(APP_ROOT, 'src'), [])) {
    if (relative(APP_ROOT, fichier) === join('src', 'design', 'tokens.css')) {
      continue;
    }
    const contenu = readFileSync(fichier, 'utf8');
    for (const trouve of contenu.matchAll(/var\(\s*(--vx-[a-z0-9-]+)/g)) {
      const nom = trouve[1];
      if (nom !== undefined) {
        lues.add(nom);
      }
    }
  }
  return lues;
}

/**
 * Variables produites par COMPOSITION et jamais écrites en toutes lettres.
 * `--vx-page-accent*` est assignée dans un bloc `[data-page-accent="…"]` et lue
 * ailleurs ; les familles `--vx-<famille>-gradient-*` alimentent ces blocs. Une
 * exemption ici dit « cette variable est un intermédiaire », pas « on ne sait
 * pas si elle sert ».
 */
const INTERMEDIAIRES = /^--vx-(?:macro|option|warning|positive|negative|silver)-gradient-(?:start|end)$/;

/**
 * DETTE V1 — TEMPORAIRE, ET ELLE NE PEUT QUE RÉTRÉCIR.
 *
 * Toutes les variables mortes n'ont pas la même cause, et les traiter pareil
 * aurait été faux :
 *
 *   - `space-40`, `space-48`, `shadow-floating`, `ease-decelerate` sont morts
 *     ET retirables : ils sont retirés dans ce lot.
 *   - Les PLANS Z sont une échelle nommée cohérente dont le défaut réel est
 *     ailleurs : le CSS écrit encore des `z-index` bruts. Les supprimer
 *     entérinerait le défaut au lieu de le corriger ; les mapper à la hâte sur
 *     des valeurs brutes qui ne leur correspondent pas serait pire.
 *   - `--vx-page-accent-soft` et ses dégradés attendent leurs consommateurs :
 *     `--vx-page-accent` en a un depuis le lot P3a, eux pas encore.
 *
 * Chaque entrée nomme le lot qui la ferme. Le plafond ne remonte jamais.
 */
const DETTE_V1: ReadonlyArray<{ readonly variable: string; readonly lot: string }> = [
  { variable: '--vx-z-base', lot: 'V3b' },
  { variable: '--vx-z-popover', lot: 'V3b' },
  { variable: '--vx-z-sheet', lot: 'V3b' },
  { variable: '--vx-z-dialog', lot: 'V3b' },
  { variable: '--vx-page-accent-soft', lot: 'V6' },
  { variable: '--vx-page-accent-gradient-start', lot: 'V6' },
  { variable: '--vx-page-accent-gradient-end', lot: 'V6' },
];

/** Plafond de la dette. ABAISSÉ à chaque lot, jamais relevé. */
const DETTE_MAX = 7;

const EN_DETTE: ReadonlySet<string> = new Set(DETTE_V1.map((entree) => entree.variable));

describe('Aucun jeton mort', () => {
  it('le balayage voit réellement des variables des deux côtés', () => {
    // Anti-vacuité : si l'un des deux ensembles était vide, le test passerait
    // en ne prouvant rien.
    expect(variablesEmises().length).toBeGreaterThan(50);
    expect(variablesLues().size).toBeGreaterThan(50);
  });

  it('chaque variable émise est lue au moins une fois', () => {
    const lues = variablesLues();
    const mortes = variablesEmises().filter(
      (nom) => !lues.has(nom) && !INTERMEDIAIRES.test(nom) && !EN_DETTE.has(nom),
    );
    expect(
      mortes,
      `Variables générées que personne ne lit :\n  ${mortes.join('\n  ')}\n` +
        'Un jeton s’ajoute le jour où il sert, pas avant.',
    ).toEqual([]);
  });

  it('la dette ne peut que RÉTRÉCIR — cliquet du lot V1', () => {
    expect(DETTE_V1.length).toBeLessThanOrEqual(DETTE_MAX);
    expect(new Set(DETTE_V1.map((e) => e.variable)).size).toBe(DETTE_V1.length);
    for (const { lot } of DETTE_V1) {
      expect(lot, 'chaque dette nomme le lot qui la ferme').toMatch(/^V\d+[a-z]?$/);
    }
  });

  it('une variable en dette est RÉELLEMENT morte', () => {
    // Sinon elle est déjà consommée et doit sortir de la liste — c'est ce qui
    // fait avancer le cliquet. Une dette qui survit à sa cause est une
    // exemption qui se déguise.
    const lues = variablesLues();
    const inutiles = DETTE_V1.filter((e) => lues.has(e.variable)).map((e) => e.variable);
    expect(inutiles, 'dette à retirer : ces variables sont consommées').toEqual([]);
  });
});
