// @vitest-environment node
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { SIGNED_STEPS, signedStep } from './signedScale.ts';
import { color } from './tokens.ts';

/**
 * Ce que ces tests gèlent : l'échelle est une TABLE FIXE, pas une
 * normalisation. Une valeur donne toujours le même cran, quelles que soient
 * les autres valeurs de la planche.
 */
describe('Échelle divergente — bornes fixes, jamais normalisées', () => {
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
    expect(signedStep(-9.9)?.key).toBe('down-3');
    expect(signedStep(-2)?.key).toBe('down-2'); // borne basse INCLUSE
    expect(signedStep(-2.0001)?.key).toBe('down-3');
    expect(signedStep(-1)?.key).toBe('down-1');
    expect(signedStep(-0.01)?.key).toBe('down-1');
    expect(signedStep(0)?.key).toBe('flat');
    expect(signedStep(0.01)?.key).toBe('up-1');
    expect(signedStep(1)?.key).toBe('up-2');
    expect(signedStep(2)?.key).toBe('up-3');
    expect(signedStep(48)?.key).toBe('up-3');
  });

  it('donne au ZÉRO EXACT son propre cran', () => {
    // « Exactement zéro » est une OBSERVATION, pas une absence, et pas non plus
    // une petite hausse : il ne doit ressembler à aucun des deux signes.
    const zero = signedStep(0);
    expect(zero?.key).toBe('flat');
    expect(zero?.token).not.toBe(signedStep(0.01)?.token);
    expect(zero?.token).not.toBe(signedStep(-0.01)?.token);
  });

  it('ne peint AUCUNE absence', () => {
    expect(signedStep(null)).toBeNull();
    expect(signedStep(Number.NaN)).toBeNull();
    expect(signedStep(Number.POSITIVE_INFINITY)).toBeNull();
  });

  it('ne dépend pas des autres valeurs — c’est ce qui la distingue d’une normalisation', () => {
    // La même entrée, seule ou au milieu d'une planche entière, rend le même
    // cran. Une normalisation locale échouerait ici.
    const isolee = signedStep(1.5);
    for (const bruit of [-100, -3, 0, 0.2, 7, 250]) {
      signedStep(bruit);
    }
    expect(signedStep(1.5)).toEqual(isolee);
  });

  it('nomme des jetons qui EXISTENT', () => {
    for (const cran of SIGNED_STEPS) {
      expect(Object.keys(color), `jeton inconnu : ${cran.token}`).toContain(cran.token);
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

  it('publie une légende chiffrée pour chaque cran', () => {
    for (const cran of SIGNED_STEPS) {
      expect(cran.label, `libellé sans chiffre : ${cran.key}`).toMatch(/\d/);
      expect(cran.label).toContain('%');
    }
    expect(new Set(SIGNED_STEPS.map((c) => c.token)).size).toBe(SIGNED_STEPS.length);
  });
});
