import { useState } from 'react';
import { useLocation } from 'react-router-dom';

import { isApiError, postSimulationPreview } from '../../api/client.ts';
import type { SimulationPreviewResponse } from '../../api/client.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { Card } from '../../components/Card.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import { AssumptionsEditor, LegsEditor } from './SimComposer.tsx';
import { EchoModule, KpiModule, MethodModule, PayoffResult, ScenarioGridModule } from './SimResult.tsx';
import { AbsentSimulatorModule, CatalystsModule, SourcesModule } from './SimulatorModules.tsx';
import { StudyInspector } from './StudyInspector.tsx';
import { simulatorModule } from './simulatorModules.ts';
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
 * Page Simulateur (`TL / 06`) — question : « Comment une structure
 * réagit-elle au prix, au temps et à la volatilité ? »
 *
 * LOT-A5 — LA PLANCHE §6 EN ENTIER. `pages-05-06-options-simulator.png`
 * (moitié droite) compose quatorze modules. Neuf sont SERVIS : la structure
 * et les hypothèses déclarées (le composeur borné, unique action
 * « Calculer »), puis — après calcul — le payoff en dominante (points et
 * breakevens certifiés, table équivalente), les résultats certifiés, la
 * grille de scénarios, l'écho des hypothèses, la méthode ; et, à tout
 * moment, les catalyseurs du sous-jacent transféré et la provenance. Cinq
 * n'ont ni source ni contrat : Monte-Carlo, probabilité de profit, chocs,
 * sensibilités, impact portefeuille — rien de probabiliste n'est publié.
 *
 * À VIDE, AUCUNE DOMINANTE : la lumière n'est donnée qu'à un résultat
 * réellement calculé. L'inspecteur porte l'étude (contrat, bornes,
 * origine, puis nature, risque défini, lignée).
 *
 * Tout est validé et calculé CÔTÉ SERVEUR (`vertex_core` via POST
 * /simulations/preview). Un 422 est affiché avec la raison EXACTE. Rien
 * n'est persisté (Sauvegarde : NON_IMPLÉMENTÉ) et rien ici n'est, ni ne
 * devient, transmissible à un courtier.
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

function RejectionNotice({ rejection }: { readonly rejection: RejectionView | null }) {
  return (
    <div className="vx-sim-rejection" role="alert" data-testid="sim-rejection">
      <strong>Prévisualisation refusée par le serveur (422)</strong>
      {rejection === null ? (
        <p>Refus sans corps lisible — aucune raison n'est inventée à la place.</p>
      ) : rejection.kind === 'refusal' ? (
        <>
          <p>
            Raison exacte :{' '}
            {rejection.code === null ? (
              <span className="vx-cell-absent">code de refus non publié</span>
            ) : (
              <code>{rejection.code}</code>
            )}
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

/** La cellule du payoff : le résultat calculé, sinon l'état de l'étude — jamais une dominante à vide. */
function OutcomeCell({ outcome }: { readonly outcome: ResultPhase }) {
  if (outcome.phase === 'ok') {
    return <PayoffResult result={outcome.result} />;
  }
  const module = simulatorModule('payoff');
  return (
    <Card rank="quiet" kicker="Calculé par le serveur" title={module.title} titleId="vx-sim-payoff-title" footer={<>la lumière n’est donnée qu’à un résultat réellement calculé</>}>
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
              Les valeurs décimales elles-mêmes sont validées côté serveur ; seuls les défauts de structure du
              formulaire sont détectés ici.
            </p>
          </div>
        ) : outcome.phase === 'pending' ? (
          <DataStateBoundary state="loading" />
        ) : outcome.phase === 'offline' ? (
          <DataStateBoundary state="offline" detail="L'API locale est injoignable — aucun calcul n'a été effectué." />
        ) : outcome.phase === 'error' ? (
          <DataStateBoundary state="error" detail="Réponse invalide ou inattendue de l'API — aucun résultat affiché." />
        ) : outcome.phase === 'auth-required' ? (
          <AuthRequiredNotice />
        ) : (
          <RejectionNotice rejection={outcome.rejection} />
        )}
      </section>
    </Card>
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
  const result = outcome.phase === 'ok' ? outcome.result : null;

  async function compute(): Promise<void> {
    const built = buildPreviewRequest(legs, assumptions);
    if (built.request === null) {
      setOutcome({ phase: 'invalid_input', issues: built.issues });
      return;
    }
    setOutcome({ phase: 'pending' });
    try {
      const response = await postSimulationPreview(built.request);
      setOutcome({ phase: 'ok', result: response });
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

      <div className="vx-sim-grid vx-board" data-testid="simulator-grid">
        <div data-module="manual-entry">
          <Card
            rank="quiet"
            kicker="Saisie bornée"
            title={`Structure déclarée (${legs.length}/${MAX_LEGS} jambes)`}
            titleId="vx-sim-composer-title"
            className="vx-sim-composer"
            footer={<>chaînes décimales envoyées verbatim ; le serveur valide et calcule tout</>}
          >
            <LegsEditor legs={legs} onChange={setLegs} />
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
          </Card>
        </div>

        <div data-module="base-parameters">
          <Card
            rank="quiet"
            kicker="Saisie bornée"
            title={simulatorModule('base-parameters').title}
            titleId="vx-sim-assumptions-title"
            className="vx-sim-assumptions"
            footer={<>décimaux validés côté serveur ; grilles bornées par le contrat</>}
          >
            <AssumptionsEditor assumptions={assumptions} onChange={setAssumptions} />
          </Card>
        </div>

        <div data-module="payoff" {...(outcome.phase === 'ok' ? { 'data-testid': 'sim-result' } : {})}>
          <OutcomeCell outcome={outcome} />
        </div>
        <div data-module="kpi-served">
          <KpiModule result={result} />
        </div>

        <div data-module="scenarios">
          <ScenarioGridModule result={result} />
        </div>
        <AbsentSimulatorModule id="monte-carlo" />
        <AbsentSimulatorModule id="kpi-probabilistic" />

        <AbsentSimulatorModule id="stress-tests" />
        <AbsentSimulatorModule id="sensitivity" />
        <AbsentSimulatorModule id="portfolio-impact" />
        <div data-module="catalysts">
          <CatalystsModule transfer={transfer} />
        </div>

        <div data-module="key-assumptions">
          <EchoModule result={result} />
        </div>
        <div data-module="sources">
          <SourcesModule transfer={transfer} />
        </div>
        <div data-module="method">
          <MethodModule result={result} />
        </div>
      </div>

      <StudyInspector result={result} transfer={transfer} legCount={legs.length} />
    </article>
  );
}
