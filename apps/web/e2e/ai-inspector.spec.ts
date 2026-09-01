/**
 * LOT-12 : l'explication n'est plus une destination. Elle est un panneau de
 * l'inspecteur, monté par les pages qui portent un dossier explicable —
 * Analyse (`analysis/<instrument>`) et Portefeuille (`portfolio_valuation` et
 * `performance`). Règle 3 de `docs/05-design/PAGE_ARBITRATION.md` : ces
 * assertions sont DÉPLACÉES, pas supprimées ; seule la route visitée change.
 *
 * Parcours /ai — explication DÉTERMINISTE réelle de l'API.
 *
 * Vérifications : bandeau B-05 permanent + `/ai/status`, affirmations et
 * citations identiques à l'API, extraits externes isolés et non interprétés
 * comme du balisage, contradictions, données manquantes, limites (B-05 en
 * tête), traçabilité complète, note NON_IMPLÉMENTÉE, axe et hors ligne.
 */
import type { Page } from '@playwright/test';

import { expect, expectNoSeriousAxeViolations, screenshotPath, test } from './fixtures.ts';

interface ApiAiAnswer {
  readonly provider: string;
  readonly state: string;
  readonly refusal_reason: string | null;
  readonly snapshot_version: number;
  readonly content_hash: string;
  readonly as_of: string;
  readonly claims: readonly { text: string; kind: string; evidence_refs: string[] }[];
  readonly external_excerpts: readonly {
    evidence_ref: string;
    label: string;
    excerpt: string;
    truncated: boolean;
  }[];
  readonly contradictions: readonly { code: string; reference: string | null; text: string }[];
  readonly missing_data: readonly string[];
  readonly limitations: readonly string[];
  readonly evidence_catalog: readonly {
    evidence_id: string;
    evidence_type: string;
    path: string;
  }[];
}

const SUBJECT_INSTRUMENT = 'SYN-TECH-01';

async function apiExplain(
  page: Page,
  subject: { kind: string; key: string },
): Promise<ApiAiAnswer> {
  const response = await page.request.post('/api/v1/ai/explain', {
    data: { subject, locale: 'fr' },
    headers: { 'X-Vertex-CSRF': await csrfToken(page) },
  });
  expect(response.ok()).toBe(true);
  return (await response.json()) as ApiAiAnswer;
}

async function csrfToken(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  const cookie = cookies.find((entry) => entry.name === 'vertex_csrf');
  expect(cookie).toBeDefined();
  return cookie!.value;
}

