import { MODULE_STATE_LABELS } from './moduleState.ts';
import type { ModuleState } from './moduleState.ts';

/**
 * L'état d'UN module, à sa place — libellé stable du vocabulaire fermé, code
 * serveur en chasse fixe quand il existe. Rien n'est rendu en succès : un
 * module servi n'a pas d'état à dire, il montre ses valeurs.
 *
 * Extrait de `TodayModules.tsx` au LOT-A4 : chaque page composée en a besoin.
 */
export function ModuleStatus({
  state,
  raw,
}: {
  readonly state: ModuleState;
  readonly raw?: string | null | undefined;
}) {
  if (state === 'ready' || state === 'refreshing') {
    return null;
  }
  return (
    <p className="vx-module-state" role="status" data-state={state}>
      {MODULE_STATE_LABELS[state]}
      {raw !== undefined && raw !== null && raw !== '' ? (
        <>
          {' '}
          — <code>{raw}</code>
        </>
      ) : null}
    </p>
  );
}
