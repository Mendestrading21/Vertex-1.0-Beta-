import { Link } from 'react-router-dom';

import type { OpportunitiesResponse } from '../../api/client.ts';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { EXCLUSION_KIND_LABELS, disqualifyingFacts } from './opportunitiesView.ts';
import type { CandidateView, OpportunitiesContentView } from './opportunitiesView.ts';

/**
 * Inspecteur de la page Opportunités (planche §3 : « candidat sélectionné,
 * admission, preuves, provenance »).
 *
 * Deux contenus, un panneau à la fois : le CANDIDAT ouvert depuis le
 * classement — admission, abstention ou exclusion publiée, gates, preuves
 * requises présentes ou absentes, provenance, lien vers son dossier — sinon
 * la vérité du snapshot. Aucune nouvelle vérité : ce panneau ne classe pas,
 * ne note pas, ne complète rien.
 */

export function CandidateInspector({
  candidate,
  contradictory,
  onClose,
}: {
  readonly candidate: CandidateView;
  readonly contradictory: boolean;
  readonly onClose: () => void;
}) {
  const facts = contradictory ? disqualifyingFacts(candidate) : [];
  return (
    <InspectorPanel subject={candidate.ticker}>
      <div className="vx-sheet-head">
        <p className="vx-inspector-note">
          {candidate.sector ?? 'secteur non publié'}
          {candidate.synthetic ? <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span> : null}
          {contradictory ? <span className="vx-badge vx-badge-warning">SNAPSHOT INCOHÉRENT</span> : null}
        </p>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>

      <SnapshotFacts
        testId="opp-candidate-facts"
        facts={[
          {
            label: 'Statut publié',
            value: (
              <span className="vx-opp-status" data-status={candidate.advice.status}>
                <code>{candidate.advice.status}</code>
              </span>
            ),
          },
          { label: 'Direction', value: <code>{publishedOr(candidate.advice.direction)}</code> },
          { label: 'Horizon', value: publishedOr(candidate.advice.horizon) },
          { label: 'Rang publié', value: candidate.rank === null ? 'non publié' : String(candidate.rank) },
          {
            label: 'Exclusion',
            value:
              candidate.exclusion === null ? (
                'aucune exclusion publiée'
              ) : (
                <>
                  {candidate.exclusion.kind !== null
                    ? (EXCLUSION_KIND_LABELS[candidate.exclusion.kind] ?? candidate.exclusion.kind)
                    : 'nature non publiée'}
                  {candidate.primaryExclusionReason === null ? null : (
                    <>
                      {' '}
                      · gate <code>{candidate.primaryExclusionReason.gateId}</code>{' '}
                      <code>{candidate.primaryExclusionReason.reasonCode}</code>
                    </>
                  )}
                </>
              ),
          },
          {
            label: 'Validité de l’avis',
            value: (
              <>
                {candidate.advice.asOf === null ? 'non publiée' : <time dateTime={candidate.advice.asOf}>{candidate.advice.asOf}</time>}
                {' → '}
                {candidate.advice.validUntil === null ? 'non publiée' : <time dateTime={candidate.advice.validUntil}>{candidate.advice.validUntil}</time>}
              </>
            ),
          },
          { label: 'Barres', value: <code>{publishedOr(candidate.barsStatus)}</code> },
          { label: 'Scénarios', value: <code>{publishedOr(candidate.scenariosStatus)}</code> },
          { label: 'Moteur', value: <code>{publishedOr(candidate.advice.engineVersion)}</code> },
        ]}
      />

      {facts.length > 0 ? (
        <p className="vx-inspector-note" role="status">
          Publié qualifié mais contredit par ses propres faits : {facts.join(' ; ')}.
        </p>
      ) : null}

      <h3 className="vx-snapshot-block-title">Gates</h3>
      {candidate.gates.length === 0 ? (
        <p className="vx-inspector-note">Aucune gate publiée.</p>
      ) : (
        <ul className="vx-inspector-list" data-testid="opp-candidate-gates">
          {candidate.gates.map((gate) => (
            <li key={gate.gateId} data-status={gate.status}>
              <code>{gate.gateId}</code>{' '}
              <span className="vx-gate-status" data-status={gate.status}>
                {gate.status}
              </span>
              {gate.reasonCode === null ? null : (
                <>
                  {' '}
                  — <code>{gate.reasonCode}</code>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <h3 className="vx-snapshot-block-title">Preuves requises</h3>
      {candidate.requiredEvidence.length === 0 ? (
        <p className="vx-inspector-note">Aucune preuve requise publiée.</p>
      ) : (
        <ul className="vx-inspector-list" data-testid="opp-candidate-evidence">
          {candidate.requiredEvidence.map((check) => (
            <li key={check.name} data-present={check.present ? 'true' : 'false'}>
              <span aria-hidden="true">{check.present ? '●' : '○'}</span> <code>{check.name}</code>{' '}
              {check.present ? 'présente' : 'absente'}
              {check.detail === null ? null : <span className="vx-inspector-unit"> — {check.detail}</span>}
            </li>
          ))}
        </ul>
      )}

      <p className="vx-inspector-lineage">
        avis <code>{publishedOr(candidate.advice.adviceId)}</code>
        <br />
        clusters {candidate.evidenceClusterIds.length} · scénarios {candidate.scenarioIds.length} ·
        population <code>{publishedOr(candidate.population)}</code>
      </p>
      <p className="vx-inspector-note">
        <Link to={`/analysis/${encodeURIComponent(candidate.ticker)}`}>Ouvrir le dossier d’analyse</Link>
      </p>
    </InspectorPanel>
  );
}

export function OpportunitiesSnapshotInspector({
  data,
  view,
}: {
  readonly data: OpportunitiesResponse;
  readonly view: OpportunitiesContentView;
}) {
  const coverage = view.coverage;
  return (
    <InspectorPanel subject="Snapshot publié">
      <SnapshotFacts
        testId="opp-snapshot-facts"
        facts={[
          {
            label: 'Snapshot',
            value: (
              <>
                v{publishedOr(data.snapshot_version)} · <code>{publishedOr(view.engineVersion)}</code>
              </>
            ),
          },
          {
            label: 'as_of',
            value: view.asOf === null ? 'non publié' : <time dateTime={view.asOf}>{view.asOf}</time>,
          },
          {
            label: 'Âge publié',
            value: <FreshnessBadge ageSeconds={data.age_seconds} sourceLabel="âge publié par le serveur" />,
          },
          { label: 'État servi', value: <code>{data.state}</code> },
          { label: 'Population', value: <code>{publishedOr(view.population)}</code> },
          { label: 'Schéma', value: <code>{publishedOr(view.schemaVersion)}</code> },
          {
            label: 'Ordre publié',
            value: (
              <>
                <code>{publishedOr(view.ordering.method)}</code>
                {view.ordering.keys.length === 0 ? null : <> · {view.ordering.keys.join(' → ')}</>}
              </>
            ),
          },
          {
            label: 'Couverture',
            value: `${publishedOr(coverage.qualifiedCount)} qualifiés · ${publishedOr(coverage.excludedCount)} exclus · univers ${publishedOr(coverage.universeSize)} · ${publishedOr(coverage.observationsConsidered)} observations`,
          },
          {
            label: 'Populations',
            value:
              coverage.populationCounts.size === 0
                ? 'non publiées'
                : [...coverage.populationCounts.entries()].map(([key, count]) => `${key} × ${count}`).join(' · '),
          },
        ]}
      />
      <p className="vx-inspector-note">
        Sélectionner un candidat (bouton « Inspecter » dans le classement) pour lire son admission, ses
        gates et ses preuves requises.
      </p>
    </InspectorPanel>
  );
}
