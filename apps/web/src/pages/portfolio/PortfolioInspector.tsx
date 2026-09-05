import { Link } from 'react-router-dom';

import type { LedgerTransactionEntry, PortfolioResponse } from '../../api/client.ts';
import { useCalendar } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { AgendaLine } from '../../components/calendar/AgendaLine.tsx';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { moduleShowsContent, moduleStateOf } from '../../components/moduleState.ts';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { calendarEventsOf } from '../calendar/calendarView.ts';
import type { ValuationContentView, ValuedLotRow } from './portfolioView.ts';
import { signGroupOfText } from '../../components/widgets/sign.ts';

/**
 * Inspecteur de la page Portefeuille (planche §7 : « ligne sélectionnée,
 * provenance manuelle, corrections et impacts »).
 *
 * Deux contenus, un panneau à la fois : le LOT ouvert depuis la table —
 * ses chaînes serveur, son poids publié, les faits du journal qui le
 * concernent et leurs corrections, les catalyseurs publiés pour son ticker —
 * sinon la vérité du snapshot de valorisation. Aucune nouvelle vérité : ce
 * panneau n'additionne rien, ne convertit rien, ne déduit aucune position.
 */

const CATALYST_LINES = 4;

function tickerOf(entry: LedgerTransactionEntry): string | null {
  const instrument = entry.instrument;
  if (typeof instrument !== 'object' || instrument === null) {
    return null;
  }
  const ticker = (instrument as Record<string, unknown>)['ticker'];
  return typeof ticker === 'string' && ticker !== '' ? ticker : null;
}

function TickerCatalysts({ ticker }: { readonly ticker: string }) {
  const query = useCalendar(null);
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const events =
    data === undefined ? [] : calendarEventsOf(Array.isArray(data.agenda) ? data.agenda : []).filter((event) => event.ticker === ticker);
  if (!moduleShowsContent(state) || data === undefined) {
    return (
      <p className="vx-inspector-note" role="status">
        Agenda non lisible ({state}) : aucun catalyseur affiché.
      </p>
    );
  }
  if (events.length === 0) {
    return (
      <p className="vx-inspector-note" role="status" data-testid="pf-lot-catalysts-empty">
        Aucun événement publié pour <code>{ticker}</code> dans l’agenda.
      </p>
    );
  }
  return (
    <ul className="vx-agenda-mini" aria-label={`Événements publiés pour ${ticker}`} data-testid="pf-lot-catalysts">
      {events.slice(0, CATALYST_LINES).map((event) => (
        <AgendaLine key={event.eventId} event={event} />
      ))}
    </ul>
  );
}

