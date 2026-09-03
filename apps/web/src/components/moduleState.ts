/**
 * État d'un MODULE de page — dérivé des faits servis, jamais du seul succès
 * HTTP, et jamais fondu dans un succès.
 *
 * POURQUOI CE MODULE EXISTE. Les planches composent chaque page de plusieurs
 * modules alimentés par des snapshots DIFFÉRENTS (attention, marchés,
 * calendrier, capacités, opportunités, portefeuille). Chacun a son propre
 * état canonique ; un seul cadre de page ne peut pas les porter tous. Chaque
 * module doit donc dire, à sa place, s'il est servi, vide, périmé, différé,
 * hors ligne ou fermé — et ne montrer AUCUNE valeur dans les autres cas.
 *
 * La priorité est celle des cadres de page existants (`attentionFrameStateOf`,
 * `frameStateOf`) : état de requête hors succès d'abord, puis réponse absente,
 * puis état servi `empty`/`stale`, puis population `DELAYED`.
 */
import type { PageDataState } from '../api/hooks.ts';

export type ModuleState =
  | 'ready'
  | 'refreshing'
  | 'loading'
  | 'empty'
  | 'stale'
  | 'partial'
  | 'delayed'
  | 'offline'
  | 'error'
  | 'auth-required'
  /** État servi hors du vocabulaire `ok`/`stale`/`empty` : fermé, code affiché tel quel. */
  | 'closed';

export const MODULE_STATE_LABELS: Readonly<Record<Exclude<ModuleState, 'ready' | 'refreshing'>, string>> = {
  loading: 'Chargement',
  empty: 'Aucun snapshot publié',
  stale: 'Données périmées',
  partial: 'Données partielles',
  delayed: 'Données différées',
  offline: 'Hors ligne',
  error: 'Réponse invalide',
  'auth-required': 'Session requise',
  closed: 'État serveur fermé',
};

export interface ServedFacts {
  readonly state?: string | null;
  readonly population?: string | null;
}

export function moduleStateOf(queryState: PageDataState, served: ServedFacts | undefined): ModuleState {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return queryState;
  }
  if (served === undefined) {
    return 'error';
  }
  const state = served.state ?? null;
  if (state === 'empty') {
    return 'empty';
  }
  if (state === 'stale') {
    return 'stale';
  }
  if (state !== null && state !== 'ok') {
    return 'closed';
  }
  if (served.population === 'DELAYED') {
    return 'delayed';
  }
  return queryState;
}

/** `true` quand le module peut montrer son contenu (daté ou différé, mais réel). */
export function moduleShowsContent(state: ModuleState): boolean {
  return (
    state === 'ready' ||
    state === 'refreshing' ||
    state === 'stale' ||
    state === 'partial' ||
    state === 'delayed'
  );
}
