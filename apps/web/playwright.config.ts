import { existsSync } from 'node:fs';

import { defineConfig } from '@playwright/test';

/**
 * E2E Playwright — pipeline réel (PostgreSQL de test + worker + API uvicorn
 * + build web servi par vite preview), démarré par e2e/global.setup.ts.
 *
 * Pré-requis d'environnement (jamais stockés dans un fichier) :
 * - VERTEX_TEST_DATABASE_URL : DSN de la base de test jetable ;
 * - PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers (Chromium préinstallé ; ne
 *   JAMAIS lancer `playwright install`). Si la résolution automatique échoue,
 *   l'exécutable /opt/pw-browsers/chromium est utilisé explicitement.
 *
 * Viewports desktop de phase 1 : 1280×800, 1440×900, 1600×1000 ; 1024×768
 * sert uniquement de contrôle de dégradation laptop (spec smoke), ce n'est ni
 * un breakpoint mobile ni une cible de release.
 */

const FALLBACK_CHROMIUM = '/opt/pw-browsers/chromium';
const autoResolutionAvailable = Boolean(process.env['PLAYWRIGHT_BROWSERS_PATH']);
const executablePath =
  !autoResolutionAvailable && existsSync(FALLBACK_CHROMIUM) ? FALLBACK_CHROMIUM : undefined;

export const WEB_BASE_URL = 'http://localhost:4173';
export const API_BASE_URL = 'http://127.0.0.1:8000';

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e-artifacts/test-output',
  globalSetup: './e2e/global.setup.ts',
  globalTeardown: './e2e/global.teardown.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  reporter: [['list']],
  use: {
    baseURL: WEB_BASE_URL,
    ...(executablePath !== undefined ? { launchOptions: { executablePath } } : {}),
  },
  projects: [
    {
      name: 'desktop-1280x800',
      testIgnore: /smoke\.spec\.ts/,
      use: { viewport: { width: 1280, height: 800 } },
    },
    {
      name: 'desktop-1440x900',
      testIgnore: /smoke\.spec\.ts/,
      use: { viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'desktop-1600x1000',
      testIgnore: /smoke\.spec\.ts/,
      use: { viewport: { width: 1600, height: 1000 } },
    },
    {
      name: 'smoke-1024x768',
      testMatch: /smoke\.spec\.ts/,
      use: { viewport: { width: 1024, height: 768 } },
    },
  ],
});
