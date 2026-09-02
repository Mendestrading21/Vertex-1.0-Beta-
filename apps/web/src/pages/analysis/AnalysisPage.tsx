import { Link, useParams } from 'react-router-dom';

import type { AnalysisResponse } from '../../api/client.ts';
import { pageStateOf, useAnalysis } from '../../api/hooks.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { AiExplanationPanel } from '../../components/ai/AiExplanationPanel.tsx';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { Card } from '../../components/Card.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { useDeclaredInstruments } from '../devUniverse.ts';
import { AdviceCard } from './AdviceCard.tsx';
import { DossierInspector } from './AnalysisInspector.tsx';
import {
  CatalystsModule,
  FinancialsModule,
  IdentityModule,
  InstrumentHeaderModule,
  KeyRisksModule,
  PeersModule,
} from './AnalysisModules.tsx';
import { CandleChart } from './CandleChart.tsx';
import { EvidenceRail } from './EvidenceRail.tsx';
import { IndicatorsPanel } from './IndicatorsPanel.tsx';
import { OhlcvTable } from './OhlcvTable.tsx';
import { ScenarioPanel } from './ScenarioPanel.tsx';
import { analysisModule } from './analysisModules.ts';
import type { BarsView } from './analysisView.ts';
import { adviceViewOf, analysisStateOf, barsViewOf, evidenceViewOf, scenariosViewOf } from './analysisView.ts';

/**
 * LOT-A4 : la table OHLCV et les indicateurs vivent dans leurs propres
 * fichiers ; ce ré-export conserve le point d'entrée de la page Graphiques
 * (PR #25), qui les importe d'ici.
 */
export { IndicatorsPanel, OhlcvTable };

/**
 * Page Analyse (`TL / 04`) — question : « Que disent les données certifiées
 * sur cet instrument, et quelles limites restent ouvertes ? »
 *
 * LOT-A4 — LA PLANCHE §4 EN ENTIER. `pages-03-04-opportunities-analysis.png`
 * (moitié droite) compose dix-neuf modules autour d'une dominante : les
 * chandeliers et le volume (Lightweight Charts™, chunk paresseux, attribution
 * TradingView visible, table OHLCV ÉQUIVALENTE). Onze modules sont SERVIS —
 * l'en-tête instrument (clôture, variation 1 j du snapshot Marchés,
 * mini-série), l'identité, les indicateurs, les faits officiels SEC (relais
 * verbatim de la route déjà typée), le verdict, les scénarios, les
 * catalyseurs de l'instrument (agenda publié), les risques déclarés, les
 * pairs du secteur, l'evidence — et huit n'ont ni source ni contrat :
 * oscillateurs, régime, qualité fondamentale, valorisation, confiance du
 * modèle, révisions d'analystes, niveaux, contradictions. Ils tiennent leur
 * place avec le motif mesuré de leur absence (article 17).
 *
 * L'INSPECTEUR PORTE LE DOSSIER OUVERT (version, instant, âge, population,
 * référence, couverture, fraîcheur, limites) ; l'explication IA (LOT-12)
 * reste un second panneau. Aucun calcul financier ici.
 */

function InstrumentPicker({ current }: { readonly current: string | null }) {
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
          to={`/analysis/${candidate}`}
          className="vx-underlying-link"
          aria-current={candidate === current ? 'page' : undefined}
        >
          {candidate}
        </Link>
      ))}
    </nav>
  );
}

