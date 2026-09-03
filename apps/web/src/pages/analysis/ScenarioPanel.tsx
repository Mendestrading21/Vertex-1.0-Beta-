import type { ScenariosView } from './analysisView.ts';
import { scenarioAbsentLabel } from './analysisView.ts';

/** Scénarios THÉORIQUES repricés par le worker, ou leur absence typée. */
export function ScenarioPanel({ scenarios }: { readonly scenarios: ScenariosView | null }) {
  if (scenarios === null) {
    return (
      <section className="vx-scenarios" aria-labelledby="vx-scenarios-title">
        <h3 id="vx-scenarios-title">Scénarios</h3>
        <p role="status">Aucun bloc scénarios publié.</p>
      </section>
    );
  }
  if (scenarios.status === 'ABSENT') {
    return (
      <section className="vx-scenarios" aria-labelledby="vx-scenarios-title">
        <h3 id="vx-scenarios-title">Scénarios</h3>
        <p role="status" data-testid="scenarios-absent">
          {scenarioAbsentLabel(scenarios.reason)}
        </p>
      </section>
    );
  }
  const scenario = scenarios.grid[0] ?? [];
  return (
    <section className="vx-scenarios" aria-labelledby="vx-scenarios-title">
      <h3 id="vx-scenarios-title">
        Scénarios <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span>
      </h3>
      <p className="vx-scenarios-basis">
        Base : {scenarios.basisLabel ?? '—'} — grille P&amp;L (avant coûts déclarés) repricée par le
        worker (<code>{scenarios.calculationId ?? '—'}</code>), IV inchangée.
      </p>
      <div
        className="vx-ohlcv-scroll"
        tabIndex={0}
        role="region"
        aria-label="Grille de scénarios défilante"
      >
        <table className="vx-scenarios-table" aria-label="Grille de scénarios théorique (P&L par spot et temps)">
          <thead>
            <tr>
              <th scope="col">Temps restant (années)</th>
              {scenarios.spotGrid.map((spot) => (
                <th scope="col" key={spot} className="vx-num">
                  spot {spot}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scenarios.timeGridYears.map((time, timeIndex) => (
              <tr key={time}>
                <th scope="row" className="vx-num">
                  {time}
                </th>
                {(scenario[timeIndex] ?? []).map((cell, spotIndex) => (
                  <td key={scenarios.spotGrid[spotIndex] ?? spotIndex} className="vx-num">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

