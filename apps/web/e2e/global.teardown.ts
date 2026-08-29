/** Arrêt des processus démarrés par global.setup.ts (API uvicorn, preview). */

function stop(pidText: string | undefined, label: string): void {
  if (pidText === undefined) {
    return;
  }
  const pid = Number(pidText);
  if (!Number.isInteger(pid) || pid <= 1) {
    return;
  }
  try {
    // Groupe de processus (spawn detached) puis le processus lui-même.
    process.kill(-pid, 'SIGTERM');
  } catch {
    try {
      process.kill(pid, 'SIGTERM');
    } catch {
      // Déjà arrêté : rien à faire.
    }
  }
  process.stdout.write(`teardown: ${label} (pid ${pid}) arrêté\n`);
}

export default function globalTeardown(): void {
  stop(process.env['VX_E2E_PREVIEW_PID'], 'vite preview');
  stop(process.env['VX_E2E_API_PID'], 'uvicorn');
}
