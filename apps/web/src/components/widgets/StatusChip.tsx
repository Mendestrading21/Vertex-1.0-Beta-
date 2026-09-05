/**
 * Pastille d'état ou de nature — glyphe FACULTATIF, texte OBLIGATOIRE.
 *
 * « Aucun badge sans texte » (`docs/05-design/WIDGET_LIBRARY.md`) et « une
 * couleur = une signification » (`docs/05-design/DESIGN_SYSTEM.md`). Le
 * vocabulaire de teintes est donc FERMÉ, et il ne contient AUCUNE teinte pour
 * l'état d'un lien : `macro` catégorise une SOURCE, pas une connexion (revue
 * adverse du lot C0, point B2). Un état de lien se rend en `neutral`.
 */
export const STATUS_CHIP_TONES = [
  'positive',
  'negative',
  'warning',
  'neutral',
  'macro',
  'option',
] as const;

export type StatusChipTone = (typeof STATUS_CHIP_TONES)[number];

export interface StatusChipProps {
  readonly label: string;
  readonly tone: StatusChipTone;
  /** Glyphe décoratif : toujours `aria-hidden`, jamais porteur de sens seul. */
  readonly icon?: string;
  /** Code serveur affiché en chasse fixe, verbatim. */
  readonly code?: string;
  readonly testId?: string;
}

export function StatusChip({ label, tone, icon, code, testId }: StatusChipProps) {
  // Un badge muet est refusé : il DIT que son libellé manque plutôt que de
  // laisser une couleur parler seule.
  const empty = label.trim() === '';
  const shownLabel = empty ? 'libellé non publié' : label;
  const shownTone: StatusChipTone = empty ? 'neutral' : tone;

  return (
    <span
      className="vx-w2-chip"
      data-tone={shownTone}
      {...(empty ? { 'data-absent': 'true' } : {})}
      data-testid={testId ?? 'status-chip'}
    >
      {icon === undefined || empty ? null : <span aria-hidden="true">{icon}</span>}
      {shownLabel}
      {code === undefined || code === '' ? null : <code className="vx-w2-chip-code">{code}</code>}
    </span>
  );
}
