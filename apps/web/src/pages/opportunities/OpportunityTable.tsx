import { Link } from 'react-router-dom';

import { EXCLUSION_KIND_LABELS, disqualifyingFacts } from './opportunitiesView.ts';
import type { CandidateView } from './opportunitiesView.ts';

/**
 * Composant dominant de la page Opportunités : le tableau des candidats.
 *
 * Le composant est INSTANCIÉ UNE FOIS PAR GROUPE et ne mélange jamais les
 * deux : chaque groupe possède sa propre région, son propre titre et sa
 * propre table dans le DOM (`data-group="qualified"` /
 * `data-group="excluded"`). Aucune ligne exclue n'existe dans le sous-arbre
 * du groupe qualifié.
 */

function StatusCell({ candidate }: { readonly candidate: CandidateView }) {
  return (
    <span className="vx-opp-status" data-status={candidate.advice.status}>
      <span aria-hidden="true">{candidate.advice.status === 'QUALIFIED' ? '●' : '○'}</span>{' '}
      <code>{candidate.advice.status}</code>
    </span>
  );
}

function ExclusionCell({ candidate }: { readonly candidate: CandidateView }) {
  const { exclusion, primaryExclusionReason } = candidate;
  if (exclusion === null && primaryExclusionReason === null) {
    return <span className="vx-cell-absent">Aucune exclusion publiée</span>;
  }
  return (
    <div className="vx-opp-exclusion">
      {exclusion !== null ? (
        <p className="vx-opp-exclusion-kind" data-kind={exclusion.kind ?? ''}>
          <strong>
            {exclusion.kind !== null
              ? (EXCLUSION_KIND_LABELS[exclusion.kind] ?? exclusion.kind)
              : 'Nature d’exclusion non publiée'}
          </strong>{' '}
          (<code>{exclusion.kind ?? '—'}</code>)
        </p>
      ) : null}
      {primaryExclusionReason !== null ? (
        <p className="vx-opp-exclusion-primary">
          Raison première : gate <code>{primaryExclusionReason.gateId}</code> —{' '}
          <code>{primaryExclusionReason.reasonCode}</code>
        </p>
      ) : (
        <p className="vx-opp-exclusion-primary vx-cell-absent">
          Aucune raison première publiée (exclusion sans gate bloquante).
        </p>
      )}
      {exclusion?.detail !== null && exclusion?.detail !== undefined ? (
        <p className="vx-opp-exclusion-detail">{exclusion.detail}</p>
      ) : null}
    </div>
  );
}

function ListCell({
  items,
  emptyLabel,
}: {
  readonly items: readonly string[];
  readonly emptyLabel: string;
}) {
  if (items.length === 0) {
    return <span className="vx-cell-absent">{emptyLabel}</span>;
  }
  return (
    <ul className="vx-opp-list">
      {items.map((item) => (
        <li key={item}>
          <code>{item}</code>
        </li>
      ))}
    </ul>
  );
}

export interface OpportunityTableProps {
  readonly group: 'qualified' | 'excluded';
  readonly candidates: readonly CandidateView[];
  readonly emptyMessage: string;
  /** Candidats publiés qualifiés mais contredits — jamais rendus qualifiés. */
  readonly contradictory?: readonly CandidateView[];
}

