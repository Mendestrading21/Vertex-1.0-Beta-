/**
 * Badge de fraîcheur — affiche un âge FOURNI PAR PROPS (calculé côté backend).
 * Ce composant ne lit jamais `Date.now()` ni `new Date()` : il ne fait que
 * formater une durée déjà mesurée ailleurs.
 */

export interface FreshnessBadgeProps {
  /**
   * Âge de la donnée en secondes, fourni par l'API.
   * `null` = âge inconnu (distinct d'un âge invalide ou de zéro).
   */
  readonly ageSeconds: number | null;
  /** Étiquette de source facultative (ex. « IBKR différé »). */
  readonly sourceLabel?: string;
}

/** Formatage déterministe d'un âge en secondes. Exporté pour les tests. */
export function formatAge(ageSeconds: number | null): string {
  if (ageSeconds === null) {
    return 'âge inconnu';
  }
  if (Number.isNaN(ageSeconds) || !Number.isFinite(ageSeconds) || ageSeconds < 0) {
    return 'âge invalide';
  }
  const seconds = Math.floor(ageSeconds);
  if (seconds < 60) {
    return `il y a ${seconds} s`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `il y a ${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `il y a ${hours} h`;
  }
  const days = Math.floor(hours / 24);
  return `il y a ${days} j`;
}

export function FreshnessBadge({ ageSeconds, sourceLabel }: FreshnessBadgeProps) {
  return (
    <span className="vx-freshness">
      <span className="vx-freshness-age">{formatAge(ageSeconds)}</span>
      {sourceLabel !== undefined ? (
        <span className="vx-freshness-source">— {sourceLabel}</span>
      ) : null}
    </span>
  );
}
