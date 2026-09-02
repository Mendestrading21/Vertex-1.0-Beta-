import type { EvidenceView } from './analysisView.ts';

/** Rail evidence : les clusters de la fusion déterministe, ou leur absence dite. */
export function EvidenceRail({ evidence }: { readonly evidence: EvidenceView | null }) {
  return (
    <section className="vx-evidence" aria-labelledby="vx-evidence-title">
      <h3 id="vx-evidence-title">Evidence (clusters de fusion)</h3>
      {evidence === null ? (
        <p role="status">Aucun bloc evidence publié.</p>
      ) : evidence.clusters.length === 0 ? (
        <p role="status">
          Aucun cluster pertinent pour cet instrument ({evidence.considered ?? 0} observation(s)
          considérée(s), ruleset {evidence.rulesetVersion ?? '—'}). L'absence reste une absence.
        </p>
      ) : (
        <ul className="vx-evidence-list">
          {evidence.clusters.map((cluster) => (
            <li key={cluster.clusterId}>
              <p className="vx-evidence-title">
                {cluster.title}{' '}
                {cluster.synthetic ? (
                  <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
                ) : null}
              </p>
              <p className="vx-evidence-meta">
                {cluster.sources.join(', ')} · {cluster.memberCount ?? '—'} événement(s) · reçu{' '}
                {cluster.lastReceivedAt ?? '—'}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

