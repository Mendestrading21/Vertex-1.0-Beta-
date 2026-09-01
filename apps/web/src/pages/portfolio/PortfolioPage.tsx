import { useQueryClient } from '@tanstack/react-query';

import { pageStateOf, queryKeyForResource } from '../../api/hooks.ts';
import { usePortfolio } from '../../api/portfolioApi.ts';
import type { PageDataState } from '../../api/hooks.ts';
import type { PortfolioResponse } from '../../api/client.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { ConcentrationPanel } from './ConcentrationPanel.tsx';
import { CsvImportPanel } from './CsvImportPanel.tsx';
import { LedgerPanel } from './LedgerPanel.tsx';
import { PortfolioSummary } from './PortfolioSummary.tsx';
import { PortfolioTable } from './PortfolioTable.tsx';
import { PerformanceSection } from './performance/PerformanceSection.tsx';
import { TransactionForm } from './TransactionForm.tsx';
import { valuationContentOf } from './portfolioView.ts';
import type { ValuationContentView } from './portfolioView.ts';

/**
 * Page Portefeuille — question : « Quelles expositions et concentrations
 * résultent de mon ledger manuel ? »
 *
 * Le journal manuel est la SEULE source de positions — aucun compte courtier,
 * jamais). La valorisation affichée est le snapshot publié par le worker,
 * relayé verbatim : marques SYNTHÉTIQUES étiquetées, lots exclus listés à
 * part avec raison, totaux serveur uniquement. L'interface enregistre des
 * FAITS PASSÉS et n'émet aucune instruction.
 *
 * Depuis le LOT-08, la page porte aussi le module Performance, absorbé depuis
 * l'ancienne destination `/performance` (docs/05-design/PAGE_ARBITRATION.md).
 * Le contrat des douze pages range l'« historique » du registre parmi les
 * widgets de Portefeuille, et les deux vues lisent le même portefeuille
 * manuel : ce sont deux lectures d'UN seul registre, pas deux destinations.
 */

/** État du CADRE de valorisation (les sections dérivées du snapshot). */
export function valuationFrameStateOf(
  queryState: PageDataState,
  data: PortfolioResponse | undefined,
): { readonly state: DataState | 'auth-required'; readonly view: ValuationContentView | null } {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return { state: queryState, view: null };
  }
  if (data === undefined) {
    return { state: 'error', view: null };
  }
  if (data.valuation.state === 'empty') {
    return { state: 'empty', view: null };
  }
  const view = valuationContentOf(data.valuation);
  if (view === null) {
    return { state: 'error', view: null };
  }
  // Le relais publie l'âge de l'instantané et bascule en `stale` au-delà
  // du budget de fraîcheur du registre. Le contenu reste VISIBLE sous un
  // bandeau « Données périmées » : ce qui était interdit, c'est de le
  // servir sans dire son âge, pas de le servir. Testé AVANT `partial` :
  // un instantané périmé l'est en entier, la partialité de son contenu
  // est la moins forte des deux affirmations.
  if (data.valuation.state === 'stale') {
    return { state: 'stale', view };
  }
  // Dégradation honnête signalée PAR LE SERVEUR : marques absentes ou lots
  // exclus → cadre « partiel » (le contenu daté reste visible sous bandeau).
  if (view.marks.status !== 'OK' || view.excludedLots.length > 0 || view.coverage.invalidPositions.length > 0) {
    return { state: 'partial', view };
  }
  return { state: queryState, view };
}

export function PortfolioPage() {
  const query = usePortfolio();
  const queryClient = useQueryClient();
  const queryState = pageStateOf(query);
  const data = query.data;
  const frame = valuationFrameStateOf(queryState, data);

  // Refetch explicite après une écriture acceptée : le signal SSE couvre la
  // valorisation (publication du worker), l'invalidation locale couvre le
  // journal immédiatement (la réponse GET porte les deux).
  function refetchPortfolio(): void {
    void queryClient.invalidateQueries({ queryKey: queryKeyForResource('portfolio_valuation/any') });
  }

  const excludedRows =
    frame.view === null
      ? []
      : [...frame.view.excludedLots, ...frame.view.coverage.invalidPositions];

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-portfolio">
      <div className="vx-page-header">
        <h1 id="vx-page-title-portfolio">Portefeuille</h1>
        <p className="vx-page-question">
          Quelles expositions et concentrations résultent de mon ledger manuel ?
        </p>
      </div>

      <p className="vx-pf-scope" role="note">
        Journal manuel uniquement : les positions dérivent des faits que VOUS avez déclarés après
        coup. Aucun compte, position ou P&amp;L de courtier n'est lu — cette capacité n'existe pas.
      </p>

      {queryState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : queryState === 'loading' || queryState === 'offline' || queryState === 'error' ? (
        <DataStateBoundary
          state={queryState}
          {...(queryState === 'offline'
            ? { detail: "L'API locale est injoignable — aucun journal ni valorisation affiché." }
            : queryState === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — rien n'est affiché à la place." }
              : {})}
        />
      ) : data === undefined ? (
        <DataStateBoundary state="error" detail="Réponse absente — rien n'est affiché à la place." />
      ) : (
        <>
          <SyntheticBanner population={frame.view?.markPopulation ?? null} />

          <section aria-label="Valorisation et expositions">
            {frame.state === 'empty' ? (
              <DataStateBoundary
                state="empty"
                detail={
                  data.valuation.reason !== null
                    ? `Aucune valorisation publiée — raison serveur : ${data.valuation.reason}`
                    : 'Aucune valorisation publiée par le worker pour ce portefeuille.'
                }
              />
            ) : frame.view === null ? (
              <DataStateBoundary
                state="error"
                detail="Snapshot de valorisation illisible — rien n'est reconstruit côté client."
              />
            ) : (
              <DataStateBoundary
                state={frame.state === 'auth-required' ? 'error' : frame.state}
                {...(frame.state === 'partial'
                  ? {
                      detail:
                        'Couverture incomplète signalée par le serveur : lots exclus ou marques indisponibles — voir la section « Lots exclus ».',
                    }
                  : {})}
                {...(frame.view.asOf !== null ? { asOfLabel: frame.view.asOf } : {})}
              >
                <PortfolioSummary valuation={frame.view} />
                <PortfolioTable lots={frame.view.valuedLots} excluded={excludedRows} />
                <ConcentrationPanel blocks={frame.view.blocks} />
              </DataStateBoundary>
            )}
          </section>

          <PerformanceSection />

          <LedgerPanel transactions={data.transactions} onCompensated={refetchPortfolio} />
          <TransactionForm onRecorded={refetchPortfolio} />
          <CsvImportPanel onImported={refetchPortfolio} />
        </>
      )}
    </article>
  );
}
