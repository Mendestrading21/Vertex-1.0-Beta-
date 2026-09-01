/**
 * Parcours /catalysts — destination créée au LOT-10, qui ABSORBE l'ancienne
 * page /follow-up (docs/05-design/PAGE_ARBITRATION.md).
 *
 * Règle 3 de l'arbitrage : les assertions du module de revue sont DÉPLACÉES,
 * pas supprimées. Seule la route visitée change ; ce que chaque test vérifie
 * est identique. La timeline des catalyseurs est testée à part, plus bas.
 *
 * Module de revue — file de revues réelle (snapshot publié par le worker
 * sur les thèses semées) : ordre serveur, badge « nouvelle information »
 * avec raison, fiche thèse (invalidation), nouvelle thèse via le formulaire
 * (idempotency_key client) qui APPARAÎT dans la file, revue qui fait
 * disparaître le badge, axe et offline.
 *
 * Le journal des thèses est append-only et partagé entre les trois projets
 * de viewport : les assertions se réfèrent à l'état courant lu sur l'API
 * (le badge de la thèse semée disparaît à la PREMIÈRE revue et reste absent
 * ensuite — les deux états sont vérifiés honnêtement).
 */
import type { Page } from '@playwright/test';

import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface QueueThesis {
  readonly thesis: { readonly id: number; readonly title: string };
  readonly state: { readonly revision_count: number };
  readonly has_new_information: boolean;
}

async function apiQueue(page: Page): Promise<Record<string, unknown>> {
  const response = await page.request.get('/api/v1/follow-up/queue');
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as Record<string, unknown>;
  expect(body['state']).toBe('ok');
  return body['content'] as Record<string, unknown>;
}

function seededDueThesis(content: Record<string, unknown>): QueueThesis {
  const theses = content['theses'] as QueueThesis[];
  const found = theses.find((entry) =>
    entry.thesis.title.includes('These due - surveiller SYN7'),
  );
  expect(found).toBeDefined();
  return found!;
}

test.describe('Catalyseurs — module de revue (ex-page /follow-up)', () => {
  test('populations séparées, file due ordonnée par le serveur, provenance du contexte', async ({
    page,
  }) => {
    const content = await apiQueue(page);
    const due = content['due'] as { thesis_id: number; rank: number }[];
    expect(due.length).toBeGreaterThanOrEqual(1);

    await page.goto('/catalysts');
    const populations = page.getByTestId('fu-populations');
    await expect(populations).toContainText('USER_DECLARED');
    await expect(populations).toContainText('SYNTHETIC');

    // La liste due rend EXACTEMENT les entrées publiées, dans l'ordre.
    const list = page.getByTestId('fu-due-list');
    await expect(list.locator('> li')).toHaveCount(due.length);
    for (const entry of due) {
      await expect(page.getByTestId(`fu-due-${entry.thesis_id}`)).toBeVisible();
    }
    await expect(page.getByText(/effective_review_due_at asc/)).toBeVisible();
  });

  test('fiche thèse : invalidation, état projeté serveur, historique honnête', async ({ page }) => {
    const content = await apiQueue(page);
    const seeded = seededDueThesis(content);

    await page.goto('/catalysts');
    await page
      .getByTestId(`fu-due-${seeded.thesis.id}`)
      .getByRole('button')
      .click();
    const sheet = page.getByTestId('thesis-sheet');
    await expect(sheet).toBeVisible();
    await expect(sheet.getByTestId('thesis-invalidation')).toContainText(
      'Invalidee si la cloture synthetique retombe sous 90.',
    );
    await expect(sheet).toContainText('ACTIVE');
    await expect(sheet).toContainText(`${seeded.state.revision_count} révision(s) au total`);
    // Pas de timeline inventée : l'API ne sert pas l'historique ligne à ligne.
    await expect(sheet).toContainText('NON DISPONIBLE');

    // Échap referme le panneau.
    await page.keyboard.press('Escape');
    await expect(sheet).toHaveCount(0);
  });

  test('nouvelle thèse (invalidation obligatoire) → apparaît dans la file publiée', async ({
    page,
  }) => {
    const before = await apiQueue(page);
    const totalBefore = (before['theses'] as unknown[]).length;
    const title = `[SYNTHETIC] These E2E ${Date.now()}`;

    await page.goto('/catalysts');
    await page.getByLabel('Titre').fill(title);
    await page.getByLabel(/Hypothèses/).fill('[SYNTHETIC] Hypothese saisie par le test E2E.');
    await page.getByLabel(/Invalidation \(OBLIGATOIRE/).fill('[SYNTHETIC] Invalidee si Y.');
    await page.getByRole('button', { name: 'Enregistrer la thèse' }).click();
    await expect(page.getByTestId('thesis-form-created')).toBeVisible();

    // Le worker republie la file : la thèse apparaît côté API puis côté UI.
    await expect
      .poll(async () => ((await apiQueue(page))['theses'] as unknown[]).length, {
        timeout: 20_000,
      })
      .toBe(totalBefore + 1);
    await expect(page.getByRole('button', { name: title })).toBeVisible({ timeout: 20_000 });
  });

  test('revue faite → le badge « nouvelle information » disparaît de la thèse semée', async ({
    page,
  }) => {
    const before = await apiQueue(page);
    const seededBefore = seededDueThesis(before);
    const revisionsBefore = seededBefore.state.revision_count;

    await page.goto('/catalysts');
    const badge = page.getByTestId(`fu-new-info-${seededBefore.thesis.id}`);
    if (seededBefore.has_new_information) {
      // Première revue (1er projet de viewport) : le badge est encore là,
      // avec sa raison machine publiée par le worker.
      await expect(badge).toBeVisible();
      await expect(page.getByTestId(`fu-due-${seededBefore.thesis.id}`)).toContainText(
        'NEW_INFORMATION_SINCE_LAST_REVIEW',
      );
    } else {
      // Projets suivants : déjà revue, le badge est resté absent (append-only).
      await expect(badge).toHaveCount(0);
    }

    await page
      .getByTestId(`fu-due-${seededBefore.thesis.id}`)
      .getByRole('button')
      .click();
    const sheet = page.getByTestId('thesis-sheet');
    await sheet.getByRole('button', { name: 'Revue faite' }).click();
    await sheet.getByRole('button', { name: 'Enregistrer la révision' }).click();
    await expect(sheet.getByText(/Révision « Revue faite » enregistrée/)).toBeVisible();

    // La file republiée reflète la révision : +1 révision, plus de nouveauté.
    await expect
      .poll(
        async () => {
          const content = await apiQueue(page);
          const entry = seededDueThesis(content);
          return { revisions: entry.state.revision_count, newInfo: entry.has_new_information };
        },
        { timeout: 20_000 },
      )
      .toEqual({ revisions: revisionsBefore + 1, newInfo: false });

    await page.keyboard.press('Escape');
    await expect(page.getByTestId(`fu-new-info-${seededBefore.thesis.id}`)).toHaveCount(0, {
      timeout: 20_000,
    });
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/catalysts');
    await expect(page.getByTestId('fu-due-list')).toBeVisible();
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('catalysts-review', testInfo.project.name),
      fullPage: true,
    });
  });

  test('hors ligne simulé → état offline honnête, propre à CHAQUE source', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/catalysts');

    // La page lit DEUX snapshots indépendants (agenda et file de revue). Hors
    // ligne, chacun affiche son propre état : `.claude/rules/frontend.md`
    // exige que « chaque vue et composant connecté » couvre explicitement
    // `offline`. Un seul bandeau partagé laisserait croire à une seule
    // source, et masquerait le cas — bien plus fréquent — où une seule des
    // deux est indisponible.
    const boundaries = page.locator('[data-state="offline"]');
    await expect(boundaries).toHaveCount(2);

    // Les deux disent laquelle des deux sources manque : jamais deux fois le
    // même message.
    await expect(boundaries.first()).toContainText('aucun catalyseur affiché');
    await expect(boundaries.last()).toContainText('aucune file affichée');
    for (const index of [0, 1]) {
      await expect(boundaries.nth(index)).toContainText('Hors ligne');
    }

    await expect(page.getByTestId('fu-due-list')).toHaveCount(0);
    await expect(page.getByTestId('cat-list')).toHaveCount(0);
  });
});

