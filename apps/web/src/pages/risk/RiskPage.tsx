import { useState } from 'react';

import type { RiskMatrixResponse } from '../../api/client.ts';
import { useRiskMatrix } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { moduleStateOf } from '../../components/moduleState.ts';
import type { ModuleState } from '../../components/moduleState.ts';
import { CellGrid } from '../../components/widgets/CellGrid.tsx';
import type { GridCell, GridLegendEntry } from '../../components/widgets/CellGrid.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
import type { WidgetServed } from '../../components/widgets/Widget.tsx';
import { InstrumentInspector, MatrixInspector } from './RiskInspector.tsx';
import {
  AbsentRiskModule,
  AlignmentModule,
  CoverageModule,
  DiscardsModule,
  DrawdownModule,
  ExtremesModule,
  MatrixStateChip,
  RegisterConcentrationModule,
  riskModuleState,
} from './RiskModules.tsx';
import { riskModule } from './riskModules.ts';
import { BAND_LABELS, riskViewOf } from './riskView.ts';
import type { RiskView } from './riskView.ts';
import { pageAccentAttrs } from '../../components/widgets/pageAccent.ts';

/**
 * Page Risques (`TL / 09`) — question : « Qu'est-ce qui bouge ensemble dans
 * mon périmètre, et qu'est-ce qui protège de quoi ? »
 *
 * Tout ce qui est CORRÉLATION vient du snapshot `risk_matrix/global` publié
 * par le worker et relayé verbatim par l'API. L'interface ne calcule AUCUN
 * coefficient et ne reclasse aucune case : les nombres arrivent en chaînes
 * rendues, les bandes arrivent sous forme de noms.
 *
 * LOT P4 — LA PLANCHE §9 SUR LES FORMES V2. La matrice devient une `CellGrid`
 * (ADR-017) : la bande SERVIE passe verbatim dans `data-band`, une bande
 * absente devient `unknown` VISIBLE, et une cellule non publiée se lit « non
 * publié ». Le composant précédent remplaçait une bande manquante par `weak`,
 * ce qui affirmait « peu liés » sur une case dont personne n'avait rien
 * publié : un faux rassurant, corrigé ici.
 *
 * La page déclare sa teinte secondaire `macro` (`PAGE_ACCENTS`) : contexte de
 * marché, jamais un verdict. Le vert et le rouge restent réservés au signe
 * financier servi.
 *
 * TROIS ÉTATS DE MATRICE, JAMAIS CONFONDUS.
 *
 * - `ok` : la matrice est servie ;
 * - `refus` : le worker A publié, mais il n'a PAS pu bâtir la matrice —
 *   périmètre trop court, séances communes insuffisantes, variance nulle. Le
 *   motif et la conclusion française s'affichent dans la dominante. Ce n'est
 *   pas un écran vide : c'est une réponse ;
 * - `empty` : rien n'a jamais été publié, soit qu'aucun périmètre ne soit
 *   déclaré, soit qu'aucune barre n'ait été collectée. La planche reste
 *   composée : la dominante porte l'aveu, les autres modules leur état.
 *
 * L'AVERTISSEMENT DE SYNCHRONICITÉ EST AFFICHÉ, PAS RANGÉ. Les places ne
 * ferment pas à la même heure : mesuré le 2026-09-01, SPX/N225 tombe à
 * +0,168 parce que Tokyo ferme avant l'ouverture de New York, et non parce
 * que le Japon serait décorrélé du monde. Sans cette phrase à l'écran, un
 * artefact de fuseau se lirait comme un fait de marché.
 *
 * L'INSPECTEUR MONTRE L'INSTRUMENT OUVERT depuis la matrice — coefficients
 * avec chacun, bande publiée, séances perdues, motif d'écart — sinon la
 * vérité du snapshot.
 */

/** Libellés des bandes SERVIES. Une bande inconnue reste visible et nommée. */
const BAND_LEGEND: readonly GridLegendEntry[] = Object.entries(BAND_LABELS).map(([band, label]) => ({
  band,
  label,
}));

