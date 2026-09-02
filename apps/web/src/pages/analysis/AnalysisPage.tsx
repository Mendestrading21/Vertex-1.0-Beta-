import { Link, useParams } from 'react-router-dom';

import type { AnalysisResponse } from '../../api/client.ts';
import { pageStateOf, useAnalysis } from '../../api/hooks.ts';
import { AiExplanationPanel } from '../../components/ai/AiExplanationPanel.tsx';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { useDeclaredInstruments } from '../devUniverse.ts';
import { CandleChart } from './CandleChart.tsx';
import type { AdviceView, BarsView, EvidenceView, ScenariosView } from './analysisView.ts';
import {
  ADVICE_STATUS_FR,
  DIRECTION_FR,
  adviceViewOf,
  analysisStateOf,
  barsViewOf,
  evidenceViewOf,
  scenarioAbsentLabel,
  scenariosViewOf,
} from './analysisView.ts';

/**
 * Page Analyse — question : « Que disent les données certifiées sur cet
 * instrument, et quelles limites restent ouvertes ? »
 *
 * Dominante unique : chandeliers + volume (Lightweight Charts™, chunk
 * paresseux dédié, attribution TradingView visible) dans un cadre
 * CHART_STANDARD complet, avec table OHLCV accessible ÉQUIVALENTE (mêmes
 * chaînes serveur). Modules : AdviceCard (statut canonique relayé, gates
 * dépliables), rail evidence (clusters de fusion) et bloc scénarios
 * THÉORIQUE ou son absence typée. Aucun calcul financier ici.
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

function OhlcvTable({ bars, currency }: { readonly bars: BarsView; readonly currency: string }) {
  return (
    <div
      className="vx-ohlcv-scroll"
      tabIndex={0}
      role="region"
      aria-label="Table OHLCV défilante"
    >
      <table className="vx-ohlcv-table" aria-label="Table OHLCV équivalente des chandeliers">
        <thead>
          <tr>
            <th scope="col">Jour</th>
            <th scope="col">Open ({currency})</th>
            <th scope="col">High ({currency})</th>
            <th scope="col">Low ({currency})</th>
            <th scope="col">Close ({currency})</th>
            <th scope="col">Volume</th>
          </tr>
        </thead>
        <tbody>
          {bars.bars.map((bar) => (
            <tr key={bar.tradingDay}>
              <th scope="row">
                <time dateTime={bar.tradingDay}>{bar.tradingDay}</time>
              </th>
              <td className="vx-num">{bar.open}</td>
              <td className="vx-num">{bar.high}</td>
              <td className="vx-num">{bar.low}</td>
              <td className="vx-num">{bar.close}</td>
              <td className="vx-num">{bar.volume}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdviceCard({ advice }: { readonly advice: AdviceView | null }) {
  if (advice === null) {
    return (
      <section className="vx-advice" aria-labelledby="vx-advice-title">
        <h3 id="vx-advice-title">Verdict analytique</h3>
        <p role="status">Aucun AdviceResult publié dans ce dossier — rien n'est reconstruit.</p>
      </section>
    );
  }
  const statusExplained = ADVICE_STATUS_FR[advice.status];
  const directionExplained = DIRECTION_FR[advice.direction];
  const blockedGates = advice.gates.filter((gate) => gate.status !== 'PASS');
  return (
    <section className="vx-advice" aria-labelledby="vx-advice-title" data-testid="advice-card">
      <h3 id="vx-advice-title">Verdict analytique (AdviceEngine, autorité unique)</h3>
      <dl className="vx-advice-facts">
        <div>
          <dt>Statut</dt>
          <dd>
            <span className="vx-advice-status" data-status={advice.status}>
              {advice.status}
            </span>{' '}
            {statusExplained !== undefined ? `— ${statusExplained}` : null}
          </dd>
        </div>
        <div>
          <dt>Direction (distincte du statut)</dt>
          <dd>
            <span className="vx-advice-direction" data-direction={advice.direction}>
              {advice.direction}
            </span>{' '}
            {directionExplained !== undefined ? `— ${directionExplained}` : null}
          </dd>
        </div>
        <div>
          <dt>Validité</dt>
          <dd>
            {advice.asOf !== null ? <time dateTime={advice.asOf}>{advice.asOf}</time> : '—'}
            {' → '}
            {advice.validUntil !== null ? (
              <time dateTime={advice.validUntil}>{advice.validUntil}</time>
            ) : (
              '—'
            )}{' '}
            (horizon {advice.horizon ?? '—'})
          </dd>
        </div>
        <div>
          <dt>Moteur</dt>
          <dd>
            <code>{advice.engineVersion ?? '—'}</code>
          </dd>
        </div>
        <div>
          <dt>Résumé de risque</dt>
          <dd>{advice.riskSummary ?? '—'}</dd>
        </div>
      </dl>

      <details className="vx-advice-gates">
        <summary>
          Gates : {advice.gates.length} évaluées, {blockedGates.length} non passées (fail-closed)
        </summary>
        <ul>
          {advice.gates.map((gate) => (
            <li key={gate.gateId} data-status={gate.status}>
              <code>{gate.gateId}</code>{' '}
              <span className="vx-gate-status" data-status={gate.status}>
                {gate.status}
              </span>{' '}
              — <code>{gate.reasonCode}</code>
              {gate.message !== '' ? ` : ${gate.message}` : null}
            </li>
          ))}
        </ul>
      </details>

      {advice.limitations.length > 0 ? (
        <div className="vx-advice-limitations">
          <h4>Limites déclarées</h4>
          <ul>
            {advice.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {advice.explanationFacts.length > 0 ? (
        <div className="vx-advice-facts-list">
          <h4>Faits d'explication publiés</h4>
          <ul>
            {advice.explanationFacts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function EvidenceRail({ evidence }: { readonly evidence: EvidenceView | null }) {
  return (
    <section className="vx-evidence" aria-labelledby="vx-evidence-title">
      <h3 id="vx-evidence-title">Evidence (clusters de fusion)</h3>
      {evidence === null ? (
        <p role="status">Aucun bloc evidence publié.</p>
      ) : evidence.clusters.length === 0 ? (
        <p role="status">
          Aucun cluster pertinent pour cet instrument ({evidence.considered ?? 0} observation(s)
          considérée(s), ruleset {evidence.rulesetVersion ?? '—'}). L'absence reste une absence.
        </p>
      ) : (
        <ul className="vx-evidence-list">
          {evidence.clusters.map((cluster) => (
            <li key={cluster.clusterId}>
              <p className="vx-evidence-title">
                {cluster.title}{' '}
                {cluster.synthetic ? (
                  <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
                ) : null}
              </p>
              <p className="vx-evidence-meta">
                {cluster.sources.join(', ')} · {cluster.memberCount ?? '—'} événement(s) · reçu{' '}
                {cluster.lastReceivedAt ?? '—'}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ScenarioPanel({ scenarios }: { readonly scenarios: ScenariosView | null }) {
  if (scenarios === null) {
    return (
      <section className="vx-scenarios" aria-labelledby="vx-scenarios-title">
        <h3 id="vx-scenarios-title">Scénarios</h3>
        <p role="status">Aucun bloc scénarios publié.</p>
      </section>
    );
  }
  if (scenarios.status === 'ABSENT') {
    return (
      <section className="vx-scenarios" aria-labelledby="vx-scenarios-title">
        <h3 id="vx-scenarios-title">Scénarios</h3>
        <p role="status" data-testid="scenarios-absent">
          {scenarioAbsentLabel(scenarios.reason)}
        </p>
      </section>
    );
  }
  const scenario = scenarios.grid[0] ?? [];
  return (
    <section className="vx-scenarios" aria-labelledby="vx-scenarios-title">
      <h3 id="vx-scenarios-title">
        Scénarios <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span>
      </h3>
      <p className="vx-scenarios-basis">
        Base : {scenarios.basisLabel ?? '—'} — grille P&amp;L (avant coûts déclarés) repricée par le
        worker (<code>{scenarios.calculationId ?? '—'}</code>), IV inchangée.
      </p>
      <div
        className="vx-ohlcv-scroll"
        tabIndex={0}
        role="region"
        aria-label="Grille de scénarios défilante"
      >
        <table className="vx-scenarios-table" aria-label="Grille de scénarios théorique (P&L par spot et temps)">
          <thead>
            <tr>
              <th scope="col">Temps restant (années)</th>
              {scenarios.spotGrid.map((spot) => (
                <th scope="col" key={spot} className="vx-num">
                  spot {spot}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scenarios.timeGridYears.map((time, timeIndex) => (
              <tr key={time}>
                <th scope="row" className="vx-num">
                  {time}
                </th>
                {(scenario[timeIndex] ?? []).map((cell, spotIndex) => (
                  <td key={scenarios.spotGrid[spotIndex] ?? spotIndex} className="vx-num">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AnalysisFrame({
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
    <section className="vx-chartframe" data-rank="dominant" aria-labelledby="vx-analysis-title">
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
              Aucune conclusion serveur publiée pour ce dossier — les faits d'explication de
              l'AdviceCard ci-dessous sont les seuls énoncés certifiés.
            </p>
            <OhlcvTable bars={bars} currency={currency} />
          </>
        ) : (
          <p role="status">Aucune barre exploitable à dessiner — rien n'est inventé à la place.</p>
        )}

        <AdviceCard advice={advice} />
        <EvidenceRail evidence={evidence} />
        <ScenarioPanel scenarios={scenarios} />
      </DataStateBoundary>

      <footer className="vx-chartframe-foot">
        <p>
          Méthode : barres OHLCV validées barre à barre par le worker (une barre invalide est
          écartée avec sa raison, jamais réparée) ; verdict par l'unique <code>AdviceEngine</code>{' '}
          (<code>{advice?.engineVersion ?? data.engine_version ?? '—'}</code>) ; clusters par la
          fusion déterministe. Rendu : Lightweight Charts™ —{' '}
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


/**
 * Indicateurs techniques — valeurs SERVEUR, affichées telles quelles.
 *
 * Aucun calcul ici : la forme en pourcentage arrive du serveur, comme
 * `return_1d_pct` sur Marchés. Aucune interprétation non plus : un ATR est une
 * amplitude, pas un jugement, et aucun seuil n'est déclaré qui permettrait de
 * dire « élevé ».
 */
