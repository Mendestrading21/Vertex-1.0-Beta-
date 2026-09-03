import { Link } from 'react-router-dom';

import type { AnalysisResponse } from '../../api/client.ts';
import { useCalendar } from '../../api/decisionApi.ts';
import { pageStateOf, useMarketsOverview, useSecFundamentals } from '../../api/hooks.ts';
import { Card } from '../../components/Card.tsx';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { Metric } from '../../components/Metric.tsx';
import { ModuleStatus } from '../../components/ModuleStatus.tsx';
import { AgendaLine } from '../../components/calendar/AgendaLine.tsx';
import { Sparkline } from '../../components/markets/Sparkline.tsx';
import type { FlatTicker } from '../../components/markets/marketsView.ts';
import { GROUP_LABELS_FR, flattenTickers, frDecimal, signSymbolOf } from '../../components/markets/marketsView.ts';
import { moduleShowsContent, moduleStateOf } from '../../components/moduleState.ts';
import type { ModuleState } from '../../components/moduleState.ts';
import { calendarEventsOf } from '../calendar/calendarView.ts';
import { analysisModule } from './analysisModules.ts';
import type { AdviceView, BarsView } from './analysisView.ts';
import { IDENTITY_STATE_FR, secFundamentalsViewOf } from './secView.ts';

/**
 * Les modules SERVIS de la planche §4, hors la dominante (le cadre des
 * chandeliers) et les panneaux déjà extraits (verdict, evidence, scénarios,
 * indicateurs). Chacun lit son propre snapshot par le hook de la page
 * propriétaire — Marchés pour la variation et le secteur, Calendrier pour
 * les catalyseurs, la route SEC pour les faits officiels — dit son état à
 * sa place et ne montre AUCUNE valeur hors des états qui en portent une.
 * Aucun calcul : chaînes serveur, comptes publiés, géométrie des clôtures.
 */

const LINE_WINDOW = 30;
const VOLUME_WINDOW = 14;
const CATALYST_LINES = 6;
const FACT_ROWS = 12;

function publie(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? 'non publié' : String(value);
}

/** L'entrée Marchés de l'instrument, si le snapshot la couvre. */
function useMarketsEntry(instrument: string): {
  readonly entry: FlatTicker | null;
  readonly peers: readonly FlatTicker[];
  readonly state: ModuleState;
} {
  const query = useMarketsOverview();
  const state = moduleStateOf(pageStateOf(query), query.data);
  const sectors = query.data?.sectors ?? [];
  const all = flattenTickers(sectors);
  const entry = all.find((candidate) => candidate.ticker.ticker === instrument) ?? null;
  const peers =
    entry === null
      ? []
      : all.filter(
          (candidate) =>
            candidate.sectorLabel === entry.sectorLabel && candidate.ticker.ticker !== instrument,
        );
  return { entry, peers, state };
}

// ---------------------------------------------------------------------------

