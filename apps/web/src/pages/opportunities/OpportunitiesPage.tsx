import { useMemo, useState } from 'react';

import type { OpportunitiesResponse } from '../../api/client.ts';
import { useOpportunities } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { Metric } from '../../components/Metric.tsx';
import { ProvenanceLine } from '../../components/widgets/ProvenanceLine.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
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
    // LOT P2d — LA TAILLE VIENT DU CATALOGUE, PAS DE LA MISE EN PAGE. Une
    // absence occupe l'aire que la planche lui a réservée ; sans `data-size`
    // elle prendrait la taille par défaut et déplacerait ses voisines.
    <div data-module={id} data-size={module.size}>
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
    <Widget
      id={module.id}
      size={module.size}
      state="ready"
      rank="dominant"
      kicker="Ordre publié"
      title={module.title}
      titleId="vx-opp-ranking-title"
      action={<>{view.candidates.qualified.length + view.candidates.contradictory.length + view.candidates.excluded.length} candidats publiés</>}
      footer={
        <>
          Classement :{' '}
          {view.ordering.method === null ? (
            <span className="vx-cell-absent">méthode de classement non publiée</span>
          ) : (
            <code>{view.ordering.method}</code>
          )}
          {' — '}
          {view.ordering.keys.join(' → ') || 'aucune clé publiée'}.{' '}
          {view.ordering.note ?? ''} Aucun reclassement local.
        </>
      }
    >
      {/* LOT T4-1 — SIX TIRETS MUETS DANS UNE SEULE LIGNE. Chacun remplaçait
          un fait de provenance différent, et aucun ne disait lequel manquait.
          `ProvenanceLine` (première pose du produit) dit chaque champ ABSENT à
          sa place ; les deux DÉNOMBREMENTS, qui ne sont pas de la provenance,
          passent en `Metric`, qui rend nativement « non publié ».

          Le conteneur devient un <div> : `ProvenanceLine` rend un <p>, et un
          <p> dans un <p> est du HTML invalide. Le testid reste sur le
          conteneur — il porte l'assertion de fraîcheur.

          `sources={[]}` est un FAIT : le contrat Opportunités ne publie aucune
          liste de sources, et la primitive le dira plutôt que de laisser
          croire qu'on ne l'a pas demandée. */}
      <div className="vx-opp-provenance" data-testid="opp-provenance">
        <FreshnessBadge
          ageSeconds={data.age_seconds}
          sourceLabel="âge publié par le serveur"
        />
        <ProvenanceLine
          asOf={view.asOf}
          snapshotVersion={data.snapshot_version ?? null}
          schemaVersion={view.schemaVersion}
          engineVersion={view.engineVersion}
          sources={[]}
          method={view.ordering.method}
          population={view.population}
        />
        <div className="vx-metrics-row">
          <Metric
            label="Univers déclaré"
            size="compact"
            value={view.coverage.universeSize === null ? null : String(view.coverage.universeSize)}
            absentLabel="Univers déclaré : non publié par le snapshot"
          />
          <Metric
            label="Observations considérées"
            size="compact"
            value={
              view.coverage.observationsConsidered === null
                ? null
                : String(view.coverage.observationsConsidered)
            }
            absentLabel="Observations considérées : non publiées par le snapshot"
          />
        </div>
      </div>

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
    </Widget>
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
        <ActiveIdeasModule view={view} />
        <AbsentOpportunitiesModule id="mean-score" />
        <AbsentOpportunitiesModule id="global-bias" />
        <AbsentOpportunitiesModule id="expected-return" />

        <RankingModule data={data} view={view} selected={selected} onInspect={setSelected} />

        <BiasSplitModule view={view} />
        <AbsentOpportunitiesModule id="score-return-scatter" />
        <AbsentOpportunitiesModule id="factor-contribution" />
        <AbsentOpportunitiesModule id="recent-activity" />

        <OpportunityHealthModule view={view} />
        <ProfileModule view={view} />
        <ExclusionsModule view={view} />
        <CalendarRefModule view={view} />
        <LimitationsModule view={view} />
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
