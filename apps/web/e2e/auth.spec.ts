/**
 * Parcours d'authentification passkey réel :
 * - sans session, les pages protégées montrent l'état dédié « Session
 *   requise » (aucune donnée) ;
 * - avec l'authenticator WebAuthn virtuel (CDP) porteur de la clé créée au
 *   setup, « Se connecter » sur /auth ouvre une session réelle.
 *
 * Ce spec utilise des contextes VIERGES (sans cookies) : il importe le test
 * de base Playwright, pas la fixture authentifiée.
 */
import { expect, test } from '@playwright/test';

const WEB_BASE_URL = 'http://localhost:4173';

test.describe('Accès passkey', () => {
  test('sans session : état dédié « Session requise » et lien vers /auth', async ({
    browser,
  }) => {
    const context = await browser.newContext({ baseURL: WEB_BASE_URL });
    const page = await context.newPage();
    await page.goto('/today');

    const notice = page.locator('[data-state="auth-required"]');
    await expect(notice).toBeVisible();
    await expect(notice).toContainText('Session requise');
    await expect(notice).toContainText('AUTH_REQUIRED');
    await expect(notice.getByRole('link', { name: 'Accès' })).toHaveAttribute('href', '/auth');
    // Aucune donnée affichée sans session.
    await expect(page.locator('.vx-queue-item')).toHaveCount(0);
    // La barre de contexte reflète l'état observé (401 reçu → non connecté).
    await expect(page.getByRole('banner').getByText('Non connecté')).toBeVisible();

    await page.goto('/system');
    await expect(page.locator('[data-state="auth-required"]')).toBeVisible();
    await expect(page.getByRole('table')).toHaveCount(0);

    await context.close();
  });

  test('« Se connecter » avec la passkey existante ouvre une session réelle', async ({
    browser,
  }, testInfo) => {
    const raw = process.env['VX_E2E_CREDENTIAL'];
    if (raw === undefined) {
      throw new Error('VX_E2E_CREDENTIAL absent : global.setup.ts n’a pas abouti.');
    }
    const credential = JSON.parse(raw) as Record<string, unknown>;
    // Compteur de signature WebAuthn strictement croissant : chaque projet
    // (exécution séquentielle) réimporte la clé avec un décalage supérieur,
    // sinon le serveur détecterait — à raison — une régression de compteur
    // (clé clonée) et révoquerait la passkey et toutes les sessions.
    const signCountOffsets: Record<string, number> = {
      'desktop-1280x800': 100,
      'desktop-1440x900': 200,
      'desktop-1600x1000': 300,
    };
    credential['signCount'] =
      Number(credential['signCount'] ?? 0) + (signCountOffsets[testInfo.project.name] ?? 400);

    const context = await browser.newContext({ baseURL: WEB_BASE_URL });
    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send('WebAuthn.enable');
    const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
      options: {
        protocol: 'ctap2',
        transport: 'internal',
        hasResidentKey: true,
        hasUserVerification: true,
        isUserVerified: true,
        automaticPresenceSimulation: true,
      },
    });
    // Import de la clé créée pendant le setup (cérémonie réelle ensuite).
    await cdp.send('WebAuthn.addCredential', {
      authenticatorId,
      credential: credential as never,
    });

    await page.goto('/auth');
    await page.getByRole('button', { name: 'Se connecter' }).click();
    await expect(page.getByRole('banner').getByText('Connecté', { exact: true })).toBeVisible({
      timeout: 15_000,
    });

    // La session ouvre réellement les pages protégées.
    await page.goto('/today');
    await expect(page.locator('.vx-queue-item').first()).toBeVisible();

    await context.close();
  });
});
