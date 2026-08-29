import { useState } from 'react';
import { useLocation } from 'react-router-dom';

import { isApiError, postSimulationPreview } from '../../api/client.ts';
import type { SimulationPreviewResponse } from '../../api/client.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import { PayoffChart } from './PayoffChart.tsx';
import type { AssumptionsDraft, LegDraft, RejectionView } from './simulatorView.ts';
import {
  EMPTY_ASSUMPTIONS,
  MAX_LEGS,
  assumptionsFromTransfer,
  buildPreviewRequest,
  legDraftFromTransfer,
  makeLegDraft,
  rejectionViewOf,
} from './simulatorView.ts';
import { parseSimulatorTransfer } from './transfer.ts';

/**
 * Page Simulateur — question : « Comment une structure réagit-elle au prix,
 * au temps et à la volatilité ? »
 *
 * Étude THÉORIQUE d'une structure DÉCLARÉE : le composeur borné collecte des
 * jambes (« jambe longue / jambe courte », CALL/PUT/STOCK) et des hypothèses
 * en champs texte décimaux — tout est validé et calculé CÔTÉ SERVEUR
 * (`vertex_core` via POST /simulations/preview, CSRF géré par le client).
 * Unique action : « Calculer ». Un 422 est affiché avec la raison EXACTE du
 * serveur (code + message verbatim, explication française). Rien n'est
 * persisté (Sauvegarde : NON_IMPLÉMENTÉ) et rien ici n'est, ni ne devient,
 * transmissible à un courtier.
 */

type ResultPhase =
  | { readonly phase: 'idle' }
  | { readonly phase: 'invalid_input'; readonly issues: readonly string[] }
  | { readonly phase: 'pending' }
  | { readonly phase: 'ok'; readonly result: SimulationPreviewResponse }
  | { readonly phase: 'rejected'; readonly rejection: RejectionView | null }
  | { readonly phase: 'auth-required' }
  | { readonly phase: 'offline' }
  | { readonly phase: 'error' };

function LegRow({
  leg,
  index,
  onChange,
  onRemove,
}: {
  readonly leg: LegDraft;
  readonly index: number;
  readonly onChange: (leg: LegDraft) => void;
  readonly onRemove: () => void;
}) {
  const prefix = `leg-${leg.id}`;
  return (
    <fieldset className="vx-leg">
      <legend>Jambe {index + 1}</legend>
      <div className="vx-leg-grid">
        <label htmlFor={`${prefix}-side`}>
          Sens
          <select
            id={`${prefix}-side`}
            value={leg.side}
            onChange={(event) => {
              onChange({ ...leg, side: event.target.value === 'SHORT' ? 'SHORT' : 'LONG' });
            }}
          >
            <option value="LONG">Jambe longue (quantité positive)</option>
            <option value="SHORT">Jambe courte (quantité négative)</option>
          </select>
        </label>
        <label htmlFor={`${prefix}-count`}>
          Quantité (entier)
          <input
            id={`${prefix}-count`}
            type="text"
            inputMode="numeric"
            value={leg.count}
            onChange={(event) => {
              onChange({ ...leg, count: event.target.value });
            }}
          />
        </label>
        <label htmlFor={`${prefix}-right`}>
          Type
          <select
            id={`${prefix}-right`}
            value={leg.right}
            onChange={(event) => {
              const right =
                event.target.value === 'PUT'
                  ? 'PUT'
                  : event.target.value === 'STOCK'
                    ? 'STOCK'
                    : 'CALL';
              onChange({
                ...leg,
                right,
                strike: right === 'STOCK' ? '' : leg.strike,
              });
            }}
          >
            <option value="CALL">CALL</option>
            <option value="PUT">PUT</option>
            <option value="STOCK">STOCK (jambe linéaire)</option>
          </select>
        </label>
        <label htmlFor={`${prefix}-strike`}>
          Strike (décimal)
          <input
            id={`${prefix}-strike`}
            type="text"
            inputMode="decimal"
            value={leg.strike}
            disabled={leg.right === 'STOCK'}
            onChange={(event) => {
              onChange({ ...leg, strike: event.target.value });
            }}
          />
        </label>
        <label htmlFor={`${prefix}-premium`}>
          Prime unitaire déclarée (décimal)
          <input
            id={`${prefix}-premium`}
            type="text"
            inputMode="decimal"
            value={leg.premium}
            onChange={(event) => {
              onChange({ ...leg, premium: event.target.value });
            }}
          />
        </label>
        <label htmlFor={`${prefix}-multiplier`}>
          Multiplicateur (entier)
          <input
            id={`${prefix}-multiplier`}
            type="text"
            inputMode="numeric"
            value={leg.multiplier}
            onChange={(event) => {
              onChange({ ...leg, multiplier: event.target.value });
            }}
          />
        </label>
      </div>
      <button type="button" className="vx-leg-remove" onClick={onRemove}>
        Retirer la jambe {index + 1}
      </button>
    </fieldset>
  );
}