function IndicatorsPanel({
  indicators,
  currency,
}: {
  readonly indicators: Readonly<Record<string, unknown>> | null | undefined;
  readonly currency: string;
}) {
  if (indicators === null || indicators === undefined) {
    return null;
  }

  const lire = (nom: string): Readonly<Record<string, unknown>> | null => {
    const bloc = indicators[nom];
    return typeof bloc === 'object' && bloc !== null
      ? (bloc as Readonly<Record<string, unknown>>)
      : null;
  };
  const texte = (bloc: Readonly<Record<string, unknown>>, cle: string): string | null => {
    const valeur = bloc[cle];
    return typeof valeur === 'string' && valeur !== '' ? valeur : null;
  };
  const nombre = (bloc: Readonly<Record<string, unknown>>, cle: string): number | null =>
    typeof bloc[cle] === 'number' ? (bloc[cle] as number) : null;

  const volatilite = lire('realized_volatility');
  const atr = lire('atr');
  if (volatilite === null && atr === null) {
    return null;
  }

  const methode = (bloc: Readonly<Record<string, unknown>> | null): string | null => {
    if (bloc === null) return null;
    const calcul = bloc.calculation;
    if (typeof calcul !== 'object' || calcul === null) return null;
    const m = (calcul as Record<string, unknown>).method;
    return typeof m === 'string' ? m : null;
  };

  function Ligne({
    bloc,
    libelle,
    valeurAffichee,
    fenetreCle,
    fenetreLibelle,
    testid,
  }: {
    readonly bloc: Readonly<Record<string, unknown>> | null;
    readonly libelle: string;
    readonly valeurAffichee: string | null;
    readonly fenetreCle: string;
    readonly fenetreLibelle: string;
    readonly testid: string;
  }) {
    if (bloc === null) return null;
    const statut = texte(bloc, 'status');
    const fenetre = nombre(bloc, fenetreCle);
    return (
      <div className="vx-indicator" data-testid={testid}>
        <dt>
          {libelle}
          {fenetre === null ? null : (
            <span className="vx-indicator-window">
              {' '}
              — {fenetreLibelle} {fenetre}
            </span>
          )}
        </dt>
        <dd>
          {statut === 'OK' && valeurAffichee !== null ? (
            <span className="vx-indicator-value">{valeurAffichee}</span>
          ) : (
            <span className="vx-cell-absent" data-testid={`${testid}-absent`}>
              {statut ?? 'ABSENT'}
              {texte(bloc, 'detail') === null ? null : ` — ${texte(bloc, 'detail')}`}
            </span>
          )}
        </dd>
      </div>
    );
  }

  const volPct = volatilite === null ? null : texte(volatilite, 'value_pct');
  const atrValeur = atr === null ? null : texte(atr, 'value');

  return (
    <section className="vx-indicators" aria-labelledby="vx-indicators-title">
      <h2 id="vx-indicators-title">Indicateurs techniques</h2>
      <p className="vx-indicators-note">
        Valeurs calculées par le moteur serveur et relayées telles quelles. Aucun seuil
        n’est déclaré : la mesure est publiée, son interprétation ne l’est pas.
      </p>
      <dl className="vx-indicator-list">
        <Ligne
          bloc={volatilite}
          libelle="Volatilité réalisée annualisée"
          valeurAffichee={volPct === null ? null : `${volPct} %`}
          fenetreCle="window"
          fenetreLibelle="fenêtre"
          testid="indicator-volatility"
        />
        <Ligne
          bloc={atr}
          libelle="ATR (Wilder)"
          valeurAffichee={atrValeur === null ? null : `${atrValeur} ${currency}`}
          fenetreCle="lookback"
          fenetreLibelle="sur"
          testid="indicator-atr"
        />
      </dl>
      <p className="vx-indicators-method">
        {methode(volatilite) === null ? null : (
          <span>
            <code>market.realized_volatility</code> : {methode(volatilite)}
          </span>
        )}
        {methode(atr) === null ? null : (
          <span>
            {' · '}
            <code>market.atr</code> : {methode(atr)}
          </span>
        )}
      </p>
    </section>
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
        <>
          <AnalysisFrame key={instrument} data={data} state={state} instrument={instrument} />

          <IndicatorsPanel
            indicators={data.indicators}
            currency={
              typeof data.bars?.currency === 'string' ? data.bars.currency : ''
            }
          />

          {/*
            LOT-12 : l'explication IA vit dans l'inspecteur et porte sur le
            dossier OUVERT. Elle n'est donc montée QUE lorsque le dossier est
            réellement affiché : sans dossier chargé, il n'y a rien à
            expliquer, et un panneau d'explication à côté d'un écran hors
            ligne serait un second état dégradé pour rien.
          */}
          <AiExplanationPanel dossiers={[{ kind: 'analysis', key: instrument }]} />
        </>
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
