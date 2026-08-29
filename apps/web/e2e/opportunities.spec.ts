/**
 * Parcours /opportunities — snapshot `opportunities/global` réel.
 *
 * Vérifications VALEUR PAR VALEUR contre l'API : séparation DOM stricte des
 * deux groupes, répartition complète des raisons d'exclusion, statuts,
 * `profile_ref` (appliqué / non appliqué), `calendar_ref` (provenance des
 * catalyseurs), plus axe et hors ligne.
 */
import type { Page } from '@playwright/test';

import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface ApiOpportunities {
  readonly state: string;
  readonly snapshot_version: number;
  readonly content: Record<string, unknown>;
}

async function apiOpportunities(page: Page): Promise<Record<string, unknown>> {
  const response = await page.request.get('/api/v1/opportunities');
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as ApiOpportunities;
  expect(body.state).toBe('ok');
  return body.content;
}

test.describe('Page Opportunités — snapshot réel', () => {
  test('les deux groupes sont séparés dans le DOM ; aucun exclu chez les qualifiés', async ({
    page,
  }) => {
    const content = await apiOpportunities(page);
    const qualified = content['qualified'] as Record<string, unknown>[];
    const excluded = content['excluded'] as Record<string, unknown>[];
    expect(qualified.length).toBe(0);
    expect(excluded.length).toBeGreaterThanOrEqual(1);

    await page.goto('/opportunities');
    const qualifiedGroup = page.getByTestId('opp-group-qualified');
    const excludedGroup = page.getByTestId('opp-group-excluded');
    await expect(qualifiedGroup).toBeVisible({ timeout: 20_000 });
    await expect(excludedGroup).toBeVisible();
    // Séparation structurelle : aucun conteneur n'inclut l'autre.
    const nested = await page.evaluate(() => {
      const first = document.querySelector('[data-testid="opp-group-qualified"]');
      const second = document.querySelector('[data-testid="opp-group-excluded"]');
      if (first === null || second === null) {
        return true;
      }
      return first.contains(second) || second.contains(first);
    });
    expect(nested).toBe(false);
    // Chaque exclu de l'API existe DANS le groupe exclus, et nulle part ailleurs.
    for (const candidate of excluded) {
      const ticker = candidate['ticker'] as string;
      await expect(excludedGroup.getByTestId(`opp-row-excluded-${ticker}`)).toHaveCount(1);
      await expect(qualifiedGroup.getByTestId(`opp-row-excluded-${ticker}`)).toHaveCount(0);
      await expect(qualifiedGroup.getByText(ticker, { exact: true })).toHaveCount(0);
    }
    await expect(page.getByTestId('opp-empty-qualified')).toBeVisible();
  });

  test('chaque exclu publie statut, direction, raison, gates dégradées et preuves manquantes', async ({
    page,
  }) => {
    const content = await apiOpportunities(page);
    const excluded = content['excluded'] as Record<string, unknown>[];

    await page.goto('/opportunities');
    await expect(page.getByTestId('opp-group-excluded')).toBeVisible({ timeout: 20_000 });
    for (const candidate of excluded) {
      const ticker = candidate['ticker'] as string;
      const row = page.getByTestId(`opp-row-excluded-${ticker}`);
      const advice = candidate['advice'] as Record<string, unknown>;
      await expect(row).toContainText(advice['status'] as string);
      await expect(row).toContainText(advice['direction'] as string);
      const primary = candidate['primary_exclusion_reason'] as Record<string, unknown> | null;
      if (primary !== null) {
        await expect(row).toContainText(primary['gate_id'] as string);
        await expect(row).toContainText(primary['reason_code'] as string);
      }
      const exclusion = candidate['exclusion'] as Record<string, unknown> | null;
      if (exclusion !== null) {
        await expect(row).toContainText(exclusion['kind'] as string);
      }
      for (const gate of candidate['degraded_gates'] as string[]) {
        await expect(row).toContainText(gate);
      }
      for (const evidence of candidate['missing_evidence'] as string[]) {
        await expect(row).toContainText(evidence);
      }
      await expect(row).toContainText(candidate['population'] as string);
    }
  });

  test('répartition des raisons d’exclusion : chaque compteur égal à l’API', async ({ page }) => {
    const content = await apiOpportunities(page);
    const reasons = content['exclusion_reasons'] as Record<string, number>;
    const coverage = content['coverage'] as Record<string, unknown>;
    const statusCounts = coverage['status_counts'] as Record<string, number>;
    expect(Object.keys(reasons).length).toBeGreaterThanOrEqual(1);

    await page.goto('/opportunities');
    await expect(page.getByTestId('opp-exclusion-reasons')).toBeVisible({ timeout: 20_000 });
    for (const [reason, count] of Object.entries(reasons)) {
      const row = page.getByTestId(`opp-reason-${reason}`);
      await expect(row.locator('td')).toHaveText(String(count));
    }
    for (const [status, count] of Object.entries(statusCounts)) {
      const row = page.getByTestId(`opp-status-count-${status}`);
      await expect(row.locator('td')).toHaveText(String(count));
    }
    // La totalité exclue en INSUFFICIENT_DATA est le comportement VOULU :
    // l'état vide du groupe qualifié le dit, sans aucune alerte d'erreur.
    expect(statusCounts['INSUFFICIENT_DATA']).toBe(coverage['universe_size']);
    await expect(page.getByTestId('opp-empty-qualified')).toContainText('fail-closed');
    await expect(page.locator('[role="alert"]')).toHaveCount(0);
  });

  test('profile_ref : id, version, appliqué ET non appliqué distincts', async ({ page }) => {
    const content = await apiOpportunities(page);
    const profile = content['profile_ref'] as Record<string, unknown>;

    await page.goto('/opportunities');
    await expect(page.getByTestId('opp-profile')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('opp-profile-id')).toHaveText(profile['id'] as string);
    await expect(page.getByTestId('opp-profile-version')).toHaveText(profile['version'] as string);
    const applied = page.getByTestId('opp-profile-applied');
    for (const entry of profile['applied'] as string[]) {
      await expect(applied).toContainText(entry);
    }
    const notApplied = page.getByTestId('opp-profile-not-applied');
    for (const entry of profile['not_applied'] as Record<string, unknown>[]) {
      await expect(notApplied).toContainText(entry['field'] as string);
      await expect(notApplied).toContainText(entry['reason'] as string);
    }
    // Les deux listes ne se confondent pas.
    for (const entry of profile['not_applied'] as Record<string, unknown>[]) {
      await expect(applied).not.toContainText(entry['reason'] as string);
    }
  });

  test('calendar_ref : statut, version et as_of affichés comme provenance', async ({ page }) => {
    const content = await apiOpportunities(page);
    const reference = content['calendar_ref'] as Record<string, unknown>;

    await page.goto('/opportunities');
    const block = page.getByTestId('opp-calendar-ref');
    await expect(block).toBeVisible({ timeout: 20_000 });
    await expect(block).toHaveAttribute('data-status', reference['status'] as string);
    await expect(page.getByTestId('opp-calref-status')).toHaveText(reference['status'] as string);
    await expect(page.getByTestId('opp-calref-version')).toHaveText(
      String(reference['version']),
    );
    await expect(block).toContainText(reference['snapshot_as_of'] as string);
    await expect(block).toContainText(reference['content_schema_version'] as string);
    await expect(block).toContainText(String(reference['events_upcoming']));
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/opportunities');
    await expect(page.getByTestId('opp-group-excluded')).toBeVisible({ timeout: 20_000 });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('opportunities', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé → état offline honnête, aucun groupe affiché', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/opportunities');
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(page.getByTestId('opp-group-qualified')).toHaveCount(0);
    await expect(page.getByTestId('opp-group-excluded')).toHaveCount(0);
  });
});
