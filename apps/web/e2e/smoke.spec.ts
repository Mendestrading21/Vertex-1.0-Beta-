/**
 * Contrôle de dégradation laptop 1024×768 (ni breakpoint mobile, ni cible de
 * release) : aucune donnée masquée, aucun défilement horizontal de page —
 * les contenus larges défilent dans leur propre conteneur.
 */
import { expect, screenshotPath, test } from './fixtures.ts';

async function expectNoHorizontalPageScroll(page: import('@playwright/test').Page): Promise<void> {
  const overflow = await page.evaluate(() => {
    const root = document.scrollingElement;
    if (root === null) {
      return 0;
    }
    return root.scrollWidth - root.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(0);
}

test.describe('Dégradation 1024×768', () => {
  test('/system : les 14 capacités restent présentes, sans défilement horizontal de page', async ({
    page,
  }, testInfo) => {
    await page.goto('/system');
    const table = page.getByRole('table');
    await expect(table).toBeVisible();
    // Aucune donnée masquée : les 14 lignes et 6 colonnes existent toutes.
    await expect(table.locator('tbody tr')).toHaveCount(14);
    await expect(table.locator('thead th')).toHaveCount(6);
    await expectNoHorizontalPageScroll(page);
    // Le conteneur de la table (et lui seul) peut défiler horizontalement.
    const scrollMode = await page
      .locator('.vx-matrix-scroll')
      .evaluate((element) => getComputedStyle(element).overflowX);
    expect(scrollMode).toBe('auto');
    await page.screenshot({
      path: screenshotPath('system-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/today : file complète visible, bandeau SYNTHETIC non masqué, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/today');
    const items = page.locator('.vx-queue-item');
    await expect(items.first()).toBeVisible();
    const count = await items.count();
    expect(count).toBeGreaterThanOrEqual(8);
    // Le marqueur SYNTHÉTIQUE de chaque item reste rendu (jamais masqué).
    await expect(page.locator('.vx-queue-item .vx-badge-synthetic')).toHaveCount(count);
    await expect(page.getByText('DONNÉES SYNTHÉTIQUES')).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    await page.screenshot({
      path: screenshotPath('today-smoke', testInfo.project.name),
      fullPage: true,
    });
  });
});