test.describe('Explication IA dans l’inspecteur — déterministe et réelle', () => {
  test('bandeau B-05 permanent et /ai/status affichés', async ({ page }) => {
    const status = await page.request.get('/api/v1/ai/status');
    expect(status.ok()).toBe(true);
    const body = (await status.json()) as Record<string, unknown>;
    expect(body['provider']).toBe('DISABLED');

    await page.goto('/portfolio');
    const banner = page.getByTestId('ai-provider-banner');
    await expect(banner).toBeVisible({ timeout: 20_000 });
    await expect(banner).toContainText(
      'Explication par gabarit déterministe — fournisseur IA désactivé (décision B-05 en attente)',
    );
    await expect(page.getByTestId('ai-status-provider')).toHaveText(body['provider'] as string);
    await expect(page.getByTestId('ai-status-reason')).toHaveText(body['reason'] as string);
    // Non masquable : aucun contrôle de fermeture dans le bandeau.
    await expect(banner.locator('button')).toHaveCount(0);
  });

  test('affirmations et citations identiques à l’API, citations ouvrables', async ({ page }) => {
    await page.goto(`/analysis/${SUBJECT_INSTRUMENT}`);
    await expect(page.getByTestId('ai-subject-key')).toHaveText(SUBJECT_INSTRUMENT, {
      timeout: 20_000,
    });
    await expect(page.getByTestId('ai-claims')).toBeVisible();
    const answer = await apiExplain(page, { kind: 'analysis', key: SUBJECT_INSTRUMENT });
    expect(answer.state).toBe('ok');
    expect(answer.claims.length).toBeGreaterThanOrEqual(1);

    const claims = page.getByTestId('ai-claims');
    for (const claim of answer.claims) {
      await expect(claims).toContainText(claim.text);
      for (const reference of claim.evidence_refs) {
        const link = page.getByTestId(`ai-claim-ref-${reference}`).first();
        await expect(link).toBeVisible();
        const href = await link.getAttribute('href');
        expect(href).not.toBeNull();
        // La cible existe réellement dans le catalogue rendu.
        const target = page.locator(href!);
        await expect(target).toHaveCount(1);
      }
    }
    for (const entry of answer.evidence_catalog) {
      const row = page.getByTestId(`ai-evidence-${entry.evidence_id}`);
      await expect(row).toContainText(entry.evidence_type);
      await expect(row).toContainText(entry.path);
    }
  });

  test('extraits externes : bloc distinct, étiquetés, jamais interprétés comme du balisage', async ({
    page,
  }) => {
    await page.goto(`/analysis/${SUBJECT_INSTRUMENT}`);
    await expect(page.getByTestId('ai-subject-key')).toHaveText(SUBJECT_INSTRUMENT, {
      timeout: 20_000,
    });
    await expect(page.getByTestId('ai-external')).toBeVisible();
    const answer = await apiExplain(page, { kind: 'analysis', key: SUBJECT_INSTRUMENT });
    expect(answer.external_excerpts.length).toBeGreaterThanOrEqual(1);

    const external = page.getByTestId('ai-external');
    await expect(external).toContainText('Contenu externe non vérifié');
    const claims = page.getByTestId('ai-claims');
    for (const excerpt of answer.external_excerpts) {
      const item = page.getByTestId(`ai-external-${excerpt.evidence_ref}`);
      await expect(item).toContainText(excerpt.label);
      // Le TEXTE rendu est exactement la chaîne servie (déjà échappée).
      await expect(item.getByTestId('ai-external-quote')).toHaveText(excerpt.excerpt);
      // Aucun extrait n'apparaît dans le bloc des affirmations.
      await expect(claims).not.toContainText(excerpt.excerpt);
    }
    // Les deux blocs sont disjoints dans le DOM.
    const nested = await page.evaluate(() => {
      const first = document.querySelector('[data-testid="ai-claims"]');
      const second = document.querySelector('[data-testid="ai-external"]');
      if (first === null || second === null) {
        return true;
      }
      return first.contains(second) || second.contains(first);
    });
    expect(nested).toBe(false);
    // Aucune balise injectée par le contenu externe.
    const injected = await page.evaluate(
      () => document.querySelectorAll('[data-testid="ai-external"] script').length,
    );
    expect(injected).toBe(0);
  });

  test('contradictions, données manquantes, limites (B-05 en tête) et traçabilité', async ({
    page,
  }) => {
    await page.goto(`/analysis/${SUBJECT_INSTRUMENT}`);
    await expect(page.getByTestId('ai-subject-key')).toHaveText(SUBJECT_INSTRUMENT, {
      timeout: 20_000,
    });
    await expect(page.getByTestId('ai-trace')).toBeVisible();
    const answer = await apiExplain(page, { kind: 'analysis', key: SUBJECT_INSTRUMENT });

    for (const contradiction of answer.contradictions) {
      await expect(page.getByTestId('ai-contradictions')).toContainText(contradiction.text);
    }
    for (const missing of answer.missing_data) {
      await expect(page.getByTestId('ai-missing')).toContainText(missing);
    }
    const limitations = page.getByTestId('ai-limitations').locator('li');
    await expect(limitations).toHaveCount(answer.limitations.length);
    await expect(limitations.first()).toHaveText(answer.limitations[0]!);
    await expect(limitations.first()).toContainText('B-05');

    await expect(page.getByTestId('ai-snapshot-version')).toHaveText(
      String(answer.snapshot_version),
    );
    await expect(page.getByTestId('ai-content-hash')).toHaveText(answer.content_hash);
    await expect(page.getByTestId('ai-as-of')).toHaveText(answer.as_of);
    await expect(page.getByTestId('ai-answer-provider')).toHaveText(answer.provider);
  });

  test('choix de dossier : valorisation puis performance du portefeuille déclaré', async ({
    page,
  }) => {
    const portfolio = await page.request.get('/api/v1/portfolio');
    expect(portfolio.ok()).toBe(true);
    const portfolioId = String(
      (
        ((await portfolio.json()) as Record<string, unknown>)['portfolio'] as Record<
          string,
          unknown
        >
      )['id'],
    );

    await page.goto('/portfolio');
    await expect(page.getByTestId('ai-claims')).toBeVisible({ timeout: 20_000 });
    for (const kind of ['portfolio_valuation', 'performance']) {
      await page.getByRole('combobox', { name: 'Dossier' }).selectOption(kind);
      await expect(page.getByTestId('ai-subject-key')).toHaveText(portfolioId);
      const answer = await apiExplain(page, { kind, key: portfolioId });
      await expect(page.getByTestId('ai-content-hash')).toHaveText(answer.content_hash, {
        timeout: 20_000,
      });
      for (const claim of answer.claims) {
        await expect(page.getByTestId('ai-claims')).toContainText(claim.text);
      }
    }
  });

  test('enregistrement d’une note : NON_IMPLÉMENTÉ, aucun formulaire', async ({ page }) => {
    await page.goto('/portfolio');
    const note = page.getByTestId('ai-note');
    await expect(note).toBeVisible({ timeout: 20_000 });
    await expect(note).toContainText('NON_IMPLÉMENTÉ');
    await expect(note.locator('button')).toHaveCount(0);
    await expect(note.locator('input')).toHaveCount(0);
    await expect(note.locator('textarea')).toHaveCount(0);
  });

  test('axe : zéro violation critique/sérieuse + capture', async ({ page }, testInfo) => {
    await page.goto('/portfolio');
    await expect(page.getByTestId('ai-claims')).toBeVisible({ timeout: 20_000 });
    await expectNoSeriousAxeViolations(page);
    await page.screenshot({ path: screenshotPath('ai-inspector', testInfo.project.name), fullPage: true });
  });

  test('hors ligne simulé → AUCUNE explication, et la page hôte le dit', async ({ page }) => {
    // Ce que le test protégeait sur l'ancienne page : hors ligne, aucune
    // explication n'est affichée, et l'état dégradé est explicite. Les deux
    // propriétés sont intactes.
    //
    // Ce qui change : le bandeau B-05 n'est plus rendu hors ligne, parce que
    // le panneau lui-même ne l'est plus. « L'IA explique le dossier ouvert » —
    // hors ligne, AUCUN dossier n'est ouvert, donc il n'y a rien à expliquer
    // ni à qualifier. Le bandeau n'a pas disparu d'un écran qui montre une
    // explication : c'est l'explication entière qui est absente. L'invariant
    // qui compte — jamais d'explication sans le bandeau — est vérifié par le
    // test suivant.
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/portfolio');

    const boundary = page.locator('[data-state="offline"]').first();
    await expect(boundary).toBeVisible();
    await expect(boundary).toContainText('Hors ligne');

    await expect(page.getByTestId('ai-claims')).toHaveCount(0);
    await expect(page.getByTestId('ai-external')).toHaveCount(0);
    await expect(page.getByTestId('ai-provider-banner')).toHaveCount(0);
  });

  test('INVARIANT : aucune explication n’est jamais rendue sans le bandeau B-05', async ({
    page,
  }) => {
    // Le bandeau dit que le texte vient d'un gabarit déterministe et non d'un
    // modèle. Toute explication visible doit donc le porter, sur CHAQUE page
    // hôte — c'est la propriété que l'absorption devait préserver.
    for (const route of ['/portfolio', `/analysis/${SUBJECT_INSTRUMENT}`]) {
      await page.goto(route);
      const claims = page.getByTestId('ai-claims');
      await expect(claims).toBeVisible({ timeout: 20_000 });
      await expect(page.getByTestId('ai-provider-banner')).toBeVisible();
      await expect(page.getByTestId('ai-provider-banner')).toContainText(
        'fournisseur IA désactivé (décision B-05 en attente)',
      );
    }
  });
});
