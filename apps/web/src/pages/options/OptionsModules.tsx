import { Link } from 'react-router-dom';

import type { OptionChainExpiration, OptionChainResponse } from '../../api/client.ts';
import { pageStateOf, useAnalysis, useMarketsOverview } from '../../api/hooks.ts';
import { Card } from '../../components/Card.tsx';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { Metric } from '../../components/Metric.tsx';
import { ModuleStatus } from '../../components/ModuleStatus.tsx';
import { Sparkline } from '../../components/markets/Sparkline.tsx';
import { flattenTickers, frDecimal } from '../../components/markets/marketsView.ts';
import { moduleShowsContent, moduleStateOf } from '../../components/moduleState.ts';
import { IvSmile } from '../../components/options/IvSmile.tsx';
import { InstrumentWidget } from '../InstrumentWidget.tsx';
import { analysisStateOf, barsViewOf } from '../analysis/analysisView.ts';
import { optionsModule } from './optionsModules.ts';
import { groupLabelOf, rowBudgetOf, sourceEventIdsOf, spotViewOf } from './optionsView.ts';

/**
 * Les modules SERVIS de la planche §5, hors la dominante (la chaîne). Le
 * snapshot de chaîne est déjà validé par la page (`data`) ; le sous-jacent
 * lit Marchés (variation 1 j) et son dossier d'analyse (série) par les hooks
 * des pages propriétaires, chacun avec son état. Aucun calcul : chaînes
 * serveur, comptes publiés, géométrie des points publiés.
 */

const SERIES_WINDOW = 60;
const VOLUME_WINDOW = 20;

function publie(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? 'non publié' : String(value);
}

