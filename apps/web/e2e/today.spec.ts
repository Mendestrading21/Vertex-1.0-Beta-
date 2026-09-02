/**
 * Parcours /today — file d'attention réelle (snapshot publié par le worker
 * sur les envelopes SYNTHETIC semées), panneau latéral au clavier, axe,
 * et état hors ligne simulé par interruption des routes /api.
 */
import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

test.describe("Page Aujourd'hui — AttentionQueue", () => {
  test('8 à 15 items SYNTHETIC badgés + bandeau population', async ({ page }) => {
    await page.goto('/today');
    const items = page.locator('.vx-queue-item');
    await expect(items.first()).toBeVisible();

    const count = await items.count();
    expect(count).toBeGreaterThanOrEqual(8);
    expect(count).toBeLessThanOrEqual(15);

    // Marqueur SYNTHÉTIQUE sur CHAQUE item + bandeau population global.
    await expect(page.locator('.vx-queue-item .vx-badge-synthetic')).toHaveCount(count);
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES')).toBeVisible();

    // Chaque ligne porte titre, sources, âge (badge de fraîcheur) et raisons.
    const firstItem = items.first();
    await expect(firstItem.locator('.vx-queue-title')).toContainText('[SYNTHETIC]');
    await expect(firstItem.locator('.vx-queue-sources')).not.toBeEmpty();
    await expect(firstItem.locator('.vx-freshness')).toBeVisible();
    const reasonsCount = await firstItem.locator('.vx-badge-reason').count();
    expect(reasonsCount).toBeGreaterThanOrEqual(1);
    expect(reasonsCount).toBeLessThanOrEqual(3);

    // Bandeau santé haut (réutilise la réponse capacités, minimal).
    await expect(page.locator('.vx-health-strip')).toContainText('Base locale');
    await expect(page.locator('.vx-health-strip')).toContainText('Disponible');
    await expect(page.locator('.vx-health-strip')).toContainText('Worker ·');
  });

  test('inspecteur accessible au clavier (Entrée, focus entrant, Échap)', async ({ page }) => {
    // LOT-13 : le détail n'est plus un dialogue modal, c'est un panneau de
    // l'inspecteur du shell. Le contenu et les propriétés clavier qui
    // comptent sont identiques ; ce qui change est asséré au test suivant.
    await page.goto('/today');
    const trigger = page.locator('.vx-queue-title').first();
    await expect(trigger).toBeVisible();

    // Activation au clavier uniquement.
    await trigger.focus();
    await page.keyboard.press('Enter');
    const panneau = page.locator('.vx-inspector-panel');
    await expect(panneau).toBeVisible();

    // Provenance complète : cluster, événements membres, droits.
    await expect(panneau.getByText('Cluster')).toBeVisible();
    await expect(panneau.getByText('Événements membres')).toBeVisible();
    await expect(panneau.getByText('Droits')).toBeVisible();
    await expect(panneau.getByText('SYNTHETIC', { exact: true })).toBeVisible();

    // CONSERVÉ : le focus entre dans le panneau à l'ouverture.
    const focusDansPanneau = await panneau.evaluate((element) =>
      element.contains(document.activeElement),
    );
    expect(focusDansPanneau).toBe(true);

    // CONSERVÉ : Échap referme et rend le focus au déclencheur. LOT-A3 :
    // l'inspecteur n'est jamais vide — il retombe sur la vérité du snapshot.
    await page.keyboard.press('Escape');
    await expect(page.locator('.vx-inspector-panel')).toHaveCount(1);
    await expect(page.locator('.vx-inspector-heading')).toHaveText('Inspecteur — Snapshot publié');
    await expect(page.getByTestId('snapshot-rail')).toBeVisible();
    const focusedIsTrigger = await trigger.evaluate(
      (element) => element === document.activeElement,
    );
    expect(focusedIsTrigger).toBe(true);
  });

  test('le panneau n’est PLUS modal et ne piège plus le clavier', async ({ page }) => {
    // Le piège de focus est CORRECT pour un dialogue modal, où le reste de la
    // page est inerte. Sur un panneau non modal il serait un DÉFAUT : il
    // enfermerait l'utilisateur hors de sa propre page. Cette assertion
    // remplace donc l'ancienne, et elle est plus forte — elle prouve que la
    // page reste opérable au clavier.
    await page.goto('/today');
    await page.locator('.vx-queue-title').first().focus();
    await page.keyboard.press('Enter');
    const panneau = page.locator('.vx-inspector-panel');
    await expect(panneau).toBeVisible();

    await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    await expect(page.locator('[aria-modal]')).toHaveCount(0);

    // Assez de tabulations pour SORTIR du panneau : le clavier n'y reboucle
    // pas. L'ancien test exigeait l'inverse, et c'était juste — pour un modal.
    let sorti = false;
    for (let index = 0; index < 12 && !sorti; index += 1) {
      await page.keyboard.press('Tab');
      sorti = !(await panneau.evaluate((element) => element.contains(document.activeElement)));
    }
    expect(sorti).toBe(true);
  });

  test('LOT-A3 : les ONZE modules de la planche §1, une dominante, absences motivées, inspecteur par défaut', async ({
    page,
  }) => {
    await page.goto('/today');
    await expect(page.locator('.vx-queue-item').first()).toBeVisible();
    const MODULES = [
      'regime',
      'global-market',
      'volatility',
      'next-catalyst',
      'source-health',
      'attention',
      'opportunities',
      'active-risks',
      'sectors',
      'manual-portfolio',
      'calendar',
    ];
    for (const module of MODULES) {
      await expect(page.locator(`[data-module="${module}"]`).first(), module).toBeVisible();
    }
    const dominantes = page.locator('.vx-main [data-rank="dominant"]');
    await expect(dominantes).toHaveCount(1);
    // Trois absences, motif fermé, aucun chiffre dans le corps (article 17).
    const badges = page.locator('.vx-absent-badge');
    await expect(badges).toHaveCount(3);
    for (const corps of await page.locator('.vx-absent-body').allTextContents()) {
      expect(corps).not.toMatch(/\d/);
    }
    // Les modules servis portent des valeurs SERVIES : breadth du snapshot Marchés.
    const overview = await (await page.request.get('/api/v1/markets/overview')).json();
    const breadth = overview.breadth?.value_pct as string;
    await expect(page.locator('[data-module="global-market"]')).toContainText(breadth.replace('.', ','));
    // Carte sectorielle : autant de puces que d'instruments couverts.
    const couverts = overview.sectors.flatMap((s: { tickers: unknown[] }) => s.tickers).length;
    await expect(page.locator('[data-module="sectors"] .vx-sector-chip')).toHaveCount(couverts);
    // Inspecteur par défaut : la vérité du snapshot, jamais une colonne vide.
    await expect(page.locator('.vx-inspector-heading')).toHaveText('Inspecteur — Snapshot publié');
    await expect(page.getByTestId('snapshot-rail')).toBeVisible();
    // La file est bornée : région défilante atteignable au clavier.
    await expect(page.locator('.vx-queue-scroll[tabindex="0"]')).toBeVisible();
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/today');
    await expect(page.locator('.vx-queue-item').first()).toBeVisible();
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('today', testInfo.project.name),
      fullPage: true,
    });
  });

  test("hors ligne simulé (routes /api interrompues) → état offline honnête", async ({
    page,
  }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/today');
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(boundary).toContainText("L'API locale est injoignable");
    // Aucune file fabriquée en mode hors ligne.
    await expect(page.locator('.vx-queue-item')).toHaveCount(0);
  });
});
