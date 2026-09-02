/**
 * Parcours /simulator — parcours COMPLET options → « Envoyer au Simulateur »
 * → Calculer → payoff rendu (points et breakevens serveur), refus 422 affiché
 * avec la raison exacte (jambe courte nue), état invalid_input, axe et hors
 * ligne. Tous les chiffres viennent de POST /simulations/preview.
 */
import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

const UNDERLYING = 'SYN-TECH-01';

interface ApiChain {
  expirations: {
    expiration: string;
    trading_class: string;
    exchange: string;
    quality: string;
    contracts: {
      strike: string | null;
      right: string | null;
      iv: { status: string };
      quote: { ask: string | null; status: string };
    }[];
  }[];
  spot: { value: string } | null;
}

async function fillRemainingAssumptions(page: import('@playwright/test').Page): Promise<void> {
  // Le transfert préremplit strike/prime/spot (et IV si résolue) ; le reste
  // est déclaré ici (chaînes décimales, validées côté serveur).
  const vol = page.getByLabel('Volatilité annualisée (décimal, 0.25 = 25 %/an)');
  if ((await vol.inputValue()) === '') {
    await vol.fill('0.25');
  }
  await page.getByLabel('Taux annualisé (décimal)').fill('0.02');
  await page.getByLabel('Rendement de dividende annualisé (décimal)').fill('0.00');
  const spot = page.getByLabel('Spot déclaré (décimal)');
  if ((await spot.inputValue()) === '') {
    await spot.fill('366.08');
  }
  await page
    .getByLabel('Grille de spots (1 à 41 valeurs, séparées par des virgules)')
    .fill('250, 300, 350, 400, 450');
  await page.getByLabel('Grille de temps en années (1 à 8 valeurs)').fill('0');
}

