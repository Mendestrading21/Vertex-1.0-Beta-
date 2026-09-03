/**
 * Parcours /charts/:instrument — Graphiques (LOT-A2, `TL / 08`).
 *
 * La planche §8 rendue sur données SYNTHETIC : dominante Lightweight Charts
 * (canvas réel, attribution TradingView), les DOUZE modules présents — quatre
 * servis par le contrat Analyse (LOT-S2 : la comparaison base 100 l'est
 * désormais), huit déclarés absents avec leur motif —, une seule dominante,
 * axe, et capture pleine page.
 */
import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

const INSTRUMENT = 'SYN-TECH-01';

const MODULES = [
  'main-chart',
  'volume',
  'served-indicators',
  'overlays',
  'rsi',
  'macd',
  'comparison',
  'synchronized',
  'selected-object',
  'linked-alerts',
  'layouts',
  'saved-studies',
] as const;

const ABSENCE_LABELS = [
  'AUCUNE SOURCE',
  'ABONNEMENT REQUIS',
  'CONTRAT SERVEUR ABSENT',
  'DÉCISION EN ATTENTE',
] as const;

test.describe('Page Graphiques — planche complète, servie ou déclarée absente', () => {
  test('dominante rendue (canvas) + attribution TradingView + signature TL / 08', async ({
    page,
  }) => {
    const response = await page.request.get(`/api/v1/analysis/${INSTRUMENT}`);
    expect(response.ok()).toBe(true);

    await page.goto(`/charts/${INSTRUMENT}`);
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES', { exact: true })).toBeVisible();
    const link = page.locator('.vx-chartframe-foot a', { hasText: 'TradingView' }).first();
    await expect(link).toHaveAttribute('href', 'https://www.tradingview.com/');
    await expect(page.locator('main')).toHaveAttribute('data-ledger-code', 'TL / 08');
  });

  test('les douze modules de la planche sont présents, chacun servi ou déclaré absent', async ({
    page,
  }) => {
    await page.goto(`/charts/${INSTRUMENT}`);
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({
      timeout: 15_000,
    });
    for (const module of MODULES) {
      await expect(page.locator(`[data-module="${module}"]`).first(), module).toBeVisible();
    }
    // Chaque absence porte un motif du vocabulaire FERMÉ — jamais un rectangle muet.
    // LOT-S2 : la comparaison base 100 est SERVIE, huit modules restent
    // declares absents.
    const badges = page.locator('.vx-absent-badge');
    await expect(badges).toHaveCount(8);
    for (const texte of await badges.allTextContents()) {
      expect(ABSENCE_LABELS).toContain(texte);
    }
    // Un corps de module absent ne porte aucun chiffre (article 17).
    for (const corps of await page.locator('.vx-absent-body').allTextContents()) {
      expect(corps).not.toMatch(/\d/);
    }
  });

  test('une seule lumière dominante, et c’est l’espace graphique', async ({ page }) => {
    await page.goto(`/charts/${INSTRUMENT}`);
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({
      timeout: 15_000,
    });
    const dominantes = page.locator('.vx-main [data-rank="dominant"]');
    await expect(dominantes).toHaveCount(1);
    await expect(dominantes.first()).toHaveAttribute('data-module', 'main-chart');
  });

  test('sans instrument : état vide explicite, sélecteur, et absences déjà déclarées', async ({
    page,
  }) => {
    await page.goto('/charts');
    await expect(page.getByRole('heading', { level: 1, name: 'Graphiques' })).toBeVisible();
    await expect(page.getByText(/Aucun instrument sélectionné/)).toBeVisible();
    await expect(page.locator('.vx-absent-badge')).toHaveCount(8);
  });

  test('axe : zéro violation sérieuse ou critique, puis capture pleine page', async ({
    page,
  }, testInfo) => {
    await page.goto(`/charts/${INSTRUMENT}`);
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({
      timeout: 15_000,
    });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('charts', testInfo.project.name),
      fullPage: true,
    });
  });
});
