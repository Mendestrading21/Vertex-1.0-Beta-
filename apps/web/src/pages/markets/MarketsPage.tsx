import { useCallback, useMemo, useState } from 'react';

import type { MarketsOverview } from '../../api/client.ts';
import { pageStateOf, useMarketsOverview } from '../../api/hooks.ts';
import { useWorkspace } from '../../app/workspace.tsx';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { Metric } from '../../components/Metric.tsx';
import { CensusBars } from '../../components/CensusBars.tsx';
import { SectorGrid } from '../../components/markets/SectorGrid.tsx';
import { StatusChip } from '../../components/widgets/StatusChip.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { BreadthPanel } from './BreadthPanel.tsx';
import { MarketMap } from './MarketMap.tsx';
import { InstrumentInspector, SnapshotInspector } from './MarketsInspector.tsx';
import { MarketsTable } from './MarketsTable.tsx';
import { FocusRowModule } from '../../components/widgets/InstrumentTile.tsx';
import type { SignGroup } from '../../components/markets/marketsView.ts';
import {
  GROUP_LABELS_FR,
  censusOfNature,
  flattenTickers,
  provenanceSentence,
} from '../../components/markets/marketsView.ts';
import { marketsModule } from './marketsModules.ts';
import { pageAccentAttrs } from '../../components/widgets/pageAccent.ts';
import { MethodNote } from '../../components/widgets/MethodNote.tsx';

/**
 * Page Marchés (`TL / 02`) — question : « Dans quel contexte de marché
 * vais-je analyser les instruments ? »
 *
 * LOT-A3 — LA PLANCHE §2 EN ENTIER. `pages-01-02-today-markets.png` (moitié
 * droite) compose douze modules autour d'une dominante. Cinq sont SERVIS par
 * le seul snapshot `markets_overview` — la carte (dominante), la largeur de
 * marché, la santé de la couverture, la carte sectorielle, les écartés et
 * rejets — et sept n'ont aucune source ou aucun contrat (sessions, indices,
 * volatilité, taux, devises, corrélation, structure de volatilité) : ils
 * tiennent leur place avec le motif mesuré de leur absence (article 17).
 *
 * L'INSPECTEUR MONTRE L'INSTRUMENT SÉLECTIONNÉ — depuis une tuile, une puce
 * sectorielle ou une ligne de table — avec ses chaînes serveur et la lignée
 * de son calcul ; sans sélection, la vérité du snapshot.
 *
 * Aucun calcul financier ici : rendements, poids, breadth, pourcentages et
 * conclusion arrivent calculés et formatés par le worker via l'API.
 */

const ALL_GROUPS: readonly SignGroup[] = ['up', 'down', 'flat'];

/** État du cadre : l'état canonique publié par le worker prime en succès. */
export function frameStateOf(
  queryState: DataState | 'auth-required',
  data: MarketsOverview | undefined,
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
  if (data.data_state === 'partial') {
    return 'partial';
  }
  if (data.data_state === 'stale') {
    return 'stale';
  }
  return queryState;
}

