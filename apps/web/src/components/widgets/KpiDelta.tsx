import { GROUP_LABELS_FR, signSymbolOf } from '../markets/marketsView.ts';
import type { SignGroup } from '../markets/marketsView.ts';

/**
 * Pastille de variation — la chaîne servie, son signe TEXTUEL, sa période.
 *
 * La règle de signe elle-même vit désormais dans `sign.ts`, seule autorité du
 * produit : elle était ici, dans un fichier de composant, et trois copies
 * divergentes en étaient nées ailleurs.
 */
export interface KpiDeltaProps {
  /** Chaîne SERVIE, affichée verbatim. `null` = variation non publiée. */
  readonly value: string | null;
  /** Sens obtenu par l'appelant depuis le SIGNE de la chaîne servie. */
  readonly sign: SignGroup | null;
  /** Période SERVIE de la variation (« 1 j », « depuis l'ouverture servie »). */
  readonly period: string;
  readonly absentLabel?: string;
}

export function KpiDelta({ value, sign, period, absentLabel }: KpiDeltaProps) {
  // Un signe SANS valeur ne colore rien : il n'a rien à qualifier.
  const effectif = value === null ? null : sign;

  return (
    <span
      className="vx-w2-delta"
      data-sign={effectif ?? 'unknown'}
      data-testid="kpi-delta"
    >
      {effectif === null ? null : <span aria-hidden="true">{signSymbolOf(effectif)}</span>}
      {value === null ? (
        <span data-absent="true">{absentLabel ?? 'variation non publiée'}</span>
      ) : (
        <span>{value}</span>
      )}
      {value !== null && effectif === null ? (
        <span data-absent="true">signe non publié</span>
      ) : null}
      {effectif === null ? null : (
        <span className="vx-visually-hidden">{GROUP_LABELS_FR[effectif]}</span>
      )}
      <span className="vx-w2-delta-period">{period}</span>
    </span>
  );
}