export function InstrumentHeaderModule({
  instrument,
  data,
  bars,
}: {
  readonly instrument: string;
  readonly data: AnalysisResponse;
  readonly bars: BarsView | null;
}) {
  const module = analysisModule('instrument-header');
  const { entry, state } = useMarketsEntry(instrument);
  const lineBars = bars === null ? [] : bars.bars.slice(-LINE_WINDOW);
  const volumeBars = bars === null ? [] : bars.bars.slice(-VOLUME_WINDOW);
  const sign = entry?.group ?? 'flat';
  return (
    <article className="vx-ih" data-sign={sign} data-testid="instrument-header" aria-labelledby="vx-ih-title">
      <header className="vx-ih-head">
        <div className="vx-ih-identity">
          <p className="vx-focus-kicker">{module.title}</p>
          <h2 id="vx-ih-title" className="vx-ih-ticker">
            <code>{instrument}</code>
          </h2>
          <p className="vx-ih-sector">{entry === null ? 'secteur non publié par Marchés' : entry.sectorLabel}</p>
        </div>
        <div className="vx-iw-fresh">
          <FreshnessBadge ageSeconds={data.age_seconds} sourceLabel="dossier" />
        </div>
      </header>

      <div className="vx-ih-price-row">
        {bars !== null && bars.lastClose !== null ? (
          <span className="vx-ih-price" data-testid="instrument-header-price">
            {frDecimal(bars.lastClose)}
            <span className="vx-iw-currency"> {bars.currency ?? 'devise non publiée'}</span>
          </span>
        ) : (
          <span className="vx-ih-price vx-cell-absent">dernière clôture non publiée</span>
        )}
        {entry === null ? (
          <span className="vx-iw-delta" data-sign="flat" data-testid="instrument-header-delta">
            {state === 'loading' ? 'variation 1 j : chargement' : 'variation 1 j non publiée'}
          </span>
        ) : (
          <span className="vx-iw-delta" data-sign={entry.group} data-testid="instrument-header-delta">
            <span aria-hidden="true">{signSymbolOf(entry.group)}</span> {frDecimal(entry.ticker.return_1d_pct)} %
            <span className="vx-visually-hidden"> ({GROUP_LABELS_FR[entry.group]}, rendement 1 j)</span>
          </span>
        )}
      </div>

      <div className="vx-iw-chart">
        {lineBars.length > 0 && bars !== null ? (
          <Sparkline
            closes={lineBars.map((bar) => bar.close)}
            volumes={volumeBars.map((bar) => bar.volume)}
            sign={sign}
            label={`${lineBars.length} clôtures publiées de ${lineBars[0]?.tradingDay ?? ''} à ${
              lineBars[lineBars.length - 1]?.tradingDay ?? ''
            }, première ${lineBars[0]?.close ?? ''}, dernière ${lineBars[lineBars.length - 1]?.close ?? ''} ${
              bars.currency ?? ''
            }`}
          />
        ) : (
          <p className="vx-iw-absent" role="status">
            Dossier publié sans barre exploitable : aucune série à tracer.
          </p>
        )}
      </div>

      <footer className="vx-iw-foot">
        {bars === null ? 'aucune série publiée' : `clôture ${publie(bars.lastTradingDay)}`}
        {lineBars.length > 0 ? ` · ${lineBars.length} séances tracées` : ''}
        {entry === null ? '' : ` · variation 1 j du snapshot Marchés (${entry.ticker.trading_day})`}
      </footer>
    </article>
  );
}

// ---------------------------------------------------------------------------

