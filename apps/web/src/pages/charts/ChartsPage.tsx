import { Link, useParams } from 'react-router-dom';

import type { AnalysisResponse } from '../../api/client.ts';
import { pageStateOf, useAnalysis } from '../../api/hooks.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { IndicatorsPanel, OhlcvTable } from '../analysis/AnalysisPage.tsx';
import { CandleChart } from '../analysis/CandleChart.tsx';
import type { BarsView } from '../analysis/analysisView.ts';
import { analysisStateOf, barsViewOf } from '../analysis/analysisView.ts';
import { RebasedComparison } from './RebasedComparison.tsx';
import { useDeclaredInstruments } from '../devUniverse.ts';
import { absentModules, comparisonViewOf } from './chartsView.ts';

/**
 * Page Graphiques (`TL / 08`) — question : « Quelles relations puis-je
 * explorer sans perdre méthode et contexte ? » (`references/pages.md` §8).
 *
 * LOT-A2, 2026-09-02. La planche `pages-07-08-portfolio-charts.png` (moitié
 * droite) montre douze modules. Trois sont SERVIS par le contrat Analyse
 * (`GET /api/v1/analysis/{instrument}`) : l'espace graphique, son volume et
 * les indicateurs publiés par le moteur serveur. Les neuf autres n'ont AUCUNE
 * source dans ce dépôt ; ils sont rendus à leur place, à leur géométrie, avec
 * le motif exact de leur absence (`AbsentModule`, vocabulaire fermé) — jamais
 * une valeur, jamais un rectangle muet, jamais une promesse (article 17).
 *
 * UN SEUL PROPRIÉTAIRE DE DONNÉE. Cette page lit le MÊME DTO, par le MÊME
 * client, et le rend par le MÊME composant (`CandleChart`) que `/analysis`.
 * Le propriétaire est le contrat ; la page ne recalcule rien : aucun overlay,
 * aucun indicateur, aucun rebasage, aucune comparaison côté navigateur
 * (`.claude/rules/frontend.md`). LOT-S2 : la comparaison base 100 est
 * désormais SERVIE — le worker rebase les deux séries et intersecte leurs
 * calendriers, la page affiche ce qu'il publie. Ce que `/analysis` porte en
 * propre — verdict,
 * gates, preuves, scénarios, explication — n'est PAS repris ici : ce n'est pas
 * la question de cette page.
 */

function ChartsInstrumentPicker({ current }: { readonly current: string | null }) {
  const instruments = useDeclaredInstruments();
  if (instruments.length === 0) {
    return (
      <nav className="vx-underlying-picker" aria-label="Instruments disponibles">
        <span className="vx-underlying-picker-label">Instrument :</span>
        <span className="vx-underlying-empty">
          Aucun instrument publié — la page Marchés n&apos;en couvre encore aucun.
        </span>
      </nav>
    );
  }
  return (
    <nav className="vx-underlying-picker" aria-label="Instruments disponibles">
      <span className="vx-underlying-picker-label">Instrument :</span>
      {instruments.map((candidate) => (
        <Link
          key={candidate}
          to={`/charts/${candidate}`}
          className="vx-underlying-link"
          aria-current={candidate === current ? 'page' : undefined}
        >
          {candidate}
        </Link>
      ))}
    </nav>
  );
}

/** Une valeur absente est DITE absente — jamais un tiret ambigu. */
function publie(valeur: string | number | null | undefined): string {
  if (valeur === null || valeur === undefined || valeur === '') {
    return 'non publié';
  }
  return String(valeur);
}

