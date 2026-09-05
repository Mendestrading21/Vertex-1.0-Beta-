/**
 * PORTE — UNE MESURE NE SE COUPE PAS EN DEUX LIGNES.
 *
 * CE QU'ELLE ATTRAPE. Vue en capture dans le pied de Marchés, la pastille de
 * fraîcheur rendait :
 *
 *     il y a 4 │ budget 3  — instantané de
 *     min      │ j           marchés
 *
 * Chaque MESURE coupée entre son nombre et son unité. Un « 3 » seul au bout
 * d'une ligne n'est pas trois jours : c'est un chiffre orphelin, et le lecteur
 * doit reconstruire l'information au lieu de la lire. C'est la même faute que
 * la valeur bornée qui perdait son unité (« 4.413571428… SYN » réduit à
 * « SYN »), corrigée plus tôt : une unité séparée de son nombre ne mesure plus
 * rien.
 *
 * COMMENT ELLE MESURE, ET LA PREMIÈRE VERSION QUI SE TROMPAIT. Compter les
 * rectangles clients (`getClientRects().length > 1`) semblait suffire : un
 * élément qui passe à la ligne en produit un par ligne. Une sonde a réfuté ce
 * raisonnement — sur Portefeuille, `« % »` rendait DEUX rectangles
 * `985,515 8x17` et `993,515 8x17` : même ordonnée, abscisses contiguës. Une
 * seule ligne. Chromium boîte simplement l'espace initial du segment à part.
 * Trois « défauts » sur trois pages étaient des artefacts de mesure.
 *
 * La porte compte donc les ORDONNÉES DISTINCTES. Deux rectangles sur la même
 * ligne de base sont une ligne ; deux ordonnées sont une coupure. Elle ne vise
 * que les segments ATOMIQUES : ceux dont le contenu est une mesure unique,
 * indivisible par nature.
 *
 * CE QU'ELLE N'INTERDIT PAS. Qu'une pastille passe à la ligne ENTRE ses
 * segments : dans une colonne étroite, c'est le bon comportement. Ce qui est
 * interdit, c'est de plier À L'INTÉRIEUR d'une mesure.
 *
 * POURQUOI EN NAVIGATEUR. jsdom ne met rien en page : il n'a ni lignes, ni
 * rectangles. Ce défaut ne peut être vu qu'ici — et il ne l'a d'abord été que
 * dans une capture.
 */
import { expect, test } from './fixtures.ts';

/** Segments dont le contenu est UNE mesure, donc insécable. */
const ATOMES = [
  '.vx-freshness-age',
  '.vx-freshness-budget',
  '.vx-metric-number',
  '.vx-metric-unit',
];

const DESTINATIONS = [
  '/today',
  '/markets',
  '/opportunities',
  '/analysis/SYN-TECH-01',
  '/options/SYN-TECH-01',
  '/portfolio',
  '/risks',
  '/catalysts',
  '/calendar',
  '/sources-reports',
];

test.describe('Aucune mesure ne se coupe entre son nombre et son unité', () => {
  for (const route of DESTINATIONS) {
    test(`${route} : les segments atomiques tiennent sur une ligne`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator('main')).toBeVisible();
      // Les instantanés arrivent après le premier rendu : mesurer trop tôt,
      // c'est mesurer une page vide et la déclarer saine.
      let precedent = -1;
      for (let essai = 0; essai < 25; essai += 1) {
        await page.waitForTimeout(200);
        const courant = await page.locator(ATOMES.join(', ')).count();
        if (courant === precedent) {
          break;
        }
        precedent = courant;
      }

      const fautes = await page.evaluate((selecteurs: string[]) => {
        const resultats: string[] = [];
        for (const selecteur of selecteurs) {
          for (const element of document.querySelectorAll(selecteur)) {
            const html = element as HTMLElement;
            const rects = [...html.getClientRects()];
            if (rects.length === 0) {
              continue; // non peint : rien n'y est coupé
            }
            // L'ordonnée arrondie au pixel : deux boîtes sur la même ligne de
            // base ne font qu'une ligne, quel qu'en soit le nombre.
            const lignes = new Set(rects.map((rect) => Math.round(rect.top)));
            if (lignes.size > 1) {
              resultats.push(
                `${selecteur} « ${(html.textContent ?? '').trim()} » sur ${lignes.size} lignes`,
              );
            }
          }
        }
        return resultats;
      }, ATOMES);

      expect(fautes, `Mesures coupées sur ${route} :\n${fautes.join('\n')}`).toEqual([]);
    });
  }
});
