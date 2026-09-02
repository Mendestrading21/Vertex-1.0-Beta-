import type { CurrencyBlockView } from './portfolioView.ts';

/**
 * Concentration par ticker — barres CSS (tokens) + table équivalente.
 *
 * Les poids affichés sont les chaînes serveur VERBATIM
 * (`portfolio.concentration`, poids normalisés + Herfindahl). Le nombre n'est
 * parsé que pour la GÉOMÉTRIE de la barre (largeur), jamais pour recalculer
 * ou reformater une valeur.
 *
 * REFONTE V3 — OÙ VIT LA CHAÎNE EXACTE. Le poids serveur fait jusqu'à
 * 28 décimales (`0.4295692665890570437233410943`, mesuré à l'écran). Affiché
 * tel quel à côté de sa barre, il ne se lit pas : il occupe la moitié de la
 * ligne et aucun œil n'en tire de comparaison. Il n'est pas question de
 * l'arrondir ici — arrondir, c'est produire une valeur que le serveur n'a pas
 * servie, ce que `.claude/rules/frontend.md` interdit.
 *
 * La résolution ne retire donc RIEN. La chaîne exacte reste :
 *   1. dans la table équivalente juste dessous, dont l'en-tête dit lui-même
 *      « Poids normalisé (chaîne serveur) » ;
 *   2. dans le nom accessible de chaque ligne de barre — un lecteur d'écran
 *      entend la valeur complète, chiffre par chiffre.
 * Seul l'œil est soulagé, au profit de la barre, qui est la comparaison qu'il
 * cherchait.
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
                  <li
                    key={entry.ticker}
                    className="vx-pf-bar-row"
                    aria-label={`${entry.ticker} — poids normalisé ${entry.weight}`}
                  >
                    <span className="vx-pf-bar-ticker">
                      <code>{entry.ticker}</code>
                    </span>
                    <span className="vx-pf-bar-track" aria-hidden="true">
                      <span className="vx-pf-bar-fill" style={{ width: `${barWidthPct(entry.weight)}%` }} />
                    </span>
                    {/*
                      `title` porte la chaîne exacte au survol ; le texte visible
                      est la MÊME chaîne, simplement bornée en largeur par le
                      style. Rien n'est réécrit : `text-overflow` coupe le rendu,
                      il ne fabrique pas un arrondi — la distinction compte, car
                      un arrondi ressemblerait à une valeur servie.
                    */}
                    <span className="vx-num vx-pf-bar-value" title={entry.weight}>
                      {entry.weight}
                    </span>
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
