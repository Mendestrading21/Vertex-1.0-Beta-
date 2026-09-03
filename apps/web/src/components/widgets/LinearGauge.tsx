import { geometryValue, servedWidth } from './geometry.ts';

/**
 * Jauge linéaire / bullet — généralise `BreadthPanel`.
 *
 * « Le navigateur ne calcule ni pourcentage, ni seuil, ni position du
 * marqueur » (`docs/05-design/WIDGET_LIBRARY.md`). Toutes les coordonnées
 * arrivent SERVIES en pourcentage ; la largeur CSS est la chaîne servie, telle
 * quelle. `aria-valuenow` est une coercition de cette même chaîne — aucune
 * arithmétique.
 *
 * REFUS. Position absente ou statut `INVALID` : « non calculable », la RAISON
 * servie, et AUCUNE barre. Pas de valeur de remplacement, précédent
 * `BreadthPanel`.
 */
export interface GaugeMarker {
  /** Position SERVIE en pourcentage. */
  readonly pct: string;
  readonly label: string;
}

export interface GaugeSegment {
  readonly fromPct: string | null;
  readonly toPct: string | null;
  readonly name: string;
}

export interface LinearGaugeProps {
  readonly label: string;
  /** Position SERVIE en pourcentage. `null` = non calculable. */
  readonly valuePct: string | null;
  /** Texte SERVI de la valeur (unité comprise). */
  readonly valueText: string | null;
  readonly boundsText: { readonly min: string; readonly max: string };
  readonly markers: readonly GaugeMarker[];
  readonly segments?: readonly GaugeSegment[];
  /** Méthode/version SERVIE du calcul. */
  readonly method?: string;
  /** Motif SERVI du refus. */
  readonly reason?: string;
  readonly status?: string;
}

export function LinearGauge({
  label,
  valuePct,
  valueText,
  boundsText,
  markers,
  segments,
  method,
  reason,
  status,
}: LinearGaugeProps) {
  const invalid = status === 'INVALID';

  if (valuePct === null || valueText === null || invalid) {
    return (
      <div className="vx-w2-gauge" data-state="invalid">
        <span className="vx-w2-gauge-label">{label}</span>
        <p className="vx-w2-absent" role="status">
          Valeur non calculable. Aucune valeur de remplacement.
          {reason === undefined ? null : (
            <>
              {' '}
              Raison serveur : <code>{reason}</code>.
            </>
          )}
        </p>
      </div>
    );
  }

  const drawnSegments = (segments ?? []).filter(
    (segment) => segment.fromPct !== null && segment.toPct !== null,
  );

  return (
    <div className="vx-w2-gauge">
      <span className="vx-w2-gauge-label" id={`vx-w2-gauge-${label}`}>
        {label}
      </span>
      <div
        className="vx-w2-gauge-track"
        role="meter"
        aria-labelledby={`vx-w2-gauge-${label}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={geometryValue(valuePct) ?? undefined}
        aria-valuetext={valueText}
      >
        {drawnSegments.map((segment) => (
          <span
            key={segment.name}
            className="vx-w2-gauge-seg"
            data-name={segment.name}
            style={{
              left: servedWidth(segment.fromPct as string),
              width: servedWidth(segment.toPct as string),
            }}
          />
        ))}
        <span className="vx-w2-gauge-fill" style={{ width: servedWidth(valuePct) }} />
        {markers.map((marker) => (
          <span
            key={marker.label}
            className="vx-w2-gauge-marker"
            style={{ left: servedWidth(marker.pct) }}
            title={marker.label}
          />
        ))}
      </div>
      <p className="vx-w2-gauge-bounds">
        <span>{boundsText.min}</span>
        <span>{valueText}</span>
        <span>{boundsText.max}</span>
      </p>
      {markers.length === 0 ? null : (
        <p className="vx-w2-absent">{markers.map((marker) => marker.label).join(' · ')}</p>
      )}
      {method === undefined ? null : (
        <p className="vx-w2-absent">
          méthode <code>{method}</code>
        </p>
      )}
    </div>
  );
}
