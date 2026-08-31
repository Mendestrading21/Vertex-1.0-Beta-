/**
 * Parcours /system — matrice de santé des sources sur le pipeline réel :
 * 14 capacités déclarées (manifeste committé), 5 sondes DEMO persistées, le
 * reste honnêtement ERROR/NEVER_TESTED. Axe + capture par viewport.
 */
import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

const EXPECTED_TOTAL = 14;

test.describe('Page Sources & Rapports — SourceHealthMatrix', () => {
  test('matrice complète : 14 lignes exactes, badges, zéro cellule vide', async ({ page }) => {
    await page.goto('/sources-reports');
    const table = page.getByRole('table');
    await expect(table).toBeVisible();

    // Compte exact = manifeste déclaré (total du DTO).
    const rows = table.locator('tbody tr');
    await expect(rows).toHaveCount(EXPECTED_TOTAL);
    await expect(
      page.getByText(`${EXPECTED_TOTAL} capacités affichées sur ${EXPECTED_TOTAL} déclarées`),
    ).toBeVisible();

    // Table accessible : caption + th scope.
    await expect(table.locator('caption')).toContainText('Capacités IBKR market-data déclarées');
    const headerScopes = await table.locator('thead th').evaluateAll((cells) =>
      cells.map((cell) => cell.getAttribute('scope')),
    );
    expect(headerScopes).toEqual(['col', 'col', 'col', 'col', 'col', 'col']);

    // Badges icône + texte pour les statuts réellement sondés (semis DEMO).
    for (const status of ['AVAILABLE', 'DELAYED', 'NOT_ENTITLED', 'UNSUPPORTED', 'MANUAL_EXPORT']) {
      const badge = table.locator(`.vx-status-badge[data-status="${status}"]`).first();
      await expect(badge).toBeVisible();
      await expect(badge).toContainText(status);
      await expect(badge.locator('[aria-hidden="true"]')).not.toBeEmpty();
    }
    // Les capacités jamais sondées restent ERROR / NEVER_TESTED (9 = 14 − 5).
    await expect(table.locator('.vx-status-badge[data-status="ERROR"]')).toHaveCount(9);
    await expect(table.getByRole('cell', { name: 'NEVER_TESTED' })).toHaveCount(9);

    // ZÉRO cellule vide ; « — » porte l'aria-label « jamais sondé ».
    const emptyCells = await table
      .locator('tbody td, tbody th')
      .evaluateAll((cells) => cells.filter((cell) => cell.textContent?.trim() === '').length);
    expect(emptyCells).toBe(0);
    await expect(table.locator('[aria-label="jamais sondé"]')).toHaveCount(9);

    // Bandeau population SYNTHETIC (le pipeline E2E est 100 % synthétique).
    await expect(page.getByText('DONNÉES SYNTHÉTIQUES')).toBeVisible();
  });

  test('filtres famille/statut : compteurs cohérents et persistance URL', async ({ page }) => {
    await page.goto('/sources-reports');
    const table = page.getByRole('table');
    await expect(table.locator('tbody tr')).toHaveCount(EXPECTED_TOTAL);

    // Filtre famille : le nombre de lignes égale le compteur de l'option.
    const familySelect = page.getByLabel('Famille');
    const optionLabel = await familySelect
      .locator('option[value="market_data"]')
      .textContent();
    const expectedFamilyCount = Number(/\((\d+)\)/.exec(optionLabel ?? '')?.[1]);
    expect(Number.isInteger(expectedFamilyCount)).toBe(true);
    await familySelect.selectOption('market_data');
    await expect(table.locator('tbody tr')).toHaveCount(expectedFamilyCount);
    await expect(page).toHaveURL(/famille=market_data/);

    // Filtre statut cumulé, puis rechargement : les filtres persistent.
    await page.getByLabel('Statut testé').selectOption('DELAYED');
    await expect(page).toHaveURL(/statut=DELAYED/);
    const filteredCount = await table.locator('tbody tr').count();
    await page.reload();
    await expect(table.locator('tbody tr')).toHaveCount(filteredCount);
    await expect(page.getByLabel('Statut testé')).toHaveValue('DELAYED');
  });

  test('santé des composants et accessibilité (axe) + capture', async ({ page }, testInfo) => {
    await page.goto('/sources-reports');
    await expect(page.getByRole('table')).toBeVisible();

    // Modules secondaires : santé db/snapshots/worker avec la limitation
    // heartbeat_proxy affichée explicitement.
    await expect(page.getByText('ok (SELECT 1)')).toBeVisible();
    await expect(page.getByText('(heartbeat_proxy)')).toBeVisible();
    await expect(page.getByText(/mesure l'âge du snapshot le plus récent/)).toBeVisible();

    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('system', testInfo.project.name),
      fullPage: true,
    });
  });
});
