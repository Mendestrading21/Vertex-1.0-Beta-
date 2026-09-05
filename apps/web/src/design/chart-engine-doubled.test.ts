// @vitest-environment node
/**
 * PORTE DU MOTEUR DE CHANDELIERS DOUBLÉ.
 *
 * `CandleChart` importe `charts/lightweightChartsLoader.ts` et appelle
 * `createChart`. Dans jsdom il n'y a pas de canvas : le graphique se construit
 * quand même, planifie un `requestAnimationFrame`, et quand celui-ci s'exécute
 * après le démontage `PriceAxisWidget._internal_optimalWidth` lève « Value is
 * null » — HORS de tout test.
 *
 * CE QUE CELA COÛTE, ET POURQUOI AUCUNE ASSERTION NE L'ATTRAPE. L'erreur ne
 * fait échouer aucun test : elle est comptée par Vitest en « unhandled error ».
 * La campagne affiche donc ses tests TOUS VERTS et sort en code 1. Un lecteur
 * pressé lit « 1171 passed » et cherche le défaut ailleurs.
 *
 * PIRE : c'est une COURSE. Le défaut a vécu des semaines dans
 * `AiExplanationPanel.test.tsx`, qui rendait `/analysis/SYN-TECH-01` sans
 * doubler le moteur, sans jamais tomber dans la fenêtre. Il a émergé en CI le
 * jour où un fichier de test supplémentaire a décalé l'ordonnancement. Une
 * campagne verte ne prouvait donc rien à son sujet, et n'aurait rien prouvé
 * demain non plus.
 *
 * CE QU'ELLE NE VOIT PAS, et il faut le dire plutôt que de laisser croire
 * qu'elle couvre tout : elle reconnaît `renderApp('/analysis…` et
 * `renderApp('/charts…` LITTÉRALEMENT. Un test qui passerait la route par une
 * variable, ou qui monterait `CandleChart` directement, lui échapperait.
 * Mesuré au moment de l'écrire : aucun fichier de test n'importe `CandleChart`
 * directement, et aucune route n'est construite par variable. La porte couvre
 * donc l'existant ; elle demandera d'être élargie si cela change.
 *
 * LA PORTE : tout fichier de test qui rend une route montant `CandleChart`
 * DOIT doubler le chargeur. Elle est statique — elle lit les fichiers — parce
 * qu'une porte dynamique dépendrait de l'ordonnancement, c'est-à-dire de la
 * chose même qui rend ce défaut invisible.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { globSync } from 'node:fs';

const racine = fileURLToPath(new URL('../', import.meta.url));

/** Les routes dont le rendu monte `CandleChart`. */
const ROUTES_A_GRAPHIQUE = ['/analysis/', '/charts/'];

const CHARGEUR = 'charts/lightweightChartsLoader.ts';

describe('le moteur de chandeliers est doublé partout où il serait monté', () => {
  const fichiers = globSync('**/*.test.{ts,tsx}', { cwd: racine })
    .map((relatif) => relatif.replaceAll('\\', '/'))
    .filter((relatif) => !relatif.startsWith('design/'));

  it('énumère des fichiers de test — sinon cette porte ne mesure rien', () => {
    expect(fichiers.length).toBeGreaterThan(50);
  });

  it('aucun fichier ne monte une route à graphique sans doubler le chargeur', () => {
    const fautifs: string[] = [];
    for (const relatif of fichiers) {
      const texte = readFileSync(`${racine}${relatif}`, 'utf8');
      const monte = ROUTES_A_GRAPHIQUE.some(
        (route) => texte.includes(`renderApp('${route}`) || texte.includes(`renderApp("${route}`),
      );
      if (!monte) {
        continue;
      }
      if (!texte.includes(CHARGEUR)) {
        fautifs.push(relatif);
      }
    }
    expect(
      fautifs,
      'ces fichiers rendent une route qui monte CandleChart sans doubler ' +
        `\`${CHARGEUR}\` — un vrai graphique est créé dans jsdom, et son ` +
        'requestAnimationFrame lèvera « Value is null » hors de tout test :\n  ' +
        fautifs.join('\n  '),
    ).toEqual([]);
  });
});
