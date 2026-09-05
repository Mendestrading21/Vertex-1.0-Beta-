import type { CapabilityEntry } from '../../api/client.ts';
import { StatusBadge } from '../../components/StatusBadge.tsx';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';

/**
 * Inspecteur de la page Sources & Rapports (planche §12 : « source/rapport
 * sélectionné, limites, champs, licence et historique »).
 *
 * Une capacité ouverte depuis le registre : son identifiant, sa famille, son
 * mode déclaré, sa DESCRIPTION (publiée par le manifeste, jamais affichée
 * dans la matrice), son statut testé, sa raison et l'instant de sa sonde.
 * Champs, licence et historique ne sont pas publiés : ils sont dits non
 * publiés, jamais inventés. Aucun panneau par défaut : le témoin « aucune
 * colonne morte » du shell lit cette page sans sélection.
 */

export function CapabilityInspector({ entry, onClose }: { readonly entry: CapabilityEntry; readonly onClose: () => void }) {
  return (
    <InspectorPanel subject={entry.capability_id}>
      <div className="vx-sheet-head">
        <p className="vx-inspector-note">
          <StatusBadge status={entry.tested_status} />
        </p>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>

      <SnapshotFacts
        testId="src-capability-facts"
        facts={[
          { label: 'Capacité', value: <code>{entry.capability_id}</code> },
          { label: 'Famille', value: entry.family },
          { label: 'Mode déclaré', value: <code>{entry.declared_mode}</code> },
          { label: 'Description du manifeste', value: publishedOr(entry.description) },
          { label: 'Statut testé', value: <code>{entry.tested_status}</code> },
          { label: 'Raison', value: publishedOr(entry.reason) },
          {
            label: 'Sondé le',
            value: entry.tested_at === null ? 'jamais sondé' : <time dateTime={entry.tested_at}>{entry.tested_at}</time>,
          },
          { label: 'Champs, licence, historique', value: 'non publiés par le contrat' },
        ]}
      />
      <p className="vx-inspector-note">
        Limite : un statut vient d’une sonde persistée et datée, jamais d’une disponibilité supposée ; une capacité jamais
        sondée reste ERROR / NEVER_TESTED.
      </p>
    </InspectorPanel>
  );
}
