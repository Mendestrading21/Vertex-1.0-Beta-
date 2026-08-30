/**
 * Parcours /performance — snapshot réel publié par le worker (marques
 * synthétiques × ledger déclaré) : bandeau de population non masquable,
 * courbe + heatmap ECharts, et TROIS métriques affichées STRICTEMENT égales
 * aux chaînes de l'API (TWR brut, XIRR brut, drawdown brut), export
 * CSV + manifeste servis par l'API, axe et offline.
 */
import type { Page } from '@playwright/test';

import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface MetricBlock {
  readonly status: string;
  readonly total_return_pct?: string;
  readonly rate_pct?: string;
  readonly max_drawdown_pct?: string;
}

async function apiPerformance(page: Page): Promise<Record<string, unknown>> {
  const portfolio = await page.request.get('/api/v1/portfolio');
  expect(portfolio.ok()).toBe(true);
  const portfolioId = (
    ((await portfolio.json()) as Record<string, unknown>)['portfolio'] as Record<string, unknown>
  )['id'] as number;
  const response = await page.request.get(`/api/v1/performance/${portfolioId}`);
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as Record<string, unknown>;
  expect(body['state']).toBe('ok');
  return body['content'] as Record<string, unknown>;
}

test.describe('Page Performance — snapshot réel', () => {
  test('bandeau population SYNTHETIC_MARKS_REAL_LEDGER non masquable + courbe rendue', async ({
    page,
  }) => {
    const content = await apiPerformance(page);
    expect(content['population']).toBe('SYNTHETIC_MARKS_REAL_LEDGER');

    await page.goto('/performance');
    const population = page.getByTestId('perf-population');
    await expect(population).toBeVisible({ timeout: 20_000 });
    await expect(population).toContainText('SYNTHETIC_MARKS_REAL_LEDGER');
    await expect(population).toContainText('SYNTHETIC');
    await expect(population).toContainText('USER_DECLARED');

    // Dominante : le moteur ECharts rend un canvas réel (chunk paresseux).
    await expect(page.locator('.vx-perf-chart-canvas canvas')).toBeVisible({ timeout: 20_000 });
  });

  test('3 métriques affichées === chaînes API (TWR brut, XIRR brut, drawdown brut)', async ({
    page,
  }) => {
    const content = await apiPerformance(page);
    const metrics = content['metrics'] as Record<string, MetricBlock>;
    const twr = metrics['twr_gross']!;
    const xirr = metrics['xirr_gross']!;
    const drawdown = metrics['drawdown_gross']!;
    expect(twr.status).toBe('OK');
    expect(xirr.status).toBe('OK');
    expect(drawdown.status).toBe('OK');

    await page.goto('/performance');
    await expect(page.getByTestId('perf-metrics')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('perf-metric-value-twr_gross')).toHaveText(
      `${twr.total_return_pct!} %`,
      { timeout: 20_000 },
    );
    await expect(page.getByTestId('perf-metric-value-xirr_gross')).toHaveText(
      `${xirr.rate_pct!} % / an`,
    );
    await expect(page.getByTestId('perf-metric-value-drawdown_gross')).toHaveText(
      `${drawdown.max_drawdown_pct!} %`,
    );

    // Chaque métrique porte sa définition, sa période et sa méthode+version.
    const twrCard = page.getByTestId('perf-metric-twr_gross');
    await expect(twrCard).toContainText('performance.twr');
    await expect(twrCard).toContainText('Période :');
  });

  test('série quotidienne : chaînes API exactes ; heatmap et table mensuelle avec mois incomplets marqués', async ({
    page,
  }) => {
    const content = await apiPerformance(page);
    const series = content['series'] as Record<string, unknown>;
    expect(series['status']).toBe('OK');
    const points = series['points'] as { trading_day: string; gross_value: string }[];
    expect(points.length).toBeGreaterThanOrEqual(2);
    const heatmap = content['heatmap'] as Record<string, unknown>;
    const months = heatmap['months'] as {
      month: string;
      return_pct: string;
      complete: boolean;
      incomplete_reasons: string[];
    }[];
    expect(months.length).toBeGreaterThanOrEqual(1);

    await page.goto('/performance');
    for (const point of points) {
      await expect(page.getByTestId(`perf-gross-${point.trading_day}`)).toHaveText(
        point.gross_value,
        { timeout: 20_000 },
      );
    }
    for (const month of months) {
      const row = page.getByTestId(`perf-month-${month.month}`);
      await expect(row).toContainText(month.return_pct);
      if (!month.complete) {
        await expect(row).toContainText('NON — mois incomplet');
        await expect(row).toContainText(month.incomplete_reasons[0]!);
      }
    }
  });

  // UN téléchargement par action, et le test le dit.
  //
  // Ce test attendait DEUX fichiers depuis un seul clic. Il passait sur
  // Chromium et Firefox et ÉCHOUAIT sur WebKit, qui n'en délivrait qu'un : le
  // manifeste ne partait jamais. C'était un défaut PRODUIT, pas un défaut de
  // test — un utilisateur Safari n'aurait jamais reçu son manifeste d'audit.
  // La page a désormais deux boutons ; le test les exerce séparément.
  test('export : le CSV des points est servi par l’API, un fichier par action', async ({
    page,
  }) => {
    await page.goto('/performance');
    await expect(page.getByTestId('perf-metrics')).toBeVisible({ timeout: 20_000 });

    const downloads: string[] = [];
    page.on('download', (download) => {
      downloads.push(download.suggestedFilename());
    });
    await page.getByRole('button', { name: "Exporter les points (CSV servi par l'API)" }).click();
    await expect.poll(() => downloads.length, { timeout: 15_000 }).toBe(1);
    expect(downloads[0]!.endsWith('.csv')).toBe(true);
  });

  test('export : le manifeste JSON est servi par l’API, un fichier par action', async ({
    page,
  }) => {
    await page.goto('/performance');
    await expect(page.getByTestId('perf-metrics')).toBeVisible({ timeout: 20_000 });

    const downloads: string[] = [];
    page.on('download', (download) => {
      downloads.push(download.suggestedFilename());
    });
    await page
      .getByRole('button', { name: "Exporter le manifeste (JSON servi par l'API)" })
      .click();
    await expect.poll(() => downloads.length, { timeout: 15_000 }).toBe(1);
    expect(downloads[0]!.endsWith('-manifest.json')).toBe(true);
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/performance');
    await expect(page.getByTestId('perf-metrics')).toBeVisible({ timeout: 20_000 });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('performance', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé → état offline honnête', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/performance');
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(page.getByTestId('perf-metrics')).toHaveCount(0);
  });
});
