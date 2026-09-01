/**
 * Campagne d'accessibilité LOT-23 — au-delà du seuil « critique/sérieux ».
 *
 * Les specs de page exécutent déjà axe avec le seuil zéro sur les violations
 * critiques et sérieuses. Ce n'est PAS une conformité WCAG 2.2 AA : une
 * violation d'impact « moderate » reste une violation de critère AA, et axe ne
 * couvre de toute façon qu'une part des critères.
 *
 * Cette campagne ajoute donc quatre choses que le seuil précédent laissait
 * passer :
 *
 * 1. axe restreint aux ÉTIQUETTES WCAG (2.0 A/AA, 2.1 A/AA, 2.2 AA) avec un
 *    seuil de zéro violation, TOUS impacts confondus ;
 * 2. la traversée clavier : chaque route atteint un élément interactif par
 *    Tab, et l'élément focalisé porte un indicateur de focus visible
 *    (WCAG 2.4.7, et 2.4.11 en 2.2) ;
 * 3. le redimensionnement à 200 % (WCAG 1.4.10 « Reflow ») : à 640×400 px CSS,
 *    ce qui équivaut à un zoom 200 % sur 1280×800, la page ne défile pas
 *    horizontalement ; les contenus larges défilent dans leur conteneur ;
 * 4. `prefers-reduced-motion` (WCAG 2.3.3) : aucune animation ni transition
 *    d'une durée perceptible ne subsiste.
 *
 * Ce que cette campagne NE prouve PAS, et qui reste inscrit à
 * `docs/99-status/DEBT.md` : la revue par un lecteur d'écran réel (NVDA,
 * VoiceOver, Orca) par une personne. Aucun outil automatique ne la remplace,
 * et aucune ligne d'ici ne doit être lue comme si elle le faisait.
 */
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { expect, test } from './fixtures.ts';

/** Étiquettes de règles axe correspondant aux critères WCAG jusqu'à 2.2 AA. */
const WCAG_AA_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] as const;

/**
 * Les routes mesurées — 14 chemins pour 12 des 13 routes de l'application.
 *
 * `/analysis` et `/options` sont PARAMÉTRÉES (`/analysis/:instrument?`,
 * `/options/:underlying?` dans `src/app/pages.ts`). Les visiter sans paramètre
 * rend un encart « Aucun instrument sélectionné » : `OptionChainTable`,
 * `OptionInspector`, `CandleChart` et `PayoffChart` — les composants les plus
 * larges et les plus animés du produit — n'étaient JAMAIS montés. La campagne
 * annonçait « 12 routes » en mesurant neuf pages et trois encarts vides.
 *
 * Les deux états sont désormais mesurés : l'état vide, qui est une vraie page,
 * ET l'état peuplé, qui porte les composants qui décident du contraste, de
 * l'ordre de tabulation dans une grille et du mouvement.
 *
 * `/simulator/:id?` sans paramètre rend en revanche son composeur complet
 * (seule la zone de résultat est vide) : c'est bien la page, pas un encart.
 *
 * `/auth` n'est PAS ici : elle n'a aucune couverture d'accessibilité, et le
 * rapport le dit désormais au lieu de la déclarer couverte.
 */
const INSTRUMENT_SYNTHETIQUE = 'SYN-TECH-01';

const ROUTES = [
  '/today',
  '/calendar',
  '/markets',
  '/opportunities',
  '/analysis',
  `/analysis/${INSTRUMENT_SYNTHETIQUE}`,
  '/options',
  `/options/${INSTRUMENT_SYNTHETIQUE}`,
  '/simulator',
  '/portfolio',
  // Risques porte une GRILLE dense et défilable : c'est précisément le genre
  // de composant où l'accessibilité se perd — en-têtes de ligne collants,
  // région à défilement clavier, couleur porteuse de sens. D'où sa présence
  // ici, plutôt qu'une confiance dans la relecture.
  '/risks',
  '/catalysts',
  // '/performance' a été absorbée dans '/portfolio' (LOT-08) : la visiter
  // ici ne mesurerait plus qu'une redirection. Le module Performance est
  // désormais dans le DOM de '/portfolio', donc balayé par cette entrée —
  // c'est une couverture ajoutée, pas retirée.
  // '/ai' a été absorbée dans l'inspecteur (LOT-12) : la visiter ici ne
  // mesurerait plus qu'une redirection. Le panneau d'explication est dans le
  // DOM de '/analysis' et de '/portfolio', donc balayé par ces deux entrées.
  '/sources-reports',
] as const;