test.describe('Simulateur — parcours complet et refus honnêtes', () => {
  test('options → Envoyer au Simulateur → Calculer → payoff rendu avec breakevens certifiés', async ({
    page,
  }) => {
    // 1. Chaîne : ouvrir l'inspecteur d'un CALL avec IV résolue.
    const response = await page.request.get(`/api/v1/options/${UNDERLYING}/chain`);
    expect(response.ok()).toBe(true);
    const chain = (await response.json()) as ApiChain;
    expect(chain.expirations.some((candidate) => candidate.quality !== 'VALID')).toBe(true);
    const group = chain.expirations.find(
      (candidate) =>
        candidate.quality === 'VALID' &&
        candidate.contracts.some(
          (entry) =>
            entry.right === 'CALL' &&
            entry.strike !== null &&
            entry.iv.status === 'OK' &&
            entry.quote.status === 'OK' &&
            entry.quote.ask !== null,
        ),
    );
    expect(group, 'le seed doit publier un groupe Options VALID transférable').toBeDefined();
    if (group === undefined) {
      throw new Error('aucun groupe Options VALID transférable publié par le seed');
    }
    const resolved = group.contracts.find(
      (entry) =>
        entry.right === 'CALL' &&
        entry.strike !== null &&
        entry.iv.status === 'OK' &&
        entry.quote.status === 'OK' &&
        entry.quote.ask !== null,
    );
    expect(resolved, 'le groupe VALID doit contenir un CALL avec IV et ask saines').toBeDefined();
    if (resolved === undefined) {
      throw new Error('aucun CALL sain publié dans le groupe Options VALID');
    }

    await page.goto(`/options/${UNDERLYING}`);
    await expect(page.getByText('Données partielles', { exact: true })).toBeVisible();
    const groupButton = page.getByTestId('chain-group').filter({
      hasText: `${group.expiration} · ${group.trading_class} (${group.exchange})`,
    });
    await expect(groupButton).toHaveCount(1);
    await groupButton.click();
    await expect(groupButton).toHaveAttribute('aria-pressed', 'true');
    await page
      .getByRole('button', {
        name: `Inspecter CALL strike ${resolved.strike} ${group.expiration} ${group.trading_class}`,
      })
      .click();
    const transfer = page.getByRole('button', { name: 'Envoyer au Simulateur' });
    await expect(transfer).toBeEnabled();
    await transfer.click();

    // 2. Simulateur : préremplissage typé visible et éditable.
    await expect(page).toHaveURL(/\/simulator$/);
    await expect(page.getByTestId('sim-transfer-note')).toContainText(UNDERLYING);
    await expect(page.getByLabel('Strike (décimal)')).toHaveValue(resolved.strike!);
    await expect(page.getByLabel('Prime unitaire déclarée (décimal)')).toHaveValue(
      resolved.quote.ask!,
    );
    await expect(page.getByLabel('Spot déclaré (décimal)')).toHaveValue(chain.spot!.value);
    // Honnêteté : la sauvegarde n'existe pas encore, dit clairement.
    await expect(page.getByText(/Sauvegarde/)).toContainText('NON_IMPLÉMENTÉ');

    // 3. Calculer : le serveur calcule tout ; la dominante payoff se rend.
    await fillRemainingAssumptions(page);
    await page.getByRole('button', { name: 'Calculer' }).click();
    const result = page.getByTestId('sim-result');
    await expect(result).toBeVisible({ timeout: 15_000 });
    await expect(result.getByText('THÉORIQUE', { exact: true })).toBeVisible();
    await expect(page.locator('.vx-payoff-canvas canvas')).toBeVisible({ timeout: 15_000 });

    // 4. Breakevens certifiés : mêmes chaînes que la réponse serveur.
    const breakevens = page.getByTestId('sim-breakevens');
    await expect(breakevens).toBeVisible();
    await expect(breakevens).toContainText('résidu certifié');
    // Une jambe longue unique : ALL_LONG (résultats certifiés), écho des hypothèses.
    await expect(page.getByTestId('sim-kpi')).toContainText('ALL_LONG');
    await expect(page.getByTestId('sim-echo')).toContainText('250, 300, 350, 400, 450');
    // Table équivalente des points serveur (grille déclarée + strikes + zéro).
    const pointsTable = result.getByRole('table', { name: /Points de P&L/ });
    await expect(pointsTable.locator('tbody tr').first()).toBeVisible();
  });

  test('jambe courte nue → 422 affiché avec la raison exacte du vérificateur', async ({
    page,
  }) => {
    await page.goto('/simulator');
    // Déclarer une jambe COURTE CALL sans couverture (perte non bornée).
    await page.getByLabel('Sens').selectOption('SHORT');
    await page.getByLabel('Strike (décimal)').fill('300');
    await page.getByLabel('Prime unitaire déclarée (décimal)').fill('10');
    await fillRemainingAssumptions(page);
    await page.getByRole('button', { name: 'Calculer' }).click();

    const rejection = page.getByTestId('sim-rejection');
    await expect(rejection).toBeVisible({ timeout: 15_000 });
    await expect(rejection).toContainText('422');
    // Code machine exact du vérificateur, relayé verbatim.
    await expect(rejection).toContainText('UNCOVERED_SHORT_UPSIDE_TAIL');
    // Explication française du refus (fail-closed, rien d'approximé).
    await expect(rejection).toContainText('perte théorique n’est pas bornée');
    await expect(page.getByTestId('sim-result')).toHaveCount(0);
  });

  test('invalid_input : formulaire incomplet, rien n’est envoyé', async ({ page }) => {
    let previewCalls = 0;
    await page.route('**/api/v1/simulations/preview', (route) => {
      previewCalls += 1;
      void route.continue();
    });
    await page.goto('/simulator');
    await page.getByRole('button', { name: 'Calculer' }).click();
    const invalid = page.getByTestId('sim-invalid-input');
    await expect(invalid).toBeVisible();
    await expect(invalid).toContainText('strike est requis');
    expect(previewCalls).toBe(0);
  });

  test('LOT-A5 : les QUATORZE modules de la planche §6, aucune dominante à vide, une après Calculer, scénarios servis', async ({
    page,
  }) => {
    await page.goto('/simulator');
    const MODULES = [
      'manual-entry',
      'base-parameters',
      'scenarios',
      'payoff',
      'monte-carlo',
      'kpi-served',
      'kpi-probabilistic',
      'stress-tests',
      'sensitivity',
      'portfolio-impact',
      'catalysts',
      'key-assumptions',
      'sources',
      'method',
    ];
    for (const module of MODULES) {
      await expect(page.locator(`[data-module="${module}"]`).first(), module).toBeVisible();
    }
    // À vide : aucune dominante ; cinq absences motivées, sans chiffre.
    await expect(page.locator('.vx-main [data-rank="dominant"]')).toHaveCount(0);
    await expect(page.locator('.vx-absent-badge')).toHaveCount(5);
    for (const corps of await page.locator('.vx-absent-body').allTextContents()) {
      expect(corps).not.toMatch(/\d/);
    }
    await expect(page.locator('.vx-inspector-heading')).toHaveText('Inspecteur — Étude');

    await page.getByLabel('Strike (décimal)').fill('300');
    await page.getByLabel('Prime unitaire déclarée (décimal)').fill('10');
    await fillRemainingAssumptions(page);
    await page.getByRole('button', { name: 'Calculer' }).click();
    await expect(page.getByTestId('sim-result')).toBeVisible({ timeout: 15_000 });
    // Après calcul : une seule dominante, le payoff ; scénarios et lignée servis.
    await expect(page.locator('.vx-main [data-rank="dominant"]')).toHaveCount(1);
    await expect(page.locator('[data-module="payoff"] [data-rank="dominant"]')).toHaveCount(1);
    await expect(page.getByTestId('sim-scenarios').locator('tbody tr').first()).toBeVisible();
    await expect(page.getByTestId('sim-method')).toContainText('options.payoff');
    await expect(page.getByTestId('sim-kpi')).toContainText('Gain max');
    await expect(page.getByTestId('sim-study-facts')).toContainText('THEORETICAL');
  });

  test('axe : zéro violation critique/sérieuse + capture (formulaire et résultat)', async ({
    page,
  }, testInfo) => {
    await page.goto('/simulator');
    await page.getByLabel('Strike (décimal)').fill('300');
    await page.getByLabel('Prime unitaire déclarée (décimal)').fill('10');
    await fillRemainingAssumptions(page);
    await page.getByRole('button', { name: 'Calculer' }).click();
    await expect(page.getByTestId('sim-result')).toBeVisible({ timeout: 15_000 });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('simulator', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé : Calculer → état offline honnête, aucun résultat', async ({ page }) => {
    await page.goto('/simulator');
    await page.getByLabel('Strike (décimal)').fill('300');
    await page.getByLabel('Prime unitaire déclarée (décimal)').fill('10');
    await fillRemainingAssumptions(page);
    await page.route('**/api/**', (route) => route.abort());
    await page.getByRole('button', { name: 'Calculer' }).click();
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText("aucun calcul n'a été effectué");
    await expect(page.getByTestId('sim-result')).toHaveCount(0);
  });
});
