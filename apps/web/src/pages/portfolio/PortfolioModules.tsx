import type { LedgerTransactionEntry } from '../../api/client.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { usePerformance } from '../../api/portfolioApi.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { Card } from '../../components/Card.tsx';
import { Metric } from '../../components/Metric.tsx';
import { ModuleStatus } from '../../components/ModuleStatus.tsx';
import { moduleShowsContent, moduleStateOf } from '../../components/moduleState.ts';
import type { ModuleState } from '../../components/moduleState.ts';
import { PortfolioTable } from './PortfolioTable.tsx';
import { METRIC_LABELS, performanceContentOf } from './performance/performanceView.ts';
import type { MetricBlockView, MetricKey } from './performance/performanceView.ts';
import { portfolioModule } from './portfolioModules.ts';
import { LEDGER_KIND_LABELS } from './portfolioView.ts';
import type { ExcludedLotRow, ValuationContentView, ValuedLotRow } from './portfolioView.ts';

/**
 * Les modules SERVIS de la planche §7, hors la dominante (la concentration,
 * portée par la page) et hors les trois sections d'écriture (journal,
 * déclaration, import), conservées telles quelles dans leurs cellules.
 * Aucun calcul : chaînes serveur, comptes de lignes, lignage publié.
 */

export function AbsentPortfolioModule({ id }: { readonly id: string }) {
  const module = portfolioModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    <div data-module={id}>
      <AbsentModule title={module.title} question={module.question} reason={module.status.reason} note={module.status.note} />
    </div>
  );
}

/**
 * Ce qu'un module de valorisation montre quand le snapshot n'est pas lisible.
 * La raison serveur n'est écrite qu'UNE fois sur la page (module
 * « Valorisation publiée ») ; les autres modules renvoient vers elle.
 */
export function ValuationAbsence({
  state,
  reason,
  withReason = false,
}: {
  readonly state: ModuleState;
  readonly reason: string | null;
  readonly withReason?: boolean;
}) {
  if (state === 'empty') {
    return (
      <p className="vx-module-sentence" role="status">
        {withReason
          ? `Aucune valorisation publiée${reason !== null ? ` — raison serveur : ${reason}` : ' par le worker pour ce portefeuille'}.`
          : 'Aucune valorisation publiée : rien à mesurer (voir « Valorisation publiée »).'}
      </p>
    );
  }
  return <ModuleStatus state={state} raw={withReason ? reason : null} />;
}

// ---------------------------------------------------------------------------

function signOf(value: string | null): 'up' | 'down' | 'flat' | null {
  if (value === null) {
    return null;
  }
  if (value.startsWith('-')) {
    return 'down';
  }
  return /^[+]?0*(\.0+)?$/.test(value) ? 'flat' : 'up';
}

function ratioMetric(key: MetricKey, block: MetricBlockView) {
  const isTwr = key === 'twr_gross' || key === 'twr_net';
  const pct = isTwr ? block.totalReturnPct : block.ratePct;
  return (
    <Metric
      key={key}
      label={METRIC_LABELS[key]}
      value={block.status === 'OK' ? pct : null}
      unit={isTwr ? '%' : '% / an'}
      sign={block.status === 'OK' ? signOf(pct) : null}
      absentLabel={block.status === 'OK' ? 'non publié' : `${block.status}${block.reason !== null ? ` — ${block.reason}` : ''}`}
      testId={`pf-total-${key}`}
    />
  );
}

