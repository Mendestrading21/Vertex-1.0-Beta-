import type { MarketsBreadth } from '../../api/client.ts';
import { frDecimal } from '../../components/markets/marketsView.ts';

/**
 * BreadthPanel — jauge factuelle en BARRE LINÉAIRE (jamais circulaire).
 *
 * Deux barres INDÉPENDANTES (règle FreshnessCoverageGauge) : la breadth
 * (part des instruments couverts en hausse) puis la couverture (couverts /
 * attendus) avec le marqueur du seuil. Toutes les largeurs et tous les
 * pourcentages viennent du SERVEUR (chaînes déjà rendues) : le navigateur ne
 * calcule ni pourcentage, ni seuil, ni position de marqueur.
 *
 * `status = "INVALID"` (couverture sous le seuil) : aucune valeur de
 * remplacement — le panneau nomme la raison et n'affiche pas de barre.
 *
 * Les comptes (hausses, baisses, inchangés, couverts) sont ceux PUBLIÉS par
 * le worker, relayés tels quels : aucun n'est déduit des autres ici, et ils
 * restent affichés dans l'état INVALID — le ratio est refusé, pas les faits.
 */
export function BreadthPanel({ breadth }: { readonly breadth: MarketsBreadth }) {
  const counts = `${breadth.above_count} en hausse, ${breadth.down_count} en baisse, ${breadth.flat_count} stables sur ${breadth.covered_count} couverts (univers ${breadth.universe_size})`;

  if (breadth.status === 'INVALID' || breadth.value_pct === null) {
    return (
      <section className="vx-breadth" aria-labelledby="vx-breadth-title">
        <h3 id="vx-breadth-title">Breadth globale</h3>
        <p className="vx-breadth-invalid" role="status">
          <strong>Breadth non calculable</strong>
          <span>
            Couverture {frDecimal(breadth.coverage_pct)} % sous le seuil requis de{' '}
            {frDecimal(breadth.coverage_threshold_pct)} % (raison serveur :{' '}
            {breadth.reason ?? 'non fournie'}). Aucune valeur de remplacement.
          </span>
        </p>
        <p className="vx-breadth-counts">{counts}</p>
      </section>
    );
  }

  return (
    <section className="vx-breadth" aria-labelledby="vx-breadth-title">
      <h3 id="vx-breadth-title">Breadth globale</h3>

      <div className="vx-breadth-row">
        <span className="vx-breadth-label" id="vx-breadth-value-label">
          Breadth
        </span>
        <div
          className="vx-breadth-bar"
          role="meter"
          aria-labelledby="vx-breadth-value-label"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Number.parseFloat(breadth.value_pct)}
          aria-valuetext={`${frDecimal(breadth.value_pct)} %`}
        >
          <div className="vx-breadth-fill" style={{ width: `${breadth.value_pct}%` }} />
        </div>
        <span className="vx-breadth-figure">{frDecimal(breadth.value_pct)} %</span>
      </div>

      <div className="vx-breadth-row">
        <span className="vx-breadth-label" id="vx-breadth-coverage-label">
          Couverture
        </span>
        <div
          className="vx-breadth-bar"
          role="meter"
          aria-labelledby="vx-breadth-coverage-label"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Number.parseFloat(breadth.coverage_pct)}
          aria-valuetext={`${frDecimal(breadth.coverage_pct)} % (seuil ${frDecimal(breadth.coverage_threshold_pct)} %)`}
        >
          <div
            className="vx-breadth-fill vx-breadth-fill-coverage"
            style={{ width: `${breadth.coverage_pct}%` }}
          />
          <div
            className="vx-breadth-threshold"
            style={{ left: `${breadth.coverage_threshold_pct}%` }}
            aria-hidden="true"
          />
        </div>
        <span className="vx-breadth-figure">
          {frDecimal(breadth.coverage_pct)} % (seuil {frDecimal(breadth.coverage_threshold_pct)} %)
        </span>
      </div>

      <p className="vx-breadth-counts">{counts}</p>
    </section>
  );
}