test.describe('Catalyseurs — timeline reliée aux thèses et positions', () => {
  test('la timeline ne montre QUE des événements reliés, et dit combien ne le sont pas', async ({
    page,
  }) => {
    await page.goto('/catalysts');
    const scope = page.getByTestId('cat-unlinked');
    await expect(scope).toBeVisible();

    // L'agenda complet est servi par l'API ; la page n'en garde que la part
    // reliée. Les deux nombres doivent s'additionner à l'agenda servi — sinon
    // un événement aurait été perdu, ce qui serait pire qu'un événement de
    // trop.
    const agenda = await page.request.get('/api/v1/calendar');
    expect(agenda.ok()).toBe(true);
    const corps = (await agenda.json()) as { agenda: Record<string, unknown>[] };
    const relies = corps.agenda.filter((event) => {
      const contexte = event['event_context'] as
        | { positions?: unknown[]; theses?: unknown[] }
        | undefined;
      return (
        (contexte?.positions?.length ?? 0) > 0 || (contexte?.theses?.length ?? 0) > 0
      );
    });

    expect(Number(await scope.innerText())).toBe(corps.agenda.length - relies.length);

    if (relies.length === 0) {
      await expect(page.getByTestId('cat-empty')).toBeVisible();
      return;
    }
    const items = page.locator('.vx-cat-item');
    await expect(items).toHaveCount(relies.length);

    // Chaque élément affiché porte au moins un motif de rétention EXPLICITE.
    for (let index = 0; index < relies.length; index += 1) {
      const item = items.nth(index);
      const motifs = await item.locator('.vx-cat-links .vx-badge').count();
      expect(motifs).toBeGreaterThanOrEqual(1);
    }
  });

  test('le widget « consensus fourni » du contrat est déclaré absent, pas approximé', async ({
    page,
  }) => {
    await page.goto('/catalysts');
    await expect(page.getByTestId('cat-missing-widget')).toContainText('ABSENT');
  });

  test('axe : zéro violation critique/sérieuse sur la page complète + capture', async ({
    page,
  }, testInfo) => {
    await page.goto('/catalysts');
    await expect(page.getByTestId('cat-unlinked')).toBeVisible();
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({
      path: screenshotPath('catalysts', testInfo.project.name),
      fullPage: true,
    });
  });
});
