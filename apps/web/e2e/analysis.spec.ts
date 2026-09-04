/**
 * Parcours /analysis/:instrument — dossier réel (snapshot analysis publié par
 * le worker sur les 60 barres SYNTHETIC semées) : chandeliers Lightweight
 * Charts avec ATTRIBUTION TradingView visible, table OHLCV vérifiée VALEUR
 * PAR VALEUR contre l'API, AdviceCard honnête (INSUFFICIENT_DATA attendu),
 * axe et état hors ligne.
 */
import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface ApiBar {
  trading_day: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
}

interface ApiAnalysis {
  state: string;
  population: string | null;
  bars: { status: string; count: number; currency: string | null; bars: ApiBar[] } | null;
  advice: {
    status: string;
    direction: string;
    gates: {
      gate_id: string;
      status: string;
      reason_code: string;
      observed_values?: Record<string, unknown>;
      thresholds?: Record<string, unknown>;
    }[];
  } | null;
  scenarios: { status: string; reason?: string } | null;
}

const INSTRUMENT = 'SYN-TECH-01';

async function fetchAnalysis(page: import('@playwright/test').Page): Promise<ApiAnalysis> {
  const response = await page.request.get(`/api/v1/analysis/${INSTRUMENT}`);
  expect(response.ok()).toBe(true);
  const analysis = (await response.json()) as ApiAnalysis;
  expect(analysis.state).toBe('ok');
  return analysis;
}