/** Cellules de la matrice, SERVIES : rien n'est complété ni reclassé. */
function gridCells(view: RiskView): readonly GridCell[] {
  const cells: GridCell[] = [];
  view.instruments.forEach((row, rowIndex) => {
    view.instruments.forEach((col, colIndex) => {
      cells.push({
        row: row.ticker,
        col: col.ticker,
        band: view.bands[rowIndex]?.[colIndex] ?? '',
        text: view.matrix[rowIndex]?.[colIndex] ?? null,
      });
    });
  });
  return cells;
}

function thresholdLegend(view: RiskView): string {
  const fort = view.coverage.strongThreshold;
  const modere = view.coverage.moderateThreshold;
  const dire = (valeur: string | null) => (valeur === null ? 'un seuil non publié' : valeur);
  return `Coefficients servis sur les séances communes — fort dès ${dire(fort)}, modéré dès ${dire(modere)} en valeur absolue ; le signe donne le sens.`;
}

function MatrixModule({
  data,
  view,
  state,
  served,
  selected,
  onSelect,
}: {
  readonly data: RiskMatrixResponse;
  readonly view: RiskView | null;
  readonly state: ModuleState;
  readonly served: WidgetServed;
  readonly selected: string | null;
  readonly onSelect: (ticker: string) => void;
}) {
  const module = riskModule('correlations');
  return (
    <Widget
      id="correlations"
      size={module.size}
      rank="dominant"
      kicker="Corrélations publiées"
      title={module.title}
      titleId="vx-risk-matrix-title"
      state={state}
      served={served}
      conclusion={view === null || view.serverState === 'empty' ? null : view.conclusion}
      stateDetail={
        view === null || view.serverState === 'empty'
          ? `Aucun instantané publié — soit aucun périmètre n'est déclaré, soit aucune barre n'a encore été collectée (raison serveur : ${data.reason ?? 'non fournie'}). Rien n'est inventé à la place.`
          : view.refusalReason
      }
      action={view === null ? undefined : <MatrixStateChip view={view} />}
      footer={<>rendements quotidiens sur les séances communes ; coefficients et bandes publiés par le worker, jamais recalculés</>}
    >
      {view === null || view.serverState === 'empty' ? (
        <p className="vx-module-sentence" role="status">
          Aucun instantané publié — soit aucun périmètre n'est déclaré, soit aucune barre n'a encore été collectée (raison
          serveur&nbsp;: {data.reason ?? 'non fournie'}). Rien n'est inventé à la place.
        </p>
      ) : view.refusalReason !== null ? (
        // La conclusion servie est déjà dans la tête du widget : le motif ne
        // s'écrit qu'ici, jamais la même phrase deux fois.
        <p className="vx-module-sentence" role="status">
          Aucune matrice n'a pu être construite&nbsp;: {view.refusalReason}.
        </p>
      ) : (
        <div className="vx-riskmatrix">
          <CellGrid
            rows={view.instruments.map((entry) => ({ key: entry.ticker, label: entry.label }))}
            cols={view.instruments.map((entry) => ({ key: entry.ticker, label: entry.ticker }))}
            cells={gridCells(view)}
            legend={BAND_LEGEND}
            caption={thresholdLegend(view)}
            onOpenRow={onSelect}
            selectedRow={selected}
            rowActionLabel={(row) => `Inspecter ${row.key} (${row.label})`}
          />
        </div>
      )}
    </Widget>
  );
}

