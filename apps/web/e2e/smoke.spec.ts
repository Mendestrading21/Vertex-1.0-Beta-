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
  test('/sources-reports : les 14 capacités restent présentes, sans défilement horizontal de page', async ({
    page,
  }, testInfo) => {
    await page.goto('/sources-reports');
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
      path: screenshotPath('sources-reports-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/markets : carte sémantique conservée, table équivalente accessible, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/markets');
    await expect(page.locator('.vx-marketmap-canvas canvas')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES', { exact: true })).toBeVisible();
    // L'alternative tabulaire reste disponible sous la dominante (22 couverts).
    const table = page.getByRole('table', { name: 'Table équivalente de la carte des marchés' });
    await expect(table.locator('tbody tr')).toHaveCount(22);
    await expectNoHorizontalPageScroll(page);
    // Seul le conteneur de la table peut défiler horizontalement.
    const scrollMode = await page
      .locator('.vx-markets-table-scroll')
      .evaluate((element) => getComputedStyle(element).overflowX);
    expect(scrollMode).toBe('auto');
    await page.screenshot({
      path: screenshotPath('markets-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/options : chaîne complète, table dans son conteneur défilant, pas de scroll horizontal de page', async ({
    page,
  }, testInfo) => {
    await page.goto('/options/SYN-TECH-01');
    const table = page.getByRole('table', { name: /Chaîne d'options/ });
    await expect(table).toBeVisible();
    await expect(table.locator('tbody tr')).toHaveCount(12); // 12 strikes appariés
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES', { exact: true })).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    const scrollMode = await page
      .locator('.vx-chain-table-scroll')
      .evaluate((element) => getComputedStyle(element).overflowX);
    expect(scrollMode).toBe('auto');
    await page.screenshot({
      path: screenshotPath('options-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/analysis : chandeliers + attribution + table OHLCV présents, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/analysis/SYN-TECH-01');
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole('link', { name: 'TradingView' }).first()).toBeVisible();
    await expect(
      page.getByRole('table', { name: /Table OHLCV — équivalent exact des chandeliers/ }).locator('tbody tr'),
    ).toHaveCount(60);
    await expectNoHorizontalPageScroll(page);
    await page.screenshot({
      path: screenshotPath('analysis-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/simulator : composeur et action unique présents, honnêteté sauvegarde, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/simulator');
    await expect(page.getByRole('heading', { level: 1, name: 'Simulateur' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Calculer' })).toBeVisible();
    await expect(page.getByText(/NON_IMPLÉMENTÉ/)).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    await page.screenshot({
      path: screenshotPath('simulator-smoke', testInfo.project.name),
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
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES')).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    await page.screenshot({
      path: screenshotPath('today-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/portfolio : badge marques, tables dans leurs conteneurs défilants, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/portfolio');
    await expect(page.getByTestId('pf-marks-badge')).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole('heading', { name: 'Enregistrer une transaction (déjà exécutée hors Vertex)' }),
    ).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    const scrollMode = await page
      .locator('.vx-pf-table-scroll')
      .first()
      .evaluate((element) => getComputedStyle(element).overflowX);
    expect(scrollMode).toBe('auto');
    await page.screenshot({
      path: screenshotPath('portfolio-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/catalysts : timeline, file due et populations séparées visibles, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/catalysts');
    await expect(page.getByTestId('fu-due-list')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('fu-populations')).toContainText('USER_DECLARED');
    await expectNoHorizontalPageScroll(page);
    await page.screenshot({
      path: screenshotPath('catalysts-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/calendar : agenda complet et compteurs présents, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/calendar');
    await expect(page.getByTestId('cal-agenda')).toBeVisible({ timeout: 20_000 });
    // Aucune donnée masquée : chaque événement servi porte sa carte.
    const response = await page.request.get('/api/v1/calendar');
    const body = (await response.json()) as { agenda: { event_id: string }[] };
    await expect(page.locator('.vx-cal-event')).toHaveCount(body.agenda.length);
    await expect(page.getByTestId('cal-counters')).toBeVisible();
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES')).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    // Seul le conteneur des compteurs (et lui seul) peut défiler.
    const scrollMode = await page
      .locator('.vx-cal-counters .vx-cal-scroll')
      .evaluate((element) => getComputedStyle(element).overflowX);
    expect(scrollMode).toBe('auto');
    await page.screenshot({
      path: screenshotPath('calendar-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/opportunities : deux groupes séparés et tables dans leur conteneur, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/opportunities');
    await expect(page.getByTestId('opp-group-excluded')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('opp-group-qualified')).toBeVisible();
    await expect(page.getByTestId('opp-empty-qualified')).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    const scrollMode = await page
      .locator('.vx-opp-group[data-group="excluded"] .vx-matrix-scroll')
      .first()
      .evaluate((element) => getComputedStyle(element).overflowX);
    expect(scrollMode).toBe('auto');
    await page.screenshot({
      path: screenshotPath('opportunities-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/analysis (inspecteur IA) : bandeau B-05, affirmations et extraits externes séparés, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    // Un instrument EXPLICITE : sans dossier ouvert, l'inspecteur ne monte
    // aucun panneau — c'est la règle « aucune colonne morte ».
    await page.goto('/analysis/SYN-TECH-01');
    await expect(page.getByTestId('ai-provider-banner')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('ai-claims')).toBeVisible();
    await expect(page.getByTestId('ai-external')).toBeVisible();
    await expect(page.getByTestId('ai-note')).toContainText('NON_IMPLÉMENTÉ');
    await expectNoHorizontalPageScroll(page);
    await page.screenshot({
      path: screenshotPath('ai-inspector-smoke', testInfo.project.name),
      fullPage: true,
    });
  });

  test('/portfolio (module Performance) : bandeau population, métriques et table quotidienne présents, pas de scroll horizontal', async ({
    page,
  }, testInfo) => {
    await page.goto('/portfolio');
    await expect(page.getByTestId('perf-population')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('perf-metrics')).toBeVisible();
    await expectNoHorizontalPageScroll(page);
    await page.screenshot({
      path: screenshotPath('portfolio-performance-smoke', testInfo.project.name),
      fullPage: true,
    });
  });
});
