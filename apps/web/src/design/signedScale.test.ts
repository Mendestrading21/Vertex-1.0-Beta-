// @vitest-environment node
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { SIGNED_SCALES, signedStep } from './signedScale.ts';
import { color } from './tokens.ts';

/**
 * Ce que ces tests gèlent : l'échelle est une TABLE FIXE, pas une
 * normalisation. Une valeur donne toujours le même cran, quelles que soient
 * les autres valeurs de la planche.
 */
const QUOTIDIEN = SIGNED_SCALES.quotidien;
const SIGNED_STEPS = QUOTIDIEN.steps;

describe('Échelle divergente — bornes fixes, jamais normalisées', () => {
  it('couvre la droite réelle sans trou ni recouvrement, sur CHAQUE échelle', () => {
    for (const echelle of Object.values(SIGNED_SCALES)) {
      const crans = echelle.steps.filter((cran) => cran.key !== 'flat');
      expect(crans[0]?.from, `${echelle.key} : première borne`).toBeNull();
      expect(crans.at(-1)?.to, `${echelle.key} : dernière borne`).toBeNull();
      for (let i = 1; i < crans.length; i += 1) {
        expect(crans[i]?.from, `${echelle.key} : discontinuité avant ${crans[i]?.key}`).toBe(
          crans[i - 1]?.to,
        );
      }
    }
  });

  it('donne à chaque échelle ses PROPRES seuils', () => {
    // Un rendement quotidien et un rendement mensuel n'ont pas la même
    // amplitude usuelle. Peindre les deux avec les mêmes bornes saturerait la
    // grille mensuelle — tout au dernier cran — et la couleur cesserait de
    // mesurer, ce qui est exactement le défaut qu'on vient de corriger.
    const bornesQuotidien = SIGNED_SCALES.quotidien.steps.map((c) => c.to);
    const bornesMensuel = SIGNED_SCALES.mensuel.steps.map((c) => c.to);
    expect(bornesQuotidien).not.toEqual(bornesMensuel);
    // Et chaque échelle DIT ce qu'elle mesure : une légende sans grandeur
    // nommée laisse croire qu'une seule échelle existe.
    for (const echelle of Object.values(SIGNED_SCALES)) {
      expect(echelle.mesure.length, `${echelle.key} : grandeur non nommée`).toBeGreaterThan(8);
    }
  });

  it('couvre la droite réelle sans trou ni recouvrement', () => {
    // Un trou laisserait une valeur sans couleur ; un recouvrement rendrait le
    // rangement dépendant de l'ordre de la table. Les deux sont des défauts
    // silencieux : la carte s'afficherait quand même.
    const signes = SIGNED_STEPS.filter((cran) => cran.key !== 'flat');
    expect(signes[0]!.from).toBeNull();
    expect(signes.at(-1)!.to).toBeNull();
    for (let i = 1; i < signes.length; i += 1) {
      expect(signes[i]!.from, `discontinuité avant ${signes[i]!.key}`).toBe(signes[i - 1]!.to);
    }
  });

  it('range chaque valeur dans un seul cran, bornes comprises', () => {
    expect(signedStep(-9.9, QUOTIDIEN)?.key).toBe('down-3');
    expect(signedStep(-2, QUOTIDIEN)?.key).toBe('down-2'); // borne basse INCLUSE
    expect(signedStep(-2.0001, QUOTIDIEN)?.key).toBe('down-3');
    expect(signedStep(-1, QUOTIDIEN)?.key).toBe('down-1');
    expect(signedStep(-0.01, QUOTIDIEN)?.key).toBe('down-1');
    expect(signedStep(0, QUOTIDIEN)?.key).toBe('flat');
    expect(signedStep(0.01, QUOTIDIEN)?.key).toBe('up-1');
    expect(signedStep(1, QUOTIDIEN)?.key).toBe('up-2');
    expect(signedStep(2, QUOTIDIEN)?.key).toBe('up-3');
    expect(signedStep(48, QUOTIDIEN)?.key).toBe('up-3');
  });

  it('donne au ZÉRO EXACT son propre cran', () => {
    // « Exactement zéro » est une OBSERVATION, pas une absence, et pas non plus
    // une petite hausse : il ne doit ressembler à aucun des deux signes.
    const zero = signedStep(0, QUOTIDIEN);
    expect(zero?.key).toBe('flat');
    expect(zero?.token).not.toBe(signedStep(0.01, QUOTIDIEN)?.token);
    expect(zero?.token).not.toBe(signedStep(-0.01, QUOTIDIEN)?.token);
  });

  it('ne peint AUCUNE absence', () => {
    expect(signedStep(null, QUOTIDIEN)).toBeNull();
    expect(signedStep(Number.NaN, QUOTIDIEN)).toBeNull();
    expect(signedStep(Number.POSITIVE_INFINITY, QUOTIDIEN)).toBeNull();
  });

  it('ne dépend pas des autres valeurs — c’est ce qui la distingue d’une normalisation', () => {
    // La même entrée, seule ou au milieu d'une planche entière, rend le même
    // cran. Une normalisation locale échouerait ici.
    const isolee = signedStep(1.5, QUOTIDIEN);
    for (const bruit of [-100, -3, 0, 0.2, 7, 250]) {
      signedStep(bruit, QUOTIDIEN);
    }
    expect(signedStep(1.5, QUOTIDIEN)).toEqual(isolee);
  });

  it('nomme des jetons qui EXISTENT, sur chaque échelle', () => {
    for (const echelle of Object.values(SIGNED_SCALES)) {
      for (const cran of echelle.steps) {
        expect(Object.keys(color), `jeton inconnu : ${cran.token}`).toContain(cran.token);
      }
    }
  });

  it('la LÉGENDE peint exactement ce que la carte peint', () => {
    // Le rangement valeur → jeton vit ici ; la pastille de légende le recopie
    // en CSS. Deux endroits, donc deux occasions de diverger — et une légende
    // qui ment sur les couleurs qu'elle explique est pire qu'une absence de
    // légende, parce qu'on lui fait confiance.
    const css = readFileSync(fileURLToPath(new URL('../styles/widgets.css', import.meta.url)), 'utf8');
    for (const cran of SIGNED_STEPS) {
      const regle = new RegExp(
        `\\[data-step='${cran.key}'\\][^}]*background-color:\\s*var\\(--vx-${cran.token}\\)`,
      );
      expect(regle.test(css), `la pastille « ${cran.key} » ne peint pas ${cran.token}`).toBe(true);
    }
  });

  it('publie une légende chiffrée pour chaque cran de chaque échelle', () => {
    for (const echelle of Object.values(SIGNED_SCALES)) {
      for (const cran of echelle.steps) {
        expect(cran.label, `libellé sans chiffre : ${echelle.key}/${cran.key}`).toMatch(/\d/);
        expect(cran.label).toContain('%');
      }
      expect(new Set(echelle.steps.map((c) => c.token)).size).toBe(echelle.steps.length);
    }
  });
});
