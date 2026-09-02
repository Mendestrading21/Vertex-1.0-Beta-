/**
 * Parcours /markets — carte des marchés réelle (snapshot markets_overview
 * publié par le worker sur les quotes SYNTHETIC semées), table équivalente
 * vérifiée VALEUR PAR VALEUR contre la réponse API, axe, et état hors ligne
 * simulé par interruption des routes /api.
 */
import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface ApiTicker {
  ticker: string;
  last_close: string;
  currency: string | null;
  return_1d_pct: string;
  weight_in_sector_pct: string;
  weight_global_pct: string;
  quality: string;
}

interface ApiOverview {
  state: string;
  population: string | null;
  data_state: string | null;
  conclusion: string | null;
  sectors: { sector: string; label: string; tickers: ApiTicker[] }[];
  breadth: { status: string; value_pct: string | null; coverage_pct: string } | null;
  coverage: { expected: number; covered: number; discarded: number } | null;
}

function fr(value: string): string {
  return value.replace('.', ',');
}

test.describe('Page Marchés — MarketMap + table équivalente + breadth', () => {
  test('treemap rendue (canvas) et table équivalente aux valeurs API exactes', async ({
    page,
  }) => {
    const apiResponse = await page.request.get('/api/v1/markets/overview');
    expect(apiResponse.ok()).toBe(true);
    const overview = (await apiResponse.json()) as ApiOverview;
    expect(overview.state).toBe('ok');
    expect(overview.population).toBe('SYNTHETIC');
    expect(overview.coverage?.expected).toBe(24);
    expect(overview.coverage?.covered).toBe(22);
    expect(overview.coverage?.discarded).toBe(2);

    await page.goto('/markets');

    // Dominante : le moteur Canvas d'ECharts est réellement monté.
    await expect(page.locator('.vx-marketmap-canvas canvas')).toBeVisible({ timeout: 15_000 });

    // Bandeau SYNTHETIC et conclusion serveur verbatim.
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES', { exact: true })).toBeVisible();
    const conclusion = page.getByTestId('markets-conclusion');
    await expect(conclusion).toHaveText(overview.conclusion ?? '');

    // Table équivalente : une ligne par ticker couvert, valeurs exactes.
    const table = page.getByRole('table', { name: 'Table équivalente de la carte des marchés' });
    const tickers = overview.sectors.flatMap((sector) => sector.tickers);
    expect(tickers.length).toBe(22);
    await expect(table.locator('tbody tr')).toHaveCount(22);
    for (const ticker of tickers) {
      const row = table.locator('tbody tr', { hasText: ticker.ticker }).first();
      const text = (await row.textContent()) ?? '';
      expect(text).toContain(
        `${fr(ticker.last_close)}${ticker.currency !== null ? ` ${ticker.currency}` : ''}`,
      );
      expect(text).toContain(`${fr(ticker.return_1d_pct)} %`);
      expect(text).toContain(`${fr(ticker.weight_in_sector_pct)} %`);
      expect(text).toContain(`${fr(ticker.weight_global_pct)} %`);
      expect(text).toContain(ticker.quality);
    }

    // Breadth : barres linéaires, valeur et couverture serveur.
    const breadth = overview.breadth;
    expect(breadth?.status).toBe('OK');
    await expect(page.getByText('Breadth globale')).toBeVisible();
    await expect(page.getByText(`${fr(breadth?.value_pct ?? '')} %`, { exact: true })).toBeVisible();

    // Instruments écartés nommés avec leur raison (jamais interpolés).
    await expect(page.getByText('Instruments écartés (2)')).toBeVisible();
    await expect(page.getByText('missing_close').first()).toBeVisible();
  });

  test('tri de la table au clavier (Entrée sur un en-tête, aria-sort reflété)', async ({
    page,
  }) => {
    await page.goto('/markets');
    const table = page.getByRole('table', { name: 'Table équivalente de la carte des marchés' });
    await expect(table.locator('tbody tr')).toHaveCount(22);

    const sortButton = table.getByRole('button', { name: /Rendement 1 j/ });
    await sortButton.focus();
    await page.keyboard.press('Enter');
    const header = table.locator('th[aria-sort="ascending"]');
    await expect(header).toHaveCount(1);
    await expect(header).toContainText('Rendement 1 j');

    // Premier rang = plus mauvais rendement affiché (chaîne serveur signée).
    const firstReturnCell = table.locator('tbody tr').first().locator('td[data-sign]');
    await expect(firstReturnCell).toContainText('▼');

    await page.keyboard.press('Enter');
    await expect(table.locator('th[aria-sort="descending"]')).toHaveCount(1);
    await expect(
      table.locator('tbody tr').first().locator('td[data-sign]'),
    ).toContainText('▲');
  });

  test('LOT-A3 : les DOUZE modules de la planche §2, une dominante, sept absences motivées', async ({
    page,
  }) => {
    await page.goto('/markets');
    await expect(page.locator('.vx-marketmap-canvas canvas')).toBeVisible({ timeout: 15_000 });
    const MODULES = [
      'sessions',
      'volatility',
      'indices',
      'breadth',
      'market-health',
      'focus',
      'market-map',
      'sectors',
      'rates-curve',
      'fx',
      'correlation',
      'vol-structure',
      'discards',
    ];
    for (const module of MODULES) {
      await expect(page.locator(`[data-module="${module}"]`).first(), module).toBeVisible();
    }
    await expect(page.locator('.vx-main [data-rank="dominant"]')).toHaveCount(1);
    await expect(page.locator('.vx-absent-badge')).toHaveCount(7);
    for (const corps of await page.locator('.vx-absent-body').allTextContents()) {
      expect(corps).not.toMatch(/\d/);
    }
    await expect(page.locator('.vx-markets-table-scroll[tabindex="0"]')).toBeVisible();
  });

  test('sélection au clavier dans la table → inspecteur de l’instrument, chaînes API exactes', async ({
    page,
  }) => {
    const overview = (await (await page.request.get('/api/v1/markets/overview')).json()) as ApiOverview;
    const premier = overview.sectors.flatMap((sector) => sector.tickers)[0]!;
    await page.goto('/markets');
    await expect(page.locator('.vx-marketmap-canvas canvas')).toBeVisible({ timeout: 15_000 });
    // Par défaut : la vérité du snapshot.
    await expect(page.locator('.vx-inspector-heading')).toHaveText('Inspecteur — Carte des marchés');

    const bouton = page.getByRole('button', { name: `Inspecter ${premier.ticker}` });
    await bouton.focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('.vx-inspector-heading')).toHaveText(`Inspecteur — ${premier.ticker}`);
    const faits = page.getByTestId('markets-instrument-facts');
    await expect(faits).toContainText(fr(premier.last_close));
    await expect(faits).toContainText(`${fr(premier.return_1d_pct)} %`);
    await expect(faits).toContainText(`${fr(premier.weight_global_pct)} %`);
    await expect(faits).toContainText(premier.quality);
    await expect(page.getByTestId('markets-instrument-lineage')).toContainText('market.simple_return');
    await expect(bouton).toHaveAttribute('aria-pressed', 'true');

    // Fermer rend l'inspecteur par défaut.
    await page.getByRole('button', { name: 'Fermer' }).click();
    await expect(page.locator('.vx-inspector-heading')).toHaveText('Inspecteur — Carte des marchés');
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/markets');
    await expect(page.locator('.vx-marketmap-canvas canvas')).toBeVisible({ timeout: 15_000 });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('markets', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé (routes /api interrompues) → état offline honnête', async ({
    page,
  }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/markets');
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(boundary).toContainText("L'API locale est injoignable");
    // Aucune carte ni table fabriquée en mode hors ligne.
    await expect(page.locator('.vx-marketmap-canvas')).toHaveCount(0);
    await expect(page.getByRole('table')).toHaveCount(0);
  });
});