function AbsentAnalysisModule({ id }: { readonly id: string }) {
  const module = analysisModule(id);
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

function AnalysisFrame({
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
  const asOf = data.as_of;
  const currency = bars?.currency ?? '—';
  const population = data.population ?? 'NON_DÉCLARÉE';

  const detail =
    state === 'partial'
      ? bars === null || bars.status !== 'OK'
        ? 'Dossier publié sans série de barres exploitable.'
        : `Série publiée avec dégradation : qualité ${bars.quality ?? '—'}, ${bars.discardedCount} barre(s) écartée(s) par le worker.`
      : state === 'stale'
        ? data.state === 'stale'
          ? `Dossier publié périmé par le relais : ${data.reason ?? 'raison non publiée'} ; âge publié ${data.age_seconds ?? '—'} s.`
          : `Le worker a publié la série comme non fraîche (fresh = false) ; âge publié ${data.age_seconds ?? '—'} s.`
        : state === 'delayed'
          ? 'Population DELAYED publiée par le worker : le dossier est conservé, mais ne décrit pas le marché à cet instant.'
          : undefined;

  const description =
    bars !== null && bars.status === 'OK'
      ? `${bars.count ?? bars.bars.length} barres journalières publiées de ${bars.firstTradingDay ?? '?'} à ${bars.lastTradingDay ?? '?'}, dernière clôture ${bars.lastClose ?? '?'} ${currency}.`
      : 'Aucune série de barres exploitable publiée.';

  return (
    <section
      className="vx-chartframe"
      data-rank="dominant"
      data-module="chart"
      aria-labelledby="vx-analysis-title"
    >
      <header className="vx-chartframe-head">
        <p className="vx-chartframe-question">
          Que disent les données certifiées sur cet instrument, et quelles limites restent ouvertes ?
        </p>
        <h2 id="vx-analysis-title">Analyse — {instrument}</h2>
      </header>

      <dl className="vx-chartframe-meta">
        <div>
          <dt>Unité</dt>
          <dd>prix OHLC en {currency} ; volume en titres (entiers serveur)</dd>
        </div>
        <div>
          <dt>Devise</dt>
          <dd>{currency}</dd>
        </div>
        <div>
          <dt>Timezone</dt>
          <dd>UTC (stockage) — jours de bourse affichés tels que publiés</dd>
        </div>
        <div>
          <dt>Référence d’observation publiée</dt>
          <dd>
            <code>{bars?.sourceEventId ?? '—'}</code> via snapshot worker v
            {data.snapshot_version ?? '—'} (moteur <code>{data.engine_version ?? '—'}</code>)
          </dd>
        </div>
        <div>
          <dt>as_of</dt>
          <dd>{asOf === null ? '—' : <time dateTime={asOf}>{asOf}</time>}</dd>
        </div>
        <div>
          <dt>Couverture</dt>
          <dd>
            {bars === null
              ? '—'
              : `${bars.count ?? 0} barre(s) valides (${bars.firstTradingDay ?? '—'} → ${bars.lastTradingDay ?? '—'}), ${bars.discardedCount} écartée(s), base ${bars.adjustmentBasis ?? '—'}`}
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
            <p className="vx-chartframe-conclusion" data-testid="analysis-conclusion">
              {/* Conclusion si fournie : le dossier n'en publie pas — dit tel quel. */}
              Aucune conclusion serveur publiée pour ce dossier — les faits d'explication du
              verdict analytique sont les seuls énoncés certifiés.
            </p>
            <OhlcvTable bars={bars} currency={currency} />
          </>
        ) : (
          <p role="status">Aucune barre exploitable à dessiner — rien n'est inventé à la place.</p>
        )}
      </DataStateBoundary>

      <footer className="vx-chartframe-foot">
        <p>
          Méthode : barres OHLCV validées barre à barre par le worker (une barre invalide est
          écartée avec sa raison, jamais réparée) ; verdict par l'unique <code>AdviceEngine</code>{' '}
          (<code>{data.engine_version ?? '—'}</code>) ; clusters par la fusion déterministe. Rendu :
          Lightweight Charts™ —{' '}
          <a href="https://www.tradingview.com/" rel="noopener noreferrer" target="_blank">
            TradingView
          </a>{' '}
          (Apache-2.0, version épinglée), chargé uniquement sur cette route.
        </p>
        <p>
          Limites : population <code>{population}</code> déclarée par le worker ; les gates non
          évaluables restent BLOCK <code>UNEVALUABLE</code> (fail-closed) et le statut publié est
          affiché tel quel.
        </p>
      </footer>
    </section>
  );
}

