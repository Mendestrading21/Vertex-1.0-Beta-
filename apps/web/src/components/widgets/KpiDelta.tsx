import { GROUP_LABELS_FR, signSymbolOf } from '../markets/marketsView.ts';
import type { SignGroup } from '../markets/marketsView.ts';

/**
 * Pastille de variation — la chaîne servie, son signe TEXTUEL, sa période.
 *
 * POURQUOI UNE FONCTION DE SIGNE DE PLUS. `signGroupOf` (`marketsView.ts`)
 * prend un `MarketsTicker` : elle ne peut pas classer `total_unrealized` ni
 * aucune autre chaîne signée d'un autre contrat (revue adverse « données »,
 * point 4). Celle-ci lit une CHAÎNE.
 *
 * ET POURQUOI ELLE REFUSE DE TRANCHER. Une chaîne positive publiée SANS « + »
 * n'est pas « stable » : son signe n'est pas publié. Le classer `flat`
 * inventerait une stabilité. La pastille le DIT alors, et ne prend aucune
 * couleur de sens.
 */
const ZERO = /^[+-]?0+([.,]0+)?\s*%?$/;
const SIGNED = /^([+-])/;

export function signGroupOfText(value: string): SignGroup | null {
  const trimmed = value.trim();
  if (trimmed === '') {
    return null;
  }
  if (ZERO.test(trimmed)) {
    return 'flat';
  }
  const signe = SIGNED.exec(trimmed)?.[1];
  if (signe === '+') {
    return 'up';
  }
  if (signe === '-') {
    return 'down';
  }
  return null;
}

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
