import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import { Card } from '../Card.tsx';
import type { CardRank } from '../Card.tsx';
import { FreshnessBadge } from '../FreshnessBadge.tsx';
import { ModuleStatus } from '../ModuleStatus.tsx';
import { moduleShowsContent } from '../moduleState.ts';
import type { ModuleState } from '../moduleState.ts';
import { StatusChip } from './StatusChip.tsx';

/**
 * LE conteneur des widgets v2 — `docs/09-adr/017-titanium-ledger-v2-formes-widgets.md`.
 *
 * CE QU'IL NE FAIT PAS, et c'est le point le plus important de la revue du
 * lot C0. Il NE REDÉCLARE AUCUNE SURFACE. Pas de fond, pas de bordure, pas de
 * rayon, pas d'ombre : la surface est celle de `Card` (`.vx-card`) et la
 * composition celle de `.vx-board` (`global.css`), qui cible déjà
 * `.vx-board > [data-module] > .vx-card`. Un `.vx-w2-board` parallèle serait la
 * seizième liste de sélecteurs énumérée à la main que
 * `docs/05-design/REFONTE_TITANIUM_LEDGER.md` a mesurée et refusée.
 *
 * UN SEUL PORTEUR DE RANG. `data-rank` est posé par `Card`, jamais ici : l'e2e
 * canonique COMPTE les éléments `[data-rank='dominant']` d'une page, et deux
 * porteurs pour une même dominante la feraient échouer.
 *
 * ONZE ÉTATS, PAS HUIT. `ModuleState` publie aussi `auth-required` et
 * `closed` ; un état inconnu doit échouer visiblement, pas se fondre dans un
 * succès. Dans tout état qui ne montre pas de contenu, les enfants ne sont pas
 * rendus du tout : pas de zéro de remplacement, pas de tiret ambigu.
 */

export const MODULE_STATES = [
  'ready',
  'refreshing',
  'loading',
  'empty',
  'stale',
  'partial',
  'delayed',
  'offline',
  'error',
  'auth-required',
  'closed',
] as const satisfies readonly ModuleState[];

/** Taille = SPAN DE COMPOSITION sur la planche, jamais une apparence. */
export const WIDGET_SIZES = ['S', 'M', 'L', 'XL'] as const;
export type WidgetSize = (typeof WIDGET_SIZES)[number];

/**
 * Variante VISUELLE — vocabulaire fermé de `docs/05-design/WIDGET_LIBRARY.md`.
 * Elle est distincte de la taille : `dominant` est un rang de lecture, `L` est
 * un nombre de cellules.
 */
export const WIDGET_VARIANTS = [
  'dominant',
  'support',
  'rail',
  'inline',
  'sheet',
  'workflow-step',
] as const;
export type WidgetVariant = (typeof WIDGET_VARIANTS)[number];

export interface WidgetServed {
  /** Horodatage ISO SERVI (`as_of`). `null` = non publié. */
  readonly asOf?: string | null;
  /** Âge en secondes CALCULÉ PAR LE SERVEUR. `undefined` = non publié. */
  readonly ageSeconds?: number | null;
  readonly snapshotVersion?: number | string | null;
  readonly population?: string | null;
  readonly sourceLabel?: string;
}

export interface WidgetProps {
  /** Identifiant du catalogue de la page → `data-module`. */
  readonly id: string;
  readonly size: WidgetSize;
  readonly kicker?: string;
  readonly title: string;
  readonly titleId?: string;
  readonly rank?: CardRank;
  /** Action RÉELLE de la tête (lien, bouton, compte). Jamais un ornement. */
  readonly action?: ReactNode;
  readonly state: ModuleState;
  /**
   * Provenance SERVIE du module. Absente ⇒ AUCUNE ligne de méta : un module
   * qui partage la source déjà datée par la dominante ne répète pas quatre
   * « non publié », qui feraient lire une absence là où rien n'a été demandé.
   */
  readonly served?: WidgetServed;
  /** Champ `conclusion` SERVI. `null`/absent ⇒ la ligne n'existe pas. */
  readonly conclusion?: string | null;
  /** Cause servie de l'état (motif de refus, diagnostic). */
  readonly stateDetail?: string | null;
  readonly footer?: ReactNode;
  /** Classe de la PAGE sur la carte — témoin de composition, jamais du style
   *  de surface, qui reste celui de `Card`. */
  readonly className?: string;
  readonly children: ReactNode;
}