function ChartsFrame({
  data,
  bars,
  state,
  instrument,
}: {
  readonly data: AnalysisResponse;
  readonly bars: BarsView | null;
  readonly state: DataState;
  readonly instrument: string;
}) {
  const currency = bars?.currency ?? 'devise non publiée';
  const asOf = data.as_of ?? null;
  const detail =
    state === 'stale'
      ? `Snapshot publié périmé par le relais (âge publié ${publie(data.age_seconds)} s) : la série reste affichée, mais ne décrit pas le marché à cet instant.`
      : state === 'partial'
        ? 'Série publiée avec des barres écartées par le worker : la couverture ci-dessus dit lesquelles.'
        : state === 'delayed'
          ? 'Population DELAYED publiée par le worker : la série est conservée, mais ne décrit pas le marché à cet instant.'
          : undefined;

  const description =
    bars !== null && bars.status === 'OK'
      ? `${publie(bars.count ?? bars.bars.length)} barres journalières publiées de ${publie(bars.firstTradingDay)} à ${publie(bars.lastTradingDay)}, dernière clôture ${publie(bars.lastClose)} ${currency}.`
      : 'Aucune série de barres exploitable publiée.';

  return (
    <section
      className="vx-chartframe"
      data-rank="dominant"
      data-module="main-chart"
      aria-labelledby="vx-charts-title"
    >
      <header className="vx-chartframe-head">
        <p className="vx-chartframe-question">
          Quelles relations puis-je explorer sans perdre méthode et contexte ?
        </p>
        <h2 id="vx-charts-title">Graphiques — {instrument}</h2>
      </header>

      <dl className="vx-chartframe-meta">
        <div>
          <dt>Unité</dt>
          <dd>prix OHLC en {currency} ; volume en titres (entiers serveur)</dd>
        </div>
        <div data-module="volume">
          <dt>Volume</dt>
          <dd>histogramme sous les chandeliers, publié barre à barre par le worker</dd>
        </div>
        <div>
          <dt>Timezone</dt>
          <dd>UTC (stockage) — jours de bourse affichés tels que publiés</dd>
        </div>
        <div>
          <dt>as_of</dt>
          <dd>{asOf === null ? 'non publié' : <time dateTime={asOf}>{asOf}</time>}</dd>
        </div>
        <div>
          <dt>Couverture</dt>
          <dd>
            {bars === null
              ? 'aucune série publiée'
              : `${publie(bars.count)} barre(s) valides (${publie(bars.firstTradingDay)} → ${publie(bars.lastTradingDay)}), ${bars.discardedCount} écartée(s), base ${publie(bars.adjustmentBasis)}`}
          </dd>
        </div>
      </dl>

      <SyntheticBanner population={data.population} />

      <DataStateBoundary
        state={state}
        {...(detail !== undefined ? { detail } : {})}
        {...(asOf !== null ? { asOfLabel: `as_of ${asOf}` } : {})}
      >
        {bars !== null && bars.bars.length > 0 ? (
          <>
            <CandleChart bars={bars.bars} description={description} />
            <OhlcvTable bars={bars} currency={currency} />
          </>
        ) : (
          <p role="status">Aucune barre exploitable à dessiner — rien n&apos;est inventé à la place.</p>
        )}
      </DataStateBoundary>

      <footer className="vx-chartframe-foot">
        <p>
          Méthode : barres OHLCV validées barre à barre par le worker (une barre invalide est
          écartée avec sa raison, jamais réparée), relayées telles quelles. Rendu : Lightweight
          Charts™ —{' '}
          <a href="https://www.tradingview.com/" rel="noopener noreferrer" target="_blank">
            TradingView
          </a>{' '}
          (Apache-2.0, version épinglée), chargé uniquement sur cette route.
        </p>
        <p>
          Limites : population <code>{publie(data.population)}</code> déclarée par le worker ;
          aucun overlay, indicateur, rebasage ni comparaison n&apos;est calculé dans le navigateur —
          ce qui n&apos;est pas publié est déclaré absent ci-dessous, avec son motif.
        </p>
      </footer>
    </section>
  );
}

/**
 * Inspecteur — la DÉFINITION de la série servie : instrument, unités, source,
 * fraîcheur, version et exclusions (`references/pages.md` §8). Rien d'autre :
 * thèse, verdict et explication appartiennent à `/analysis`.
 */
