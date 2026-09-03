import { Link } from 'react-router-dom';

import { pageStateOf } from '../../api/hooks.ts';
import { usePerformance, usePortfolio } from '../../api/portfolioApi.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { Card } from '../../components/Card.tsx';
import { Metric } from '../../components/Metric.tsx';
import { ModuleStatus } from '../../components/ModuleStatus.tsx';
import { moduleShowsContent, moduleStateOf } from '../../components/moduleState.ts';
import { ConcentrationBars } from '../portfolio/ConcentrationPanel.tsx';
import { METRIC_LABELS, performanceContentOf } from '../portfolio/performance/performanceView.ts';
import { valuationContentOf } from '../portfolio/portfolioView.ts';
import type { ValuationContentView } from '../portfolio/portfolioView.ts';
import { riskModule } from './riskModules.ts';
import type { RiskView } from './riskView.ts';

/**
 * Les modules SERVIS de la planche §9, hors la dominante (la matrice, portée
 * par la page). Quatre lisent le snapshot de la matrice déjà validé par la
 * page ; deux lisent le registre manuel et sa performance par les hooks des
 * pages propriétaires (vues pures importées, jamais les pages — porte
 * `INEFFECTIVE_DYNAMIC_IMPORT`), chacun avec son état. Aucun calcul :
 * chaînes serveur, comptes publiés, géométrie des poids publiés.
 */

export function AbsentRiskModule({ id }: { readonly id: string }) {
  const module = riskModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    <div data-module={id}>
      <AbsentModule title={module.title} question={module.question} reason={module.status.reason} note={module.status.note} />
    </div>
  );
}

// ---------------------------------------------------------------------------