async function expectNoWcagViolation(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags([...WCAG_AA_TAGS]).analyze();
  expect(
    results.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      nodes: violation.nodes.length,
      help: violation.help,
    })),
    'violations WCAG 2.2 AA (tous impacts) — le seuil est zéro',
  ).toEqual([]);
}

test.describe('Accessibilité — WCAG 2.2 AA, tous impacts', () => {
  for (const route of ROUTES) {
    test(`${route} : zéro violation sur les règles étiquetées WCAG`, async ({ page }) => {
      await page.goto(route);
      // Une page encore en chargement n'a pas encore son arbre d'accessibilité
      // définitif : analyser trop tôt donnerait un vert sans signification.
      await expect(page.getByRole('main')).toBeVisible();
      await expectNoWcagViolation(page);
    });
  }
});

test.describe('Accessibilité — traversée clavier et focus visible', () => {
  for (const route of ROUTES) {
    test(`${route} : Tab atteint un élément interactif au focus visible`, async ({ page }) => {
      await page.goto(route);
      await expect(page.getByRole('main')).toBeVisible();

      await page.keyboard.press('Tab');

      // DIFFÉRENTIEL avant/après focus. La version précédente acceptait
      // n'importe quelle `box-shadow` NON VIDE — or
      // `.vx-rail-link[aria-current='page']` en porte une en permanence, hors
      // focus. Le test aurait annoncé « focus visible » en mesurant un
      // indicateur d'état de navigation. On compare donc l'apparence de
      // l'élément focalisé avec elle-même sans focus.
      const focus = await page.evaluate(() => {
        const active = document.activeElement as HTMLElement | null;
        if (active === null || active === document.body) {
          return null;
        }
        const lire = (): { outline: string; shadow: string } => {
          const style = getComputedStyle(active);
          return {
            outline: `${style.outlineStyle} ${style.outlineWidth} ${style.outlineColor}`,
            shadow: style.boxShadow,
          };
        };
        const avecFocus = lire();
        active.blur();
        const sansFocus = lire();
        active.focus();
        return {
          tag: active.tagName.toLowerCase(),
          avecFocus,
          sansFocus,
          change:
            avecFocus.outline !== sansFocus.outline || avecFocus.shadow !== sansFocus.shadow,
        };
      });

      expect(focus, `${route} : la première tabulation n'a focalisé aucun élément`).not.toBeNull();
      expect(
        focus?.change,
        `${route} : l'apparence de l'élément focalisé (${focus?.tag}) est IDENTIQUE avec et ` +
          `sans focus — outline « ${focus?.avecFocus.outline} », ombre ` +
          `« ${focus?.avecFocus.shadow} ». Une décoration permanente n'est pas un ` +
          'indicateur de focus — WCAG 2.4.7',
      ).toBe(true);
    });
  }
});

/**
 * WCAG 1.4.10 (Reflow) — NON CONFORME, mesuré et déclaré.
 *
 * L'enveloppe applicative porte `min-width: 1024px` (src/styles/global.css) :
 * c'est le plancher « desktop only » de la phase 1, écrit dans
 * `.claude/rules/frontend.md` et dans `manifests/performance-budgets.yaml`
 * (`beta_scope: desktop_only`, `mobile_ui_status: later`). À 200 % de zoom sur
 * une fenêtre de 1280 px, la largeur CSS tombe à 640 px, sous ce plancher : la
 * page défile alors horizontalement, ce que le critère 1.4.10 interdit.
 *
 * Ces tests ne prétendent donc PAS la conformité. Ils épinglent la réalité
 * mesurée pour qu'elle ne se dégrade pas en silence :
 *
 * 1. le débordement vaut EXACTEMENT le manque par rapport au plancher déclaré
 *    (1024 − largeur), sur chaque route. Un composant qui ajouterait sa propre
 *    largeur minimale ferait dépasser cette valeur et serait détecté ;
 * 2. aucun contenu n'est perdu : la page peut être défilée jusqu'au plancher,
 *    tout reste atteignable.
 *
 * L'écart est inscrit à `docs/99-status/DEBT.md`. Le lever suppose de retirer
 * le plancher et de refondre les mises en page larges — un chantier d'interface
 * entier, pas un correctif ; et la décision « desktop only » de la phase 1 le
 * précède.
 */
const PLANCHER_DESKTOP_PX = 1024;

