import type { SourceCapabilityStatus } from '../api/client.ts';

/**
 * Badge de statut de capacité — icône + texte, jamais la couleur seule.
 * Les libellés restent les valeurs canoniques du contrat (`AVAILABLE`, …) :
 * aucun statut n'est reformulé ni recalculé côté interface.
 */

const STATUS_PRESENTATION: Readonly<
  Record<SourceCapabilityStatus, { icon: string; tone: 'positive' | 'warning' | 'negative' | 'neutral' }>
> = {
  AVAILABLE: { icon: '●', tone: 'positive' },
  DELAYED: { icon: '◐', tone: 'warning' },
  NOT_ENTITLED: { icon: '⊘', tone: 'warning' },
  UNSUPPORTED: { icon: '○', tone: 'neutral' },
  ERROR: { icon: '✕', tone: 'negative' },
  MANUAL_EXPORT: { icon: '⇣', tone: 'neutral' },
};

export function StatusBadge({ status }: { readonly status: SourceCapabilityStatus }) {
  const presentation = STATUS_PRESENTATION[status];
  return (
    <span className={`vx-status-badge vx-status-badge-${presentation.tone}`} data-status={status}>
      <span aria-hidden="true" className="vx-status-badge-icon">
        {presentation.icon}
      </span>
      {status}
    </span>
  );
}
