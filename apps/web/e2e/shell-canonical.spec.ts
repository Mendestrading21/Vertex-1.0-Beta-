/**
 * Conformité du shell à l'anatomie canonique.
 *
 * Source unique : `.claude/skills/vertex-titanium-ledger/references/canonical-visual.md`
 * et la capture `assets/vertex-dashboard-canonical.png`, dont l'empreinte
 * SHA-256 est vérifiée par `scripts/audit_titanium_ledger.py`.
 *
 * Ces tests mesurent des styles CALCULÉS dans un vrai navigateur, parce que
 * les écarts corrigés au LOT-09 étaient tous invisibles à jsdom : une plaque
 * de fond, une pastille par icône, une barre latérale au lieu d'une capsule
 * et une tuile dégradée sous la marque. Aucun des 399 tests existants ne les
 * voyait.
 *
 * Ils portent sur des PROPRIÉTÉS NOMMÉES par le contrat canonique (« intégré
 * au fond », « seul l'item actif », « aucun halo néon permanent »), pas sur
 * des valeurs de pixels : une recomposition ultérieure reste libre tant
 * qu'elle respecte ces propriétés.
 */
import AxeBuilder from '@axe-core/playwright';

import { expect, test } from './fixtures.ts';

/**
 * Surface de fond calculée, normalisée : aucune surface → null.
 *
 * Lit `background-color` ET `background-image`. Un dégradé ne pose PAS de
 * `background-color` : ne mesurer que la couleur laisserait passer une plaque
 * dégradée, ce qui est précisément l'écart trouvé au LOT-09 sur `.vx-rail`.
 */
async function backgroundOf(
  page: import('@playwright/test').Page,
  selector: string,
): Promise<string | null> {
  const surface = await page
    .locator(selector)
    .first()
    .evaluate((element) => {
      const style = getComputedStyle(element);
      return { color: style.backgroundColor, image: style.backgroundImage };
    });
  const couleurAbsente = surface.color === 'rgba(0, 0, 0, 0)' || surface.color === 'transparent';
  const imageAbsente = surface.image === 'none';
  return couleurAbsente && imageAbsente ? null : `${surface.color} | ${surface.image}`;
}

