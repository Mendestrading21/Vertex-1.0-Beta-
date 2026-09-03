import type { AdviceView } from './analysisView.ts';
import { ADVICE_STATUS_FR, DIRECTION_FR } from './analysisView.ts';

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
            {advice.asOf !== null ? <time dateTime={advice.asOf}>{advice.asOf}</time> : '—'}
            {' → '}
            {advice.validUntil !== null ? (
              <time dateTime={advice.validUntil}>{advice.validUntil}</time>
            ) : (
              '—'
            )}{' '}
            (horizon {advice.horizon ?? '—'})
          </dd>
        </div>
        <div>
          <dt>Moteur</dt>
          <dd>
            <code>{advice.engineVersion ?? '—'}</code>
          </dd>
        </div>
        <div>
          <dt>Résumé de risque</dt>
          <dd>{advice.riskSummary ?? '—'}</dd>
        </div>
      </dl>

      <details className="vx-advice-gates">
        <summary>
          Gates : {advice.gates.length} évaluées, {blockedGates.length} non passées (fail-closed)
        </summary>
        <ul>
          {advice.gates.map((gate) => (
            <li key={gate.gateId} data-status={gate.status}>
              <code>{gate.gateId}</code>{' '}
              <span className="vx-gate-status" data-status={gate.status}>
                {gate.status}
              </span>{' '}
              — <code>{gate.reasonCode}</code>
              {gate.message !== '' ? ` : ${gate.message}` : null}
            </li>
          ))}
        </ul>
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

