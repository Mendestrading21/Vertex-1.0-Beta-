import type { SimulationPreviewResponse } from '../../api/client.ts';
import { Card } from '../../components/Card.tsx';
import { Metric } from '../../components/Metric.tsx';
import { frDecimal } from '../../components/markets/marketsView.ts';
import { PayoffChart } from './PayoffChart.tsx';
import { simulatorModule } from './simulatorModules.ts';

/**
 * Les modules de RÉSULTAT du Simulateur — tous lisent la même réponse
 * `POST /simulations/preview`, calculée par le serveur pour une structure
 * DÉCLARÉE. Rien n'est recalculé : chaînes décimales verbatim, breakevens
 * certifiés, grilles publiées, lignée des calculs. Sans calcul, chaque
 * module DIT qu'aucun calcul n'a été effectué.
 */

function recordString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function NoResult({ testId }: { readonly testId: string }) {
  return (
    <p className="vx-module-sentence" role="status" data-testid={testId}>
      Aucun calcul effectué : déclarer une structure et ses hypothèses, puis Calculer.
    </p>
  );
}

function signOf(value: string): 'up' | 'down' | 'flat' {
  if (value.startsWith('-')) {
    return 'down';
  }
  return /^[+]?0*(\.0+)?$/.test(value) ? 'flat' : 'up';
}

// ---------------------------------------------------------------------------

