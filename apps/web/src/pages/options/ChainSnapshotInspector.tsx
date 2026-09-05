import type { OptionChainResponse } from '../../api/client.ts';
import { FreshnessBadge, policyProps } from '../../components/FreshnessBadge.tsx';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { rowBudgetOf, sourceEventIdsOf, spotViewOf } from './optionsView.ts';

/**
 * Inspecteur par défaut de la page Options : la vérité du snapshot de chaîne
 * tant qu'aucun contrat n'est ouvert. Un contrat ouvert le remplace par
 * `OptionInspector` (LOT-13) ; « Fermer » ou Échap y reviennent.
 */
export function ChainSnapshotInspector({ data }: { readonly data: OptionChainResponse }) {
  const budget = rowBudgetOf(data);
  const spot = spotViewOf(data);
  const references = sourceEventIdsOf(data);
  return (
    <InspectorPanel subject="Chaîne publiée">
      <SnapshotFacts
        testId="options-snapshot-facts"
        facts={[
          {
            label: 'Snapshot',
            value: (
              <>
                v{publishedOr(data.snapshot_version)} · <code>{publishedOr(data.engine_version)}</code>
              </>
            ),
          },
          { label: 'as_of', value: data.as_of === null ? 'non publié' : <time dateTime={data.as_of}>{data.as_of}</time> },
          { label: 'Âge publié', value: <FreshnessBadge ageSeconds={data.age_seconds} {...policyProps(data.freshness_policy)} sourceLabel="chaîne" /> },
          { label: 'État servi', value: <code>{data.state}</code> },
          { label: 'Population', value: <code>{publishedOr(data.population)}</code> },
          {
            label: 'Spot',
            value: spot === null || spot.value === null ? 'non publié' : `${spot.value} ${spot.currency ?? ''} · ${spot.observedAt ?? 'instant non publié'}`,
          },
          {
            label: 'Groupes',
            value: `${data.expirations.length} publiés · ${data.expirations.filter((group) => group.quality === 'VALID').length} VALID`,
          },
          {
            label: 'Budget de lignes',
            value:
              budget === null
                ? 'non publié'
                : `${publishedOr(budget.publishedRows)} / ${publishedOr(budget.totalRows)} · plafond ${publishedOr(budget.maxRows)} · ${publishedOr(budget.truncatedRows)} tronquées`,
          },
          { label: 'Nature des valeurs', value: <code>{publishedOr(data.value_nature)}</code> },
          {
            label: 'Références',
            value: references.length === 0 ? 'non publiées' : <code>{references.join(' · ')}</code>,
          },
        ]}
      />
      <p className="vx-inspector-note">
        Ouvrir un contrat (bouton « Détail » dans la chaîne) pour lire son identité complète, sa quote, son IV et ses
        Greeks avec leur lignée. L’unique action reste « Envoyer au Simulateur ».
      </p>
    </InspectorPanel>
  );
}