export function PositionInspector({
  lot,
  view,
  transactions,
  onClose,
}: {
  readonly lot: ValuedLotRow;
  readonly view: ValuationContentView;
  readonly transactions: readonly LedgerTransactionEntry[];
  readonly onClose: () => void;
}) {
  const block = view.blocks.find((candidate) => candidate.currency === lot.currency) ?? null;
  const weight = block?.weights.find((entry) => entry.ticker === lot.ticker)?.weight ?? null;
  const facts = transactions.filter((entry) => tickerOf(entry) === lot.ticker);
  const corrections = facts.filter((entry) => entry.compensates !== null || entry.compensated_by !== null);
  return (
    <InspectorPanel subject={lot.ticker}>
      <div className="vx-sheet-head">
        <p className="vx-inspector-note">
          lot <code>{lot.lotId}</code> <span className="vx-badge vx-badge-synthetic">MARQUE SYNTHÉTIQUE</span>
        </p>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>

      <SnapshotFacts
        testId="pf-lot-facts"
        facts={[
          { label: 'Provenance', value: 'journal manuel — faits déclarés après coup, aucun compte courtier' },
          { label: 'Quantité restante', value: <code className="vx-num">{lot.quantity}</code> },
          {
            label: 'Coût unitaire',
            value: (
              <>
                <code className="vx-num">{lot.unitCost}</code> {lot.currency}
              </>
            ),
          },
          {
            label: 'Mark',
            value: (
              <>
                <code className="vx-num">{lot.mark}</code> {lot.currency} (clôture synthétique)
              </>
            ),
          },
          {
            label: 'Valeur marquée',
            value: (
              <>
                <code className="vx-num">{lot.marketValue}</code> {lot.currency}
              </>
            ),
          },
          {
            label: 'P&L latent',
            value: (
              <>
                <code
                  className="vx-num"
                  {...(signGroupOfText(lot.unrealizedPnl) === null
                    ? {}
                    : { 'data-sign': signGroupOfText(lot.unrealizedPnl) })}
                >
                  {lot.unrealizedPnl}
                </code>{' '}
                {lot.currency}
              </>
            ),
          },
          {
            label: 'Poids publié',
            value: weight === null ? 'non publié' : <code className="vx-num">{weight}</code>,
          },
          { label: 'Méthode de lots', value: <code>{publishedOr(view.lotMethod)}</code> },
        ]}
      />

      <h3 className="vx-snapshot-block-title">Faits du journal pour ce ticker</h3>
      {facts.length === 0 ? (
        <p className="vx-inspector-note">Aucune ligne de journal ne porte ce ticker.</p>
      ) : (
        <ul className="vx-inspector-list" data-testid="pf-lot-journal">
          {facts.map((entry) => (
            <li key={entry.id}>
              n°{entry.id} · <code>{entry.kind}</code> · <time dateTime={entry.effective_at}>{entry.effective_at}</time> ·{' '}
              <code className="vx-num">{entry.amount}</code> {entry.currency}
              {entry.compensates !== null ? <span className="vx-badge vx-badge-warning">compense n°{entry.compensates}</span> : null}
              {entry.compensated_by !== null ? <span className="vx-badge vx-badge-warning">compensée par n°{entry.compensated_by}</span> : null}
            </li>
          ))}
        </ul>
      )}
      <p className="vx-inspector-note" data-testid="pf-lot-corrections">
        {corrections.length === 0
          ? 'Aucune correction compensatoire sur ce ticker.'
          : `${corrections.length} ligne(s) de correction compensatoire sur ce ticker — l’historique reste append-only.`}
      </p>

      <h3 className="vx-snapshot-block-title">Catalyseurs publiés</h3>
      <TickerCatalysts ticker={lot.ticker} />

      <p className="vx-inspector-note">
        <Link to={`/analysis/${encodeURIComponent(lot.ticker)}`}>Ouvrir le dossier d’analyse</Link>
      </p>
    </InspectorPanel>
  );
}

export function ValuationInspector({ data, view }: { readonly data: PortfolioResponse; readonly view: ValuationContentView | null }) {
  return (
    <InspectorPanel subject="Valorisation publiée">
      <SnapshotFacts
        testId="pf-snapshot-facts"
        facts={[
          {
            label: 'Portefeuille',
            value: (
              <>
                <code>{data.portfolio.name}</code> · base <code>{data.portfolio.base_currency}</code>
              </>
            ),
          },
          { label: 'État servi', value: <code>{data.valuation.state}</code> },
          {
            label: 'Snapshot',
            value: (
              <>
                v{publishedOr(data.valuation.snapshot_version)} · <code>{publishedOr(view?.engineVersion)}</code>
              </>
            ),
          },
          {
            label: 'as_of',
            value: data.valuation.as_of === null ? 'non publié' : <time dateTime={data.valuation.as_of}>{data.valuation.as_of}</time>,
          },
          {
            label: 'Âge publié',
            value: <FreshnessBadge ageSeconds={data.valuation.age_seconds} sourceLabel="âge publié par le serveur" />,
          },
          { label: 'Population des marques', value: <code>{publishedOr(view?.markPopulation)}</code> },
          { label: 'Méthode de lots', value: <code>{publishedOr(view?.lotMethod)}</code> },
          {
            label: 'Marques',
            value:
              view === null
                ? 'non publiées'
                : `${publishedOr(view.marks.status)} · ${publishedOr(view.marks.tickersMarked)} tickers · snapshot marchés v${publishedOr(view.marks.snapshotVersion)}`,
          },
          {
            label: 'Couverture',
            value:
              view === null
                ? 'non publiée'
                : `${publishedOr(view.coverage.eventsConsidered)} événements considérés · ${publishedOr(view.coverage.lotsValued)} lot(s) valorisé(s) · ${publishedOr(view.coverage.lotsExcluded)} exclu(s) · ${publishedOr(view.coverage.compensationPairs)} paire(s) de compensation`,
          },
          { label: 'Journal', value: `${data.transactions.length} ligne(s) déclarée(s)` },
          ...(data.valuation.reason === null ? [] : [{ label: 'Raison serveur', value: <code>{data.valuation.reason}</code> }]),
        ]}
      />
      <p className="vx-inspector-note">
        Sélectionner un lot (bouton « Détail » dans la table) pour lire sa provenance, son poids publié, ses faits
        de journal et ses catalyseurs.
      </p>
    </InspectorPanel>
  );
}
