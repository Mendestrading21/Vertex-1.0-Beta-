/**
 * PORTES DE MISE EN PAGE — LOT V3a.
 *
 * Trois questions qu'AUCUN test ne posait aux largeurs de release :
 *
 *   1. le contenu d'une carte TIENT-IL dans sa carte ?
 *   2. un module placé sur une planche à aires nommées OBTIENT-IL son aire ?
 *   3. une rangée de planche est-elle majoritairement VIDE ?
 *
 * CE QUI EXISTAIT. Le débordement horizontal n'était mesuré qu'à 1024×768
 * (`smoke.spec.ts`), une largeur explicitement déclarée « ni breakpoint mobile,
 * ni cible de release ». Aux trois largeurs de release, personne ne mesurait
 * rien. Ces portes tournent sur les trois projets desktop.
 *
 * CE QUE LA MESURE A TROUVÉ, avant d'écrire une seule assertion :
 *
 *   - AUCUN débordement horizontal de PAGE, aux trois largeurs. La planche
 *     tient. Le défaut est un cran plus bas, dans les cartes.
 *   - VINGT cartes dont le contenu ne tient pas. La pire, `market-map` sur
 *     Marchés : `table.vx-markets-table` mesure 1 613 px dans une carte qui
 *     coupe à 1 365 px, aux TROIS largeurs. Environ treize lignes de marché
 *     sont peintes hors de la carte et effacées par
 *     `.vx-chartframe { overflow: hidden }` — sans défilement, sans indicateur,
 *     sans que rien ne le dise. La donnée n'est pas illisible : elle est
 *     ABSENTE de l'écran.
 *   - ZÉRO module privé de son aire nommée. Cette porte est donc une porte de
 *     NON-RÉGRESSION, et sa capacité à échouer est prouvée par mutation, pas
 *     par un défaut du jour.
 *   - QUATRE-VINGT-SEPT rangées dont la carte la plus haute fait plus de 1,6
 *     fois la plus basse, pour 49 761 px de hauteur vide cumulée. Au seuil du
 *     tiers retenu ici : DIX-NEUF rangées sur SEPT pages.
 */
import { expect, test } from './fixtures.ts';

const INSTRUMENT = 'SYN-TECH-01';

/**
 * Les destinations qui portent une PLANCHE de modules.
 *
 * `/analysis` sans instrument en est absente : elle ne rend aucun
 * `[data-module]`. Ce n'est pas un oubli commode — le dernier test de ce
 * fichier le VÉRIFIE, pour qu'une planche ajoutée un jour à cette route ne
 * puisse pas échapper aux trois portes par le simple fait d'être exclue ici.
 */
const ROUTES = [
  '/today',
  '/calendar',
  '/markets',
  '/opportunities',
  `/analysis/${INSTRUMENT}`,
  '/options',
  `/options/${INSTRUMENT}`,
  '/simulator',
  '/charts',
  `/charts/${INSTRUMENT}`,
  '/portfolio',
  '/risks',
  '/catalysts',
  '/sources-reports',
] as const;

const SANS_PLANCHE = ['/analysis'] as const;

/** Tolérance d'un pixel : les hauteurs calculées sont fractionnaires. */
const EPSILON = 1;

/**
 * DETTE V3a — CARTES DONT LE CONTENU NE TIENT PAS.
 *
 * Chaque entrée nomme la route, le module, ce qui se passe et le lot qui la
 * ferme. Aucune n'est fermée ici : V3a POSE les portes, il ne recompose pas les
 * pages — c'est le travail des lots de page, qui décideront si la carte
 * s'agrandit, si son contenu défile, ou s'il faut moins en montrer.
 *
 * Une dette est une promesse datée, pas une exemption : le cliquet plus bas
 * interdit de l'allonger.
 */