function AbsentMarketsModule({ id }: { readonly id: string }) {
  const module = marketsModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
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

function MarketsFrame({
  data,
  state,
  selected,
  onSelect,
}: {
  readonly data: MarketsOverview;
  readonly state: DataState;
  readonly selected: string | null;
  readonly onSelect: (ticker: string) => void;
}) {
  const [visibleGroups, setVisibleGroups] = useState<ReadonlySet<SignGroup>>(
    new Set(ALL_GROUPS),
  );

  const allEntries = useMemo(() => flattenTickers(data.sectors), [data.sectors]);
  const nature = useMemo(() => censusOfNature(data.sectors), [data.sectors]);
  const visibleEntries = useMemo(
    () => allEntries.filter((entry) => visibleGroups.has(entry.group)),
    [allEntries, visibleGroups],
  );

  function toggleGroup(group: SignGroup): void {
    setVisibleGroups((previous) => {
      const next = new Set(previous);
      if (next.has(group)) {
        next.delete(group);
      } else {
        next.add(group);
      }
      // Vider entièrement la légende n'affiche plus rien : autorisé, honnête.
      return next;
    });
  }

  const coverage = data.coverage;
  const asOf = data.as_of;
  const description =
    data.conclusion ?? 'Carte des marchés : aucune conclusion serveur fournie.';

  const detail =
    state === 'partial'
      ? `Couverture incomplète publiée par le worker : ${
          coverage?.covered ?? 'nombre non publié d’'
        } instruments couverts sur ${coverage?.expected ?? 'un nombre non publié'} attendus, ${
          coverage?.discarded ?? 'un nombre non publié'
        } écartés.`
      : state === 'stale'
        ? data.state === 'stale'
          ? `Snapshot publié périmé par le relais : ${data.reason ?? 'raison non publiée'} ; âge publié ${data.age_seconds ?? 'non publié'} s.`
          : 'Toutes les observations couvertes sont périmées (data_state STALE publié par le worker).'
        : state === 'delayed'
          ? 'Population DELAYED publiée par le worker : les observations sont conservées, mais ne décrivent pas le marché à cet instant.'
        : undefined;

  return (
    <section
      className="vx-chartframe"
      data-rank="dominant"
      data-module="market-map"
      aria-labelledby="vx-marketmap-title"
    >
      {/* 1. WidgetHeader : question + titre */}
      <header className="vx-chartframe-head">
        <p className="vx-chartframe-question">
          Comment les secteurs et instruments suivis ont-ils évolué sur la dernière séance ?
        </p>
        {/*
          §4.1 : le titre disait « synthétiques » EN DUR, au-dessus de 161
          instruments IBKR réels. La nature appartient au bandeau de
          population, seul propriétaire de ce vocabulaire ; la dupliquer ici
          créait une seconde vérité, et elle était fausse.
        */}
        <h2 id="vx-marketmap-title">Carte des marchés</h2>
      </header>

      {/* 2. DataMeta : unité, période, source, as_of, couverture */}
      <dl className="vx-chartframe-meta">
        <div>
          <dt>Unité</dt>
          <dd>rendement 1 jour en % (ratio serveur « {data.unit ?? 'non publié'} »)</dd>
        </div>
        <div>
          <dt>Période</dt>
          <dd>2 clôtures journalières consécutives · UTC (stockage)</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>
            {/*
              §4.1 : `synthetic-dev` était écrit en dur alors que la source
              réelle est `ibkr`. Le contrat ne publie AUCUN champ de source ;
              il publie un drapeau `synthetic` PAR instrument. On recense donc
              ce qui est déclaré, au lieu de nommer une source qu'on ignore.
            */}
            snapshot worker v{data.snapshot_version ?? 'non publié'} — {provenanceSentence(nature)}
          </dd>
        </div>
        <div>
          <dt>as_of</dt>
          <dd>{asOf === null ? 'non publié' : <time dateTime={asOf}>{asOf}</time>}</dd>
        </div>
        <div>
          <dt>Couverture</dt>
          <dd>
            {coverage === null
              ? 'non publiée'
              : `${coverage.covered}/${coverage.expected} couverts, ${coverage.discarded} écartés, ${coverage.received} reçus`}
          </dd>
        </div>
      </dl>

      {/* 3. DataStateBoundary : état canonique publié + états requête */}
      <DataStateBoundary
        state={state}
        {...(detail !== undefined ? { detail } : {})}
        {...(asOf !== null ? { asOfLabel: `as_of ${asOf}` } : {})}
      >
        {/* Légende interactive : filtre LOCAL d'affichage, valeurs intactes. */}
        <div className="vx-chartframe-legend" role="group" aria-label="Légende et filtre local">
          {ALL_GROUPS.map((group) => (
            <button
              key={group}
              type="button"
              className="vx-legend-chip"
              data-group={group}
              aria-pressed={visibleGroups.has(group)}
              onClick={() => {
                toggleGroup(group);
              }}
            >
              <span className="vx-legend-swatch" data-group={group} aria-hidden="true" />
              {GROUP_LABELS_FR[group]}
            </button>
          ))}
          <span className="vx-legend-note">Filtre local d'affichage — aucune valeur modifiée.</span>
        </div>

        {/* 4. WidgetBody : dominante treemap */}
        <MarketMap
          sectors={data.sectors}
          visibleGroups={visibleGroups}
          description={description}
          onSelect={onSelect}
        />

        {/* 5. WidgetConclusion : phrase factuelle serveur, verbatim */}
        <p className="vx-chartframe-conclusion" data-testid="markets-conclusion">
          {data.conclusion ?? 'Aucune conclusion publiée.'}
        </p>

        {/* Table accessible équivalente (mêmes valeurs, tri clavier, sélection). */}
        <MarketsTable
          entries={visibleEntries}
          population={data.population}
          selected={selected}
          onSelect={onSelect}
        />
      </DataStateBoundary>

      {/* 6. WidgetFooter : méthode/calcul, version, limites et hypothèses */}
      <MethodNote
        methode={
          <>
            rendement 1 j <code>market.simple_return</code> et breadth{' '}
            <code>market.breadth</code> calculés par le worker (
            <code>{data.engine_version ?? 'version inconnue'}</code>, lignée{' '}
            <code>input_hash</code> conservée dans le snapshot). Poids = parts descriptives des
            clôtures servies.
          </>
        }
        attribution={<>Rendu : Apache ECharts (licence Apache-2.0), chargé uniquement sur cette route.</>}
        limites={
          <>
            2 clôtures par instrument, breadth refusée sous le seuil de couverture ; un instrument
            sans ses 2 clôtures est écarté et compté. Nature des données : voir le bandeau de
            population ci-dessus, qui en est le seul propriétaire.
          </>
        }
      />
    </section>
  );
}

/**
 * Santé de la couverture — trois mesures servies, puis leur DÉNOMBREMENT.
 *
 * Aucune part n'est calculée ici : le contrat publie des COMPTES (reçus,
 * couverts, écartés, rejetés) et aucun pourcentage de couverture. Les barres
 * de dénombrement montrent leur rapport de taille sans jamais écrire un
 * pourcentage que le serveur n'a pas servi — c'est exactement la raison
 * d'être de `CensusBars`.
 */
function MarketHealthModule({ data }: { readonly data: MarketsOverview }) {
  const module = marketsModule('market-health');
  const coverage = data.coverage;
  return (
    <Widget
      id="market-health"
      size={module.size}
      kicker="Couverture publiée"
      title={module.title}
      titleId="vx-markets-health-title"
      state="ready"
      footer={
        <>
          état worker <code>{data.data_state ?? 'non publié'}</code> · âge publié{' '}
          {data.age_seconds === null ? 'non publié' : `${data.age_seconds} s`}
        </>
      }
    >
      <div className="vx-metrics-row">
        <Metric
          label="Couverts"
          value={coverage === null ? null : `${coverage.covered}/${coverage.expected}`}
          {...(coverage !== null ? { note: `${coverage.received} reçus` } : {})}
        />
        <Metric
          label="Écartés"
          value={coverage === null ? null : String(coverage.discarded)}
          {...(coverage !== null ? { note: 'sans leurs deux clôtures' } : {})}
        />
        <Metric
          label="Rejets"
          value={coverage === null ? null : String(coverage.rejected_records.length)}
          {...(coverage !== null ? { note: 'observations refusées par les gates' } : {})}
        />
      </div>
      {coverage === null ? null : (
        <CensusBars
          entries={[
            { key: 'received', label: 'Reçus', count: coverage.received },
            { key: 'covered', label: 'Couverts', count: coverage.covered },
            { key: 'discarded', label: 'Écartés', count: coverage.discarded },
            { key: 'rejected', label: 'Rejetés', count: coverage.rejected_records.length },
          ]}
          ariaLabel="Dénombrement de la couverture publiée"
          testIdPrefix="markets-coverage-count"
          emptyLabel="Aucun compte de couverture publié."
        />
      )}
    </Widget>
  );
}

function DiscardsModule({ data }: { readonly data: MarketsOverview }) {
  const module = marketsModule('discards');
  const coverage = data.coverage;
  return (
    <Widget
      id="discards"
      size={module.size}
      kicker="Refus nommés"
      title={module.title}
      titleId="vx-markets-discards-title"
      state="ready"
      footer={<>raisons relayées telles quelles — jamais interpolées</>}
    >
      {coverage === null ? (
        <p className="vx-module-sentence" role="status">
          Couverture non publiée : aucun écart ni rejet n&apos;est connu.
        </p>
      ) : (
        <section className="vx-markets-discards" aria-labelledby="vx-markets-discards-list-title">
          <h3 id="vx-markets-discards-list-title">Instruments écartés ({coverage.discarded})</h3>
          {coverage.discarded_tickers.length === 0 ? (
            <p className="vx-module-sentence">Aucun instrument écarté.</p>
          ) : (
            <ul>
              {coverage.discarded_tickers.map((entry) => (
                <li key={entry.ticker}>
                  <code>{entry.ticker}</code> — raison :{' '}
                  <StatusChip label={entry.reason} tone="warning" />
                </li>
              ))}
            </ul>
          )}
          <h3>Observations rejetées ({coverage.rejected_records.length})</h3>
          {coverage.rejected_records.length === 0 ? (
            <p className="vx-module-sentence">Aucune observation rejetée par les gates.</p>
          ) : (
            <ul>
              {coverage.rejected_records.map((record) => (
                <li key={record.event_id}>
                  <code>{record.event_id}</code> — raison :{' '}
                  <StatusChip label={record.reason} tone="warning" />
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </Widget>
  );
}

function MarketsBoard({ data, state }: { readonly data: MarketsOverview; readonly state: DataState }) {
  const [selected, setSelected] = useState<string | null>(null);
  /*
    La sélection reste LOCALE pour l'inspecteur de cette planche — c'est elle
    qui décide quelle carte est mise en avant ici — et devient AUSSI un choix
    d'espace de travail, de sorte que passer ensuite sur Analyse ou Options
    retrouve l'instrument qu'on regardait. Sans cela, chaque page repartait de
    zéro : c'est le défaut que le contexte corrige.
  */
  const { selectInstrument } = useWorkspace();
  const choisir = useCallback(
    (ticker: string | null) => {
      setSelected(ticker);
      selectInstrument(ticker);
    },
    [selectInstrument],
  );
  const allEntries = useMemo(() => flattenTickers(data.sectors), [data.sectors]);
  const selectedEntry = allEntries.find((entry) => entry.ticker.ticker === selected) ?? null;
  const breadthModule = marketsModule('breadth');
  const sectorsModule = marketsModule('sectors');

  return (
    <>
      <SyntheticBanner population={data.population} />
      <div className="vx-markets-grid" data-testid="markets-grid">
        <AbsentMarketsModule id="sessions" />
        <AbsentMarketsModule id="volatility" />
        <AbsentMarketsModule id="indices" />

        <Widget
          id="breadth"
          size={breadthModule.size}
          kicker="Breadth publiée"
          title={breadthModule.title}
          titleId="vx-markets-breadth-title"
          state="ready"
          footer={<>comptes et seuils publiés par le worker — aucun pourcentage recalculé</>}
        >
          {data.breadth === null ? (
            <p className="vx-module-sentence" role="status">
              Breadth non publiée par le worker — aucune valeur de remplacement.
            </p>
          ) : (
            <BreadthPanel breadth={data.breadth} />
          )}
        </Widget>

        <MarketHealthModule data={data} />

        <div data-module="focus">
          <FocusRowModule />
        </div>

        <MarketsFrame data={data} state={state} selected={selected} onSelect={setSelected} />

        <Widget
          id="sectors"
          size={sectorsModule.size}
          kicker="Snapshot Marchés"
          title={sectorsModule.title}
          titleId="vx-markets-sectors-title"
          state="ready"
          action={<StatusChip label={`${data.sectors.length} secteur(s) publié(s)`} tone="neutral" />}
          footer={<>rendement 1 j par instrument, chaîne serveur ; aucun rendement de secteur n&apos;est publié</>}
        >
          <SectorGrid sectors={data.sectors} selected={selected} onSelect={setSelected} />
        </Widget>

        <AbsentMarketsModule id="rates-curve" />
        <AbsentMarketsModule id="fx" />
        <AbsentMarketsModule id="correlation" />
        <AbsentMarketsModule id="vol-structure" />

        <DiscardsModule data={data} />
      </div>

      {selectedEntry === null ? (
        <SnapshotInspector data={data} />
      ) : (
        <InstrumentInspector
          entry={selectedEntry}
          data={data}
          onClose={() => {
            choisir(null);
          }}
        />
      )}
    </>
  );
}

export function MarketsPage() {
  const overview = useMarketsOverview();
  const queryState = pageStateOf(overview);
  const data = overview.data;
  const state = frameStateOf(queryState, data);

  return (
    <article className="vx-page" {...pageAccentAttrs('markets')} aria-labelledby="vx-page-title-markets">
      <div className="vx-page-header">
        <h1 id="vx-page-title-markets">Marchés</h1>
        <p className="vx-page-question">
          Dans quel contexte de marché vais-je analyser les instruments ?
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
                  "L'API locale est injoignable — la carte des marchés ne peut pas être affichée.",
              }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucune carte affichée." }
              : {})}
        />
      ) : data !== undefined ? (
        <MarketsBoard data={data} state={state} />
      ) : null}
    </article>
  );
}
