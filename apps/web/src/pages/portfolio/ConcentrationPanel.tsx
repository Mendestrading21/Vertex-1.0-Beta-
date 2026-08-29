import type { CurrencyBlockView } from './portfolioView.ts';

/**
 * Concentration par ticker — barres CSS (tokens) + table équivalente.
 *
 * Les poids affichés sont les chaînes serveur VERBATIM
 * (`portfolio.concentration`, poids normalisés + Herfindahl). Le nombre n'est
 * parsé que pour la GÉOMÉTRIE de la barre (largeur), jamais pour recalculer
 * ou reformater une valeur.
 */

/** Largeur de barre en % (géométrie de rendu uniquement). */
export function barWidthPct(weight: string): number {
  const parsed = Number(weight);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return 0;
  }
  return Math.min(100, parsed * 100);
}

export function ConcentrationPanel({ blocks }: { readonly blocks: readonly CurrencyBlockView[] }) {
  return (
    <section className="vx-pf-concentration" aria-labelledby="vx-pf-concentration-title">
      <h2 id="vx-pf-concentration-title">Concentration par ticker</h2>
      {blocks.map((block) => (
        <div key={block.currency} className="vx-pf-concentration-block">
          <h3>
            Devise <code>{block.currency}</code>
          </h3>
          {block.concentrationStatus !== 'OK' ? (
            <p className="vx-cell-absent" data-testid={`pf-concentration-absent-${block.currency}`}>
              {block.concentrationStatus ?? 'ABSENT'}
              {block.concentrationReason !== null ? ` — ${block.concentrationReason}` : null} : aucune
              concentration n'est affichée sans calcul serveur publié.
            </p>
          ) : (
            <>
              <ul className="vx-pf-bars" data-testid={`pf-bars-${block.currency}`}>
                {block.weights.map((entry) => (
                  <li key={entry.ticker} className="vx-pf-bar-row">
                    <span className="vx-pf-bar-ticker">
                      <code>{entry.ticker}</code>
                    </span>
                    <span className="vx-pf-bar-track" aria-hidden="true">
                      <span className="vx-pf-bar-fill" style={{ width: `${barWidthPct(entry.weight)}%` }} />
                    </span>
                    <span className="vx-num vx-pf-bar-value">{entry.weight}</span>
                  </li>
                ))}
              </ul>
              <table className="vx-pf-concentration-table" aria-label={`Poids de concentration (${block.currency})`}>
                <thead>
                  <tr>
                    <th scope="col">Ticker</th>
                    <th scope="col">Poids normalisé (chaîne serveur)</th>
                  </tr>
                </thead>
                <tbody>
                  {block.weights.map((entry) => (
                    <tr key={entry.ticker}>
                      <th scope="row">
                        <code>{entry.ticker}</code>
                      </th>
                      <td className="vx-num">{entry.weight}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="vx-pf-concentration-meta">
                Indice de Herfindahl : <code className="vx-num">{block.herfindahl ?? '—'}</code>
                {' · '}valeur totale marquée :{' '}
                <code className="vx-num">{block.totalValue ?? '—'}</code> {block.currency}
                {block.concentrationCalculation !== null ? (
                  <>
                    {' · '}calcul <code>{block.concentrationCalculation.calculationId ?? '—'}</code> (
                    {block.concentrationCalculation.engineVersion ?? '—'})
                  </>
                ) : null}
              </p>
            </>
          )}
        </div>
      ))}
    </section>
  );
}