const DETTE_CARTE: ReadonlyArray<{
  readonly route: string;
  readonly module: string;
  readonly nature: string;
  readonly lot: string;
}> = [
  {
    route: '/markets',
    module: 'market-map',
    nature: 'COUPE ~1 086 px : la table des marchés est plus haute que sa carte et `overflow: hidden` en efface la fin',
    lot: 'V4',
  },
  { route: '/today', module: 'global-market', nature: 'déborde en largeur', lot: 'V6' },
  { route: '/today', module: 'calendar', nature: 'déborde en largeur', lot: 'V6' },
  { route: '/calendar', module: 'next-event', nature: 'déborde en largeur', lot: 'V10' },
  { route: `/analysis/${INSTRUMENT}`, module: 'indicators', nature: 'déborde en largeur', lot: 'V7' },
  { route: `/analysis/${INSTRUMENT}`, module: 'upcoming-catalysts', nature: 'déborde en largeur', lot: 'V7' },
  { route: `/analysis/${INSTRUMENT}`, module: 'key-risks', nature: 'déborde en largeur', lot: 'V7' },
  { route: `/analysis/${INSTRUMENT}`, module: 'evidence', nature: 'déborde en largeur', lot: 'V7' },
  { route: '/portfolio', module: 'total-performance', nature: 'déborde en largeur', lot: 'V9' },
  { route: '/risks', module: 'coverage', nature: 'déborde en largeur', lot: 'V9' },
];

const DETTE_CARTE_MAX = 10;

/**
 * DETTE V3a — RANGÉES MAJORITAIREMENT VIDES, par route.
 *
 * La valeur est le nombre de rangées tolérées SUR CETTE ROUTE, toutes largeurs
 * confondues au sein d'un même projet. La pire mesure du produit est la
 * première rangée d'Aujourd'hui à 1440×900 : quatre cartes, la plus haute à
 * 1 052 px, la plus basse à 156 px, soit 2 459 px de vide — 58 % de la surface
 * de la rangée. C'est le trou que la capture montrait sans que rien ne le
 * chiffre.
 */
const DETTE_TROU: Readonly<Record<string, { readonly max: number; readonly lot: string }>> = {
  '/catalysts': { max: 2, lot: 'V10' },
  '/today': { max: 1, lot: 'V6' },
  '/portfolio': { max: 1, lot: 'V9' },
  '/simulator': { max: 1, lot: 'V8' },
  [`/analysis/${INSTRUMENT}`]: { max: 1, lot: 'V7' },
  [`/options/${INSTRUMENT}`]: { max: 1, lot: 'V8' },
};

/**
 * CES PLAFONDS ONT ÉTÉ RESSERRÉS DEUX FOIS, ET LES DEUX PREMIERS JETS ÉTAIENT FAUX.
 *
 * Je les avais d'abord dimensionnés sur la SOMME des trois largeurs — 5 pour
 * Aujourd'hui, 5 pour Catalyseurs, 3 pour Portefeuille. Or la porte tourne PAR
 * LARGEUR : un plafond de 5 pour une route qui n'en produit jamais plus de 2
 * laisse passer trois régressions sans rien dire. Une dette trop large est une
 * porte qui ment sur ce qu'elle garde.
 *
 * Le deuxième jet était faux autrement : il figeait des maxima relevés sur une
 * mesure INSTABLE, avant que `attendreStabilite` n'existe. Aujourd'hui est
 * ainsi passé de 2 à 1, et `/risks` — que j'avais retiré, puis remis en le
 * croyant réel — n'a AUCUNE violation une fois la planche stabilisée : sa
 * rangée à 36 % était un artefact de mesure, pas un défaut du produit.
 *
 * Les valeurs ci-dessus sont le maximum observé sur UNE largeur, relevé en
 * vidant la dette et en comptant les échecs des trois projets — et ce relevé a
 * été refait une seconde fois, à la ligne près, pour ne plus conclure sur une
 * observation unique. C'est la troisième fois que ce fichier me reprend ; les
 * deux premières, j'avais cru une porte verte sans l'avoir fait rougir.
 */

/** Part maximale de surface vide tolérée dans une rangée. */
const PART_VIDE_MAX = 1 / 3;

interface MesureCarte {
  readonly id: string;
  readonly dx: number;
  readonly dy: number;
  readonly coupe: boolean;
}

interface MesureRangee {
  readonly hauteurs: readonly number[];
  readonly part: number;
}