export function OpportunityTable({
  group,
  candidates,
  emptyMessage,
  contradictory = [],
}: OpportunityTableProps) {
  const titleId = `vx-opp-group-${group}`;
  const isQualified = group === 'qualified';
  return (
    <section
      className="vx-opp-group"
      data-group={group}
      data-testid={`opp-group-${group}`}
      aria-labelledby={titleId}
    >
      <h2 id={titleId} className="vx-opp-group-title">
        <span aria-hidden="true">{isQualified ? '▲' : '▼'}</span>{' '}
        {isQualified ? 'Qualifiés' : 'Exclus'}
        <span className="vx-opp-group-count">
          {' '}
          — {candidates.length + contradictory.length} candidat
          {candidates.length + contradictory.length > 1 ? 's' : ''}
        </span>
      </h2>
      {candidates.length === 0 && contradictory.length === 0 ? (
        <p
          className="vx-opp-group-empty"
          role="status"
          data-state="empty"
          data-testid={`opp-empty-${group}`}
        >
          {emptyMessage}
        </p>
      ) : (
        <div className="vx-matrix-scroll" tabIndex={0} role="region" aria-labelledby={titleId}>
          <table className="vx-matrix-table vx-opp-table">
            <caption>
              {isQualified
                ? 'Candidats admissibles : statut ouvert, aucune gate bloquante, toutes les preuves requises présentes.'
                : 'Candidats exclus : chacun publie POURQUOI il l’est. Aucune ligne de ce groupe n’apparaît chez les qualifiés.'}
            </caption>
            <thead>
              <tr>
                {isQualified ? <th scope="col">Rang</th> : null}
                <th scope="col">Instrument</th>
                <th scope="col">Statut</th>
                <th scope="col">Direction</th>
                <th scope="col">{isQualified ? 'Exclusion' : 'Raison d’exclusion'}</th>
                <th scope="col">Gates dégradées</th>
                <th scope="col">Preuves manquantes</th>
                <th scope="col">Population</th>
              </tr>
            </thead>
            <tbody>
              {contradictory.map((candidate) => (
                <tr
                  key={`contradictory-${candidate.ticker}`}
                  data-testid={`opp-contradictory-${candidate.ticker}`}
                  className="vx-opp-contradictory"
                >
                  {isQualified ? <td className="vx-num">—</td> : null}
                  <th scope="row">
                    <code>{candidate.ticker}</code>
                    <span className="vx-badge vx-badge-warning">SNAPSHOT INCOHÉRENT</span>
                  </th>
                  <td>
                    <StatusCell candidate={candidate} />
                  </td>
                  <td>
                    <code>{candidate.advice.direction ?? '—'}</code>
                  </td>
                  <td>
                    <p>
                      Publié dans le groupe qualifié alors que ses propres faits l’interdisent :{' '}
                      {disqualifyingFacts(candidate).join(' ; ')}. Il est affiché ici, jamais parmi
                      les qualifiés.
                    </p>
                    <ExclusionCell candidate={candidate} />
                  </td>
                  <td>
                    <ListCell items={candidate.degradedGates} emptyLabel="Aucune" />
                  </td>
                  <td>
                    <ListCell items={candidate.missingEvidence} emptyLabel="Aucune" />
                  </td>
                  <td>
                    <code>{candidate.population ?? '—'}</code>
                  </td>
                </tr>
              ))}
              {candidates.map((candidate) => (
                <tr key={candidate.ticker} data-testid={`opp-row-${group}-${candidate.ticker}`}>
                  {isQualified ? (
                    <td className="vx-num">{candidate.rank ?? '—'}</td>
                  ) : null}
                  <th scope="row">
                    <Link to={`/analysis/${encodeURIComponent(candidate.ticker)}`}>
                      <code>{candidate.ticker}</code>
                    </Link>
                    {candidate.sector !== null ? (
                      <span className="vx-opp-sector"> {candidate.sector}</span>
                    ) : null}
                  </th>
                  <td>
                    <StatusCell candidate={candidate} />
                  </td>
                  <td>
                    <code>{candidate.advice.direction ?? '—'}</code>
                  </td>
                  <td>
                    <ExclusionCell candidate={candidate} />
                  </td>
                  <td>
                    <ListCell items={candidate.degradedGates} emptyLabel="Aucune gate dégradée" />
                  </td>
                  <td>
                    <ListCell
                      items={candidate.missingEvidence}
                      emptyLabel="Aucune preuve manquante"
                    />
                  </td>
                  <td>
                    <code>{candidate.population ?? '—'}</code>
                    {candidate.synthetic ? (
                      <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