function assumptionString(data: OptionChainResponse, key: string): string | null {
  const value = data.assumptions?.[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function assumptionInt(data: OptionChainResponse, key: string): number | null {
  const value = data.assumptions?.[key];
  return typeof value === 'number' && Number.isInteger(value) ? value : null;
}

// ---------------------------------------------------------------------------

export function UnderlyingModule({ underlying }: { readonly underlying: string }) {
  const module = optionsModule('underlying');
  const overview = useMarketsOverview();
  const state = moduleStateOf(pageStateOf(overview), overview.data);
  const entry = flattenTickers(overview.data?.sectors ?? []).find((candidate) => candidate.ticker.ticker === underlying) ?? null;
  if (moduleShowsContent(state) && entry !== null) {
    return <InstrumentWidget entry={entry} />;
  }
  return (
    <Card rank="quiet" kicker="Snapshot Marchés" title={module.title} titleId="vx-options-underlying-title">
      <ModuleStatus state={state} raw={state === 'closed' ? overview.data?.state : overview.data?.reason} />
      {moduleShowsContent(state) ? (
        <p className="vx-module-sentence" role="status">
          <code>{underlying}</code> n’est pas couvert par le snapshot Marchés : aucune clôture ni variation à afficher.{' '}
          <Link to={`/analysis/${encodeURIComponent(underlying)}`}>Ouvrir le dossier d’analyse</Link>
        </p>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function UnderlyingSeriesModule({ underlying }: { readonly underlying: string }) {
  const module = optionsModule('underlying-series');
  const query = useAnalysis(underlying);
  const state = analysisStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const bars = data === undefined ? null : barsViewOf(data);
  const shows = state === 'ready' || state === 'refreshing' || state === 'stale' || state === 'delayed' || state === 'partial';
  const lineBars = bars === null ? [] : bars.bars.slice(-SERIES_WINDOW);
  const volumeBars = bars === null ? [] : bars.bars.slice(-VOLUME_WINDOW);
  return (
    <Card
      rank="quiet"
      kicker="Dossier d’analyse"
      title={module.title}
      titleId="vx-options-series-title"
      {...(shows && data !== undefined
        ? {
            aside: <FreshnessBadge ageSeconds={data.age_seconds} sourceLabel="dossier" />,
            footer: (
              <>
                {lineBars.length} clôtures publiées{bars === null ? '' : ` · dernière ${publie(bars.lastClose)} ${publie(bars.currency)} (${publie(bars.lastTradingDay)})`} ·{' '}
                <Link to={`/analysis/${encodeURIComponent(underlying)}`}>voir Analyse</Link>
              </>
            ),
          }
        : {})}
    >
      {shows && bars !== null && lineBars.length > 0 ? (
        <div className="vx-iw-chart" data-testid="options-underlying-series">
          <Sparkline
            closes={lineBars.map((bar) => bar.close)}
            volumes={volumeBars.map((bar) => bar.volume)}
            sign="flat"
            label={`${lineBars.length} clôtures publiées de ${lineBars[0]?.tradingDay ?? ''} à ${lineBars[lineBars.length - 1]?.tradingDay ?? ''}`}
          />
        </div>
      ) : (
        <p className="vx-module-state" role="status" data-state={state === 'ready' || state === 'refreshing' ? 'empty' : state}>
          {state === 'loading'
            ? 'Chargement du dossier…'
            : state === 'empty'
              ? 'Aucun dossier d’analyse publié : aucune série à tracer.'
              : state === 'auth-required'
                ? 'Session requise pour lire le dossier.'
                : state === 'offline'
                  ? 'Dossier injoignable : aucune série à tracer.'
                  : state === 'error'
                    ? 'Réponse invalide : aucune série à tracer.'
                    : 'Dossier publié sans barre exploitable.'}
        </p>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function IdentityStripModule({ data }: { readonly data: OptionChainResponse }) {
  const module = optionsModule('identity-strip');
  const budget = rowBudgetOf(data);
  const sourceEventIds = sourceEventIdsOf(data);
  return (
    <Card
      rank="quiet"
      kicker="Références publiées"
      title={module.title}
      titleId="vx-options-identity-title"
      footer={
        <>
          quotes verbatim ; IV/Greeks <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span> ({data.value_nature ?? 'nature non publiée'})
        </>
      }
    >
      <dl className="vx-inspector-facts vx-options-facts">
        <div>
          <dt>Références d’observation</dt>
          <dd data-testid="chain-source-references">
            {sourceEventIds.length === 0 ? '—' : <code>{sourceEventIds.join(' · ')}</code>}
          </dd>
        </div>
        <div>
          <dt>Snapshot</dt>
          <dd>
            version {data.snapshot_version ?? '—'} · moteur <code>{data.engine_version ?? '—'}</code>
          </dd>
        </div>
        <div>
          <dt>as_of</dt>
          <dd>{data.as_of === null ? '—' : <time dateTime={data.as_of}>{data.as_of}</time>}</dd>
        </div>
        <div>
          <dt>Âge publié</dt>
          <dd>
            <FreshnessBadge ageSeconds={data.age_seconds} sourceLabel="âge publié par le serveur" />
          </dd>
        </div>
        <div>
          <dt>Couverture</dt>
          <dd>
            {data.coverage === null
              ? '—'
              : `${String(data.coverage['groups_published'] ?? '—')} groupe(s) publié(s) sur ${String(
                  data.coverage['observations_considered'] ?? '—',
                )} observation(s) considérée(s)`}
          </dd>
        </div>
        <div>
          <dt>Budget de lignes</dt>
          <dd data-testid="chain-row-budget">
            {budget === null
              ? '—'
              : `${budget.publishedRows ?? '—'} publiée(s) / ${budget.totalRows ?? '—'} construite(s), plafond ${budget.maxRows ?? '—'}, ${budget.truncatedRows ?? '—'} tronquée(s)`}
          </dd>
        </div>
        <div>
          <dt>Population</dt>
          <dd>
            <code>{publie(data.population)}</code>
          </dd>
        </div>
      </dl>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function SpotModule({ data }: { readonly data: OptionChainResponse }) {
  const module = optionsModule('spot');
  const spot = spotViewOf(data);
  return (
    <Card
      rank="quiet"
      kicker="Observé"
      title={module.title}
      titleId="vx-options-spot-title"
      footer={<>{spot === null || spot.observedAt === null ? 'instant d’observation non publié' : `observé ${spot.observedAt}`}</>}
    >
      <Metric
        label="Spot"
        value={spot === null || spot.value === null ? null : frDecimal(spot.value)}
        {...(spot?.currency === null || spot?.currency === undefined ? {} : { unit: spot.currency })}
        absentLabel="Spot non publié"
        testId="options-spot"
      />
    </Card>
  );
}

export function RateModule({ data }: { readonly data: OptionChainResponse }) {
  const module = optionsModule('rate');
  const rate = assumptionString(data, 'rate');
  const side = assumptionString(data, 'quote_side_for_iv');
  const maxAge = assumptionInt(data, 'max_quote_age_seconds');
  return (
    <Card
      rank="quiet"
      kicker="Hypothèse du calcul d’IV"
      title={module.title}
      titleId="vx-options-rate-title"
      footer={
        <>
          IV calculée sur le côté <code>{publie(side)}</code> · quote admise jusqu’à {maxAge === null ? 'un âge non publié' : `${maxAge} s`}
        </>
      }
    >
      <Metric label="Taux annualisé" value={rate === null ? null : frDecimal(rate)} note="décimal, hypothèse déclarée par le worker" testId="options-rate" />
    </Card>
  );
}

export function DividendModule({ data }: { readonly data: OptionChainResponse }) {
  const module = optionsModule('dividend');
  const dividend = assumptionString(data, 'dividend_yield');
  return (
    <Card rank="quiet" kicker="Hypothèse du calcul d’IV" title={module.title} titleId="vx-options-dividend-title" footer={<>aucun dividende observé n’est collecté ; ceci est l’hypothèse du calcul</>}>
      <Metric label="Rendement de dividende" value={dividend === null ? null : frDecimal(dividend)} note="décimal annualisé" testId="options-dividend" />
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function IvSmileModule({ group }: { readonly group: OptionChainExpiration | null }) {
  const module = optionsModule('iv-smile');
  return (
    <Card
      rank="quiet"
      kicker="IV publiées par contrat"
      title={module.title}
      titleId="vx-options-smile-title"
      footer={<>{group === null ? 'aucun groupe affiché' : `groupe ${groupLabelOf(group)}`} · géométrie des IV publiées, aucun point de référence choisi</>}
    >
      {group === null ? (
        <p className="vx-module-sentence" role="status">
          Aucun groupe publié : rien à tracer.
        </p>
      ) : (
        <IvSmile group={group} label={`Sourire d’IV du groupe ${groupLabelOf(group)} : IV THÉORIQUES publiées par strike, calls et puts`} />
      )}
    </Card>
  );
}

export function VolStructureModule({ groups }: { readonly groups: readonly OptionChainExpiration[] }) {
  const module = optionsModule('vol-structure');
  return (
    <Card
      rank="quiet"
      kicker="Petits multiples"
      title={module.title}
      titleId="vx-options-volstructure-title"
      footer={<>un sourire par groupe publié, jamais fusionnés ; aucune IV résumée par échéance</>}
    >
      {groups.length === 0 ? (
        <p className="vx-module-sentence" role="status">
          Aucun groupe publié.
        </p>
      ) : (
        <ul className="vx-smile-multiples" aria-label="Sourires d’IV par groupe publié" data-testid="options-vol-structure">
          {groups.map((group) => (
            <li key={`${group.expiration}::${group.trading_class}`}>
              <p className="vx-smile-multiple-title">
                <code>{group.expiration}</code> · {group.trading_class} · qualité {group.quality}
              </p>
              <IvSmile compact group={group} label={`Sourire d’IV ${groupLabelOf(group)}`} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
