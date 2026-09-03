import { Card } from '../../components/Card.tsx';
import { portfolioModule } from './portfolioModules.ts';
import type { ValuationContentView } from './portfolioView.ts';

/**
 * Module « Valorisation publiée » (planche §7) — chiffres = chaînes serveur
 * VERBATIM, avec provenance (calcul, méthode, hash) et `as_of` du snapshot.
 *
 * - Le badge « Marks : DONNÉES SYNTHÉTIQUES » est TOUJOURS rendu tant que la
 *   population des marques publiée est SYNTHETIC (elle l'est par contrat en
 *   1.0 Beta) : une marque synthétique ne se présente jamais comme réelle.
 * - Le solde d'espèces n'existe PAS dans le snapshot de valorisation publié :
 *   il est affiché comme absent avec sa raison, jamais recalculé côté client
 *   depuis le journal (aucun total TypeScript). Le module « Espèces » de la
 *   planche porte le même aveu à sa place.
 */

function StatusValue({
  status,
  reason,
  value,
  currency,
}: {
  readonly status: string | null;
  readonly reason: string | null;
  readonly value: string | null;
  readonly currency: string;
}) {
  if (status === 'OK' && value !== null) {
    return (
      <span>
        <code className="vx-num">{value}</code> {currency}
      </span>
    );
  }
  return (
    <span className="vx-cell-absent">
      {status ?? 'ABSENT'}
      {reason !== null ? ` — ${reason}` : null}
    </span>
  );
}

export function PortfolioSummary({ valuation }: { readonly valuation: ValuationContentView }) {
  const module = portfolioModule('value');
  return (
    <Card
      rank="quiet"
      kicker="Snapshot du worker"
      title={module.title}
      titleId="vx-pf-summary-title"
      className="vx-pf-value"
      aside={
        valuation.markPopulation === 'SYNTHETIC' ? (
          <span className="vx-badge vx-badge-synthetic" data-testid="pf-marks-badge">
            Marks : DONNÉES SYNTHÉTIQUES
          </span>
        ) : (
          <span className="vx-badge vx-badge-warning" data-testid="pf-marks-badge">
            Population de marques : {valuation.markPopulation ?? 'inconnue'}
          </span>
        )
      }
      footer={
        <>
          <code>as_of</code>{' '}
          {valuation.asOf !== null ? <time dateTime={valuation.asOf}>{valuation.asOf}</time> : '—'}
          {' · '}lots <code>{valuation.lotMethod ?? '—'}</code>
          {' · '}moteur <code>{valuation.engineVersion ?? '—'}</code>
          {' · '}marques :{' '}
          {valuation.marks.status === 'OK' ? (
            <>
              snapshot marchés v{valuation.marks.snapshotVersion ?? '—'} ({valuation.marks.tickersMarked ?? '—'} tickers,{' '}
              {valuation.marks.asOf !== null ? <time dateTime={valuation.marks.asOf}>{valuation.marks.asOf}</time> : '—'})
            </>
          ) : (
            <span className="vx-cell-absent">
              {valuation.marks.status ?? 'ABSENT'}
              {valuation.marks.reason !== null ? ` — ${valuation.marks.reason}` : null}
            </span>
          )}
        </>
      }
    >
      {valuation.blocks.length === 0 ? (
        <p className="vx-cell-absent">
          Aucune position dérivée du journal — aucun agrégat n'est fabriqué.
        </p>
      ) : (
        <dl className="vx-pf-summary-grid" data-testid="pf-summary-grid">
          {valuation.blocks.map((block) => (
            <div key={block.currency} className="vx-pf-summary-block">
              <dt>
                Devise <code>{block.currency}</code>
              </dt>
              <dd>
                <ul className="vx-pf-summary-list">
                  <li>
                    Valeur marquée des lots ouverts :{' '}
                    <StatusValue
                      status={block.concentrationStatus}
                      reason={block.concentrationReason}
                      value={block.totalValue}
                      currency={block.currency}
                    />
                  </li>
                  <li>
                    P&amp;L latent (marques synthétiques) :{' '}
                    <StatusValue
                      status={block.unrealizedStatus}
                      reason={block.unrealizedReason}
                      value={block.totalUnrealized}
                      currency={block.currency}
                    />
                  </li>
                  <li>
                    P&amp;L réalisé (journal, {valuation.lotMethod ?? 'méthode —'}) :{' '}
                    <StatusValue
                      status={block.realizedStatus}
                      reason={block.realizedReason}
                      value={block.totalRealized}
                      currency={block.currency}
                    />
                  </li>
                  <li>
                    Espèces :{' '}
                    <span className="vx-cell-absent" data-testid="pf-cash-absent">
                      non publié — le snapshot de valorisation ne contient pas de solde
                      d'espèces et l'interface n'en calcule aucun ({valuation.coverage.cashEvents ?? 0}{' '}
                      événement(s) de trésorerie au journal)
                    </span>
                  </li>
                </ul>
                <p className="vx-pf-provenance">
                  Provenance :{' '}
                  {block.unrealizedCalculation !== null ? (
                    <>
                      <code>{block.unrealizedCalculation.calculationId ?? '—'}</code> (
                      {block.unrealizedCalculation.engineVersion ?? '—'},{' '}
                      <code className="vx-pf-hash">{block.unrealizedCalculation.inputHash ?? '—'}</code>)
                    </>
                  ) : (
                    'aucun calcul latent publié'
                  )}
                  {' · '}
                  {block.realizedCalculation !== null ? (
                    <>
                      <code>{block.realizedCalculation.calculationId ?? '—'}</code> (
                      {block.realizedCalculation.engineVersion ?? '—'})
                    </>
                  ) : (
                    'aucun calcul réalisé publié'
                  )}
                </p>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  );
}
