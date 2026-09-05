/**
 * INTÉGRITÉ DES TABLEAUX — une cellule doit rester une cellule.
 *
 * POURQUOI CETTE PORTE EXISTE. Deux défauts de cette session ont la MÊME
 * cause : un élément de tableau à qui une règle CSS retire son `display`
 * tabulaire. Un `<caption>` passé en `display: flex` s'est rendu comme une
 * cellule ; un `<td>` passé en `display: inline-block` a cessé d'être une
 * cellule, et le navigateur a enveloppé ses voisines dans des boîtes de
 * tableau anonymes — en-tête et corps ne s'alignaient plus, quatre valeurs se
 * retrouvaient dans une seule colonne.
 *
 * AUCUN TEST UNITAIRE NE POUVAIT LES VOIR : le DOM était correct dans les deux
 * cas, et jsdom ne fait pas de mise en page. Seule une mesure dans un vrai
 * navigateur les attrape. Les deux fois, c'est la CAPTURE qui a alerté, jamais
 * la suite. Cette porte remplace l'œil.
 *
 * CE QU'ELLE VÉRIFIE, ET RIEN DE PLUS.
 *
 *   1. Chaque `td`, `th`, `tr`, `thead`, `tbody` et `caption` conserve le
 *      `display` que sa nature impose.
 *   2. Dans chaque tableau, la première ligne de corps s'aligne exactement sur
 *      la ligne d'en-tête qui la nomme : les bords gauche et droit de chaque
 *      cellule tombent sur ceux d'une cellule d'en-tête. Un décalage signe une
 *      colonne perdue.
 */
import { expect, test } from './fixtures.ts';

/**
 * Destinations, et le nombre de tableaux qu'on doit y TROUVER.
 *
 * Le minimum n'est pas décoratif. Une première version de cette porte est
 * passée au vert sur `/options` alors que la chaîne y était cassée : la table
 * n'était pas encore rendue au moment de la mesure, `querySelectorAll('table')`
 * rendait une liste vide, et une boucle sur zéro élément ne trouve jamais rien.
 * C'est la même vacuité que `toContain` sur un sur-ensemble. Le minimum rend
 * l'absence de table BRUYANTE.
 */
const DESTINATIONS: ReadonlyArray<{ readonly route: string; readonly minimum: number }> = [
  { route: '/today', minimum: 0 },
  { route: '/opportunities', minimum: 1 },
  { route: '/analysis', minimum: 0 },
  // Sans sous-jacent, /options ne rend AUCUNE chaîne — c'est son état vide
  // légitime, pas un défaut. La chaîne se mesure sur l'adresse qui la porte.
  { route: '/options', minimum: 0 },
  { route: '/options/SYN-TECH-01', minimum: 1 },
  { route: '/analysis/SYN-TECH-01', minimum: 1 },
  { route: '/simulator', minimum: 0 },
  { route: '/calendar', minimum: 0 },
  { route: '/markets', minimum: 1 },
  { route: '/charts', minimum: 0 },
  { route: '/portfolio', minimum: 1 },
  { route: '/catalysts', minimum: 0 },
  { route: '/risks', minimum: 0 },
  { route: '/sources-reports', minimum: 1 },
];

/**
 * Attend que le nombre de tableaux se STABILISE.
 *
 * Les pages chargent leurs instantanés après le premier rendu : mesurer trop
 * tôt, c'est mesurer une page vide et conclure qu'elle est saine.
 */
async function attendreLesTables(page: import('@playwright/test').Page): Promise<number> {
  let precedent = -1;
  for (let essai = 0; essai < 25; essai += 1) {
    await page.waitForTimeout(200);
    const courant = await page.locator('table').count();
    if (courant === precedent) {
      return courant;
    }
    precedent = courant;
  }
  return precedent;
}

/** `display` admissible par nature d'élément de tableau. */
const ATTENDU: Readonly<Record<string, readonly string[]>> = {
  TABLE: ['table'],
  CAPTION: ['table-caption'],
  THEAD: ['table-header-group'],
  TBODY: ['table-row-group'],
  TFOOT: ['table-footer-group'],
  TR: ['table-row'],
  TH: ['table-cell'],
  TD: ['table-cell'],
};

