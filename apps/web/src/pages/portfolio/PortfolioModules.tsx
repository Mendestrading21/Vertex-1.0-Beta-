import type { LedgerTransactionEntry } from '../../api/client.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { usePerformance } from '../../api/portfolioApi.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { ActivityFeed } from '../../components/widgets/ActivityFeed.tsx';
import type { FeedGroup, FeedItem } from '../../components/widgets/ActivityFeed.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
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
import { signGroupOfServed } from '../../components/widgets/sign.ts';

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
    <div data-module={id} data-size={module.size}>
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

/*
  LA COPIE LOCALE TESTAIT `'-'` AVANT LE ZÉRO : un `-0.00` servi — un zéro que
  le serveur a signé — se lisait comme une PERTE. Et sa branche finale rendait
  `up` sur une chaîne positive NON signée, inventant un gain là où le signe
  n'était pas publié. L'autorité de `sign.ts` fait les deux correctement.
*/
const signOf = signGroupOfServed;

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
            population <code>{view.population ?? 'non publiée'}</code> · devise <code>{view.currency ?? 'non publiée'}</code> · brut et net des frais déclarés
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
  // Groupement sur le JOUR SERVI de l'effet (`effective_at`), jamais sur une
  // horloge locale : le libellé de jour est la date servie elle-même, aucune
  // formule relative (« aujourd'hui ») que la primitive refuserait.
  const parJour = new Map<string, FeedItem[]>();
  for (const entry of dividends) {
    const jour = entry.effective_at.slice(0, 10);
    const ticker = tickerOf(entry);
    const item: FeedItem = {
      id: String(entry.id),
      timeIso: entry.effective_at,
      timeLabel: entry.effective_at,
      title: ticker ?? 'sans instrument',
      amount: entry.amount,
      ...(entry.compensated_by !== null ? { chips: [{ label: 'COMPENSÉE', tone: 'warning' as const }] } : {}),
    };
    parJour.set(jour, [...(parJour.get(jour) ?? []), item]);
  }
  const groupes: FeedGroup[] = [...parJour.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([jour, items]) => ({ dayIso: jour, dayLabel: jour, items }));

  return (
    <Widget
      id="dividends"
      size={module.size}
      kicker="Faits déclarés au journal"
      title={module.title}
      titleId="vx-pf-dividends-title"
      /*
        `ready` EST JUSTE ICI, et c'est le seul endroit du produit où il l'est
        encore en dur. Ce module lit le JOURNAL MANUEL — des faits déclarés par
        l'utilisateur, pas un instantané de marché. Un journal n'a ni fraîcheur,
        ni population, ni état servi : il n'y a rien à propager. Ailleurs, un
        `ready` en dur cachait un instantané périmé ; ici, il n'y a pas
        d'instantané.
      */
      state="ready"
      footer={<>{dividends.length} ligne(s) de nature « {LEDGER_KIND_LABELS.DIVIDEND} » ; montants verbatim, jamais sommés</>}
    >
      <div data-testid={dividends.length === 0 ? 'pf-dividends-empty' : 'pf-dividends'}>
        <ActivityFeed
          groups={groupes}
          ariaLabel="Dividendes enregistrés, groupés par jour servi"
          emptyLabel="Aucun dividende enregistré au journal."
        />
      </div>
    </Widget>
  );
}
