import { StepList } from '../../components/widgets/StepList.tsx';
import type { Step, StepEvidence } from '../../components/widgets/StepList.tsx';
import type { StatusChipTone } from '../../components/widgets/StatusChip.tsx';
import type { AdviceView, GateView } from './analysisView.ts';
import { ADVICE_STATUS_FR, DIRECTION_FR } from './analysisView.ts';

/**
 * Teintes des trois statuts de gate SERVIS. Vocabulaire FERMÉ : un statut hors
 * de ce dictionnaire reste neutre plutôt que d'emprunter une couleur au
 * hasard. La correspondance reprend celle que `.vx-gate-status` applique
 * depuis le LOT-A4 — une seule signification par couleur.
 */
const GATE_TONES: Readonly<Record<string, StatusChipTone>> = {
  PASS: 'positive',
  DEGRADE: 'warning',
  BLOCK: 'negative',
};

/**
 * LOT P2b — LA PREUVE ÉTAIT SERVIE ET INVISIBLE. `GateResult` publie
 * `observed_values` et `thresholds` (`contracts/decision.py`), le moteur les
 * remplit à chaque point de retour et le worker les publie entiers. La page
 * n'en lisait rien : le lecteur voyait « BLOCK / UNEVALUABLE » sans jamais
 * savoir CE QUE la gate avait regardé.
 *
 * Rien n'est calculé ici : les couples servis sont relayés dans l'ordre du
 * serveur, à leur valeur publiée.
 */
function gateStep(gate: GateView): Step {
  const evidence: StepEvidence[] = [
    { title: 'Observé', facts: gate.observedValues },
    { title: 'Seuils', facts: gate.thresholds },
  ];
  return {
    id: gate.gateId,
    label: gate.gateId,
    status: gate.status,
    tone: GATE_TONES[gate.status] ?? 'neutral',
    code: gate.reasonCode,
    evidence,
    ...(gate.message === '' ? {} : { detail: gate.message }),
  };
}

/**
 * Le verdict de l'unique `AdviceEngine`, relayé : statut canonique et
 * direction DISTINCTS, validité, gates dépliables avec leur reason_code,
 * limites et faits d'explication publiés. Rien n'est reconstruit.
 */
export function AdviceCard({ advice }: { readonly advice: AdviceView | null }) {
  if (advice === null) {
    return (
      <section className="vx-advice" aria-labelledby="vx-advice-title">
        <h3 id="vx-advice-title">Verdict analytique</h3>
        <p role="status">Aucun AdviceResult publié dans ce dossier — rien n'est reconstruit.</p>
      </section>
    );
  }
  const statusExplained = ADVICE_STATUS_FR[advice.status];
  const directionExplained = DIRECTION_FR[advice.direction];
  const blockedGates = advice.gates.filter((gate) => gate.status !== 'PASS');
  return (
    <section className="vx-advice" aria-labelledby="vx-advice-title" data-testid="advice-card">
      <h3 id="vx-advice-title">Verdict analytique (AdviceEngine, autorité unique)</h3>
      <dl className="vx-advice-facts">
        <div>
          <dt>Statut</dt>
          <dd>
            <span className="vx-advice-status" data-status={advice.status}>
              {advice.status}
            </span>{' '}
            {statusExplained !== undefined ? `— ${statusExplained}` : null}
          </dd>
        </div>
        <div>
          <dt>Direction (distincte du statut)</dt>
          <dd>
            <span className="vx-advice-direction" data-direction={advice.direction}>
              {advice.direction}
            </span>{' '}
            {directionExplained !== undefined ? `— ${directionExplained}` : null}
          </dd>
        </div>
        <div>
          <dt>Validité</dt>
          <dd>
            {advice.asOf === null ? (
              <span className="vx-cell-absent">instant non publié</span>
            ) : (
              <time dateTime={advice.asOf}>{advice.asOf}</time>
            )}
            {' → '}
            {advice.validUntil === null ? (
              <span className="vx-cell-absent">échéance de validité non publiée</span>
            ) : (
              <time dateTime={advice.validUntil}>{advice.validUntil}</time>
            )}{' '}
            (horizon {advice.horizon ?? 'non publié'})
          </dd>
        </div>
        <div>
          <dt>Moteur</dt>
          <dd>
            <code>{advice.engineVersion ?? 'non publié'}</code>
          </dd>
        </div>
        <div>
          <dt>Résumé de risque</dt>
          <dd>
            {advice.riskSummary ?? (
              <span className="vx-cell-absent">résumé de risque non publié</span>
            )}
          </dd>
        </div>
      </dl>

      <details className="vx-advice-gates">
        <summary>
          Gates : {advice.gates.length} évaluées, {blockedGates.length} non passées (fail-closed)
        </summary>
        <StepList
          ordered
          ariaLabel="Gates de décision publiées, avec leur preuve servie"
          steps={advice.gates.map(gateStep)}
          emptyLabel="Aucune gate publiée dans cet AdviceResult."
        />
      </details>

      {advice.limitations.length > 0 ? (
        <div className="vx-advice-limitations">
          <h4>Limites déclarées</h4>
          <ul>
            {advice.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {advice.explanationFacts.length > 0 ? (
        <div className="vx-advice-facts-list">
          <h4>Faits d'explication publiés</h4>
          <ul>
            {advice.explanationFacts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

