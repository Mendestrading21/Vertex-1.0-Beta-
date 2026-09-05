/**
 * Liste d'étapes ou de portes — chaque étape porte un TEXTE et une pastille de
 * statut. Une coche sans texte est refusée : « aucun badge sans texte »
 * (`docs/05-design/WIDGET_LIBRARY.md`).
 *
 * Les statuts et les codes sont SERVIS (`advice.gates[]`, `calculations`,
 * `due[]`) : rien n'est reformulé, rien n'est déduit.
 */
import { AbsentCell } from '../absence.tsx';
import { StatusChip } from './StatusChip.tsx';
import type { StatusChipTone } from './StatusChip.tsx';

/**
 * Un fait SERVI attaché à une étape : le couple `clé → valeur` que le moteur a
 * réellement observé ou comparé.
 *
 * `text === null` dit que la clé est publiée mais que sa valeur n'est pas
 * relayable verbatim ; la cellule l'AVOUE (« non reconnu »), elle ne la
 * remplace ni par un vide, ni par un zéro, ni par un tiret nu.
 */
interface StepFact {
  readonly key: string;
  readonly text: string | null;
}

/** Un groupe nommé de faits servis — p. ex. « observé » et « seuils ». */
export interface StepEvidence {
  readonly title: string;
  readonly facts: readonly StepFact[];
}

export interface Step {
  readonly id: string;
  readonly label: string;
  /** Statut SERVI, verbatim. Vide ⇒ « statut non publié ». */
  readonly status: string;
  readonly tone: StatusChipTone;
  readonly detail?: string;
  /** Code serveur (`gate_id:STATUS`) rendu en chasse fixe. */
  readonly code?: string;
  /**
   * PREUVE SERVIE de l'étape. Un groupe sans fait n'est pas rendu : le silence
   * du serveur ne devient pas un titre vide. La liste est affichée dans
   * l'ORDRE du serveur, sans tri ni agrégat.
   */
  readonly evidence?: readonly StepEvidence[];
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
        {(step.evidence ?? [])
          .filter((group) => group.facts.length > 0)
          .map((group) => (
            <div className="vx-w2-step-evidence" key={group.title}>
              <p className="vx-w2-step-evidence-title">{group.title}</p>
              <dl className="vx-w2-step-facts">
                {group.facts.map((fact) => (
                  <div className="vx-w2-step-fact" key={fact.key}>
                    <dt>
                      <code>{fact.key}</code>
                    </dt>
                    <dd>
                      {fact.text === null ? (
                        <AbsentCell quoi="valeur" nature="not_recognised" reason={null} accord="f" />
                      ) : (
                        <code>{fact.text}</code>
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
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
