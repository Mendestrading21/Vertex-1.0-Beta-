/**
 * Mise en place E2E — pipeline réel, aucune donnée simulée côté navigateur :
 *
 * 1. PostgreSQL local démarré si nécessaire ;
 * 2. semis SYNTHETIC via les modules Python existants (migrations Alembic
 *    réelles + vertex_worker.ingest + drain du worker réel) — voir
 *    e2e/seed_synthetic.py ;
 * 3. API FastAPI réelle sous uvicorn (127.0.0.1:8000, loopback) ;
 * 4. build Vite + `vite preview` (proxy /api → API locale) ;
 * 5. création de la PREMIÈRE passkey via l'UI /auth avec l'authenticator
 *    WebAuthn virtuel de Chromium (CDP) → session réelle. Les cookies de
 *    session et la clé virtuelle sont transmis aux tests via process.env
 *    (jamais écrits dans un fichier).
 *
 * Le DSN de la base de test vient exclusivement de VERTEX_TEST_DATABASE_URL.
 */
import { execSync, spawn } from 'node:child_process';
import { mkdirSync, openSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { chromium, expect } from '@playwright/test';
import type { FullConfig } from '@playwright/test';

const WEB_ROOT = fileURLToPath(new URL('..', import.meta.url));
const REPO_ROOT = fileURLToPath(new URL('../../..', import.meta.url));
const ARTIFACTS_DIR = `${WEB_ROOT}e2e-artifacts`;
const WEB_BASE_URL = 'http://localhost:4173';
const API_HEALTH_URL = 'http://127.0.0.1:8000/api/v1/health';

const PYTHONPATH = [
  'packages/python/vertex_core/src',
  'packages/python/vertex_persistence/src',
  'apps/worker/src',
  'apps/api/src',
]
  .map((entry) => `${REPO_ROOT}${entry}`)
  .join(':');

function requireTestDatabaseUrl(): string {
  const url = process.env['VERTEX_TEST_DATABASE_URL'];
  if (url === undefined || url === '') {
    throw new Error(
      'VERTEX_TEST_DATABASE_URL est absent. Exporter le DSN de la base de test ' +
        'jetable dans l’environnement (jamais dans un fichier) avant `pnpm e2e`.',
    );
  }
  return url;
}

function ensurePostgresRunning(): void {
  try {
    execSync('pg_isready -h 127.0.0.1 -p 5432 -t 3', { stdio: 'pipe' });
    return;
  } catch {
    // Pas prêt : démarrage du service local (autorisé par la mission E2E).
  }
  execSync('service postgresql start', { stdio: 'pipe' });
  execSync('pg_isready -h 127.0.0.1 -p 5432 -t 15', { stdio: 'pipe' });
}

async function waitForHttp(url: string, timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError: unknown = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
      lastError = new Error(`status ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timeout en attendant ${url} : ${String(lastError)}`);
}

function spawnLogged(
  command: string,
  args: readonly string[],
  env: NodeJS.ProcessEnv,
  logName: string,
): number {
  mkdirSync(`${ARTIFACTS_DIR}/logs`, { recursive: true });
  const log = openSync(`${ARTIFACTS_DIR}/logs/${logName}.log`, 'w');
  const child = spawn(command, [...args], {
    cwd: WEB_ROOT,
    env,
    detached: true,
    stdio: ['ignore', log, log],
  });
  if (child.pid === undefined) {
    throw new Error(`Impossible de démarrer ${command}`);
  }
  child.unref();
  return child.pid;
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  const databaseUrl = requireTestDatabaseUrl();

  // 1-2. Base démarrée + semis SYNTHETIC par le pipeline Python réel.
  ensurePostgresRunning();
  execSync(`python3 ${WEB_ROOT}e2e/seed_synthetic.py`, {
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONPATH,
      VERTEX_TEST_DATABASE_URL: databaseUrl,
      VERTEX_ALLOW_TEST_DB: '1',
    },
  });

  // 3. API réelle (uvicorn, loopback uniquement).
  const apiPid = spawnLogged(
    'python3',
    [
      '-m',
      'uvicorn',
      'vertex_api.app:create_app',
      '--factory',
      '--host',
      '127.0.0.1',
      '--port',
      '8000',
    ],
    {
      ...process.env,
      PYTHONPATH,
      VERTEX_DATABASE_URL: databaseUrl,
      VERTEX_AUTH_COOKIE_INSECURE_DEV: '1', // http loopback E2E (opt-out documenté)
      VERTEX_AUTH_DEV_ORIGIN_PORTS: '4173',
    },
    'uvicorn',
  );
  process.env['VX_E2E_API_PID'] = String(apiPid);
  await waitForHttp(API_HEALTH_URL, 30_000);

  // 3 bis. Worker RÉEL en continu (vague 4) : les écritures faites via l'UI
  // pendant les tests (transactions, compensations, révisions de thèses)
  // sont traitées et republiées (valorisation, performance, file de revues),
  // puis signalées par le flux SSE — aucun instantané simulé.
  const workerPid = spawnLogged(
    'python3',
    [`${WEB_ROOT}e2e/run_worker.py`],
    {
      ...process.env,
      PYTHONPATH,
      VERTEX_TEST_DATABASE_URL: databaseUrl,
    },
    'worker',
  );
  process.env['VX_E2E_WORKER_PID'] = String(workerPid);

  // 4. Build réel + serveur de prévisualisation Vite (proxy /api).
  execSync('pnpm build', { cwd: WEB_ROOT, stdio: 'inherit', env: process.env });
  const previewPid = spawnLogged(
    'pnpm',
    ['exec', 'vite', 'preview', '--port', '4173', '--strictPort', '--host', '127.0.0.1'],
    { ...process.env },
    'vite-preview',
  );
  process.env['VX_E2E_PREVIEW_PID'] = String(previewPid);
  await waitForHttp(WEB_BASE_URL, 30_000);

  // 5. Première passkey créée via l'UI /auth (WebAuthn virtuel CDP).
  const executablePath = config.projects[0]?.use?.launchOptions?.executablePath;
  const browser = await chromium.launch(
    executablePath !== undefined ? { executablePath } : {},
  );
  try {
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

    await page.goto('/auth');
    await page.getByRole('button', { name: 'Créer la passkey (premier démarrage)' }).click();
    // Session réelle ouverte : la barre de contexte reflète l'état observé.
    await expect(page.getByRole('banner').getByText('Connecté', { exact: true })).toBeVisible({
      timeout: 15_000,
    });

    // Export de la clé virtuelle et des cookies de session pour les tests —
    // via l'environnement du processus uniquement, jamais un fichier.
    const { credentials } = await cdp.send('WebAuthn.getCredentials', { authenticatorId });
    if (credentials.length !== 1) {
      throw new Error(`1 credential attendu après l'enrôlement, trouvé ${credentials.length}`);
    }
    const cookies = await context.cookies(WEB_BASE_URL);
    if (!cookies.some((cookie) => cookie.name === 'vertex_session')) {
      throw new Error('cookie de session absent après le parcours /auth');
    }
    process.env['VX_E2E_COOKIES'] = JSON.stringify(cookies);
    process.env['VX_E2E_CREDENTIAL'] = JSON.stringify(credentials[0]);
    await context.close();
  } finally {
    await browser.close();
  }
}