export function TotalPerformanceModule({ portfolioId }: { readonly portfolioId: number | null }) {
  const module = portfolioModule('total-performance');
  const query = usePerformance(portfolioId);
  const state = moduleStateOf(portfolioId === null ? 'error' : pageStateOf(query), query.data);
  const view = query.data === undefined || query.data.state === 'empty' ? null : performanceContentOf(query.data.content);
  return (
    <Card
      rank="quiet"
      kicker="Snapshot de performance"
      title={module.title}
      titleId="vx-pf-total-title"
      footer={
        view === null ? (
          <>rendement pondéré par le temps et taux interne, publiés par le serveur</>
        ) : (
          <>
            population <code>{view.population ?? 'non publiée'}</code> · devise <code>{view.currency ?? '—'}</code> · brut et net des frais déclarés
          </>
        )
      }
    >
      <ModuleStatus state={state} raw={query.data?.reason ?? null} />
      {moduleShowsContent(state) && view !== null ? (
        <div className="vx-metrics-row" data-testid="pf-total-performance">
          {(['twr_gross', 'twr_net', 'xirr_gross', 'xirr_net'] as const).map((key) => ratioMetric(key, view.metrics[key]))}
        </div>
      ) : moduleShowsContent(state) ? (
        <p className="vx-module-sentence" role="status">
          Aucun snapshot de performance publié pour ce portefeuille.
        </p>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function CurrencyExposureModule({
  view,
  state,
  reason,
}: {
  readonly view: ValuationContentView | null;
  readonly state: ModuleState;
  readonly reason: string | null;
}) {
  const module = portfolioModule('currency-exposure');
  return (
    <Card rank="quiet" kicker="Valeur marquée par devise" title={module.title} titleId="vx-pf-currency-title" footer={<>un bloc par devise publiée ; aucune conversion, aucun total consolidé</>}>
      {view === null ? (
        <ValuationAbsence state={state} reason={reason} />
      ) : view.blocks.length === 0 ? (
        <p className="vx-module-sentence" role="status">
          Aucune position dérivée du journal.
        </p>
      ) : (
        <div className="vx-metrics-row" data-testid="pf-currency-exposure">
          {view.blocks.map((block) => (
            <Metric
              key={block.currency}
              label={`Devise ${block.currency}`}
              value={block.concentrationStatus === 'OK' ? block.totalValue : null}
              unit={block.currency}
              absentLabel={block.concentrationStatus === 'OK' ? 'non publié' : (block.concentrationStatus ?? 'ABSENT')}
              note={`${block.weights.length} ticker(s) pondéré(s)`}
              testId={`pf-currency-${block.currency}`}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function PositionsModule({
  view,
  state,
  reason,
  excluded,
  selected,
  onInspect,
}: {
  readonly view: ValuationContentView | null;
  readonly state: ModuleState;
  readonly reason: string | null;
  readonly excluded: readonly ExcludedLotRow[];
  readonly selected: string | null;
  readonly onInspect: (lotId: string) => void;
}) {
  const module = portfolioModule('positions');
  const lots: readonly ValuedLotRow[] = view?.valuedLots ?? [];
  return (
    <Card
      rank="quiet"
      kicker="Dérivés du journal"
      title={module.title}
      titleId="vx-pf-table-title"
      className="vx-pf-positions"
      aside={view === null ? undefined : <>{lots.length} valorisé(s) · {excluded.length} exclu(s)</>}
      footer={<>marques SYNTHÉTIQUES ; « Détail » ouvre le lot dans l’inspecteur</>}
    >
      {view === null ? <ValuationAbsence state={state} reason={reason} /> : <PortfolioTable lots={lots} excluded={excluded} selected={selected} onInspect={onInspect} />}
    </Card>
  );
}

// ---------------------------------------------------------------------------

function tickerOf(entry: LedgerTransactionEntry): string | null {
  const instrument = entry.instrument;
  if (typeof instrument !== 'object' || instrument === null) {
    return null;
  }
  const ticker = (instrument as Record<string, unknown>)['ticker'];
  return typeof ticker === 'string' && ticker !== '' ? ticker : null;
}

export function DividendsModule({ transactions }: { readonly transactions: readonly LedgerTransactionEntry[] }) {
  const module = portfolioModule('dividends');
  const dividends = transactions.filter((entry) => entry.kind === 'DIVIDEND');
  return (
    <Card
      rank="quiet"
      kicker="Faits déclarés au journal"
      title={module.title}
      titleId="vx-pf-dividends-title"
      footer={<>{dividends.length} ligne(s) de nature « {LEDGER_KIND_LABELS.DIVIDEND} » ; montants verbatim, jamais sommés</>}
    >
      {dividends.length === 0 ? (
        <p className="vx-module-sentence" role="status" data-testid="pf-dividends-empty">
          Aucun dividende enregistré au journal.
        </p>
      ) : (
        <ul className="vx-inspector-list vx-pf-dividends" data-testid="pf-dividends" aria-label="Dividendes enregistrés">
          {dividends.map((entry) => {
            const ticker = tickerOf(entry);
            return (
              <li key={entry.id} data-testid={`pf-dividend-${entry.id}`}>
                <time dateTime={entry.effective_at}>{entry.effective_at}</time>{' '}
                {ticker !== null ? <code>{ticker}</code> : <span className="vx-cell-absent">sans instrument</span>}{' '}
                <code className="vx-num">{entry.amount}</code> {entry.currency}
                {entry.compensated_by !== null ? <span className="vx-badge vx-badge-warning">compensée</span> : null}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