test.describe('Page Analyse — chandeliers, table équivalente, AdviceCard', () => {
  test('dominante rendue (canvas Lightweight Charts) + attribution TradingView visible', async ({
    page,
  }) => {
    const analysis = await fetchAnalysis(page);
    expect(analysis.population).toBe('SYNTHETIC');
    expect(analysis.bars?.count).toBe(60);

    await page.goto(`/analysis/${INSTRUMENT}`);
    // Le moteur crée un vrai canvas dans le conteneur dédié.
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.locator('main').getByText('DONNÉES SYNTHÉTIQUES', { exact: true })).toBeVisible();
    // ATTRIBUTION obligatoire : mention TradingView VISIBLE dans la légende du
    // cadre ET dans le pied de méthode (le moteur ajoute en plus son propre
    // logo-lien « Charting by TradingView », jamais retiré).
    for (const scope of ['.vx-candles-attribution', '.vx-chartframe-foot']) {
      const link = page.locator(`${scope} a`, { hasText: 'TradingView' }).first();
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute('href', 'https://www.tradingview.com/');
    }
    await expect(page.getByText(/Lightweight Charts™/).first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Charting by TradingView' })).toBeVisible();
  });

  test('table OHLCV équivalente : 60 lignes, 5 barres vérifiées valeur par valeur', async ({
    page,
  }) => {
    const analysis = await fetchAnalysis(page);
    const bars = analysis.bars!.bars;
    expect(bars).toHaveLength(60);

    await page.goto(`/analysis/${INSTRUMENT}`);
    const table = page.getByRole('table', { name: 'Table OHLCV équivalente des chandeliers' });
    await expect(table).toBeVisible();
    await expect(table.locator('tbody tr')).toHaveCount(60);

    // 5 barres (première, dernière et trois intermédiaires) : chaînes exactes.
    for (const bar of [bars[0]!, bars[14]!, bars[29]!, bars[44]!, bars[59]!]) {
      const row = table.locator('tbody tr', {
        has: page.locator(`time[datetime="${bar.trading_day}"]`),
      });
      const cells = row.locator('td');
      await expect(cells.nth(0)).toHaveText(bar.open);
      await expect(cells.nth(1)).toHaveText(bar.high);
      await expect(cells.nth(2)).toHaveText(bar.low);
      await expect(cells.nth(3)).toHaveText(bar.close);
      await expect(cells.nth(4)).toHaveText(String(bar.volume));
    }
  });

  test('AdviceCard honnête : statut publié tel quel, direction séparée, gates dépliables', async ({
    page,
  }) => {
    const analysis = await fetchAnalysis(page);
    const advice = analysis.advice!;
    // Population synthétique : le moteur publie INSUFFICIENT_DATA (fail-closed).
    expect(advice.status).toBe('INSUFFICIENT_DATA');
    expect(advice.direction).toBe('UNKNOWN');

    await page.goto(`/analysis/${INSTRUMENT}`);
    const card = page.getByTestId('advice-card');
    await expect(card).toBeVisible();
    await expect(card.locator('.vx-advice-status')).toHaveText(advice.status);
    await expect(card.locator('.vx-advice-direction')).toHaveText(advice.direction);

    // Gates : résumé (compte exact) puis détail avec les reason_codes exacts.
    const blocked = advice.gates.filter((gate) => gate.status !== 'PASS');
    const summary = card.locator('summary');
    await expect(summary).toContainText(
      `${advice.gates.length} évaluées, ${blocked.length} non passées`,
    );
    await summary.click();
    for (const gate of advice.gates.slice(0, 4)) {
      // Portée .vx-advice-gates : les limitations citent aussi des gate_ids.
      const item = card.locator('.vx-advice-gates li', { hasText: gate.gate_id }).first();
      await expect(item).toContainText(gate.status);
      await expect(item).toContainText(gate.reason_code);
    }
    // Les gates non évaluables restent BLOCK UNEVALUABLE, affichées telles quelles.
    await expect(
      card.locator('.vx-advice-gates li', { hasText: 'UNEVALUABLE' }).first(),
    ).toBeVisible();

    // LOT P2b — LA PREUVE SERVIE EST LUE, ET COMPARÉE À L'API. Chaque couple
    // `observed_values` / `thresholds` que le dossier publie doit être lisible
    // DANS la gate qui l'a produit. L'assertion est faite depuis la réponse
    // réelle, jamais depuis une liste écrite à la main.
    let couplesPublies = 0;
    for (const gate of advice.gates) {
      const item = card.locator('.vx-advice-gates li', { hasText: gate.gate_id }).first();
      for (const dictionnaire of [gate.observed_values ?? {}, gate.thresholds ?? {}]) {
        for (const [cle, valeur] of Object.entries(dictionnaire)) {
          couplesPublies += 1;
          await expect(item, `${gate.gate_id}.${cle}`).toContainText(cle);
          // Scalaires seulement : le reste est avoué « non reconnue » côté
          // affichage, et cette boucle ne prétend pas le contraire.
          if (typeof valeur === 'string' || typeof valeur === 'number' || typeof valeur === 'boolean') {
            await expect(item, `${gate.gate_id}.${cle}=${String(valeur)}`).toContainText(
              String(valeur),
            );
          }
        }
      }
    }
    // Une boucle vide serait une assertion vide : le dossier DOIT publier de
    // la preuve, sinon ce lot n'a rien rendu visible et le test doit le dire.
    expect(couplesPublies).toBeGreaterThan(0);
  });

  test('scénarios : bloc relayé tel que publié (THÉORIQUE ou raison d’absence)', async ({
    page,
  }) => {
    const analysis = await fetchAnalysis(page);
    await page.goto(`/analysis/${INSTRUMENT}`);
    if (analysis.scenarios?.status === 'OK') {
      const section = page.locator('.vx-scenarios');
      await expect(section.getByText('THÉORIQUE', { exact: true })).toBeVisible();
      await expect(
        section.getByRole('table', { name: /Grille de scénarios théorique/ }),
      ).toBeVisible();
    } else {
      await expect(page.getByTestId('scenarios-absent')).toContainText(
        analysis.scenarios?.reason ?? '',
      );
    }
  });

  test('LOT-A4 : les DIX-NEUF modules de la planche §4, une dominante, absences motivées, inspecteur du dossier', async ({
    page,
  }) => {
    const analysis = await fetchAnalysis(page);
    await page.goto(`/analysis/${INSTRUMENT}`);
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({ timeout: 15_000 });
    const MODULES = [
      'instrument-header',
      'identity-facts',
      'chart',
      'indicators',
      'oscillators',
      'regime',
      'fundamental-quality',
      'valuation',
      'financials',
      'model-confidence',
      'analyst-revisions',
      'verdict',
      'scenarios',
      'upcoming-catalysts',
      'key-risks',
      'peers',
      'evidence',
      'levels',
      'contradictions',
    ];
    for (const module of MODULES) {
      await expect(page.locator(`[data-module="${module}"]`).first(), module).toBeVisible();
    }
    await expect(page.locator('.vx-main [data-rank="dominant"]')).toHaveCount(1);
    // LOT P2 — huit → SEPT. Le module « Oscillateurs » déclarait « le
    // registre des calculs ne publie aucun oscillateur » ; le worker publie
    // RSI et MACD depuis le LOT-S6. Même assertion, sur un compte devenu
    // juste — et le module rend désormais ce qui est servi.
    await expect(page.locator('.vx-absent-badge')).toHaveCount(7);
    await expect(page.getByTestId('analysis-rsi')).toBeVisible();
    await expect(page.getByTestId('analysis-macd')).toBeVisible();
    for (const corps of await page.locator('.vx-absent-body').allTextContents()) {
      expect(corps).not.toMatch(/\d/);
    }
    // L'en-tête porte la dernière clôture PUBLIÉE du dossier et une série tracée.
    const lastClose = analysis.bars!.bars[analysis.bars!.bars.length - 1]!.close;
    await expect(page.getByTestId('instrument-header-price')).toContainText(lastClose.replace('.', ','));
    await expect(page.getByTestId('instrument-header').getByTestId('spark-line')).toBeVisible();
    // Faits SEC : aucun snapshot semé → état vide HONNÊTE, rien à la place.
    const sec = await (await page.request.get(`/api/v1/sources/sec/${INSTRUMENT}/fundamentals`)).json();
    if (sec.state === 'empty') {
      await expect(page.getByTestId('sec-empty')).toBeVisible();
    } else {
      await expect(page.getByTestId('sec-facts')).toBeVisible();
    }
    // Inspecteur du dossier + panneau d'explication : deux panneaux, le premier est le dossier.
    await expect(page.locator('.vx-inspector-heading').first()).toHaveText(`Inspecteur — Dossier ${INSTRUMENT}`);
    await expect(page.getByTestId('analysis-dossier-facts')).toBeVisible();
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto(`/analysis/${INSTRUMENT}`);
    await expect(page.locator('.vx-candles-canvas canvas').first()).toBeVisible({
      timeout: 15_000,
    });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('analysis', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé (routes /api interrompues) → état offline honnête', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto(`/analysis/${INSTRUMENT}`);
    // Locator STRICT et non `.first()` : depuis le LOT-12, le panneau
    // d'explication n'est monté que si le dossier est chargé. Hors ligne il ne
    // l'est pas, donc il ne doit y avoir QU'UN seul état hors ligne sur la
    // page. Un `.first()` masquerait un second panneau dégradé surnuméraire.
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(page.getByRole('table')).toHaveCount(0);
    await expect(page.locator('.vx-candles-canvas')).toHaveCount(0);
  });
});
