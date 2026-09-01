/**
 * Parcours /options/:underlying — chaîne réelle (snapshot option_chain publié
 * par le worker sur les tranches SYNTHETIC semées), groupes (expiration,
 * trading_class) jamais fusionnés, cellules vérifiées VALEUR PAR VALEUR
 * contre la réponse API, IV absente ≠ 0, inspecteur avec lignée
 * CalculationRecord, axe et état hors ligne.
 */
import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface ApiContract {
  con_id: number | null;
  strike: string | null;
  right: 'CALL' | 'PUT' | null;
  quote: { bid: string | null; ask: string | null; status: string };
  iv: { status: string; value?: string; reason?: string };
  greeks: { status: string; delta?: string };
}

interface ApiGroup {
  expiration: string;
  trading_class: string;
  exchange: string;
  quality: string;
  contracts: ApiContract[];
  coverage: { expected: number; quotes_valid: number; iv_resolved: number };
}

interface ApiChain {
  state: string;
  population: string | null;
  underlying: string;
  expirations: ApiGroup[];
  row_budget: { max_rows: number; total_rows: number; published_rows: number; truncated_rows: number } | null;
  spot: { value: string } | null;
}

const UNDERLYING = 'SYN-TECH-01';

async function fetchChain(page: import('@playwright/test').Page): Promise<ApiChain> {
  const response = await page.request.get(`/api/v1/options/${UNDERLYING}/chain`);
  expect(response.ok()).toBe(true);
  const chain = (await response.json()) as ApiChain;
  expect(chain.state).toBe('ok');
  return chain;
}