test.describe('Accessibilité — zoom 200 % : plancher desktop mesuré (WCAG 1.4.10 non conforme)', () => {
  for (const route of ROUTES) {
    test(`${route} : le débordement à 200 % vaut exactement le manque au plancher`, async ({
      page,
    }) => {
      // 640×400 px CSS = 1280×800 physiques à 200 %. Le viewport est posé ICI,
      // par l'API page, et non par `test.use` : une sonde a montré que
      // l'option de contexte n'était pas appliquée dans ce projet, et un test
      // qui croit émuler quelque chose sans l'émuler ne prouve rien.
      const largeur = 640;
      await page.setViewportSize({ width: largeur, height: 400 });
      await page.goto(route);
      await expect(page.getByRole('main')).toBeVisible();

      const mesure = await page.evaluate(() => {
        const root = document.scrollingElement;
        if (root === null) {
          return null;
        }
        return { scrollWidth: root.scrollWidth, clientWidth: root.clientWidth };
      });
      expect(mesure).not.toBeNull();

      expect(
        mesure?.scrollWidth,
        `${route} : la largeur défilable est ${mesure?.scrollWidth} px au lieu du plancher ` +
          `déclaré ${PLANCHER_DESKTOP_PX} px — un composant impose sa propre largeur minimale`,
      ).toBe(PLANCHER_DESKTOP_PX);

      // L'assertion précédente — « le défilement atteint le bord droit » —
      // était une TAUTOLOGIE : `scrollTo` est borné par
      // `scrollWidth − clientWidth`, donc `scrollLeft + clientWidth` vaut
      // toujours `scrollWidth`, déjà contraint à 1024 ci-dessus. Elle ne
      // pouvait pas échouer et le rapport la présentait comme une mesure.
      //
      // Ce qui se mesure vraiment : le contenu du `main` reste-t-il ATTEIGNABLE
      // horizontalement ? On vérifie que le défilement de la page découvre bien
      // la largeur manquante, en comparant la position du bord droit du `main`
      // avant et après défilement.
      const avant = await page
        .getByRole('main')
        .evaluate((element) => element.getBoundingClientRect().right);
      await page.evaluate((cible) => {
        document.scrollingElement?.scrollTo({ left: cible, behavior: 'instant' });
      }, PLANCHER_DESKTOP_PX);
      const apres = await page
        .getByRole('main')
        .evaluate((element) => element.getBoundingClientRect().right);
      expect(
        Math.round(avant - apres),
        `${route} : le défilement horizontal ne déplace pas le contenu — il n'est pas ` +
          'atteignable, du contenu serait réellement perdu',
      ).toBe(PLANCHER_DESKTOP_PX - largeur);
    });
  }
});

test.describe('Accessibilité — mouvement réduit (WCAG 2.3.3)', () => {
  for (const route of ROUTES) {
    test(`${route} : aucune animation perceptible sous prefers-reduced-motion`, async ({
      page,
    }) => {
      // Émulation posée par l'API page. `test.use({ reducedMotion })` a été
      // essayé d'abord : une sonde a montré que
      // `matchMedia('(prefers-reduced-motion: reduce)').matches` restait
      // `false`. Le test aurait alors mesuré la page SANS préférence tout en
      // prétendant mesurer avec — exactement le genre de vert sans preuve que
      // le dépôt interdit.
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.goto(route);
      await expect(page.getByRole('main')).toBeVisible();

      // Anti-vacuité : si l'émulation ne prend pas, le test doit échouer là,
      // et non annoncer un vert.
      const emulationActive = await page.evaluate(
        () => matchMedia('(prefers-reduced-motion: reduce)').matches,
      );
      expect(emulationActive, "l'émulation prefers-reduced-motion n'a pas pris").toBe(true);

      const animes = await page.evaluate(() => {
        // 100 ms : en deçà, la transition n'est pas perçue comme un mouvement.
        // Au-delà, elle l'est, et le critère demande de la supprimer.
        const SEUIL_MS = 100;
        const duree = (valeur: string): number =>
          valeur
            .split(',')
            .map((part) => {
              const texte = part.trim();
              if (texte.endsWith('ms')) {
                return Number.parseFloat(texte);
              }
              if (texte.endsWith('s')) {
                return Number.parseFloat(texte) * 1000;
              }
              return 0;
            })
            .reduce((max, value) => (value > max ? value : max), 0);

        const coupables: string[] = [];
        for (const element of Array.from(document.querySelectorAll('*'))) {
          const style = getComputedStyle(element);
          const plusLong = Math.max(
            duree(style.animationDuration),
            duree(style.transitionDuration),
          );
          if (plusLong > SEUIL_MS) {
            coupables.push(
              `${element.tagName.toLowerCase()}.${element.className || '(sans classe)'} → ${plusLong}ms`,
            );
          }
        }
        // Bornée : un rapport d'échec ne doit pas déverser tout le DOM.
        return coupables.slice(0, 10);
      });

      expect(
        animes,
        `${route} : des animations de plus de 100 ms subsistent sous ` +
          'prefers-reduced-motion — WCAG 2.3.3',
      ).toEqual([]);
    });
  }
});
