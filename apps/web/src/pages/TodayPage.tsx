import type { AttentionSnapshot } from '../api/client.ts';
import { pageStateOf, useAttention } from '../api/hooks.ts';
import type { PageDataState } from '../api/hooks.ts';
import { AbsentModule } from '../components/AbsentModule.tsx';
import { AuthRequiredNotice } from '../components/AuthRequiredNotice.tsx';
import { Card } from '../components/Card.tsx';
import { DataStateBoundary } from '../components/DataStateBoundary.tsx';
import type { DataState } from '../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../components/SyntheticBanner.tsx';
import { InspectorPanel } from '../shell/inspector.tsx';
import { AttentionQueue } from './AttentionQueue.tsx';
import { FocusRowModule } from './InstrumentWidget.tsx';
import { SnapshotRail } from './SnapshotRail.tsx';
import {
  CalendarModule,
  GlobalMarketModule,
  ManualPortfolioModule,
  NextCatalystModule,
  OpportunitiesModule,
  SectorsModule,
  SourceHealthModule,
} from './TodayModules.tsx';
import { todayModule } from './todayView.ts';

/**
 * Page Aujourd'hui (`TL / 01`) — question : « Qu'est-ce qui mérite réellement
 * mon attention maintenant ? »
 *
 * LOT-A3 — LA PLANCHE §1 EN ENTIER. `pages-01-02-today-markets.png` (moitié
 * gauche) compose onze modules autour d'une dominante. Huit sont SERVIS par
 * des contrats existants, chacun lu par le hook de sa page propriétaire :
 * la file d'attention (dominante), le marché global et la carte sectorielle
 * (snapshot Marchés), le catalyseur suivant et le calendrier (snapshot
 * Calendrier), la santé des sources (capacités), les opportunités (moteur
 * fail-closed) et le portefeuille manuel (valorisation déclarée). Trois n'ont
 * AUCUNE source — régime, volatilité, risques actifs — et tiennent leur
 * place avec le motif mesuré de leur absence (`AbsentModule`, article 17).
 *
 * LA DOMINANTE RESTE LA FILE. La planche pose « régime + graphique global »
 * en dominante ; aucun des deux n'a de source. La file est la seule donnée
 * qui RÉPOND à la question de la page — elle garde la lumière, et le régime
 * absent le dit à sa place, à sa géométrie.
 *
 * L'INSPECTEUR EST TOUJOURS OCCUPÉ : le détail de l'item ouvert, sinon la
 * vérité du snapshot (version, horodatage, population, couverture) — la
 * provenance de la file, jamais une colonne vide.
 *
 * Un seul propriétaire par donnée, aucun calcul ici : chaînes serveur,
 * comptes publiés, ordre publié. Chaque module dit son propre état.
 */

/**
 * État du cadre d'attention, dérivé des faits servis et jamais du seul succès
 * HTTP. L'absence explicite de snapshot prime sur les états qui supposent un
 * contenu ; un snapshot périmé prime ensuite sur sa population, puis une
 * population retardée sur un rafraîchissement de transport.
 */
export function attentionFrameStateOf(
  queryState: PageDataState,
  data: AttentionSnapshot | undefined,
): DataState | 'auth-required' {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return queryState;
  }
  if (data === undefined) {
    return 'error';
  }
  if (data.state === 'empty') {
    return 'empty';
  }
  if (data.state === 'stale') {
    return 'stale';
  }
  if (data.population === 'DELAYED') {
    return 'delayed';
  }
  return queryState;
}

function degradedDetailOf(state: DataState | 'auth-required', data: AttentionSnapshot | undefined) {
  if (data === undefined) {
    return undefined;
  }
  const age = data.age_seconds === null ? 'âge non publié' : `âge publié ${data.age_seconds} s`;
  if (state === 'stale') {
    return `Snapshot publié périmé par le relais : ${
      data.reason ?? 'raison non publiée'
    } ; ${age}.`;
  }
  if (state === 'delayed') {
    return `Population DELAYED publiée par le worker : ces observations ne décrivent pas le marché à cet instant ; ${age}.`;
  }
  return undefined;
}

function AbsentTodayModule({ id }: { readonly id: string }) {
  const module = todayModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    <div data-module={id} className="vx-today-cell">
      <AbsentModule
        title={module.title}
        question={module.question}
        reason={module.status.reason}
        note={module.status.note}
      />
    </div>
  );
}