export function ExtremesModule({ view }: { readonly view: RiskView }) {
  const module = riskModule('extremes');
  return (
    <Card rank="quiet" kicker="Publiées avec la matrice" title={module.title} titleId="vx-risk-extremes-title" footer={<>coefficients exacts du serveur ; l’avertissement de synchronicité reste visible</>}>
      {view.extremes === null ? (
        <p className="vx-module-sentence" role="status" data-testid="risk-extremes-empty">
          Aucune paire extrême publiée : la matrice n’a pas été construite.
        </p>
      ) : (
        <dl className="vx-risk-extremes" data-testid="risk-extremes">
          <div>
            <dt>Paire la plus liée</dt>
            <dd>
              {view.extremes.mostCorrelated.pair} <strong>{view.extremes.mostCorrelated.value}</strong>
            </dd>
          </div>
          <div>
            <dt>Paire la plus opposée</dt>
            <dd>
              {view.extremes.mostOpposed.pair} <strong>{view.extremes.mostOpposed.value}</strong>
            </dd>
          </div>
        </dl>
      )}
      {view.synchronicityWarning !== null ? (
        <p className="vx-risk-caveat" role="note">
          {view.synchronicityWarning}
        </p>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

function lookbackLabel(seconds: number | null): string {
  if (seconds === null) {
    return 'non publiée';
  }
  return `${seconds} s`;
}

export function CoverageModule({ view }: { readonly view: RiskView }) {
  const module = riskModule('coverage');
  const coverage = view.coverage;
  return (
    <Card
      rank="quiet"
      kicker="Périmètre déclaré"
      title={module.title}
      titleId="vx-risk-coverage-title"
      footer={<>le périmètre est DÉCLARÉ, jamais deviné : comparer qui à qui est une décision, pas une déduction du code</>}
    >
      <dl className="vx-risk-coverage" data-testid="risk-coverage">
        <div>
          <dt>Instruments retenus</dt>
          <dd>
            {coverage.retained} sur {coverage.perimeterSize} déclarés
            {coverage.retainedTickers.length > 0 ? (
              <>
                {' '}
                (<code>{coverage.retainedTickers.join(', ')}</code>)
              </>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>Séances communes</dt>
          <dd>
            {coverage.commonDays} (minimum déclaré&nbsp;: {coverage.minimumDays})
          </dd>
        </div>
        <div>
          <dt>Fenêtre</dt>
          <dd>{coverage.window ?? 'non publiée'}</dd>
        </div>
        <div>
          <dt>Seuils des bandes</dt>
          <dd>
            modéré à partir de {coverage.moderateThreshold}, fort à partir de {coverage.strongThreshold}
          </dd>
        </div>
        <div>
          <dt>Unité</dt>
          <dd>
            <code>{view.unit ?? 'non publiée'}</code>
          </dd>
        </div>
        <div>
          <dt>Retour en arrière</dt>
          <dd>{lookbackLabel(coverage.lookbackSeconds)}</dd>
        </div>
      </dl>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function AlignmentModule({ view }: { readonly view: RiskView }) {
  const module = riskModule('alignment');
  const coverage = view.coverage;
  return (
    <Card
      rank="quiet"
      kicker="Séances perdues"
      title={module.title}
      titleId="vx-risk-alignment-title"
      footer={<>une séance manquante chez un seul instrument la retire à TOUS : le calcul exige une matrice complète et refuse un trou plutôt que de le combler</>}
    >
      {coverage.alignmentLoss.length === 0 ? (
        <p className="vx-module-sentence" role="status" data-testid="risk-alignment-empty">
          Aucune séance perdue à l’alignement — ou aucun compte publié.
        </p>
      ) : (
        <ul className="vx-risk-alignment-list" data-testid="risk-alignment">
          {coverage.alignmentLoss.map((entry) => (
            <li key={entry.ticker}>
              <span>{entry.ticker}</span> {entry.lost} séance
              {entry.lost > 1 ? 's' : ''} perdue{entry.lost > 1 ? 's' : ''}
            </li>
          ))}
        </ul>
      )}
      {coverage.tradingDaysPerInstrument.length > 0 ? (
        <p className="vx-module-sentence">
          Séances par instrument :{' '}
          {coverage.tradingDaysPerInstrument.map((entry, index) => (
            <span key={entry.ticker}>
              {index > 0 ? ' · ' : ''}
              <code>{entry.ticker}</code> {entry.days}
            </span>
          ))}
        </p>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function DiscardsModule({ view }: { readonly view: RiskView }) {
  const module = riskModule('discards');
  const coverage = view.coverage;
  return (
    <Card rank="quiet" kicker="Écartés avec leur raison" title={module.title} titleId="vx-risk-discards-title" footer={<>un instrument écarté ne devient jamais une colonne vide : il sort avec son motif</>}>
      {coverage.discarded.length === 0 ? (
        <p className="vx-module-sentence" role="status" data-testid="risk-discards-empty">
          Aucun instrument écarté du périmètre déclaré.
        </p>
      ) : (
        <ul className="vx-risk-discards-list" data-testid="risk-discards">
          {coverage.discarded.map((entry) => (
            <li key={entry.instrument}>
              <span>{entry.instrument}</span> {entry.reason}
            </li>
          ))}
        </ul>
      )}
      {coverage.rejectedRecords.length > 0 ? (
        <p className="vx-module-sentence" data-testid="risk-rejected-records">
          {coverage.rejectedRecords.length} enregistrement(s) rejeté(s) : {coverage.rejectedRecords.join(' ; ')}
        </p>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

/** Lecture DÉFENSIVE du portefeuille : un corps étranger reste une absence. */
function valuationOf(data: unknown): ValuationContentView | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const valuation = (data as Record<string, unknown>)['valuation'];
  if (typeof valuation !== 'object' || valuation === null || typeof (valuation as Record<string, unknown>)['state'] !== 'string') {
    return null;
  }
  return valuationContentOf(valuation as Parameters<typeof valuationContentOf>[0]);
}

function portfolioIdOf(data: unknown): number | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const portfolio = (data as Record<string, unknown>)['portfolio'];
  if (typeof portfolio !== 'object' || portfolio === null) {
    return null;
  }
  const id = (portfolio as Record<string, unknown>)['id'];
  return typeof id === 'number' ? id : null;
}

export function RegisterConcentrationModule() {
  const module = riskModule('concentration');
  const query = usePortfolio();
  const view = valuationOf(query.data);
  const state = moduleStateOf(pageStateOf(query), query.data === undefined ? undefined : { state: view === null ? 'error' : 'ok' });
  return (
    <Card
      rank="quiet"
      kicker="Registre manuel"
      title={module.title}
      titleId="vx-risk-concentration-title"
      footer={
        <>
          poids normalisés et Herfindahl publiés par la valorisation ; <Link to="/portfolio">voir Portefeuille</Link>
        </>
      }
    >
      <ModuleStatus state={state} raw={view === null ? 'valorisation illisible ou absente' : null} />
      {moduleShowsContent(state) && view !== null ? (
        view.blocks.length === 0 ? (
          <p className="vx-module-sentence" role="status" data-testid="risk-concentration-empty">
            Aucune position dérivée du journal : aucune concentration à mesurer.
          </p>
        ) : (
          <div data-testid="risk-concentration">
            {view.blocks.map((block) => (
              <div key={block.currency} className="vx-risk-concentration-block">
                <div className="vx-metrics-row">
                  <Metric
                    label={`Herfindahl (${block.currency})`}
                    value={block.concentrationStatus === 'OK' ? block.herfindahl : null}
                    absentLabel={block.concentrationStatus === 'OK' ? 'non publié' : (block.concentrationStatus ?? 'ABSENT')}
                    note={`${block.weights.length} ticker(s) pondéré(s)`}
                    testId={`risk-herfindahl-${block.currency}`}
                    size="compact"
                  />
                </div>
                {block.concentrationStatus === 'OK' ? <ConcentrationBars block={block} testIdPrefix="risk-bars" /> : null}
              </div>
            ))}
          </div>
        )
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function DrawdownModule() {
  const module = riskModule('max-drawdown');
  const portfolioQuery = usePortfolio();
  const portfolioId = portfolioIdOf(portfolioQuery.data);
  const query = usePerformance(portfolioId);
  const portfolioState = pageStateOf(portfolioQuery);
  const queryState =
    portfolioId === null ? (portfolioState === 'ready' || portfolioState === 'refreshing' ? 'error' : portfolioState) : pageStateOf(query);
  const view = query.data === undefined || query.data.state === 'empty' ? null : performanceContentOf(query.data.content);
  const state = moduleStateOf(queryState, query.data);
  return (
    <Card
      rank="quiet"
      kicker="Snapshot de performance"
      title={module.title}
      titleId="vx-risk-drawdown-title"
      footer={
        view === null ? (
          <>baisse maximale depuis un sommet, publiée par le serveur, brut et net des frais</>
        ) : (
          <>
            population <code>{view.population ?? 'non publiée'}</code> · <Link to="/portfolio">voir Performance</Link>
          </>
        )
      }
    >
      <ModuleStatus state={state} raw={portfolioId === null ? 'portefeuille non lu' : (query.data?.reason ?? null)} />
      {moduleShowsContent(state) && view !== null ? (
        <div className="vx-metrics-row" data-testid="risk-drawdown">
          {(['drawdown_gross', 'drawdown_net'] as const).map((key) => {
            const block = view.metrics[key];
            return (
              <Metric
                key={key}
                label={METRIC_LABELS[key]}
                value={block.status === 'OK' ? block.maxDrawdownPct : null}
                unit="%"
                sign={block.status === 'OK' && block.maxDrawdownPct !== null ? (block.maxDrawdownPct.startsWith('-') ? 'down' : 'flat') : null}
                absentLabel={block.status === 'OK' ? 'non publié' : `${block.status}${block.reason !== null ? ` — ${block.reason}` : ''}`}
                {...(block.status === 'OK' && block.peakAt !== null && block.troughAt !== null ? { note: `sommet ${block.peakAt} → creux ${block.troughAt}` } : {})}
                testId={`risk-${key}`}
              />
            );
          })}
        </div>
      ) : moduleShowsContent(state) ? (
        <p className="vx-module-sentence" role="status">
          Aucun snapshot de performance publié pour ce portefeuille.
        </p>
      ) : null}
    </Card>
  );
}
