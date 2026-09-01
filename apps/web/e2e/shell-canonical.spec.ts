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
