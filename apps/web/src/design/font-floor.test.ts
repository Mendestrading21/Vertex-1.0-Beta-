// @vitest-environment node
/**
 * PORTE — AUCUNE TAILLE DE TEXTE SOUS LE PLANCHER DÉCLARÉ.
 *
 * CE QU'ELLE ATTRAPE. Le CSS portait trente tailles LITTÉRALES sous le
 * plancher affiché du système : dix-huit à 10 px, cinq à 10,5 px, six à 11 px,
 * une à 12 px. Chaque nouvelle micro-étiquette recopiait le nombre de sa
 * voisine, et l'échelle typographique cessait d'exister là où le texte est le
 * plus dense — exactement là où elle compte le plus. Le commentaire de
 * `widgets.css` nommait cette dette ; rien ne la gardait.
 *
 * CE QU'ELLE EXIGE. Toute taille de texte vient d'un jeton de l'échelle, et
 * aucun jeton ne descend sous le plancher. Une taille littérale, même égale à
 * un jeton, est refusée : c'est le nombre recopié qui fait dériver l'échelle,
 * pas sa valeur du jour.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { fontSize } from './tokens.ts';

const FEUILLES = ['../styles/global.css', '../styles/widgets.css'];

/** Le plus petit corps où Geist reste lisible sur fond obsidienne, mesuré. */
const PLANCHER_PX = 11;

describe('Échelle typographique — un plancher, et il est tenu', () => {
  it('aucun jeton de l’échelle ne descend sous le plancher', () => {
    for (const [nom, valeur] of Object.entries(fontSize)) {
      const px = Number.parseFloat(valeur);
      expect(px, `jeton trop petit : ${nom} = ${valeur}`).toBeGreaterThanOrEqual(PLANCHER_PX);
    }
  });

  it('le CSS n’écrit AUCUNE taille de texte littérale', () => {
    const fautes: string[] = [];
    for (const nom of FEUILLES) {
      const css = readFileSync(fileURLToPath(new URL(nom, import.meta.url)), 'utf8');
      let ligne = 0;
      for (const texte of css.split('\n')) {
        ligne += 1;
        const nue = texte.trim();
        if (nue.startsWith('*') || nue.startsWith('/*') || nue.startsWith('//')) {
          continue;
        }
        // `font-size: <nombre>px` — la forme exacte que la porte refuse.
        // `inherit`, `0` et les jetons passent.
        if (/font-size:\s*[\d.]+px/.test(nue)) {
          fautes.push(`${nom.replace('../styles/', '')}:${ligne} — ${nue}`);
        }
      }
    }
    expect(
      fautes,
      `Tailles de texte littérales : elles doivent venir d’un jeton.\n  ${fautes.join('\n  ')}`,
    ).toEqual([]);
  });
});