export function IdentityModule({
  instrument,
  data,
  bars,
}: {
  readonly instrument: string;
  readonly data: AnalysisResponse;
  readonly bars: BarsView | null;
}) {
  const module = analysisModule('identity-facts');
  const { entry } = useMarketsEntry(instrument);
  return (
    <Card
      rank="quiet"
      kicker="Faits publiés"
      title={module.title}
      titleId="vx-analysis-identity-title"
      footer={<>industrie, capitalisation et bêta : aucune source ne les publie — rien n’est déduit</>}
    >
      <div className="vx-metrics-grid" data-testid="identity-facts">
        <Metric label="Secteur" value={entry === null ? null : entry.sectorLabel} size="compact" />
        <Metric label="Devise" value={bars?.currency ?? null} size="compact" />
        <Metric label="Population" value={data.population} size="compact" />
        <Metric label="Base d’ajustement" value={bars?.adjustmentBasis ?? null} size="compact" />
        <Metric label="Industrie" value={null} size="compact" />
        <Metric label="Capitalisation" value={null} size="compact" />
        <Metric label="Bêta" value={null} size="compact" />
        <Metric label="Qualité de la série" value={bars?.quality ?? null} size="compact" />
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function FinancialsModule({ instrument }: { readonly instrument: string }) {
  const module = analysisModule('financials');
  const query = useSecFundamentals(instrument);
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const view = data === undefined ? null : secFundamentalsViewOf(data);
  return (
    <Card
      rank="quiet"
      kicker="Relais SEC EDGAR"
      title={module.title}
      titleId="vx-analysis-financials-title"
      className="vx-sec"
      {...(data !== undefined && moduleShowsContent(state)
        ? {
            footer: (
              <>
                source <code>{publie(data.source)}</code> · droits <code>{publie(data.rights)}</code> · snapshot v
                {publie(data.snapshot_version)} · données au {publie(data.data_as_of)}
              </>
            ),
          }
        : { footer: <>aucun ratio, score ni avis n’est calculé sur ces faits</> })}
    >
      <ModuleStatus state={state} raw={state === 'closed' ? data?.state : data?.reason} />
      {state === 'empty' ? (
        <p className="vx-module-sentence" role="status" data-testid="sec-empty">
          Aucun snapshot SEC publié pour <code>{instrument}</code> : rien n’est affiché à la place.
        </p>
      ) : null}
      {moduleShowsContent(state) && data !== undefined && view !== null ? (
        <div data-testid="sec-facts">
          <p className="vx-module-sentence">
            <code>{publie(data.identity_state)}</code> —{' '}
            {data.identity_state === null ? 'état non publié' : (IDENTITY_STATE_FR[data.identity_state] ?? data.identity_state)}
            {data.entity_name === null ? null : (
              <>
                {' '}
                · {data.entity_name} (CIK <code>{publie(data.cik)}</code>)
              </>
            )}
          </p>
          <h3 className="vx-snapshot-block-title">Dépôts publiés ({view.filings.length})</h3>
          {view.filings.length === 0 ? (
            <p className="vx-module-sentence">Aucun dépôt publié.</p>
          ) : (
            <ul className="vx-sec-filings">
              {view.filings.map((filing) => (
                <li key={filing.accession}>
                  <code>{filing.form ?? 'formulaire non publié'}</code> · disponible {publie(filing.availableAt)}
                  {filing.primaryDocumentUrl === null ? (
                    <>
                      {' '}
                      · <code>{filing.accession}</code>
                    </>
                  ) : (
                    <>
                      {' '}
                      ·{' '}
                      <a href={filing.primaryDocumentUrl} rel="noopener noreferrer" target="_blank">
                        document officiel {filing.accession}
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
          <h3 className="vx-snapshot-block-title">Faits XBRL publiés ({view.facts.length})</h3>
          {view.facts.length === 0 ? (
            <p className="vx-module-sentence">Aucun fait publié.</p>
          ) : (
            <div className="vx-cal-scroll" tabIndex={0} role="region" aria-label="Faits XBRL publiés">
              <table className="vx-matrix-table vx-sec-facts">
                <thead>
                  <tr>
                    <th scope="col">Concept</th>
                    <th scope="col">Valeur</th>
                    <th scope="col">Unité</th>
                    <th scope="col">Période</th>
                  </tr>
                </thead>
                <tbody>
                  {view.facts.slice(0, FACT_ROWS).map((fact) => (
                    <tr key={fact.key}>
                      <th scope="row">
                        <code>{fact.concept}</code>
                        {fact.taxonomy === null ? null : <span className="vx-inspector-unit"> {fact.taxonomy}</span>}
                      </th>
                      <td className="vx-num">{fact.value ?? 'non publiée'}</td>
                      <td>{fact.unit ?? '—'}</td>
                      <td>{fact.periodEnd ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="vx-module-sentence">
            {view.facts.length > FACT_ROWS ? `${FACT_ROWS} premiers faits de ${view.facts.length} publiés · ` : ''}
            {view.conflictCount} conflit{view.conflictCount > 1 ? 's' : ''} publié{view.conflictCount > 1 ? 's' : ''} ·{' '}
            {publie(view.coverage.observationsConsidered)} observations considérées
          </p>
        </div>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function CatalystsModule({ instrument }: { readonly instrument: string }) {
  const module = analysisModule('upcoming-catalysts');
  const query = useCalendar(null);
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const events =
    data === undefined
      ? []
      : calendarEventsOf(Array.isArray(data.agenda) ? data.agenda : []).filter(
          (event) => event.ticker === instrument,
        );
  const lines = events.slice(0, CATALYST_LINES);
  return (
    <Card
      rank="quiet"
      kicker="Agenda publié"
      title={module.title}
      titleId="vx-analysis-catalysts-title"
      {...(moduleShowsContent(state) && data !== undefined
        ? {
            footer: (
              <>
                {lines.length} sur {events.length} pour cet instrument · snapshot v{publie(data.snapshot_version)} ·{' '}
                <Link to="/calendar">voir le calendrier</Link>
              </>
            ),
          }
        : {})}
    >
      <ModuleStatus state={state} raw={state === 'closed' ? data?.state : data?.reason} />
      {moduleShowsContent(state) && data !== undefined ? (
        lines.length === 0 ? (
          <p className="vx-module-sentence" role="status" data-testid="analysis-catalysts-empty">
            Aucun événement publié pour <code>{instrument}</code> dans l’agenda.
          </p>
        ) : (
          <ul className="vx-agenda-mini" aria-label={`Événements publiés pour ${instrument}`} data-testid="analysis-catalysts">
            {lines.map((event) => (
              <AgendaLine key={event.eventId} event={event} />
            ))}
          </ul>
        )
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function KeyRisksModule({ advice }: { readonly advice: AdviceView | null }) {
  const module = analysisModule('key-risks');
  const degraded = advice === null ? [] : advice.gates.filter((gate) => gate.status !== 'PASS');
  return (
    <Card
      rank="quiet"
      kicker="Déclaré par le moteur"
      title={module.title}
      titleId="vx-analysis-risks-title"
      footer={<>résumé, limites et gates non passées de l’AdviceResult — aucun risque estimé ici</>}
    >
      {advice === null ? (
        <p className="vx-module-sentence" role="status">
          Aucun AdviceResult publié : aucun risque déclaré à relayer.
        </p>
      ) : (
        <div data-testid="analysis-risks">
          <p className="vx-module-sentence">{advice.riskSummary ?? 'Résumé de risque non publié.'}</p>
          {degraded.length > 0 ? (
            <ul className="vx-inspector-list">
              {degraded.map((gate) => (
                <li key={gate.gateId} data-status={gate.status}>
                  <code>{gate.gateId}</code>{' '}
                  <span className="vx-gate-status" data-status={gate.status}>
                    {gate.status}
                  </span>{' '}
                  — <code>{gate.reasonCode}</code>
                </li>
              ))}
            </ul>
          ) : (
            <p className="vx-module-sentence">Toutes les gates publiées sont passées.</p>
          )}
          {advice.limitations.length > 0 ? (
            <ul className="vx-opp-limits">
              {advice.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function PeersModule({ instrument }: { readonly instrument: string }) {
  const module = analysisModule('peers');
  const { entry, peers, state } = useMarketsEntry(instrument);
  return (
    <Card
      rank="quiet"
      kicker="Snapshot Marchés"
      title={module.title}
      titleId="vx-analysis-peers-title"
      footer={<>rendement 1 j par instrument, chaîne serveur · <Link to="/markets">voir Marchés</Link></>}
    >
      <ModuleStatus state={state} />
      {moduleShowsContent(state) ? (
        entry === null ? (
          <p className="vx-module-sentence" role="status">
            <code>{instrument}</code> n’est pas couvert par le snapshot Marchés : aucun pair connu.
          </p>
        ) : peers.length === 0 ? (
          <p className="vx-module-sentence" role="status">
            Seul instrument couvert dans {entry.sectorLabel}.
          </p>
        ) : (
          <ul className="vx-sector-chips" aria-label={`Pairs de ${instrument} dans ${entry.sectorLabel}`} data-testid="analysis-peers">
            {peers.map((peer) => (
              <li key={peer.ticker.ticker} data-sign={peer.group}>
                <Link className="vx-sector-chip" to={`/analysis/${encodeURIComponent(peer.ticker.ticker)}`}>
                  <code>{peer.ticker.ticker}</code>
                  <span className="vx-sector-return">
                    <span aria-hidden="true">{signSymbolOf(peer.group)}</span> {frDecimal(peer.ticker.return_1d_pct)} %
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </Card>
  );
}
