import type { ComparisonView } from './chartsView.ts';

/**
 * Comparaison base 100 — module SERVI de la planche §8 (LOT-S2).
 *
 * Le serveur publie `indicators.rebased_comparison` : deux séries ramenées à
 * la MÊME base par `market.rebased_series`, sur les SEULES séances communes
 * aux deux calendriers, intersectées côté worker. Ce composant n'a donc rien
 * à rebaser, rien à aligner et rien à arrondir — un rebasage ici serait un
 * calcul de performance en TypeScript, que `.claude/rules/frontend.md`
 * interdit, et une seconde autorité financière.
 *
 * Les valeurs sont des CHAÎNES serveur, rendues telles quelles. Un refus est
 * affiché avec son code exact et sa phrase : `BENCHMARK_NOT_OBSERVED` et
 * `INSUFFICIENT_SAMPLE` n'appellent pas la même action, et un « — » les
 * confondrait.
 *
 * La table EST la représentation : elle porte le même contenu qu'une courbe,
 * lisible au clavier et par un lecteur d'écran, sans axe à interpréter.
 */
export function RebasedComparison({
  comparison,
  instrument,
}: {
  readonly comparison: ComparisonView;
  readonly instrument: string;
}) {
  // LOT P5 — le TITRE vit désormais sur le widget qui porte ce corps ; le
  // répéter ici donnait deux fois « Comparaison base 100 » l'un sous l'autre.
  const sujet =
    comparison.kind === 'served'
      ? `${instrument} contre ${comparison.benchmark}`
      : 'aucun indice de référence retenu';

  return (
    <section
      className="vx-comparison"
      aria-label={`Comparaison base 100 — ${sujet}`}
      data-testid="charts-comparison"
    >
      <p className="vx-comparison-question">
        Comment cette série se compare-t-elle à d’autres, ramenées à une base commune ?{' '}
        <strong>{sujet}</strong>
      </p>

      {comparison.kind === 'none' ? (
        <p className="vx-cell-absent" role="status" data-testid="charts-comparison-none">
          Aucune comparaison publiée par le serveur pour ce dossier.
        </p>
      ) : comparison.kind === 'unreadable' ? (
        <p className="vx-cell-absent" role="status" data-testid="charts-comparison-unreadable">
          Comparaison publiée dans une forme que cette page ne sait pas lire — rien n’est
          affiché à la place.
        </p>
      ) : comparison.kind === 'absent' ? (
        <>
          <p className="vx-cell-absent" role="status" data-testid="charts-comparison-absent">
            {comparison.status}
            {comparison.detail === null ? null : ` — ${comparison.detail}`}
          </p>
          {comparison.rejected.length === 0 ? null : (
            <ul className="vx-comparison-rejected" data-testid="charts-comparison-rejected">
              {comparison.rejected.map((rejet) => (
                <li key={rejet}>
                  <code>{rejet}</code>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <>
          <dl className="vx-comparison-meta" data-testid="charts-comparison-meta">
            <div>
              <dt>Indice de référence</dt>
              <dd>{comparison.benchmark}</dd>
            </div>
            <div>
              <dt>Base</dt>
              <dd>
                {comparison.baseValue} ({comparison.unit}, sans dimension)
              </dd>
            </div>
            <div>
              <dt>Devise · base d’ajustement</dt>
              <dd>
                {comparison.currency ?? 'non publiée'} ·{' '}
                {comparison.adjustmentBasis ?? 'non publiée'}
              </dd>
            </div>
            <div>
              <dt>Séances communes</dt>
              <dd>
                {comparison.commonSessions ?? 'non publié'}
                {comparison.firstTradingDay === null || comparison.lastTradingDay === null
                  ? null
                  : ` — ${comparison.firstTradingDay} → ${comparison.lastTradingDay}`}
              </dd>
            </div>
          </dl>

          <div
            className="vx-ohlcv-scroll"
            tabIndex={0}
            role="region"
            aria-label="Table de la comparaison base 100, défilante"
          >
            <table
              className="vx-ohlcv-table"
              data-testid="charts-comparison-table"
              aria-label={`Comparaison base 100 de ${instrument} et ${comparison.benchmark}`}
            >
              <thead>
                <tr>
                  <th scope="col">Séance</th>
                  <th scope="col">{instrument}</th>
                  <th scope="col">{comparison.benchmark}</th>
                </tr>
              </thead>
              <tbody>
                {comparison.points.map((point) => (
                  <tr key={point.tradingDay}>
                    <th scope="row">
                      <time dateTime={point.tradingDay}>{point.tradingDay}</time>
                    </th>
                    <td className="vx-num">{point.instrument}</td>
                    <td className="vx-num">{point.benchmark}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="vx-comparison-method">
            Séances alignées et ramenées à la base par le serveur (
            <code>market.rebased_series</code>
            {comparison.method === null ? null : ` : ${comparison.method}`}). Cette page
            n’en rebase ni n’en aligne aucune : elle affiche les valeurs publiées.
          </p>
        </>
      )}
    </section>
  );
}