/**
 * Attend que la PLANCHE ait fini de bouger avant de la mesurer.
 *
 * POURQUOI CE N'EST PAS UN CONFORT. Sans cette attente, la même page mesurée
 * deux fois donne deux résultats : les graphiques se dessinent après le premier
 * rendu, les textes se réenveloppent, et les hauteurs de carte changent. Une
 * porte qui bascule d'un run à l'autre est un test flaky — et un test flaky est
 * un échec, pas un aléa. On lit donc les hauteurs jusqu'à obtenir DEUX relevés
 * identiques consécutifs.
 *
 * Ce n'est pas non plus `networkidle` : Vertex tient un flux SSE ouvert en
 * permanence, le réseau n'est jamais au repos et l'attente n'aboutirait jamais.
 * On observe la mise en page, pas le réseau.
 */
async function attendreStabilite(page: import('@playwright/test').Page): Promise<void> {
  const lire = async (): Promise<string> =>
    page.evaluate(() =>
      [...document.querySelectorAll('[data-module]')]
        .map((el) => {
          const r = el.getBoundingClientRect();
          return `${Math.round(r.top)}:${Math.round(r.height)}:${Math.round(r.width)}`;
        })
        .join('|'),
    );
  let precedent = await lire();
  for (let essai = 0; essai < 20; essai += 1) {
    await page.waitForTimeout(150);
    const courant = await lire();
    if (courant === precedent && courant !== '') {
      return;
    }
    precedent = courant;
  }
  throw new Error('la planche ne se stabilise pas : mesure impossible sans flakiness');
}

