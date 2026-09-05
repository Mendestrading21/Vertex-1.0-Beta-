/**
 * Parcours /risks — pipeline réel (seed SYNTHETIC : la matrice de corrélation
 * est publiée par le drain `risk.matrix.refresh` du semis, puis servie par
 * `GET /api/v1/risk/matrix`). LOT-A6 : la planche §9 composée en entier —
 * dix-neuf modules, une dominante (la matrice), l'inspecteur « Matrice
 * publiée » remplacé par l'instrument ouvert depuis un en-tête de ligne.
 *
 * Les assertions sont RELATIVES à l'état lu sur l'API : coefficients et
 * bandes comparés au corps servi, jamais à une valeur attendue en dur.
 */
import type { APIResponse, Page } from '@playwright/test';

import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

async function apiRiskMatrix(page: Page): Promise<Record<string, unknown>> {
  const response: APIResponse = await page.request.get('/api/v1/risk/matrix');
  expect(response.ok()).toBe(true);
  return (await response.json()) as Record<string, unknown>;
}

function contentOf(body: Record<string, unknown>): Record<string, unknown> | null {
  const content = body['content'];
  return typeof content === 'object' && content !== null ? (content as Record<string, unknown>) : null;
}

test.describe('Page Risques — matrice réelle (LOT-A6)', () => {
  test('LOT-A6 : les dix-neuf modules de la planche, une seule dominante, matrice = API', async ({ page }) => {
    const body = await apiRiskMatrix(page);
    const content = contentOf(body);

    await page.goto('/risks');
    await expect(page.getByRole('heading', { level: 1, name: 'Risques' })).toBeVisible();
    const grille = page.getByTestId('risk-grid');
    await expect(grille).toBeVisible();
    await expect(grille.locator('> [data-module]')).toHaveCount(19);
    await expect(page.locator('.vx-main [data-rank="dominant"]')).toHaveCount(1);
    await expect(page.locator('[data-module="correlations"] [data-rank="dominant"]')).toBeVisible();
    // Douze absences déclarées, corps sans chiffre.
    await expect(grille.locator('.vx-absent')).toHaveCount(12);
    for (const body of await grille.locator('[data-testid="absent-body"]').allTextContents()) {
      expect(body).not.toMatch(/\d/);
    }

    const coverage = content === null ? null : (content['coverage'] as Record<string, unknown> | undefined) ?? null;
    const refusal = coverage === null ? null : coverage['refusal_reason'];
    if (body['state'] === 'empty' || content === null) {
      await expect(page.locator('[data-module="correlations"]')).toContainText('Aucun instantané publié');
      return;
    }
    if (typeof refusal === 'string') {
      await expect(page.locator('[data-module="correlations"]')).toContainText("Aucune matrice n'a pu être construite");
      return;
    }
    // Matrice servie : chaque coefficient affiché est la chaîne API, avec sa bande.
    const matrice = page.locator('[data-module="correlations"] table');
    await expect(matrice).toBeVisible();
    const instruments = content['instruments'] as Record<string, unknown>[];
    const matrix = content['matrix'] as string[][];
    const bands = content['matrix_bands'] as string[][];
    await expect(matrice.locator('tbody tr')).toHaveCount(instruments.length);
    const first = matrix[0] ?? [];
    for (const [column, value] of first.entries()) {
      const cellule = matrice.locator('tbody tr').first().locator('td').nth(column);
      await expect(cellule).toHaveText(value);
      await expect(cellule).toHaveAttribute('data-band', String(bands[0]?.[column]));
    }
    // Couverture : les comptes publiés, tels quels.
    await expect(page.getByTestId('risk-coverage')).toContainText(
      `${String(coverage?.['retained_count'])} sur ${String(coverage?.['perimeter_size'])} déclarés`,
    );
  });

  test('LOT-A6 : l’inspecteur porte la matrice publiée, un en-tête de ligne ouvre l’instrument, Fermer y revient', async ({ page }) => {
    const body = await apiRiskMatrix(page);
    const content = contentOf(body);
    test.skip(content === null || !Array.isArray(content['instruments']) || (content['instruments'] as unknown[]).length === 0, 'aucune matrice servie par le pipeline');

    await page.goto('/risks');
    await expect(page.getByTestId('risk-matrix-facts')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: 'Inspecteur — Matrice publiée' })).toBeVisible();

    const instruments = content?.['instruments'] as Record<string, unknown>[];
    const ticker = String(instruments[0]?.['ticker']);
    const bouton = page.locator('[data-module="correlations"] tbody th button').first();
    await expect(bouton).toHaveText(ticker);
    await bouton.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('risk-instrument-facts')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: `Inspecteur — ${ticker}` })).toBeVisible();
    await expect(bouton).toHaveAttribute('aria-pressed', 'true');
    // Les coefficients de l'instrument avec chacun des autres, sans le sien.
    await expect(page.getByTestId('risk-instrument-coefficients').locator('li')).toHaveCount(instruments.length - 1);

    await page.getByRole('button', { name: 'Fermer' }).click();
    await expect(page.getByTestId('risk-matrix-facts')).toBeVisible();
    await expect(page.getByTestId('risk-instrument-facts')).toHaveCount(0);
  });

  test('LOT-A6 : concentration du registre et drawdown, lus par leurs propriétaires', async ({ page }) => {
    await page.goto('/risks');
    await expect(page.getByTestId('risk-grid')).toBeVisible();
    const concentration = page.locator('[data-module="concentration"]');
    await expect(concentration).toBeVisible();
    // Registre manuel semé : la valorisation publie des poids, jamais une table sur cette page.
    await expect(concentration.locator('table')).toHaveCount(0);
    await expect(page.locator('[data-module="max-drawdown"]')).toBeVisible();
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/risks');
    await expect(page.getByTestId('risk-grid')).toBeVisible();
    await expect(page.getByTestId('risk-matrix-facts')).toBeVisible();
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({ path: screenshotPath('risk', testInfo.project.name), fullPage: true });
  });

  test('hors ligne simulé → état offline honnête, aucune matrice fabriquée', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/risks');
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary.first()).toBeVisible();
    await expect(page.locator('[data-module="correlations"] table')).toHaveCount(0);
    await expect(page.getByTestId('risk-grid')).toHaveCount(0);
  });
});
