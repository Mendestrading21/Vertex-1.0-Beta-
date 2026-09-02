import { useMemo, useState } from 'react';

import type { OpportunitiesResponse } from '../../api/client.ts';
import { useOpportunities } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { Card } from '../../components/Card.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { CandidateInspector, OpportunitiesSnapshotInspector } from './CandidateInspector.tsx';
import {
  ActiveIdeasModule,
  BiasSplitModule,
  CalendarRefModule,
  ExclusionsModule,
  LimitationsModule,
  OpportunityHealthModule,
  ProfileModule,
} from './OpportunitiesModules.tsx';
import { OpportunityTable } from './OpportunityTable.tsx';
import { opportunitiesModule } from './opportunitiesModules.ts';
import { opportunitiesFrameStateOf } from './opportunitiesView.ts';
import type { CandidateView, OpportunitiesContentView } from './opportunitiesView.ts';

/**
 * LOT-A3 : la dérivation d'état vit dans la vue pure, parce qu'Aujourd'hui
 * la réutilise. L'importer depuis ce fichier tirait la page entière dans le
 * chunk d'Aujourd'hui (porte performance : `INEFFECTIVE_DYNAMIC_IMPORT`).
 * Le ré-export conserve le point d'entrée des tests.
 */
export { opportunitiesFrameStateOf };

/**
 * Page Opportunités (`TL / 03`) — question : « Quels candidats admissibles
 * méritent une analyse approfondie ? »
 *
 * LOT-A4 — LA PLANCHE §3 EN ENTIER. `pages-03-04-opportunities-analysis.png`
 * (moitié gauche) compose quatorze modules autour d'une dominante. Huit sont
 * SERVIS par le seul snapshot `opportunities/global` — le classement
 * (dominante : les deux groupes, jamais mélangés), les candidats évalués, la
 * répartition des directions, les statuts sur l'univers, le profil, les
 * raisons d'exclusion, la provenance des catalyseurs, les limites — et six
 * n'ont aucune source ou aucun contrat : score moyen, biais global,
 * rendement attendu, nuage score/rendement, contribution des facteurs
 * (le moteur ne publie AUCUN score : « aucun score opaque »), activité
 * récente. Ils tiennent leur place avec le motif mesuré de leur absence.
 *
 * L'INSPECTEUR MONTRE LE CANDIDAT OUVERT depuis le classement — admission,
 * exclusion publiée, gates, preuves requises — sinon la vérité du snapshot.
 *
 * Tout vient du snapshot publié par le worker sous l'unique `AdviceEngine`.
 * L'interface ne classe ni ne note : elle sépare strictement les deux
 * groupes, affiche pour chaque exclu la raison publiée, et rend visible la
 * provenance. Sur la population synthétique actuelle, la totalité des
 * candidats est exclue en `INSUFFICIENT_DATA` : comportement VOULU d'un
 * moteur fail-closed, affiché comme tel — pas un état d'erreur.
 *
 * États servis, jamais confondus : `ok`, `stale` (même contenu sous le
 * bandeau « Données périmées », âge PUBLIÉ par le serveur) et `empty`.
 * `clock_inconsistent` reste FERMÉ, avec la cause publiée.
 */

function AbsentOpportunitiesModule({ id }: { readonly id: string }) {
  const module = opportunitiesModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    <div data-module={id}>
      <AbsentModule
        title={module.title}
        question={module.question}
        reason={module.status.reason}
        note={module.status.note}
      />
    </div>
  );
}

/** Filtre LOCAL d'affichage par statut publié — jamais un reclassement. */
function statusesOf(view: OpportunitiesContentView): readonly string[] {
  const statuses = new Set<string>();
  for (const candidate of [
    ...view.candidates.qualified,
    ...view.candidates.contradictory,
    ...view.candidates.excluded,
  ]) {
    statuses.add(candidate.advice.status);
  }
  return [...statuses].sort((left, right) => left.localeCompare(right));
}

