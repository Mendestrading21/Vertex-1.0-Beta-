import { StatusChip } from './StatusChip.tsx';
import type { StatusChipTone } from './StatusChip.tsx';

/**
 * Liste d'étapes ou de portes — chaque étape porte un TEXTE et une pastille de
 * statut. Une coche sans texte est refusée : « aucun badge sans texte »
 * (`docs/05-design/WIDGET_LIBRARY.md`).
 *
 * Les statuts et les codes sont SERVIS (`advice.gates[]`, `calculations`,
 * `due[]`) : rien n'est reformulé, rien n'est déduit.
 */
export interface Step {
  readonly id: string;
  readonly label: string;
  /** Statut SERVI, verbatim. Vide ⇒ « statut non publié ». */
  readonly status: string;
  readonly tone: StatusChipTone;
  readonly detail?: string;
  /** Code serveur (`gate_id:STATUS`) rendu en chasse fixe. */
  readonly code?: string;
}

export interface StepListProps {
  readonly steps: readonly Step[];
  readonly ariaLabel: string;
  /** Une suite ORDONNÉE de portes se rend en `<ol>`. */
  readonly ordered?: boolean;
  readonly emptyLabel?: string;
}

export function StepList({ steps, ariaLabel, ordered, emptyLabel }: StepListProps) {
  if (steps.length === 0) {
    return (
      <p className="vx-w2-absent" role="status">
        {emptyLabel ?? 'Aucune étape publiée.'}
      </p>
    );
  }

  const items = steps.map((step) => {
    const missing = step.status.trim() === '';
    return (
      <li key={step.id} className="vx-w2-step">
        <span className="vx-w2-step-head">
          <span>{step.label}</span>
          <StatusChip
            label={missing ? 'statut non publié' : step.status}
            tone={missing ? 'neutral' : step.tone}
            {...(step.code === undefined ? {} : { code: step.code })}
          />
        </span>
        {step.detail === undefined ? null : <p className="vx-w2-step-detail">{step.detail}</p>}
      </li>
    );
  });

  return ordered === true ? (
    <ol className="vx-w2-steps" aria-label={ariaLabel}>
      {items}
    </ol>
  ) : (
    <ul className="vx-w2-steps" aria-label={ariaLabel}>
      {items}
    </ul>
  );
}
