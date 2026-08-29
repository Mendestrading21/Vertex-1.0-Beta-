import { useMemo, useState } from 'react';

import type { MarketsOverview } from '../../api/client.ts';
import { pageStateOf, useMarketsOverview } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { BreadthPanel } from './BreadthPanel.tsx';
import { MarketMap } from './MarketMap.tsx';
import { MarketsTable } from './MarketsTable.tsx';
import type { SignGroup } from './marketsView.ts';
import { GROUP_LABELS_FR, flattenTickers } from './marketsView.ts';

/**
 * Page Marchés — question : « Dans quel contexte de marché vais-je analyser
 * les instruments ? »
 *
 * Dominante unique : la MarketMap (treemap ECharts, chunk chargé par la
 * route) dans un cadre conforme CHART_STANDARD — question, titre, unité,
 * source, `as_of`, couverture, état, légende interactive (filtre local
 * d'affichage), conclusion textuelle DÉTERMINISTE produite côté serveur,
 * table accessible équivalente (mêmes valeurs, tri clavier) et pied
 * méthode/version/limites. Module complémentaire : BreadthPanel (barres
 * linéaires ; jamais de jauge circulaire).
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
  if (data.data_state === 'partial') {
    return 'partial';
  }
  if (data.data_state === 'stale') {
    return 'stale';
  }
  return queryState;
}

function MarketsFrame({ data, state }: { readonly data: MarketsOverview; readonly state: DataState }) {
  const [visibleGroups, setVisibleGroups] = useState<ReadonlySet<SignGroup>>(
    new Set(ALL_GROUPS),
  );

  const allEntries = useMemo(() => flattenTickers(data.sectors), [data.sectors]);
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
    data.conclusion ?? 'Carte des marchés synthétiques : aucune conclusion serveur fournie.';

  const detail =
    state === 'partial'
      ? `Couverture incomplète publiée par le worker : ${coverage?.covered ?? '?'} instruments couverts sur ${coverage?.expected ?? '?'} attendus, ${coverage?.discarded ?? '?'} écartés.`
      : state === 'stale'
        ? 'Toutes les observations couvertes sont périmées (statut serveur STALE).'
        : undefined;

  return (
    <section className="vx-chartframe" aria-labelledby="vx-marketmap-title">
      {/* 1. WidgetHeader : question + titre */}
      <header className="vx-chartframe-head">
        <p className="vx-chartframe-question">
          Comment les secteurs et instruments suivis ont-ils évolué sur la dernière séance ?
        </p>
        <h2 id="vx-marketmap-title">Carte des marchés synthétiques</h2>
      </header>

      {/* 2. DataMeta : unité, devise, timezone, période, source, as_of, couverture */}
      <dl className="vx-chartframe-meta">
        <div>
          <dt>Unité</dt>
          <dd>rendement 1 jour en % (ratio serveur « {data.unit ?? '—'} »)</dd>
        </div>
        <div>
          <dt>Période</dt>
          <dd>2 clôtures journalières consécutives</dd>
        </div>
        <div>
          <dt>Timezone</dt>
          <dd>UTC (stockage) — horodatages affichés tels que publiés</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>
            <code>synthetic-dev</code> via snapshot worker v{data.snapshot_version ?? '—'}
          </dd>
        </div>
        <div>
          <dt>as_of</dt>
          <dd>{asOf === null ? '—' : <time dateTime={asOf}>{asOf}</time>}</dd>
        </div>
        <div>
          <dt>Couverture</dt>
          <dd>
            {coverage === null
              ? '—'
              : `${coverage.covered}/${coverage.expected} couverts, ${coverage.discarded} écartés, ${coverage.received} reçus`}
          </dd>
        </div>
      </dl>

      <SyntheticBanner population={data.population} />

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
        <MarketMap sectors={data.sectors} visibleGroups={visibleGroups} description={description} />

        {/* 5. WidgetConclusion : phrase factuelle serveur, verbatim */}
        <p className="vx-chartframe-conclusion" data-testid="markets-conclusion">
          {data.conclusion ?? 'Aucune conclusion publiée.'}
        </p>

        {/* Table accessible équivalente (mêmes valeurs, tri clavier). */}
        <MarketsTable entries={visibleEntries} />

        {/* Module complémentaire : breadth en barres linéaires. */}
        {data.breadth !== null ? <BreadthPanel breadth={data.breadth} /> : null}

        {coverage !== null && coverage.discarded_tickers.length > 0 ? (
          <section className="vx-markets-discards" aria-labelledby="vx-markets-discards-title">
            <h3 id="vx-markets-discards-title">
              Instruments écartés ({coverage.discarded})
            </h3>
            <ul>
              {coverage.discarded_tickers.map((entry) => (
                <li key={entry.ticker}>
                  <code>{entry.ticker}</code> — raison : <code>{entry.reason}</code> (jamais
                  interpolé)
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </DataStateBoundary>

      {/* 6. WidgetFooter : méthode/calcul, version, limites et hypothèses */}
      <footer className="vx-chartframe-foot">
        <p>
          Méthode : rendement 1 j <code>market.simple_return</code> et breadth{' '}
          <code>market.breadth</code> calculés par le worker (
          <code>{data.engine_version ?? 'version inconnue'}</code>, lignée{' '}
          <code>input_hash</code> conservée dans le snapshot). Poids = parts
          descriptives des clôtures (synthétiques). Rendu : Apache ECharts
          (licence Apache-2.0), chargé uniquement sur cette route.
        </p>
        <p>
          Limites : données SYNTHÉTIQUES de développement, 2 clôtures par
          instrument, breadth refusée sous le seuil de couverture ; un
          instrument sans ses 2 clôtures est écarté et compté.
        </p>
      </footer>
    </section>
  );
}

export function MarketsPage() {
  const overview = useMarketsOverview();
  const queryState = pageStateOf(overview);
  const data = overview.data;
  const state = frameStateOf(queryState, data);

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-markets">
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
        <MarketsFrame data={data} state={state} />
      ) : null}
    </article>
  );
}
