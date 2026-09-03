import type { SimulationPreviewResponse } from '../../api/client.ts';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { MAX_LEGS, MAX_SPOT_GRID, MAX_TIME_GRID } from './simulatorView.ts';
import type { SimulatorTransfer } from './transfer.ts';

/**
 * Inspecteur de la page Simulateur — « l'étude ». Avant tout calcul : le
 * contrat de la route et ses bornes. Après : la nature des valeurs, le
 * risque défini, la lignée des calculs et les avertissements. Aucune valeur
 * n'est calculée ni devinée ici.
 */
export function StudyInspector({
  result,
  transfer,
  legCount,
}: {
  readonly result: SimulationPreviewResponse | null;
  readonly transfer: SimulatorTransfer | null;
  readonly legCount: number;
}) {
  const definedRisk = result?.defined_risk ?? null;
  const code = definedRisk !== null && typeof definedRisk['reason_code'] === 'string' ? definedRisk['reason_code'] : null;
  return (
    <InspectorPanel subject="Étude">
      <SnapshotFacts
        testId="sim-study-facts"
        facts={[
          { label: 'Jambes déclarées', value: `${legCount} / ${MAX_LEGS}` },
          { label: 'Grilles admises', value: `${MAX_SPOT_GRID} spots · ${MAX_TIME_GRID} temps (contrat serveur)` },
          {
            label: 'Origine',
            value:
              transfer === null ? (
                'saisie manuelle'
              ) : (
                <>
                  Options · <code>{transfer.underlying}</code> · {transfer.right} {transfer.strike} · {transfer.expiration}
                </>
              ),
          },
          { label: 'Calcul', value: <code>POST /api/v1/simulations/preview</code> },
          { label: 'Persistance', value: 'aucune — rien n’est enregistré' },
          {
            label: 'Nature des valeurs',
            value: result === null ? 'aucun calcul effectué' : <code>{result.value_nature}</code>,
          },
          { label: 'Risque défini', value: result === null ? 'aucun calcul effectué' : <code>{publishedOr(code)}</code> },
          {
            label: 'Avertissements',
            value: result === null ? 'aucun calcul effectué' : String(result.warnings.length),
          },
        ]}
      />
      <p className="vx-inspector-note">
        Une prévisualisation d’analyse, jamais une transaction : aucun bouton, champ ni vocabulaire d’exécution
        n’existe sur cette page.
      </p>
    </InspectorPanel>
  );
}