export function PayoffResult({ result }: { readonly result: SimulationPreviewResponse }) {
  const module = simulatorModule('payoff');
  return (
    <Card
      rank="dominant"
      kicker="Calculé par le serveur"
      title={module.title}
      titleId="vx-sim-result-title"
      className="vx-sim-result"
      aside={
        <>
          <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span>{' '}
          <span className="vx-sim-nature">({result.value_nature})</span>
        </>
      }
      footer={
        <>
          points serveur exacts reliés linéairement ; la table porte exactement les mêmes chaînes — jamais un prix
          exécutable
        </>
      }
    >
      <div data-testid="sim-payoff">
        <PayoffChart
          points={result.payoff_points}
          breakevens={result.breakevens}
          maxGain={result.max_gain_on_grid}
          maxLoss={result.max_loss_on_grid}
        />
        <p className="vx-sim-defined-risk">
          Breakevens certifiés :{' '}
          {result.breakevens.length === 0 ? (
            'aucun sur le domaine évalué'
          ) : (
            <ul className="vx-sim-breakevens" data-testid="sim-breakevens">
              {result.breakevens.map((breakeven) => (
                <li key={breakeven.spot}>
                  spot <code className="vx-num">{breakeven.spot}</code> — résidu certifié{' '}
                  <code className="vx-num">{breakeven.payoff_at_spot}</code> (encadré par{' '}
                  <code className="vx-num">{breakeven.bracket_low}</code> / <code className="vx-num">{breakeven.bracket_high}</code>)
                </li>
              ))}
            </ul>
          )}
        </p>
        <div className="vx-ohlcv-scroll" tabIndex={0} role="region" aria-label="Points de P&L défilants">
          <table className="vx-sim-points" aria-label="Points de P&L à l'expiration (valeurs serveur exactes)">
            <thead>
              <tr>
                <th scope="col">Spot terminal</th>
                <th scope="col">P&amp;L théorique</th>
              </tr>
            </thead>
            <tbody>
              {result.payoff_points.map((point) => (
                <tr key={point.spot}>
                  <th scope="row" className="vx-num">
                    {point.spot}
                  </th>
                  <td className="vx-num">{point.pnl}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function KpiModule({ result }: { readonly result: SimulationPreviewResponse | null }) {
  const module = simulatorModule('kpi-served');
  const definedRisk = result?.defined_risk ?? null;
  const code = definedRisk === null ? null : recordString(definedRisk, 'reason_code');
  const detail = definedRisk === null ? null : recordString(definedRisk, 'detail');
  return (
    <Card
      rank="quiet"
      kicker="Certifié par le serveur"
      title={module.title}
      titleId="vx-sim-kpi-title"
      footer={<>extrêmes sur la GRILLE déclarée, jamais sur tout le domaine ; aucune probabilité</>}
    >
      {result === null ? (
        <NoResult testId="sim-kpi-empty" />
      ) : (
        <div data-testid="sim-kpi">
          <div className="vx-metrics-row">
            <Metric
              label="Gain max sur la grille"
              value={frDecimal(result.max_gain_on_grid.pnl)}
              sign={signOf(result.max_gain_on_grid.pnl)}
              note={`à spot ${result.max_gain_on_grid.at_spot}`}
            />
            <Metric
              label="Perte max sur la grille"
              value={frDecimal(result.max_loss_on_grid.pnl)}
              sign={signOf(result.max_loss_on_grid.pnl)}
              note={`à spot ${result.max_loss_on_grid.at_spot}`}
            />
            <Metric
              label="Breakevens certifiés"
              value={String(result.breakevens.length)}
              {...(result.breakevens.length === 0 ? {} : { note: result.breakevens.map((entry) => entry.spot).join(' · ') })}
            />
          </div>
          <p className="vx-sim-defined-risk">
            Risque défini : <code>{code ?? 'non publié'}</code>
            {detail === null ? null : ` — ${detail}`}
          </p>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function ScenarioGridModule({ result }: { readonly result: SimulationPreviewResponse | null }) {
  const module = simulatorModule('scenarios');
  const grid = result?.scenario_grid[0] ?? [];
  return (
    <Card
      rank="quiet"
      kicker="Repricée par le worker, valeur théorique"
      title={module.title}
      titleId="vx-sim-scenarios-title"
      footer={<>P&amp;L par spot et temps restant, avant coûts déclarés ; volatilité déclarée inchangée</>}
    >
      {result === null ? (
        <NoResult testId="sim-scenarios-empty" />
      ) : result.scenario_spot_grid.length === 0 || result.scenario_time_grid_years.length === 0 ? (
        <p className="vx-module-sentence" role="status">
          Aucune grille de scénarios publiée pour cette structure.
        </p>
      ) : (
        <div className="vx-ohlcv-scroll" tabIndex={0} role="region" aria-label="Grille de scénarios défilante">
          <table className="vx-scenarios-table" aria-label="Grille de scénarios théorique (P&L par spot et temps)" data-testid="sim-scenarios">
            <thead>
              <tr>
                <th scope="col">Temps restant (années)</th>
                {result.scenario_spot_grid.map((spot) => (
                  <th scope="col" key={spot} className="vx-num">
                    spot {spot}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.scenario_time_grid_years.map((time, timeIndex) => (
                <tr key={time}>
                  <th scope="row" className="vx-num">
                    {time}
                  </th>
                  {(grid[timeIndex] ?? []).map((cell, spotIndex) => (
                    <td key={result.scenario_spot_grid[spotIndex] ?? spotIndex} className="vx-num">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function EchoModule({ result }: { readonly result: SimulationPreviewResponse | null }) {
  const module = simulatorModule('key-assumptions');
  const assumptions = result?.assumptions ?? null;
  const text = (key: string): string => {
    const value = assumptions?.[key];
    return typeof value === 'string' ? value : '—';
  };
  const list = (key: string): string => {
    const value = assumptions?.[key];
    return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string').join(', ') : '—';
  };
  return (
    <Card rank="quiet" kicker="Renvoyées par le serveur" title={module.title} titleId="vx-sim-echo-title" footer={<>ce que le serveur a réellement appliqué, pas ce que le formulaire contenait</>}>
      {result === null ? (
        <NoResult testId="sim-echo-empty" />
      ) : (
        <dl className="vx-sim-echo" data-testid="sim-echo">
          <div>
            <dt>Spot</dt>
            <dd className="vx-num">{text('spot')}</dd>
          </div>
          <div>
            <dt>Volatilité (annualisée)</dt>
            <dd className="vx-num">{text('volatility')}</dd>
          </div>
          <div>
            <dt>Taux</dt>
            <dd className="vx-num">{text('rate')}</dd>
          </div>
          <div>
            <dt>Dividendes</dt>
            <dd className="vx-num">{text('dividend_yield')}</dd>
          </div>
          <div>
            <dt>Coûts déclarés</dt>
            <dd className="vx-num">{text('fees')}</dd>
          </div>
          <div>
            <dt>Grille de spots</dt>
            <dd className="vx-num">{list('spot_grid')}</dd>
          </div>
          <div>
            <dt>Grille de temps (années)</dt>
            <dd className="vx-num">{list('time_grid_years')}</dd>
          </div>
        </dl>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function MethodModule({ result }: { readonly result: SimulationPreviewResponse | null }) {
  const module = simulatorModule('method');
  const calculations = result === null ? [] : Object.entries(result.calculations);
  return (
    <Card rank="quiet" kicker="Lignée des calculs" title={module.title} titleId="vx-sim-method-title" footer={<>rien n’est persisté ; rien ici n’est, ni ne devient, transmissible à un courtier</>}>
      {result === null ? (
        <NoResult testId="sim-method-empty" />
      ) : (
        <div data-testid="sim-method">
          <p className="vx-module-sentence">
            Nature des valeurs : <code>{result.value_nature}</code>
          </p>
          {calculations.length === 0 ? (
            <p className="vx-module-sentence">Aucune lignée de calcul publiée.</p>
          ) : (
            <ul className="vx-inspector-list">
              {calculations.map(([name, meta]) => {
                const record = typeof meta === 'object' && meta !== null ? (meta as Record<string, unknown>) : null;
                return (
                  <li key={name}>
                    <code>{name}</code> → <code>{record === null ? 'non publié' : (recordString(record, 'calculation_id') ?? 'non publié')}</code>
                    {record === null ? null : <span className="vx-inspector-unit"> · {recordString(record, 'engine_version') ?? 'moteur non publié'}</span>}
                  </li>
                );
              })}
            </ul>
          )}
          {result.warnings.length > 0 ? (
            <div className="vx-sim-warnings" role="note">
              <h3 className="vx-snapshot-block-title">Avertissements du serveur</h3>
              <ul>
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}
