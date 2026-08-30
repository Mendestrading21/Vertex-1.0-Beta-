/**
 * Parcours /calendar — snapshot `calendar/global` réel publié par le worker.
 *
 * Vérifications VALEUR PAR VALEUR contre l'API (au moins 5 événements) :
 * statut, instant UTC, heure locale de place, fuseau IANA, rang et code
 * d'importance. Puis : libellés estimé/confirmé strictement distincts,
 * valeurs antérieures lisibles sur les événements révisés, compteurs servis
 * vs totaux du snapshot, refus typés de fenêtre, axe et hors ligne.
 */
import type { Page } from '@playwright/test';

import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface ApiCalendar {
  readonly state: string;
  readonly snapshot_version: number;
  readonly population: string;
  readonly agenda: readonly Record<string, unknown>[];
  readonly categories: Record<string, number>;
  readonly statuses: Record<string, number>;
  readonly coverage: Record<string, unknown>;
  readonly window: Record<string, unknown>;
  readonly importance_rule: Record<string, unknown>;
}

async function apiCalendar(page: Page, query = ''): Promise<ApiCalendar> {
  const response = await page.request.get(`/api/v1/calendar${query}`);
  expect(response.ok()).toBe(true);
  return (await response.json()) as ApiCalendar;
}

test.describe('Page Calendrier — snapshot réel', () => {
  test('agenda servi : au moins 5 événements identiques valeur par valeur à l’API', async ({
    page,
  }) => {
    const body = await apiCalendar(page);
    expect(body.state).toBe('ok');
    expect(body.population).toBe('SYNTHETIC');
    expect(body.agenda.length).toBeGreaterThanOrEqual(5);

    await page.goto('/calendar');
    await expect(page.getByTestId('cal-agenda')).toBeVisible({ timeout: 20_000 });

    const checked = body.agenda.slice(0, 5);
    expect(checked.length).toBe(5);
    for (const event of checked) {
      const id = event['event_id'] as string;
      const card = page.getByTestId(`cal-event-${id}`);
      await expect(card).toBeVisible();
      // Statut : attribut ET libellé distinct, jamais la couleur seule.
      await expect(card).toHaveAttribute('data-status', event['status'] as string);
      const expectedLabel = event['status'] === 'ESTIMATED' ? 'Estimé' : 'Confirmé';
      await expect(page.getByTestId(`cal-head-${id}`)).toContainText(expectedLabel);
      // Les trois lectures du temps, verbatim pour les deux chaînes serveur.
      const times = page.getByTestId(`cal-times-${id}`);
      await expect(times).toContainText(event['event_time_utc'] as string);
      await expect(times).toContainText(event['event_time_local'] as string);
      await expect(times).toContainText(event['exchange_timezone'] as string);
      // Importance : rang + code + version de règle publiés.
      const importance = event['importance'] as Record<string, unknown>;
      const importanceCell = page.getByTestId(`cal-importance-${id}`);
      await expect(importanceCell).toContainText(`rang ${String(importance['rank'])}`);
      await expect(importanceCell).toContainText(importance['code'] as string);
      await expect(importanceCell).toContainText(importance['rule_version'] as string);
    }
  });

  test('estimé et confirmé ne partagent jamais le même libellé', async ({ page }) => {
    const body = await apiCalendar(page);
    const estimated = body.agenda.filter((event) => event['status'] === 'ESTIMATED');
    const confirmed = body.agenda.filter((event) => event['status'] === 'CONFIRMED');
    expect(estimated.length).toBeGreaterThanOrEqual(1);
    expect(confirmed.length).toBeGreaterThanOrEqual(1);

    await page.goto('/calendar');
    await expect(page.getByTestId('cal-agenda')).toBeVisible({ timeout: 20_000 });
    const estimatedHead = page.getByTestId(`cal-head-${estimated[0]!['event_id'] as string}`);
    await expect(estimatedHead).toContainText('Estimé');
    await expect(estimatedHead).not.toContainText('Confirmé');
    const confirmedHead = page.getByTestId(`cal-head-${confirmed[0]!['event_id'] as string}`);
    await expect(confirmedHead).toContainText('Confirmé');
    await expect(confirmedHead).not.toContainText('Estimé');
  });

  test('événements révisés : valeurs antérieures (statut et instant) restées lisibles', async ({
    page,
  }) => {
    const body = await apiCalendar(page);
    const revised = body.agenda.filter((event) => event['revised'] === true);
    expect(revised.length).toBeGreaterThanOrEqual(1);

    await page.goto('/calendar');
    await expect(page.getByTestId('cal-agenda')).toBeVisible({ timeout: 20_000 });
    for (const event of revised) {
      const id = event['event_id'] as string;
      const details = page.getByTestId(`cal-revision-${id}`);
      await details.locator('summary').click();
      const previousValues = event['previous_values'] as Record<string, unknown>[];
      for (const previous of previousValues) {
        await expect(details).toContainText(previous['event_time_utc'] as string);
        await expect(details).toContainText(
          previous['status'] === 'ESTIMATED' ? 'Estimé' : 'Confirmé',
        );
      }
      const revisions = event['revisions'] as Record<string, unknown>[];
      for (const revision of revisions) {
        await expect(details).toContainText(revision['previous_event_time_utc'] as string);
      }
      // La valeur COURANTE reste distincte de l'antérieure.
      await expect(page.getByTestId(`cal-times-${id}`)).toContainText(
        event['event_time_utc'] as string,
      );
    }
  });

  test('compteurs : liste servie ≠ totaux du snapshot, chacun étiqueté', async ({ page }) => {
    const body = await apiCalendar(page);
    const windowEcho = body.window;

    await page.goto('/calendar');
    await expect(page.getByTestId('cal-counters')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('cal-count-served')).toHaveText(
      String(windowEcho['events_in_window']),
    );
    await expect(page.getByTestId('cal-count-total')).toHaveText(
      String(windowEcho['events_total']),
    );
    const servedCategories = windowEcho['categories'] as Record<string, number>;
    for (const [category, count] of Object.entries(body.categories)) {
      const row = page.getByTestId(`cal-counter-category-${category}`);
      const cells = row.locator('td');
      await expect(cells.nth(0)).toHaveText(String(servedCategories[category] ?? 0));
      await expect(cells.nth(1)).toHaveText(String(count));
    }
    for (const [status, count] of Object.entries(body.statuses)) {
      const row = page.getByTestId(`cal-counter-status-${status}`);
      await expect(row.locator('td').nth(1)).toHaveText(String(count));
    }
  });

  test('fenêtre appliquée : la liste servie est celle de l’API, avec ses propres compteurs', async ({
    page,
  }) => {
    const full = await apiCalendar(page);
    const instants = full.agenda
      .map((event) => event['event_time_utc'] as string)
      .sort((left, right) => left.localeCompare(right));
    const from = instants[0]!;
    const to = instants[Math.min(1, instants.length - 1)]!;
    const query = `?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
    const windowed = await apiCalendar(page, query);
    expect(windowed.window['applied']).toBe(true);

    await page.goto(`/calendar${query}`);
    await expect(page.getByTestId('cal-agenda')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('cal-count-served')).toHaveText(
      String(windowed.window['events_in_window']),
    );
    await expect(page.getByTestId('cal-count-total')).toHaveText(
      String(windowed.window['events_total']),
    );
    for (const event of windowed.agenda) {
      await expect(page.getByTestId(`cal-event-${event['event_id'] as string}`)).toBeVisible();
    }
  });

  test('fenêtre valide ne sélectionnant rien : état empty_window explicite', async ({ page }) => {
    const query = '?from=2020-01-01T00:00:00Z&to=2020-02-01T00:00:00Z';
    const body = await apiCalendar(page, query);
    expect(body.state).toBe('empty_window');
    expect(body.agenda.length).toBe(0);

    await page.goto(`/calendar${query}`);
    const boundary = page.locator('[data-state="empty"]');
    await expect(boundary).toBeVisible({ timeout: 20_000 });
    await expect(boundary).toContainText('Fenêtre demandée');
    await expect(page.getByTestId('cal-agenda')).toHaveCount(0);
    // Ce n'est ni un refus de droit, ni une erreur.
    await expect(page.getByTestId('cal-blocked')).toHaveCount(0);
    await expect(page.getByTestId('cal-window-error')).toHaveCount(0);
  });

  test('les 4 refus typés de fenêtre sont affichés en clair', async ({ page }) => {
    const cases: readonly { readonly query: string; readonly code: string }[] = [
      { query: '?from=2026-09-01T00:00:00Z', code: 'WINDOW_INCOMPLETE' },
      {
        query: '?from=2026-09-01T00:00:00&to=2026-09-10T00:00:00',
        code: 'WINDOW_NAIVE_DATETIME',
      },
      {
        query: '?from=2026-09-10T00:00:00Z&to=2026-09-01T00:00:00Z',
        code: 'WINDOW_INVERTED',
      },
      {
        query: '?from=2026-01-01T00:00:00Z&to=2026-12-31T00:00:00Z',
        code: 'WINDOW_TOO_LARGE',
      },
    ];
    for (const entry of cases) {
      // Le serveur produit RÉELLEMENT ce refus typé.
      const response = await page.request.get(`/api/v1/calendar${entry.query}`);
      expect(response.status()).toBe(422);
      const body = (await response.json()) as { detail: { code: string } };
      expect(body.detail.code).toBe(entry.code);

      await page.goto(`/calendar${entry.query}`);
      const error = page.getByTestId('cal-window-error');
      await expect(error).toBeVisible({ timeout: 20_000 });
      await expect(error).toContainText(entry.code);
      await expect(page.getByTestId('cal-agenda')).toHaveCount(0);
    }
  });

  test('filtres persistés en URL : catégorie et statut', async ({ page }) => {
    const body = await apiCalendar(page);
    const servedStatuses = body.window['statuses'] as Record<string, number>;
    await page.goto('/calendar');
    await expect(page.getByTestId('cal-agenda')).toBeVisible({ timeout: 20_000 });
    await page.getByRole('combobox', { name: 'Statut de date' }).selectOption('ESTIMATED');
    await expect(page).toHaveURL(/status=ESTIMATED/);
    await expect(page.getByTestId('cal-filter-count')).toContainText(
      `${servedStatuses['ESTIMATED']} événement`,
    );
    for (const event of body.agenda.filter((entry) => entry['status'] === 'CONFIRMED')) {
      await expect(page.getByTestId(`cal-event-${event['event_id'] as string}`)).toHaveCount(0);
    }
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/calendar');
    await expect(page.getByTestId('cal-agenda')).toBeVisible({ timeout: 20_000 });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('calendar', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé → état offline honnête, aucun agenda affiché', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/calendar');
    const boundary = page.locator('[data-state="offline"]');
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');
    await expect(page.getByTestId('cal-agenda')).toHaveCount(0);
    await expect(page.getByTestId('cal-blocked')).toHaveCount(0);
  });
});
