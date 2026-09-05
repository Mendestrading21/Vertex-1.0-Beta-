/**
 * PORTE — AUCUN NOMBRE SERVI N'EST ROGNÉ EN SILENCE.
 *
 * CE QU'ELLE ATTRAPE. Le worker publie ses flottants ENTIERS :
 * `4.413571428571428`, `0.0034193193797471775973762693`. Rendus tels quels
 * dans une carte étroite, ils débordent, coupent au milieu d'un chiffre, ou
 * sont rognés par `text-overflow` — et un nombre coupé n'est plus une donnée,
 * c'est une donnée FAUSSE. « 0.184… » lu comme « 0.184 » perd sa précision
 * sans le dire.
 *
 * CE QU'ELLE N'INTERDIT PAS. Rogner au rendu est légitime : la valeur exacte à
 * seize décimales détruit l'alignement d'une colonne, et la comparaison de
 * deux lignes EST la fonction d'une table. Ce que la porte exige, c'est que la
 * valeur complète reste ATTEIGNABLE — dans le `title` de l'élément ou d'un de
 * ses parents proches, donc au survol et dans le nom accessible.
 *
 * POURQUOI EN NAVIGATEUR ET PAS EN UNITAIRE. `scrollWidth > clientWidth` n'a
 * de sens qu'après une vraie mise en page. jsdom ne mesure rien : ce défaut ne
 * peut pas être vu ailleurs qu'ici.
 */
import { expect, test } from './fixtures.ts';

const DESTINATIONS = [
  '/today',
  '/opportunities',
  '/analysis/SYN-TECH-01',
  '/options/SYN-TECH-01',
  '/simulator',
  '/calendar',
  '/markets',
  '/charts',
  '/portfolio',
  '/catalysts',
  '/risks',
  '/sources-reports',
];

test.describe('Nombres servis — rognés seulement si la valeur reste atteignable', () => {
  for (const route of DESTINATIONS) {
    test(`${route} : aucune valeur rognée sans recours`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator('main')).toBeVisible();
      // Les instantanés arrivent après le premier rendu : mesurer trop tôt,
      // c'est mesurer une page vide et la déclarer saine.
      let precedent = -1;
      for (let essai = 0; essai < 25; essai += 1) {
        await page.waitForTimeout(200);
        const courant = await page.locator('.vx-num').count();
        if (courant === precedent) {
          break;
        }
        precedent = courant;
      }
      const fautes = await page.evaluate(() => {
        const resultats: string[] = [];
        for (const element of document.querySelectorAll('.vx-num')) {
          const html = element as HTMLElement;
          if (html.offsetParent === null && html.getClientRects().length === 0) {
            continue; // hors écran : rien n'est rogné de ce qui n'est pas peint
          }
          const rogne = html.scrollWidth > html.clientWidth + 1;
          if (!rogne) {
            continue;
          }
          // La valeur complète doit rester atteignable : `title` sur l'élément
          // ou sur un parent proche (la cellule, l'étiquette).
          let recours = false;
          let noeud: HTMLElement | null = html;
          for (let niveau = 0; niveau < 4 && noeud !== null; niveau += 1) {
            const titre = noeud.getAttribute('title') ?? '';
            const nom = noeud.getAttribute('aria-label') ?? '';
            const complet = (html.textContent ?? '').trim();
            if (titre.includes(complet) || nom.includes(complet)) {
              recours = true;
              break;
            }
            // Un `title` non vide qui contient DÉJÀ la valeur brute compte
            // aussi quand le rendu tronque : on compare alors sans l'ellipse.
            const sansEllipse = complet.replace(/[……]/g, '');
            if (sansEllipse !== '' && (titre.includes(sansEllipse) || nom.includes(sansEllipse))) {
              recours = true;
              break;
            }
            noeud = noeud.parentElement;
          }
          if (!recours) {
            resultats.push(
              `« ${(html.textContent ?? '').trim().slice(0, 40)} » rogné (${html.scrollWidth} px dans ${html.clientWidth} px) sans valeur complète atteignable`,
            );
          }
        }
        return resultats;
      });
      expect(
        fautes,
        `Valeurs rognées sans recours sur ${route} :\n  ${fautes.join('\n  ')}`,
      ).toEqual([]);
    });
  }
});
