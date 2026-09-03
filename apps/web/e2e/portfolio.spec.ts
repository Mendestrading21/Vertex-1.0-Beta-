/**
 * Parcours /portfolio — pipeline réel (seed SYNTHETIC + worker en continu) :
 * valorisation publiée relayée verbatim, saisie d'une transaction (fait
 * passé) suivie de la revalorisation réelle (SSE/refetch) vérifiée CONTRE
 * L'API, correction compensatoire (la paire disparaît des lots), import CSV
 * en 3 temps avec ligne en erreur, export servi par l'API, axe et offline.
 *
 * Les assertions sont RELATIVES à l'état courant lu sur l'API : les trois
 * projets de viewport rejouent ce fichier sur la même base (journal
 * append-only), aucun compte absolu ne serait honnête.
 */
import type { APIResponse, Page } from '@playwright/test';

import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface ValuationLot {
  readonly lot_id: string;
  readonly ticker: string;
  readonly market_value: string;
  readonly unrealized_pnl: string;
}

async function apiPortfolio(page: Page): Promise<Record<string, unknown>> {
  const response: APIResponse = await page.request.get('/api/v1/portfolio');
  expect(response.ok()).toBe(true);
  return (await response.json()) as Record<string, unknown>;
}

function valuationLots(portfolio: Record<string, unknown>): ValuationLot[] {
  const valuation = portfolio['valuation'] as Record<string, unknown>;
  const content = valuation['content'] as Record<string, unknown>;
  const blocks = content['positions_by_currency'] as Record<string, unknown>[];
  return blocks.flatMap(
    (block) => ((block['unrealized'] as Record<string, unknown>)['lots'] ?? []) as ValuationLot[],
  );
}

function valuationVersion(portfolio: Record<string, unknown>): number {
  return (portfolio['valuation'] as Record<string, unknown>)['snapshot_version'] as number;
}