test.describe('Page Options — chaîne, groupes jamais fusionnés, inspecteur', () => {
  test('groupes distincts par (expiration, trading_class) + budget de lignes affiché', async ({
    page,
  }) => {
    const chain = await fetchChain(page);
    expect(chain.population).toBe('SYNTHETIC');
    // Le seed publie 3 groupes dont DEUX partagent la même date d'expiration.
    expect(chain.expirations).toHaveLength(3);
    const near = chain.expirations.filter(
      (group) => group.expiration === chain.expirations[0]!.expiration,
    );
    expect(near).toHaveLength(2);
    expect(new Set(near.map((group) => group.trading_class)).size).toBe(2);

    await page.goto(`/options/${UNDERLYING}`);
    await expect(page.getByText('DONNÉES SYNTHÉTIQUES', { exact: true })).toBeVisible();
    const groups = page.getByTestId('chain-group');
    await expect(groups).toHaveCount(3);
    // Deux entrées distinctes pour la même date : jamais fusionnées. Le
    // libellé COMPLET (date · classe (exchange)) distingue SYN-TECH-01 de
    // SYN-TECH-01W sans collision de sous-chaîne.
    for (const group of chain.expirations) {
      await expect(
        groups.filter({
          hasText: `${group.expiration} · ${group.trading_class} (${group.exchange})`,
        }),
      ).toHaveCount(1);
    }
    // Couverture par groupe et budget publiés, affichés.
    const first = chain.expirations[0]!;
    await expect(groups.first()).toContainText(`${first.coverage.expected} contrats attendus`);
    await expect(groups.first()).toContainText(`${first.coverage.iv_resolved} IV résolues`);
    const budget = chain.row_budget!;
    await expect(page.getByTestId('chain-row-budget')).toContainText(
      `${budget.published_rows} publiée(s) / ${budget.total_rows} construite(s), plafond ${budget.max_rows}, ${budget.truncated_rows} tronquée(s)`,
    );
  });

  test('table Calls | Strike | Puts : cellules exactes valeur par valeur contre l’API', async ({
    page,
  }) => {
    const chain = await fetchChain(page);
    const group = chain.expirations[0]!; // groupe affiché par défaut
    await page.goto(`/options/${UNDERLYING}`);
    const table = page.getByRole('table', {
      name: `Chaîne d'options ${group.expiration} ${group.trading_class}`,
    });
    await expect(table).toBeVisible();

    // 12 strikes = 12 lignes (24 contrats appariés CALL/PUT).
    const strikes = [...new Set(group.contracts.map((entry) => entry.strike))].filter(
      (strike): strike is string => strike !== null,
    );
    await expect(table.locator('tbody tr')).toHaveCount(strikes.length);

    // Vérification VALEUR PAR VALEUR d'au moins 5 cellules (bid/ask/IV/delta),
    // sur 3 strikes distincts, contre les chaînes serveur verbatim.
    let checkedCells = 0;
    for (const strike of strikes.slice(0, 3)) {
      const call = group.contracts.find((c) => c.strike === strike && c.right === 'CALL')!;
      const put = group.contracts.find((c) => c.strike === strike && c.right === 'PUT')!;
      const row = table.locator('tbody tr', {
        has: page.locator('th', { hasText: strike }),
      });
      const cells = row.locator('td');
      // CALL : bid, ask, IV, delta (indices 0..3) ; PUT : 5..8.
      for (const [index, contract, key] of [
        [0, call, 'bid'],
        [1, call, 'ask'],
        [5, put, 'bid'],
        [6, put, 'ask'],
      ] as const) {
        const value = contract.quote[key];
        if (value !== null) {
          await expect(cells.nth(index)).toContainText(value);
          checkedCells += 1;
        }
      }
      if (call.iv.status === 'OK') {
        await expect(cells.nth(2)).toContainText(call.iv.value!);
        checkedCells += 1;
      }
      if (call.greeks.status === 'OK') {
        await expect(cells.nth(3)).toContainText(call.greeks.delta!);
        checkedCells += 1;
      }
    }
    expect(checkedCells).toBeGreaterThanOrEqual(5);
  });

  test('IV absente : « — » avec la raison typée au survol, jamais 0', async ({ page }) => {
    const chain = await fetchChain(page);
    const group = chain.expirations[0]!;
    // Le seed dégrade volontairement ce groupe : au moins une IV ABSENT.
    const absent = group.contracts.find((entry) => entry.iv.status === 'ABSENT');
    expect(absent).toBeDefined();
    await page.goto(`/options/${UNDERLYING}`);
    const table = page.getByRole('table', {
      name: `Chaîne d'options ${group.expiration} ${group.trading_class}`,
    });
    await expect(table).toBeVisible();
    const cell = table.getByLabel(new RegExp(absent!.iv.reason!)).first();
    await expect(cell).toHaveText('—');
    await expect(cell).toHaveAttribute('title', new RegExp(absent!.iv.reason!));
    // La quote croisée du seed est marquée par son statut EN TEXTE.
    await expect(table.locator('.vx-quote-status', { hasText: 'CROSSED' }).first()).toBeVisible();
  });

  test('inspecteur : identité complète, THÉORIQUE et CalculationRecord, Échap referme', async ({
    page,
  }) => {
    const chain = await fetchChain(page);
    const group = chain.expirations[0]!;
    const resolved = group.contracts.find(
      (entry) => entry.iv.status === 'OK' && entry.right === 'CALL',
    )!;
    await page.goto(`/options/${UNDERLYING}`);
    await page
      .getByRole('button', {
        name: `Inspecter CALL strike ${resolved.strike} ${group.expiration} ${group.trading_class}`,
      })
      .click();
    const inspector = page.getByTestId('option-inspector');
    await expect(inspector).toBeVisible();
    await expect(inspector).toContainText(String(resolved.con_id));
    await expect(inspector).toContainText(resolved.iv.value!); // IV verbatim
    await expect(inspector.getByText('THÉORIQUE').first()).toBeVisible();
    await expect(inspector).toContainText('options.implied_volatility');
    await expect(inspector).toContainText('options.greeks');
    await expect(inspector).toContainText('sha256:'); // input/result hashes
    // LOT-13 : le panneau n'est plus modal. Il ne doit donc PAS piéger le
    // clavier — un piège n'est correct que quand le reste de la page est
    // inerte, ce qui n'est plus le cas.
    await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    await expect(page.locator('[aria-modal]')).toHaveCount(0);
    let sorti = false;
    for (let index = 0; index < 20 && !sorti; index += 1) {
      await page.keyboard.press('Tab');
      sorti = !(await inspector.evaluate((element) => element.contains(document.activeElement)));
    }
    expect(sorti).toBe(true);

    // CONSERVÉ : Échap referme le panneau.
    await inspector.getByRole('button', { name: 'Fermer' }).focus();
    await page.keyboard.press('Escape');
    await expect(inspector).toHaveCount(0);
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto(`/options/${UNDERLYING}`);
    await expect(page.getByRole('table').first()).toBeVisible();
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('options', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé (routes /api interrompues) → état offline honnête', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto(`/options/${UNDERLYING}`);
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(page.getByRole('table')).toHaveCount(0);
  });
});
