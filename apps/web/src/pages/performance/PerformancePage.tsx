import { useState } from 'react';

import { isApiError } from '../../api/client.ts';
import { saveTextAsFile } from '../../app/downloadFile.ts';
import { getPerformanceExport, usePerformance, usePortfolio } from '../../api/portfolioApi.ts';
import type { PerformanceSnapshotResponse } from '../../api/client.ts';
import { pageStateOf } from '../../api/hooks.ts';
import type { PageDataState } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { MonthlyHeatmap } from './MonthlyHeatmap.tsx';
import { PerformanceChart } from './PerformanceChart.tsx';
import {
  METRIC_DEFINITIONS,
  METRIC_KEYS,
  METRIC_LABELS,
  performanceContentOf,
} from './performanceView.ts';
import type { MetricBlockView, MetricKey, PerformanceContentView } from './performanceView.ts';

/**
 * Page Performance — question : « Quelle performance ai-je réellement
 * enregistrée, avec quels risques et contributions ? »
 *
 * Tout vient du snapshot `performance/<id>` publié par le worker : série
 * quotidienne, TWR/XIRR/drawdown brut|net avec leur lignage de calcul,
 * heatmap mensuelle. Un statut INSUFFICIENT_DATA ou INVALID est affiché AVEC
 * SA RAISON à la place de toute valeur. Le bandeau de population
 * « SYNTHETIC_MARKS_REAL_LEDGER » n'est jamais masquable.
 */

export function performanceFrameStateOf(
  queryState: PageDataState,
  data: PerformanceSnapshotResponse | undefined,
): { readonly state: DataState | 'auth-required'; readonly view: PerformanceContentView | null } {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return { state: queryState, view: null };
  }
  if (data === undefined) {
    return { state: 'error', view: null };
  }
  if (data.state === 'empty') {
    return { state: 'empty', view: null };
  }
  const view = performanceContentOf(data.content);
  if (view === null) {
    return { state: 'error', view: null };
  }
  // Dégradation signalée PAR LE SERVEUR : jours exclus ou série insuffisante.
  if (view.seriesStatus !== 'OK' || view.excludedDays.length > 0) {
    return { state: 'partial', view };
  }
  return { state: queryState, view };
}

function metricValue(key: MetricKey, block: MetricBlockView): string | null {
  if (key === 'twr_gross' || key === 'twr_net') {
    return block.totalReturnPct !== null ? `${block.totalReturnPct} %` : null;
  }
  if (key === 'xirr_gross' || key === 'xirr_net') {
    return block.ratePct !== null ? `${block.ratePct} % / an` : null;
  }
  return block.maxDrawdownPct !== null ? `${block.maxDrawdownPct} %` : null;
}

function metricRawValue(key: MetricKey, block: MetricBlockView): string | null {
  if (key === 'twr_gross' || key === 'twr_net') {
    return block.totalReturn;
  }
  if (key === 'xirr_gross' || key === 'xirr_net') {
    return block.rate;
  }
  return block.maxDrawdown;
}