test.describe('Page Portefeuille — valorisation réelle', () => {
  test('badge marques SYNTHÉTIQUES, totaux identiques à l’API, exclusions séparées', async ({
    page,
  }) => {
    const before = await apiPortfolio(page);
    const content = (before['valuation'] as Record<string, unknown>)['content'] as Record<
      string,
      unknown
    >;
    expect(content['mark_population']).toBe('SYNTHETIC');

    await page.goto('/portfolio');
    await expect(page.getByTestId('pf-marks-badge')).toContainText('Marks : DONNÉES SYNTHÉTIQUES');
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES', { exact: true })).toBeVisible();

    // Chaque valeur affichée est la chaîne API verbatim (aucun total local).
    const blocks = content['positions_by_currency'] as Record<string, unknown>[];
    const summary = page.getByTestId('pf-summary-grid');
    for (const block of blocks) {
      const unrealized = block['unrealized'] as Record<string, unknown>;
      const concentration = block['concentration'] as Record<string, unknown>;
      if (unrealized['status'] === 'OK') {
        await expect(summary).toContainText(String(unrealized['total_unrealized']));
      }
      if (concentration['status'] === 'OK') {
        await expect(summary).toContainText(String(concentration['total_value']));
      }
    }

    // Lots valorisés : mêmes lignes que l'API, une par lot.
    const lots = valuationLots(before);
    const table = page.getByRole('table', { name: 'Lots ouverts valorisés (valeurs serveur exactes)' });
    await expect(table.locator('tbody tr')).toHaveCount(lots.length);
    for (const lot of lots) {
      await expect(table.locator('tbody')).toContainText(lot.market_value);
    }

    // Section d'exclusion présente et SÉPARÉE (états du seed : aucun exclu).
    const excludedCount = (
      (content['excluded_lots'] ?? []) as unknown[]
    ).length;
    const excludedSection = page.getByTestId('pf-excluded');
    await expect(excludedSection).toContainText(`Lots exclus de la valorisation (${excludedCount})`);

    // Espèces jamais fabriquées côté client.
    await expect(page.getByTestId('pf-cash-absent').first()).toContainText('non publié');
  });

  // Les champs du formulaire sont cherchés DANS `main` : le ticker du shell
  // (LOT-14) porte `aria-label="Ticker des marchés"`, et `/^Ticker/` non scopé
  // résolvait donc à deux éléments. Le shell est rendu sur les douze
  // destinations — ce qu'il ajoute, il l'ajoute partout.
  test('saisie d’une transaction (fait passé) → revalorisation réelle vérifiée contre l’API', async ({
    page,
  }) => {
    const before = await apiPortfolio(page);
    const lotsBefore = valuationLots(before).length;
    const versionBefore = valuationVersion(before);

    await page.goto('/portfolio');
    await expect(
      page.getByRole('heading', { name: 'Enregistrer une transaction (déjà exécutée hors Vertex)' }),
    ).toBeVisible();

    // Fait passé : achat déjà exécuté hors Vertex, effectif il y a ~2 h.
    const effective = new Date(Date.now() - 2 * 3600 * 1000);
    const local = new Date(effective.getTime() - effective.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    await page.getByLabel('Nature du fait').selectOption('BUY_RECORDED');
    await page.getByLabel(/Effet le/).fill(local);
    await page.getByLabel(/Impact de trésorerie signé/).fill('-110');
    await page.getByLabel('Devise', { exact: true }).fill('SYN');
    await page.locator('main').getByLabel(/^Ticker/).fill('SYN-FINL-01');
    await page.getByLabel('Quantité (décimal)').fill('1');
    await page.getByLabel('Prix unitaire (décimal)').fill('110');
    await page.getByRole('button', { name: 'Enregistrer la transaction' }).click();
    await expect(page.getByText(/Fait enregistré au journal/)).toBeVisible();

    // Le worker republie la valorisation ; l'API porte la nouvelle version.
    await expect
      .poll(async () => valuationVersion(await apiPortfolio(page)), { timeout: 20_000 })
      .toBeGreaterThan(versionBefore);
    const after = await apiPortfolio(page);
    const lotsAfter = valuationLots(after);
    expect(lotsAfter.length).toBe(lotsBefore + 1);

    // L'interface converge (signal SSE ou refetch) vers les MÊMES lignes.
    const table = page.getByRole('table', { name: 'Lots ouverts valorisés (valeurs serveur exactes)' });
    await expect(table.locator('tbody tr')).toHaveCount(lotsAfter.length, { timeout: 20_000 });
    const newest = lotsAfter[lotsAfter.length - 1]!;
    await expect(table.locator('tbody')).toContainText(newest.lot_id);
  });

  test('correction compensatoire → la paire disparaît des lots (net nul), 2e essai = 409 affiché', async ({
    page,
  }) => {
    const before = await apiPortfolio(page);
    const lotsBefore = valuationLots(before).length;

    await page.goto('/portfolio');

    // 1. Enregistrer un achat dédié à ce scénario (fait passé).
    const effective = new Date(Date.now() - 3600 * 1000);
    const local = new Date(effective.getTime() - effective.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    await page.getByLabel('Nature du fait').selectOption('BUY_RECORDED');
    await page.getByLabel(/Effet le/).fill(local);
    await page.getByLabel(/Impact de trésorerie signé/).fill('-220');
    await page.getByLabel('Devise', { exact: true }).fill('SYN');
    await page.locator('main').getByLabel(/^Ticker/).fill('SYN-TECH-02');
    await page.getByLabel('Quantité (décimal)').fill('2');
    await page.getByLabel('Prix unitaire (décimal)').fill('110');
    await page.getByRole('button', { name: 'Enregistrer la transaction' }).click();
    const recordedNote = await page.getByText(/Fait enregistré au journal \(ligne n°\d+\)/).textContent();
    const transactionId = Number(/ligne n°(\d+)/.exec(recordedNote ?? '')?.[1]);
    expect(Number.isInteger(transactionId)).toBe(true);

    // Le lot correspondant apparaît (worker réel).
    await expect
      .poll(async () => valuationLots(await apiPortfolio(page)).length, { timeout: 20_000 })
      .toBe(lotsBefore + 1);

    // 2. Correction compensatoire : confirmation + note obligatoire.
    const row = page.getByTestId(`pf-ledger-row-${transactionId}`);
    await expect(row).toBeVisible({ timeout: 20_000 });
    await row.getByRole('button', { name: 'Correction compensatoire' }).click();
    const confirmBox = page.getByTestId('pf-compensate-confirm');
    await expect(confirmBox).toBeVisible();
    await confirmBox.getByLabel('Raison de la correction').fill('erreur de saisie (démo E2E)');
    await confirmBox.getByRole('button', { name: 'Confirmer la correction compensatoire' }).click();

    // 3. La paire (fait + compensation) NET À ZÉRO : le lot disparaît.
    await expect
      .poll(async () => valuationLots(await apiPortfolio(page)).length, { timeout: 20_000 })
      .toBe(lotsBefore);
    const table = page.getByRole('table', { name: 'Lots ouverts valorisés (valeurs serveur exactes)' });
    await expect(table.locator('tbody tr')).toHaveCount(lotsBefore, { timeout: 20_000 });

    // Les DEUX lignes restent au journal, liées — l'historique n'est pas édité.
    await expect(page.getByTestId(`pf-ledger-row-${transactionId}`)).toContainText(
      /compensée par n°\d+/,
    );

    // 4. Un second essai sur la même ligne est impossible dans l'UI (le
    // bouton a disparu) — le 409 serveur est vérifié par l'API directement.
    await expect(
      page.getByTestId(`pf-ledger-row-${transactionId}`).getByRole('button', {
        name: 'Correction compensatoire',
      }),
    ).toHaveCount(0);
    const csrf = (await page.context().cookies()).find((c) => c.name === 'vertex_csrf');
    const conflict = await page.request.post(
      `/api/v1/portfolio/transactions/${transactionId}/compensate`,
      {
        headers: { 'X-Vertex-CSRF': csrf?.value ?? '' },
        data: { note: 'second essai (doit échouer)' },
      },
    );
    expect(conflict.status()).toBe(409);
    expect(((await conflict.json()) as { detail: { code: string } }).detail.code).toBe(
      'ALREADY_COMPENSATED',
    );
  });

  test('import CSV 3 temps : aperçu avec ligne en erreur, confirmation des lignes valides seules', async ({
    page,
  }) => {
    await page.goto('/portfolio');
    const before = await apiPortfolio(page);
    const ledgerBefore = (before['transactions'] as unknown[]).length;

    // CSV : 1 ligne valide (dépôt passé) + 1 ligne invalide (kind inconnu).
    const csv = [
      'kind,ticker,quantity,price,amount,currency,fees,effective_at,note',
      `DEPOSIT,,,,250,SYN,0,2026-08-27T09:00:00+00:00,[SYNTHETIC] import e2e ${Date.now()}`,
      'NOT_A_KIND,,,,10,SYN,0,2026-08-27T09:30:00+00:00,ligne invalide',
    ].join('\n');

    await page.getByLabel('Fichier CSV du journal').setInputFiles({
      name: 'import-demo.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csv, 'utf8'),
    });

    // Temps 2 : aperçu serveur — 1 valide, 1 en erreur, AUCUNE écriture.
    const previewBox = page.getByTestId('pf-import-preview');
    await expect(previewBox).toBeVisible({ timeout: 15_000 });
    await expect(previewBox).toContainText('2 ligne(s) lue(s), 1 valide(s), 1 en erreur');
    await expect(page.getByTestId('pf-import-error-2')).toContainText('UNKNOWN_KIND');
    expect(((await apiPortfolio(page))['transactions'] as unknown[]).length).toBe(ledgerBefore);

    // Temps 3 : confirmation — seules les lignes VALIDES sont enregistrées.
    await page
      .getByRole('button', { name: /Confirmer l'enregistrement des 1 ligne\(s\) valide\(s\)/ })
      .click();
    await expect(page.getByTestId('pf-import-recorded')).toContainText('1 ligne(s) enregistrée(s)');
    await expect(page.getByTestId('pf-import-recorded')).toContainText('IMPORT_CONFIRMED');
    await expect
      .poll(async () => ((await apiPortfolio(page))['transactions'] as unknown[]).length, {
        timeout: 15_000,
      })
      .toBe(ledgerBefore + 1);
  });

  test('export : le CSV téléchargé est celui servi par l’API', async ({ page }) => {
    await page.goto('/portfolio');
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: "Exporter le journal (CSV servi par l'API)" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('vertex-ledger.csv');
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(chunk as Buffer);
    }
    const body = Buffer.concat(chunks).toString('utf8');
    expect(body.startsWith('# vertex.portfolio-ledger-export/')).toBe(true);
    expect(body).toContain('id,kind,ticker,quantity,price,amount,currency,fees,effective_at');
  });

  test('LOT-A6 : les dix-huit modules de la planche, une seule dominante (la concentration), inspecteur du lot', async ({
    page,
  }) => {
    const before = await apiPortfolio(page);
    const lots = valuationLots(before);

    await page.goto('/portfolio');
    const grille = page.getByTestId('portfolio-grid');
    await expect(grille).toBeVisible();
    await expect(grille.locator('> [data-module]')).toHaveCount(18);
    await expect(page.locator('.vx-main [data-rank="dominant"]')).toHaveCount(1);
    await expect(page.locator('[data-module="concentration"] .vx-pf-concentration[data-rank="dominant"]')).toBeVisible();
    await expect(grille.locator('.vx-absent')).toHaveCount(8);
    for (const body of await grille.locator('[data-testid="absent-body"]').allTextContents()) {
      expect(body).not.toMatch(/\d/);
    }
    // L'exposition par devise relaie la valeur totale publiée, verbatim.
    const content = (before['valuation'] as Record<string, unknown>)['content'] as Record<string, unknown>;
    for (const block of content['positions_by_currency'] as Record<string, unknown>[]) {
      const concentration = block['concentration'] as Record<string, unknown>;
      if (concentration['status'] === 'OK') {
        await expect(page.getByTestId(`pf-currency-${String(block['currency'])}`)).toContainText(
          String(concentration['total_value']),
        );
      }
    }

    // Inspecteur : la valorisation publiée par défaut, puis le lot ouvert.
    await expect(page.getByRole('heading', { level: 2, name: 'Inspecteur — Valorisation publiée' })).toBeVisible();
    test.skip(lots.length === 0, 'aucun lot valorisé dans le pipeline courant');
    const lot = lots[0] as ValuationLot;
    await page.getByRole('button', { name: `Inspecter ${lot.ticker} (lot ${lot.lot_id})` }).click();
    const faits = page.getByTestId('pf-lot-facts');
    await expect(faits).toBeVisible();
    await expect(faits).toContainText(lot.market_value);
    await expect(page.getByRole('heading', { level: 2, name: `Inspecteur — ${lot.ticker}` })).toBeVisible();
    await page.getByRole('button', { name: 'Fermer' }).click();
    await expect(page.getByTestId('pf-snapshot-facts')).toBeVisible();
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/portfolio');
    await expect(page.getByTestId('pf-summary-grid')).toBeVisible();
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('portfolio', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé → état offline honnête, aucune donnée fabriquée', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/portfolio');
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(page.getByTestId('pf-summary-grid')).toHaveCount(0);
  });
});
