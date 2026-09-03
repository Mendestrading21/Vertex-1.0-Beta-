import type { AssumptionsDraft, LegDraft } from './simulatorView.ts';
import { MAX_LEGS, makeLegDraft } from './simulatorView.ts';

/**
 * Le composeur borné du Simulateur — jambes et hypothèses en champs texte
 * décimaux. Les CHAÎNES saisies partent verbatim vers le serveur, qui valide
 * et calcule tout ; ici, seule la STRUCTURE du formulaire est connue.
 * Extrait de `SimulatorPage.tsx` au LOT-A5 : le composeur occupe désormais
 * deux modules de la planche §6 (structure déclarée, hypothèses déclarées).
 */

function LegRow({
  leg,
  index,
  onChange,
  onRemove,
}: {
  readonly leg: LegDraft;
  readonly index: number;
  readonly onChange: (leg: LegDraft) => void;
  readonly onRemove: () => void;
}) {
  const prefix = `leg-${leg.id}`;
  return (
    <fieldset className="vx-leg">
      <legend>Jambe {index + 1}</legend>
      <div className="vx-leg-grid">
        <label htmlFor={`${prefix}-side`}>
          Sens
          <select
            id={`${prefix}-side`}
            value={leg.side}
            onChange={(event) => {
              onChange({ ...leg, side: event.target.value === 'SHORT' ? 'SHORT' : 'LONG' });
            }}
          >
            <option value="LONG">Jambe longue (quantité positive)</option>
            <option value="SHORT">Jambe courte (quantité négative)</option>
          </select>
        </label>
        <label htmlFor={`${prefix}-count`}>
          Quantité (entier)
          <input
            id={`${prefix}-count`}
            type="text"
            inputMode="numeric"
            value={leg.count}
            onChange={(event) => {
              onChange({ ...leg, count: event.target.value });
            }}
          />
        </label>
        <label htmlFor={`${prefix}-right`}>
          Type
          <select
            id={`${prefix}-right`}
            value={leg.right}
            onChange={(event) => {
              const right =
                event.target.value === 'PUT' ? 'PUT' : event.target.value === 'STOCK' ? 'STOCK' : 'CALL';
              onChange({
                ...leg,
                right,
                strike: right === 'STOCK' ? '' : leg.strike,
              });
            }}
          >
            <option value="CALL">CALL</option>
            <option value="PUT">PUT</option>
            <option value="STOCK">STOCK (jambe linéaire)</option>
          </select>
        </label>
        <label htmlFor={`${prefix}-strike`}>
          Strike (décimal)
          <input
            id={`${prefix}-strike`}
            type="text"
            inputMode="decimal"
            value={leg.strike}
            disabled={leg.right === 'STOCK'}
            onChange={(event) => {
              onChange({ ...leg, strike: event.target.value });
            }}
          />
        </label>
        <label htmlFor={`${prefix}-premium`}>
          Prime unitaire déclarée (décimal)
          <input
            id={`${prefix}-premium`}
            type="text"
            inputMode="decimal"
            value={leg.premium}
            onChange={(event) => {
              onChange({ ...leg, premium: event.target.value });
            }}
          />
        </label>
        <label htmlFor={`${prefix}-multiplier`}>
          Multiplicateur (entier)
          <input
            id={`${prefix}-multiplier`}
            type="text"
            inputMode="numeric"
            value={leg.multiplier}
            onChange={(event) => {
              onChange({ ...leg, multiplier: event.target.value });
            }}
          />
        </label>
      </div>
      <button type="button" className="vx-leg-remove" onClick={onRemove}>
        Retirer la jambe {index + 1}
      </button>
    </fieldset>
  );
}

export function LegsEditor({
  legs,
  onChange,
}: {
  readonly legs: readonly LegDraft[];
  readonly onChange: (legs: readonly LegDraft[]) => void;
}) {
  return (
    <>
      {legs.map((leg, index) => (
        <LegRow
          key={leg.id}
          leg={leg}
          index={index}
          onChange={(next) => {
            onChange(legs.map((entry) => (entry.id === leg.id ? next : entry)));
          }}
          onRemove={() => {
            onChange(legs.filter((entry) => entry.id !== leg.id));
          }}
        />
      ))}
      <button
        type="button"
        className="vx-sim-add-leg"
        disabled={legs.length >= MAX_LEGS}
        onClick={() => {
          onChange([...legs, makeLegDraft()]);
        }}
      >
        Ajouter une jambe
      </button>
    </>
  );
}

function AssumptionField({
  id,
  label,
  value,
  onChange,
  hint,
}: {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly hint?: string;
}) {
  return (
    <label htmlFor={id}>
      {label}
      <input
        id={id}
        type="text"
        inputMode="decimal"
        value={value}
        {...(hint !== undefined ? { placeholder: hint } : {})}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />
    </label>
  );
}

export function AssumptionsEditor({
  assumptions,
  onChange,
}: {
  readonly assumptions: AssumptionsDraft;
  readonly onChange: (assumptions: AssumptionsDraft) => void;
}) {
  const update = (key: keyof AssumptionsDraft) => (value: string) => {
    onChange({ ...assumptions, [key]: value });
  };
  return (
    <div className="vx-sim-assumptions-grid">
      <AssumptionField id="sim-spot" label="Spot déclaré (décimal)" value={assumptions.spot} onChange={update('spot')} />
      <AssumptionField
        id="sim-vol"
        label="Volatilité annualisée (décimal, 0.25 = 25 %/an)"
        value={assumptions.volatility}
        onChange={update('volatility')}
      />
      <AssumptionField id="sim-rate" label="Taux annualisé (décimal)" value={assumptions.rate} onChange={update('rate')} hint="ex. 0.02" />
      <AssumptionField
        id="sim-div"
        label="Rendement de dividende annualisé (décimal)"
        value={assumptions.dividendYield}
        onChange={update('dividendYield')}
        hint="ex. 0.00"
      />
      <AssumptionField id="sim-fees" label="Coûts déclarés à l'expiration (décimal)" value={assumptions.fees} onChange={update('fees')} />
      <AssumptionField
        id="sim-spot-grid"
        label="Grille de spots (1 à 41 valeurs, séparées par des virgules)"
        value={assumptions.spotGrid}
        onChange={update('spotGrid')}
        hint="ex. 300, 330, 366.08, 400, 430"
      />
      <AssumptionField
        id="sim-time-grid"
        label="Grille de temps en années (1 à 8 valeurs)"
        value={assumptions.timeGridYears}
        onChange={update('timeGridYears')}
        hint="ex. 0.0767, 0.0384, 0"
      />
    </div>
  );
}