function SeriesInspector({
  data,
  bars,
  instrument,
}: {
  readonly data: AnalysisResponse;
  readonly bars: BarsView | null;
  readonly instrument: string;
}) {
  return (
    <InspectorPanel subject={instrument}>
      <dl className="vx-inspector-facts" data-testid="charts-series-definition">
        <div>
          <dt>Série</dt>
          <dd>clôtures journalières OHLCV de {instrument}</dd>
        </div>
        <div>
          <dt>Devise</dt>
          <dd>{publie(bars?.currency)}</dd>
        </div>
        <div>
          <dt>Base d&apos;ajustement</dt>
          <dd>{publie(bars?.adjustmentBasis)}</dd>
        </div>
        <div>
          <dt>Qualité publiée</dt>
          <dd>{publie(bars?.quality)}</dd>
        </div>
        <div>
          <dt>Fraîcheur</dt>
          <dd>
            as_of {publie(data.as_of)} · âge publié {publie(data.age_seconds)} s · fresh{' '}
            {bars?.fresh === null || bars?.fresh === undefined ? 'non publié' : String(bars.fresh)}
          </dd>
        </div>
        <div>
          <dt>Référence d&apos;observation</dt>
          <dd>
            <code>{publie(bars?.sourceEventId)}</code>
          </dd>
        </div>
        <div>
          <dt>Snapshot · moteur</dt>
          <dd>
            v{publie(data.snapshot_version)} · <code>{publie(data.engine_version)}</code>
          </dd>
        </div>
        <div>
          <dt>Exclusions</dt>
          <dd>
            {bars === null
              ? 'aucune série publiée'
              : `${bars.discardedCount} barre(s) écartée(s) par le worker, avec raison`}
          </dd>
        </div>
      </dl>
    </InspectorPanel>
  );
}

/** Les neuf modules de la planche sans source : présents, à leur place, motivés. */
function AbsentModulesGrid() {
  return (
    <section className="vx-charts-modules" aria-label="Modules de la planche sans source publiée">
      {absentModules().map((module) => (
        <div key={module.id} data-module={module.id}>
          <AbsentModule
            title={module.title}
            question={module.question}
            reason={module.status.reason}
            note={module.status.note}
          />
        </div>
      ))}
    </section>
  );
}

function ChartsRoute({ instrument }: { readonly instrument: string }) {
  const analysis = useAnalysis(instrument);
  const queryState = pageStateOf(analysis);
  const data = analysis.data;
  const state = analysisStateOf(queryState, data);

  return (
    <>
      <ChartsInstrumentPicker current={instrument} />

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={`Aucun dossier publié pour « ${instrument} » — raison serveur : ${
            data?.reason ?? 'non fournie'
          }. Rien n'est inventé à la place.`}
        />
      ) : state === 'loading' || state === 'offline' || state === 'error' ? (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? { detail: "L'API locale est injoignable — la série ne peut pas être affichée." }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucune série affichée." }
              : {})}
        />
      ) : data !== undefined ? (
        <>
          <ChartsFrame
            key={instrument}
            data={data}
            bars={barsViewOf(data)}
            state={state}
            instrument={instrument}
          />

          <div data-module="comparison">
            <RebasedComparison
              comparison={comparisonViewOf(data.indicators)}
              instrument={instrument}
            />
          </div>

          <div data-module="served-indicators">
            {data.indicators === null || data.indicators === undefined ? (
              <p role="status">Aucun indicateur publié par le moteur serveur pour cette série.</p>
            ) : (
              <IndicatorsPanel
                indicators={data.indicators}
                currency={typeof data.bars?.currency === 'string' ? data.bars.currency : ''}
              />
            )}
          </div>

          <AbsentModulesGrid />

          <SeriesInspector data={data} bars={barsViewOf(data)} instrument={instrument} />
        </>
      ) : null}
    </>
  );
}

export function ChartsPage() {
  const { instrument } = useParams<{ instrument?: string }>();

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-charts">
      <div className="vx-page-header">
        <h1 id="vx-page-title-charts">Graphiques</h1>
        <p className="vx-page-question">
          Quelles relations puis-je explorer sans perdre méthode et contexte ?
        </p>
      </div>

      {instrument === undefined || instrument === '' ? (
        <>
          <ChartsInstrumentPicker current={null} />
          <DataStateBoundary
            state="empty"
            detail="Aucun instrument sélectionné — en choisir un ci-dessus. Aucun instrument n'est ouvert par défaut."
          />
          <AbsentModulesGrid />
        </>
      ) : (
        <ChartsRoute instrument={instrument} />
      )}
    </article>
  );
}
