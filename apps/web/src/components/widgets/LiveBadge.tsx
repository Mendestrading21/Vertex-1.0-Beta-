import type { SessionState } from '../../api/client.ts';
import type { SseLinkMode, SseLinkState } from '../../api/events.ts';
import type { SnapshotMeta } from '../../api/hooks.ts';
import { formatAge } from '../FreshnessBadge.tsx';
import { POPULATION_NATURES } from '../SyntheticBanner.tsx';
import { StatusChip } from './StatusChip.tsx';
import type { StatusChipTone } from './StatusChip.tsx';

/**
 * Badge du LIEN DE SIGNALEMENT — point 5 de l'anatomie canonique.
 *
 * CE QU'IL DIT, ET CE QU'IL NE DIT PAS. Le flux SSE est signal-only : chaque
 * trame vaut `{resource, version}` et ne porte aucune donnée. Le badge dit donc
 * l'état du LIEN et la fraîcheur SERVIE — « publié il y a N », jamais « en
 * direct » ni « coté » (revue adverse du canon, point D11). Le mot « direct »
 * n'apparaît dans aucun libellé de la table, et un test l'exige.
 *
 * COULEUR. L'état du lien n'a pas de teinte propre : `macro` catégorise une
 * SOURCE (`references/ICON_SYSTEM.md`), pas une connexion. Seuls le retard, le
 * périmé, le silence (`warning`) et l'absence de session (`negative`) en
 * portent une ; tout le reste est neutre ou atténué, TOUJOURS avec du texte.
 *
 * POPULATION. Une population `SYNTHETIC` ou `DEMO` interdit tout mot d'activité
 * et impose la pastille de nature à côté du badge.
 */
export type LiveTone = 'neutral' | 'warning' | 'negative' | 'muted';

export type LiveState =
  | 'open'
  | 'retrying'
  | 'silent'
  | 'stopped'
  | 'untracked'
  | 'stale'
  | 'delayed'
  | 'offline'
  | 'session';

export interface LiveBadgeInput {
  readonly session: SessionState;
  readonly link: SseLinkState;
  readonly mode: SseLinkMode;
  /** La ressource de la page est-elle SUIVIE par le flux ? */
  readonly tracked: boolean;
  readonly meta: SnapshotMeta;
}

export interface LiveDecision {
  readonly label: string;
  readonly tone: LiveTone;
  readonly live: LiveState;
  readonly populationChip: string | null;
}

/** Populations qui interdisent tout mot d'activité sur la donnée. */
const NEVER_ACTIVE = new Set(['SYNTHETIC', 'DEMO', 'SIMULATED', 'THEORETICAL']);

function freshnessOf(meta: SnapshotMeta): string {
  if (meta.ageSeconds === null) {
    return 'âge non publié';
  }
  return `publié ${formatAge(meta.ageSeconds)}`;
}

export function liveBadgeDecision(input: LiveBadgeInput): LiveDecision {
  const { meta } = input;
  const population = meta.population ?? null;
  const chip = population;
  const fresh = freshnessOf(meta);
  const busy = meta.fetchStatus === 'fetching' ? ' · actualisation' : '';

  function decide(label: string, tone: LiveTone, live: LiveState): LiveDecision {
    return { label: `${label}${busy}`, tone, live, populationChip: chip };
  }

  if (input.session === 'unauthenticated') {
    return decide('SESSION REQUISE', 'negative', 'session');
  }
  if (meta.error === 'NETWORK') {
    return decide(
      `HORS LIGNE • dernier instantané ${meta.asOf ?? 'non daté'}`,
      'muted',
      'offline',
    );
  }
  if (meta.state === 'stale') {
    return decide(`PÉRIMÉ • ${fresh}`, 'warning', 'stale');
  }
  if (population === 'DELAYED') {
    return decide(`DIFFÉRÉ • ${fresh}`, 'warning', 'delayed');
  }
  if (!input.tracked) {
    return decide(`SANS SIGNAL • ${fresh}`, 'muted', 'untracked');
  }
  if (input.link === 'retrying' || input.link === 'connecting') {
    return decide(`RECONNEXION • ${fresh}`, 'warning', 'retrying');
  }
  if (input.link === 'silent') {
    return input.mode === 'sondage'
      ? decide(`SONDAGE • ${fresh}`, 'warning', 'silent')
      : decide(`SILENCE • ${fresh}`, 'warning', 'silent');
  }
  if (input.link === 'stopped') {
    return decide(`SIGNAL ARRÊTÉ • ${fresh}`, 'muted', 'stopped');
  }
  const head = population !== null && NEVER_ACTIVE.has(population) ? 'SIGNAL' : 'SIGNAL ACTIF';
  return decide(`${head} • ${fresh}`, 'neutral', 'open');
}

function populationChipOf(population: string | null): { label: string; tone: StatusChipTone } {
  if (population === null || population === '') {
    return { label: 'NATURE NON DÉCLARÉE', tone: 'warning' };
  }
  const nature = (POPULATION_NATURES as Record<string, { label: string } | undefined>)[population];
  if (nature === undefined) {
    return { label: 'NATURE NON RECONNUE', tone: 'warning' };
  }
  return {
    label: nature.label,
    tone: population === 'REAL' || population === 'USER_DECLARED' ? 'neutral' : 'warning',
  };
}

export function LiveBadge(input: LiveBadgeInput) {
  const decision = liveBadgeDecision(input);
  const chip = populationChipOf(decision.populationChip);

  return (
    <span className="vx-w2-live-block">
      <span
        className="vx-w2-live"
        data-live={decision.live}
        data-tone={decision.tone}
        data-testid="live-badge"
      >
        {decision.label}
      </span>
      <StatusChip label={chip.label} tone={chip.tone} />
    </span>
  );
}
