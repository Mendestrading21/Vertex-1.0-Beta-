import type { ReactNode } from 'react';

/**
 * Primitive d'affichage des états de données — docs/05-design/UI_STATES.md.
 *
 * L'état vient TOUJOURS des props (donc du backend) : ce composant ne lit
 * jamais l'horloge du navigateur et ne déduit aucune fraîcheur lui-même.
 * `asOfLabel` et `detail` sont des textes déjà formés, fournis par l'appelant.
 */

/** Les 8 états canoniques + l'état nominal `ready` (rendu direct des enfants). */
export type DataState =
  | 'ready'
  | 'loading'
  | 'refreshing'
  | 'empty'
  | 'partial'
  | 'delayed'
  | 'stale'
  | 'offline'
  | 'error';

/** Libellés français stables — ne pas reformuler sans décision produit. */
export const DATA_STATE_LABELS: Readonly<Record<Exclude<DataState, 'ready'>, string>> = {
  loading: 'Chargement',
  refreshing: 'Actualisation',
  empty: 'Aucune donnée',
  partial: 'Données partielles',
  delayed: 'Données différées',
  stale: 'Données périmées',
  offline: 'Hors ligne',
  error: 'Erreur de données',
};

export interface DataStateBoundaryProps {
  readonly state: DataState;
  /**
   * Contenu nominal. Selon l'état, il reste visible (refreshing, partial,
   * delayed, stale, offline, error avec dernière donnée valide) ou est
   * remplacé (loading, empty).
   */
  readonly children?: ReactNode;
  /** Cause, couverture manquante ou diagnostic — fourni par l'appelant. */
  readonly detail?: string;
  /** Horodatage exact fourni par le backend (ex. « 14:32:05 UTC »). */
  readonly asOfLabel?: string;
}

function Banner({
  label,
  tone,
  detail,
  asOfLabel,
  role,
}: {
  readonly label: string;
  readonly tone: 'neutral' | 'warning' | 'error';
  readonly detail?: string | undefined;
  readonly asOfLabel?: string | undefined;
  readonly role: 'status' | 'alert';
}) {
  const toneClass =
    tone === 'warning'
      ? ' vx-dsb-banner-warning'
      : tone === 'error'
        ? ' vx-dsb-banner-error'
        : '';
  return (
    <p className={`vx-dsb-banner${toneClass}`} role={role}>
      <strong>{label}</strong>
      {detail !== undefined ? <span>{detail}</span> : null}
      {asOfLabel !== undefined ? <span className="vx-dsb-asof">{asOfLabel}</span> : null}
    </p>
  );
}

export function DataStateBoundary({ state, children, detail, asOfLabel }: DataStateBoundaryProps) {
  if (state === 'ready') {
    // Emplacement STABLE du contenu : `null` occupe la position du bandeau
    // des états dégradés, donc un passage ready ↔ refreshing/partial/stale ne
    // déplace pas `children` dans l'arbre React — les composants enfants (et
    // leur état local : formulaires en cours de saisie, messages de
    // confirmation) ne sont pas démontés par un simple rafraîchissement.
    return (
      <div data-state="ready">
        {null}
        {children}
      </div>
    );
  }

  const label = DATA_STATE_LABELS[state];

  // Premier chargement : squelette seul, aucun résultat affiché.
  if (state === 'loading') {
    return (
      <div data-state={state} role="status" aria-busy="true" className="vx-dsb-message">
        <strong>{label}</strong>
        <div className="vx-dsb-skeleton" aria-hidden="true" />
      </div>
    );
  }

  // Vide : cause et action corrective, jamais une valeur zéro fabriquée.
  if (state === 'empty') {
    return (
      <div data-state={state} role="status" className="vx-dsb-message">
        <strong>{label}</strong>
        {detail !== undefined ? <p className="vx-dsb-detail">{detail}</p> : null}
      </div>
    );
  }

  // Erreur sans dernière donnée valide : message seul, pas de faux succès.
  if (state === 'error' && children === undefined) {
    return (
      <div data-state={state} role="alert" className="vx-dsb-message vx-dsb-message-error">
        <strong>{label}</strong>
        {detail !== undefined ? <p className="vx-dsb-detail">{detail}</p> : null}
      </div>
    );
  }

  // États où l'ancien contenu (daté) reste visible sous un bandeau explicite.
  const tone: 'neutral' | 'warning' | 'error' =
    state === 'error'
      ? 'error'
      : state === 'refreshing'
        ? 'neutral'
        : 'warning'; // partial, delayed, stale, offline : prudence/dégradation
  return (
    <div data-state={state}>
      <Banner
        label={label}
        tone={tone}
        detail={detail}
        asOfLabel={asOfLabel}
        role={state === 'error' ? 'alert' : 'status'}
      />
      {children}
    </div>
  );
}