test.describe('Portes de mise en page — trois largeurs de release', () => {
  for (const route of ROUTES) {
    test(`${route} : le contenu de chaque carte tient dans sa carte`, async ({ page }) => {
      await page.goto(route);
      await page.locator('[data-module]').first().waitFor({ state: 'attached' });
      await attendreStabilite(page);
      const cartes: MesureCarte[] = await page.evaluate(() => {
        return [...document.querySelectorAll('[data-module]')]
          .map((el) => {
            const style = getComputedStyle(el);
            const defilable = (v: string): boolean => v === 'auto' || v === 'scroll';
            return {
              id: el.getAttribute('data-module') ?? '?',
              dx: el.scrollWidth - el.clientWidth,
              dy: el.scrollHeight - el.clientHeight,
              // COUPE = le contenu disparaît. Une carte prévue pour défiler
              // n'est pas en faute : son contenu reste atteignable.
              coupe: !defilable(style.overflowX) && !defilable(style.overflowY),
            };
          })
          .filter((c) => c.dx > 1 || c.dy > 1);
      });
      const enDette = new Set(
        DETTE_CARTE.filter((d) => d.route === route).map((d) => d.module),
      );
      const fautes = cartes
        .filter((c) => c.coupe && c.dx + c.dy > EPSILON && !enDette.has(c.id))
        .map((c) => `${c.id} : dépasse de ${c.dx} px en largeur et ${c.dy} px en hauteur`);
      expect(
        fautes,
        `${route} — le contenu de ces cartes ne tient pas, et rien ne permet d'y accéder :\n  ${fautes.join('\n  ')}`,
      ).toEqual([]);
    });

    test(`${route} : aucun module ne perd son aire nommée`, async ({ page }) => {
      await page.goto(route);
      await page.locator('[data-module]').first().waitFor({ state: 'attached' });
      await attendreStabilite(page);
      // RÉGRESSION PAYÉE QUATRE FOIS. `widgets.css` est importé APRÈS
      // `global.css` et les deux sélecteurs ont la même spécificité : une aire
      // nommée déclarée du mauvais côté est simplement ignorée. Aucune erreur,
      // aucun avertissement — les cartes se placent ailleurs, et seul l'œil le
      // voit. Cette porte le dit.
      const perdus: string[] = await page.evaluate(() => {
        return [...document.querySelectorAll('[data-module]')]
          .filter((el) => {
            const parent = el.parentElement;
            if (parent === null) {
              return false;
            }
            const aires = getComputedStyle(parent).gridTemplateAreas;
            if (aires === 'none' || aires === '') {
              return false;
            }
            // ON LIT LES LONGHANDS, PAS LE RACCOURCI.
            //
            // La première version comparait `gridArea` à
            // 'auto / auto / auto / auto'. Chromium sérialise ce cas en 'auto'
            // tout court : la comparaison ne correspondait JAMAIS, et cette
            // porte — écrite pour attraper une régression payée quatre fois —
            // n'aurait rien attrapé du tout. Elle est passée au vert sous une
            // mutation qui retirait délibérément l'aire du module dominant de
            // Marchés. C'est cette mise en échec, pas la relecture, qui l'a
            // révélé : une porte verte qu'on n'a pas su faire rougir ne
            // mesure rien.
            const style = getComputedStyle(el);
            return style.gridRowStart === 'auto' && style.gridColumnStart === 'auto';
          })
          .map((el) => el.getAttribute('data-module') ?? '?');
      });
      expect(
        perdus,
        `${route} — ces modules sont sur une planche à aires nommées mais n'en obtiennent aucune :\n  ${perdus.join('\n  ')}`,
      ).toEqual([]);
    });

    test(`${route} : aucune rangée n'est vide à plus d'un tiers`, async ({ page }) => {
      await page.goto(route);
      await page.locator('[data-module]').first().waitFor({ state: 'attached' });
      await attendreStabilite(page);
      const rangees: MesureRangee[] = await page.evaluate(() => {
        // CSS Grid dimensionne une rangée sur son élément le plus HAUT ; les
        // autres ne s'étirent pas. Une carte qui porte le contenu d'une grande
        // surface sous une taille déclarée petite creuse donc un trou chez ses
        // voisines, sans qu'aucune règle CSS soit fausse.
        const paquets = new Map<number, number[]>();
        for (const el of document.querySelectorAll('[data-module]')) {
          const rect = el.getBoundingClientRect();
          const cle = Math.round(rect.top / 8) * 8;
          paquets.set(cle, [...(paquets.get(cle) ?? []), Math.round(rect.height)]);
        }
        return [...paquets.values()]
          .filter((hauteurs) => hauteurs.length > 1)
          .map((hauteurs) => {
            const max = Math.max(...hauteurs);
            const vide = hauteurs.reduce((somme, h) => somme + (max - h), 0);
            return { hauteurs, part: vide / (hauteurs.length * max) };
          });
      });
      const trouees = rangees.filter((r) => r.part > PART_VIDE_MAX);
      const tolere = DETTE_TROU[route]?.max ?? 0;
      expect(
        trouees.length,
        `${route} — ${trouees.length} rangées vides à plus d'un tiers (toléré : ${tolere}) :\n  ` +
          trouees
            .map((r) => `${r.hauteurs.length} cartes, ${Math.round(r.part * 100)} % de vide, hauteurs ${r.hauteurs.join(' / ')} px`)
            .join('\n  '),
      ).toBeLessThanOrEqual(tolere);
    });
  }

  for (const route of SANS_PLANCHE) {
    test(`${route} ne porte AUCUNE planche — l'exclusion est vérifiée, pas supposée`, async ({
      page,
    }) => {
      await page.goto(route);
      await page.locator('main').waitFor({ state: 'attached' });
      // Si cette route recevait un jour une planche, elle échapperait aux trois
      // portes par sa seule absence de la liste. Ce test transforme
      // l'exclusion en affirmation vérifiable.
      await expect(page.locator('[data-module]')).toHaveCount(0);
    });
  }

  test('les dettes ne peuvent que RÉTRÉCIR — cliquet du lot V3a', () => {
    expect(DETTE_CARTE.length).toBeLessThanOrEqual(DETTE_CARTE_MAX);
    for (const { route, module, nature, lot } of DETTE_CARTE) {
      expect(ROUTES, `dette sur une route non mesurée : ${route}`).toContain(route);
      expect(module.length, 'une dette nomme son module').toBeGreaterThan(0);
      expect(nature.length, `une dette dit CE QUI se passe : ${module}`).toBeGreaterThan(15);
      expect(lot, `une dette nomme le lot qui la ferme : ${module}`).toMatch(/^V\d+[a-z]?$/);
    }
    for (const [route, { max, lot }] of Object.entries(DETTE_TROU)) {
      expect(ROUTES, `dette de trou sur une route non mesurée : ${route}`).toContain(route);
      expect(max, `une tolérance de zéro n'est pas une dette : ${route}`).toBeGreaterThan(0);
      expect(lot, `une dette nomme le lot qui la ferme : ${route}`).toMatch(/^V\d+[a-z]?$/);
    }
  });
});