function RiskBoard({
  data,
  view,
  pageState,
}: {
  readonly data: RiskMatrixResponse;
  readonly view: RiskView | null;
  readonly pageState: ModuleState;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const opened = view !== null && selected !== null && view.instruments.some((entry) => entry.ticker === selected) ? selected : null;
  // Un seul état pour tous les modules du snapshot : celui de la page, affiné
  // par l'état des données SERVI (`data_state`) quand il annonce du partiel.
  const state = riskModuleState(pageState, view?.dataState ?? null);
  const served: WidgetServed = {
    asOf: view?.asOf ?? data.as_of ?? null,
    ageSeconds: data.age_seconds,
    // L'ÉCHELLE SERVIE. `freshness_policy` traverse douze routes depuis le
    // début ; aucun fichier d'interface ne la lisait. Sans elle, « il y a 3 j »
    // ne dit pas de quoi il est l'âge.
    budgetSeconds: data.freshness_policy?.budget_seconds ?? null,
    policyKind: data.freshness_policy?.kind ?? null,
    policyVersion: data.freshness_policy?.version ?? null,
    snapshotVersion: data.snapshot_version ?? null,
    population: view?.population ?? null,
    sourceLabel: 'instantané de matrice publié',
  };

  return (
    <>
      <div className="vx-risk-grid vx-board" data-testid="risk-grid">
        <AbsentRiskModule id="risk-score" />
        <AbsentRiskModule id="var-cvar" />
        <DrawdownModule />
        <AbsentRiskModule id="benchmark-relative" />

        <AbsentRiskModule id="volatility" />
        <RegisterConcentrationModule />
        <AbsentRiskModule id="liquidity" />

        <MatrixModule
          data={data}
          view={view}
          state={state}
          served={served}
          selected={opened}
          onSelect={(ticker) => {
            setSelected((previous) => (previous === ticker ? null : ticker));
          }}
        />
        <AbsentRiskModule id="turnover" />
        <ExtremesModule view={view} state={state} />

        <AbsentRiskModule id="stress-loss" />
        <AbsentRiskModule id="factor-exposures" />
        <AbsentRiskModule id="risk-budget" />
        <AbsentRiskModule id="radar" />

        <CoverageModule view={view} state={state} />
        <AlignmentModule view={view} state={state} />
        <DiscardsModule view={view} state={state} />
        <AbsentRiskModule id="risk-register" />
        <AbsentRiskModule id="alert-log" />
      </div>

      {opened === null || view === null ? (
        <MatrixInspector data={data} view={view} />
      ) : (
        <InstrumentInspector
          ticker={opened}
          view={view}
          onClose={() => {
            setSelected(null);
          }}
        />
      )}
    </>
  );
}

export function RiskPage() {
  const query = useRiskMatrix();
  const state = pageStateOf(query);
  const data = query.data;
  const view = data === undefined || data.state === 'empty' ? null : riskViewOf(data);
  const moduleState = moduleStateOf(state, data);

  return (
    <article className="vx-page" {...pageAccentAttrs('risks')} aria-labelledby="vx-page-title-risk">
      <div className="vx-page-header">
        <h1 id="vx-page-title-risk">Risques</h1>
        <p className="vx-page-question">
          Qu'est-ce qui bouge ensemble dans mon périmètre, et qu'est-ce qui protège de quoi ?
        </p>
      </div>

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'loading' || state === 'offline' || state === 'error' ? (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? { detail: "L'API locale est injoignable — la matrice ne peut pas être affichée." }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucune matrice affichée." }
              : {})}
        />
      ) : data === undefined ? (
        <DataStateBoundary state="error" detail="Réponse absente — rien n'est affiché à la place." />
      ) : (
        <>
          {/*
            Le bandeau est TOUJOURS rendu quand un contenu est publié, avec
            l'aveu tel quel. Il juge lui-même : une population non déclarée ou
            non reconnue est signalée plutôt que passée sous silence.
          */}
          {view !== null ? <SyntheticBanner population={view.population} /> : null}
          {view !== null && view.serverState === 'stale' ? (
            <DataStateBoundary state="stale" {...(typeof data.reason === 'string' ? { detail: data.reason } : {})} />
          ) : null}
          <RiskBoard data={data} view={view} pageState={moduleState} />
        </>
      )}
    </article>
  );
}
