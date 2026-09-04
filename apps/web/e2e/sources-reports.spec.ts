/**
 * Parcours /sources-reports — matrice de santé des sources sur le pipeline réel :
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

    // ZÉRO cellule vide.
    const emptyCells = await table
      .locator('tbody td, tbody th')
      .evaluateAll((cells) => cells.filter((cell) => cell.textContent?.trim() === '').length);
    expect(emptyCells).toBe(0);
    // LOT T4-7 — « jamais sondé » se lit EN TOUTES LETTRES, sans glyphe à
    // expliquer. `tested_at === null` signifie qu'aucune sonde n'a jamais
    // tourné : c'est un FAIT servi, pas une absence de publication, et un
    // tiret + `aria-label` le réservait au lecteur d'écran. Même compte,
    // même exigence, sur du texte réellement visible.
    // LA PORTÉE COMPTE : la LÉGENDE de la table écrit elle aussi « un statut
    // jamais sondé reste ERROR / NEVER_TESTED ». Un `getByText` sur la table
    // entière la comptait comme une dixième occurrence — l'assertion était
    // fausse d'un cran, et rouge. Elle vise désormais le CORPS de la table,
    // là où vivent les cellules. Même exigence, même compte, portée juste.
    await expect(table.locator('tbody').getByText('jamais sondé')).toHaveCount(9);
    // Et TOUT glyphe restant porte un nom accessible qui NOMME le champ
    // manquant — c'est l'invariant du lot T4, et il ne dépend d'aucun compte
    // de fixture : quel que soit le nombre de raisons non publiées, aucune
    // n'est un tiret muet.
    const glyphes = table.locator('[data-absent="true"]');
    const nombreGlyphes = await glyphes.count();
    expect(nombreGlyphes).toBeGreaterThan(0);
    for (let index = 0; index < nombreGlyphes; index += 1) {
      const cellule = glyphes.nth(index);
      await expect(cellule).toHaveAttribute('role', 'img');
      const nom = await cellule.getAttribute('aria-label');
      expect(nom).toContain('non publiée');
    }

    // Bandeau population SYNTHETIC (le pipeline E2E est 100 % synthétique).
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES')).toBeVisible();
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
      path: screenshotPath('sources-reports', testInfo.project.name),
      fullPage: true,
    });
  });
});

test.describe('Page Sources & Rapports — composition de la planche §12 (LOT-A8)', () => {
  test('LOT-A8 : les dix-sept modules, une seule dominante (le registre), neuf absences, inspecteur sur sélection seulement', async ({
    page,
  }) => {
    await page.goto('/sources-reports');
    const grille = page.getByTestId('sources-grid');
    await expect(grille).toBeVisible();
    await expect(grille.locator('> [data-module]')).toHaveCount(17);
    await expect(page.locator('.vx-main [data-rank="dominant"]')).toHaveCount(1);
    await expect(page.locator('[data-module="registry"] [data-rank="dominant"] table')).toBeVisible();
    await expect(grille.locator('.vx-absent')).toHaveCount(9);
    for (const body of await grille.locator('[data-testid="absent-body"]').allTextContents()) {
      expect(body).not.toMatch(/\d/);
    }
    await expect(page.getByTestId('src-status-ERROR')).toBeVisible();
    await expect(page.locator('.vx-health')).toBeVisible();
    // Témoin du shell : aucune colonne morte tant qu'aucune capacité n'est ouverte.
    await expect(page.locator('#vx-inspector-slot')).toBeHidden();

    const bouton = page.getByRole('table').getByRole('button', { name: /^Inspecter/ }).first();
    await bouton.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('src-capability-facts')).toBeVisible();
    await expect(page.locator('#vx-inspector-slot')).toBeVisible();
    await expect(bouton).toHaveAttribute('aria-pressed', 'true');
    await page.getByRole('button', { name: 'Fermer' }).click();
    await expect(page.locator('#vx-inspector-slot')).toBeHidden();
  });
});