function RankingModule({
  data,
  view,
  selected,
  onInspect,
}: {
  readonly data: OpportunitiesResponse;
  readonly view: OpportunitiesContentView;
  readonly selected: string | null;
  readonly onInspect: (ticker: string) => void;
}) {
  const module = opportunitiesModule('ranking');
  const statuses = useMemo(() => statusesOf(view), [view]);
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());
  const keep = (candidate: CandidateView): boolean => !hidden.has(candidate.advice.status);
  const qualified = view.candidates.qualified.filter(keep);
  const contradictory = view.candidates.contradictory.filter(keep);
  const excluded = view.candidates.excluded.filter(keep);

  function toggle(status: string): void {
    setHidden((previous) => {
      const next = new Set(previous);
      if (next.has(status)) {
        next.delete(status);
      } else {
        next.add(status);
      }
      return next;
    });
  }

  return (
    <Card
      rank="dominant"
      kicker="Ordre publié"
      title={module.title}
      titleId="vx-opp-ranking-title"
      aside={<>{view.candidates.qualified.length + view.candidates.contradictory.length + view.candidates.excluded.length} candidats publiés</>}
      footer={
        <>
          Classement : <code>{view.ordering.method ?? '—'}</code> —{' '}
          {view.ordering.keys.join(' → ') || 'aucune clé publiée'}.{' '}
          {view.ordering.note ?? ''} Aucun reclassement local.
        </>
      }
    >
      <p className="vx-opp-provenance" data-testid="opp-provenance">
        <FreshnessBadge
          ageSeconds={data.age_seconds}
          sourceLabel="âge publié par le serveur"
        />
        {' — '}
        Snapshot version <code>{data.snapshot_version ?? '—'}</code> — publié{' '}
        {view.asOf !== null ? <time dateTime={view.asOf}>{view.asOf}</time> : '—'} — moteur{' '}
        <code>{view.engineVersion ?? '—'}</code> — schéma <code>{view.schemaVersion ?? '—'}</code>{' '}
        — univers déclaré <span className="vx-num">{view.coverage.universeSize ?? '—'}</span> —
        observations considérées{' '}
        <span className="vx-num">{view.coverage.observationsConsidered ?? '—'}</span>
      </p>

      {statuses.length > 1 ? (
        <div className="vx-matrix-filters vx-opp-filters" role="group" aria-label="Statuts affichés">
          {statuses.map((status) => (
            <button
              key={status}
              type="button"
              className="vx-legend-chip"
              aria-pressed={!hidden.has(status)}
              onClick={() => {
                toggle(status);
              }}
            >
              <code>{status}</code>
            </button>
          ))}
        </div>
      ) : null}

      <OpportunityTable
        group="qualified"
        candidates={qualified}
        contradictory={[]}
        selected={selected}
        onInspect={onInspect}
        emptyMessage={
          hidden.size > 0 && view.candidates.qualified.length > 0
            ? 'Aucun candidat qualifié dans les statuts affichés.'
            : 'Aucun candidat qualifié. Sur cette population, le moteur unique ferme les gates ' +
              'requises et publie un statut fermé pour chaque candidat : c’est le comportement ' +
              'attendu d’une décision fail-closed, pas une panne. Le détail par candidat est ' +
              'dans le groupe « Exclus » ci-dessous.'
        }
      />

      <OpportunityTable
        group="excluded"
        candidates={excluded}
        contradictory={contradictory}
        selected={selected}
        onInspect={onInspect}
        emptyMessage="Aucun candidat exclu publié."
      />
    </Card>
  );
}

function OpportunitiesBoard({
  data,
  view,
}: {
  readonly data: OpportunitiesResponse;
  readonly view: OpportunitiesContentView;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const picked = useMemo(() => {
    if (selected === null) {
      return null;
    }
    const contradictory = view.candidates.contradictory.find((candidate) => candidate.ticker === selected);
    if (contradictory !== undefined) {
      return { candidate: contradictory, contradictory: true };
    }
    const candidate = [...view.candidates.qualified, ...view.candidates.excluded].find(
      (entry) => entry.ticker === selected,
    );
    return candidate === undefined ? null : { candidate, contradictory: false };
  }, [selected, view]);

  return (
    <>
      <div className="vx-opp-grid vx-board" data-testid="opportunities-grid">
        <div data-module="active-ideas">
          <ActiveIdeasModule view={view} />
        </div>
        <AbsentOpportunitiesModule id="mean-score" />
        <AbsentOpportunitiesModule id="global-bias" />
        <AbsentOpportunitiesModule id="expected-return" />

        <div data-module="ranking">
          <RankingModule data={data} view={view} selected={selected} onInspect={setSelected} />
        </div>

        <div data-module="bias-split">
          <BiasSplitModule view={view} />
        </div>
        <AbsentOpportunitiesModule id="score-return-scatter" />
        <AbsentOpportunitiesModule id="factor-contribution" />
        <AbsentOpportunitiesModule id="recent-activity" />

        <div data-module="opportunity-health">
          <OpportunityHealthModule view={view} />
        </div>
        <div data-module="profile">
          <ProfileModule view={view} />
        </div>
        <div data-module="exclusions">
          <ExclusionsModule view={view} />
        </div>
        <div data-module="catalysts-provenance">
          <CalendarRefModule view={view} />
        </div>
        <div data-module="quality">
          <LimitationsModule view={view} />
        </div>
      </div>

      {picked === null ? (
        <OpportunitiesSnapshotInspector data={data} view={view} />
      ) : (
        <CandidateInspector
          candidate={picked.candidate}
          contradictory={picked.contradictory}
          onClose={() => {
            setSelected(null);
          }}
        />
      )}
    </>
  );
}

export function OpportunitiesPage() {
  const query = useOpportunities();
  const queryState = pageStateOf(query);
  const frame = opportunitiesFrameStateOf(queryState, query.data);
  const view = frame.view;

  return (
    <article className="vx-page vx-opportunities" aria-labelledby="vx-page-title-opportunities">
      <div className="vx-page-header">
        <h1 id="vx-page-title-opportunities">Opportunités</h1>
        <p className="vx-page-question">
          Quels candidats admissibles méritent une analyse approfondie ?
        </p>
      </div>

      {view !== null ? <SyntheticBanner population={view.population} /> : null}

      {frame.state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : view === null || query.data === undefined ? (
        <DataStateBoundary
          state={frame.state as DataState}
          {...(frame.state === 'empty'
            ? {
                detail:
                  query.data?.reason ??
                  'Aucun snapshot d’opportunités publié : rien n’est affiché.',
              }
            : {})}
          {...(frame.detail !== undefined ? { detail: frame.detail } : {})}
        />
      ) : (
        <DataStateBoundary
          state={frame.state as DataState}
          {...(frame.state === 'stale'
            ? {
                detail:
                  query.data.reason ??
                  'Verdict hors budget de fraîcheur (raison non publiée) : il n’est pas courant.',
              }
            : {})}
          {...(query.data.as_of != null ? { asOfLabel: query.data.as_of } : {})}
        >
          <OpportunitiesBoard data={query.data} view={view} />
        </DataStateBoundary>
      )}
    </article>
  );
}