function AnalysisBoard({
  data,
  state,
  instrument,
}: {
  readonly data: AnalysisResponse;
  readonly state: DataState;
  readonly instrument: string;
}) {
  const bars = barsViewOf(data);
  const advice = adviceViewOf(data);
  const evidence = evidenceViewOf(data);
  const scenarios = scenariosViewOf(data);
  const currency = typeof data.bars?.currency === 'string' ? data.bars.currency : '';
  const indicatorsModule = analysisModule('indicators');

  return (
    <>
      <div className="vx-analysis-grid vx-board" data-testid="analysis-grid">
        <div data-module="instrument-header">
          <InstrumentHeaderModule instrument={instrument} data={data} bars={bars} />
        </div>
        <div data-module="identity-facts">
          <IdentityModule instrument={instrument} data={data} bars={bars} />
        </div>

        <AnalysisFrame data={data} bars={bars} state={state} instrument={instrument} />

        <div data-module="indicators">
          {data.indicators === null || data.indicators === undefined ? (
            <Card rank="quiet" kicker="Registre des calculs" title={indicatorsModule.title} titleId="vx-indicators-title">
              <p className="vx-module-sentence" role="status">
                Aucun indicateur publié dans ce dossier — rien n&apos;est calculé à la place.
              </p>
            </Card>
          ) : (
            <IndicatorsPanel indicators={data.indicators} currency={currency} />
          )}
        </div>
        <AbsentAnalysisModule id="oscillators" />
        <AbsentAnalysisModule id="analyst-revisions" />

        <div data-module="verdict">
          <Card
            rank="quiet"
            kicker="AdviceEngine, autorité unique"
            title={analysisModule('verdict').title}
            titleId="vx-analysis-verdict-title"
            footer={<>statut et direction distincts, relayés tels quels ; gates fail-closed</>}
          >
            <AdviceCard advice={advice} />
          </Card>
        </div>
        <div data-module="financials">
          <FinancialsModule instrument={instrument} />
        </div>

        <div data-module="scenarios">
          <Card
            rank="quiet"
            kicker="Repricés par le worker"
            title={analysisModule('scenarios').title}
            titleId="vx-analysis-scenarios-title"
            footer={<>grille THÉORIQUE ou absence typée — jamais une valeur de marché</>}
          >
            <ScenarioPanel scenarios={scenarios} />
          </Card>
        </div>
        <div data-module="upcoming-catalysts">
          <CatalystsModule instrument={instrument} />
        </div>
        <div data-module="key-risks">
          <KeyRisksModule advice={advice} />
        </div>

        <AbsentAnalysisModule id="regime" />
        <AbsentAnalysisModule id="fundamental-quality" />
        <AbsentAnalysisModule id="valuation" />
        <AbsentAnalysisModule id="model-confidence" />

        <div data-module="peers">
          <PeersModule instrument={instrument} />
        </div>
        <div data-module="evidence">
          <Card
            rank="quiet"
            kicker="Fusion déterministe"
            title={analysisModule('evidence').title}
            titleId="vx-analysis-evidence-title"
            footer={<>clusters dédoublonnés — aucune pertinence inventée</>}
          >
            <EvidenceRail evidence={evidence} />
          </Card>
        </div>
        <AbsentAnalysisModule id="levels" />
        <AbsentAnalysisModule id="contradictions" />
      </div>

      <DossierInspector instrument={instrument} data={data} bars={bars} advice={advice} />
      {/*
        LOT-12 : l'explication IA vit dans l'inspecteur et porte sur le
        dossier OUVERT. Elle n'est montée QUE lorsque le dossier est réellement
        affiché : sans dossier chargé, il n'y a rien à expliquer.
      */}
      <AiExplanationPanel dossiers={[{ kind: 'analysis', key: instrument }]} />
    </>
  );
}

function AnalysisRoute({ instrument }: { readonly instrument: string }) {
  const analysis = useAnalysis(instrument);
  const queryState = pageStateOf(analysis);
  const data = analysis.data;
  const state = analysisStateOf(queryState, data);

  return (
    <>
      <InstrumentPicker current={instrument} />

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={`Aucun dossier d'analyse publié pour « ${instrument} » — raison serveur : ${
            data?.reason ?? 'non fournie'
          }. Rien n'est inventé à la place.`}
        />
      ) : state === 'loading' || state === 'offline' || state === 'error' ? (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? { detail: "L'API locale est injoignable — le dossier ne peut pas être affiché." }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucun dossier affiché." }
              : {})}
        />
      ) : data !== undefined ? (
        <AnalysisBoard key={instrument} data={data} state={state} instrument={instrument} />
      ) : null}
    </>
  );
}

export function AnalysisPage() {
  const { instrument } = useParams<{ instrument?: string }>();

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-analysis">
      <div className="vx-page-header">
        <h1 id="vx-page-title-analysis">Analyse</h1>
        <p className="vx-page-question">
          Que disent les données certifiées sur cet instrument, et quelles limites restent ouvertes ?
        </p>
      </div>

      {instrument === undefined || instrument === '' ? (
        <>
          <InstrumentPicker current={null} />
          <DataStateBoundary
            state="empty"
            detail="Aucun instrument sélectionné — en choisir un ci-dessus. Aucun instrument n'est ouvert par défaut."
          />
        </>
      ) : (
        <AnalysisRoute instrument={instrument} />
      )}
    </article>
  );
}