/** Inspecteur par défaut : la vérité du snapshot qui alimente la file. */
function SnapshotInspector({ data }: { readonly data: AttentionSnapshot }) {
  return (
    <InspectorPanel subject="Snapshot publié">
      <SnapshotRail
        snapshotVersion={data.snapshot_version}
        asOf={data.as_of}
        population={data.population}
        itemCount={data.items.length}
        rejectedCount={data.rejected_count}
        coverage={data.coverage}
      />
    </InspectorPanel>
  );
}

function TodayBoard({
  data,
  state,
}: {
  readonly data: AttentionSnapshot;
  readonly state: DataState;
}) {
  const degradedDetail = degradedDetailOf(state, data);
  return (
    <div className="vx-today-grid" data-testid="today-grid">
      <AbsentTodayModule id="regime" />

      <div data-module="global-market" className="vx-today-cell">
        <GlobalMarketModule />
      </div>
      <AbsentTodayModule id="volatility" />
      <div data-module="next-catalyst" className="vx-today-cell">
        <NextCatalystModule />
      </div>
      <div data-module="source-health" className="vx-today-cell">
        <SourceHealthModule />
      </div>

      {/*
        Les instruments suivis — prix, variation, mini-courbe, volume — sur
        les dossiers d'analyse publiés. Un module de plus que la planche §1 :
        demandé explicitement, servi entièrement, borné à quatre dossiers.
      */}
      <div data-module="focus" className="vx-today-cell">
        <FocusRowModule />
      </div>

      <div data-module="attention" className="vx-today-cell vx-today-primary">
        <DataStateBoundary
          state={state}
          {...(degradedDetail !== undefined ? { detail: degradedDetail } : {})}
          {...(data.as_of !== null ? { asOfLabel: `as_of ${data.as_of}` } : {})}
        >
          {/*
            Le bandeau de population qualifie CE snapshot — celui de la file.
            Les autres modules lisent d'autres snapshots et portent chacun
            leur population dans leur pied : un bandeau de page les
            confondrait.
          */}
          <SyntheticBanner population={data.population} />
          <Card
            rank="dominant"
            kicker="Priorité publiée"
            title="File d'attention"
            titleId="vx-attention-title"
            aside={<>{data.items.length} éléments</>}
            footer={
              <>
                Ordre publié par le worker — aucun reclassement local. Population{' '}
                {data.population ?? 'non publiée'}
                {data.as_of === null ? '' : ` · as_of ${data.as_of}`}
              </>
            }
          >
            <AttentionQueue
              items={data.items}
              asOf={data.as_of}
              fallbackInspector={<SnapshotInspector data={data} />}
            />
          </Card>
        </DataStateBoundary>
      </div>

      <div data-module="opportunities" className="vx-today-cell">
        <OpportunitiesModule />
      </div>
      <AbsentTodayModule id="active-risks" />
      <div data-module="sectors" className="vx-today-cell">
        <SectorsModule />
      </div>
      <div data-module="manual-portfolio" className="vx-today-cell">
        <ManualPortfolioModule />
      </div>
      <div data-module="calendar" className="vx-today-cell">
        <CalendarModule />
      </div>
    </div>
  );
}

export function TodayPage() {
  const attention = useAttention();
  const queryState = pageStateOf(attention);
  const data = attention.data;
  const state = attentionFrameStateOf(queryState, data);

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-today">
      <div className="vx-page-header">
        <p className="vx-page-eyebrow">Cockpit décisionnel</p>
        <h1 id="vx-page-title-today">Aujourd'hui</h1>
        <p className="vx-page-question">
          Qu'est-ce qui mérite réellement mon attention maintenant ?
        </p>
      </div>

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={`Aucun snapshot publié — le worker n'a encore rien produit (raison serveur : ${
            data?.reason ?? 'non fournie'
          }). Rien n'est inventé à la place.`}
        />
      ) : state === 'loading' || state === 'offline' || state === 'error' ? (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? {
                detail:
                  "L'API locale est injoignable — la file d'attention ne peut pas être affichée.",
              }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucune file affichée." }
              : {})}
        />
      ) : data !== undefined ? (
        <TodayBoard data={data} state={state} />
      ) : (
        <DataStateBoundary
          state="error"
          detail="Réponse absente — aucune file affichée à la place."
        />
      )}
    </article>
  );
}
