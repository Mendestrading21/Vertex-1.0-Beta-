import { Link } from 'react-router-dom';

import { useOpportunities } from '../../api/decisionApi.ts';
import { pageStateOf, useAnalysis, useMarketsOverview } from '../../api/hooks.ts';
import { analysisStateOf, barsViewOf } from '../../pages/analysis/analysisView.ts';
import { focusInstrumentsOf } from '../../pages/focusView.ts';
import { opportunitiesFrameStateOf } from '../../pages/opportunities/opportunitiesView.ts';
import { FreshnessBadge } from '../FreshnessBadge.tsx';
import { Sparkline } from '../markets/Sparkline.tsx';
import type { FlatTicker } from '../markets/marketsView.ts';
import { GROUP_LABELS_FR, frDecimal, signSymbolOf } from '../markets/marketsView.ts';
import { MODULE_STATE_LABELS, moduleStateOf } from '../moduleState.ts';
import { StatusChip } from './StatusChip.tsx';

/**
 * Tuile d'instrument — prix en grand, variation en pastille, mini-courbe des
 * clôtures et barres de volume, fraîcheur en haut à droite.
 *
 * DÉPLACÉE depuis `pages/InstrumentWidget.tsx` (lot L0) : c'est une primitive
 * partagée par Aujourd'hui, Marchés et Options, pas une pièce d'une page. Le
 * balayage des gardes la suit — `no-fabricated-values.test.ts` couvre
 * désormais `src/components/widgets` en plus de `src/pages`, un déplacement ne
 * sort jamais un fichier du périmètre des portes.
 *
 * TOUT est servi : la dernière clôture, la clôture PRÉCÉDENTE et son jour de
 * séance, la qualité déclarée, le rendement 1 j viennent du snapshot Marchés
 * (chaînes verbatim) ; la série vient du dossier d'analyse de l'instrument,
 * avec son propre état et sa propre fraîcheur. La tuile ne calcule rien : le
 * sens de la pastille est le SIGNE de la chaîne publiée, la courbe n'est que la
 * géométrie des clôtures publiées.
 *
 * Sans dossier, le cadre de la courbe DIT ce qui manque — il ne montre ni une
 * courbe plate, ni un exemple.
 */

const LINE_WINDOW = 30;
const VOLUME_WINDOW = 14;