function AssumptionField({
  id,
  label,
  value,
  onChange,
  hint,
}: {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly hint?: string;
}) {
  return (
    <label htmlFor={id}>
      {label}
      <input
        id={id}
        type="text"
        inputMode="decimal"
        value={value}
        {...(hint !== undefined ? { placeholder: hint } : {})}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />
    </label>
  );
}

function RejectionNotice({ rejection }: { readonly rejection: RejectionView | null }) {
  return (
    <div className="vx-sim-rejection" role="alert" data-testid="sim-rejection">
      <strong>Prévisualisation refusée par le serveur (422)</strong>
      {rejection === null ? (
        <p>Refus sans corps lisible — aucune raison n'est inventée à la place.</p>
      ) : rejection.kind === 'refusal' ? (
        <>
          <p>
            Raison exacte : <code>{rejection.code ?? '—'}</code>
            {rejection.message !== null ? (
              <>
                {' — '}
                <span className="vx-sim-rejection-message">{rejection.message}</span>
              </>
            ) : null}
          </p>
          {rejection.explanation !== null ? <p>{rejection.explanation}</p> : null}
        </>
      ) : (
        <>
          <p>Contrat d'entrée violé — défauts exacts renvoyés par le serveur :</p>
          <ul>
            {rejection.wireIssues.map((issue) => (
              <li key={issue}>
                <code>{issue}</code>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function ResultPanel({ result }: { readonly result: SimulationPreviewResponse }) {
  const definedRisk = result.defined_risk;
  const definedRiskDetail =
    typeof definedRisk['detail'] === 'string' ? definedRisk['detail'] : null;
  const definedRiskCode =
    typeof definedRisk['reason_code'] === 'string' ? definedRisk['reason_code'] : null;
  const assumptions = result.assumptions;
  const assumptionText = (key: string): string => {
    const value = assumptions[key];
    return typeof value === 'string' ? value : '—';
  };
  const assumptionList = (key: string): string => {
    const value = assumptions[key];
    return Array.isArray(value)
      ? value.filter((entry): entry is string => typeof entry === 'string').join(', ')
      : '—';
  };
  return (
    <section className="vx-sim-result" aria-labelledby="vx-sim-result-title" data-testid="sim-result">
      <h3 id="vx-sim-result-title">
        Résultat <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span>{' '}
        <span className="vx-sim-nature">({result.value_nature})</span>
      </h3>

      <p className="vx-sim-defined-risk">
        Vérification de risque défini : <code>{definedRiskCode ?? '—'}</code>
        {definedRiskDetail !== null ? ` — ${definedRiskDetail}` : null}
      </p>

      <PayoffChart
        points={result.payoff_points}
        breakevens={result.breakevens}
        maxGain={result.max_gain_on_grid}
        maxLoss={result.max_loss_on_grid}
      />

      <dl className="vx-sim-summary">
        <div>
          <dt>Gain max sur la grille évaluée</dt>
          <dd>
            <code className="vx-num">{result.max_gain_on_grid.pnl}</code> à spot{' '}
            <code className="vx-num">{result.max_gain_on_grid.at_spot}</code>
          </dd>
        </div>
        <div>
          <dt>Perte max sur la grille évaluée</dt>
          <dd>
            <code className="vx-num">{result.max_loss_on_grid.pnl}</code> à spot{' '}
            <code className="vx-num">{result.max_loss_on_grid.at_spot}</code>
          </dd>
        </div>
        <div>
          <dt>Breakevens certifiés</dt>
          <dd>
            {result.breakevens.length === 0 ? (
              'aucun sur le domaine évalué'
            ) : (
              <ul className="vx-sim-breakevens" data-testid="sim-breakevens">
                {result.breakevens.map((breakeven) => (
                  <li key={breakeven.spot}>
                    spot <code className="vx-num">{breakeven.spot}</code> — résidu certifié{' '}
                    <code className="vx-num">{breakeven.payoff_at_spot}</code> (encadré par{' '}
                    <code className="vx-num">{breakeven.bracket_low}</code> /{' '}
                    <code className="vx-num">{breakeven.bracket_high}</code>)
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
      </dl>

      <h4>Hypothèses écho (déclarées, renvoyées par le serveur)</h4>
      <dl className="vx-sim-echo">
        <div>
          <dt>Spot</dt>
          <dd className="vx-num">{assumptionText('spot')}</dd>
        </div>
        <div>
          <dt>Volatilité (annualisée)</dt>
          <dd className="vx-num">{assumptionText('volatility')}</dd>
        </div>
        <div>
          <dt>Taux</dt>
          <dd className="vx-num">{assumptionText('rate')}</dd>
        </div>
        <div>
          <dt>Dividendes</dt>
          <dd className="vx-num">{assumptionText('dividend_yield')}</dd>
        </div>
        <div>
          <dt>Coûts déclarés</dt>
          <dd className="vx-num">{assumptionText('fees')}</dd>
        </div>
        <div>
          <dt>Grille de spots</dt>
          <dd className="vx-num">{assumptionList('spot_grid')}</dd>
        </div>
        <div>
          <dt>Grille de temps (années)</dt>
          <dd className="vx-num">{assumptionList('time_grid_years')}</dd>
        </div>
      </dl>

      {result.warnings.length > 0 ? (
        <div className="vx-sim-warnings" role="note">
          <h4>Avertissements du serveur</h4>
          <ul>
            {result.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div
        className="vx-ohlcv-scroll"
        tabIndex={0}
        role="region"
        aria-label="Points de P&L défilants"
      >
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
    </section>
  );
}

export function SimulatorPage() {
  const location = useLocation();
  const transfer = parseSimulatorTransfer(
    typeof location.state === 'object' && location.state !== null
      ? (location.state as Record<string, unknown>)['simulatorTransfer']
      : undefined,
  );

  const [legs, setLegs] = useState<readonly LegDraft[]>(() =>
    transfer !== null ? [legDraftFromTransfer(transfer)] : [makeLegDraft()],
  );
  const [assumptions, setAssumptions] = useState<AssumptionsDraft>(() =>
    transfer !== null ? assumptionsFromTransfer(transfer) : EMPTY_ASSUMPTIONS,
  );
  const [outcome, setOutcome] = useState<ResultPhase>({ phase: 'idle' });

  function updateAssumption(key: keyof AssumptionsDraft): (value: string) => void {
    return (value) => {
      setAssumptions((previous) => ({ ...previous, [key]: value }));
    };
  }

  async function compute(): Promise<void> {
    const built = buildPreviewRequest(legs, assumptions);
    if (built.request === null) {
      setOutcome({ phase: 'invalid_input', issues: built.issues });
      return;
    }
    setOutcome({ phase: 'pending' });
    try {
      const result = await postSimulationPreview(built.request);
      setOutcome({ phase: 'ok', result });
    } catch (error) {
      if (isApiError(error)) {
        if (error.kind === 'AUTH_REQUIRED') {
          setOutcome({ phase: 'auth-required' });
          return;
        }
        if (error.kind === 'NETWORK') {
          setOutcome({ phase: 'offline' });
          return;
        }
        if (error.status === 422) {
          setOutcome({ phase: 'rejected', rejection: rejectionViewOf(error.detail) });
          return;
        }
      }
      setOutcome({ phase: 'error' });
    }
  }

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-simulator">
      <div className="vx-page-header">
        <h1 id="vx-page-title-simulator">Simulateur</h1>
        <p className="vx-page-question">
          Comment une structure réagit-elle au prix, au temps et à la volatilité ?
        </p>
      </div>

      <p className="vx-sim-scope" role="note">
        Étude théorique d'une structure DÉCLARÉE — tous les chiffres sont calculés par le serveur
        (<code>vertex_core</code>) et étiquetés THÉORIQUE ; rien ici n'est un prix exécutable ni
        une capacité de transaction. Sauvegarde : <code>NON_IMPLÉMENTÉ</code> — lot ultérieur.
      </p>

      {transfer !== null ? (
        <p className="vx-sim-transfer" role="status" data-testid="sim-transfer-note">
          Préremplie depuis Options : {transfer.right}{' '}
          <code className="vx-num">{transfer.strike}</code> · {transfer.expiration} ·{' '}
          <code>{transfer.tradingClass}</code> (sous-jacent <code>{transfer.underlying}</code>
          {transfer.conId !== null ? (
            <>
              , con_id <code>{transfer.conId}</code>
            </>
          ) : null}
          ) — prime suggérée côté {transfer.premiumSide ?? '—'}, spot et IV du snapshot ; tout
          reste éditable.{' '}
          {transfer.population === 'SYNTHETIC' ? (
            <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
          ) : null}
        </p>
      ) : null}

      <section className="vx-sim-composer" aria-labelledby="vx-sim-composer-title">
        <h2 id="vx-sim-composer-title">Structure déclarée ({legs.length}/{MAX_LEGS} jambes)</h2>
        {legs.map((leg, index) => (
          <LegRow
            key={leg.id}
            leg={leg}
            index={index}
            onChange={(next) => {
              setLegs((previous) => previous.map((entry) => (entry.id === leg.id ? next : entry)));
            }}
            onRemove={() => {
              setLegs((previous) => previous.filter((entry) => entry.id !== leg.id));
            }}
          />
        ))}
        <button
          type="button"
          className="vx-sim-add-leg"
          disabled={legs.length >= MAX_LEGS}
          onClick={() => {
            setLegs((previous) => [...previous, makeLegDraft()]);
          }}
        >
          Ajouter une jambe
        </button>
      </section>

      <section className="vx-sim-assumptions" aria-labelledby="vx-sim-assumptions-title">
        <h2 id="vx-sim-assumptions-title">Hypothèses déclarées</h2>
        <div className="vx-sim-assumptions-grid">
          <AssumptionField
            id="sim-spot"
            label="Spot déclaré (décimal)"
            value={assumptions.spot}
            onChange={updateAssumption('spot')}
          />
          <AssumptionField
            id="sim-vol"
            label="Volatilité annualisée (décimal, 0.25 = 25 %/an)"
            value={assumptions.volatility}
            onChange={updateAssumption('volatility')}
          />
          <AssumptionField
            id="sim-rate"
            label="Taux annualisé (décimal)"
            value={assumptions.rate}
            onChange={updateAssumption('rate')}
            hint="ex. 0.02"
          />
          <AssumptionField
            id="sim-div"
            label="Rendement de dividende annualisé (décimal)"
            value={assumptions.dividendYield}
            onChange={updateAssumption('dividendYield')}
            hint="ex. 0.00"
          />
          <AssumptionField
            id="sim-fees"
            label="Coûts déclarés à l'expiration (décimal)"
            value={assumptions.fees}
            onChange={updateAssumption('fees')}
          />
          <AssumptionField
            id="sim-spot-grid"
            label="Grille de spots (1 à 41 valeurs, séparées par des virgules)"
            value={assumptions.spotGrid}
            onChange={updateAssumption('spotGrid')}
            hint="ex. 300, 330, 366.08, 400, 430"
          />
          <AssumptionField
            id="sim-time-grid"
            label="Grille de temps en années (1 à 8 valeurs)"
            value={assumptions.timeGridYears}
            onChange={updateAssumption('timeGridYears')}
            hint="ex. 0.0767, 0.0384, 0"
          />
        </div>
      </section>

      <div className="vx-sim-actions">
        <button
          type="button"
          className="vx-primary-action"
          onClick={() => {
            void compute();
          }}
          disabled={outcome.phase === 'pending'}
        >
          Calculer
        </button>
        <span className="vx-sim-actions-note">
          Unique action de la page — une prévisualisation d'analyse, jamais une transaction.
        </span>
      </div>

      <section className="vx-sim-outcome" aria-live="polite" aria-label="Résultat du calcul">
        {outcome.phase === 'idle' ? (
          <DataStateBoundary
            state="empty"
            detail="Aucun résultat — déclarer une structure et ses hypothèses puis Calculer. Rien n'est précalculé."
          />
        ) : outcome.phase === 'invalid_input' ? (
          <div className="vx-sim-invalid" role="alert" data-testid="sim-invalid-input">
            <strong>Entrée invalide — rien n'a été envoyé</strong>
            <ul>
              {outcome.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
            <p>
              Les valeurs décimales elles-mêmes sont validées côté serveur ; seuls les défauts de
              structure du formulaire sont détectés ici.
            </p>
          </div>
        ) : outcome.phase === 'pending' ? (
          <DataStateBoundary state="loading" />
        ) : outcome.phase === 'offline' ? (
          <DataStateBoundary
            state="offline"
            detail="L'API locale est injoignable — aucun calcul n'a été effectué."
          />
        ) : outcome.phase === 'error' ? (
          <DataStateBoundary
            state="error"
            detail="Réponse invalide ou inattendue de l'API — aucun résultat affiché."
          />
        ) : outcome.phase === 'auth-required' ? (
          <AuthRequiredNotice />
        ) : outcome.phase === 'rejected' ? (
          <RejectionNotice rejection={outcome.rejection} />
        ) : (
          <ResultPanel result={outcome.result} />
        )}
      </section>
    </article>
  );
}
