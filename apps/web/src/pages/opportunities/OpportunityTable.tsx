import { Link } from 'react-router-dom';

import { POPULATION_NATURES, resolvePopulationNature } from '../../components/SyntheticBanner.tsx';
import type { PopulationTone } from '../../components/SyntheticBanner.tsx';
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
 *
 * LA NATURE D'UN DOSSIER (7e audit, P1-8). La colonne « Population »
 * imprimait la nature BRUTE — `<code>{candidate.population ?? '—'}</code>` —
 * aux deux emplacements de lignes : aucun vocabulaire fermé, aucun ton, aucun
 * repli fail-closed, et un mot anglais seul dans une interface française. Une
 * étiquette forgée (`LIVE`, `IBKR_REALTIME_ENTITLED`) ou absente était donc
 * rendue en silence. `SyntheticBanner` protège la TÊTE du snapshot ; il ne
 * protège pas les DOSSIERS, et c'est le dossier que l'utilisateur lit ligne
 * par ligne.
 *
 * `PopulationCell` réutilise le vocabulaire fermé (`POPULATION_NATURES`) et
 * le résolveur fail-closed (`resolvePopulationNature`) du bandeau plutôt que
 * d'ouvrir une seconde table de natures : deux tables dériveraient, et la
 * nature est précisément le champ où une divergence est interdite.
 *
 * CE QUE CE COMPOSANT NE FAIT PAS. Il ne juge pas la cohérence entre la
 * nature de la tête et celle d'une ligne. Une ligne « DONNÉES RÉELLES » sous
 * un bandeau « DONNÉES SYNTHÉTIQUES » est un état produit LÉGITIME — la
 * dégradation vers le plus prudent que `vertex_worker.opportunities` applique
 * délibérément, et que le relais sert exprès (règle asymétrique de
 * `checked_relayed_content`). Ce qui était fautif n'était pas cette ligne,
 * mais qu'elle n'était ni nommée, ni distincte, ni fail-closed.
 */

/**
 * Teintes autorisées : ambre = prudence/dégradation, rouge = risque, neutre
 * pour le reste. Uniquement des tokens `--vx-*` — aucune couleur brute, sinon
 * `src/design/no-raw-colors.test.ts` échoue.
 *
 * La table est volontairement locale et typée `Record<PopulationTone, …>` :
 * TypeScript en garantit l'exhaustivité, et un ton ajouté au vocabulaire
 * casse la compilation ici au lieu de rendre une cellule sans teinte.
 */
const TONE_ACCENT: Record<PopulationTone, string> = {
  neutral: 'var(--vx-text)',
  caution: 'var(--vx-warning)',
  risk: 'var(--vx-negative)',
};

/** Longueur maximale d'une étiquette inconnue recopiée à l'écran. */
const MAX_ECHOED_LABEL = 24;

/**
 * La nature d'UN dossier : libellé français du vocabulaire fermé, ton,
 * code technique, et repli fail-closed identique à celui du bandeau.
 */
function PopulationCell({ candidate }: { readonly candidate: CandidateView }) {
  const { key, nature } = resolvePopulationNature(candidate.population);
  const declared = Object.hasOwn(POPULATION_NATURES, key);
  // L'écho ne cite QUE une étiquette reçue sous forme de chaîne, et bornée :
  // une valeur hors vocabulaire est du texte non fiable.
  const raw = typeof candidate.population === 'string' ? candidate.population : '';
  const echoed =
    key === 'UNRECOGNISED'
      ? raw.slice(0, MAX_ECHOED_LABEL) + (raw.length > MAX_ECHOED_LABEL ? '…' : '')
      : null;
  return (
    <span
      className="vx-opp-population"
      data-vx-population-cell=""
      data-vx-nature={key}
      data-vx-tone={nature.tone}
      title={nature.detail}
    >
      <strong data-testid="opp-population-label" style={{ color: TONE_ACCENT[nature.tone] }}>
        {nature.label}
      </strong>{' '}
      {declared ? <code>{key}</code> : null}
      {echoed !== null ? <code>{echoed}</code> : null}
      {candidate.synthetic ? (
        <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
      ) : null}
    </span>
  );
}

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
  /** LOT-A4 : ouvre le candidat dans l'inspecteur de la page. */
  readonly onInspect?: (ticker: string) => void;
  readonly selected?: string | null;
}

function InspectButton({
  ticker,
  selected,
  onInspect,
}: {
  readonly ticker: string;
  readonly selected: string | null;
  readonly onInspect: ((ticker: string) => void) | undefined;
}) {
  if (onInspect === undefined) {
    return null;
  }
  return (
    <button
      type="button"
      className="vx-opp-inspect"
      aria-label={`Inspecter ${ticker}`}
      aria-pressed={selected === ticker}
      onClick={() => {
        onInspect(ticker);
      }}
    >
      Inspecter
    </button>
  );
}

export function OpportunityTable({
  group,
  candidates,
  emptyMessage,
  contradictory = [],
  onInspect,
  selected = null,
}: OpportunityTableProps) {
  const titleId = `vx-opp-group-${group}`;
  const isQualified = group === 'qualified';
  return (
    <section
      className="vx-opp-group"
      /*
        LOT-A4 : le rang dominant est porté par la CARTE « Classement publié »
        qui contient les deux groupes — un seul porteur par page, tenu par la
        porte `one-dominant-per-page`. Le groupe qualifié garde sa tranche
        verte, le groupe exclu son ambre : deux régions, jamais confondues.
      */
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
                    <InspectButton ticker={candidate.ticker} selected={selected} onInspect={onInspect} />
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
                    <PopulationCell candidate={candidate} />
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
                    <InspectButton ticker={candidate.ticker} selected={selected} onInspect={onInspect} />
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
                    <PopulationCell candidate={candidate} />
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