export function InstrumentTile({ entry }: { readonly entry: FlatTicker }) {
  const ticker = entry.ticker;
  const query = useAnalysis(ticker.ticker);
  const state = analysisStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const bars = data === undefined ? null : barsViewOf(data);
  const showsSeries =
    (state === 'ready' || state === 'refreshing' || state === 'stale' || state === 'delayed' || state === 'partial') &&
    bars !== null &&
    bars.bars.length > 0;
  const lineBars = bars === null ? [] : bars.bars.slice(-LINE_WINDOW);
  const volumeBars = bars === null ? [] : bars.bars.slice(-VOLUME_WINDOW);
  const previousClose = ticker.previous_close.trim();
  const previousDay = ticker.previous_trading_day.trim();
  const quality = ticker.quality.trim();

  return (
    <article className="vx-iw vx-w2-tile" data-sign={entry.group} data-testid="instrument-widget">
      <header className="vx-iw-head">
        <div className="vx-iw-identity">
          <Link to={`/analysis/${ticker.ticker}`} className="vx-iw-ticker">
            <code>{ticker.ticker}</code>
          </Link>
          <span className="vx-iw-sector">{entry.sectorLabel}</span>
        </div>
        <div className="vx-iw-fresh">
          {data !== undefined && (state === 'ready' || state === 'refreshing' || state === 'stale' || state === 'delayed' || state === 'partial') ? (
            <FreshnessBadge ageSeconds={data.age_seconds} sourceLabel="dossier" />
          ) : (
            <span className="vx-iw-state" data-state={state}>
              {state === 'ready' || state === 'refreshing' ? '' : MODULE_STATE_LABELS[state]}
            </span>
          )}
        </div>
      </header>

      <div className="vx-iw-price-row">
        <span className="vx-iw-price">
          {frDecimal(ticker.last_close)}
          <span className="vx-iw-currency"> {ticker.currency ?? 'devise non publiée'}</span>
        </span>
        <span className="vx-iw-delta" data-sign={entry.group}>
          <span aria-hidden="true">{signSymbolOf(entry.group)}</span> {frDecimal(ticker.return_1d_pct)} %
          <span className="vx-visually-hidden"> ({GROUP_LABELS_FR[entry.group]}, rendement 1 j)</span>
        </span>
      </div>

      {/* Faits SERVIS que le contrat publiait déjà sans être affichés
          (`MarketsTicker.previous_close`, `previous_trading_day`, `quality`). */}
      <p className="vx-w2-tile-facts" data-testid="instrument-tile-facts">
        <span>
          clôture précédente{' '}
          {previousClose === '' ? (
            <span data-absent="true">non publiée</span>
          ) : (
            frDecimal(previousClose)
          )}
        </span>
        <span>
          {previousDay === '' ? <span data-absent="true">séance non publiée</span> : previousDay}
        </span>
        <StatusChip
          label={quality === '' ? '' : quality}
          tone={quality === 'OK' ? 'neutral' : 'warning'}
        />
      </p>

      <div className="vx-iw-chart" data-testid="instrument-widget-chart">
        {showsSeries && bars !== null ? (
          <Sparkline
            closes={lineBars.map((bar) => bar.close)}
            volumes={volumeBars.map((bar) => bar.volume)}
            sign={entry.group}
            label={`${lineBars.length} clôtures publiées de ${lineBars[0]?.tradingDay ?? ''} à ${
              lineBars[lineBars.length - 1]?.tradingDay ?? ''
            }, première ${lineBars[0]?.close ?? ''}, dernière ${lineBars[lineBars.length - 1]?.close ?? ''} ${
              bars.currency ?? ''
            }`}
          />
        ) : (
          <p className="vx-iw-absent" role="status">
            {state === 'loading'
              ? 'Chargement du dossier…'
              : state === 'empty'
                ? 'Aucun dossier d’analyse publié : aucune série à tracer.'
                : state === 'auth-required'
                  ? 'Session requise pour lire le dossier.'
                  : state === 'offline'
                    ? 'Dossier injoignable : aucune série à tracer.'
                    : bars !== null && bars.bars.length === 0
                      ? 'Dossier publié sans barre exploitable.'
                      : 'Réponse invalide : aucune série à tracer.'}
          </p>
        )}
      </div>

      <footer className="vx-iw-foot">
        clôture {ticker.trading_day}
        {showsSeries ? ` · ${lineBars.length} séances tracées` : ''}
        {state === 'stale' ? ' · dossier périmé' : state === 'delayed' ? ' · différé' : ''}
      </footer>
    </article>
  );
}

/**
 * La rangée des instruments suivis, partagée par Aujourd'hui et Marchés. Elle
 * lit deux snapshots existants et n'ouvre qu'un nombre BORNÉ de dossiers.
 */
export function FocusRowModule() {
  const opportunities = useOpportunities();
  const overview = useMarketsOverview();
  const frame = opportunitiesFrameStateOf(pageStateOf(opportunities), opportunities.data);
  const overviewState = moduleStateOf(pageStateOf(overview), overview.data);
  const entries = focusInstrumentsOf(frame.view, overview.data?.sectors ?? []);

  return (
    <section className="vx-focus" aria-labelledby="vx-focus-title" data-testid="focus-row">
      <header className="vx-focus-head">
        <p className="vx-focus-kicker">Instruments suivis</p>
        <h2 id="vx-focus-title" className="vx-visually-hidden">
          Instruments suivis — dossiers d’analyse publiés
        </h2>
        <p className="vx-focus-note">
          les premiers candidats de l’ordre publié dont un dossier d’analyse existe · clôture et
          rendement 1 j du snapshot Marchés · série du dossier
        </p>
      </header>
      {entries.length === 0 ? (
        <p className="vx-module-state" role="status" data-state={frame.state === 'ready' ? 'empty' : frame.state}>
          {frame.state === 'loading' || overviewState === 'loading'
            ? MODULE_STATE_LABELS.loading
            : frame.state !== 'ready' && frame.state !== 'refreshing'
              ? MODULE_STATE_LABELS[frame.state]
              : overviewState !== 'ready' && overviewState !== 'refreshing'
                ? MODULE_STATE_LABELS[overviewState]
                : 'Aucun dossier d’analyse publié : aucun instrument suivi à afficher.'}
        </p>
      ) : (
        <div className="vx-focus-grid">
          {entries.map((entry) => (
            <InstrumentTile key={entry.ticker.ticker} entry={entry} />
          ))}
        </div>
      )}
    </section>
  );
}