function MetricsBand({ view }: { readonly view: PerformanceContentView }) {
  const firstDay = view.points[0]?.tradingDay ?? null;
  const lastDay = view.points[view.points.length - 1]?.tradingDay ?? null;
  return (
    <section className="vx-perf-metrics" aria-labelledby="vx-perf-metrics-title">
      <h2 id="vx-perf-metrics-title">Métriques (jours ouvrables valorisés)</h2>
      <dl className="vx-perf-metrics-grid" data-testid="perf-metrics">
        {METRIC_KEYS.map((key) => {
          const block = view.metrics[key];
          const display = metricValue(key, block);
          const raw = metricRawValue(key, block);
          return (
            <div key={key} className="vx-perf-metric" data-testid={`perf-metric-${key}`}>
              <dt>{METRIC_LABELS[key]}</dt>
              <dd>
                {block.status === 'OK' && display !== null ? (
                  <>
                    <span className="vx-num vx-perf-metric-value" data-testid={`perf-metric-value-${key}`}>
                      {display}
                    </span>
                    {raw !== null ? (
                      <span className="vx-perf-metric-raw">
                        {' '}
                        (exact : <code className="vx-num">{raw}</code>)
                      </span>
                    ) : null}
                  </>
                ) : (
                  <span className="vx-perf-metric-blocked" data-testid={`perf-metric-status-${key}`}>
                    <code>{block.status}</code>
                    {block.reason !== null ? ` — raison : ${block.reason}` : ' — raison non fournie'}
                  </span>
                )}
                <p className="vx-perf-metric-def">{METRIC_DEFINITIONS[key]}</p>
                <p className="vx-perf-metric-meta">
                  Période :{' '}
                  {firstDay !== null && lastDay !== null ? (
                    <>
                      <time dateTime={firstDay}>{firstDay}</time> →{' '}
                      <time dateTime={lastDay}>{lastDay}</time>
                    </>
                  ) : (
                    'aucun jour valorisé'
                  )}
                  {' · '}méthode :{' '}
                  {block.calculation !== null ? (
                    <>
                      <code>{block.calculation.calculationId ?? '—'}</code> v
                      {block.calculation.engineVersion ?? '—'}
                    </>
                  ) : (
                    'aucun calcul publié'
                  )}
                </p>
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}

export function PerformancePage() {
  const portfolioQuery = usePortfolio();
  const portfolioId = portfolioQuery.data?.portfolio.id ?? null;
  const performanceQuery = usePerformance(portfolioId);
  const [exportState, setExportState] = useState<'idle' | 'pending' | 'failed' | 'not_found'>(
    'idle',
  );

  const portfolioState = pageStateOf(portfolioQuery);
  const queryState: PageDataState =
    portfolioId === null
      ? portfolioState === 'ready' || portfolioState === 'refreshing'
        ? 'error'
        : portfolioState
      : pageStateOf(performanceQuery);
  const frame = performanceFrameStateOf(queryState, performanceQuery.data);

  /**
   * UN téléchargement par clic, et c'est délibéré.
   *
   * Cette page émettait les deux fichiers depuis un seul bouton. La première
   * exécution des trois moteurs de rendu a mesuré que WebKit n'en délivrait
   * qu'UN — le CSV partait, le manifeste jamais. Différer la révocation de
   * l'URL objet et rendre la main entre les deux enregistrements n'y a rien
   * changé : la seconde exécution nocturne a reproduit exactement le même
   * échec. Ce qui EST mesuré comme fonctionnant partout, c'est un
   * téléchargement par geste utilisateur.
   *
   * Deux boutons suppriment donc la dépendance au multi-téléchargement au lieu
   * de tenter une troisième variante non vérifiable localement. Le contenu
   * exporté est inchangé : les deux fichiers restent ceux servis par l'API.
   */
  async function exportPart(id: number, part: 'csv' | 'manifest'): Promise<void> {
    setExportState('pending');
    try {
      const result = await getPerformanceExport(id);
      if (part === 'csv') {
        saveTextAsFile(result.csv, `vertex-performance-${id}.csv`, 'text/csv');
      } else {
        saveTextAsFile(
          JSON.stringify(result.manifest, null, 2),
          `vertex-performance-${id}-manifest.json`,
          'application/json',
        );
      }
      setExportState('idle');
    } catch (error) {
      if (isApiError(error) && error.status === 404) {
        setExportState('not_found');
        return;
      }
      setExportState('failed');
    }
  }

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-performance">
      <div className="vx-page-header">
        <h1 id="vx-page-title-performance">Performance</h1>
        <p className="vx-page-question">
          Quelle performance ai-je réellement enregistrée, avec quels risques et contributions ?
        </p>
      </div>

      {queryState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : frame.state === 'loading' || frame.state === 'offline' || (frame.state === 'error' && frame.view === null) ? (
        <DataStateBoundary
          state={frame.state}
          {...(frame.state === 'offline'
            ? { detail: "L'API locale est injoignable — aucune performance affichée." }
            : frame.state === 'error'
              ? { detail: "Snapshot absent ou illisible — rien n'est reconstruit à la place." }
              : {})}
        />
      ) : frame.state === 'empty' || frame.view === null ? (
        <DataStateBoundary
          state="empty"
          detail={
            performanceQuery.data?.reason !== null && performanceQuery.data?.reason !== undefined
              ? `Aucun snapshot de performance publié — raison serveur : ${performanceQuery.data.reason}`
              : 'Aucun snapshot de performance publié par le worker pour ce portefeuille.'
          }
        />
      ) : (
        <DataStateBoundary
          state={frame.state === 'auth-required' ? 'error' : frame.state}
          {...(frame.state === 'partial'
            ? {
                detail: `Couverture incomplète signalée par le serveur : série ${frame.view.seriesStatus}${frame.view.seriesReason !== null ? ` (${frame.view.seriesReason})` : ''}, ${frame.view.excludedDays.length} jour(s) exclu(s).`,
              }
            : {})}
          {...(frame.view.asOf !== null ? { asOfLabel: frame.view.asOf } : {})}
        >
          <p className="vx-perf-population" role="note" data-testid="perf-population">
            <strong>Population : {frame.view.population ?? '—'}</strong> — marques{' '}
            <code>{frame.view.populationMarks ?? '—'}</code> × journal{' '}
            <code>{frame.view.populationLedger ?? '—'}</code>. Marques synthétiques croisées avec le
            ledger réellement déclaré : aucune de ces courbes n'est une performance de marché réel.
          </p>

          {frame.view.seriesStatus !== 'OK' ? (
            <p className="vx-perf-metric-blocked" role="status" data-testid="perf-series-blocked">
              Série quotidienne : <code>{frame.view.seriesStatus}</code>
              {frame.view.seriesReason !== null ? ` — raison : ${frame.view.seriesReason}` : null}.
              Aucune courbe n'est tracée à la place.
            </p>
          ) : (
            <PerformanceChart
              points={frame.view.points}
              drawdown={frame.view.metrics.drawdown_gross}
              currency={frame.view.currency}
            />
          )}

          <MetricsBand view={frame.view} />

          <section className="vx-perf-heatmap-section" aria-labelledby="vx-perf-heatmap-title">
            <h2 id="vx-perf-heatmap-title">Rendements mensuels</h2>
            <MonthlyHeatmap heatmap={frame.view.heatmap} />
            {frame.view.heatmap.status === 'OK' ? (
              <div
                className="vx-pf-table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Rendements mensuels défilants"
              >
              <table className="vx-perf-months-table" aria-label="Table équivalente des rendements mensuels">
                <thead>
                  <tr>
                    <th scope="col">Mois</th>
                    <th scope="col">Rendement (%)</th>
                    <th scope="col">Périodes</th>
                    <th scope="col">Complet</th>
                    <th scope="col">Raisons d'incomplétude</th>
                  </tr>
                </thead>
                <tbody>
                  {frame.view.heatmap.months.map((month) => (
                    <tr key={month.month} data-testid={`perf-month-${month.month}`}>
                      <th scope="row">
                        <time dateTime={month.month}>{month.month}</time>
                      </th>
                      <td className="vx-num">{month.retPct}</td>
                      <td className="vx-num">{month.periods ?? '—'}</td>
                      <td>{month.complete ? 'oui' : 'NON — mois incomplet'}</td>
                      <td>
                        {month.incompleteReasons.length > 0 ? (
                          month.incompleteReasons.map((reason) => (
                            <code key={reason} className="vx-pf-import-error-code">
                              {reason}
                            </code>
                          ))
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            ) : null}
          </section>

          {frame.view.points.length > 0 ? (
            <section aria-labelledby="vx-perf-points-title">
              <h2 id="vx-perf-points-title">Points quotidiens (valeurs serveur exactes)</h2>
              <div className="vx-pf-table-scroll" tabIndex={0} role="region" aria-label="Points quotidiens défilants">
                <table className="vx-perf-points-table" aria-label="Série quotidienne de valorisation">
                  <thead>
                    <tr>
                      <th scope="col">Jour</th>
                      <th scope="col">Valeur brute</th>
                      <th scope="col">Valeur nette</th>
                      <th scope="col">Espèces</th>
                      <th scope="col">Positions</th>
                      <th scope="col">Frais cumulés</th>
                      <th scope="col">Lots valorisés</th>
                    </tr>
                  </thead>
                  <tbody>
                    {frame.view.points.map((point) => (
                      <tr key={point.tradingDay}>
                        <th scope="row">
                          <time dateTime={point.tradingDay}>{point.tradingDay}</time>
                        </th>
                        <td className="vx-num" data-testid={`perf-gross-${point.tradingDay}`}>
                          {point.grossValue}
                        </td>
                        <td className="vx-num">{point.netValue}</td>
                        <td className="vx-num">{point.cash ?? '—'}</td>
                        <td className="vx-num">{point.positionValue ?? '—'}</td>
                        <td className="vx-num">{point.feesCumulative ?? '—'}</td>
                        <td className="vx-num">{point.lotsValued ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {frame.view.excludedDays.length > 0 ? (
            <section aria-labelledby="vx-perf-excluded-title" data-testid="perf-excluded-days">
              <h2 id="vx-perf-excluded-title">
                Jours exclus de la série ({frame.view.excludedDays.length})
              </h2>
              <ul>
                {frame.view.excludedDays.map((day) => (
                  <li key={day.tradingDay}>
                    <time dateTime={day.tradingDay}>{day.tradingDay}</time> —{' '}
                    <code>{day.reason}</code> (jour écarté avec sa raison, jamais interpolé)
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="vx-perf-export" aria-labelledby="vx-perf-export-title">
            <h2 id="vx-perf-export-title">Export reproductible</h2>
            <p>
              CSV des points quotidiens et manifeste d'audit JSON (méthodes, versions, hashes) —
              fonction pure du snapshot publié : deux exports du même snapshot sont identiques
              octet pour octet. Les deux fichiers sont téléchargés séparément, un par action.
            </p>
            <button
              type="button"
              className="vx-markets-export"
              disabled={exportState === 'pending' || portfolioId === null}
              onClick={() => {
                if (portfolioId !== null) {
                  void exportPart(portfolioId, 'csv');
                }
              }}
            >
              Exporter les points (CSV servi par l'API)
            </button>
            <button
              type="button"
              className="vx-markets-export"
              disabled={exportState === 'pending' || portfolioId === null}
              onClick={() => {
                if (portfolioId !== null) {
                  void exportPart(portfolioId, 'manifest');
                }
              }}
            >
              Exporter le manifeste (JSON servi par l'API)
            </button>
            {exportState === 'failed' ? (
              <p role="alert" className="vx-pf-form-rejected">
                Export impossible — le serveur n'a pas répondu ; rien n'a été généré localement.
              </p>
            ) : exportState === 'not_found' ? (
              <p role="alert" className="vx-pf-form-rejected">
                Aucun snapshot à exporter (404 <code>NO_PERFORMANCE_SNAPSHOT</code>) — il n'existe
                rien d'honnête à exporter.
              </p>
            ) : null}
          </section>

          <section className="vx-perf-conventions" aria-labelledby="vx-perf-conventions-title">
            <h2 id="vx-perf-conventions-title">Conventions du calcul (serveur)</h2>
            <dl className="vx-perf-conventions-list">
              {Object.entries(frame.view.conventions).map(([key, value]) => (
                <div key={key}>
                  <dt>
                    <code>{key}</code>
                  </dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <p className="vx-perf-metric-meta">
              Couverture : {frame.view.coverage.daysValued ?? '—'} jour(s) valorisé(s) /{' '}
              {frame.view.coverage.daysWithClose ?? '—'} jour(s) de clôture (ratio{' '}
              <code className="vx-num">{frame.view.coverage.coverageRatio ?? '—'}</code>) ·{' '}
              {frame.view.coverage.externalCashflows ?? '—'} flux externe(s) · méthode de lots{' '}
              <code>{frame.view.lotMethod ?? '—'}</code> · moteur{' '}
              <code>{frame.view.engineVersion ?? '—'}</code>
            </p>
          </section>
        </DataStateBoundary>
      )}
    </article>
  );
}