/** Durée de la surbrillance d'une valeur mise à jour (`--vx-motion-600`). */
const HIGHLIGHT_MS = 600;
/**
 * Sous mouvement réduit, la durée CSS tombe à 0 ms : l'attribut reste posé
 * plus longtemps et se lit comme un contour statique
 * (`docs/05-design/MOTION_AND_MICROINTERACTIONS.md`, « Valeur mise à jour »).
 */
const HIGHLIGHT_REDUCED_MS = 1000;

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** `true` une fois, quand `snapshot_version` a changé — jamais en boucle. */
function useUpdatedFlag(version: number | string | null | undefined): boolean {
  const previous = useRef(version);
  const [updated, setUpdated] = useState(false);

  useEffect(() => {
    if (previous.current === version) {
      return;
    }
    previous.current = version;
    if (version === null || version === undefined) {
      return;
    }
    setUpdated(true);
    const delay = prefersReducedMotion() ? HIGHLIGHT_REDUCED_MS : HIGHLIGHT_MS;
    const timer = setTimeout(() => {
      setUpdated(false);
    }, delay);
    return () => {
      clearTimeout(timer);
    };
  }, [version]);

  return updated;
}

function WidgetMeta({ served }: { readonly served: WidgetServed | undefined }) {
  const asOf = served?.asOf ?? null;
  const ageSeconds = served?.ageSeconds;
  const version = served?.snapshotVersion ?? null;
  const population = served?.population ?? null;

  return (
    <p className="vx-w2-meta">
      {ageSeconds === undefined ? (
        <span data-absent="true">âge non publié</span>
      ) : (
        <FreshnessBadge
          ageSeconds={ageSeconds}
          {...(served?.sourceLabel === undefined ? {} : { sourceLabel: served.sourceLabel })}
        />
      )}
      {asOf === null ? (
        <span data-absent="true">instantané non daté</span>
      ) : (
        <time dateTime={asOf}>{asOf}</time>
      )}
      {version === null ? (
        <span data-absent="true">version non publiée</span>
      ) : (
        <span>v{version}</span>
      )}
      {population === null || population === '' ? (
        <StatusChip label="NATURE NON DÉCLARÉE" tone="warning" />
      ) : (
        <StatusChip label={population} tone="neutral" />
      )}
    </p>
  );
}

export function Widget({
  id,
  size,
  kicker,
  title,
  titleId,
  rank = 'default',
  className,
  action,
  state,
  served,
  conclusion,
  stateDetail,
  footer,
  children,
}: WidgetProps) {
  const updated = useUpdatedFlag(served?.snapshotVersion);
  const showsContent = moduleShowsContent(state);

  return (
    <div
      className="vx-w2"
      data-module={id}
      data-size={size}
      data-state={state}
      {...(updated ? { 'data-updated': 'true' } : {})}
    >
      <Card
        {...(kicker === undefined ? {} : { kicker })}
        title={title}
        {...(titleId === undefined ? {} : { titleId })}
        {...(action === undefined ? {} : { aside: action })}
        rank={rank}
        {...(className === undefined ? {} : { className })}
        footer={
          <>
            {conclusion === undefined || conclusion === null || conclusion === '' ? null : (
              <p className="vx-w2-conclusion">{conclusion}</p>
            )}
            {served === undefined ? null : <WidgetMeta served={served} />}
            {footer}
          </>
        }
      >
        <ModuleStatus state={state} raw={stateDetail} />
        {state === 'loading' ? (
          <div className="vx-w2-skeleton-stack" aria-hidden="true">
            <span className="vx-w2-skeleton" />
            <span className="vx-w2-skeleton" />
          </div>
        ) : null}
        {showsContent ? children : null}
      </Card>
    </div>
  );
}
