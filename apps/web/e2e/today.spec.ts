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
    await expect(page.getByText('DONNÉES SYNTHÉTIQUES')).toBeVisible();

    // Chaque ligne porte titre, sources, âge (badge de fraîcheur) et raisons.
    const firstItem = items.first();
    await expect(firstItem.locator('.vx-queue-title')).toContainText('[SYNTHETIC]');
    await expect(firstItem.locator('.vx-queue-sources')).not.toBeEmpty();
    await expect(firstItem.locator('.vx-freshness')).toBeVisible();
    const reasonsCount = await firstItem.locator('.vx-badge-reason').count();
    expect(reasonsCount).toBeGreaterThanOrEqual(1);
    expect(reasonsCount).toBeLessThanOrEqual(3);

    // Bandeau santé haut (réutilise la réponse capacités, minimal).
    await expect(page.locator('.vx-health-strip')).toContainText('Base : ok');
  });

  test('panneau latéral accessible au clavier (Entrée, piège de focus, Échap)', async ({
    page,
  }) => {
    await page.goto('/today');
    const trigger = page.locator('.vx-queue-title').first();
    await expect(trigger).toBeVisible();

    // Activation au clavier uniquement.
    await trigger.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');

    // Provenance complète : cluster, événements membres, droits.
    await expect(dialog.getByText('Cluster')).toBeVisible();
    await expect(dialog.getByText('Événements membres')).toBeVisible();
    await expect(dialog.getByText('Droits')).toBeVisible();
    await expect(dialog.getByText('SYNTHETIC', { exact: true })).toBeVisible();

    // Piège de focus : plusieurs tabulations restent dans le panneau.
    for (let index = 0; index < 6; index += 1) {
      await page.keyboard.press('Tab');
      const inDialog = await dialog.evaluate(
        (element) => element.contains(document.activeElement),
      );
      expect(inDialog).toBe(true);
    }

    // Échap referme et rend le focus au déclencheur.
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    const focusedIsTrigger = await trigger.evaluate(
      (element) => element === document.activeElement,
    );
    expect(focusedIsTrigger).toBe(true);
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