test.describe('Intégrité des tableaux — une cellule reste une cellule', () => {
  for (const { route, minimum } of DESTINATIONS) {
    test(`${route} : aucun élément de tableau ne perd son display tabulaire`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator('main')).toBeVisible();
      const tables = await attendreLesTables(page);
      expect(tables, `${route} devrait rendre au moins ${minimum} tableau(x)`).toBeGreaterThanOrEqual(
        minimum,
      );
      const fautes = await page.evaluate((attendu: Record<string, readonly string[]>) => {
        const resultats: string[] = [];
        for (const table of document.querySelectorAll('table')) {
          const nom = (table.getAttribute('aria-label') ?? table.className) || '(table sans nom)';
          for (const element of [table, ...table.querySelectorAll('*')]) {
            const admis = attendu[element.tagName];
            if (admis === undefined) {
              continue;
            }
            const rendu = getComputedStyle(element).display;
            if (!admis.includes(rendu)) {
              resultats.push(
                `${nom} → <${element.tagName.toLowerCase()}> rendu en « ${rendu} », attendu ${admis.join(' ou ')}`,
              );
            }
          }
        }
        return resultats;
      }, ATTENDU);
      expect(fautes, `Éléments de tableau au display non tabulaire sur ${route}`).toEqual([]);
    });

    test(`${route} : en-tête et corps partagent les mêmes colonnes`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator('main')).toBeVisible();
      const tables = await attendreLesTables(page);
      expect(tables, `${route} devrait rendre au moins ${minimum} tableau(x)`).toBeGreaterThanOrEqual(
        minimum,
      );
      const fautes = await page.evaluate(() => {
        const resultats: string[] = [];
        const bord = (n: Element) => {
          const r = n.getBoundingClientRect();
          return { g: Math.round(r.left), d: Math.round(r.right) };
        };
        for (const table of document.querySelectorAll('table')) {
          const nom = (table.getAttribute('aria-label') ?? table.className) || '(table sans nom)';
          const corps = table.tBodies[0]?.rows[0];
          const tete = table.tHead;
          if (corps === undefined || tete === null || tete.rows.length === 0) {
            continue;
          }
          // Une ligne pleine largeur (repère, message) n'a pas de colonnes à
          // comparer : on ne l'invente pas.
          if (corps.cells.length === 1 && corps.cells[0]!.colSpan > 1) {
            continue;
          }
          const bordsTete = new Set<number>();
          for (const ligne of tete.rows) {
            for (const cellule of ligne.cells) {
              const b = bord(cellule);
              bordsTete.add(b.g);
              bordsTete.add(b.d);
            }
          }
          for (const cellule of corps.cells) {
            const b = bord(cellule);
            // Tolérance d'un pixel : les bordures fusionnées peuvent arrondir.
            const proche = (x: number) => [...bordsTete].some((t) => Math.abs(t - x) <= 1);
            if (!proche(b.g) || !proche(b.d)) {
              resultats.push(
                `${nom} → cellule « ${(cellule.textContent ?? '').trim().slice(0, 24)} » à ${b.g}..${b.d}, hors de toute colonne d'en-tête`,
              );
            }
          }
        }
        return resultats;
      });
      expect(fautes, `Colonnes désalignées entre en-tête et corps sur ${route}`).toEqual([]);
    });
  }
});

/**
 * PORTE — CHAQUE DESTINATION A SON PROPRE TITRE DE DOCUMENT.
 *
 * Les treize routes partageaient un unique « Vertex » : dans une fenêtre à
 * plusieurs onglets, aucun ne se distinguait, l'historique du navigateur
 * n'était qu'une colonne de doublons, et un signet ne disait pas ce qu'il
 * pointait. Le titre d'un document EST une information de navigation
 * (WCAG 2.4.2), pas une décoration.
 */
test.describe('Titre du document — une destination, un titre', () => {
  test('les douze destinations portent des titres DISTINCTS', async ({ page }) => {
    const vus = new Map<string, string>();
    for (const { route } of DESTINATIONS) {
      await page.goto(route);
      await expect(page.locator('main')).toBeVisible();
      const titre = await page.title();
      expect(titre, `${route} : titre vide`).not.toBe('');
      expect(titre, `${route} : titre générique`).not.toBe('Vertex');
      const deja = vus.get(titre);
      // Deux ADRESSES peuvent partager un titre quand elles montrent la même
      // destination (« /options » et « /options/SYN-TECH-01 ») : c'est la
      // DESTINATION qui doit se distinguer, pas l'URL.
      if (deja !== undefined && !route.startsWith(`${deja}`)) {
        expect(
          deja.split('/')[1],
          `${route} porte le même titre que ${deja} : « ${titre} »`,
        ).toBe(route.split('/')[1]);
      }
      vus.set(titre, route);
    }
    // Au moins dix titres différents pour treize adresses : sans ce plancher,
    // la porte passerait au vert sur un titre unique mal découpé.
    expect(new Set([...vus.keys()]).size).toBeGreaterThanOrEqual(10);
  });
});
