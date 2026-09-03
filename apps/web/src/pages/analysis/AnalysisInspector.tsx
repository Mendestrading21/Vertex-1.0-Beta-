import type { AnalysisResponse } from '../../api/client.ts';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import type { AdviceView, BarsView } from './analysisView.ts';

/**
 * Inspecteur par défaut de la page Analyse (planche §4 : « dossier ouvert :
 * thèse, invalidation, sources, fraîcheur »).
 *
 * Le dossier ne publie ni thèse ni condition d'invalidation — elles sont
 * dites « non publiées », jamais devinées. Ce que le dossier publie est
 * relayé : version, instant, âge, population, référence d'observation,
 * couverture, fraîcheur du worker, limites et méthode.
 */
export function DossierInspector({
  instrument,
  data,
  bars,
  advice,
}: {
  readonly instrument: string;
  readonly data: AnalysisResponse;
  readonly bars: BarsView | null;
  readonly advice: AdviceView | null;
}) {
  const coverage = data.coverage;
  const observations =
    coverage !== null && typeof coverage['observations_considered'] === 'number'
      ? String(coverage['observations_considered'])
      : 'non publié';
  return (
    <InspectorPanel subject={`Dossier ${instrument}`}>
      <SnapshotFacts
        testId="analysis-dossier-facts"
        facts={[
          {
            label: 'Snapshot',
            value: (
              <>
                v{publishedOr(data.snapshot_version)} · <code>{publishedOr(data.engine_version)}</code>
              </>
            ),
          },
          {
            label: 'as_of',
            value: data.as_of === null ? 'non publié' : <time dateTime={data.as_of}>{data.as_of}</time>,
          },
          { label: 'Âge publié', value: <FreshnessBadge ageSeconds={data.age_seconds} sourceLabel="dossier" /> },
          { label: 'État servi', value: <code>{data.state}</code> },
          { label: 'Population', value: <code>{publishedOr(data.population)}</code> },
          { label: 'Thèse', value: 'non publiée' },
          { label: 'Invalidation', value: 'non publiée' },
          {
            label: 'Observation de référence',
            value: <code>{publishedOr(bars?.sourceEventId)}</code>,
          },
          {
            label: 'Couverture',
            value:
              bars === null
                ? 'aucune série publiée'
                : `${publishedOr(bars.count)} barres valides · ${bars.discardedCount} écartées · ${observations} observations`,
          },
          {
            label: 'Fraîcheur worker',
            value: bars === null ? 'non publiée' : bars.fresh === null ? 'non publiée' : bars.fresh ? 'fraîche' : 'publiée non fraîche par le worker',
          },
          {
            label: 'Verdict',
            value:
              advice === null ? (
                'aucun AdviceResult publié'
              ) : (
                <>
                  <code>{advice.status}</code> · <code>{advice.direction}</code> · horizon {publishedOr(advice.horizon)}
                </>
              ),
          },
        ]}
      />
      {advice !== null && advice.limitations.length > 0 ? (
        <>
          <h3 className="vx-snapshot-block-title">Limites déclarées</h3>
          <ul className="vx-inspector-list">
            {advice.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </>
      ) : null}
      <p className="vx-inspector-lineage">
        Méthode : barres validées barre à barre par le worker ; verdict par l’unique AdviceEngine ;
        clusters par la fusion déterministe. Aucune valeur n’est calculée dans le navigateur.
      </p>
    </InspectorPanel>
  );
}