test.describe('Shell — anatomie canonique', () => {
  test('point 2 : le rail est intégré au fond, sans plaque flottante', async ({ page }) => {
    await page.goto('/today');
    const rail = page.locator('.vx-rail');
    await expect(rail).toBeVisible();

    // « rail gauche fin et intégré au fond, sans grande plaque flottante » :
    // ni surface propre, ni bordure de séparation, ni ombre de panneau.
    expect(await backgroundOf(page, '.vx-rail')).toBeNull();
    const chrome = await rail.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        borderRightWidth: style.borderRightWidth,
        boxShadow: style.boxShadow,
      };
    });
    expect(chrome.borderRightWidth).toBe('0px');
    expect(chrome.boxShadow).toBe('none');
  });

  test('point 3 : SEUL l’item actif porte la capsule ambre et l’icône ambre', async ({ page }) => {
    await page.goto('/today');
    const links = page.locator('.vx-rail-link');
    const total = await links.count();
    expect(total).toBeGreaterThan(1);

    const remplis: string[] = [];
    for (let index = 0; index < total; index += 1) {
      const link = links.nth(index);
      const fond = await link.evaluate((element) => {
        const style = getComputedStyle(element);
        return style.backgroundColor !== 'rgba(0, 0, 0, 0)' || style.backgroundImage !== 'none';
      });
      if (fond) {
        remplis.push((await link.getAttribute('aria-label')) ?? '?');
      }
      // Aucune pastille autour d'une icône, active ou non : la capture n'en
      // montre aucune. La seule surface colorée du rail est la capsule.
      const pastille = await link
        .locator('.vx-rail-link-short')
        .evaluate((element) => getComputedStyle(element).backgroundColor);
      expect(pastille).toBe('rgba(0, 0, 0, 0)');
    }

    // Exactement un item rempli, et c'est celui que porte aria-current.
    expect(remplis).toEqual(["Aujourd'hui"]);
    await expect(page.locator('.vx-rail-link[aria-current="page"]')).toHaveCount(1);

    // L'icône de l'item actif hérite de la teinte de la capsule : la couleur
    // du lien actif diffère de celle d'un lien inactif.
    const actif = await page
      .locator('.vx-rail-link[aria-current="page"]')
      .evaluate((element) => getComputedStyle(element).color);
    const inactif = await page
      .locator('.vx-rail-link:not([aria-current="page"])')
      .first()
      .evaluate((element) => getComputedStyle(element).color);
    expect(actif).not.toBe(inactif);
  });

  test('point 3 bis : l’état actif ne repose pas sur la seule couleur', async ({ page }) => {
    await page.goto('/today');
    const actif = page.locator('.vx-rail-link[aria-current="page"]');
    const inactif = page.locator('.vx-rail-link:not([aria-current="page"])').first();

    // Forme : une capsule APPARAÎT là où il n'y avait aucune surface.
    expect(await backgroundOf(page, '.vx-rail-link[aria-current="page"]')).not.toBeNull();
    // « une capsule ambre TRANSLUCIDE » : un aplat, jamais un dégradé, et
    // aucune barre latérale déguisée en ombre interne.
    const capsule = await actif.evaluate((element) => {
      const style = getComputedStyle(element);
      return { image: style.backgroundImage, shadow: style.boxShadow };
    });
    expect(capsule.image).toBe('none');
    expect(capsule.shadow).toBe('none');
    // Graisse : vecteur textuel indépendant de la couleur.
    const graisseActive = await actif.evaluate((element) => getComputedStyle(element).fontWeight);
    const graisseInactive = await inactif.evaluate(
      (element) => getComputedStyle(element).fontWeight,
    );
    expect(Number(graisseActive)).toBeGreaterThan(Number(graisseInactive));
  });

  test('points 2 et 6 : la densité canonique, mesurée en pixels', async ({ page }) => {
    /**
     * V2 — LA DENSITÉ. `references/canonical-visual.md`, « Densité et
     * géométrie », donne trois nombres et un interdit :
     *
     *   « Navigation visuelle : environ 120 px »
     *   « Gouttières principales : 12–16 px »
     *   « Inspecteur : 300–340 px selon viewport »
     *   dérive interdite : « rail gauche large, flottant ou très arrondi »
     *
     * MESURE AVANT CORRECTIF, à 1600×1000 : rail **248 px** et marge de travail
     * **40 / 32 / 48 px**. Le rail mangeait donc 128 px de largeur utile sur
     * CHACUNE des onze destinations, et la marge valait deux à trois fois la
     * gouttière canonique. Aucune porte ne mesurait ces trois nombres : le
     * contrat les écrivait, le code s'en éloignait, et rien ne le disait.
     *
     * LA BANDE ACCEPTÉE, ET POURQUOI ELLE N'EST PAS « 120 » AU PIXEL. Les
     * libellés français de Vertex sont plus longs que ceux de la capture :
     * « Sources & Rapports » demande 192 px de largeur intrinsèque, le
     * cartouche 154 px, la tête 126 px. Un rail de 120 px stricts les
     * TRONQUERAIT — et un libellé de navigation tronqué est pire qu'un rail de
     * 16 px trop large. La bande retenue est donc 120–140 px : « environ
     * 120 px » au sens du contrat, sans rien couper.
     */
    for (const largeurFenetre of [1280, 1440, 1600]) {
      await page.setViewportSize({ width: largeurFenetre, height: 900 });
      await page.goto('/today');
      await expect(page.getByRole('main')).toBeVisible();

      const mesure = await page.evaluate(() => {
        const rail = document.querySelector('.vx-rail') as HTMLElement;
        const main = document.querySelector('.vx-main') as HTMLElement;
        const style = getComputedStyle(main);
        return {
          rail: Math.round(rail.getBoundingClientRect().width),
          hautMain: Number.parseFloat(style.paddingTop),
          coteMain: Number.parseFloat(style.paddingLeft),
          // Débordement horizontal d'un libellé : le seul vrai risque de la
          // compression. `scrollWidth > clientWidth` sur le rail le dit.
          railDeborde: rail.scrollWidth > rail.clientWidth + 1,
        };
      });

      expect(
        mesure.rail,
        `rail ${mesure.rail} px à ${largeurFenetre} — le contrat dit « environ 120 px »`,
      ).toBeGreaterThanOrEqual(120);
      expect(mesure.rail).toBeLessThanOrEqual(140);

      expect(
        mesure.coteMain,
        `marge latérale ${mesure.coteMain} px à ${largeurFenetre} — gouttière canonique 12–16 px`,
      ).toBeLessThanOrEqual(20);
      expect(mesure.hautMain).toBeLessThanOrEqual(20);

      // Rien n'est coupé. C'est la contrepartie obligatoire de la compression :
      // sans cette assertion, le test récompenserait un rail étroit qui
      // tronque ses libellés.
      expect(mesure.railDeborde, `le rail tronque son contenu à ${largeurFenetre}`).toBe(false);

      // ET RIEN N'EST COUPÉ AU MILIEU D'UN MOT. La première version de ce lot
      // autorisait `overflow-wrap: anywhere` : le rail ne débordait pas, le
      // test passait, et la capture montrait « Aujourd / 'hui »,
      // « Opportu / nités », « Portefeu / ille ». Un libellé sans espace n'a
      // aucun point de coupure légitime : il doit tenir sur une ligne.
      const coupesDansUnMot = await page.evaluate(() => {
        const liens = Array.from(document.querySelectorAll('.vx-rail-link')) as HTMLElement[];
        return liens
          .map((lien) => {
            const etiquette = lien.querySelector('span:not(.vx-rail-link-short)');
            const texte = (etiquette?.textContent ?? '').trim();
            if (texte === '' || texte.includes(' ')) {
              return null;
            }
            const boite = (etiquette as HTMLElement).getBoundingClientRect();
            const hauteurLigne = Number.parseFloat(
              getComputedStyle(etiquette as HTMLElement).lineHeight,
            );
            // Plus d'une ligne pour un mot unique = coupure interne.
            return boite.height > hauteurLigne * 1.5 ? texte : null;
          })
          .filter((valeur): valeur is string => valeur !== null);
      });
      expect(
        coupesDansUnMot,
        `libellés coupés au milieu d’un mot à ${largeurFenetre} : ${coupesDansUnMot.join(', ')}`,
      ).toEqual([]);
    }
  });

  test('une seule lumière dominante par écran, sur les douze destinations', async ({ page }) => {
    /**
     * « Une lumière dominante maximum par carte, deux par écran hors
     * rouge/vert. » — `references/canonical-visual.md`.
     *
     * POURQUOI CE TEST EXISTE, ET POURQUOI IL ATTEND UN TÉMOIN DE CONTENU.
     * La porte statique `one-dominant-per-page.test.ts` compte les
     * déclarations dans le source ; elle ne peut pas voir ce qui est
     * RÉELLEMENT rendu. Ce test-ci le voit — à une condition apprise à ses
     * dépens : une sonde qui attend seulement `main` visible mesure le
     * SQUELETTE DE CHARGEMENT (`.vx-dsb-skeleton`) et rapporte zéro dominante
     * partout. C'est exactement l'erreur qui m'a fait annoncer « dix pages sur
     * onze sans dominante » alors que la règle fonctionnait. Chaque route
     * attend donc un témoin de son contenu réel.
     *
     * ZÉRO EST PERMIS, DEUX NE L'EST PAS. Le contrat dit « maximum », et le
     * Simulateur au repos n'a rien à faire dominer : sa carte de résultat
     * n'existe qu'après un calcul. Un formulaire sans dominante est honnête ;
     * deux dominantes ne le sont jamais.
     */
    const ROUTES: ReadonlyArray<readonly [string, string]> = [
      ['/today', '.vx-today-primary'],
      ['/markets', '.vx-chartframe'],
      ['/opportunities', '.vx-opp-group'],
      ['/analysis/SYN-TECH-01', '.vx-chartframe'],
      ['/options/SYN-TECH-01', '.vx-chartframe'],
      ['/simulator', '.vx-sim-composer'],
      ['/charts/SYN-TECH-01', '.vx-chartframe'],
      ['/portfolio', '.vx-pf-summary'],
      ['/risks', '.vx-riskmatrix'],
      ['/catalysts', '.vx-fu-queue'],
      ['/calendar', '.vx-cal-agenda'],
      ['/sources-reports', '.vx-health'],
    ];

    for (const [route, temoin] of ROUTES) {
      await page.goto(route);
      await expect(page.locator(temoin).first()).toBeVisible({ timeout: 15000 });
      const porteurs = await page.evaluate(() => {
        const main = document.querySelector('.vx-main');
        if (main === null) {
          return null;
        }
        return Array.from(main.querySelectorAll('[data-rank="dominant"]')).map((element) =>
          ((element as HTMLElement).className || element.tagName).toString(),
        );
      });
      expect(porteurs, `${route} : aucun \`.vx-main\``).not.toBeNull();
      expect(
        porteurs?.length,
        `${route} porte ${porteurs?.length} dominantes : ${porteurs?.join(', ')}`,
      ).toBeLessThanOrEqual(1);
    }
  });

  test('point 1 : la marque est un glyphe facetté argent, pas une tuile', async ({ page }) => {
    await page.goto('/today');
    const marque = page.locator('.vx-brand-mark');
    await expect(marque).toBeVisible();

    // « monogramme facetté argent/titane » + « aucun halo néon permanent » :
    // aucune tuile, aucun dégradé, aucune ombre portée sous la marque.
    const style = await marque.evaluate((element) => {
      const computed = getComputedStyle(element);
      return {
        backgroundColor: computed.backgroundColor,
        backgroundImage: computed.backgroundImage,
        boxShadow: computed.boxShadow,
      };
    });
    expect(style.backgroundColor).toBe('rgba(0, 0, 0, 0)');
    expect(style.backgroundImage).toBe('none');
    expect(style.boxShadow).toBe('none');

    // Le glyphe est rendu par un masque héritant de `currentColor` : il reste
    // donc une seule teinte, jamais un aplat multicolore.
    const facette = page.locator('.vx-brand-facet');
    await expect(facette).toBeVisible();
    const glyphe = await facette.evaluate((element) => {
      const computed = getComputedStyle(element);
      return {
        backgroundColor: computed.backgroundColor,
        maskImage: computed.maskImage,
        webkitMaskImage: computed.webkitMaskImage,
      };
    });
    expect(glyphe.backgroundColor).not.toBe('rgba(0, 0, 0, 0)');

    // LE MASQUE EST RÉELLEMENT APPLIQUÉ. Sans cette assertion, une déclaration
    // `mask-image` invalide est calculée à `none` SANS ERREUR : le carré se
    // remplit intégralement de `currentcolor` et la « marque facettée » devient
    // un pavé plein. C'est exactement ce qui se passait, et aucune assertion de
    // couleur ne pouvait le voir.
    expect(glyphe.maskImage).not.toBe('none');
    expect(glyphe.webkitMaskImage).not.toBe('none');
  });

  test('point 7 : le cartouche d’édition est en bas à gauche, dans le rail', async ({ page }) => {
    await page.goto('/today');
    const cartouche = page.locator('.vx-rail .vx-edition-cartouche');
    await expect(cartouche).toBeVisible();
    await expect(cartouche).toHaveText('Vertex 1.0 Beta');

    // Il n'est plus en haut à droite : cet emplacement revient au badge de
    // mode, à la cloche et à la fraîcheur (point 5), non encore livrés.
    await expect(page.locator('.vx-contextbar .vx-edition-cartouche')).toHaveCount(0);

    // « en bas à gauche » : dans la moitié basse du rail, et à gauche de la
    // zone de travail.
    const boiteCartouche = await cartouche.boundingBox();
    const boiteRail = await page.locator('.vx-rail').boundingBox();
    const boiteMain = await page.locator('main').boundingBox();
    expect(boiteCartouche).not.toBeNull();
    expect(boiteRail).not.toBeNull();
    expect(boiteMain).not.toBeNull();
    expect(boiteCartouche!.y).toBeGreaterThan(boiteRail!.y + boiteRail!.height / 2);
    expect(boiteCartouche!.x + boiteCartouche!.width).toBeLessThanOrEqual(boiteMain!.x);
  });

  test('point 4 : le ticker est horizontal, en haut, dans une surface continue', async ({
    page,
  }) => {
    // « ticker horizontal compact en haut, dans une surface vitrée continue ».
    await page.goto('/today');
    const ticker = page.locator('.vx-ticker');
    await expect(ticker).toBeVisible();

    // EN HAUT : sous la barre de contexte, au-dessus de la zone de travail.
    const boiteTicker = (await ticker.boundingBox())!;
    const boiteBarre = (await page.locator('.vx-contextbar').boundingBox())!;
    const boiteMain = (await page.locator('main').boundingBox())!;
    expect(boiteTicker.y).toBeGreaterThanOrEqual(boiteBarre.y + boiteBarre.height - 1);
    expect(boiteTicker.y + boiteTicker.height).toBeLessThanOrEqual(boiteMain.y + 1);

    // HORIZONTAL et COMPACT : plus large que haut, d'un ordre de grandeur, et
    // sous la hauteur de la barre de contexte qu'il prolonge.
    expect(boiteTicker.width).toBeGreaterThan(boiteTicker.height * 10);
    expect(boiteTicker.height).toBeLessThan(boiteBarre.height);

    // CONTINUE : aucune arête entre la barre et le ticker. C'est l'enveloppe
    // `.vx-topbar` qui porte l'unique arête basse du bandeau.
    const arete = await page
      .locator('.vx-contextbar')
      .evaluate((element) => getComputedStyle(element).borderBottomWidth);
    expect(arete).toBe('0px');
    const areteBandeau = await page
      .locator('.vx-topbar')
      .evaluate((element) => getComputedStyle(element).borderBottomWidth);
    expect(areteBandeau).not.toBe('0px');

    // AUCUN MOUVEMENT : « aucun ticker animé faisant croire à une donnée live ».
    const anime = await ticker.evaluate((element) => {
      const style = getComputedStyle(element);
      const liste = element.querySelector('.vx-ticker-list');
      const listeStyle = liste === null ? null : getComputedStyle(liste);
      return {
        nom: style.animationName,
        nomListe: listeStyle?.animationName ?? 'none',
        transition: listeStyle?.transitionProperty ?? 'none',
      };
    });
    expect(anime.nom).toBe('none');
    expect(anime.nomListe).toBe('none');

    // La bande porte SA nature et SA fraîcheur — pas le coin haut-droit, qui
    // leur donnerait une portée applicative qu'aucune source ne publie.
    await expect(ticker.locator('.vx-ticker-nature')).toBeVisible();
    await expect(ticker.locator('.vx-ticker-freshness')).toBeVisible();
    await expect(page.locator('.vx-contextbar .vx-ticker-nature')).toHaveCount(0);

    // La région défilante est atteignable au clavier (axe
    // `scrollable-region-focusable`, impact « serious »).
    await expect(ticker.locator('.vx-ticker-list')).toHaveAttribute('tabindex', '0');
  });

  test('point 5 : l’identité de l’instantané est à DROITE, et son heure est celle servie', async ({
    page,
  }) => {
    // LOT-A1. Les planches posent nature, fraîcheur et heure UTC à
    // l'extrémité droite de la bande. Ce test mesure les DEUX moitiés de la
    // promesse : la position réelle à l'écran, et le fait que l'heure vienne
    // du serveur — les tests unitaires ne peuvent prouver ni l'une ni l'autre.
    await page.goto('/today');
    const ticker = page.locator('.vx-ticker');
    await expect(ticker).toHaveAttribute('data-mode', 'values');

    const meta = ticker.locator('.vx-ticker-meta');
    const liste = ticker.locator('.vx-ticker-list');
    await expect(meta).toBeVisible();

    const boiteMeta = (await meta.boundingBox())!;
    const boiteListe = (await liste.boundingBox())!;
    const boiteBande = (await ticker.boundingBox())!;

    // À DROITE des cours, et collé au bord droit de la bande : c'est la
    // planche. Une tolérance de 40 px couvre la gouttière et le padding, pas
    // un bloc qui aurait glissé au milieu.
    expect(boiteMeta.x).toBeGreaterThan(boiteListe.x);

    // UNE SEULE RANGÉE. « Ticker horizontal COMPACT » : les cours et le bloc
    // d'identité partagent la même bande. Cette assertion manquait, et une
    // première version du placement de grille a bel et bien produit DEUX
    // lignes — les cours renvoyés sous le bloc de droite et tronqués — sans
    // qu'aucun test ne bronche. C'est la capture qui l'a montré.
    const centre = (boite: { y: number; height: number }) => boite.y + boite.height / 2;
    expect(Math.abs(centre(boiteMeta) - centre(boiteListe))).toBeLessThan(6);
    const bordDroitBande = boiteBande.x + boiteBande.width;
    const bordDroitMeta = boiteMeta.x + boiteMeta.width;
    expect(bordDroitBande - bordDroitMeta).toBeLessThan(40);

    // L'ORDRE DU DOM, lui, n'a pas bougé : l'identité reste AVANT les cours
    // dans le document, donc lue avant eux par un lecteur d'écran. C'est ce
    // que le placement de grille permet et qu'un déplacement du DOM aurait
    // détruit.
    const precede = await ticker.evaluate((bande) => {
      const bloc = bande.querySelector('.vx-ticker-meta');
      const cours = bande.querySelector('.vx-ticker-list');
      if (bloc === null || cours === null) {
        return null;
      }
      // eslint-disable-next-line no-bitwise
      return (bloc.compareDocumentPosition(cours) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
    });
    expect(precede).toBe(true);

    // L'HEURE EST CELLE DE L'INSTANTANÉ. La preuve tient à la comparaison
    // avec ce que l'API a réellement servi : une horloge murale dériverait de
    // cette valeur dès la seconde suivante.
    const horloge = ticker.locator('[data-testid="ticker-clock"]');
    await expect(horloge).toBeVisible();
    const servi = await horloge.getAttribute('datetime');
    expect(servi).not.toBeNull();
    const attendu = await page.evaluate(async () => {
      const reponse = await fetch('/api/v1/markets/overview', { credentials: 'include' });
      const corps = (await reponse.json()) as { as_of: string | null };
      return corps.as_of;
    });
    expect(servi).toBe(attendu);

    // Et le texte rendu est bien cet instant-là, converti en UTC.
    const rendu = (await horloge.textContent())?.trim() ?? '';
    expect(rendu).toMatch(/^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} UTC$/);
    const instant = new Date(servi!);
    const deux = (valeur: number) => String(valeur).padStart(2, '0');
    expect(rendu).toBe(
      `${deux(instant.getUTCDate())}/${deux(instant.getUTCMonth() + 1)}/` +
        `${instant.getUTCFullYear()} ${deux(instant.getUTCHours())}:` +
        `${deux(instant.getUTCMinutes())} UTC`,
    );
  });

  test('point 6 : l’inspecteur défilant est atteignable au clavier PAR LUI-MÊME', async ({
    page,
  }) => {
    /**
     * DÉFAUT ANTÉRIEUR AU LOT-A1, trouvé par la campagne et confirmé identique
     * sur la baseline. `.vx-inspector` porte `max-height: 100vh;
     * overflow-y: auto` : dès que son contenu dépasse — mesuré à 6367 px pour
     * 900 px visibles sur `/analysis/SYN-TECH-01` — c'est une RÉGION
     * DÉFILANTE, et une région défilante inatteignable au clavier est la
     * violation axe `scrollable-region-focusable`, impact « serious », sur un
     * seuil déclaré à zéro. Même faute que `.vx-ticker-list` au LOT-14.
     *
     * CE QUE LA MESURE A MONTRÉ, ET QUI CHANGE LE DIAGNOSTIC. La règle passait
     * déjà, mais par ACCIDENT : le panneau monté contient 22 éléments
     * focalisables (les liens de citation), et axe s'en contente. Entre
     * l'instant où le nœud devient défilant et celui où ces liens existent, la
     * région était inatteignable. C'est une COURSE, pas un état stable — d'où
     * une campagne verte pendant des sessions, puis rouge sur un seul des
     * trois viewports.
     *
     * CE QUE CE TEST VÉRIFIE DONC, et c'est plus fort que la règle axe : la
     * joignabilité ne dépend PAS de ce que la page a eu le temps de rendre.
     * Le nœud est atteignable par son propre `tabindex`, contenu vide ou non.
     * Un test qui n'aurait mesuré qu'axe serait resté vert avant le correctif
     * — vérifié : il l'était.
     */
    await page.setViewportSize({ width: 1440, height: 420 });
    await page.goto('/analysis/SYN-TECH-01');
    await expect(page.getByRole('main')).toBeVisible();
    const inspecteur = page.locator('#vx-inspector-slot');
    await expect(inspecteur).toBeVisible();

    // Le dépassement est bien réel : sans lui, le test ne prouverait rien.
    const deborde = await inspecteur.evaluate(
      (noeud) => noeud.scrollHeight > noeud.clientHeight + 1,
    );
    expect(deborde, 'la fenêtre courte devait faire déborder l’inspecteur').toBe(true);

    // L'INVARIANT : le nœud lui-même est un point d'arrêt clavier. C'est ce
    // qui retire la joignabilité du domaine du hasard.
    await expect(inspecteur).toHaveAttribute('tabindex', '0');

    // Et le clavier y arrive vraiment, pas seulement l'attribut.
    await inspecteur.focus();
    await expect(inspecteur).toBeFocused();

    const resultats = await new AxeBuilder({ page })
      .withRules(['scrollable-region-focusable'])
      .analyze();
    expect(
      resultats.violations.flatMap((violation) => violation.nodes.map((n) => n.target)),
      'une région défilante doit être atteignable au clavier',
    ).toEqual([]);
  });

  test('point 6 : l’inspecteur n’occupe la grille que si une page le remplit', async ({
    page,
  }) => {
    // « zone de travail dense avec une dominante centrale et un inspecteur
    // contextuel à droite ». L'emplacement existe dans le shell, mais une
    // colonne vide en permanence serait de la chrome décorative : il ne
    // prend de place que rempli.
    await page.goto('/today');
    const inspecteur = page.locator('#vx-inspector-slot');
    await expect(inspecteur).toBeHidden();

    // Sur Catalyseurs, il reste masqué tant qu'aucun élément n'est ouvert.
    await page.goto('/catalysts');
    await expect(page.getByTestId('cat-unlinked')).toBeVisible();
    await expect(inspecteur).toBeHidden();

    const premier = page.locator('.vx-cat-open').first();
    if ((await page.locator('.vx-cat-item').count()) === 0) {
      // Aucun catalyseur servi : l'inspecteur DOIT rester masqué, et c'est
      // exactement la propriété testée.
      return;
    }
    await premier.click();
    await expect(inspecteur).toBeVisible();

    // Largeur canonique : 300–340 px selon viewport.
    const boite = await inspecteur.boundingBox();
    expect(boite).not.toBeNull();
    expect(boite!.width).toBeGreaterThanOrEqual(300);
    expect(boite!.width).toBeLessThanOrEqual(340);

    // « à droite » : au-delà du bord droit de la dominante.
    const dominante = await page.locator('main').boundingBox();
    expect(boite!.x).toBeGreaterThanOrEqual(dominante!.x + dominante!.width - 1);

    // Changer de destination libère l'emplacement : aucun panneau ne survit
    // à la page qui l'a monté.
    await page.goto('/today');
    await expect(inspecteur).toBeHidden();
  });

  test('le shell reste identique d’une destination à l’autre', async ({ page }) => {
    // « Le shell reste identique sur les douze destinations. Seuls l'item
    // actif, le titre, la dominante, les modules secondaires et l'inspecteur
    // changent. » Le cartouche et la marque ne bougent donc pas.
    for (const route of ['/today', '/portfolio', '/sources-reports']) {
      await page.goto(route);
      await expect(page.locator('.vx-rail .vx-edition-cartouche')).toBeVisible();
      await expect(page.locator('.vx-brand-mark')).toBeVisible();
      await expect(page.locator('.vx-ticker')).toBeVisible();
      await expect(page.locator('.vx-rail-link[aria-current="page"]')).toHaveCount(1);
    }
  });
});
